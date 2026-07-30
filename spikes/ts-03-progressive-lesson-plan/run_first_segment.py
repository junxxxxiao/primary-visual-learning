#!/usr/bin/env python3
"""Measure staged first-meaningful-segment readiness for four synthetic TS-03 fixtures."""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from run_model import QUESTIONS, api_call, assert_knowledge_provenance, load_local_env, parse_content, usage  # noqa: E402
from src.first_segment import validate_first_segment  # noqa: E402


def percentile(values: list[int], quantile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction)


def prompts(
    fixture: dict[str, Any],
    schema: dict[str, Any],
    generation_policy: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    system = (
        "你只生成可立即播放的第一个渐进讲解子片段，不生成后续段落或迁移题。"
        "只使用输入 knowledge.claims，不补充外部事实。首段 phase 必须是 explanation。"
        "用户确认问题后直接进入实质讲解，不生成预测、猜答案或等待儿童先作答的阶段。"
        "segment.fact_refs 和 static_fallback.fact_refs 必须引用相关 claim。"
        "起始画面在 0ms 完整显示，到 1000ms 才同时启动旁白和视觉。必须包含静态降级。"
        "visual.terms 只能从 stage_rules.allowed_terms 中选择，不得包含普通物体名称。"
        "严格返回符合 first-segment/1.2 Schema 的单个 JSON 对象，不要 Markdown。"
    )
    payload = {
        "schema_version": "first-segment-input/1.3",
        "fixture_id": fixture["fixture_id"],
        "question": QUESTIONS[fixture["fixture_id"]],
        "stage_profile": fixture["stage_profile"],
        "stage_rules": fixture["stage_rules"],
        "knowledge": fixture["knowledge"],
        "core_relation": fixture["core_relation"],
        "primary_object": fixture["primary_object"],
        "generation_policy": generation_policy,
        "required_output_schema": schema,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def main() -> int:
    load_local_env(ROOT / ".env.local")
    api_key = os.environ.get("TS03_API_KEY", "").strip()
    base_url = os.environ.get("TS03_API_BASE_URL", "").strip()
    model = os.environ.get("TS03_MODEL", "").strip()
    if not api_key or not base_url or not model:
        raise RuntimeError("TS03_API_KEY, TS03_API_BASE_URL, and TS03_MODEL must be configured")

    run_label = re.sub(r"[^a-zA-Z0-9._-]+", "-", os.environ.get("TS03_FIRST_SEGMENT_RUN_LABEL", "first-segment-round-1"))
    timeout_seconds = 30
    plans = json.loads((ROOT / "fixtures" / "plans.json").read_text(encoding="utf-8"))["plans"]
    assert_knowledge_provenance(plans)
    policies = json.loads((ROOT / "fixtures" / "policies.json").read_text(encoding="utf-8"))["policies"]
    schema = json.loads((ROOT / "schemas" / "first-segment.schema.json").read_text(encoding="utf-8"))
    safe_model = re.sub(r"[^a-zA-Z0-9._-]+", "-", model)
    raw_dir = ROOT / "results" / "raw" / safe_model / run_label
    raw_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []

    for fixture_id, fixture in plans.items():
        started = time.perf_counter()
        try:
            response, response_latency_ms = api_call(
                base_url,
                api_key,
                model,
                prompts(fixture, schema, policies[fixture_id]),
                timeout_seconds,
                max_tokens=3000,
            )
        except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as exc:
            records.append(
                {
                    "fixture_id": fixture_id,
                    "output_kind": "candidate_output",
                    "response_received": False,
                    "schema_valid": False,
                    "gate_result": "fail",
                    "first_meaningful_ready_ms": None,
                    "request_duration_ms": round((time.perf_counter() - started) * 1000),
                    "error": str(exc),
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                }
            )
            print(f"{fixture_id}: request failed: {exc}", flush=True)
            continue

        raw_text = json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        (raw_dir / f"{fixture_id}.json").write_text(raw_text, encoding="utf-8")
        parse_errors: list[str] = []
        output: dict[str, Any] | None = None
        try:
            output = parse_content(response)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            parse_errors.append(str(exc))
        gate = (
            validate_first_segment(
                output,
                fixture,
                schema,
                policies[fixture_id],
            )
            if output is not None
            else {"result": "fail", "violations": []}
        )
        ready_ms = round((time.perf_counter() - started) * 1000) if not parse_errors and gate["result"] == "pass" else None
        record = {
            "fixture_id": fixture_id,
            "output_kind": "candidate_output",
            "response_received": True,
            "schema_valid": not parse_errors and not any(item["code"] == "SCHEMA_INVALID" for item in gate["violations"]),
            "gate_result": gate["result"],
            "violation_codes": sorted({item["code"] for item in gate["violations"]}),
            "output_errors": parse_errors,
            "response_latency_ms": response_latency_ms,
            "first_meaningful_ready_ms": ready_ms,
            "response_model": response.get("model"),
            "response_hash": "sha256:" + hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
            "finish_reason": (response.get("choices") or [{}])[0].get("finish_reason"),
            "usage": usage(response),
        }
        records.append(record)
        print(
            f"{fixture_id}: schema={record['schema_valid']} gate={record['gate_result']} "
            f"ready_ms={ready_ms} tokens={record['usage']['total_tokens']}",
            flush=True,
        )

    ready_values = [item["first_meaningful_ready_ms"] for item in records if item["first_meaningful_ready_ms"] is not None]
    total_usage = {
        key: sum(item["usage"][key] for item in records)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    p80_ms = percentile(ready_values, 0.80)
    passes = len(ready_values) == 4 and p80_ms is not None and p80_ms < 8000
    result = {
        "slice_id": "TS-03",
        "diagnostic": "staged_first_meaningful_segment",
        "run_label": run_label,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "provider": "PackyAPI",
        "request_model": model,
        "fixed_parameters": {
            "temperature": 0,
            "response_format": "json_object",
            "max_tokens": 3000,
            "timeout_seconds": timeout_seconds,
            "automatic_retries": 0,
        },
        "requests": {"planned": 4, "attempted": len(records), "completed": sum(item["response_received"] for item in records)},
        "metrics": {
            "first_segment_gate_pass": {"numerator": len(ready_values), "denominator": 4},
            "first_meaningful_ready_p80_ms": p80_ms,
            "threshold_ms": 8000,
        },
        "usage": total_usage,
        "cost": "unverified; consult provider billing",
        "call_results": records,
        "status": "pass" if passes else "fail",
        "decision_effect": "This diagnostic does not replace or overwrite the formal round-3 TS-03 failure.",
    }
    output_path = ROOT / "results" / f"model-{safe_model}-{run_label}.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result={output_path} status={result['status']} p80_ms={p80_ms}", flush=True)
    return 0 if passes else 1


if __name__ == "__main__":
    raise SystemExit(main())
