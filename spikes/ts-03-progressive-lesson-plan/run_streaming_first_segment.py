#!/usr/bin/env python3
"""Measure streamed first-byte, content, and validated first-segment readiness."""
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
from urllib.parse import urlsplit
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from run_first_segment import prompts  # noqa: E402
from run_model import assert_knowledge_provenance, load_local_env  # noqa: E402
from src.first_segment import validate_first_segment  # noqa: E402


class StreamDeadlineExceeded(RuntimeError):
    pass


def parse_sse_data(line: bytes | str) -> dict[str, Any] | str | None:
    text = line.decode("utf-8", errors="replace") if isinstance(line, bytes) else line
    stripped = text.strip()
    if not stripped.startswith("data:"):
        return None
    payload = stripped[5:].strip()
    if payload == "[DONE]":
        return "done"
    return json.loads(payload)


def percentile(values: list[int], quantile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction)


def elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def official_request_payload(
    model: str,
    fixture: dict[str, Any],
    schema: dict[str, Any],
    generation_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": prompts(fixture, schema, generation_policy),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "max_tokens": 3000,
        "stream": True,
        "thinking": {"type": "disabled"},
    }


def validate_official_base_url(base_url: str) -> None:
    if urlsplit(base_url).hostname != "api.deepseek.com":
        raise RuntimeError("Official DeepSeek diagnostic requires TS03_API_BASE_URL host api.deepseek.com")


def stream_fixture(
    *,
    base_url: str,
    api_key: str,
    model: str,
    fixture: dict[str, Any],
    schema: dict[str, Any],
    generation_policy: dict[str, Any],
    raw_path: Path,
    deadline_seconds: int,
) -> dict[str, Any]:
    body = json.dumps(
        official_request_payload(model, fixture, schema, generation_policy),
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Primary-Visual-Learning-TS03-Streaming/1.0",
        },
        method="POST",
    )
    started = time.perf_counter()
    metrics: dict[str, int | None] = {
        "response_headers_ms": None,
        "first_sse_event_ms": None,
        "first_reasoning_delta_ms": None,
        "first_content_delta_ms": None,
        "first_meaningful_ready_ms": None,
    }
    content_parts: list[str] = []
    reasoning_character_count = 0
    sse_event_count = 0
    response_model: str | None = None
    finish_reason: str | None = None
    gate_result = "fail"
    violation_codes: list[str] = []
    parse_error: str | None = None
    timed_out = False
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with urllib.request.urlopen(request, timeout=deadline_seconds) as response, raw_path.open("wb") as raw:
            metrics["response_headers_ms"] = elapsed_ms(started)
            while True:
                if time.perf_counter() - started >= deadline_seconds:
                    raise StreamDeadlineExceeded(f"stream exceeded {deadline_seconds}s deadline")
                line = response.readline()
                if not line:
                    break
                raw.write(line)
                raw.flush()
                try:
                    event = parse_sse_data(line)
                except json.JSONDecodeError as exc:
                    parse_error = str(exc)
                    continue
                if event is None:
                    continue
                sse_event_count += 1
                if metrics["first_sse_event_ms"] is None:
                    metrics["first_sse_event_ms"] = elapsed_ms(started)
                if event == "done":
                    break
                if not isinstance(event, dict):
                    continue
                response_model = event.get("model") or response_model
                choices = event.get("choices") or []
                if not choices:
                    continue
                choice = choices[0]
                finish_reason = choice.get("finish_reason") or finish_reason
                delta = choice.get("delta") or {}
                reasoning = delta.get("reasoning_content")
                reasoning_character_count += len(reasoning or "")
                if reasoning and metrics["first_reasoning_delta_ms"] is None:
                    metrics["first_reasoning_delta_ms"] = elapsed_ms(started)
                content = delta.get("content")
                if not content:
                    continue
                if metrics["first_content_delta_ms"] is None:
                    metrics["first_content_delta_ms"] = elapsed_ms(started)
                content_parts.append(content)
                try:
                    output = json.loads("".join(content_parts))
                except json.JSONDecodeError:
                    continue
                gate = validate_first_segment(output, fixture, schema, generation_policy)
                gate_result = gate["result"]
                violation_codes = sorted({item["code"] for item in gate["violations"]})
                if gate_result == "pass":
                    metrics["first_meaningful_ready_ms"] = elapsed_ms(started)
                    break
    except (TimeoutError, socket.timeout, StreamDeadlineExceeded) as exc:
        timed_out = True
        parse_error = str(exc)
    except urllib.error.HTTPError as exc:
        parse_error = f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}"
    except urllib.error.URLError as exc:
        parse_error = f"Network error: {exc.reason}"

    raw_hash = None
    if raw_path.exists():
        raw_hash = "sha256:" + hashlib.sha256(raw_path.read_bytes()).hexdigest()
    return {
        "fixture_id": fixture["fixture_id"],
        "output_kind": "candidate_output",
        "metrics": metrics,
        "timed_out": timed_out,
        "gate_result": gate_result,
        "violation_codes": violation_codes,
        "parse_error": parse_error,
        "response_model": response_model,
        "finish_reason": finish_reason,
        "sse_event_count": sse_event_count,
        "reasoning_character_count": reasoning_character_count,
        "content_character_count": len("".join(content_parts)),
        "raw_stream_hash": raw_hash,
    }


def main() -> int:
    load_local_env(ROOT / ".env.local")
    api_key = os.environ.get("TS03_API_KEY", "").strip()
    base_url = os.environ.get("TS03_API_BASE_URL", "").strip()
    model = os.environ.get("TS03_MODEL", "").strip()
    if not api_key or not base_url or not model:
        raise RuntimeError("TS03_API_KEY, TS03_API_BASE_URL, and TS03_MODEL must be configured")
    validate_official_base_url(base_url)

    run_label = "official-stream-first-segment-round-1"
    deadline_seconds = 30
    plans = json.loads((ROOT / "fixtures" / "plans.json").read_text(encoding="utf-8"))["plans"]
    assert_knowledge_provenance(plans)
    policies = json.loads((ROOT / "fixtures" / "policies.json").read_text(encoding="utf-8"))["policies"]
    schema = json.loads((ROOT / "schemas" / "first-segment.schema.json").read_text(encoding="utf-8"))
    safe_model = re.sub(r"[^a-zA-Z0-9._-]+", "-", model)
    raw_dir = ROOT / "results" / "raw" / safe_model / run_label
    records: list[dict[str, Any]] = []

    for fixture_id, fixture in plans.items():
        record = stream_fixture(
            base_url=base_url,
            api_key=api_key,
            model=model,
            fixture=fixture,
            schema=schema,
            generation_policy=policies[fixture_id],
            raw_path=raw_dir / f"{fixture_id}.sse",
            deadline_seconds=deadline_seconds,
        )
        records.append(record)
        print(
            f"{fixture_id}: event_ms={record['metrics']['first_sse_event_ms']} "
            f"content_ms={record['metrics']['first_content_delta_ms']} "
            f"ready_ms={record['metrics']['first_meaningful_ready_ms']} "
            f"gate={record['gate_result']} timeout={record['timed_out']}",
            flush=True,
        )

    event_values = [item["metrics"]["first_sse_event_ms"] for item in records if item["metrics"]["first_sse_event_ms"] is not None]
    reasoning_values = [item["metrics"]["first_reasoning_delta_ms"] for item in records if item["metrics"]["first_reasoning_delta_ms"] is not None]
    content_values = [item["metrics"]["first_content_delta_ms"] for item in records if item["metrics"]["first_content_delta_ms"] is not None]
    ready_values = [item["metrics"]["first_meaningful_ready_ms"] for item in records if item["metrics"]["first_meaningful_ready_ms"] is not None]
    ready_p80 = percentile(ready_values, 0.80)
    passes = len(ready_values) == 4 and ready_p80 is not None and ready_p80 < 8000
    result = {
        "slice_id": "TS-03",
        "diagnostic": "streamed_first_meaningful_segment",
        "run_label": run_label,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "provider": "DeepSeek official API",
        "request_model": model,
        "fixed_parameters": {
            "temperature": 0,
            "response_format": "json_object",
            "max_tokens": 3000,
            "stream": True,
            "thinking": {"type": "disabled"},
            "deadline_seconds": deadline_seconds,
            "automatic_retries": 0,
        },
        "requests": {"planned": 4, "attempted": len(records)},
        "metrics": {
            "first_sse_event_count": len(event_values),
            "first_sse_event_p80_ms": percentile(event_values, 0.80),
            "first_reasoning_delta_count": len(reasoning_values),
            "first_reasoning_delta_p80_ms": percentile(reasoning_values, 0.80),
            "reasoning_only_stream_count": sum(
                item["reasoning_character_count"] > 0 and item["content_character_count"] == 0
                for item in records
            ),
            "first_content_delta_count": len(content_values),
            "first_content_delta_p80_ms": percentile(content_values, 0.80),
            "first_segment_gate_pass": {"numerator": len(ready_values), "denominator": 4},
            "first_meaningful_ready_p80_ms": ready_p80,
            "threshold_ms": 8000,
        },
        "call_results": records,
        "cost": "unverified; consult provider billing",
        "status": "pass" if passes else "fail",
        "decision_effect": "This diagnostic does not replace or overwrite the formal round-3 TS-03 failure.",
    }
    output_path = ROOT / "results" / f"model-{safe_model}-{run_label}.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result={output_path} status={result['status']} ready_p80_ms={ready_p80}", flush=True)
    return 0 if passes else 1


if __name__ == "__main__":
    raise SystemExit(main())
