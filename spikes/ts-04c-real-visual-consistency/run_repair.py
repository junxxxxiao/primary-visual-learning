#!/usr/bin/env python3
"""Run the single allowed TS-04C controlled repair round."""
from __future__ import annotations

import json
import os
import re
import socket
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import run_calibration as base


ROOT = Path(__file__).resolve().parent
SOURCE_RESULT = "model-deepseek-v4-pro-official-compact-calibration-round-1.json"
SOURCE_BROWSER_RESULT = "browser-official-compact-calibration-round-1-browser-round-3.json"


def prompts(
    sample: dict[str, Any],
    schema: dict[str, Any],
    original: dict[str, Any] | None,
    feedback: dict[str, Any],
) -> list[dict[str, str]]:
    system = (
        "你正在执行唯一一次受控修复，不得改变学习目标、旁白、claims 或静态降级。"
        "只返回 compact-generated-scene/0.2 JSON，不要 Markdown。只生成一份响应式 JavaScript。"
        "CanvasRenderingContext2D 方法只能在 const ctx=api.canvas.getContext('2d') 后通过 ctx 调用；"
        "禁止对 api.canvas 调用 beginPath、fillRect、clearRect 等 context 方法。"
        "每次运行必须支持 input.parameters.state 的 8 种状态，并先 emit interaction/layout_measurement，再 emit render_complete。"
        "手机 font_size>=16、min_graphic_size>=24、交互 touch_size>=44；平板分别 >=18、>=28、>=44。"
        "元素边界必须位于 0,0,width,height 内。teaching facts 的 expected、visual、narration 必须三者完全相同，"
        "且值为对应输入 claim_id。static_fallback 必须逐字复制输入。"
        "针对 feedback 逐项修复，不得增加外部事实，不得输出手机/平板或 8 状态声明。scene_code 不要注释。"
    )
    payload = {
        "schema_version": "controlled-scene-repair-input/0.1",
        "sample": sample,
        "original_candidate": original,
        "browser_feedback": feedback,
        "required_output_schema": schema,
        "repair_policy": {
            "attempt": 1,
            "maximum_attempts": 1,
            "preserve_sample_id": True,
            "preserve_learning_goal": True,
            "preserve_static_fallback": True,
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def main() -> int:
    base.load_local_env(ROOT / ".env.local")
    required = {
        key: os.environ.get(key, "").strip()
        for key in ("TS04C_PROVIDER", "TS04C_API_BASE_URL", "TS04C_API_KEY", "TS04C_MODEL", "TS04C_RUN_LABEL")
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required TS-04C configuration: {', '.join(missing)}")
    if int(os.environ.get("TS04C_MAX_REQUESTS", "0")) != 10:
        raise RuntimeError("Controlled repair budget must remain exactly 10 requests")
    if os.environ.get("TS04C_MAX_RETRIES") != "0":
        raise RuntimeError("Controlled repair requires zero automatic retries")
    if os.environ.get("TS04C_THINKING_TYPE") != "disabled":
        raise RuntimeError("Controlled repair requires thinking.type=disabled")
    if os.environ.get("TS04C_SEND_CONTROLLED_TEXTBOOK_CONTENT", "false").lower() == "true" or os.environ.get("TS04C_SEND_CHILD_DATA", "false").lower() == "true":
        raise RuntimeError("Controlled textbook content and child data are forbidden")

    fixture = json.loads((ROOT / "fixtures" / "calibration-inputs.json").read_text(encoding="utf-8"))
    source = json.loads((ROOT / "results" / SOURCE_RESULT).read_text(encoding="utf-8"))
    browser = json.loads((ROOT / "results" / SOURCE_BROWSER_RESULT).read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas" / "compact-generated-scene.schema.json").read_text(encoding="utf-8"))
    originals = {entry["sample_id"]: entry["candidate"] for entry in source["candidates"]}
    source_calls = {entry["sample_id"]: entry for entry in source["call_results"]}
    browser_results = {entry["sample_id"]: entry for entry in browser["results"]}

    run_label = re.sub(r"[^a-zA-Z0-9._-]+", "-", required["TS04C_RUN_LABEL"])
    model = required["TS04C_MODEL"]
    safe_model = re.sub(r"[^a-zA-Z0-9._-]+", "-", model)
    output = ROOT / "results" / f"model-{safe_model}-{run_label}.json"
    raw_dir = ROOT / "results" / "raw" / safe_model / run_label
    if output.exists() or raw_dir.exists():
        raise RuntimeError(f"Run label already has evidence: {run_label}")
    raw_dir.mkdir(parents=True)
    endpoint = required["TS04C_API_BASE_URL"].rstrip("/") + "/" + os.environ["TS04C_API_PATH"].strip("/")
    temperature = float(os.environ["TS04C_TEMPERATURE"])
    max_tokens = int(os.environ["TS04C_MAX_OUTPUT_TOKENS"])
    timeout = int(os.environ["TS04C_TIMEOUT_SECONDS"])
    calls = []
    candidates = []

    for sample in fixture["samples"]:
        sample_id = sample["sample_id"]
        browser_entry = browser_results.get(sample_id)
        feedback = {
            "violation_codes": browser_entry["violation_codes"] if browser_entry else ["MODEL_OUTPUT_PARSE_FAILED"],
            "runtime_errors": sorted({
                run["runtime_error_message"]
                for run in (browser_entry or {}).get("runs", [])
                if run.get("runtime_error_message")
            }),
            "original_parse_error": source_calls[sample_id].get("error"),
        }
        started = time.perf_counter()
        try:
            response, latency_ms = base.api_call(endpoint, required["TS04C_API_KEY"], {
                "model": model,
                "messages": prompts(sample, schema, originals.get(sample_id), feedback),
                "temperature": temperature,
                "response_format": {"type": "json_object"},
                "max_tokens": max_tokens,
                "stream": False,
                "thinking": {"type": "disabled"},
            }, timeout)
        except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            record = {
                "sample_id": sample_id, "output_kind": "candidate_output", "repair_attempt": 1,
                "response_received": False, "schema_valid": False, "candidate_contract": "fail",
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "violation_codes": ["MODEL_REQUEST_FAILED"], "error": str(exc),
                "repair_of_response_hash": source_calls[sample_id].get("response_hash"),
            }
            calls.append(record)
            print(f"{sample_id}: received=False schema=False contract=fail latency_ms={record['latency_ms']} tokens=0", flush=True)
            continue

        raw_text = json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        (raw_dir / f"{sample_id}.json").write_text(raw_text, encoding="utf-8")
        normalized = None
        violations = []
        parse_error = None
        try:
            normalized, violations = base.gate_candidate(base.parse_content(response), schema)
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
            parse_error = str(exc)
            violations = ["MODEL_OUTPUT_PARSE_FAILED"]
        if normalized is not None:
            candidates.append({"sample_id": sample_id, "candidate": normalized})
        record = {
            "sample_id": sample_id, "output_kind": "candidate_output", "repair_attempt": 1,
            "repair_of_response_hash": source_calls[sample_id].get("response_hash"),
            "response_received": True, "response_model": response.get("model"),
            "response_hash": base.sha256_text(raw_text),
            "finish_reason": (response.get("choices") or [{}])[0].get("finish_reason"),
            "latency_ms": latency_ms, "usage": base.usage(response),
            "schema_valid": normalized is not None,
            "candidate_contract": "pass" if normalized is not None and not violations else "fail",
            "violation_codes": violations,
        }
        if parse_error:
            record["error"] = parse_error
        calls.append(record)
        print(f"{sample_id}: received=True schema={record['schema_valid']} contract={record['candidate_contract']} latency_ms={latency_ms} tokens={record['usage']['total_tokens']}", flush=True)

    latencies = [entry["latency_ms"] for entry in calls]
    total_usage = {key: sum(entry["usage"][key] for entry in calls) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    result = {
        "slice_id": "TS-04C", "run_phase": "controlled_repair", "run_label": run_label,
        "run_at": datetime.now(timezone.utc).isoformat(), "provider": required["TS04C_PROVIDER"],
        "request_model": model, "response_models": sorted({entry.get("response_model") for entry in calls if entry.get("response_model")}),
        "base_url_origin": f"{urlsplit(endpoint).scheme}://{urlsplit(endpoint).netloc}",
        "source_result_file": SOURCE_RESULT, "source_browser_result_file": SOURCE_BROWSER_RESULT,
        "fixed_parameters": {"temperature": temperature, "response_format": "json_object", "max_tokens": max_tokens, "stream": False, "thinking": {"type": "disabled"}, "timeout_seconds": timeout, "automatic_retries": 0, "maximum_repairs_per_sample": 1},
        "requests": {"planned": 10, "attempted": len(calls), "completed": sum(entry["response_received"] for entry in calls), "automatic_retries": 0},
        "data_boundary": {"sealed_synthetic_knowledge_sent": True, "controlled_textbook_content_sent": False, "child_data_sent": False},
        "metrics": {"schema_validity": {"numerator": sum(entry["schema_valid"] for entry in calls), "denominator": 10}, "compact_contract_pass": {"numerator": sum(entry["candidate_contract"] == "pass" for entry in calls), "denominator": 10}, "sandbox_execution": "pending", "formal_denominator": False},
        "latency_ms": {"p50": base.percentile(latencies, 0.5), "p80": base.percentile(latencies, 0.8), "p95": base.percentile(latencies, 0.95), "max": max(latencies)},
        "usage": total_usage, "cost": {"amount": None, "currency": None, "reason": "Provider billing is not independently available to the runner."},
        "call_results": calls, "candidates": candidates, "human_review": {"status": "not_started"},
        "status": "candidate_run_complete" if candidates else "fail", "decision": "controlled_repair_only",
        "limits": ["Calibration repair outputs do not enter the formal denominator.", "Each sample used its single allowed repair attempt.", "Machine checks do not replace subject and product review."],
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result={output} decision={result['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
