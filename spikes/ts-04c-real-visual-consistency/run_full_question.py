#!/usr/bin/env python3
"""Generate one authorized synthetic full-question lesson with DeepSeek Flash."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import socket
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
MODEL = "deepseek-v4-flash"
RUN_LABEL = "full-question-egg-saltwater-v01-network-attempt-2"
MAX_OUTPUT_TOKENS = 5_000
TOKEN_BUDGET = 25_000


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_module("ts04c_full_question_base", ROOT / "run_calibration.py")
SCHEMA_VALIDATION = load_module(
    "ts04c_full_question_schema_validation",
    ROOT.parent / "ts-03-progressive-lesson-plan" / "src" / "schema_validation.py",
)


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def prompts(fixture: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, str]]:
    example = {
        "schema_version": "full-question-lesson/0.1",
        "question_id": "synthetic.format.example",
        "question": "示例问题是什么？",
        "answer_summary": "这是只用于展示严格输出结构的示例总结，不得复制到真实输出。",
        "fact_refs": ["example.fact-a", "example.fact-b", "example.fact-c"],
        "segments": [
            {
                "segment_id": f"example.segment-{index}",
                "title": f"示例第{index}段",
                "narration": "这是格式示例旁白，实际输出必须根据输入事实重新组织，并保持完整自然。",
                "duration_ms": 8000,
                "fact_refs": ["example.fact-a"],
                "scene": {
                    "objects": [
                        {"id": "example-tank", "kind": "tank", "x": 500, "y": 360, "width": 620, "height": 360, "label": "示例容器", "style": "water"},
                        {"id": "example-object", "kind": "ellipse", "x": 500, "y": 400, "width": 130, "height": 170, "label": "示例物体", "style": "egg"},
                        {"id": "example-label", "kind": "label", "x": 500, "y": 100, "width": 420, "height": 50, "label": "示例观察", "style": "neutral"}
                    ],
                    "timeline": [
                        {"target_id": "example-label", "property": "opacity", "from": 0, "to": 1, "start_ms": 1000, "end_ms": 2200}
                    ]
                }
            }
            for index in range(1, 5)
        ]
    }
    system = (
        "你是中小学完整动态讲解规划器。只输出 full-question-lesson/0.1 JSON，不要 Markdown。"
        "只使用输入 claims，不补充事实，不把 synthetic 描述成教材或权威结论。"
        "必须输出正好4段，依次完成：观察现象、解释盐水变化、比较浮力与重力、总结因果。"
        "每段前1000ms必须是完整静止起始画面，所以 timeline.start_ms 不得小于1000。"
        "坐标系为1000x680；物体完整包围盒必须落在 x=60..940、y=60..620。"
        "tank 表示容器，ellipse 表示鸡蛋，particles 表示盐粒或密度粒子，arrow 表示力，label 表示解释，meter 表示比较条。"
        "arrow 的 x/y 是箭头中心，width/height 表示水平/竖直方向长度；force-up 向上，force-down 向下。"
        "所有 timeline target_id 必须引用本段已有对象；end_ms 必须大于 start_ms 且不超过本段 duration_ms。"
        "question_id 与 fact_refs 必须逐字复制输入。下面实例仅用于严格模仿格式，禁止复用实例事实或 id。"
    )
    payload = {
        "schema_version": "full-question-generation-input/0.1",
        "fixture": fixture,
        "required_output_schema": schema,
        "complete_format_example": example,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def semantic_gate(candidate: dict[str, Any], fixture: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    violations = SCHEMA_VALIDATION.validate(candidate, schema)
    expected_refs = [claim["claim_id"] for claim in fixture["claims"]]
    if candidate.get("question_id") != fixture["question_id"]:
        violations.append("binding.question_id_mismatch")
    if candidate.get("question") != fixture["question"]:
        violations.append("binding.question_mismatch")
    if candidate.get("fact_refs") != expected_refs:
        violations.append("binding.fact_refs_mismatch")
    segment_ids: set[str] = set()
    for segment in candidate.get("segments", []):
        if segment.get("segment_id") in segment_ids:
            violations.append("binding.duplicate_segment_id")
        segment_ids.add(segment.get("segment_id"))
        object_ids = {item.get("id") for item in segment.get("scene", {}).get("objects", [])}
        duration = segment.get("duration_ms", 0)
        for action in segment.get("scene", {}).get("timeline", []):
            if action.get("target_id") not in object_ids:
                violations.append("binding.timeline_unknown_target")
            if action.get("end_ms", 0) > duration or action.get("end_ms", 0) <= action.get("start_ms", 0):
                violations.append("timeline.invalid_range")
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
    if os.environ.get("TS04C_SEND_SEALED_SYNTHETIC_KNOWLEDGE", "false").lower() != "true":
        raise RuntimeError("Synthetic knowledge sending must be explicitly enabled")
    if os.environ.get("TS04C_SEND_CONTROLLED_TEXTBOOK_CONTENT", "false").lower() == "true" or os.environ.get("TS04C_SEND_CHILD_DATA", "false").lower() == "true":
        raise RuntimeError("Controlled textbook content and child data are forbidden")

    fixture_path = ROOT / "fixtures" / "full-question-egg-saltwater-v01.json"
    schema_path = ROOT / "schemas" / "full-question-lesson.schema.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    endpoint = required["TS04C_API_BASE_URL"].rstrip("/") + "/" + required["TS04C_API_PATH"].strip("/")
    output = ROOT / "results" / f"model-{MODEL}-{RUN_LABEL}.json"
    raw_path = ROOT / "results" / "raw" / MODEL / RUN_LABEL / "response.json"
    if output.exists() or raw_path.exists():
        raise RuntimeError(f"Run label already exists: {RUN_LABEL}")
    raw_path.parent.mkdir(parents=True)

    started = time.perf_counter()
    response_received = False
    error = None
    candidate = None
    violations: list[str] = []
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    response_model = None
    response_hash = None
    try:
        response, latency = BASE.api_call(endpoint, required["TS04C_API_KEY"], {
            "model": MODEL,
            "messages": prompts(fixture, schema),
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "max_tokens": MAX_OUTPUT_TOKENS,
            "stream": False,
            "thinking": {"type": "disabled"},
        }, 60)
        raw_text = json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        raw_path.write_text(raw_text, encoding="utf-8")
        response_hash = BASE.sha256_text(raw_text)
        response_model = response.get("model")
        response_received = True
        candidate = BASE.parse_content(response)
        violations = semantic_gate(candidate, fixture, schema)
        usage = BASE.usage(response)
        if usage["total_tokens"] > TOKEN_BUDGET:
            violations.append("budget.token_limit_exceeded")
    except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        latency = round((time.perf_counter() - started) * 1000)
        error = str(exc)
        violations = ["MODEL_OR_PARSE_FAILED"]

    result = {
        "slice_id": "TS-04C-full-question-v01",
        "status": "candidate_run_complete",
        "run_phase": "single_full_question_calibration",
        "run_label": RUN_LABEL,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "provider": "deepseek_official",
        "request_model": MODEL,
        "response_model": response_model,
        "base_url_origin": f"{urlsplit(endpoint).scheme}://{urlsplit(endpoint).netloc}",
        "fixed_parameters": {"temperature": 0, "thinking": {"type": "disabled"}, "response_format": "json_object", "max_output_tokens": MAX_OUTPUT_TOKENS, "timeout_seconds": 60, "automatic_retries": 0, "repairs": 0, "request_limit": 1, "token_limit": TOKEN_BUDGET},
        "data_boundary": fixture["data_boundary"],
        "evidence": {"fixture_hash": sha256_file(fixture_path), "schema_hash": sha256_file(schema_path)},
        "response_received": response_received,
        "response_hash": response_hash,
        "latency_ms": latency,
        "usage": usage,
        "contract_pass": not violations,
        "violation_codes": sorted(set(violations)),
        "error": error,
        "candidate": candidate if not violations else None,
        "limits": ["One synthetic unverified question only.", "A local renderer does not establish open-world model capability.", "Human teaching-quality review is pending."],
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "received": response_received, "contract_pass": not violations, "latency_ms": latency, "tokens": usage["total_tokens"], "violations": violations}, ensure_ascii=False))
    return 0 if response_received else 1


if __name__ == "__main__":
    raise SystemExit(main())
