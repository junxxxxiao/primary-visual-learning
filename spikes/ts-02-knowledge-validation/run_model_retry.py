#!/usr/bin/env python3
"""Retry only first-round transport/Schema failures with thinking disabled."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from time import monotonic


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from pipeline import CHECKS, build_source_index  # noqa: E402
from run_model import (  # noqa: E402
    STEP_RULES,
    api_call,
    cost_summary,
    load_local_env,
    model_payload,
    parse_model_step,
    prompt_for,
    read_json,
    sum_usage,
    usage_fields,
)


def main():
    load_local_env(ROOT / ".env.local")
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    model = os.environ.get("TS02_MODEL", "").strip()
    base_url = os.environ.get("TS02_API_BASE_URL", "").strip()
    if not api_key or not model or not base_url:
        raise RuntimeError("API key, model, and base URL must be configured")

    first_round_path = ROOT / f"results/model-{model}-round-1.json"
    first_round = read_json(first_round_path)
    targets = [
        (item["case_id"], item["step"])
        for item in first_round["call_results"]
        if not item["schema_valid"]
    ]
    if len(targets) != 7:
        raise RuntimeError(f"Expected exactly 7 first-round failures, found {len(targets)}")

    manifest = read_json(ROOT / "fixtures/source-manifest.json")
    fixture_set = read_json(ROOT / "fixtures/cases.json")
    cases = {item["case_id"]: item for item in fixture_set["cases"]}
    source_index = build_source_index(ROOT, manifest)
    step_schema = read_json(ROOT / "schemas/verification-step.schema.json")
    expected_steps = {
        case_id: {check(cases[case_id], source_index)["step"]: check(cases[case_id], source_index) for check in CHECKS}
        for case_id, _ in targets
    }

    raw_dir = ROOT / "results/raw/retry-no-thinking"
    raw_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for index, (case_id, step_name) in enumerate(targets, start=1):
        case = cases[case_id]
        system, user = prompt_for(step_name, model_payload(case, source_index))
        started = monotonic()
        response, status_code, latency_ms = api_call(
            base_url,
            api_key,
            model,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            thinking_type="disabled",
        )
        elapsed_ms = round((monotonic() - started) * 1000)
        response_hash = sha256(
            json.dumps(response, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        (raw_dir / f"{case_id}.{step_name}.json").write_text(
            json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        parsed, output_errors = parse_model_step(step_name, response, step_schema)
        expected = expected_steps[case_id][step_name]
        usage = usage_fields(response)
        record = {
            "case_id": case_id,
            "step": step_name,
            "http_status": status_code,
            "latency_ms": latency_ms,
            "elapsed_ms": elapsed_ms,
            "response_model": response.get("model", ""),
            "response_hash": f"sha256:{response_hash}",
            "usage": usage,
            "schema_valid": not output_errors,
            "output_errors": output_errors,
            "expected_status": expected["status"],
            "actual_status": parsed["status"],
            "status_match": parsed["status"] == expected["status"],
            "expected_reason_codes": expected["reason_codes"],
            "actual_reason_codes": parsed["reason_codes"],
            "reason_codes_match": sorted(parsed["reason_codes"]) == sorted(expected["reason_codes"]),
        }
        records.append(record)
        print(
            f"{index}/7 {case_id:<34} {step_name:<20} "
            f"schema={'pass' if record['schema_valid'] else 'fail'} "
            f"status={'pass' if record['status_match'] else 'fail'} "
            f"tokens={usage['total_tokens']} latency_ms={latency_ms}"
        )

    usage = sum_usage(records)
    summary = {
        "slice": "TS-02-real-model-format-retry",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "request_model": model,
        "base_url_origin": base_url,
        "source_result": first_round_path.name,
        "thinking": {"type": "disabled"},
        "requests": {"planned": len(targets), "completed": len(records), "automatic_retries": 0},
        "metrics": {
            "schema_validity": {
                "numerator": sum(item["schema_valid"] for item in records),
                "denominator": len(records),
            },
            "status_accuracy": {
                "numerator": sum(item["status_match"] for item in records),
                "denominator": len(records),
            },
            "reason_code_exact_match": {
                "numerator": sum(item["reason_codes_match"] for item in records),
                "denominator": len(records),
            },
        },
        "usage": usage,
        "estimated_cost": cost_summary(base_url, usage),
        "records": records,
        "decision": "format_gate_pass" if all(item["schema_valid"] for item in records) else "format_gate_fail",
        "limits": [
            "This targeted retry measures output-format recovery only.",
            "It is not a second full TS-02 round and does not replace the first-round result.",
            "Only synthetic fixtures were sent.",
        ],
    }
    output_path = ROOT / f"results/model-{model}-retry-no-thinking.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"result={output_path} schema={summary['metrics']['schema_validity']['numerator']}/7 "
        f"status={summary['metrics']['status_accuracy']['numerator']}/7 tokens={usage['total_tokens']}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
