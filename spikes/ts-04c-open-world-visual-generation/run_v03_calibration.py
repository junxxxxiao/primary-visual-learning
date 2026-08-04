#!/usr/bin/env python3
"""Run the authorized DeepSeek V4 Flash calibration against open-visual-scene/0.3."""
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
AUTHORIZED_MODEL = "deepseek-v4-flash"
SCHEMA_VERSION = "open-visual-scene/0.3"
RUN_LABEL = "official-open-world-v03-flash-calibration-round-1"
MAX_REQUESTS = 10
TOKEN_BUDGET = 100_000


def prompts(sample: dict[str, Any], schema: dict[str, Any], quality_contract: str) -> list[dict[str, str]]:
    system = (
        "你是中小学陌生问题视觉讲解场景规划器。只返回符合 open-visual-scene/0.3 的 JSON 对象，不要 Markdown。"
        "只能使用输入中的 synthetic claims，不补充外部事实，不把它们描述为教材或权威证据。"
        "生成一份设备无关的通用矢量场景图和 3 至 6 个完整讲解 beat；每个 beat 的旁白、事实引用和视觉动作必须同步。"
        "scene.coordinate_space.anchor 必须为 center；所有 geometry.x/y 和动作 to.x/to.y 都表示元素中心点。"
        "width/height 从中心向两侧各延伸一半；任何初始图形及移动、缩放、旋转、变形的完整轨迹都必须在 0..1000 内。"
        "points 是绝对坐标；含 points 的节点不得使用 move、scale、rotate 或 morph。"
        "节点和动作只能使用 Schema 允许的类型，不得输出 JavaScript、HTML、CSS、SVG 字符串、外部 URL、手机专版或平板专版。"
        "必须原样复制 sample_id 和全部 claim_id；静态降级必须保留完整推理顺序。"
        "输出前核对所有 parent_id、target_ids 和 interaction.target_ids 均已声明，且动作结束时间不超过所属 beat。"
    )
    payload = {
        "fixture_kind": sample["fixture_kind"],
        "source_kind": "synthetic_unverified",
        "sample": sample,
        "quality_reference_contract": quality_contract,
        "required_output_schema": schema,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def main(
    *,
    run_label: str = RUN_LABEL,
    prompt_builder=prompts,
    prompt_profile: dict[str, Any] | None = None,
    schema_version: str = SCHEMA_VERSION,
    schema_filename: str = "open-visual-scene-v0.3.schema.json",
    slice_id: str = "TS-04C-v3",
) -> int:
    base.load_local_env(base.LOCAL_ENV)
    keys = ("TS04C_PROVIDER", "TS04C_API_BASE_URL", "TS04C_API_KEY", "TS04C_MODEL", "TS04C_API_PATH")
    required = {key: os.environ.get(key, "").strip() for key in keys}
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required TS-04C configuration: {', '.join(missing)}")
    endpoint = required["TS04C_API_BASE_URL"].rstrip("/") + "/" + required["TS04C_API_PATH"].strip("/")
    base.validate_authorization(required, endpoint)
    if required["TS04C_MODEL"] != AUTHORIZED_MODEL:
        raise RuntimeError(f"This v0.3 run is authorized for {AUTHORIZED_MODEL} only")

    fixtures = json.loads((ROOT / "fixtures" / "calibration-inputs.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas" / schema_filename).read_text(encoding="utf-8"))
    quality_contract = (ROOT / "reference-quality-contract.md").read_text(encoding="utf-8")
    if fixtures.get("sample_count") != MAX_REQUESTS or fixtures.get("source_kind") != "synthetic_unverified":
        raise RuntimeError("Calibration fixtures must remain ten synthetic unverified samples")
    if schema.get("$id") != schema_version:
        raise RuntimeError(f"Runner expected {schema_version}, got {schema.get('$id')}")

    output = ROOT / "results" / f"model-{AUTHORIZED_MODEL}-{run_label}.json"
    raw_dir = ROOT / "results" / "raw" / AUTHORIZED_MODEL / run_label
    if output.exists() or raw_dir.exists():
        raise RuntimeError(f"Run label already has evidence: {run_label}")
    raw_dir.mkdir(parents=True)

    gate = base.load_gate()
    calls: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    total_tokens = 0
    for index, sample in enumerate(fixtures["samples"], start=1):
        if total_tokens >= TOKEN_BUDGET:
            raise RuntimeError(f"Token budget exhausted before request {index}")
        started = time.perf_counter()
        record: dict[str, Any] = {
            "sample_id": sample["sample_id"],
            "fixture_kind": sample["fixture_kind"],
            "output_kind": "candidate_output",
        }
        try:
            response, latency_ms = base.api_call(
                endpoint,
                required["TS04C_API_KEY"],
                {
                    "model": AUTHORIZED_MODEL,
                    "messages": prompt_builder(sample, schema, quality_contract),
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "max_tokens": base.MAX_OUTPUT_TOKENS,
                    "stream": False,
                    "thinking": {"type": "disabled"},
                },
            )
            raw_text = json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            (raw_dir / f"{sample['sample_id']}.json").write_text(raw_text, encoding="utf-8")
            usage = base.response_usage(response)
            total_tokens += usage["total_tokens"]
            candidate = base.parse_candidate(response)
            violations = gate.gate_candidate(candidate, sample, schema)
            if not violations:
                candidates.append({"sample_id": sample["sample_id"], "candidate": candidate})
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
        calls.append(record)
        print(f"{index}/10 {record['sample_id']}: received={record['response_received']} gate={record['gate_pass']} tokens={record['usage']['total_tokens']}", flush=True)

    if total_tokens > TOKEN_BUDGET:
        raise RuntimeError(f"Token budget exceeded: {total_tokens} > {TOKEN_BUDGET}")
    latencies = [record["latency_ms"] for record in calls]
    usage = {key: sum(record["usage"][key] for record in calls) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    contract_pass = sum(record["gate_pass"] for record in calls)
    result = {
        "slice_id": slice_id,
        "schema_version": schema_version,
        "run_phase": "calibration",
        "run_label": run_label,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "provider": "deepseek_official",
        "request_model": AUTHORIZED_MODEL,
        "response_models": sorted({record["response_model"] for record in calls if record["response_model"]}),
        "base_url_origin": base.AUTHORIZED_ORIGIN,
        "fixed_parameters": {
            "temperature": 0,
            "thinking": {"type": "disabled"},
            "response_format": "json_object",
            "max_output_tokens": base.MAX_OUTPUT_TOKENS,
            "timeout_seconds": base.TIMEOUT_SECONDS,
            "automatic_retries": 0,
            "repairs": 0,
            "request_limit": MAX_REQUESTS,
            "total_token_limit": TOKEN_BUDGET,
        },
        "data_boundary": {
            "synthetic_unverified_fixtures_sent": True,
            "controlled_textbook_content_sent": False,
            "child_data_sent": False,
            "production_logs_sent": False,
        },
        "requests": {
            "planned": MAX_REQUESTS,
            "attempted": len(calls),
            "completed": sum(record["response_received"] for record in calls),
            "automatic_retries": 0,
        },
        "metrics": {
            "contract_pass": {"numerator": contract_pass, "denominator": MAX_REQUESTS},
            "browser_gate": "pending" if contract_pass == MAX_REQUESTS else "not_started",
            "human_review": "not_started",
        },
        "latency_ms": {
            "p50": base.percentile(latencies, 0.5),
            "p80": base.percentile(latencies, 0.8),
            "p95": base.percentile(latencies, 0.95),
            "max": max(latencies),
        },
        "usage": usage,
        "cost": {"amount": None, "currency": None, "reason": "Provider billing was not independently available to the runner."},
        "call_results": calls,
        "candidates": candidates,
        "status": "candidate_run_complete",
        "decision": "await_browser_gate" if contract_pass == MAX_REQUESTS else "contract_gate_failed",
    }
    if prompt_profile is not None:
        result["prompt_profile"] = prompt_profile
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result={output} contract_pass={contract_pass}/10 total_tokens={usage['total_tokens']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
