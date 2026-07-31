import json
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_runner():
    spec = importlib.util.spec_from_file_location("ts04c_v2_runner_test", ROOT / "run_calibration.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DslHarnessTests(unittest.TestCase):
    def test_fixture_is_bounded_and_contains_no_code(self):
        fixture = json.loads((ROOT / "fixtures/specs.json").read_text())
        self.assertEqual(fixture["sample_count"], 10)
        self.assertEqual(len({entry["spec"]["sample_id"] for entry in fixture["specs"]}), 10)
        self.assertTrue(all(entry["fixture_kind"] == "gold_fixture" for entry in fixture["specs"]))
        serialized = json.dumps(fixture)
        self.assertNotIn("scene_code", serialized)
        self.assertNotIn("javascript", serialized.lower())

    def test_summary_records_decisive_product_visual_failure(self):
        summary = json.loads((ROOT / "results/summary.json").read_text())
        self.assertEqual(summary["status"], "fail")
        self.assertEqual(summary["candidate_model_requests"], 10)
        self.assertFalse(summary["candidate_model_validated"])
        self.assertEqual(summary["human_review_status"], "product_visual_stop_condition_met")
        self.assertEqual(summary["metrics"]["product_visual_reviewed_count"], 10)
        self.assertEqual(summary["metrics"]["product_visual_displayable_count"], 0)
        self.assertEqual(summary["metrics"]["multi_beat_narration_count"], 0)
        self.assertTrue(summary["stopped_work"])

    def test_candidate_gate_rejects_binding_changes_and_code_text(self):
        runner = load_runner()
        samples = json.loads((ROOT.parent / "ts-04c-real-visual-consistency/fixtures/calibration-inputs.json").read_text())["samples"]
        schema = json.loads((ROOT / "schemas/visual-dsl.schema.json").read_text())
        candidate = json.loads((ROOT / "fixtures/specs.json").read_text())["specs"][0]["spec"]
        self.assertEqual(runner.gate_candidate(candidate, samples[0], schema), [])
        changed = json.loads(json.dumps(candidate))
        changed["sample_id"] = "wrong.sample"
        changed["labels"][0] = "<script>bad</script>"
        violations = runner.gate_candidate(changed, samples[0], schema)
        self.assertIn("binding.sample_id_mismatch", violations)
        self.assertIn("safety.code_like_content", violations)

    def test_browser_gate_requires_every_dsl_content_item(self):
        source = (ROOT / "run_browser_server.py").read_text()
        compiler = (ROOT / "src/compiler.js").read_text()
        self.assertIn("browser.dsl_content_missing", source)
        self.assertIn("spec.static_fallback.steps", compiler)
        self.assertIn("dsl-content-", compiler)

    def test_human_review_workbench_keeps_review_independent(self):
        page = (ROOT / "human-review.html").read_text()
        script = (ROOT / "src/human-review.js").read_text()
        server = (ROOT / "run_browser_server.py").read_text()
        self.assertIn("phone-canvas", page)
        self.assertIn("tablet-canvas", page)
        self.assertEqual(script.count('["static_fallback", "静态降级"]'), 1)
        self.assertIn("all eight states must be visited", server)
        self.assertIn("One submitted review does not by itself advance the slice status.", server)
        self.assertIn("subject_matter", server)
        self.assertIn("product_visual", server)


if __name__ == "__main__":
    unittest.main()
