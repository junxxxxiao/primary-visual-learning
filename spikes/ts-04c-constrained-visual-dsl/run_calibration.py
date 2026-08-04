#!/usr/bin/env python3
"""Run the authorized ten-sample DeepSeek calibration for visual-dsl/0.1."""
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
REPO = ROOT.parent.parent
SOURCE_ROOT = ROOT.parent / "ts-04c-real-visual-consistency"
RUN_LABEL = "official-dsl-calibration-round-1"
TOKEN_BUDGET = 100_000
MAX_OUTPUT_TOKENS = 2_000


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_module("ts04c_v2_api", SOURCE_ROOT / "run_calibration.py")
SCHEMA_VALIDATION = load_module(
    "ts04c_v2_schema_validation",
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
        "claims": [
            {
                "claim_id": claim["claim_id"],
                "text": claim["text"],
                "supported_terms": claim["supported_terms"],
            }
            for claim in sample["claims"]
        ],
        "static_fallback": sample["static_fallback"],
        "visual_contract": sample["visual_contract"],
    }


def prompts(sample: dict[str, Any], schema: dict[str, Any], feedback: list[str] | None = None) -> list[dict[str, str]]:
    system = (
        "你是中小学互动视觉场景规划器。只返回 visual-dsl/0.1 JSON 对象，不要 Markdown。"
        "不得输出或嵌入 JavaScript、HTML、CSS、SVG、表达式、坐标、尺寸、动画代码或外部资源。"
        "只能使用输入提供的事实；sample_id 必须原样复制，facts 必须逐项复制全部 claim_id，"
        "static_fallback.steps 和 fact_refs 必须逐字复制。标题和标签使用简短中文。"
        "手机和平板响应式重排、8 种状态、绘制和边界检查由可信本地程序完成。"
    )
    payload: dict[str, Any] = {
        "schema_version": "visual-dsl-generation-input/0.1",
        "sample": bounded_sample(sample),
        "allowed_scene_types": ["comparison", "sequence", "area_model", "wave"],
        "allowed_color_tokens": {
            "primary": ["science-green", "math-blue"],
            "accent": ["signal-coral", "focus-yellow"],
        },
        "required_output_schema": schema,
    }
    if feedback:
        payload["repair"] = {
            "attempt": 1,
            "maximum_attempts": 1,
            "violation_codes": feedback,
        }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def gate_candidate(candidate: dict[str, Any], sample: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    violations = SCHEMA_VALIDATION.validate(candidate, schema)
    expected_facts = [claim["claim_id"] for claim in sample["claims"]]
    if candidate.get("sample_id") != sample["sample_id"]:
        violations.append("binding.sample_id_mismatch")
    if candidate.get("facts") != expected_facts:
        violations.append("binding.claim_ids_mismatch")
    fallback = candidate.get("static_fallback") or {}
    if fallback.get("steps") != sample["static_fallback"]["steps"]:
        violations.append("binding.static_steps_mismatch")
    if fallback.get("fact_refs") != sample["static_fallback"]["fact_refs"]:
        violations.append("binding.static_fact_refs_mismatch")
    serialized = json.dumps(candidate, ensure_ascii=False).lower()
    prohibited = ("javascript", "<script", "<svg", "<style", "eval(", "function(", "=>")
    if any(token in serialized for token in prohibited):
        violations.append("safety.code_like_content")
    return sorted(set(violations))


def invoke(
    sample: dict[str, Any],
    schema: dict[str, Any],
    endpoint: str,
    api_key: str,
    model: str,
    timeout: int,
    raw_dir: Path,
    attempt: int,
    feedback: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    started = time.perf_counter()
    try:
        response, latency_ms = BASE.api_call(
            endpoint,
            api_key,
            {
                "model": model,
                "messages": prompts(sample, schema, feedback),
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "max_tokens": MAX_OUTPUT_TOKENS,
                "stream": False,
                "thinking": {"type": "disabled"},
            },
            timeout,
        )
    except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        return ({
            "sample_id": sample["sample_id"],
            "output_kind": "candidate_output",
            "attempt": attempt,
            "response_received": False,
            "response_model": None,
            "response_hash": None,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "contract_pass": False,
            "violation_codes": ["MODEL_REQUEST_FAILED"],
            "error": str(exc),
        }, None)

    raw_text = json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    raw_path = raw_dir / f"{sample['sample_id']}-attempt-{attempt}.json"
    raw_path.write_text(raw_text, encoding="utf-8")
    candidate = None
    violations: list[str]
    error = None
    try:
        parsed = BASE.parse_content(response)
        violations = gate_candidate(parsed, sample, schema)
        if not violations:
            candidate = parsed
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
        violations = ["MODEL_OUTPUT_PARSE_FAILED"]
        error = str(exc)
    record = {
        "sample_id": sample["sample_id"],
        "output_kind": "candidate_output",
        "attempt": attempt,
        "response_received": True,
        "response_model": response.get("model"),
        "response_hash": BASE.sha256_text(raw_text),
        "finish_reason": (response.get("choices") or [{}])[0].get("finish_reason"),
        "latency_ms": latency_ms,
        "usage": BASE.usage(response),
        "contract_pass": candidate is not None,
        "violation_codes": violations,
    }
    if error:
        record["error"] = error
    return record, candidate


def main() -> int:
    BASE.load_local_env(SOURCE_ROOT / ".env.local")
    required = {
        key: os.environ.get(key, "").strip()
        for key in ("TS04C_PROVIDER", "TS04C_API_BASE_URL", "TS04C_API_KEY", "TS04C_API_PATH", "TS04C_MODEL")
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing TS-04C configuration: {', '.join(missing)}")
    if required["TS04C_PROVIDER"].lower() != "deepseek" or required["TS04C_MODEL"] != "deepseek-v4-pro":
        raise RuntimeError("Authorized candidate is DeepSeek official deepseek-v4-pro only")
    if os.environ.get("TS04C_THINKING_TYPE") != "disabled" or float(os.environ.get("TS04C_TEMPERATURE", "-1")) != 0:
        raise RuntimeError("Authorized parameters require thinking disabled and temperature 0")
    if os.environ.get("TS04C_SEND_SEALED_SYNTHETIC_KNOWLEDGE", "false").lower() != "true":
        raise RuntimeError("Sealed synthetic knowledge must be explicitly enabled")
    if os.environ.get("TS04C_SEND_CONTROLLED_TEXTBOOK_CONTENT", "false").lower() == "true" or os.environ.get("TS04C_SEND_CHILD_DATA", "false").lower() == "true":
        raise RuntimeError("Controlled textbook content and child data are forbidden")

    fixture_path = SOURCE_ROOT / "fixtures" / "calibration-inputs.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("sample_count") != 10:
        raise RuntimeError("Calibration fixture must remain frozen at 10 samples")
    schema_path = ROOT / "schemas" / "visual-dsl.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    model = required["TS04C_MODEL"]
    safe_model = re.sub(r"[^a-zA-Z0-9._-]+", "-", model)
    output = ROOT / "results" / f"model-{safe_model}-{RUN_LABEL}.json"
    candidate_output = ROOT / "results" / f"candidate-specs-{RUN_LABEL}.json"
    raw_dir = ROOT / "results" / "raw" / safe_model / RUN_LABEL
    if output.exists() or candidate_output.exists() or raw_dir.exists():
        raise RuntimeError(f"Run label already has evidence: {RUN_LABEL}")
    raw_dir.mkdir(parents=True)

    endpoint = required["TS04C_API_BASE_URL"].rstrip("/") + "/" + required["TS04C_API_PATH"].strip("/")
    timeout = int(os.environ.get("TS04C_TIMEOUT_SECONDS", "120"))
    call_results = []
    specs = []
    total_tokens = 0
    for sample in fixture["samples"]:
        record, candidate = invoke(sample, schema, endpoint, required["TS04C_API_KEY"], model, timeout, raw_dir, 0)
        call_results.append(record)
        total_tokens += record["usage"]["total_tokens"]
        print(f"{sample['sample_id']}: attempt=0 pass={record['contract_pass']} tokens={record['usage']['total_tokens']}", flush=True)
        if candidate is None and total_tokens < TOKEN_BUDGET:
            repair, candidate = invoke(sample, schema, endpoint, required["TS04C_API_KEY"], model, timeout, raw_dir, 1, record["violation_codes"])
            call_results.append(repair)
            total_tokens += repair["usage"]["total_tokens"]
            print(f"{sample['sample_id']}: attempt=1 pass={repair['contract_pass']} tokens={repair['usage']['total_tokens']}", flush=True)
        if total_tokens > TOKEN_BUDGET:
            raise RuntimeError(f"Token budget exceeded: {total_tokens} > {TOKEN_BUDGET}")
        if candidate is not None:
            specs.append({
                "fixture_kind": "candidate_output",
                "source_input_hash": sample["input_hash"],
                "spec": candidate,
            })

    candidate_fixture = {
        "fixture_version": "visual-dsl-candidate/0.1",
        "source_model_result": output.name,
        "sample_count": len(specs),
        "specs": specs,
    }
    candidate_output.write_text(json.dumps(candidate_fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latencies = [record["latency_ms"] for record in call_results]
    usage = {
        key: sum(record["usage"][key] for record in call_results)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    result = {
        "slice_id": "TS-04C-v2",
        "run_phase": "calibration",
        "run_label": RUN_LABEL,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "provider": required["TS04C_PROVIDER"],
        "request_model": model,
        "response_models": sorted({record["response_model"] for record in call_results if record.get("response_model")}),
        "base_url_origin": f"{urlsplit(endpoint).scheme}://{urlsplit(endpoint).netloc}",
        "fixed_parameters": {
            "temperature": 0,
            "thinking": {"type": "disabled"},
            "response_format": "json_object",
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "automatic_retries": 0,
            "maximum_repairs_per_sample": 1,
            "token_budget": TOKEN_BUDGET,
        },
        "data_boundary": {
            "sealed_synthetic_knowledge_sent": True,
            "controlled_textbook_content_sent": False,
            "child_data_sent": False,
        },
        "evidence": {
            "fixture_hash": sha256_file(fixture_path),
            "schema_hash": sha256_file(schema_path),
            "candidate_fixture": candidate_output.name,
        },
        "requests": {
            "planned_initial": 10,
            "initial_attempted": sum(record["attempt"] == 0 for record in call_results),
            "repairs_attempted": sum(record["attempt"] == 1 for record in call_results),
            "completed": sum(record["response_received"] for record in call_results),
        },
        "metrics": {
            "contract_pass": {"numerator": len(specs), "denominator": 10},
            "browser_gate": "pending",
            "formal_denominator": False,
        },
        "latency_ms": {
            "p50": BASE.percentile(latencies, 0.5),
            "p80": BASE.percentile(latencies, 0.8),
            "p95": BASE.percentile(latencies, 0.95),
            "max": max(latencies),
        },
        "usage": usage,
        "cost": {"amount": None, "currency": None, "reason": "Provider billing is not independently available to the runner."},
        "call_results": call_results,
        "status": "candidate_run_complete",
        "decision": "calibration_only",
        "human_review": {"status": "not_started"},
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result={output} candidates={len(specs)}/10 total_tokens={usage['total_tokens']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
