from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .schema_validation import validate


RUNTIME_EVENT_TYPES = {"segment_playable", "lesson_complete", "fallback"}
READINESS_EVENT_TYPES = {"segment_ready", "visual_ready", "audio_ready", "segment_admitted"}
TERMINAL_SEGMENT_STATES = {"completed", "fallback", "cancelled"}


def canonical_hash(value: dict[str, Any], omitted: tuple[str, ...] = ()) -> str:
    canonical_value = {key: item for key, item in value.items() if key not in omitted}
    canonical = json.dumps(canonical_value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def manifest_hash(manifest: dict[str, Any]) -> str:
    return canonical_hash(manifest, ("manifest_hash",))


def envelope_hash(envelope: dict[str, Any]) -> str:
    return canonical_hash(envelope, ("envelope_hash",))


def event_payload_hash(event: dict[str, Any]) -> str:
    ignored = ("schema_version", "event_id", "trace_id", "offset_ms", "payload_hash")
    return canonical_hash(event, ignored)


def make_event(
    *,
    event_id: str,
    trace_id: str,
    event_type: str,
    manifest: dict[str, Any],
    offset_ms: int,
    segment: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    attempt: int = 0,
    cache_status: str = "not_applicable",
) -> dict[str, Any]:
    event = {
        "schema_version": "segment-event/1.0",
        "event_id": event_id,
        "trace_id": trace_id,
        "event_type": event_type,
        "session_id": manifest["session_id"],
        "lesson_id": manifest["lesson_id"],
        "manifest_version": manifest["manifest_version"],
        "manifest_hash": manifest["manifest_hash"],
        "segment_id": segment["segment_id"] if segment else None,
        "segment_version": segment["segment_version"] if segment else None,
        "ordinal": segment["ordinal"] if segment else None,
        "offset_ms": offset_ms,
        "attempt": attempt,
        "cache_status": cache_status,
        "payload": payload or {},
        "payload_hash": "",
    }
    event["payload_hash"] = event_payload_hash(event)
    return event


@dataclass
class SegmentState:
    descriptor: dict[str, Any]
    envelope_ready: bool = False
    visual_ready: bool = False
    audio_ready: bool = False
    admitted: bool = False
    admission_received: bool = False
    playable: bool = False
    started: bool = False
    terminal: str | None = None
    first_readiness_offset_ms: int | None = None
    playable_offset_ms: int | None = None
    cache_write_requested: bool = False


@dataclass
class RuntimeResult:
    trace_id: str
    records: list[dict[str, Any]] = field(default_factory=list)
    derived_events: list[dict[str, Any]] = field(default_factory=list)
    milestones: dict[str, int] = field(default_factory=dict)
    valid_cache_entries: set[str] = field(default_factory=set)


class ProgressiveRuntime:
    def __init__(
        self,
        manifest: dict[str, Any],
        envelopes: dict[str, dict[str, Any]],
        schemas: dict[str, dict[str, Any]],
        *,
        trace_id: str,
        segment_timeout_ms: int = 8_000,
    ) -> None:
        manifest_errors = validate(manifest, schemas["manifest"])
        if manifest_errors:
            raise ValueError(f"Invalid manifest: {manifest_errors}")
        if manifest["manifest_hash"] != manifest_hash(manifest):
            raise ValueError("Invalid manifest hash")
        self._validate_manifest_semantics(manifest)

        self.manifest = copy.deepcopy(manifest)
        self.envelopes = copy.deepcopy(envelopes)
        self.schemas = schemas
        self.trace_id = trace_id
        self.segment_timeout_ms = segment_timeout_ms
        self.now_ms = 0
        self.opened = False
        self.manifest_ready = False
        self.lesson_terminal: str | None = None
        self.processed_event_ids: dict[str, str] = {}
        self.result = RuntimeResult(trace_id=trace_id)
        self.segments = {
            descriptor["segment_id"]: SegmentState(copy.deepcopy(descriptor))
            for descriptor in manifest["segments"]
        }
        self.ordered_segment_ids = [
            item["segment_id"] for item in sorted(manifest["segments"], key=lambda item: item["ordinal"])
        ]

        if set(self.envelopes) != set(self.segments):
            raise ValueError("Envelope set must match manifest segment set")
        for segment_id, envelope in self.envelopes.items():
            errors = validate(envelope, schemas["envelope"])
            if errors:
                raise ValueError(f"Invalid envelope {segment_id}: {errors}")
            if envelope["envelope_hash"] != envelope_hash(envelope):
                raise ValueError(f"Invalid envelope hash: {segment_id}")
            self._validate_envelope_identity(envelope, self.segments[segment_id].descriptor)
            cue_offsets = [cue["at_ms"] for cue in envelope["cues"]]
            if cue_offsets != sorted(cue_offsets) or len(cue_offsets) != len(set(cue_offsets)):
                raise ValueError(f"Envelope cues must be strictly ordered: {segment_id}")

    @staticmethod
    def _validate_manifest_semantics(manifest: dict[str, Any]) -> None:
        segments = manifest["segments"]
        segment_ids = [item["segment_id"] for item in segments]
        ordinals = [item["ordinal"] for item in segments]
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("Manifest segment IDs must be unique")
        if sorted(ordinals) != list(range(len(segments))):
            raise ValueError("Manifest ordinals must be contiguous from zero")
        ordinal_by_id = {item["segment_id"]: item["ordinal"] for item in segments}
        for item in segments:
            for dependency in item["depends_on"]:
                if dependency not in ordinal_by_id:
                    raise ValueError("Manifest dependency must reference a known segment")
                if ordinal_by_id[dependency] >= item["ordinal"]:
                    raise ValueError("Manifest dependency must reference an earlier segment")

    def _validate_envelope_identity(
        self, envelope: dict[str, Any], descriptor: dict[str, Any]
    ) -> None:
        expected = {
            "session_id": self.manifest["session_id"],
            "lesson_id": self.manifest["lesson_id"],
            "manifest_version": self.manifest["manifest_version"],
            "manifest_hash": self.manifest["manifest_hash"],
            "segment_id": descriptor["segment_id"],
            "segment_version": descriptor["segment_version"],
            "ordinal": descriptor["ordinal"],
            "knowledge_package_hash": self.manifest["knowledge_package_hash"],
        }
        for key, value in expected.items():
            if envelope[key] != value:
                raise ValueError(f"Envelope identity mismatch: {key}")

    def advance_to(self, offset_ms: int) -> None:
        if offset_ms < self.now_ms:
            return
        self.now_ms = offset_ms
        if self.lesson_terminal:
            return

        for state in self.segments.values():
            deadline = (
                state.first_readiness_offset_ms + self.segment_timeout_ms
                if state.first_readiness_offset_ms is not None
                else None
            )
            if deadline is not None and offset_ms >= deadline and not state.playable and not state.terminal:
                self._fallback_segment(state, deadline, "segment.readiness_timeout")

        if offset_ms >= self.manifest["hard_deadline_ms"] and not self.lesson_terminal:
            for state in self.segments.values():
                if not state.terminal:
                    state.terminal = "fallback"
            self._emit("fallback", None, self.manifest["hard_deadline_ms"], {"reason": "lesson.hard_deadline"})
            self.lesson_terminal = "fallback"
            self.result.milestones.setdefault("fallback_ready", self.manifest["hard_deadline_ms"])

    def process(self, event: dict[str, Any]) -> dict[str, Any]:
        schema_errors = validate(event, self.schemas["event"])
        if schema_errors:
            return self._record(event, "rejected", "event.schema_invalid", False)
        if event["payload_hash"] != event_payload_hash(event):
            return self._record(event, "rejected", "event.payload_hash_mismatch", False)

        previous_hash = self.processed_event_ids.get(event["event_id"])
        if previous_hash is not None:
            if previous_hash == event["payload_hash"]:
                return self._record(event, "duplicate", "event.duplicate", False)
            return self._record(event, "rejected", "event.conflicting_duplicate", False)

        self.processed_event_ids[event["event_id"]] = event["payload_hash"]
        identity_error = self._identity_error(event)
        if identity_error:
            status = "stale" if identity_error.startswith("event.stale") else "rejected"
            return self._record(event, status, identity_error, False)
        if event["offset_ms"] < self.now_ms:
            return self._record(event, "stale", "event.non_monotonic_offset", False)

        self.advance_to(event["offset_ms"])

        if event["event_type"] in RUNTIME_EVENT_TYPES:
            return self._record(event, "rejected", "event.runtime_owned", False)
        if event["segment_id"] is not None:
            segment_state = self.segments[event["segment_id"]]
            if segment_state.terminal:
                return self._record(event, "stale", "event.stale_segment_terminal", False)
        if self.lesson_terminal and event["event_type"] != "lesson_open":
            return self._record(event, "stale", "event.stale_lesson_terminal", False)

        handler = getattr(self, f"_on_{event['event_type']}", None)
        if handler is None:
            return self._record(event, "rejected", "event.unsupported", False)
        code = handler(event)
        if code:
            status = "stale" if code.startswith("event.stale") else "rejected"
            return self._record(event, status, code, False)
        return self._record(event, "accepted", None, True)

    def _identity_error(self, event: dict[str, Any]) -> str | None:
        if event["session_id"] != self.manifest["session_id"]:
            return "event.cross_session"
        if event["lesson_id"] != self.manifest["lesson_id"]:
            return "event.cross_lesson"
        if event["manifest_version"] != self.manifest["manifest_version"]:
            return "event.stale_manifest_version"
        if event["manifest_hash"] != self.manifest["manifest_hash"]:
            return "event.manifest_hash_mismatch"

        segment_id = event["segment_id"]
        if segment_id is None:
            if event["segment_version"] is not None or event["ordinal"] is not None:
                return "event.lesson_identity_malformed"
            return None
        state = self.segments.get(segment_id)
        if state is None:
            return "event.unknown_segment"
        descriptor = state.descriptor
        if event["segment_version"] != descriptor["segment_version"]:
            return "event.stale_segment_version"
        if event["ordinal"] != descriptor["ordinal"]:
            return "event.segment_ordinal_mismatch"
        return None

    def _on_lesson_open(self, event: dict[str, Any]) -> str | None:
        if event["segment_id"] is not None:
            return "event.lesson_event_has_segment"
        if self.opened:
            return "event.invalid_transition"
        self.opened = True
        self.result.milestones.setdefault("question_confirmed", event["offset_ms"])
        return None

    def _on_manifest_ready(self, event: dict[str, Any]) -> str | None:
        if event["segment_id"] is not None:
            return "event.lesson_event_has_segment"
        if not self.opened or self.manifest_ready:
            return "event.invalid_transition"
        self.manifest_ready = True
        self.result.milestones.setdefault("manifest_ready", event["offset_ms"])
        return None

    def _segment_for_readiness(self, event: dict[str, Any]) -> tuple[SegmentState | None, str | None]:
        if not self.manifest_ready:
            return None, "event.manifest_not_ready"
        if event["segment_id"] is None:
            return None, "event.segment_required"
        state = self.segments[event["segment_id"]]
        if state.terminal:
            return None, "event.stale_segment_terminal"
        return state, None

    @staticmethod
    def _mark_first_readiness(state: SegmentState, offset_ms: int) -> None:
        if state.first_readiness_offset_ms is None:
            state.first_readiness_offset_ms = offset_ms

    def _on_segment_ready(self, event: dict[str, Any]) -> str | None:
        state, error = self._segment_for_readiness(event)
        if error:
            return error
        assert state is not None
        expected_hash = self.envelopes[event["segment_id"]]["envelope_hash"]
        if event["payload"].get("envelope_hash") != expected_hash:
            return "event.envelope_hash_mismatch"
        self._mark_first_readiness(state, event["offset_ms"])
        state.envelope_ready = True
        if state.descriptor["ordinal"] == 0:
            self.result.milestones.setdefault("first_segment_ready", event["offset_ms"])
            self.result.milestones.setdefault("first_meaningful_content", event["offset_ms"])
        self._try_playable(state, event["offset_ms"])
        return None

    def _on_visual_ready(self, event: dict[str, Any]) -> str | None:
        state, error = self._segment_for_readiness(event)
        if error:
            return error
        assert state is not None
        if not event["payload"].get("artifact_hash", "").startswith("sha256:"):
            return "event.visual_artifact_missing"
        self._mark_first_readiness(state, event["offset_ms"])
        state.visual_ready = True
        if state.descriptor["ordinal"] == 0:
            self.result.milestones.setdefault("first_visual_ready", event["offset_ms"])
        self._try_playable(state, event["offset_ms"])
        return None

    def _on_audio_ready(self, event: dict[str, Any]) -> str | None:
        state, error = self._segment_for_readiness(event)
        if error:
            return error
        assert state is not None
        if not event["payload"].get("artifact_hash", "").startswith("sha256:"):
            return "event.audio_artifact_missing"
        self._mark_first_readiness(state, event["offset_ms"])
        state.audio_ready = True
        if state.descriptor["ordinal"] == 0:
            self.result.milestones.setdefault("first_audio_ready", event["offset_ms"])
        self._try_playable(state, event["offset_ms"])
        return None

    def _on_segment_admitted(self, event: dict[str, Any]) -> str | None:
        state, error = self._segment_for_readiness(event)
        if error:
            return error
        assert state is not None
        admitted = event["payload"].get("admitted")
        if not isinstance(admitted, bool):
            return "event.admission_result_missing"
        self._mark_first_readiness(state, event["offset_ms"])
        state.admission_received = True
        state.admitted = admitted
        state.cache_write_requested = event["cache_status"] == "write"
        if not admitted:
            self._fallback_segment(state, event["offset_ms"], "segment.admission_failed")
            return None
        self._try_playable(state, event["offset_ms"])
        return None

    def _on_segment_started(self, event: dict[str, Any]) -> str | None:
        if event["segment_id"] is None:
            return "event.segment_required"
        state = self.segments[event["segment_id"]]
        if state.terminal:
            return "event.stale_segment_terminal"
        if not state.playable or state.started:
            return "event.invalid_transition"
        next_segment = next(
            (self.segments[item] for item in self.ordered_segment_ids if not self.segments[item].terminal),
            None,
        )
        if next_segment is not state:
            return "event.playback_out_of_order"
        state.started = True
        if state.descriptor["ordinal"] == 0:
            self.result.milestones.setdefault("interactive_ready", event["offset_ms"])
        return None

    def _on_segment_completed(self, event: dict[str, Any]) -> str | None:
        if event["segment_id"] is None:
            return "event.segment_required"
        state = self.segments[event["segment_id"]]
        if state.terminal:
            return "event.stale_segment_terminal"
        if not state.started:
            return "event.invalid_transition"
        state.terminal = "completed"
        self._maybe_complete_lesson(event["offset_ms"])
        return None

    def _on_cancelled(self, event: dict[str, Any]) -> str | None:
        scope = event["payload"].get("scope")
        if scope == "lesson":
            if event["segment_id"] is not None:
                return "event.lesson_event_has_segment"
            for state in self.segments.values():
                if not state.terminal:
                    state.terminal = "cancelled"
            self.result.valid_cache_entries.clear()
            self.lesson_terminal = "cancelled"
            return None
        if scope == "segment" and event["segment_id"] is not None:
            state = self.segments[event["segment_id"]]
            if state.terminal:
                return "event.stale_segment_terminal"
            state.terminal = "cancelled"
            self.result.valid_cache_entries.discard(state.descriptor["segment_id"])
            self._maybe_complete_lesson(event["offset_ms"])
            return None
        return "event.cancel_scope_invalid"

    def _try_playable(self, state: SegmentState, offset_ms: int) -> None:
        if state.playable or state.terminal:
            return
        if state.envelope_ready and state.visual_ready and state.audio_ready and state.admission_received:
            if not state.admitted:
                return
            state.playable = True
            state.playable_offset_ms = offset_ms
            segment_id = state.descriptor["segment_id"]
            self._emit("segment_playable", state.descriptor, offset_ms, {"join": "all_ready"})
            if state.cache_write_requested:
                self.result.valid_cache_entries.add(segment_id)
            if state.descriptor["ordinal"] == 0:
                self.result.milestones.setdefault("first_segment_playable", offset_ms)

    def _fallback_segment(self, state: SegmentState, offset_ms: int, reason: str) -> None:
        if state.terminal:
            return
        state.terminal = "fallback"
        state.cache_write_requested = False
        self.result.valid_cache_entries.discard(state.descriptor["segment_id"])
        self._emit("fallback", state.descriptor, offset_ms, {"reason": reason})
        self.result.milestones.setdefault("fallback_ready", offset_ms)
        self._maybe_complete_lesson(offset_ms)

    def _maybe_complete_lesson(self, offset_ms: int) -> None:
        if self.lesson_terminal:
            return
        if all(state.terminal in TERMINAL_SEGMENT_STATES for state in self.segments.values()):
            terminals = {state.terminal for state in self.segments.values()}
            self.lesson_terminal = "completed" if terminals == {"completed"} else "degraded"
            self._emit("lesson_complete", None, offset_ms, {"outcome": self.lesson_terminal})

    def _emit(
        self,
        event_type: str,
        segment: dict[str, Any] | None,
        offset_ms: int,
        payload: dict[str, Any],
    ) -> None:
        event = make_event(
            event_id=f"derived-{len(self.result.derived_events) + 1:04d}",
            trace_id=self.trace_id,
            event_type=event_type,
            manifest=self.manifest,
            offset_ms=offset_ms,
            segment=segment,
            payload=payload,
        )
        errors = validate(event, self.schemas["event"])
        if errors:
            raise AssertionError(f"Runtime emitted invalid event: {errors}")
        self.result.derived_events.append(event)

    def _record(
        self,
        event: dict[str, Any],
        status: str,
        code: str | None,
        mutated: bool,
    ) -> dict[str, Any]:
        record = {
            "event_id": event.get("event_id"),
            "event_type": event.get("event_type"),
            "offset_ms": event.get("offset_ms"),
            "status": status,
            "code": code,
            "state_mutated": mutated,
        }
        self.result.records.append(record)
        return record

    def snapshot(self) -> dict[str, Any]:
        starts = [
            state.descriptor["segment_id"]
            for state in self.segments.values()
            if state.started
        ]
        return {
            "lesson_terminal": self.lesson_terminal,
            "segments": {
                segment_id: {
                    "playable": state.playable,
                    "started": state.started,
                    "terminal": state.terminal,
                }
                for segment_id, state in self.segments.items()
            },
            "started_segments": starts,
            "valid_cache_entries": sorted(self.result.valid_cache_entries),
            "milestones": dict(sorted(self.result.milestones.items())),
        }


def max_concurrency(spans: list[dict[str, Any]]) -> int:
    points: list[tuple[int, int]] = []
    for span in spans:
        points.append((span["started_offset_ms"], 1))
        points.append((span["ended_offset_ms"], -1))
    active = 0
    peak = 0
    for _, delta in sorted(points, key=lambda item: (item[0], item[1])):
        active += delta
        peak = max(peak, active)
    return peak


def critical_path_ms(spans: list[dict[str, Any]]) -> int:
    if not spans:
        return 0
    return max(item["ended_offset_ms"] for item in spans) - min(
        item["started_offset_ms"] for item in spans
    )


def summed_work_ms(spans: list[dict[str, Any]]) -> int:
    return sum(item["ended_offset_ms"] - item["started_offset_ms"] for item in spans)
