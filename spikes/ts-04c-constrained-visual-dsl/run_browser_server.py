#!/usr/bin/env python3
"""Serve the TS-04C-v2 DSL harness and validate posted measurements."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
VALIDATOR_PATH = ROOT.parent / "ts-04b-visual-scene-gate" / "src" / "validator.py"


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("ts04c_browser_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load TS-04B validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator()
REVIEW_RUN_LABEL = "official-dsl-calibration-round-1"
REVIEW_ROLES = {"subject_matter", "product_visual"}
REVIEW_VALUES = {"pass", "fail"}


def validate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    violations = []
    runs = candidate.get("runs", [])
    if len(runs) != 16:
        violations.append({"code": "browser.missing_runs", "actual": len(runs), "expected": 16})
    for run in runs:
        target = f"{run.get('viewport')}.{run.get('state_id')}"
        if run.get("status") != "completed":
            violations.append({"code": "browser.sandbox_failure", "target": target, "actual": run.get("reason")})
        if not run.get("render_complete"):
            violations.append({"code": "browser.render_complete_missing", "target": target})
        if not run.get("layout_measurement"):
            violations.append({"code": "browser.layout_measurement_missing", "target": target})
        if run.get("rendered_content_count") != run.get("expected_content_count"):
            violations.append({
                "code": "browser.dsl_content_missing",
                "target": target,
                "actual": run.get("rendered_content_count"),
                "expected": run.get("expected_content_count"),
            })
        stats = run.get("render_stats") or {}
        if stats.get("opaque_samples", 0) == 0 or stats.get("quantized_color_count", 0) < 2:
            violations.append({"code": "browser.blank_canvas", "target": target, "actual": stats})

    scene = candidate.get("scene_declaration", {})
    try:
        violations.extend(VALIDATOR.validate_scene_structure(scene))
        if not violations:
            violations.extend(VALIDATOR.validate_teaching(scene)["violations"])
            for viewport, profile in scene["viewport_profiles"].items():
                for state in profile["states"]:
                    violations.extend(VALIDATOR.validate_visual_scene(scene, viewport, state["state_id"])["violations"])
    except (AttributeError, KeyError, StopIteration, TypeError) as exc:
        violations.append({"code": "browser.declaration_exception", "actual": type(exc).__name__, "message": str(exc)})
    return {
        "sample_id": candidate.get("sample_id"),
        "pass": not violations,
        "violation_codes": sorted({item["code"] for item in violations}),
        "violations": violations,
        "runs": runs,
        "scene_declaration": scene,
    }


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path == "/api/ts04c-v2-human-review":
            self.handle_human_review()
            return
        if self.path != "/api/ts04c-v2-browser-result":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 20_000_000:
            self.send_error(413)
            return
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        run_label = payload.get("run_label", "")
        if not re.fullmatch(r"[a-zA-Z0-9._-]+", run_label):
            self.send_error(400)
            return
        fixture_kind = payload.get("fixture_kind")
        if fixture_kind not in {"gold_fixture", "candidate_output"}:
            self.send_error(400)
            return
        results = [validate_candidate(candidate) for candidate in payload.get("candidates", [])]
        summary = {
            "slice_id": "TS-04C-v2",
            "run_label": run_label,
            "fixture_kind": fixture_kind,
            "candidate_count": len(results),
            "pass_count": sum(item["pass"] for item in results),
            "state_run_count": sum(len(item["runs"]) for item in results),
            "pass": bool(results) and all(item["pass"] for item in results),
            "results": results,
        }
        output = ROOT / "results" / f"browser-{run_label}.json"
        output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        body = json.dumps(summary, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_human_review(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 500_000:
            self.send_error(413)
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            candidate_file = ROOT / "results" / "candidate-specs-official-dsl-calibration-round-1.json"
            candidates = json.loads(candidate_file.read_text(encoding="utf-8"))
            expected_ids = {entry["spec"]["sample_id"] for entry in candidates["specs"]}
            run_label = payload.get("run_label")
            reviewer_role = payload.get("reviewer_role")
            reviewer_alias = payload.get("reviewer_alias", "")
            reviews = payload.get("reviews")
            if run_label != REVIEW_RUN_LABEL:
                raise ValueError("unexpected run label")
            if reviewer_role not in REVIEW_ROLES:
                raise ValueError("unexpected reviewer role")
            if not re.fullmatch(r"[a-zA-Z0-9._-]{1,40}", reviewer_alias):
                raise ValueError("reviewer alias must use 1-40 ASCII letters, numbers, dots, underscores or hyphens")
            if not isinstance(reviews, list) or len(reviews) != len(expected_ids):
                raise ValueError("all ten samples must be reviewed")
            if {item.get("sample_id") for item in reviews} != expected_ids:
                raise ValueError("review sample ids do not match the candidate fixture")
            required_states = {"initial", "key_process", "final", "paused", "resumed", "post_interaction", "reduced_motion", "static_fallback"}
            for item in reviews:
                if any(item.get(field) not in REVIEW_VALUES for field in ("teaching", "visual", "state_integrity")):
                    raise ValueError("each review dimension must be pass or fail")
                if item.get("visited_states") is None or set(item["visited_states"]) != required_states:
                    raise ValueError("all eight states must be visited for every sample")
                if not isinstance(item.get("critical_error"), bool):
                    raise ValueError("critical_error must be boolean")
                if not isinstance(item.get("notes", ""), str) or len(item.get("notes", "")) > 1000:
                    raise ValueError("notes must be at most 1000 characters")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.send_error(400, str(exc))
            return

        normalized = []
        for item in reviews:
            passed = (
                item["teaching"] == "pass"
                and item["visual"] == "pass"
                and item["state_integrity"] == "pass"
                and not item["critical_error"]
            )
            normalized.append({
                "sample_id": item["sample_id"],
                "teaching": item["teaching"],
                "visual": item["visual"],
                "state_integrity": item["state_integrity"],
                "critical_error": item["critical_error"],
                "visited_states": sorted(item["visited_states"]),
                "notes": item.get("notes", "").strip(),
                "pass": passed,
            })
        pass_count = sum(item["pass"] for item in normalized)
        critical_count = sum(item["critical_error"] for item in normalized)
        submitted_at = datetime.now(timezone.utc).isoformat()
        timestamp = re.sub(r"[^0-9]", "", submitted_at)[:14]
        result = {
            "slice_id": "TS-04C-v2",
            "run_label": run_label,
            "artifact_kind": "independent_human_review",
            "reviewer_role": reviewer_role,
            "reviewer_alias": reviewer_alias,
            "submitted_at": submitted_at,
            "sample_count": len(normalized),
            "pass_count": pass_count,
            "critical_error_count": critical_count,
            "threshold": {"minimum_pass_count": 9, "maximum_critical_error_count": 0},
            "threshold_pass": pass_count >= 9 and critical_count == 0,
            "status": "human_review_submitted",
            "reviews": normalized,
            "limits": [
                "One submitted review does not by itself advance the slice status.",
                "Subject-matter and product/visual review artifacts must be assessed together.",
            ],
        }
        output = ROOT / "results" / f"human-review-{run_label}-{reviewer_role}-{reviewer_alias}-{timestamp}.json"
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        response = {
            "saved": True,
            "result_file": output.name,
            "pass_count": pass_count,
            "critical_error_count": critical_count,
            "threshold_pass": result["threshold_pass"],
        }
        body = json.dumps(response, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4185
    handler = lambda *args, **kwargs: Handler(*args, directory=str(REPO), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"http://127.0.0.1:{port}/spikes/ts-04c-constrained-visual-dsl/browser-harness.html", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
