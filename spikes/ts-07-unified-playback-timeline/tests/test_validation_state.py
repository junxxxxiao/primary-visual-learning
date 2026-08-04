import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "run_validation.py"
SPEC = importlib.util.spec_from_file_location("ts07_run_validation", MODULE_PATH)
VALIDATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATION)


class ReviewedDecisionTests(unittest.TestCase):
    def test_rejects_invalid_evidence(self):
        with self.assertRaises(ValueError):
            VALIDATION.reviewed_decision(validation_pass=False, candidate_gate_pass=True)

    def test_rejects_failed_candidate_gate(self):
        with self.assertRaises(ValueError):
            VALIDATION.reviewed_decision(validation_pass=True, candidate_gate_pass=False)

    def test_stops_at_candidate_run_complete_without_current_human_review(self):
        self.assertEqual(
            VALIDATION.reviewed_decision(validation_pass=True, candidate_gate_pass=True),
            {
                "evidence_state": "candidate_run_complete",
                "decision": None,
                "prior_review": VALIDATION.PRIOR_HUMAN_REVIEW,
            },
        )

    def test_releases_current_human_review_after_both_gates(self):
        review = {
            "evidence_state": "human_review_complete",
            "decision": "conditional_pass",
            "reviewer": "reviewer",
        }
        self.assertEqual(
            VALIDATION.reviewed_decision(
                validation_pass=True,
                candidate_gate_pass=True,
                human_review=review,
            ),
            review,
        )


class RetestStructureTests(unittest.TestCase):
    def test_rejects_missing_switch_evidence_explicitly(self):
        candidate = {
            "raw": {"real_runs": [], "fallback_runs": []},
            "metrics": {"fallback_handoffs": {}},
        }
        with self.assertRaisesRegex(ValueError, "raw.switch_runs, metrics.switch"):
            VALIDATION.require_retest_structure(candidate)

    def test_accepts_required_retest_collections(self):
        candidate = {
            "raw": {"real_runs": [], "switch_runs": [], "fallback_runs": []},
            "metrics": {"switch": {}, "fallback_handoffs": {}},
        }
        VALIDATION.require_retest_structure(candidate)


if __name__ == "__main__":
    unittest.main()
