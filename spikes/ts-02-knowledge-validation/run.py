#!/usr/bin/env python3
"""Run the deterministic TS-02 protocol and write reviewable results."""

import json
import platform
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from pipeline import STAGE_FIELDS, build_source_index, validate_case  # noqa: E402
from schema_validation import validate  # noqa: E402


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def ratio_metric(numerator, denominator, threshold, comparator="equals"):
    value = numerator / denominator if denominator else 1.0
    passed = value == threshold if comparator == "equals" else value >= threshold
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": round(value, 6),
        "threshold": threshold,
        "comparator": comparator,
        "pass": passed,
    }


def count_metric(value, denominator, threshold=0):
    return {"value": value, "denominator": denominator, "threshold": threshold, "comparator": "equals", "pass": value == threshold}


def published(result):
    return result["actual_decision"] == "publish"


def unverified(result):
    return result["actual_decision"] == "unverified_generate"


def blocked(result):
    return result["actual_decision"] == "block"


def evidence_is_traceable(claim, source_index):
    refs = claim.get("evidence_refs", [])
    if not refs:
        return False
    for ref in refs:
        source = source_index.get(ref.get("source_id"))
        if not source or ref.get("page") not in source["actual_pages"]:
            return False
        if ref.get("quote", "") not in source["actual_pages"][ref["page"]]:
            return False
        if source["sha256"] != source["actual_sha256"]:
            return False
    return True


def main():
    manifest = read_json(ROOT / "fixtures/source-manifest.json")
    fixture_set = read_json(ROOT / "fixtures/cases.json")
    cases = fixture_set["cases"]
    source_index = build_source_index(ROOT, manifest)
    schemas = {
        "input": read_json(ROOT / "schemas/validation-input.schema.json"),
        "step": read_json(ROOT / "schemas/verification-step.schema.json"),
        "output": read_json(ROOT / "schemas/knowledge-package.schema.json"),
        "stage": read_json(ROOT / "schemas/stage-profile.schema.json"),
        "stage_fit": read_json(ROOT / "schemas/stage-fit.schema.json"),
    }

    results = []
    schema_checks = []
    for case in cases:
        schema_checks.append({"instance": f"input:{case['case_id']}", "errors": validate(case, schemas["input"])})
        result = validate_case(case, source_index)
        results.append(result)
        for step in result["steps"]:
            schema_checks.append({"instance": f"step:{case['case_id']}:{step['step']}", "errors": validate(step, schemas["step"])})
        schema_checks.append({"instance": f"output:{case['case_id']}", "errors": validate(result["package"], schemas["output"])})
        schema_checks.append({"instance": f"stage_fit:{case['case_id']}", "errors": validate(result["package"]["stage_fit"], schemas["stage_fit"])})
        if published(result) and result["package"]["stage_context_status"] == "provided":
            schema_checks.append({"instance": f"stage:{case['case_id']}", "errors": validate(case["stage_profile"], schemas["stage"])})

        print(f"\n[{case['case_id']}] expected={result['expected_decision']} actual={result['actual_decision']}")
        for step in result["steps"]:
            reasons = ",".join(step["reason_codes"]) or "none"
            print(f"  {step['step']:<20} {step['status']:<4} reasons={reasons}")
        print(json.dumps(result["package"], ensure_ascii=False, indent=2, sort_keys=True))

    published_results = [result for result in results if published(result)]
    published_claims = [claim for result in published_results for claim in result["package"]["claims"] if claim.get("critical")]
    traceable_claims = sum(evidence_is_traceable(claim, source_index) for claim in published_claims)
    provided_results = [result for result in published_results if result["package"]["stage_context_status"] == "provided"]
    context_denominator = len(provided_results) * len(STAGE_FIELDS)
    context_numerator = sum(
        1
        for result in provided_results
        for field in STAGE_FIELDS
        if result["package"]["stage_profile"].get(field) not in (None, "", [])
    )

    result_by_id = {result["case_id"]: result for result in results}
    schema_valid = sum(not check["errors"] for check in schema_checks)
    metrics = {
        "source_page_traceability": ratio_metric(traceable_claims, len(published_claims), 1.0),
        "provided_stage_context_completeness": ratio_metric(context_numerator, context_denominator, 1.0),
        "missing_stage_continues_without_guess": ratio_metric(int(published(result_by_id["missing_stage_context"]) and result_by_id["missing_stage_context"]["package"]["stage_fit"]["status"] == "unknown"), 1, 1.0),
        "declared_advanced_path_continues": ratio_metric(int(published(result_by_id["declared_advanced_path"]) and result_by_id["declared_advanced_path"]["package"]["stage_fit"]["status"] == "advanced"), 1, 1.0),
        "undeclared_cross_stage_publish": count_metric(int(published(result_by_id["cross_stage_source_mixing"])), 1),
        "unsupported_claim_marked_verified": count_metric(int(published(result_by_id["absent_evidence"])), 1),
        "no_source_marked_verified": count_metric(int(published(result_by_id["no_atom_no_authoritative_source"])), 1),
        "unverified_route_accuracy": ratio_metric(sum(unverified(result_by_id[case_id]) for case_id in ("absent_evidence", "no_atom_no_authoritative_source", "missing_page")), 3, 1.0),
        "unverified_notice_coverage": ratio_metric(sum(bool(result_by_id[case_id]["package"]["user_notice"]) for case_id in ("absent_evidence", "no_atom_no_authoritative_source", "missing_page")), 3, 1.0),
        "unverified_formal_result_write": count_metric(sum(result_by_id[case_id]["package"]["formal_learning_result_allowed"] for case_id in ("absent_evidence", "no_atom_no_authoritative_source", "missing_page")), 3),
        "blocked_route_accuracy": ratio_metric(sum(blocked(result_by_id[case_id]) for case_id in ("cross_stage_source_mixing", "verification_conflict", "ocr_error", "prompt_injection")), 4, 1.0),
        "verification_conflict_publish": count_metric(int(published(result_by_id["verification_conflict"])), 1),
        "schema_validity": ratio_metric(schema_valid, len(schema_checks), 0.99, "at_least"),
        "oracle_decision_accuracy": ratio_metric(sum(result["oracle_match"] for result in results), len(results), 1.0),
        "review_method_ai_only": ratio_metric(sum(result["package"]["review_method"] == "ai_only" for result in results), len(results), 1.0),
    }
    hard_metrics_pass = all(metric["pass"] for metric in metrics.values())
    unexpected_schema_failures = [check for check in schema_checks if check["errors"]]
    verdict = "conditional_pass" if hard_metrics_pass else "fail"

    summary = {
        "slice": "TS-02",
        "protocol_version": "1.0",
        "fixture_version": fixture_set["fixture_version"],
        "run_date": "2026-07-28",
        "baseline_sha": "b1632717167bc620154a82aa31cb83eb1f4fd094",
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "network_access": "disabled_by_design", "model_service": "none-deterministic-spike"},
        "cost": {"model_calls": 0, "network_requests": 0, "external_service_cost": 0, "currency": "CNY", "production_cost_validated": False},
        "sample_sizes": {"total_cases": len(cases), "expected_publish": 5, "expected_unverified_generate": 3, "expected_block": 4, "published_critical_claims": len(published_claims), "schema_instances": len(schema_checks)},
        "metrics": metrics,
        "schema_failures": unexpected_schema_failures,
        "case_results": [{"case_id": result["case_id"], "expected_decision": result["expected_decision"], "actual_decision": result["actual_decision"], "oracle_match": result["oracle_match"], "failed_steps": [step["step"] for step in result["steps"] if step["status"] == "fail"], "routing_reasons": result["package"]["routing_reasons"]} for result in results],
        "verdict": verdict,
        "verdict_scope": "Only the two fixed synthetic textbook fixtures and one synthetic temporary package; no real textbook, model, child, or broad grade coverage evidence.",
    }
    controlled_path = ROOT / "results/controlled-summary.json"
    if controlled_path.exists():
        controlled = read_json(controlled_path)
        summary["controlled_source_run"] = controlled
        summary["verdict_scope"] = (
            "Synthetic gate matrix plus the two user-authorized chapter ranges. "
            "The full math demo package routes to unverified generation because extrema and fence claims lack evidence in chapter 14."
        )
    failures = {
        "protocol_version": "1.0",
        "expected_blocked_examples": [result for result in results if result["expected_decision"] == "block"],
        "expected_unverified_examples": [result for result in results if result["expected_decision"] == "unverified_generate"],
        "unexpected_oracle_failures": [result for result in results if not result["oracle_match"]],
        "schema_failures": unexpected_schema_failures,
    }

    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    (results_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (results_dir / "failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nverdict={verdict} metrics_pass={hard_metrics_pass} cases={len(cases)} schema_instances={len(schema_checks)}")
    return 0 if hard_metrics_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
