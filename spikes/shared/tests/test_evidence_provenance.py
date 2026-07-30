from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evidence_provenance import seal_knowledge_package, validate_knowledge_provenance  # noqa: E402


class EvidenceProvenanceTests(unittest.TestCase):
    def fixture(self, quote: str) -> tuple[tempfile.TemporaryDirectory[str], Path, dict]:
        temporary = tempfile.TemporaryDirectory()
        producer_root = Path(temporary.name)
        source_path = producer_root / "fixtures" / "sources" / "source.txt"
        source_path.parent.mkdir(parents=True)
        source_path.write_text("SYNTHETIC\n\n[page 1]\nAmplitude relates to loudness.\n", encoding="utf-8")
        document_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        manifest = {
            "sources": [{"source_id": "source", "path": "fixtures/sources/source.txt", "sha256": document_hash}]
        }
        manifest_path = producer_root / "fixtures" / "source-manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        knowledge = seal_knowledge_package(
            {
                "package_version": "test/1.0",
                "producer_slice": "TS-test",
                "package_case_id": "case",
                "source_scope": "synthetic_fixture",
                "verification_status": "verified_atom",
                "review_method": "ai_only",
                "evidence_status": "exploratory_only",
                "source_refs": [{"source_id": "source", "document_hash": f"sha256:{document_hash}", "edition": "synthetic", "pages": [1]}],
                "claims": [{"claim_id": "claim", "text": "Amplitude relates to loudness.", "critical": True, "supported_terms": ["振幅", "响度"], "evidence_refs": [{"source_id": "source", "page": 1, "quote": quote}]}],
            }
        )
        export = {
            "source_manifest_sha256": f"sha256:{hashlib.sha256(manifest_path.read_bytes()).hexdigest()}",
            "packages": {"case": knowledge},
        }
        results = producer_root / "results"
        results.mkdir()
        (results / "knowledge-packages.json").write_text(json.dumps(export), encoding="utf-8")
        return temporary, producer_root, knowledge

    def test_valid_package_passes(self) -> None:
        temporary, producer_root, knowledge = self.fixture("Amplitude relates to loudness")
        self.addCleanup(temporary.cleanup)
        self.assertEqual(validate_knowledge_provenance(knowledge, producer_root), [])

    def test_unmatched_evidence_quote_is_rejected(self) -> None:
        temporary, producer_root, knowledge = self.fixture("Frequency relates to pitch")
        self.addCleanup(temporary.cleanup)
        violations = validate_knowledge_provenance(knowledge, producer_root)
        self.assertIn("EVIDENCE_QUOTE_NOT_FOUND", {item["code"] for item in violations})

    def test_changed_source_file_is_rejected(self) -> None:
        temporary, producer_root, knowledge = self.fixture("Amplitude relates to loudness")
        self.addCleanup(temporary.cleanup)
        source_path = producer_root / "fixtures" / "sources" / "source.txt"
        source_path.write_text("SYNTHETIC\n\n[page 1]\nChanged evidence.\n", encoding="utf-8")
        violations = validate_knowledge_provenance(knowledge, producer_root)
        self.assertIn("SOURCE_DOCUMENT_HASH_MISMATCH", {item["code"] for item in violations})

    def test_non_synthetic_package_requires_independent_semantic_review(self) -> None:
        temporary, producer_root, knowledge = self.fixture("Amplitude relates to loudness")
        self.addCleanup(temporary.cleanup)
        controlled = {key: value for key, value in knowledge.items() if key != "package_sha256"}
        controlled["source_scope"] = "controlled_source"
        controlled = seal_knowledge_package(controlled)
        export_path = producer_root / "results" / "knowledge-packages.json"
        export = json.loads(export_path.read_text(encoding="utf-8"))
        export["packages"]["case"] = controlled
        export_path.write_text(json.dumps(export), encoding="utf-8")
        violations = validate_knowledge_provenance(controlled, producer_root)
        self.assertIn("INDEPENDENT_SEMANTIC_REVIEW_MISSING", {item["code"] for item in violations})


if __name__ == "__main__":
    unittest.main()
