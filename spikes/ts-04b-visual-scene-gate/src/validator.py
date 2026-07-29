from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any


REQUIRED_STATE_KINDS = {
    "initial",
    "key_process",
    "final",
    "paused",
    "resumed",
    "post_interaction",
    "reduced_motion",
    "static_fallback",
}

CACHE_IDENTITY_FIELDS = (
    "learning_goal",
    "knowledge_version",
    "teaching_contract_version",
    "layout_contract_version",
    "scene_version",
    "viewport",
    "code_hash",
    "test_version",
)


def _contains(outer: dict[str, float], inner: dict[str, float]) -> bool:
    return (
        inner["x"] >= outer["x"]
        and inner["y"] >= outer["y"]
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"]
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"]
    )


def _violation(
    code: str,
    target: str,
    message: str,
    actual: Any,
    expected: Any,
) -> dict[str, Any]:
    return {
        "code": code,
        "target": target,
        "message": message,
        "actual": actual,
        "expected": expected,
    }


def validate_scene_structure(scene: dict[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    required = {
        "schema_version",
        "scene_id",
        "scene_version",
        "learning_goal",
        "knowledge_version",
        "teaching_contract_version",
        "layout_contract_version",
        "code_hash",
        "test_version",
        "teaching",
        "viewport_profiles",
    }
    missing = sorted(required - scene.keys())
    if missing:
        violations.append(
            _violation("scene.missing_fields", "scene", "Required fields are missing", missing, sorted(required))
        )
        return violations

    if scene["schema_version"] != "visual-scene/1.0":
        violations.append(
            _violation(
                "scene.schema_version",
                "scene.schema_version",
                "Unsupported scene schema version",
                scene["schema_version"],
                "visual-scene/1.0",
            )
        )
    if scene["layout_contract_version"] != "visual-layout/v1":
        violations.append(
            _violation(
                "scene.layout_contract_version",
                "scene.layout_contract_version",
                "Unsupported layout contract version",
                scene["layout_contract_version"],
                "visual-layout/v1",
            )
        )
    if not scene["code_hash"].startswith("sha256:") or len(scene["code_hash"]) != 71:
        violations.append(
            _violation(
                "scene.code_hash",
                "scene.code_hash",
                "Code hash must be a SHA-256 identity",
                scene["code_hash"],
                "sha256:<64 lowercase hex characters>",
            )
        )

    profiles = scene.get("viewport_profiles", {})
    if set(profiles) != {"phone", "tablet"}:
        violations.append(
            _violation(
                "scene.viewport_profiles",
                "scene.viewport_profiles",
                "Both and only phone and tablet profiles are required",
                sorted(profiles),
                ["phone", "tablet"],
            )
        )
        return violations

    if profiles["phone"].get("layout_mode") == profiles["tablet"].get("layout_mode"):
        violations.append(
            _violation(
                "layout.responsive_reflow",
                "viewport_profiles",
                "Phone and tablet must declare independently organized layouts",
                profiles["phone"].get("layout_mode"),
                "distinct layout_mode values",
            )
        )

    for viewport, profile in profiles.items():
        kinds = {state.get("kind") for state in profile.get("states", [])}
        missing_kinds = sorted(REQUIRED_STATE_KINDS - kinds)
        if missing_kinds:
            violations.append(
                _violation(
                    "layout.missing_states",
                    f"viewport_profiles.{viewport}.states",
                    "Required validation states are missing",
                    missing_kinds,
                    sorted(REQUIRED_STATE_KINDS),
                )
            )
    return violations


def validate_teaching(scene: dict[str, Any]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    teaching = scene["teaching"]
    if teaching["status"] != "ready":
        violations.append(
            _violation(
                f"teaching.{teaching['status']}",
                "teaching.status",
                "Teaching validation must complete unambiguously before admission",
                teaching["status"],
                "ready",
            )
        )

    for fact in teaching["facts"]:
        expected = fact["expected"]
        for modality in ("visual", "narration"):
            if fact[modality] != expected:
                violations.append(
                    _violation(
                        "teaching.fact_mismatch",
                        f"teaching.facts.{fact['fact_id']}.{modality}",
                        "Rendered or narrated claim contradicts the controlled fact",
                        fact[modality],
                        expected,
                    )
                )
        if fact["visual"] != fact["narration"]:
            violations.append(
                _violation(
                    "teaching.modality_mismatch",
                    f"teaching.facts.{fact['fact_id']}",
                    "Visual and narration cues disagree",
                    {"visual": fact["visual"], "narration": fact["narration"]},
                    {"visual": expected, "narration": expected},
                )
            )

    return {"result": "fail" if violations else "pass", "violations": violations}


def validate_visual_scene(
    scene: dict[str, Any], viewport: str, state_id: str
) -> dict[str, Any]:
    profile = scene["viewport_profiles"][viewport]
    state = next(state for state in profile["states"] if state["state_id"] == state_id)
    canvas = profile["canvas_inner_bounds"]
    limits = profile["readability_limits"]
    violations: list[dict[str, Any]] = []

    metrics = profile["container_metrics"]
    horizontal_overflow = metrics["scroll_width"] > metrics["client_width"]
    vertical_overflow = metrics["scroll_height"] > metrics["client_height"]
    hidden_overflow = (horizontal_overflow or vertical_overflow) and (
        metrics["overflow"] == "hidden" or metrics["clip"] or metrics["mask"]
    )
    if horizontal_overflow:
        violations.append(
            _violation(
                "layout.horizontal_scroll",
                f"{viewport}.container",
                "Visual canvas must not create horizontal scrolling",
                metrics,
                {"scroll_width": metrics["client_width"]},
            )
        )
    if hidden_overflow:
        violations.append(
            _violation(
                "layout.hidden_clipping",
                f"{viewport}.container",
                "Overflow, clip, or mask cannot conceal content from validation",
                metrics,
                {"overflow": "auto or visible", "clip": False, "mask": False},
            )
        )

    for element in state["elements"]:
        target = f"{viewport}.{state_id}.{element['element_id']}"
        if not _contains(canvas, element["bounds"]):
            violations.append(
                _violation(
                    "layout.element_out_of_bounds",
                    target,
                    "Element exceeds the canvas inner bounds",
                    element["bounds"],
                    canvas,
                )
            )
        local_region_id = element.get("local_safe_region")
        if local_region_id:
            local_region = profile["local_safe_regions"].get(local_region_id)
            if local_region is None or not _contains(local_region, element["bounds"]):
                violations.append(
                    _violation(
                        "layout.local_safe_region",
                        target,
                        "Element exceeds its non-rectangular container safe region",
                        element["bounds"],
                        local_region,
                    )
                )
        if element["font_size"] and element["font_size"] < limits["min_font_size"]:
            violations.append(
                _violation(
                    "layout.unreadable_text",
                    target,
                    "Text is below the viewport minimum readable size",
                    element["font_size"],
                    limits["min_font_size"],
                )
            )
        if element["min_graphic_size"] and element["min_graphic_size"] < limits["min_graphic_size"]:
            violations.append(
                _violation(
                    "layout.unreadable_graphic",
                    target,
                    "Graphic is below the viewport minimum recognizable size",
                    element["min_graphic_size"],
                    limits["min_graphic_size"],
                )
            )
        if element["interactive"] and element["touch_size"] < limits["min_touch_size"]:
            violations.append(
                _violation(
                    "layout.touch_target",
                    target,
                    "Interactive target is below the viewport touch minimum",
                    element["touch_size"],
                    limits["min_touch_size"],
                )
            )

    for envelope in state["motion_envelopes"]:
        if not _contains(canvas, envelope["bounds"]):
            violations.append(
                _violation(
                    "layout.motion_envelope_out_of_bounds",
                    f"{viewport}.{state_id}.{envelope['element_id']}.motion_envelope",
                    "Complete motion trajectory exceeds the canvas inner bounds",
                    envelope["bounds"],
                    canvas,
                )
            )

    return {
        "contract_version": scene["layout_contract_version"],
        "scene_version": scene["scene_version"],
        "viewport": viewport,
        "state": state_id,
        "result": "fail" if violations else "pass",
        "violations": violations,
    }


def cache_identity(scene: dict[str, Any], viewport: str) -> dict[str, str]:
    identity = {field: scene[field] for field in CACHE_IDENTITY_FIELDS if field != "viewport"}
    identity["viewport"] = viewport
    return {field: identity[field] for field in CACHE_IDENTITY_FIELDS}


def cache_key(identity: dict[str, str]) -> str:
    canonical = json.dumps(identity, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class CacheRead:
    status: str
    record: dict[str, Any] | None


class ValidatedSceneCache:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], dict[str, Any]] = {}

    def write(self, scene: dict[str, Any], viewport: str, admitted: bool) -> bool:
        if not admitted:
            return False
        identity = cache_identity(scene, viewport)
        self._records[(scene["scene_id"], viewport)] = {
            "cache_key": cache_key(identity),
            "identity": identity,
            "validation_status": "pass",
            "scene_id": scene["scene_id"],
        }
        return True

    def read(self, scene: dict[str, Any], viewport: str) -> CacheRead:
        slot = (scene["scene_id"], viewport)
        record = self._records.get(slot)
        if record is None:
            return CacheRead("miss", None)
        identity = cache_identity(scene, viewport)
        if record["cache_key"] != cache_key(identity) or record["identity"] != identity:
            del self._records[slot]
            return CacheRead("invalidated", None)
        return CacheRead("hit", copy.deepcopy(record))

    @property
    def size(self) -> int:
        return len(self._records)


def apply_mutations(scene: dict[str, Any], mutations: list[dict[str, Any]]) -> dict[str, Any]:
    mutated = copy.deepcopy(scene)
    for mutation in mutations:
        parts = mutation["path"].split(".")
        cursor: Any = mutated
        for part in parts[:-1]:
            cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
        final = parts[-1]
        if isinstance(cursor, list):
            cursor[int(final)] = mutation["value"]
        else:
            cursor[final] = mutation["value"]
    return mutated


def validate_all_layout_states(scene: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for viewport in ("phone", "tablet"):
        for state in scene["viewport_profiles"][viewport]["states"]:
            results.append(validate_visual_scene(scene, viewport, state["state_id"]))
    return results
