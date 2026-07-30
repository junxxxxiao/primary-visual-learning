from __future__ import annotations

from typing import Any

from .schema_validation import validate as validate_schema_instance
from .validator import validate_explanation_claim_support, violation


def validate_first_segment(
    output: dict[str, Any],
    fixture: dict[str, Any],
    schema: dict[str, Any],
    generation_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    violations = [
        violation("SCHEMA_INVALID", "$", error)
        for error in validate_schema_instance(output, schema)
    ]
    if violations:
        return {"result": "fail", "violations": violations}

    if output["fixture_id"] != fixture["fixture_id"]:
        violations.append(violation("FIXTURE_ID_CHANGED", "fixture_id", "must match the supplied fixture"))

    segment = output["segment"]
    claim_ids = {claim["claim_id"] for claim in fixture["knowledge"]["claims"]}
    fact_refs = set(segment["fact_refs"]) | set(segment["static_fallback"]["fact_refs"])
    for fact_id in sorted(fact_refs - claim_ids):
        violations.append(violation("UNSUPPORTED_FACT_REF", "segment.fact_refs", fact_id))

    allowed_prerequisites = set(fixture["stage_rules"]["allowed_prerequisite_refs"])
    for prerequisite in sorted(set(segment["prerequisite_refs"]) - allowed_prerequisites):
        violations.append(violation("UNDECLARED_PREREQUISITE", "segment.prerequisite_refs", prerequisite))

    allowed_terms = set(fixture["stage_rules"]["allowed_terms"])
    for term in sorted(set(segment["visual"]["terms"]) - allowed_terms):
        violations.append(violation("TERM_OUTSIDE_STAGE_RULE", "segment.visual.terms", term))
    if segment["visual"]["formula_symbol_count"] > fixture["stage_rules"]["max_formula_symbols_per_segment"]:
        violations.append(violation("FORMULA_DENSITY_EXCEEDED", "segment.visual.formula_symbol_count", "stage limit exceeded"))
    if segment["visual"]["element_count"] > fixture["stage_rules"]["max_visual_elements"]:
        violations.append(violation("VISUAL_DENSITY_EXCEEDED", "segment.visual.element_count", "stage limit exceeded"))

    cue_times = [cue["at_ms"] for cue in segment["cues"]]
    if cue_times != sorted(cue_times):
        violations.append(violation("CUE_ORDER_INVALID", "segment.cues", "cue times must be nondecreasing"))
    action_times = {cue["action"]: cue["at_ms"] for cue in segment["cues"]}
    if action_times.get("show_start_frame") != 0:
        violations.append(violation("START_FRAME_MISSING", "segment.cues", "start frame must appear at 0ms"))
    for action in ("start_narration", "start_visual"):
        if action_times.get(action, -1) < 1000:
            violations.append(violation("START_HOLD_TOO_SHORT", "segment.cues", f"{action} must wait at least 1000ms"))

    claims_by_id = {claim["claim_id"]: claim for claim in fixture["knowledge"]["claims"]}
    prerequisite_term_support = (generation_policy or {}).get("prerequisite_term_support", {})
    violations.extend(
        validate_explanation_claim_support(segment, claims_by_id, prerequisite_term_support, "segment")
    )

    return {"result": "fail" if violations else "pass", "violations": violations}
