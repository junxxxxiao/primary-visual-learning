from __future__ import annotations

import copy
from typing import Any

from .schema_validation import validate as validate_schema_instance


def violation(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def schema_violations(plan: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, str]]:
    return [violation("SCHEMA_INVALID", "$", error) for error in validate_schema_instance(plan, schema)]


def segment_visible_texts(segment: dict[str, Any], prefix: str) -> list[tuple[str, str]]:
    texts = [
        (f"{prefix}.goal", segment["goal"]),
        (f"{prefix}.narration", segment["narration"]),
    ]
    texts.extend((f"{prefix}.visual.states[{index}]", value) for index, value in enumerate(segment["visual"]["states"]))
    texts.extend(
        (f"{prefix}.static_fallback.steps[{index}]", value)
        for index, value in enumerate(segment["static_fallback"]["steps"])
    )
    return texts


def validate_explanation_claim_support(
    segment: dict[str, Any],
    claims_by_id: dict[str, dict[str, Any]],
    prerequisite_term_support: dict[str, list[str]],
    prefix: str,
) -> list[dict[str, str]]:
    claim_supported_terms = {
        term
        for fact_id in segment["fact_refs"]
        if fact_id in claims_by_id
        for term in claims_by_id[fact_id].get("supported_terms", [])
    }
    prerequisite_supported_terms = {
        term
        for prerequisite_id in segment["prerequisite_refs"]
        for term in prerequisite_term_support.get(prerequisite_id, [])
    }
    supported_terms = claim_supported_terms | prerequisite_supported_terms
    return [
        violation(
            "EXPLANATION_TERM_UNSUPPORTED",
            f"{prefix}.visual.terms",
            f"term {term!r} is not supported by the segment's cited claims or declared prerequisites",
        )
        for term in segment["visual"]["terms"]
        if term not in supported_terms
    ]


def validate_plan(
    plan: dict[str, Any],
    schema: dict[str, Any],
    expected_context: dict[str, Any] | None = None,
    generation_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    violations = schema_violations(plan, schema)
    if violations:
        return {"result": "fail", "violations": violations}

    if expected_context is not None:
        for field in ("fixture_id", "stage_profile", "stage_rules", "knowledge", "core_relation", "primary_object"):
            if plan[field] != expected_context[field]:
                violations.append(
                    violation(
                        "IMMUTABLE_CONTEXT_CHANGED",
                        field,
                        "generated output must preserve the supplied planning context exactly",
                    )
                )

    segments = plan["segments"]
    expected_order = list(range(1, len(segments) + 1))
    actual_order = [segment["order"] for segment in segments]
    if actual_order != expected_order:
        violations.append(violation("SEGMENT_ORDER_INVALID", "segments", f"expected {expected_order}, got {actual_order}"))
    for index, segment in enumerate(segments):
        if segment["phase"] != "explanation":
            violations.append(violation("EXPLANATION_PHASE_INVALID", f"segments[{index}].phase", "every segment must explain"))

    claims_by_id = {claim["claim_id"]: claim for claim in plan["knowledge"]["claims"]}
    claim_ids = set(claims_by_id)
    allowed_prerequisites = set(plan["stage_rules"]["allowed_prerequisite_refs"])
    allowed_terms = set(plan["stage_rules"]["allowed_terms"])
    max_formula = plan["stage_rules"]["max_formula_symbols_per_segment"]
    max_elements = plan["stage_rules"]["max_visual_elements"]

    for index, segment in enumerate(segments):
        prefix = f"segments[{index}]"
        cue_times = [cue["at_ms"] for cue in segment["cues"]]
        if cue_times != sorted(cue_times):
            violations.append(violation("CUE_ORDER_INVALID", f"{prefix}.cues", "cue times must be nondecreasing"))
        action_times = {cue["action"]: cue["at_ms"] for cue in segment["cues"]}
        if action_times.get("show_start_frame") != 0:
            violations.append(violation("START_FRAME_MISSING", f"{prefix}.cues", "start frame must appear at 0ms"))
        for action in ("start_narration", "start_visual"):
            if action_times.get(action, -1) < 1000:
                violations.append(violation("START_HOLD_TOO_SHORT", f"{prefix}.cues", f"{action} must wait at least 1000ms"))

        unknown_facts = (set(segment["fact_refs"]) | set(segment["static_fallback"]["fact_refs"])) - claim_ids
        for fact_id in sorted(unknown_facts):
            violations.append(violation("UNSUPPORTED_FACT_REF", prefix, f"unknown fact reference {fact_id}"))
        undeclared = set(segment["prerequisite_refs"]) - allowed_prerequisites
        for prerequisite in sorted(undeclared):
            violations.append(violation("UNDECLARED_PREREQUISITE", f"{prefix}.prerequisite_refs", prerequisite))
        disallowed_terms = set(segment["visual"]["terms"]) - allowed_terms
        for term in sorted(disallowed_terms):
            violations.append(violation("TERM_OUTSIDE_STAGE_RULE", f"{prefix}.visual.terms", term))
        if segment["visual"]["formula_symbol_count"] > max_formula:
            violations.append(violation("FORMULA_DENSITY_EXCEEDED", f"{prefix}.visual.formula_symbol_count", f"limit is {max_formula}"))
        if segment["visual"]["element_count"] > max_elements:
            violations.append(violation("VISUAL_DENSITY_EXCEEDED", f"{prefix}.visual.element_count", f"limit is {max_elements}"))
        if not segment["fact_refs"]:
            violations.append(violation("SEGMENT_FACTS_MISSING", f"{prefix}.fact_refs", "each segment must cite at least one verified claim"))
        if segment["phase"] == "explanation":
            prerequisite_term_support = (generation_policy or {}).get("prerequisite_term_support", {})
            violations.extend(validate_explanation_claim_support(segment, claims_by_id, prerequisite_term_support, prefix))

    tasks = plan["transfer"]
    initial = tasks["initial"]
    retry = tasks["retry"]
    if initial["object"] == plan["primary_object"]:
        violations.append(violation("TRANSFER_SKIN_SWAP", "transfer.initial.object", "initial transfer must use a different object"))
    if retry["object"] in {plan["primary_object"], initial["object"]}:
        violations.append(violation("TRANSFER_RETRY_NOT_NEW", "transfer.retry.object", "retry must use a third object"))
    for name, task in tasks.items():
        unknown = set(task["fact_refs"]) - claim_ids
        for fact_id in sorted(unknown):
            violations.append(violation("UNSUPPORTED_TRANSFER_FACT", f"transfer.{name}.fact_refs", fact_id))
        if task["difficulty"] != plan["stage_rules"]["transfer_difficulty"]:
            violations.append(violation("TRANSFER_DIFFICULTY_MISMATCH", f"transfer.{name}.difficulty", "must match the declared stage rule"))
        task_policy = (generation_policy or {}).get("transfer", {}).get(name)
        if task_policy:
            if task["object"] not in task_policy["allowed_objects"]:
                violations.append(violation("TRANSFER_OBJECT_NOT_APPROVED", f"transfer.{name}.object", task["object"]))
            if task["prompt"] != task_policy["approved_prompt"]:
                violations.append(
                    violation(
                        "TRANSFER_PROMPT_NOT_APPROVED",
                        f"transfer.{name}.prompt",
                        "must exactly match the approved transfer prompt",
                    )
                )
            for fragment in task_policy["required_prompt_fragments"]:
                if fragment not in task["prompt"]:
                    violations.append(violation("TRANSFER_REQUIRED_CONTEXT_MISSING", f"transfer.{name}.prompt", fragment))
            for fragment in task_policy["forbidden_prompt_fragments"]:
                if fragment in task["prompt"]:
                    violations.append(violation("TRANSFER_CONTEXT_REUSES_LESSON", f"transfer.{name}.prompt", fragment))
            missing_facts = set(task_policy["required_fact_refs"]) - set(task["fact_refs"])
            for fact_id in sorted(missing_facts):
                violations.append(violation("TRANSFER_FACT_SUPPORT_INCOMPLETE", f"transfer.{name}.fact_refs", fact_id))
            missing_dimensions = set(task_policy["required_difference_dimensions"]) - set(task["difference_dimensions"])
            for dimension in sorted(missing_dimensions):
                violations.append(violation("TRANSFER_DIFFERENCE_MISSING", f"transfer.{name}.difference_dimensions", dimension))

        for path, text in [item for index, segment in enumerate(segments) for item in segment_visible_texts(segment, f"segments[{index}]")]:
            if task["object"] in text:
                violations.append(violation("TRANSFER_PREEXPOSED_IN_LESSON", path, f"contains transfer object {task['object']!r}"))

    return {"result": "fail" if violations else "pass", "violations": violations}


def validate_stage_pair(primary: dict[str, Any], middle: dict[str, Any]) -> dict[str, Any]:
    violations: list[dict[str, str]] = []
    if primary["core_relation"] != middle["core_relation"]:
        violations.append(violation("PAIR_RELATION_MISMATCH", "core_relation", "paired plans must explain the same relation"))
    if (primary["stage_profile"]["school_stage"], middle["stage_profile"]["school_stage"]) != ("primary", "middle"):
        violations.append(violation("PAIR_STAGE_INVALID", "stage_profile.school_stage", "pair must be primary then middle"))
    comparisons = {
        "prerequisites": (
            primary["stage_rules"]["allowed_prerequisite_refs"],
            middle["stage_rules"]["allowed_prerequisite_refs"],
        ),
        "terms": (primary["stage_rules"]["allowed_terms"], middle["stage_rules"]["allowed_terms"]),
        "visual_density": (
            primary["stage_rules"]["max_visual_elements"],
            middle["stage_rules"]["max_visual_elements"],
        ),
        "transfer_difficulty": (
            primary["stage_rules"]["transfer_difficulty"],
            middle["stage_rules"]["transfer_difficulty"],
        ),
    }
    for name, values in comparisons.items():
        if values[0] == values[1]:
            violations.append(violation("STAGE_LABEL_ONLY_PAIR", f"stage_rules.{name}", "paired plans must differ beyond the stage label"))
    return {"result": "fail" if violations else "pass", "violations": violations}


def _resolve_parent(value: Any, path: str) -> tuple[Any, str]:
    tokens = path.split(".")
    current = value
    for token in tokens[:-1]:
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current, tokens[-1]


def _read_path(value: Any, path: str) -> Any:
    current = value
    for token in path.split("."):
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def apply_mutations(
    base: dict[str, Any],
    mutations: list[dict[str, Any]],
    all_plans: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for mutation in mutations:
        parent, key = _resolve_parent(result, mutation["path"])
        operation = mutation["op"]
        if operation == "set":
            if isinstance(parent, list):
                parent[int(key)] = mutation["value"]
            else:
                parent[key] = mutation["value"]
        elif operation == "append":
            _read_path(result, mutation["path"]).append(mutation["value"])
        elif operation == "remove":
            parent.pop(int(key)) if isinstance(parent, list) else parent.pop(key)
        elif operation == "replace_from_plan":
            source = _read_path(all_plans[mutation["source_plan"]], mutation["source_path"])
            if isinstance(parent, list):
                parent[int(key)] = copy.deepcopy(source)
            else:
                parent[key] = copy.deepcopy(source)
        else:
            raise ValueError(f"Unknown mutation operation: {operation}")
    return result
