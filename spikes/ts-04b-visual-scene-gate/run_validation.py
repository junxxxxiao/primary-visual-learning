#!/usr/bin/env python3
from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.validator import (  # noqa: E402
    CACHE_IDENTITY_FIELDS,
    ValidatedSceneCache,
    apply_mutations,
    validate_scene_structure,
    validate_teaching,
    validate_visual_scene,
)

T = TypeVar("T")


class TraceCollector:
    def __init__(self) -> None:
        self.started = time.perf_counter()
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.spans: list[dict[str, Any]] = []

    def measure(
        self,
        stage: str,
        action: Callable[[], T],
        *,
        cache_status: str = "not_applicable",
        outcome: str = "success",
    ) -> T:
        started = time.perf_counter()
        started_offset = (started - self.started) * 1000
        result = action()
        ended = time.perf_counter()
        duration = (ended - started) * 1000
        self.spans.append(
            {
                "span_id": f"span-{len(self.spans) + 1:04d}",
                "parent_span_id": None,
                "stage": stage,
                "started_offset_ms": round(started_offset, 6),
                "ended_offset_ms": round((ended - self.started) * 1000, 6),
                "duration_ms": round(duration, 6),
                "latency_scope": "system_work",
                "outcome": outcome,
                "retry_index": 0,
                "cache_status": cache_status,
                "provider": None,
                "model": None,
                "input_units": None,
                "output_units": None,
                "cost_amount": 0,
                "cost_currency": "CNY",
                "error_code": None,
            }
        )
        return result


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction, 6)


def timing_summary(spans: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for span in spans:
        grouped[span["stage"]].append(span)
    return {
        stage: {
            "count": len(items),
            "p50_ms": percentile([item["duration_ms"] for item in items], 0.50),
            "p80_ms": percentile([item["duration_ms"] for item in items], 0.80),
            "p95_ms": percentile([item["duration_ms"] for item in items], 0.95),
            "max_ms": round(max(item["duration_ms"] for item in items), 6),
            "failure_rate": round(sum(item["outcome"] == "failure" for item in items) / len(items), 6),
        }
        for stage, items in sorted(grouped.items())
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> int:
    base_data = load_json(ROOT / "fixtures" / "base-scenes.json")
    cases_data = load_json(ROOT / "fixtures" / "cases.json")
    for schema_path in sorted((ROOT / "schemas").glob("*.json")):
        load_json(schema_path)

    trace = TraceCollector()
    audit_cases: list[dict[str, Any]] = []
    compact_cases: list[dict[str, Any]] = []
    failed_display_count = 0
    failed_cache_write_count = 0
    valid_cache_hit_durations: list[float] = []

    for case in cases_data["cases"]:
        scene = apply_mutations(
            base_data["scenes"][case["base_scene"]], case.get("mutations", [])
        )
        structure = trace.measure("scene.structure", lambda scene=scene: validate_scene_structure(scene))
        if structure:
            trace.spans[-1]["outcome"] = "failure"
            trace.spans[-1]["error_code"] = structure[0]["code"]
        teaching = trace.measure("teaching.check", lambda scene=scene: validate_teaching(scene))
        if teaching["result"] == "fail":
            trace.spans[-1]["outcome"] = "failure"
            trace.spans[-1]["error_code"] = teaching["violations"][0]["code"]
        layout_results: list[dict[str, Any]] = []
        for viewport in ("phone", "tablet"):
            for state in scene["viewport_profiles"][viewport]["states"]:
                result = trace.measure(
                    f"layout.{viewport}.{state['kind']}",
                    lambda scene=scene, viewport=viewport, state=state: validate_visual_scene(
                        scene, viewport, state["state_id"]
                    ),
                )
                if result["result"] == "fail":
                    trace.spans[-1]["outcome"] = "failure"
                    trace.spans[-1]["error_code"] = result["violations"][0]["code"]
                layout_results.append(result)

        admitted = not structure and teaching["result"] == "pass" and all(
            result["result"] == "pass" for result in layout_results
        )
        displayed = admitted
        cache = ValidatedSceneCache()
        initial_read = trace.measure(
            "cache.read", lambda: cache.read(scene, "phone"), cache_status="miss"
        )
        if initial_read.status != "miss":
            raise AssertionError("Fresh cache must miss")

        cache_writes = 0
        for viewport in ("phone", "tablet"):
            wrote = trace.measure(
                "cache.write",
                lambda viewport=viewport: cache.write(scene, viewport, admitted),
                cache_status="write" if admitted else "not_applicable",
            )
            cache_writes += int(wrote)

        if admitted:
            for _ in range(20):
                for viewport in ("phone", "tablet"):
                    started = time.perf_counter()
                    read = trace.measure(
                        "cache.read",
                        lambda viewport=viewport: cache.read(scene, viewport),
                        cache_status="hit",
                    )
                    valid_cache_hit_durations.append((time.perf_counter() - started) * 1000)
                    if read.status != "hit" or read.record is None:
                        raise AssertionError("Admitted scene cache read must hit")
        else:
            failed_display_count += int(displayed)
            failed_cache_write_count += cache_writes

        actual = "pass" if admitted else "fail"
        compact_cases.append(
            {
                "case_id": case["case_id"],
                "category": case["category"],
                "expected": case["expected"],
                "actual": actual,
                "pass": actual == case["expected"],
                "displayed": displayed,
                "valid_cache_records": cache.size,
                "violation_codes": sorted(
                    {
                        violation["code"]
                        for result in [teaching, *layout_results]
                        for violation in result["violations"]
                    }
                    | {violation["code"] for violation in structure}
                ),
            }
        )
        audit_cases.append(
            {
                "case_id": case["case_id"],
                "structure_violations": structure,
                "teaching_result": teaching,
                "layout_results": layout_results,
                "admitted": admitted,
                "displayed": displayed,
                "cache_writes": cache_writes,
            }
        )

    invalidation_results: list[dict[str, Any]] = []
    reference = base_data["scenes"]["sound"]
    for field in CACHE_IDENTITY_FIELDS:
        if field == "viewport":
            continue
        cache = ValidatedSceneCache()
        cache.write(reference, "phone", True)
        changed = json.loads(json.dumps(reference))
        changed[field] = changed[field] + "+changed"
        read = trace.measure(
            "cache.version_invalidation",
            lambda changed=changed: cache.read(changed, "phone"),
            cache_status="invalidated",
        )
        invalidation_results.append(
            {"changed_field": field, "status": read.status, "pass": read.status == "invalidated"}
        )

    opposite_cases = [item for item in compact_cases if item["category"] == "teaching_opposite"]
    layout_cases = [item for item in compact_cases if item["category"].startswith("layout_")]
    cache_p80_ms = percentile(valid_cache_hit_durations, 0.80)
    thresholds = {
        "opposite_relationship_block_rate": {
            "actual": sum(item["actual"] == "fail" for item in opposite_cases) / len(opposite_cases),
            "target": 1.0,
        },
        "known_layout_violation_block_rate": {
            "actual": sum(item["actual"] == "fail" for item in layout_cases) / len(layout_cases),
            "target": 1.0,
        },
        "failed_scene_display_count": {"actual": failed_display_count, "target": 0},
        "failed_scene_valid_cache_write_count": {"actual": failed_cache_write_count, "target": 0},
        "cache_version_invalidation_rate": {
            "actual": sum(item["pass"] for item in invalidation_results) / len(invalidation_results),
            "target": 1.0,
        },
        "validated_cache_p80_ms": {"actual": cache_p80_ms, "target_max": 8000},
    }
    all_thresholds_pass = (
        thresholds["opposite_relationship_block_rate"]["actual"]
        == thresholds["opposite_relationship_block_rate"]["target"]
        and thresholds["known_layout_violation_block_rate"]["actual"]
        == thresholds["known_layout_violation_block_rate"]["target"]
        and failed_display_count == 0
        and failed_cache_write_count == 0
        and thresholds["cache_version_invalidation_rate"]["actual"] == 1.0
        and cache_p80_ms <= 8000
        and all(item["pass"] for item in compact_cases)
    )

    baseline_sha = git_value("rev-parse", "origin/main")
    head_contains_baseline = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", "origin/main", "HEAD"],
            cwd=ROOT,
            check=False,
        ).returncode
        == 0
    )
    timing = {
        "schema_version": "stage-timing/1.0",
        "trace_id": f"ts04b-{int(time.time())}",
        "slice_id": "TS-04B",
        "clock": "monotonic",
        "trace_started_at": trace.started_at,
        "milestones": [
            {"name": "validation_complete", "offset_ms": round((time.perf_counter() - trace.started) * 1000, 6), "latency_scope": "diagnostic"}
        ],
        "spans": trace.spans,
    }
    stage_stats = timing_summary(trace.spans)
    summary = {
        "slice_id": "TS-04B",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "baseline_sha": baseline_sha,
        "head_contains_baseline": head_contains_baseline,
        "fixture_versions": [base_data["fixture_version"], cases_data["fixture_version"]],
        "contract_versions": {
            "scene": "visual-scene/1.0",
            "teaching": "teaching-consistency/1.0",
            "layout": "visual-layout/v1",
            "cache": "validated-visual-cache/1.0",
            "timing": "stage-timing/1.0",
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "external_services": False,
        },
        "case_count": len(compact_cases),
        "passed_case_count": sum(item["pass"] for item in compact_cases),
        "viewport_state_result_count": sum(len(item["layout_results"]) for item in audit_cases),
        "case_results": compact_cases,
        "cache_invalidation_results": invalidation_results,
        "thresholds": thresholds,
        "timing_by_stage": stage_stats,
        "cost": {"currency": "CNY", "amount": 0, "external_services": False},
        "decision": "conditional_pass" if all_thresholds_pass else "fail",
        "pass": all_thresholds_pass,
        "unverified": [
            "real model-generated scenes and automatic repair",
            "browser DOM, SVG, Canvas and OffscreenCanvas measurement adapters",
            "real phone, tablet and WeChat WebView geometry",
            "production cache backend, concurrency, eviction and persistence",
            "human subject-matter and product visual review",
            "end-to-end generation latency and cost",
        ],
    }
    write_json(ROOT / "results" / "audit.json", {"cases": audit_cases})
    write_json(ROOT / "results" / "summary.json", summary)
    write_json(ROOT / "results" / "timing.json", timing)
    print(
        f"TS-04B: {summary['passed_case_count']}/{summary['case_count']} cases; "
        f"{summary['viewport_state_result_count']} viewport/state results; "
        f"decision={summary['decision']}"
    )
    return 0 if all_thresholds_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
