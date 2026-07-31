#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

from src.runtime import (  # noqa: E402
    ProgressiveRuntime,
    critical_path_ms,
    envelope_hash,
    event_payload_hash,
    make_event,
    manifest_hash,
    max_concurrency,
    summed_work_ms,
)
from src.schema_validation import validate  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def load_schemas() -> dict[str, dict[str, Any]]:
    return {
        "manifest": load_json(ROOT / "schemas" / "lesson-manifest.schema.json"),
        "envelope": load_json(ROOT / "schemas" / "segment-envelope.schema.json"),
        "event": load_json(ROOT / "schemas" / "segment-event.schema.json"),
        "timing": load_json(REPO_ROOT / "spikes" / "shared" / "schemas" / "stage-timing.schema.json"),
    }


def materialize_protocol(
    base: dict[str, Any], segment_count: int, fixture_kind: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = copy.deepcopy(base["manifest_template"])
    synthetic_kind = (
        "synthetic_gold_fixture"
        if fixture_kind == "gold_fixture"
        else "synthetic_adversarial_fixture"
    )
    manifest["fixture_kind"] = synthetic_kind
    manifest["segments"] = manifest["segments"][:segment_count]
    manifest["manifest_hash"] = ""
    manifest["manifest_hash"] = manifest_hash(manifest)

    defaults = base["envelope_defaults"]
    envelopes: dict[str, dict[str, Any]] = {}
    for descriptor in manifest["segments"]:
        segment_id = descriptor["segment_id"]
        envelope = {
            **copy.deepcopy(defaults),
            "fixture_kind": synthetic_kind,
            "session_id": manifest["session_id"],
            "lesson_id": manifest["lesson_id"],
            "manifest_version": manifest["manifest_version"],
            "manifest_hash": manifest["manifest_hash"],
            "segment_id": segment_id,
            "segment_version": descriptor["segment_version"],
            "ordinal": descriptor["ordinal"],
            "depends_on": descriptor["depends_on"],
            "knowledge_package_hash": manifest["knowledge_package_hash"],
            "visual_artifact_ref": f"synthetic://visual/{segment_id}",
            "audio_artifact_ref": f"synthetic://audio/{segment_id}",
            "admission_result_ref": f"synthetic://admission/{segment_id}",
            "fallback_ref": f"synthetic://fallback/{segment_id}",
            "envelope_hash": "",
        }
        envelope["envelope_hash"] = envelope_hash(envelope)
        envelopes[segment_id] = envelope
    return manifest, envelopes


def default_payload(
    event_type: str,
    segment_id: str | None,
    envelopes: dict[str, dict[str, Any]],
    raw: dict[str, Any],
) -> dict[str, Any]:
    if event_type == "segment_ready" and segment_id:
        return {"envelope_hash": envelopes[segment_id]["envelope_hash"]}
    if event_type == "visual_ready":
        return {"artifact_hash": "sha256:" + "b" * 64}
    if event_type == "audio_ready":
        return {"artifact_hash": "sha256:" + "c" * 64}
    if event_type == "segment_admitted":
        return {"admitted": raw.get("admitted", True)}
    if event_type == "cancelled":
        return {"scope": raw.get("scope", "lesson")}
    return {}


def materialize_events(
    scenario: dict[str, Any],
    manifest: dict[str, Any],
    envelopes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    trace_id = f"ts06a-{scenario['scenario_id']}"
    descriptors = {item["segment_id"]: item for item in manifest["segments"]}
    events: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}

    for index, raw in enumerate(scenario["events"], start=1):
        if "duplicate_of" in raw or "conflicting_duplicate_of" in raw:
            original_id = raw.get("duplicate_of") or raw["conflicting_duplicate_of"]
            event = copy.deepcopy(by_id[original_id])
            event["offset_ms"] = raw["at_ms"]
            if "conflicting_duplicate_of" in raw:
                event["payload"] = {**event["payload"], "conflict": True}
                event["payload_hash"] = event_payload_hash(event)
            events.append(event)
            continue

        event_type = raw["event_type"]
        segment_id = raw.get("segment_id")
        segment = descriptors.get(segment_id) if segment_id else None
        event_id = raw.get("event_id", f"input-{index:04d}")
        event = make_event(
            event_id=event_id,
            trace_id=trace_id,
            event_type=event_type,
            manifest=manifest,
            offset_ms=raw["at_ms"],
            segment=segment,
            payload=default_payload(event_type, segment_id, envelopes, raw),
            cache_status=raw.get("cache_status", "not_applicable"),
        )
        event.update(raw.get("overrides", {}))
        event["payload_hash"] = event_payload_hash(event)
        for field in raw.get("remove_fields", []):
            event.pop(field, None)
        events.append(event)
        by_id[event_id] = event
    return events


def timing_trace(
    scenario: dict[str, Any], runtime: ProgressiveRuntime, events: list[dict[str, Any]]
) -> dict[str, Any]:
    spans: list[dict[str, Any]] = []
    records_by_id: dict[str, list[dict[str, Any]]] = {}
    for record in runtime.result.records:
        records_by_id.setdefault(record["event_id"], []).append(record)

    for index, event in enumerate(events, start=1):
        matching = records_by_id.get(event.get("event_id"), [])
        record = matching.pop(0) if matching else {"status": "rejected", "code": "trace.record_missing"}
        status = record["status"]
        outcome = "success" if status in {"accepted", "duplicate"} else (
            "cancelled" if status == "stale" else "failure"
        )
        offset = event.get("offset_ms", 0)
        spans.append(
            {
                "span_id": f"input-{index:04d}",
                "parent_span_id": None,
                "stage": f"event.{event.get('event_type', 'invalid')}",
                "started_offset_ms": offset,
                "ended_offset_ms": offset,
                "duration_ms": 0,
                "latency_scope": "system_work",
                "outcome": outcome,
                "retry_index": event.get("attempt", 0),
                "cache_status": event.get("cache_status", "not_applicable"),
                "provider": None,
                "model": None,
                "input_units": None,
                "output_units": None,
                "cost_amount": 0,
                "cost_currency": "CNY",
                "error_code": record.get("code"),
            }
        )

    next_index = len(spans) + 1
    for work in scenario["work_spans"]:
        spans.append(
            {
                "span_id": f"work-{next_index:04d}",
                "parent_span_id": None,
                "stage": work["stage"],
                "started_offset_ms": work["started_offset_ms"],
                "ended_offset_ms": work["ended_offset_ms"],
                "duration_ms": work["ended_offset_ms"] - work["started_offset_ms"],
                "latency_scope": "system_work",
                "outcome": "success",
                "retry_index": 0,
                "cache_status": "not_applicable",
                "provider": None,
                "model": None,
                "input_units": None,
                "output_units": None,
                "cost_amount": 0,
                "cost_currency": "CNY",
                "error_code": None,
            }
        )
        next_index += 1

    milestones = [
        {"name": name, "offset_ms": offset, "latency_scope": "user_wait_anchor" if name == "question_confirmed" else "system_output"}
        for name, offset in sorted(runtime.result.milestones.items(), key=lambda item: (item[1], item[0]))
    ]
    return {
        "schema_version": "stage-timing/1.0",
        "trace_id": runtime.trace_id,
        "slice_id": "TS-06A",
        "clock": "monotonic",
        "trace_started_at": "2026-07-31T00:00:00Z",
        "milestones": milestones,
        "spans": spans,
    }


def evaluate_scenario(
    scenario: dict[str, Any], base: dict[str, Any], schemas: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    manifest, envelopes = materialize_protocol(
        base, scenario.get("segment_count", 2), scenario["fixture_kind"]
    )
    events = materialize_events(scenario, manifest, envelopes)
    runtime = ProgressiveRuntime(
        manifest,
        envelopes,
        schemas,
        trace_id=f"ts06a-{scenario['scenario_id']}",
    )
    for event in events:
        runtime.process(event)
    runtime.advance_to(scenario["final_offset_ms"])

    snapshot = runtime.snapshot()
    trace = timing_trace(scenario, runtime, events)
    trace_errors = validate(trace, schemas["timing"])
    expected = scenario["expected"]
    codes = {record["code"] for record in runtime.result.records if record["code"]}
    derived_types = Counter(event["event_type"] for event in runtime.result.derived_events)
    work_spans = scenario["work_spans"]
    actual_concurrency = max_concurrency(work_spans)
    actual_critical_path = critical_path_ms(work_spans)
    actual_work_sum = summed_work_ms(work_spans)

    checks = {
        "lesson_terminal": snapshot["lesson_terminal"] == expected["lesson_terminal"],
        "started_segments": snapshot["started_segments"] == expected["started_segments"],
        "valid_cache_entries": snapshot["valid_cache_entries"] == expected["valid_cache_entries"],
        "required_codes": set(expected["required_codes"]).issubset(codes),
        "derived_event_schemas": all(not validate(event, schemas["event"]) for event in runtime.result.derived_events),
        "timing_schema": not trace_errors,
        "max_concurrency": actual_concurrency == expected["max_concurrency"],
    }
    if "first_segment_playable_ms" in expected:
        checks["first_segment_playable_ms"] = (
            snapshot["milestones"].get("first_segment_playable")
            == expected["first_segment_playable_ms"]
        )
    if "fallback_ready_ms" in expected:
        checks["fallback_ready_ms"] = (
            snapshot["milestones"].get("fallback_ready") == expected["fallback_ready_ms"]
        )
    if "fallback_count" in expected:
        checks["fallback_count"] = derived_types["fallback"] == expected["fallback_count"]
    if "work_critical_path_ms" in expected:
        checks["work_critical_path_ms"] = actual_critical_path == expected["work_critical_path_ms"]
    if expected.get("work_sum_exceeds_critical_path"):
        checks["work_sum_exceeds_critical_path"] = actual_work_sum > actual_critical_path

    return {
        "scenario_id": scenario["scenario_id"],
        "fixture_kind": scenario["fixture_kind"],
        "mode": scenario["mode"],
        "pass": all(checks.values()),
        "checks": checks,
        "snapshot": snapshot,
        "record_counts": dict(sorted(Counter(item["status"] for item in runtime.result.records).items())),
        "observed_codes": sorted(codes),
        "derived_event_counts": dict(sorted(derived_types.items())),
        "work_metrics": {
            "max_concurrency": actual_concurrency,
            "critical_path_ms": actual_critical_path,
            "summed_work_ms": actual_work_sum,
        },
        "trace_errors": trace_errors,
        "trace": trace,
        "records": runtime.result.records,
        "derived_events": runtime.result.derived_events,
    }


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> int:
    base = load_json(ROOT / "fixtures" / "base-protocol.json")
    scenarios = load_json(ROOT / "fixtures" / "scenarios.json")
    schemas = load_schemas()
    results = [evaluate_scenario(item, base, schemas) for item in scenarios["scenarios"]]

    gold = [item for item in results if item["fixture_kind"] == "gold_fixture"]
    adversarial = [item for item in results if item["fixture_kind"] == "adversarial_fixture"]
    all_pass = all(item["pass"] for item in results)
    head_contains_baseline = subprocess.run(
        ["git", "merge-base", "--is-ancestor", "origin/main", "HEAD"],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    summary = {
        "schema_version": "ts-06a-summary/1.0",
        "slice_id": "TS-06A",
        "status": "harness_ready" if all_pass else "fail",
        "pass": all_pass,
        "evidence_class": "offline_harness_only",
        "baseline_sha": git_value("rev-parse", "origin/main"),
        "head_contains_baseline": head_contains_baseline,
        "fixture_versions": [base["fixture_version"], scenarios["fixture_version"]],
        "contract_versions": [
            "lesson-manifest/1.0",
            "segment-envelope/1.0",
            "segment-event/1.0",
            "stage-timing/1.0"
        ],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "external_services": False,
            "virtual_clock": True
        },
        "scenario_count": len(results),
        "passed_scenario_count": sum(item["pass"] for item in results),
        "gold_fixture_count": len(gold),
        "gold_fixture_pass_count": sum(item["pass"] for item in gold),
        "adversarial_fixture_count": len(adversarial),
        "adversarial_fixture_pass_count": sum(item["pass"] for item in adversarial),
        "thresholds": {
            "valid_gold_terminal_rate": {"actual": rate(gold), "target": 1.0},
            "known_adversarial_detection_rate": {"actual": rate(adversarial), "target": 1.0},
            "cross_session_or_stale_cache_pollution_count": {"actual": cache_pollution_count(results), "target": 0},
            "invalid_trace_count": {"actual": sum(bool(item["trace_errors"]) for item in results), "target": 0},
            "failed_scenario_count": {"actual": sum(not item["pass"] for item in results), "target": 0}
        },
        "scenario_results": [
            {
                "scenario_id": item["scenario_id"],
                "fixture_kind": item["fixture_kind"],
                "mode": item["mode"],
                "pass": item["pass"],
                "checks": item["checks"],
                "record_counts": item["record_counts"],
                "observed_codes": item["observed_codes"],
                "work_metrics": item["work_metrics"]
            }
            for item in results
        ],
        "cost": {"currency": "CNY", "amount": 0, "external_services": False},
        "candidate": {
            "provider": None,
            "model_or_service": None,
            "parameters": None,
            "requests": 0,
            "tokens_or_equivalent": 0,
            "candidate_output_count": 0
        },
        "verified": [
            "deterministic protocol validation and identity isolation",
            "virtual-time readiness join and manifest-order playback",
            "duplicate, stale, cancellation, timeout and fallback handling",
            "critical-path wall-clock calculation for overlapping synthetic spans"
        ],
        "unverified": [
            "real model or TTS latency, quality, streaming behavior and cost",
            "real visual generation, sandbox, layout admission and rendering",
            "real media timeline synchronization, pause, resume and seek",
            "browser, device, network, concurrency and production reliability"
        ]
    }
    write_json(ROOT / "results" / "audit.json", {"scenario_results": results})
    write_json(ROOT / "results" / "summary.json", summary)
    print(
        f"TS-06A: {summary['passed_scenario_count']}/{summary['scenario_count']} scenarios; "
        f"status={summary['status']}"
    )
    return 0 if all_pass else 1


def rate(items: list[dict[str, Any]]) -> float:
    return sum(item["pass"] for item in items) / len(items) if items else 0.0


def cache_pollution_count(results: list[dict[str, Any]]) -> int:
    isolated = {
        "adversarial-cross-session",
        "adversarial-cancel-late-response",
        "adversarial-cancel-after-admission",
        "adversarial-missing-audio-timeout",
        "adversarial-hard-deadline"
    }
    return sum(
        len(item["snapshot"]["valid_cache_entries"])
        for item in results
        if item["scenario_id"] in isolated
    )


if __name__ == "__main__":
    raise SystemExit(main())
