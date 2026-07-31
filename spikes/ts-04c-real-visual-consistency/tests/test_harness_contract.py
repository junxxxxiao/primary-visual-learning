import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()
