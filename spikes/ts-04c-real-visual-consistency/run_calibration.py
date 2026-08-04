#!/usr/bin/env python3
"""Run the bounded TS-04C calibration round against an OpenAI-compatible API."""
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
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
TS04B = ROOT.parent / "ts-04b-visual-scene-gate"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SCHEMA_VALIDATION = load_module("ts03_schema_validation", ROOT.parent / "ts-03-progressive-lesson-plan" / "src" / "schema_validation.py")
VISUAL_VALIDATOR = load_module("ts04b_validator", TS04B / "src" / "validator.py")
validate_schema = SCHEMA_VALIDATION.validate
validate_scene_structure = VISUAL_VALIDATOR.validate_scene_structure
validate_teaching = VISUAL_VALIDATOR.validate_teaching
validate_visual_scene = VISUAL_VALIDATOR.validate_visual_scene


def load_local_env(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def percentile(values: list[int], quantile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction)


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def prompts(sample: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "你是受限的中小学互动视觉场景生成器。只使用输入 claims 和讲解文本，不补充外部事实。"
        "只生成一份根据 input.parameters.viewport.kind、width、height 自适应的纯 JavaScript，不要生成手机/平板声明。"
        "代码只能使用 api.canvas、input.parameters 和 api.emit；禁止网络、DOM、外部资源、eval、定时器和模块导入；"
        "代码同步绘制，按 input.parameters.state 支持 initial、key_process、final、paused、resumed、post_interaction、"
        "reduced_motion、static_fallback，完成后调用 api.emit('render_complete')。"
        "每次绘制后必须先 api.emit('interaction', {type:'layout_measurement', layout_mode, canvas_inner_bounds,"
        "local_safe_regions, readability_limits, container_metrics, elements, motion_envelopes})，再 emit render_complete。"
        "elements 每项含 element_id、bounds{x,y,width,height}、font_size、min_graphic_size、interactive、touch_size、"
        "local_safe_region；这些值必须来自本次实际绘制使用的坐标。不得用 overflow hidden、clip 或 mask 掩盖越界。"
        "输出必须紧凑：scene_code 不要注释，JSON 不要解释性文字；不要输出 phone/tablet 或 8 状态声明。"
        "teaching facts 的 expected、visual、narration 必须使用输入 claim_id；static_fallback 必须逐字保留输入内容。"
        "只返回符合 compact-generated-scene/0.2 的 JSON 对象，不要 Markdown。"
    )
    payload = {
        "schema_version": "visual-generation-input/0.1",
        "sample": sample,
        "runtime_contract": {
            "available_api": ["api.canvas", "api.emit", "input.parameters"],
            "states": ["initial", "key_process", "final", "paused", "resumed", "post_interaction", "reduced_motion", "static_fallback"],
            "viewports": {"phone": [390, 632], "tablet": [1024, 728]},
            "start_frame_hold_ms": 1000,
        },
        "required_output_schema": schema,
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)}]


def api_call(url: str, api_key: str, payload: dict[str, Any], timeout: int) -> tuple[dict[str, Any], int]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": "Primary-Visual-Learning-TS04C/0.1"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8")), round((time.perf_counter() - started) * 1000)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API HTTP {exc.code}: {detail[:500]}") from exc


def parse_content(response: dict[str, Any]) -> dict[str, Any]:
    content = response["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise TypeError("response content is not a string")
    return json.loads(content)


def usage(response: dict[str, Any]) -> dict[str, int]:
    source = response.get("usage") or {}
    return {key: int(source.get(key) or 0) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}


def gate_candidate(candidate: dict[str, Any], schema: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors = validate_schema(candidate, schema)
    if errors:
        return None, errors
    return json.loads(json.dumps(candidate)), []


def main() -> int:
    load_local_env(ROOT / ".env.local")
    required = {key: os.environ.get(key, "").strip() for key in ("TS04C_PROVIDER", "TS04C_API_BASE_URL", "TS04C_API_KEY", "TS04C_MODEL", "TS04C_RUN_LABEL")}
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required TS-04C configuration: {', '.join(missing)}")
    if os.environ.get("TS04C_RUN_PHASE") != "calibration":
        raise RuntimeError("This runner only permits TS04C_RUN_PHASE=calibration")
    if int(os.environ.get("TS04C_MAX_REQUESTS", "0")) != 10:
        raise RuntimeError("Calibration budget must remain exactly 10 requests")
    if os.environ.get("TS04C_MAX_RETRIES") != "0":
        raise RuntimeError("Calibration requires zero automatic retries")
    if os.environ.get("TS04C_THINKING_TYPE") != "disabled":
        raise RuntimeError("DeepSeek calibration requires explicit thinking.type=disabled")
    if os.environ.get("TS04C_SEND_SEALED_SYNTHETIC_KNOWLEDGE", "false").lower() != "true":
        raise RuntimeError("Sealed synthetic knowledge must be explicitly enabled")
    if os.environ.get("TS04C_SEND_CONTROLLED_TEXTBOOK_CONTENT", "false").lower() == "true" or os.environ.get("TS04C_SEND_CHILD_DATA", "false").lower() == "true":
        raise RuntimeError("Controlled textbook content and child data are forbidden")

    fixture = json.loads((ROOT / "fixtures" / "calibration-inputs.json").read_text(encoding="utf-8"))
    if fixture["sample_count"] != 10 or fixture["stage_counts"] != {"middle": 5, "primary": 5}:
        raise RuntimeError("Calibration fixture must remain frozen at 10 samples with a 5/5 split")
    schema = json.loads((ROOT / "schemas" / "compact-generated-scene.schema.json").read_text(encoding="utf-8"))
    provider = required["TS04C_PROVIDER"]
    model = required["TS04C_MODEL"]
    temperature = float(os.environ["TS04C_TEMPERATURE"])
    max_tokens = int(os.environ["TS04C_MAX_OUTPUT_TOKENS"])
    timeout = int(os.environ["TS04C_TIMEOUT_SECONDS"])
    run_label = re.sub(r"[^a-zA-Z0-9._-]+", "-", required["TS04C_RUN_LABEL"])
    endpoint = required["TS04C_API_BASE_URL"].rstrip("/") + "/" + os.environ["TS04C_API_PATH"].strip("/")
    safe_model = re.sub(r"[^a-zA-Z0-9._-]+", "-", model)
    output = ROOT / "results" / f"model-{safe_model}-{run_label}.json"
    raw_dir = ROOT / "results" / "raw" / safe_model / run_label
    if output.exists() or raw_dir.exists():
        raise RuntimeError(f"Run label already has evidence: {run_label}")
    raw_dir.mkdir(parents=True)
    calls = []
    candidates = []

    for sample in fixture["samples"]:
        started = time.perf_counter()
        record = {"sample_id": sample["sample_id"], "school_stage": sample["school_stage"], "output_kind": "candidate_output"}
        try:
            response, latency_ms = api_call(endpoint, required["TS04C_API_KEY"], {
                "model": model,
                "messages": prompts(sample, schema),
                "temperature": temperature,
                "response_format": {"type": "json_object"},
                "max_tokens": max_tokens,
                "stream": False,
                "thinking": {"type": "disabled"},
            }, timeout)
        except (RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            record.update({"response_received": False, "response_model": None, "response_hash": None, "finish_reason": None, "latency_ms": round((time.perf_counter() - started) * 1000), "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "schema_valid": False, "candidate_contract": "fail", "violation_codes": ["MODEL_REQUEST_FAILED"], "error": str(exc)})
            calls.append(record)
            print(f"{record['sample_id']}: received=False schema=False contract=fail latency_ms={record['latency_ms']} tokens=0", flush=True)
            continue

        raw_text = json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        (raw_dir / f"{sample['sample_id']}.json").write_text(raw_text, encoding="utf-8")
        normalized = None
        violations = []
        parse_error = None
        try:
            candidate = parse_content(response)
            normalized, violations = gate_candidate(candidate, schema)
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
            parse_error = str(exc)
            violations = ["MODEL_OUTPUT_PARSE_FAILED"]
        if normalized is not None:
            candidates.append({"sample_id": sample["sample_id"], "candidate": normalized})
        record.update({
            "response_received": True,
            "response_model": response.get("model"),
            "response_hash": sha256_text(raw_text),
            "finish_reason": (response.get("choices") or [{}])[0].get("finish_reason"),
            "latency_ms": latency_ms,
            "usage": usage(response),
            "schema_valid": normalized is not None,
            "candidate_contract": "pass" if normalized is not None and not violations else "fail",
            "violation_codes": violations,
        })
        if parse_error:
            record["error"] = parse_error
        calls.append(record)
        print(f"{record['sample_id']}: received={record['response_received']} schema={record['schema_valid']} contract={record['candidate_contract']} latency_ms={record['latency_ms']} tokens={record['usage']['total_tokens']}", flush=True)

    latencies = [item["latency_ms"] for item in calls]
    total_usage = {key: sum(item["usage"][key] for item in calls) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    completed_requests = sum(item["response_received"] for item in calls)
    result_status = "candidate_run_complete" if completed_requests else "fail"
    result_decision = "calibration_only" if completed_requests else "calibration_provider_timeout"
    result = {
        "slice_id": "TS-04C",
        "run_phase": "calibration",
        "run_label": run_label,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "request_model": model,
        "response_models": sorted({item["response_model"] for item in calls if item["response_model"]}),
        "base_url_origin": f"{urlsplit(endpoint).scheme}://{urlsplit(endpoint).netloc}",
        "fixed_parameters": {"temperature": temperature, "response_format": "json_object", "max_tokens": max_tokens, "stream": False, "thinking": {"type": "disabled"}, "timeout_seconds": timeout, "automatic_retries": 0},
        "requests": {"planned": 10, "attempted": len(calls), "completed": sum(item["response_received"] for item in calls), "automatic_retries": 0},
        "data_boundary": {"sealed_synthetic_knowledge_sent": True, "controlled_textbook_content_sent": False, "child_data_sent": False},
        "metrics": {"schema_validity": {"numerator": sum(item["schema_valid"] for item in calls), "denominator": 10}, "compact_contract_pass": {"numerator": sum(item["candidate_contract"] == "pass" for item in calls), "denominator": 10}, "sandbox_execution": "pending", "formal_denominator": False},
        "latency_ms": {"p50": percentile(latencies, 0.5), "p80": percentile(latencies, 0.8), "p95": percentile(latencies, 0.95), "max": max(latencies)},
        "usage": total_usage,
        "cost": {"amount": None, "currency": None, "reason": "Provider billing is not independently available to the runner."},
        "call_results": calls,
        "candidates": candidates,
        "human_review": {"status": "not_started"},
        "status": result_status,
        "decision": result_decision,
        "limits": ["Calibration samples do not enter the formal denominator.", "Declared bounds do not replace browser measurements or pixel checks.", "Machine checks do not replace subject and product review."],
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result={output} decision=calibration_only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
