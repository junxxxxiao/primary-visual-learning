#!/usr/bin/env python3
"""Serve the TS-04C browser harness and validate posted measurements."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
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
        if self.path != "/api/ts04c-browser-result":
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
        browser_run_label = payload.get("browser_run_label", "")
        if not re.fullmatch(r"[a-zA-Z0-9._-]+", browser_run_label):
            self.send_error(400)
            return
        results = [validate_candidate(candidate) for candidate in payload.get("candidates", [])]
        summary = {
            "slice_id": "TS-04C",
            "run_label": run_label,
            "browser_run_label": browser_run_label,
            "model_result_file": payload.get("model_result_file"),
            "candidate_count": len(results),
            "pass_count": sum(item["pass"] for item in results),
            "state_run_count": sum(len(item["runs"]) for item in results),
            "pass": bool(results) and all(item["pass"] for item in results),
            "results": results,
        }
        output = ROOT / "results" / f"browser-{run_label}-{browser_run_label}.json"
        output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        body = json.dumps(summary, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4184
    handler = lambda *args, **kwargs: Handler(*args, directory=str(REPO), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"http://127.0.0.1:{port}/spikes/ts-04c-real-visual-consistency/browser-harness.html", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
