from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from candidate_evidence_gate import (  # noqa: E402
    canonical_sha256,
    validate_candidate_evidence,
    validate_repository_candidate_evidence,
)


def file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


class CandidateEvidenceGateTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, Path]]:
        temporary = tempfile.TemporaryDirectory()
        repo_root = Path(temporary.name)
        slice_root = repo_root / "spikes" / "ts-test"
        result_root = slice_root / "results"
        input_path = repo_root / "fixtures" / "candidate.wav"
        input_path.parent.mkdir(parents=True)
        result_root.mkdir(parents=True)
        input_path.write_bytes(b"candidate-input-v1")

        manifest = {
            "schema_version": "candidate-manifest/1.0",
            "slice_id": "TS-test",
            "candidate": {
                "subject": "test candidate",
                "supplier": "local",
                "version": "1.0",
                "invocation": "local deterministic test",
                "fixed_parameters": {"runs": 1},
            },
            "budget": {"external_requests": 0, "tokens": 0, "cost_cny": 0},
            "data_boundary": {"classification": "synthetic", "contains_child_data": False},
            "inputs": [
                {
                    "id": "candidate_audio",
                    "path": "fixtures/candidate.wav",
                    "sha256": file_sha256(input_path),
                    "result_hash_key": "/fixtures/candidate.wav",
                }
            ],
            "result_path": "spikes/ts-test/results/candidate.json",
        }
        manifest_path = slice_root / "candidate-manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        manifest_hash = canonical_sha256(manifest)

        authorization = {
            "schema_version": "candidate-authorization/1.0",
            "slice_id": "TS-test",
            "manifest_sha256": manifest_hash,
            "decision": "approved",
            "authorized_by": "reviewer",
            "authorized_at": "2026-08-04T10:00:00Z",
            "evidence": "test approval",
        }
        authorization_path = slice_root / "candidate-authorization.json"
        authorization_path.write_text(json.dumps(authorization), encoding="utf-8")

        result = {
            "result_version": "test/1.0",
            "evidence_kind": "candidate_output",
            "started_at": "2026-08-04T10:01:00Z",
            "completed_at": "2026-08-04T10:02:00Z",
            "hashes": {"/fixtures/candidate.wav": file_sha256(input_path).removeprefix("sha256:")},
            "pass": True,
        }
        result_path = result_root / "candidate.json"
        result_path.write_text(json.dumps(result), encoding="utf-8")
        result_hash = file_sha256(result_path)

        run = {
            "schema_version": "candidate-run/1.0",
            "slice_id": "TS-test",
            "manifest_sha256": manifest_hash,
            "state": "candidate_run_complete",
            "started_at": result["started_at"],
            "completed_at": result["completed_at"],
            "result_path": manifest["result_path"],
            "result_sha256": result_hash,
        }
        run_path = slice_root / "candidate-run.json"
        run_path.write_text(json.dumps(run), encoding="utf-8")

        review = {
            "schema_version": "candidate-human-review/1.0",
            "slice_id": "TS-test",
            "manifest_sha256": manifest_hash,
            "result_sha256": result_hash,
            "reviewed_at": "2026-08-04T10:03:00Z",
            "reviewer": "reviewer",
            "decision": "conditional_pass",
            "evidence": "test review",
        }
        review_path = slice_root / "candidate-human-review.json"
        review_path.write_text(json.dumps(review), encoding="utf-8")
        return temporary, repo_root, {
            "manifest": manifest_path,
            "authorization": authorization_path,
            "run": run_path,
            "review": review_path,
            "input": input_path,
        }

    def validate(self, repo_root: Path, paths: dict[str, Path], stage: str) -> set[str]:
        violations = validate_candidate_evidence(
            repo_root=repo_root,
            manifest_path=paths["manifest"],
            authorization_path=paths["authorization"],
            run_path=paths["run"],
            review_path=paths["review"],
            required_stage=stage,
        )
        return {item["code"] for item in violations}

    def test_matching_evidence_passes_release_gate(self) -> None:
        temporary, repo_root, paths = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.assertEqual(self.validate(repo_root, paths, "release"), set())

    def test_changed_candidate_input_is_rejected_before_run(self) -> None:
        temporary, repo_root, paths = self.fixture()
        self.addCleanup(temporary.cleanup)
        paths["input"].write_bytes(b"candidate-input-v2")
        self.assertIn("CANDIDATE_INPUT_HASH_MISMATCH", self.validate(repo_root, paths, "preflight"))

    def test_manifest_change_invalidates_old_authorization(self) -> None:
        temporary, repo_root, paths = self.fixture()
        self.addCleanup(temporary.cleanup)
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        manifest["candidate"]["fixed_parameters"]["runs"] = 2
        paths["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
        self.assertIn("AUTHORIZATION_MANIFEST_HASH_MISMATCH", self.validate(repo_root, paths, "preflight"))

    def test_manifest_without_budget_is_rejected_even_when_authorized(self) -> None:
        temporary, repo_root, paths = self.fixture()
        self.addCleanup(temporary.cleanup)
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        del manifest["budget"]
        paths["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
        authorization = json.loads(paths["authorization"].read_text(encoding="utf-8"))
        authorization["manifest_sha256"] = canonical_sha256(manifest)
        paths["authorization"].write_text(json.dumps(authorization), encoding="utf-8")
        self.assertIn("CANDIDATE_MANIFEST_INVALID", self.validate(repo_root, paths, "preflight"))

    def test_manifest_with_negative_budget_is_rejected(self) -> None:
        temporary, repo_root, paths = self.fixture()
        self.addCleanup(temporary.cleanup)
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        manifest["budget"]["cost_cny"] = -1
        paths["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
        authorization = json.loads(paths["authorization"].read_text(encoding="utf-8"))
        authorization["manifest_sha256"] = canonical_sha256(manifest)
        paths["authorization"].write_text(json.dumps(authorization), encoding="utf-8")
        self.assertIn("CANDIDATE_MANIFEST_INVALID", self.validate(repo_root, paths, "preflight"))

    def test_approval_without_named_authorizer_is_rejected(self) -> None:
        temporary, repo_root, paths = self.fixture()
        self.addCleanup(temporary.cleanup)
        authorization = json.loads(paths["authorization"].read_text(encoding="utf-8"))
        authorization["authorized_by"] = ""
        paths["authorization"].write_text(json.dumps(authorization), encoding="utf-8")
        self.assertIn("CANDIDATE_AUTHORIZATION_INVALID", self.validate(repo_root, paths, "preflight"))

    def test_candidate_run_before_authorization_is_rejected(self) -> None:
        temporary, repo_root, paths = self.fixture()
        self.addCleanup(temporary.cleanup)
        authorization = json.loads(paths["authorization"].read_text(encoding="utf-8"))
        authorization["authorized_at"] = "2026-08-04T10:01:30Z"
        paths["authorization"].write_text(json.dumps(authorization), encoding="utf-8")
        self.assertIn("CANDIDATE_RUN_PRECEDES_AUTHORIZATION", self.validate(repo_root, paths, "candidate"))

    def test_human_review_before_candidate_completion_is_rejected(self) -> None:
        temporary, repo_root, paths = self.fixture()
        self.addCleanup(temporary.cleanup)
        review = json.loads(paths["review"].read_text(encoding="utf-8"))
        review["reviewed_at"] = "2026-08-04T10:01:30Z"
        paths["review"].write_text(json.dumps(review), encoding="utf-8")
        self.assertIn("HUMAN_REVIEW_PRECEDES_CANDIDATE", self.validate(repo_root, paths, "release"))

    def test_run_with_unknown_schema_version_is_rejected(self) -> None:
        temporary, repo_root, paths = self.fixture()
        self.addCleanup(temporary.cleanup)
        run = json.loads(paths["run"].read_text(encoding="utf-8"))
        run["schema_version"] = "candidate-run/9.0"
        paths["run"].write_text(json.dumps(run), encoding="utf-8")
        self.assertIn("CANDIDATE_RUN_RECORD_INVALID", self.validate(repo_root, paths, "candidate"))

    def test_review_without_reviewer_is_rejected(self) -> None:
        temporary, repo_root, paths = self.fixture()
        self.addCleanup(temporary.cleanup)
        review = json.loads(paths["review"].read_text(encoding="utf-8"))
        review["reviewer"] = ""
        paths["review"].write_text(json.dumps(review), encoding="utf-8")
        self.assertIn("HUMAN_REVIEW_RECORD_INVALID", self.validate(repo_root, paths, "release"))

    def test_changed_candidate_result_invalidates_run_and_review(self) -> None:
        temporary, repo_root, paths = self.fixture()
        self.addCleanup(temporary.cleanup)
        result_path = repo_root / "spikes" / "ts-test" / "results" / "candidate.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["pass"] = False
        result_path.write_text(json.dumps(result), encoding="utf-8")
        codes = self.validate(repo_root, paths, "release")
        self.assertIn("CANDIDATE_RESULT_HASH_MISMATCH", codes)
        self.assertIn("HUMAN_REVIEW_RESULT_HASH_MISMATCH", codes)

    def test_repository_discovery_rejects_candidate_output_without_manifest(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        repo_root = Path(temporary.name)
        result_path = repo_root / "spikes" / "ts-unregistered" / "results" / "candidate.json"
        result_path.parent.mkdir(parents=True)
        result_path.write_text(json.dumps({"evidence_kind": "candidate_output"}), encoding="utf-8")
        violations = validate_repository_candidate_evidence(repo_root=repo_root, required_stage="preflight")
        self.assertIn("CANDIDATE_MANIFEST_MISSING", {item["code"] for item in violations})

    def test_repository_discovery_rejects_unregistered_extra_candidate_output(self) -> None:
        temporary, repo_root, paths = self.fixture()
        self.addCleanup(temporary.cleanup)
        extra_path = repo_root / "spikes" / "ts-test" / "results" / "extra.json"
        extra_path.write_text(json.dumps({"evidence_kind": "candidate_output"}), encoding="utf-8")
        violations = validate_repository_candidate_evidence(repo_root=repo_root, required_stage="preflight")
        self.assertIn("UNREGISTERED_CANDIDATE_OUTPUT", {item["code"] for item in violations})


if __name__ == "__main__":
    unittest.main()
