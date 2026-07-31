#!/usr/bin/env python3
"""Validate the offline TS-04C-v3 harness without calling a candidate model."""
from __future__ import annotations

import json
import importlib.util
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures" / "calibration-inputs.json"
SCHEMA = ROOT / "schemas" / "open-visual-scene.schema.json"
SCHEMA_V03 = ROOT / "schemas" / "open-visual-scene-v0.3.schema.json"
SUMMARY = ROOT / "results" / "summary.json"
GATE_CASES = ROOT / "fixtures" / "schema-gate-cases.json"

EXPECTED_TIERS = {
    "unfamiliar_wording_familiar_grammar": 4,
    "familiar_concept_new_composition": 3,
    "unfamiliar_concept_and_representation": 3,
}
EXPECTED_NODE_TYPES = {"group", "shape", "line", "text", "axis", "plot", "formula", "particles"}
EXPECTED_ACTIONS = {"show", "hide", "emphasize", "move", "scale", "rotate", "morph", "trace", "compare", "update_value"}
DEMO_MARKERS = {"primary_sound", "middle_perfect_square", "middle_sound_pair"}


def load_gate():
    path = ROOT / "src" / "gate_candidate.py"
    spec = importlib.util.spec_from_file_location("ts04c_v3_gate", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate() -> list[str]:
    fixture = json.loads(FIXTURES.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    schema_v03 = json.loads(SCHEMA_V03.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    gate_cases = json.loads(GATE_CASES.read_text(encoding="utf-8"))
    gate = load_gate()
    failures: list[str] = []

    samples = fixture.get("samples", [])
    if fixture.get("source_kind") != "synthetic_unverified":
        failures.append("fixtures.source_kind")
    if fixture.get("sample_count") != 10 or len(samples) != 10:
        failures.append("fixtures.sample_count")
    if len({sample.get("sample_id") for sample in samples}) != len(samples):
        failures.append("fixtures.duplicate_sample_id")

    kinds = Counter(sample.get("fixture_kind") for sample in samples)
    if kinds != Counter({"gold_fixture": 8, "adversarial_fixture": 2}):
        failures.append("fixtures.kind_distribution")
    tiers = Counter(sample.get("unfamiliarity_tier") for sample in samples)
    if tiers != Counter(EXPECTED_TIERS):
        failures.append("fixtures.tier_distribution")

    for sample in samples:
        sample_id = sample.get("sample_id", "unknown")
        if any(marker in sample_id for marker in DEMO_MARKERS):
            failures.append(f"fixtures.demo_reuse:{sample_id}")
        if len(sample.get("required_explanation_aspects", [])) < 4:
            failures.append(f"fixtures.explanation_aspects:{sample_id}")
        claims = sample.get("claims", [])
        if not claims or any(claim.get("status") != "synthetic_unverified" for claim in claims):
            failures.append(f"fixtures.claim_status:{sample_id}")

    if schema.get("$id") != "open-visual-scene/0.1":
        failures.append("schema.version")
    timeline = schema.get("properties", {}).get("timeline", {}).get("properties", {})
    if timeline.get("start_hold_ms", {}).get("const") != 1000:
        failures.append("schema.start_hold")
    beats = timeline.get("beats", {})
    if (beats.get("minItems"), beats.get("maxItems")) != (3, 6):
        failures.append("schema.beat_count")

    node_types = set(schema.get("$defs", {}).get("node", {}).get("properties", {}).get("type", {}).get("enum", []))
    if node_types != EXPECTED_NODE_TYPES:
        failures.append("schema.node_types")
    actions = set(schema.get("$defs", {}).get("action", {}).get("properties", {}).get("type", {}).get("enum", []))
    if actions != EXPECTED_ACTIONS:
        failures.append("schema.actions")

    serialized_schema = json.dumps(schema).lower()
    for forbidden in ("javascript", "html", "css", "external_url", "scene_code"):
        if forbidden in serialized_schema:
            failures.append(f"schema.forbidden_field:{forbidden}")

    coordinate_space_v03 = schema_v03.get("properties", {}).get("scene", {}).get("properties", {}).get("coordinate_space", {})
    if schema_v03.get("$id") != "open-visual-scene/0.3":
        failures.append("schema_v03.version")
    if "anchor" not in coordinate_space_v03.get("required", []):
        failures.append("schema_v03.anchor_not_required")
    if coordinate_space_v03.get("properties", {}).get("anchor", {}).get("const") != "center":
        failures.append("schema_v03.anchor_not_center")

    candidate = summary.get("candidate", {})
    if summary.get("status") not in {"candidate_run_complete", "human_review_complete", "conditional_pass", "pass", "fail"} or candidate.get("requests_made") != 63:
        failures.append("summary.evidence_state")
    if candidate.get("provider") != "deepseek_official" or candidate.get("model_or_service_version") != "deepseek-v4-flash":
        failures.append("summary.authorization_gate")
    if candidate.get("data_boundary_confirmed") is not True or candidate.get("budget", {}).get("total_token_limit") != 100000:
        failures.append("summary.data_or_budget_gate")

    source_sample = next(sample for sample in samples if sample["sample_id"] == gate_cases["sample_id"])
    valid_scene = gate_cases["valid_scene"]
    if gate.gate_candidate(valid_scene, source_sample, schema):
        failures.append("gate.valid_scene_rejected")

    invalid = deepcopy(valid_scene)
    invalid["sample_id"] = "wrong.sample"
    if "binding.sample_id_mismatch" not in gate.gate_candidate(invalid, source_sample, schema):
        failures.append("gate.sample_binding_not_enforced")
    invalid = deepcopy(valid_scene)
    invalid["title"] = "<script>window.bad()</script>"
    if "safety.code_like_content" not in gate.gate_candidate(invalid, source_sample, schema):
        failures.append("gate.code_text_not_blocked")
    invalid = deepcopy(valid_scene)
    invalid["timeline"]["beats"][0]["actions"][0]["target_ids"] = ["missing-node"]
    if not any(item.startswith("timeline.unknown_target") for item in gate.gate_candidate(invalid, source_sample, schema)):
        failures.append("gate.unknown_target_not_blocked")
    invalid = deepcopy(valid_scene)
    invalid["timeline"]["beats"] = invalid["timeline"]["beats"][:2]
    if not any("fewer than minItems" in item for item in gate.gate_candidate(invalid, source_sample, schema)):
        failures.append("gate.short_timeline_not_blocked")

    return failures


if __name__ == "__main__":
    problems = validate()
    if problems:
        print(json.dumps({"status": "fail", "violations": problems}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(json.dumps({"status": "pass", "scope": "harness_only", "network_requests": 0}, ensure_ascii=False))
