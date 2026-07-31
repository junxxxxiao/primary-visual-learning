#!/usr/bin/env python3
"""Run one authorized repair for each failed V4 Flash v0.2 candidate."""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_calibration as base


ROOT = Path(__file__).resolve().parent
SOURCE_RESULT = ROOT / "results" / "model-deepseek-v4-flash-official-open-world-v02-flash-calibration-round-1.json"
RUN_LABEL = "official-open-world-v02-flash-repair-round-1"
AUTHORIZED_MODEL = "deepseek-v4-flash"
MAX_REPAIR_REQUESTS = 3
TOKEN_BUDGET = 30_000


def repair_prompts(sample: dict[str, Any], candidate: dict[str, Any], violations: list[str], schema: dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "你正在修复一份 open-visual-scene/0.2 JSON。只返回修复后的完整 JSON 对象，不要 Markdown。"
        "只修复给出的机器违规，不改变题目、事实、讲解目标或结论，不增加外部事实。"
        "sample_id、所有 claim_id、旁白含义和静态降级事实绑定必须保持。"
        "所有字段必须严格来自 required_output_schema：无父节点时省略 parent_id，不得填 null；"
        "line geometry 使用 points，不使用 x1/y1/x2/y2；layout.priority 必须为 1 至 5。"
        "输出前核对所有节点引用和 beat 时间，不得输出代码、外部 URL、手机专版或平板专版。"
    )
    payload = {
        "source_kind": "candidate_output_repair",
        "sample": sample,
        "original_candidate": candidate,
        "machine_violations": violations,
        "required_output_schema": schema,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def main() -> int:
    base.load_local_env(base.LOCAL_ENV)
    keys = ("TS04C_PROVIDER", "TS04C_API_BASE_URL", "TS04C_API_KEY", "TS04C_MODEL", "TS04C_API_PATH")
    required = {key: os.environ.get(key, "").strip() for key in keys}
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required TS-04C configuration: {', '.join(missing)}")
    endpoint = required["TS04C_API_BASE_URL"].rstrip("/") + "/" + required["TS04C_API_PATH"].strip("/")
    base.validate_authorization(required, endpoint)
    if required["TS04C_MODEL"] != AUTHORIZED_MODEL:
        raise RuntimeError(f"This repair is authorized for {AUTHORIZED_MODEL} only")

    source = json.loads(SOURCE_RESULT.read_text(encoding="utf-8"))
    if source.get("request_model") != AUTHORIZED_MODEL or source.get("schema_version") != base.SCHEMA_VERSION:
        raise RuntimeError("Source candidate model or schema differs from the authorized repair")
    failed_calls = [record for record in source["call_results"] if not record["gate_pass"]]
    if len(failed_calls) != MAX_REPAIR_REQUESTS or source["metrics"]["contract_pass"] != {"numerator": 7, "denominator": 10}:
        raise RuntimeError("Repair source must remain the frozen 7/10 Flash round with exactly three failures")

    fixtures = json.loads((ROOT / "fixtures" / "calibration-inputs.json").read_text(encoding="utf-8"))
    samples = {sample["sample_id"]: sample for sample in fixtures["samples"]}
    schema = json.loads((ROOT / "schemas" / "open-visual-scene-v0.2.schema.json").read_text(encoding="utf-8"))
    gate = base.load_gate()
    output = ROOT / "results" / f"model-{AUTHORIZED_MODEL}-{RUN_LABEL}.json"
    raw_dir = ROOT / "results" / "raw" / AUTHORIZED_MODEL / RUN_LABEL
    if output.exists() or raw_dir.exists():
        raise RuntimeError(f"Run label already has evidence: {RUN_LABEL}")
    raw_dir.mkdir(parents=True)

    repairs: list[dict[str, Any]] = []
    repaired_candidates: list[dict[str, Any]] = []
    total_tokens = 0
    source_raw_dir = ROOT / "results" / "raw" / AUTHORIZED_MODEL / source["run_label"]
    for index, failed in enumerate(failed_calls, start=1):
        if total_tokens >= TOKEN_BUDGET:
            raise RuntimeError(f"Repair Token budget exhausted before request {index}")
        sample_id = failed["sample_id"]
        source_response = json.loads((source_raw_dir / f"{sample_id}.json").read_text(encoding="utf-8"))
        candidate = base.parse_candidate(source_response)
        started = time.perf_counter()
        record: dict[str, Any] = {
            "sample_id": sample_id,
            "output_kind": "candidate_output",
            "attempt": 1,
            "source_response_hash": failed["response_hash"],
            "source_violations": failed["violation_codes"],
        }
        try:
            response, latency_ms = base.api_call(
                endpoint,
                required["TS04C_API_KEY"],
                {
                    "model": AUTHORIZED_MODEL,
                    "messages": repair_prompts(samples[sample_id], candidate, failed["violation_codes"], schema),
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "max_tokens": base.MAX_OUTPUT_TOKENS,
                    "stream": False,
                    "thinking": {"type": "disabled"},
                },
            )
            raw_text = json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            (raw_dir / f"{sample_id}.json").write_text(raw_text, encoding="utf-8")
            usage = base.response_usage(response)
            total_tokens += usage["total_tokens"]
            repaired = base.parse_candidate(response)
            violations = gate.gate_candidate(repaired, samples[sample_id], schema)
            if not violations:
                repaired_candidates.append({"sample_id": sample_id, "candidate": repaired})
            record.update({
                "response_received": True,
                "response_model": response.get("model"),
                "response_hash": base.sha256_text(raw_text),
                "finish_reason": (response.get("choices") or [{}])[0].get("finish_reason"),
                "latency_ms": latency_ms,
                "usage": usage,
                "gate_pass": not violations,
                "violation_codes": violations,
            })
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500] if isinstance(exc, urllib.error.HTTPError) else str(exc)
            record.update({
                "response_received": False,
                "response_model": None,
                "response_hash": None,
                "finish_reason": None,
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "gate_pass": False,
                "violation_codes": ["MODEL_REQUEST_OR_PARSE_FAILED"],
                "error": detail,
            })
        repairs.append(record)
        print(f"{index}/3 {sample_id}: received={record['response_received']} gate={record['gate_pass']} tokens={record['usage']['total_tokens']}", flush=True)

    if total_tokens > TOKEN_BUDGET:
        raise RuntimeError(f"Repair Token budget exceeded: {total_tokens} > {TOKEN_BUDGET}")
    latencies = [record["latency_ms"] for record in repairs]
    usage = {key: sum(record["usage"][key] for record in repairs) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    repair_pass = sum(record["gate_pass"] for record in repairs)
    final_pass = 7 + repair_pass
    result = {
        "slice_id": "TS-04C-v3",
        "run_phase": "controlled_repair",
        "run_label": RUN_LABEL,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "provider": "deepseek_official",
        "request_model": AUTHORIZED_MODEL,
        "response_models": sorted({record["response_model"] for record in repairs if record["response_model"]}),
        "schema_version": base.SCHEMA_VERSION,
        "source_result_file": SOURCE_RESULT.name,
        "fixed_parameters": {
            "temperature": 0,
            "thinking": {"type": "disabled"},
            "response_format": "json_object",
            "max_output_tokens": base.MAX_OUTPUT_TOKENS,
            "timeout_seconds": base.TIMEOUT_SECONDS,
            "automatic_retries": 0,
            "maximum_repairs_per_failed_sample": 1,
            "repair_token_budget": TOKEN_BUDGET,
        },
        "data_boundary": {
            "synthetic_unverified_fixtures_sent": True,
            "failed_candidate_outputs_sent": True,
            "machine_violation_codes_sent": True,
            "controlled_textbook_content_sent": False,
            "child_data_sent": False,
            "production_logs_sent": False,
        },
        "requests": {"planned": 3, "attempted": len(repairs), "completed": sum(record["response_received"] for record in repairs), "automatic_retries": 0},
        "metrics": {
            "initial_contract_pass": {"numerator": 7, "denominator": 10},
            "repair_contract_pass": {"numerator": repair_pass, "denominator": 3},
            "final_contract_pass": {"numerator": final_pass, "denominator": 10},
            "formal_denominator": False,
            "browser_gate": "pending" if final_pass == 10 else "not_started",
            "human_review": "not_started",
        },
        "latency_ms": {"p50": base.percentile(latencies, 0.5), "p80": base.percentile(latencies, 0.8), "p95": base.percentile(latencies, 0.95), "max": max(latencies)},
        "usage": usage,
        "cost": {"amount": None, "currency": None, "reason": "Provider billing was not independently available to the runner."},
        "call_results": repairs,
        "candidates": repaired_candidates,
        "status": "candidate_run_complete",
        "decision": "await_browser_gate" if final_pass == 10 else "repair_gate_failed",
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result={output} repair_pass={repair_pass}/3 final_pass={final_pass}/10 total_tokens={usage['total_tokens']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
