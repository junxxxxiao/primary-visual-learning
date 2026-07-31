from __future__ import annotations

import importlib.util
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent.parent


def load_schema_validator():
    path = REPO / "spikes" / "ts-03-progressive-lesson-plan" / "src" / "schema_validation.py"
    spec = importlib.util.spec_from_file_location("ts04c_v3_schema_validation", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SCHEMA_VALIDATION = load_schema_validator()
CODE_LIKE = re.compile(r"<\s*(script|style|svg)|javascript:|\b(document|window)\s*\.|=>|\bfunction\s*\(", re.IGNORECASE)


def centered_bounds(
    node: dict[str, Any], geometry: dict[str, Any] | None = None, *, force_diagonal: bool = False
) -> tuple[float, float, float, float]:
    """Return the v0.3 center-anchored box used by the trusted renderer."""
    geometry = geometry or node.get("geometry", {})
    if geometry.get("points"):
        xs = [point["x"] for point in geometry["points"]]
        ys = [point["y"] for point in geometry["points"]]
        return min(xs), min(ys), max(xs), max(ys)
    width = geometry.get("width") or (geometry.get("radius", 0) * 2) or (160 if node.get("type") in {"text", "formula"} else 40)
    height = geometry.get("height") or (geometry.get("radius", 0) * 2) or (50 if node.get("type") in {"text", "formula"} else 40)
    scale = geometry.get("scale", 1)
    width *= scale
    height *= scale
    if force_diagonal or geometry.get("rotation_deg", 0) % 180:
        # The diagonal square is conservative for every intermediate rotation.
        diagonal = (width * width + height * height) ** 0.5
        width = height = diagonal
    x = geometry.get("x", 500)
    y = geometry.get("y", 500)
    return x - width / 2, y - height / 2, x + width / 2, y + height / 2


def within_coordinate_space(bounds: tuple[float, float, float, float]) -> bool:
    left, top, right, bottom = bounds
    return left >= 0 and top >= 0 and right <= 1000 and bottom <= 1000


def geometry_violations(candidate: dict[str, Any]) -> list[str]:
    """Reject v0.3 scenes whose initial or transformed envelope leaves the canvas."""
    if candidate.get("schema_version") not in {"open-visual-scene/0.3", "open-visual-scene/0.4"}:
        return []
    nodes = {node.get("id"): node for node in candidate.get("scene", {}).get("nodes", []) if node.get("id")}
    current = {node_id: deepcopy(node.get("geometry", {})) for node_id, node in nodes.items()}
    violations: list[str] = []
    for node_id, node in nodes.items():
        if not within_coordinate_space(centered_bounds(node, current[node_id])):
            violations.append(f"scene.geometry_out_of_bounds:{node_id}")
    for beat in candidate.get("timeline", {}).get("beats", []):
        beat_id = beat.get("id", "unknown")
        for action in sorted(beat.get("actions", []), key=lambda item: item.get("start_ms", 0)):
            if action.get("type") not in {"move", "scale", "rotate", "morph"}:
                continue
            for node_id in action.get("target_ids", []):
                node = nodes.get(node_id)
                if not node:
                    continue
                if current[node_id].get("points"):
                    violations.append(f"timeline.point_transform_undefined:{beat_id}:{node_id}")
                    continue
                start = deepcopy(current[node_id])
                end = deepcopy(start)
                end.update(action.get("to") or {})
                rotates_during_action = end.get("rotation_deg", 0) != start.get("rotation_deg", 0)
                start_bounds = centered_bounds(node, start, force_diagonal=rotates_during_action)
                end_bounds = centered_bounds(node, end, force_diagonal=rotates_during_action)
                envelope = (
                    min(start_bounds[0], end_bounds[0]), min(start_bounds[1], end_bounds[1]),
                    max(start_bounds[2], end_bounds[2]), max(start_bounds[3], end_bounds[3]),
                )
                if not within_coordinate_space(envelope):
                    violations.append(f"timeline.motion_envelope_out_of_bounds:{beat_id}:{node_id}")
                current[node_id] = end
    return violations


def strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def gate_candidate(candidate: dict[str, Any], sample: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    violations = [f"schema:{error}" for error in SCHEMA_VALIDATION.validate(candidate, schema)]
    expected_facts = {claim["claim_id"] for claim in sample["claims"]}
    candidate_facts = set(candidate.get("fact_refs", []))

    if candidate.get("sample_id") != sample.get("sample_id"):
        violations.append("binding.sample_id_mismatch")
    if candidate_facts != expected_facts:
        violations.append("binding.fact_refs_mismatch")
    if any(CODE_LIKE.search(value) for value in strings(candidate)):
        violations.append("safety.code_like_content")
    violations.extend(geometry_violations(candidate))

    nodes = candidate.get("scene", {}).get("nodes", [])
    node_ids = [node.get("id") for node in nodes if node.get("id")]
    known_nodes = set(node_ids)
    if len(node_ids) != len(known_nodes):
        violations.append("scene.duplicate_node_id")
    for node in nodes:
        parent_id = node.get("parent_id")
        if parent_id and parent_id not in known_nodes:
            violations.append(f"scene.unknown_parent:{node.get('id', 'unknown')}")
        node_id = node.get("id", "unknown")
        shape_kind = node.get("shape_kind")
        marker_end = node.get("marker_end")
        geometry = node.get("geometry", {})
        vertices = geometry.get("vertices")
        if shape_kind and node.get("type") != "shape":
            violations.append(f"scene.shape_kind_wrong_type:{node_id}")
        if marker_end and node.get("type") not in {"line", "plot"}:
            violations.append(f"scene.marker_wrong_type:{node_id}")
        if shape_kind == "polygon" and not vertices:
            violations.append(f"scene.polygon_missing_vertices:{node_id}")
        if vertices:
            if node.get("type") != "shape" or shape_kind != "polygon":
                violations.append(f"scene.vertices_wrong_type:{node_id}")
            if not all(key in geometry for key in ("x", "y", "width", "height")):
                violations.append(f"scene.vertices_missing_box:{node_id}")

    covered_facts: set[str] = set()
    for beat in candidate.get("timeline", {}).get("beats", []):
        beat_id = beat.get("id", "unknown")
        beat_facts = set(beat.get("fact_refs", []))
        covered_facts.update(beat_facts)
        if not beat_facts or not beat_facts.issubset(expected_facts):
            violations.append(f"timeline.invalid_fact_ref:{beat_id}")
        duration = beat.get("duration_ms", 0)
        for action in beat.get("actions", []):
            if not set(action.get("target_ids", [])).issubset(known_nodes):
                violations.append(f"timeline.unknown_target:{beat_id}")
            if action.get("start_ms", 0) + action.get("duration_ms", 0) > duration:
                violations.append(f"timeline.action_out_of_beat:{beat_id}")
    if covered_facts != expected_facts:
        violations.append("timeline.fact_coverage")

    fallback_facts = set(candidate.get("static_fallback", {}).get("fact_refs", []))
    if fallback_facts != expected_facts:
        violations.append("fallback.fact_refs_mismatch")

    interaction_targets = set(candidate.get("interaction", {}).get("target_ids", []))
    if not interaction_targets.issubset(known_nodes):
        violations.append("interaction.unknown_target")

    if candidate.get("schema_version") == "open-visual-scene/0.4":
        beat_ids = {beat.get("id") for beat in candidate.get("timeline", {}).get("beats", [])}
        expected_aspects = set(sample.get("required_explanation_aspects", []))
        bindings = candidate.get("aspect_bindings", [])
        bound_aspects = {binding.get("aspect") for binding in bindings}
        if expected_aspects and bound_aspects != expected_aspects:
            violations.append("binding.aspect_coverage_mismatch")
        for binding in bindings:
            if not set(binding.get("node_ids", [])).issubset(known_nodes):
                violations.append(f"binding.aspect_unknown_node:{binding.get('aspect', 'unknown')}")
            if not set(binding.get("beat_ids", [])).issubset(beat_ids):
                violations.append(f"binding.aspect_unknown_beat:{binding.get('aspect', 'unknown')}")

    return sorted(set(violations))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
