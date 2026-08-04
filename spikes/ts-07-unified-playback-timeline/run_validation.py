#!/usr/bin/env python3
import hashlib
import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path


SLICE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SLICE_ROOT.parents[1]
RESULTS_ROOT = SLICE_ROOT / "results"
BASELINE_SHA = "4b91022b7ca933340477d3b55eba5f863593deaa"
CHROME_BINARY = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
APPROVED_BROWSER = "Google Chrome 150.0.7871.188"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values, percentile_value):
    ordered = sorted(values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * percentile_value
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def summarize(values):
    return {
        "count": len(values),
        "p50_ms": percentile(values, 0.5),
        "p80_ms": percentile(values, 0.8),
        "p95_ms": percentile(values, 0.95),
        "max_ms": max(values) if values else None,
    }


def almost_equal(left, right, tolerance=1e-6):
    return left is not None and right is not None and abs(left - right) <= tolerance


def parse_timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main():
    candidate = load_json(RESULTS_ROOT / "browser-candidate.json")
    fixture = load_json(SLICE_ROOT / "fixtures" / "audit-cues.json")
    self_test = load_json(RESULTS_ROOT / "harness-self-test.json")
    real_runs = candidate["raw"]["real_runs"]
    fallback_runs = candidate["raw"]["fallback_runs"]

    subtitle_errors = [
        item["deviation_ms"]
        for run in real_runs
        for item in run["subtitle_observations"]
    ]
    visual_errors = [
        item["deviation_ms"]
        for run in real_runs
        for item in run["visual_observations"]
    ]
    pause_errors = [run["pause_resume_error_ms"] for run in real_runs]
    seek_errors = [
        item["error_ms"]
        for run in real_runs
        for item in run["seek_observations"]
    ]
    fallback_errors = [run["handoff_error_ms"] for run in fallback_runs]

    independent_metrics = {
        "subtitle_cues": summarize(subtitle_errors),
        "visual_cues": summarize(visual_errors),
        "pause_resume": summarize(pause_errors),
        "seek": {
            **summarize(seek_errors),
            "final_error_ms": seek_errors[-1],
            "cumulative_drift_ms": seek_errors[-1] - seek_errors[0],
            "rendered_state_consistent": all(
                run["pause_state_stable"] and all(item["state_consistent"] for item in run["seek_observations"])
                for run in real_runs
            ),
        },
        "fallback_handoffs": {
            **summarize(fallback_errors),
            "monotonic": all(run["monotonic"] for run in fallback_runs),
            "state_rollback": any(run["state_rollback"] for run in fallback_runs),
        },
    }

    hash_paths = {
        "/prototype/sound-demo.html": REPO_ROOT / "prototype" / "sound-demo.html",
        "/prototype/assets/audio/narration-math-1.wav": REPO_ROOT / "prototype" / "assets" / "audio" / "narration-math-1.wav",
        "./fixtures/audit-cues.json": SLICE_ROOT / "fixtures" / "audit-cues.json",
        "./src/audit.js": SLICE_ROOT / "src" / "audit.js",
    }
    hash_checks = {
        key: candidate["hashes"].get(key) == sha256(path)
        for key, path in hash_paths.items()
    }
    metric_checks = {
        key: almost_equal(independent_metrics[key]["p95_ms"], candidate["metrics"][key]["p95_ms"])
        for key in ["subtitle_cues", "visual_cues", "pause_resume", "seek", "fallback_handoffs"]
    }
    thresholds = fixture["thresholds"]
    gates = {
        "subtitle_cue_p95_under_250ms": independent_metrics["subtitle_cues"]["p95_ms"] < thresholds["cue_p95_ms_exclusive"],
        "visual_cue_p95_under_250ms": independent_metrics["visual_cues"]["p95_ms"] < thresholds["cue_p95_ms_exclusive"],
        "pause_resume_p95_under_250ms": independent_metrics["pause_resume"]["p95_ms"] < thresholds["pause_resume_p95_ms_exclusive"],
        "seek_max_under_250ms": independent_metrics["seek"]["max_ms"] < thresholds["seek_final_error_ms_exclusive"],
        "seek_state_consistent": independent_metrics["seek"]["rendered_state_consistent"],
        "fallback_handoff_p95_under_250ms": independent_metrics["fallback_handoffs"]["p95_ms"] < thresholds["handoff_error_ms_exclusive"],
        "fallback_monotonic": independent_metrics["fallback_handoffs"]["monotonic"],
        "fallback_no_state_rollback": not independent_metrics["fallback_handoffs"]["state_rollback"],
    }
    expected_violations = {
        "fallback.handoff_error_exceeded",
        "fallback.not_monotonic",
        "fallback.state_rollback",
    }
    browser_version = subprocess.run(
        [str(CHROME_BINARY), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    structural_checks = {
        "result_version": candidate.get("result_version") == "ts-07-browser-audit/1.0",
        "candidate_output": candidate.get("evidence_kind") == "candidate_output",
        "real_run_count": len(real_runs) == 5,
        "fallback_run_count": len(fallback_runs) == 5,
        "subtitle_observation_count": len(subtitle_errors) == 25,
        "visual_observation_count": len(visual_errors) == 10,
        "seek_observation_count": len(seek_errors) == 50,
        "one_error_per_fallback": all(run["error_count"] == 1 for run in fallback_runs),
        "zero_external_usage": candidate["candidate"]["external_requests"] == 0
        and candidate["candidate"]["tokens_or_equivalent"] == 0
        and candidate["candidate"]["cost_cny"] == 0,
        "harness_self_test": self_test.get("pass") is True and self_test.get("candidate_denominator") is False,
        "candidate_violation_set": set(candidate["violation_codes"]) == expected_violations,
        "candidate_pass_false": candidate.get("pass") is False,
        "approved_browser_matches_executable": candidate["candidate"]["approved_browser"] == APPROVED_BROWSER
        and browser_version == APPROVED_BROWSER,
    }
    head_contains_baseline = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_SHA, "HEAD"],
        cwd=REPO_ROOT,
        check=False,
    ).returncode == 0
    validation_pass = all(hash_checks.values()) and all(metric_checks.values()) and all(structural_checks.values()) and head_contains_baseline
    candidate_gate_pass = all(gates.values())

    started_at = parse_timestamp(candidate["started_at"])
    completed_at = parse_timestamp(candidate["completed_at"])
    duration_ms = (completed_at - started_at).total_seconds() * 1000
    timing = {
        "schema_version": "stage-timing/1.0",
        "trace_id": "ts07-chrome-candidate-20260804",
        "slice_id": "TS-07",
        "clock": "monotonic",
        "trace_started_at": candidate["started_at"],
        "milestones": [
            {"name": "timeline.audit_started", "offset_ms": 0, "latency_scope": "diagnostic"},
            {"name": "timeline.audit_completed", "offset_ms": duration_ms, "latency_scope": "diagnostic"},
        ],
        "spans": [
            {
                "span_id": "timeline.audit",
                "parent_span_id": None,
                "stage": "timeline.audit",
                "started_offset_ms": 0,
                "ended_offset_ms": duration_ms,
                "duration_ms": duration_ms,
                "latency_scope": "system_work",
                "outcome": "failure",
                "retry_index": 0,
                "cache_status": "not_applicable",
                "provider": "local_google_chrome",
                "model": None,
                "input_units": 10,
                "output_units": len(subtitle_errors) + len(visual_errors) + len(pause_errors) + len(seek_errors) + len(fallback_errors),
                "cost_amount": 0,
                "cost_currency": "CNY",
                "error_code": "fallback.handoff_error_exceeded",
            }
        ],
    }
    summary = {
        "slice_id": "TS-07",
        "status": "candidate_run_complete",
        "baseline_sha": BASELINE_SHA,
        "head_contains_baseline": head_contains_baseline,
        "candidate": candidate["candidate"],
        "fixture_version": fixture["fixture_version"],
        "environment": {
            "platform": platform.platform(),
            "browser": candidate["candidate"]["approved_browser"],
            "browser_executable_version": browser_version,
            "browser_user_agent": candidate["candidate"]["browser_user_agent"],
            "local_http": True,
        },
        "sample_counts": {
            "warmup_runs": 1,
            "real_audio_runs": len(real_runs),
            "fallback_runs": len(fallback_runs),
            "subtitle_cues": len(subtitle_errors),
            "visual_cues": len(visual_errors),
            "pause_resume": len(pause_errors),
            "seek_operations": len(seek_errors),
            "fallback_handoffs": len(fallback_errors),
        },
        "metrics": independent_metrics,
        "gates": gates,
        "violation_codes": sorted(expected_violations),
        "hash_checks": hash_checks,
        "metric_recalculation_checks": metric_checks,
        "structural_checks": structural_checks,
        "validation_pass": validation_pass,
        "candidate_gate_pass": candidate_gate_pass,
        "cost": {"amount": 0, "currency": "CNY", "external_services": False},
        "verified": [
            "existing Chrome Demo real-audio cue synchronization for the fixed math segment",
            "pause and resume continuity for the fixed math segment",
            "ten repeated seeks per run across five measured runs",
            "existing media-error fallback behavior across five measured runs",
        ],
        "unverified": [
            "Safari and WeChat WebView",
            "real phones and low-end devices",
            "background throttling and network buffering",
            "long lessons and production session isolation",
            "generated visual scenes from TS-04C",
        ],
    }
    write_json(RESULTS_ROOT / "timing.json", timing)
    write_json(RESULTS_ROOT / "summary.json", summary)
    print(json.dumps({
        "validation_pass": validation_pass,
        "candidate_gate_pass": candidate_gate_pass,
        "status": summary["status"],
        "violation_codes": summary["violation_codes"],
    }, ensure_ascii=False, indent=2))
    if not validation_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
