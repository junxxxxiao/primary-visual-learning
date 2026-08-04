#!/usr/bin/env python3
"""Run the authorized TS-04C-v3 open-world calibration against DeepSeek official."""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
LOCAL_ENV = ROOT.parent / "ts-04c-real-visual-consistency" / ".env.local"
SCHEMA_VERSION = "open-visual-scene/0.2"
AUTHORIZED_PROVIDER = "deepseek"
AUTHORIZED_MODELS = {
    "deepseek-v4-pro": "official-open-world-v02-calibration-round-1",
    "deepseek-v4-flash": "official-open-world-v02-flash-calibration-round-1",
}
AUTHORIZED_ORIGIN = "https://api.deepseek.com"
MAX_REQUESTS = 10
MAX_OUTPUT_TOKENS = 5_000
TOKEN_BUDGET = 100_000
TIMEOUT_SECONDS = 60


def load_local_env(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[int], quantile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction)


def load_gate():
    import importlib.util

    path = ROOT / "src" / "gate_candidate.py"
    spec = importlib.util.spec_from_file_location("ts04c_v3_candidate_gate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load candidate gate: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def prompts(sample: dict[str, Any], schema: dict[str, Any], quality_contract: str) -> list[dict[str, str]]:
    system = (
        "你是中小学陌生问题视觉讲解场景规划器。只返回符合 open-visual-scene/0.2 的 JSON 对象，不要 Markdown。"
        "只能使用输入中的 synthetic claims，不补充外部事实，不把它们描述为教材或权威证据。"
        "生成一份设备无关的通用矢量场景图和 3 至 6 个完整讲解 beat；每个 beat 的旁白、事实引用和视觉动作必须同步。"
        "节点只能使用 schema 允许的通用类型，动作只能使用 schema 允许的受限类型。"
        "不得输出 JavaScript、HTML、CSS、SVG 字符串、外部 URL、任意表达式、手机专版或平板专版。"
        "必须原样复制 sample_id 和全部 claim_id；静态降级必须保留完整推理顺序。"
        "输出前自行核对：每个 parent_id、target_ids 和 interaction.target_ids 都已在 scene.nodes 声明；"
        "每个动作的 start_ms 加 duration_ms 不得超过所属 beat.duration_ms；单动作最多引用 20 个目标。"
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


def api_call(endpoint: str, api_key: str, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Primary-Visual-Learning-TS04C-v3/0.1",
        },
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8")), round((time.perf_counter() - started) * 1000)


def parse_candidate(response: dict[str, Any]) -> dict[str, Any]:
    content = response["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise TypeError("response content is not a string")
    return json.loads(content)


def response_usage(response: dict[str, Any]) -> dict[str, int]:
    source = response.get("usage") or {}
    return {key: int(source.get(key) or 0) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}


def validate_authorization(required: dict[str, str], endpoint: str) -> None:
    if required["TS04C_PROVIDER"].lower() != AUTHORIZED_PROVIDER:
        raise RuntimeError("Authorized provider is DeepSeek official only")
    if required["TS04C_MODEL"] not in AUTHORIZED_MODELS:
        raise RuntimeError(f"Authorized models are: {', '.join(sorted(AUTHORIZED_MODELS))}")
    if f"{urlsplit(endpoint).scheme}://{urlsplit(endpoint).netloc}" != AUTHORIZED_ORIGIN:
        raise RuntimeError("Authorized origin is https://api.deepseek.com only")
    expected = {
        "TS04C_TEMPERATURE": "0",
        "TS04C_THINKING_TYPE": "disabled",
        "TS04C_MAX_OUTPUT_TOKENS": str(MAX_OUTPUT_TOKENS),
        "TS04C_TIMEOUT_SECONDS": str(TIMEOUT_SECONDS),
        "TS04C_MAX_RETRIES": "0",
        "TS04C_RUN_PHASE": "calibration",
        "TS04C_MAX_REQUESTS": str(MAX_REQUESTS),
        "TS04C_SEND_SEALED_SYNTHETIC_KNOWLEDGE": "true",
        "TS04C_SEND_CONTROLLED_TEXTBOOK_CONTENT": "false",
        "TS04C_SEND_CHILD_DATA": "false",
    }
    mismatches = [key for key, value in expected.items() if os.environ.get(key, "").lower() != value]
    if mismatches:
        raise RuntimeError(f"Configuration differs from authorized parameters: {', '.join(mismatches)}")


def main() -> int:
    load_local_env(LOCAL_ENV)
    keys = ("TS04C_PROVIDER", "TS04C_API_BASE_URL", "TS04C_API_KEY", "TS04C_MODEL", "TS04C_API_PATH")
    required = {key: os.environ.get(key, "").strip() for key in keys}
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required TS-04C configuration: {', '.join(missing)}")
    endpoint = required["TS04C_API_BASE_URL"].rstrip("/") + "/" + required["TS04C_API_PATH"].strip("/")
    validate_authorization(required, endpoint)
    model = required["TS04C_MODEL"]
    run_label = AUTHORIZED_MODELS[model]

    fixtures_path = ROOT / "fixtures" / "calibration-inputs.json"
    schema_path = ROOT / "schemas" / "open-visual-scene-v0.2.schema.json"
    fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    quality_contract = (ROOT / "reference-quality-contract.md").read_text(encoding="utf-8")
    if fixtures.get("sample_count") != MAX_REQUESTS or fixtures.get("source_kind") != "synthetic_unverified":
        raise RuntimeError("Calibration fixtures must remain ten synthetic unverified samples")

    gate = load_gate()
    output = ROOT / "results" / f"model-{model}-{run_label}.json"
    raw_dir = ROOT / "results" / "raw" / model / run_label
    if output.exists() or raw_dir.exists():
        raise RuntimeError(f"Run label already has evidence: {run_label}")
    raw_dir.mkdir(parents=True)

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
            response, latency_ms = api_call(
                endpoint,
                required["TS04C_API_KEY"],
                {
                    "model": model,
                    "messages": prompts(sample, schema, quality_contract),
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "max_tokens": MAX_OUTPUT_TOKENS,
                    "stream": False,
                    "thinking": {"type": "disabled"},
                },
            )
            raw_text = json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            (raw_dir / f"{sample['sample_id']}.json").write_text(raw_text, encoding="utf-8")
            usage = response_usage(response)
            total_tokens += usage["total_tokens"]
            candidate = parse_candidate(response)
            violations = gate.gate_candidate(candidate, sample, schema)
            if not violations:
                candidates.append({"sample_id": sample["sample_id"], "candidate": candidate})
            record.update({
                "response_received": True,
                "response_model": response.get("model"),
                "response_hash": sha256_text(raw_text),
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
    total_usage = {key: sum(record["usage"][key] for record in calls) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    result = {
        "slice_id": "TS-04C-v3",
        "schema_version": SCHEMA_VERSION,
        "run_phase": "calibration",
        "run_label": run_label,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "provider": "deepseek_official",
        "request_model": model,
        "response_models": sorted({record["response_model"] for record in calls if record["response_model"]}),
        "base_url_origin": AUTHORIZED_ORIGIN,
        "fixed_parameters": {
            "temperature": 0,
            "thinking": {"type": "disabled"},
            "response_format": "json_object",
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "timeout_seconds": TIMEOUT_SECONDS,
            "automatic_retries": 0,
            "repairs": 0,
            "token_budget": TOKEN_BUDGET,
        },
        "data_boundary": {
            "synthetic_unverified_fixtures_sent": True,
            "controlled_textbook_content_sent": False,
            "child_data_sent": False,
            "production_logs_sent": False,
        },
        "evidence": {"fixture_hash": sha256_file(fixtures_path), "schema_hash": sha256_file(schema_path)},
        "requests": {"planned": 10, "attempted": len(calls), "completed": sum(record["response_received"] for record in calls), "automatic_retries": 0, "repairs": 0},
        "metrics": {"contract_pass": {"numerator": sum(record["gate_pass"] for record in calls), "denominator": 10}, "formal_denominator": False, "browser_gate": "not_started", "human_review": "not_started"},
        "latency_ms": {"p50": percentile(latencies, 0.5), "p80": percentile(latencies, 0.8), "p95": percentile(latencies, 0.95), "max": max(latencies)},
        "usage": total_usage,
        "cost": {"amount": None, "currency": None, "reason": "Provider billing was not independently available to the runner."},
        "call_results": calls,
        "candidates": candidates,
        "status": "candidate_run_complete",
        "decision": "await_browser_and_human_review",
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result={output} model={model} gate_pass={len(candidates)}/10 total_tokens={total_usage['total_tokens']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
