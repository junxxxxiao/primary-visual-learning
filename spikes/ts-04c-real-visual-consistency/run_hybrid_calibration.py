#!/usr/bin/env python3
"""Run the authorized DeepSeek Flash hybrid DSL calibration."""
from __future__ import annotations

import hashlib
import importlib.util
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
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
RUN_LABEL = "official-hybrid-dsl-v01-flash-calibration-round-1"
MODEL = "deepseek-v4-flash"
TOKEN_BUDGET = 100_000
MAX_OUTPUT_TOKENS = 5_000


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_module("ts04c_hybrid_base", ROOT / "run_calibration.py")
SCHEMA_VALIDATION = load_module(
    "ts04c_hybrid_schema_validation",
    ROOT.parent / "ts-03-progressive-lesson-plan" / "src" / "schema_validation.py",
)


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def bounded_sample(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": sample["sample_id"],
        "school_stage": sample["school_stage"],
        "learning_goal": sample["learning_goal"],
        "narration": sample["narration"],
        "visual_contract": sample["visual_contract"],
        "claims": [
            {"claim_id": claim["claim_id"], "text": claim["text"], "supported_terms": claim["supported_terms"]}
            for claim in sample["claims"]
        ],
    }


def prompts(sample: dict[str, Any], schema: dict[str, Any], example: dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "你是中小学动态视觉场景规划器。只输出 hybrid-generated-scene/0.1 JSON，不要 Markdown。"
        "不得输出 JavaScript、HTML、CSS、SVG、表达式或外部资源。只能使用输入 claims，不补充事实。"
        "sample_id 和所有 fact_refs 必须逐字复制。所有 id 使用小写英文、数字、点、下划线或连字符。"
        "画布坐标为 1000x800；内容保持在 x=80..920、y=100..700。"
        "关系线只引用已有节点和允许锚点；节点移动后端点由本地编译器重算。"
        "直线只用 slope、intercept、domain 表达，不猜像素端点。"
        "timeline.to 只允许 x/y；不要输出 width/height 动画。"
        "下面完整实例只用于严格模仿格式，不得复用实例事实。"
    )
    payload = {
        "schema_version": "hybrid-dsl-generation-input/0.1",
        "sample": bounded_sample(sample),
        "required_output_schema": schema,
        "complete_format_example": example,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def gate(candidate: dict[str, Any], sample: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    violations = SCHEMA_VALIDATION.validate(candidate, schema)
    if candidate.get("sample_id") != sample["sample_id"]:
        violations.append("binding.sample_id_mismatch")
    expected = [claim["claim_id"] for claim in sample["claims"]]
    if candidate.get("fact_refs") != expected:
        violations.append("binding.claim_ids_mismatch")
    serialized = json.dumps(candidate, ensure_ascii=False).lower()
    if any(token in serialized for token in ("javascript", "<script", "<svg", "eval(", "function(", "=>")):
        violations.append("safety.code_like_content")
    return sorted(set(violations))


def main() -> int:
    BASE.load_local_env(ROOT / ".env.local")
    required = {key: os.environ.get(key, "").strip() for key in (
        "TS04C_PROVIDER", "TS04C_API_BASE_URL", "TS04C_API_KEY", "TS04C_API_PATH", "TS04C_MODEL",
    )}
    if any(not value for value in required.values()):
        raise RuntimeError("Missing TS-04C API configuration")
    if required["TS04C_PROVIDER"].lower() != "deepseek" or required["TS04C_MODEL"] != MODEL:
        raise RuntimeError(f"Authorized candidate must be DeepSeek official {MODEL}")
    if os.environ.get("TS04C_THINKING_TYPE") != "disabled" or float(os.environ.get("TS04C_TEMPERATURE", "-1")) != 0:
        raise RuntimeError("Authorized parameters require thinking disabled and temperature 0")
    if int(os.environ.get("TS04C_MAX_REQUESTS", "0")) != 10 or os.environ.get("TS04C_MAX_RETRIES") != "0":
        raise RuntimeError("Authorized budget is 10 requests with zero retries")
    if os.environ.get("TS04C_SEND_SEALED_SYNTHETIC_KNOWLEDGE", "false").lower() != "true":
        raise RuntimeError("Synthetic knowledge sending must be explicitly enabled")
    if os.environ.get("TS04C_SEND_CONTROLLED_TEXTBOOK_CONTENT", "false").lower() == "true" or os.environ.get("TS04C_SEND_CHILD_DATA", "false").lower() == "true":
        raise RuntimeError("Controlled textbook content and child data are forbidden")

    fixture_path = ROOT / "fixtures" / "calibration-inputs.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("sample_count") != 10:
        raise RuntimeError("Frozen calibration fixture must contain 10 samples")
    schema_path = ROOT / "schemas" / "hybrid-generated-scene.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    preview = json.loads((ROOT / "fixtures" / "hybrid-preview-scenes.json").read_text(encoding="utf-8"))
    example_scene = preview["scenes"][0]
    example = {
        "schema_version": "hybrid-generated-scene/0.1",
        "sample_id": "synthetic.format.example",
        "title": example_scene["title"],
        "caption": example_scene["caption"],
        "fact_refs": ["synthetic.format.claim"],
        "scene": {key: example_scene[key] for key in ("schema_version", "nodes", "connectors", "function_lines", "timeline")},
    }
    endpoint = required["TS04C_API_BASE_URL"].rstrip("/") + "/" + required["TS04C_API_PATH"].strip("/")
    output = ROOT / "results" / f"model-{MODEL}-{RUN_LABEL}.json"
    raw_dir = ROOT / "results" / "raw" / MODEL / RUN_LABEL
    if output.exists() or raw_dir.exists():
        raise RuntimeError(f"Run label already exists: {RUN_LABEL}")
    raw_dir.mkdir(parents=True)

    calls, candidates = [], []
    total_tokens = 0
    for sample in fixture["samples"]:
        started = time.perf_counter()
        record = {"sample_id": sample["sample_id"], "output_kind": "candidate_output"}
        try:
            response, latency = BASE.api_call(endpoint, required["TS04C_API_KEY"], {
                "model": MODEL,
                "messages": prompts(sample, schema, example),
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "max_tokens": MAX_OUTPUT_TOKENS,
                "stream": False,
                "thinking": {"type": "disabled"},
            }, 60)
            raw_text = json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            (raw_dir / f"{sample['sample_id']}.json").write_text(raw_text, encoding="utf-8")
            parsed = BASE.parse_content(response)
            violations = gate(parsed, sample, schema)
            current_usage = BASE.usage(response)
            total_tokens += current_usage["total_tokens"]
            if total_tokens > TOKEN_BUDGET:
                raise RuntimeError(f"Token budget exceeded: {total_tokens}")
            record.update({
                "response_received": True, "response_model": response.get("model"),
                "response_hash": BASE.sha256_text(raw_text), "latency_ms": latency,
                "usage": current_usage, "contract_pass": not violations, "violation_codes": violations,
            })
            if not violations:
                candidates.append(parsed)
        except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            record.update({
                "response_received": False, "response_model": None, "response_hash": None,
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "contract_pass": False, "violation_codes": ["MODEL_OR_PARSE_FAILED"], "error": str(exc),
            })
        calls.append(record)
        print(f"{sample['sample_id']}: received={record['response_received']} pass={record['contract_pass']} tokens={record['usage']['total_tokens']}", flush=True)

    result = {
        "slice_id": "TS-04C-hybrid-v01", "status": "candidate_run_complete",
        "run_phase": "calibration", "run_label": RUN_LABEL,
        "run_at": datetime.now(timezone.utc).isoformat(), "provider": "deepseek_official",
        "request_model": MODEL, "response_models": sorted({item["response_model"] for item in calls if item.get("response_model")}),
        "base_url_origin": f"{urlsplit(endpoint).scheme}://{urlsplit(endpoint).netloc}",
        "fixed_parameters": {"temperature": 0, "thinking": {"type": "disabled"}, "response_format": "json_object", "max_output_tokens": MAX_OUTPUT_TOKENS, "timeout_seconds": 60, "automatic_retries": 0, "repairs": 0, "request_limit": 10, "token_limit": TOKEN_BUDGET},
        "data_boundary": {"synthetic_unverified_only": True, "controlled_textbook_content_sent": False, "child_data_sent": False},
        "evidence": {"fixture_hash": sha256_file(fixture_path), "schema_hash": sha256_file(schema_path)},
        "metrics": {"contract_pass": {"numerator": len(candidates), "denominator": 10}, "local_compile_gate": "pending", "human_review": "not_started", "formal_denominator": False},
        "latency_ms": {"p50": BASE.percentile([item["latency_ms"] for item in calls], 0.5), "p80": BASE.percentile([item["latency_ms"] for item in calls], 0.8), "max": max(item["latency_ms"] for item in calls)},
        "usage": {key: sum(item["usage"][key] for item in calls) for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
        "call_results": calls, "candidates": candidates,
        "limits": ["Synthetic calibration only.", "Machine gates do not establish teaching quality."],
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
