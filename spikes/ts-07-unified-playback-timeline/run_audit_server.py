#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SLICE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SLICE_ROOT.parents[1]
sys.path.insert(0, str(REPO_ROOT / "spikes" / "shared"))

from candidate_evidence_gate import canonical_sha256, validate_candidate_evidence  # noqa: E402


MANIFEST_PATH = SLICE_ROOT / "candidate-manifest.json"
AUTHORIZATION_PATH = SLICE_ROOT / "candidate-authorization.json"
RUN_PATH = SLICE_ROOT / "candidate-run.json"
RESULT_TARGETS = {
    "/__ts07_result__": (SLICE_ROOT / "results" / "browser-candidate.json", "ts-07-browser-audit/1.0"),
    "/__ts07_fallback_retest__": (SLICE_ROOT / "results" / "browser-fallback-retest.json", "ts-07-browser-audit/1.0"),
    "/__ts07_shared_smoke__": (SLICE_ROOT / "results" / "browser-shared-smoke.json", "ts-07-shared-smoke/1.0"),
}
MAX_RESULT_BYTES = 2 * 1024 * 1024


class AuditHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        result_target = RESULT_TARGETS.get(self.path)
        if result_target is None:
            self.send_error(404)
            return
        result_path, expected_version = result_target
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return
        if content_length <= 0 or content_length > MAX_RESULT_BYTES:
            self.send_error(413, "Invalid result size")
            return
        try:
            payload = json.loads(self.rfile.read(content_length))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error(400, "Invalid JSON")
            return
        if payload.get("result_version") != expected_version:
            self.send_error(422, "Unexpected result version")
            return
        result_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = result_path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(result_path)
        if self.path == "/__ts07_fallback_retest__":
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            result_hash = f"sha256:{hashlib.sha256(result_path.read_bytes()).hexdigest()}"
            RUN_PATH.write_text(json.dumps({
                "schema_version": "candidate-run/1.0",
                "slice_id": manifest["slice_id"],
                "manifest_sha256": canonical_sha256(manifest),
                "state": "candidate_run_complete",
                "started_at": payload["started_at"],
                "completed_at": payload["completed_at"],
                "result_path": manifest["result_path"],
                "result_sha256": result_hash,
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        body = b'{"saved":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="Serve and persist the TS-07 browser audit")
    parser.add_argument("--port", type=int, default=4197)
    args = parser.parse_args()
    violations = validate_candidate_evidence(
        repo_root=REPO_ROOT,
        manifest_path=MANIFEST_PATH,
        authorization_path=AUTHORIZATION_PATH,
        required_stage="preflight",
    )
    if violations:
        print(json.dumps({"stage": "preflight", "pass": False, "violations": violations}, indent=2), flush=True)
        raise SystemExit(2)
    os.chdir(REPO_ROOT)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), AuditHandler)
    print(f"TS-07 audit server: http://127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
