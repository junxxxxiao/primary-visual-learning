import json
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_schema_validation():
    path = ROOT.parent / "ts-03-progressive-lesson-plan/src/schema_validation.py"
    spec = importlib.util.spec_from_file_location("ts04c_schema_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HarnessContractTests(unittest.TestCase):
    def test_harness_is_explicitly_unverified(self):
        summary = json.loads((ROOT / "results/summary.json").read_text())
        self.assertEqual(summary["status"], "fail")
        self.assertEqual(summary["decision"], "fail")
        self.assertEqual(summary["metrics"]["calibration_declaration_gate_pass"], 0)
        self.assertEqual(summary["metrics"]["candidate_samples"], 10)
        self.assertEqual(summary["metrics"]["browser_gate_pass"], 1)
        self.assertLess(summary["metrics"]["browser_gate_pass_rate"], summary["metrics"]["browser_gate_pass_threshold"])
        self.assertEqual(summary["cost"]["status"], "unverified")

    def test_referenced_upstream_contracts_exist(self):
        for relative_path in (
            "../ts-03-progressive-lesson-plan/schemas/lesson-plan.schema.json",
            "../ts-04b-visual-scene-gate/schemas/visual-scene.schema.json",
            "../shared/schemas/stage-timing.schema.json",
        ):
            self.assertTrue((ROOT / relative_path).resolve().is_file(), relative_path)

    def test_calibration_fixture_is_balanced_and_sealed(self):
        fixture = json.loads((ROOT / "fixtures/calibration-inputs.json").read_text())
        self.assertEqual(fixture["sample_count"], 10)
        self.assertEqual(fixture["stage_counts"], {"middle": 5, "primary": 5})
        self.assertEqual(len({item["sample_id"] for item in fixture["samples"]}), 10)
        self.assertTrue(all(item["input_hash"].startswith("sha256:") for item in fixture["samples"]))

    def test_full_question_relation_oracle_is_synthetic_and_claim_bound(self):
        source = json.loads((ROOT / "fixtures/full-question-egg-saltwater-v01.json").read_text())
        relations = json.loads((ROOT / "fixtures/full-question-egg-saltwater-v01.visual-relations.json").read_text())
        schema = json.loads((ROOT / "schemas/visual-relation-requirements.schema.json").read_text())
        claim_ids = {claim["claim_id"] for claim in source["claims"]}
        self.assertEqual(load_schema_validation().validate(relations, schema), [])
        self.assertEqual(relations["fixture_kind"], "gold_fixture")
        self.assertEqual(relations["evidence_status"], "synthetic_unverified")
        self.assertEqual(relations["question_id"], source["question_id"])
        self.assertTrue(all(set(item["claim_refs"]) <= claim_ids for item in relations["relations"]))


if __name__ == "__main__":
    unittest.main()
