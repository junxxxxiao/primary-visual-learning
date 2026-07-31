#!/usr/bin/env python3
"""Serve and persist TS-04C-v3 trusted-renderer browser measurements."""
from __future__ import annotations

import json
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
STATES = {"initial", "key_process", "final", "paused", "resumed", "post_interaction", "reduced_motion", "static_fallback"}
VIEWPORTS = {"phone", "tablet"}
PROFILES = {
    "v02-repaired": {"run_label": "v4-flash-v02-repaired-browser-round-1", "schema_version": "open-visual-scene/0.2"},
    "v03-example-guided": {"run_label": "v4-flash-v03-example-guided-browser-round-1", "schema_version": "open-visual-scene/0.3"},
}


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/api/ts04c-v3-browser-result":
            self.send_error(404); return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 20_000_000:
            self.send_error(413); return
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        profile_key = payload.get("profile_key", "v02-repaired")
        profile = PROFILES.get(profile_key)
        if profile is None:
            self.send_error(400); return
        run_label = payload.get("run_label", "")
        if not re.fullmatch(r"[a-zA-Z0-9._-]+", run_label):
            self.send_error(400); return
        if run_label != profile["run_label"] or payload.get("schema_version") != profile["schema_version"]:
            self.send_error(400); return
        results = []
        for candidate in payload.get("candidates", []):
            violations = []
            runs = candidate.get("runs", [])
            expected = {(viewport, state) for viewport in VIEWPORTS for state in STATES}
            actual = {(run.get("viewport"), run.get("state_id")) for run in runs}
            if len(runs) != 16 or actual != expected:
                violations.append({"code": "browser.missing_state_runs", "actual": len(runs)})
            for run in runs:
                target = f"{run.get('viewport')}.{run.get('state_id')}"
                if run.get("rendered_element_count", 0) < 1:
                    violations.append({"code": "browser.empty_scene", "target": target})
                if run.get("pixel_stats", {}).get("non_background_samples", 0) < 20:
                    violations.append({"code": "browser.blank_canvas", "target": target, "actual": run.get("pixel_stats")})
                if run.get("pixel_stats", {}).get("quantized_color_count", 0) < 2:
                    violations.append({"code": "browser.single_color_canvas", "target": target})
                if run.get("logical_violations"):
                    violations.append({"code": "browser.logical_bounds", "target": target, "actual": run["logical_violations"]})
                if run.get("screen_violations"):
                    violations.append({"code": "browser.screen_bounds", "target": target, "actual": run["screen_violations"]})
                canvas = run.get("canvas", {})
                if canvas.get("width", 0) <= 0 or canvas.get("height", 0) <= 0:
                    violations.append({"code": "browser.invalid_canvas", "target": target})
            results.append({"sample_id": candidate.get("sample_id"), "source_attempt": candidate.get("source_attempt"), "pass": not violations, "violation_codes": sorted({item["code"] for item in violations}), "violations": violations, "runs": runs})
        summary = {
            "slice_id": "TS-04C-v3", "run_label": run_label, "profile_key": profile_key,
            "model": "deepseek-v4-flash", "schema_version": profile["schema_version"], "prompt_profile": payload.get("prompt_profile"),
            "candidate_count": len(results), "pass_count": sum(item["pass"] for item in results),
            "state_run_count": sum(len(item["runs"]) for item in results), "pass": len(results) == 10 and all(item["pass"] for item in results), "results": results
        }
        output = ROOT / "results" / f"browser-{run_label}.json"
        output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        body = json.dumps(summary, ensure_ascii=False).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4186
    handler = lambda *args, **kwargs: Handler(*args, directory=str(REPO), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"http://127.0.0.1:{port}/spikes/ts-04c-open-world-visual-generation/browser-harness.html", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
