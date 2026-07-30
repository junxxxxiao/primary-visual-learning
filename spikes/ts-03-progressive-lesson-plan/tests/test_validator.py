from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "shared"))

from src.validator import apply_mutations, validate_plan, validate_stage_pair  # noqa: E402
from evidence_provenance import validate_knowledge_provenance  # noqa: E402
from run_model import assert_knowledge_provenance, official_request_payload, percentile, prompts, validate_official_base_url  # noqa: E402


class LessonPlanValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads((ROOT / "schemas" / "lesson-plan.schema.json").read_text(encoding="utf-8"))
        cls.plan_data = json.loads((ROOT / "fixtures" / "plans.json").read_text(encoding="utf-8"))
        cls.case_data = json.loads((ROOT / "fixtures" / "cases.json").read_text(encoding="utf-8"))
        cls.policies = json.loads((ROOT / "fixtures" / "policies.json").read_text(encoding="utf-8"))["policies"]
        cls.plans = cls.plan_data["plans"]

    def test_all_positive_plans_pass(self) -> None:
        positive = [case for case in self.case_data["cases"] if case["expected"] == "pass"]
        self.assertEqual(len(positive), 4)
        for case in positive:
            plan = self.plans[case["base_plan"]]
            result = validate_plan(plan, self.schema, plan, self.policies[case["base_plan"]])
            self.assertEqual(result["result"], "pass", (case["case_id"], result["violations"]))

    def test_all_positive_plans_start_with_explanation(self) -> None:
        for fixture_id, plan in self.plans.items():
            self.assertEqual(plan["segments"][0]["phase"], "explanation", fixture_id)

    def test_all_positive_plans_have_source_backed_knowledge(self) -> None:
        ts02_root = ROOT.parent / "ts-02-knowledge-validation"
        for plan in self.plans.values():
            violations = validate_knowledge_provenance(plan["knowledge"], ts02_root)
            self.assertEqual(violations, [], (plan["fixture_id"], violations))

    def test_tampered_knowledge_is_blocked_before_model_call(self) -> None:
        plans = json.loads(json.dumps(self.plans))
        plans["middle_sound_pair"]["knowledge"]["claims"][1]["text"] = "Unsupported replacement claim."
        with self.assertRaisesRegex(RuntimeError, "KNOWLEDGE_PACKAGE_HASH_MISMATCH"):
            assert_knowledge_provenance(plans)

    def test_middle_sound_claims_use_the_dedicated_wave_source(self) -> None:
        knowledge = self.plans["middle_sound_pair"]["knowledge"]
        self.assertEqual(knowledge["source_scope"], "synthetic_fixture")
        self.assertEqual(
            {item["source_id"] for item in knowledge["source_refs"]},
            {"middle-sound-wave-synthetic-v1"},
        )
        self.assertEqual(
            {
                ref["source_id"]
                for claim in knowledge["claims"]
                for ref in claim["evidence_refs"]
            },
            {"middle-sound-wave-synthetic-v1"},
        )

    def test_every_negative_fixture_is_rejected(self) -> None:
        for case in self.case_data["cases"]:
            if case["expected"] != "fail":
                continue
            plan = apply_mutations(self.plans[case["base_plan"]], case.get("mutations", []), self.plans)
            result = validate_plan(
                plan,
                self.schema,
                self.plans[case["base_plan"]],
                self.policies[case["base_plan"]],
            )
            self.assertEqual(result["result"], "fail", case["case_id"])

    def test_stage_pair_differs_beyond_label(self) -> None:
        result = validate_stage_pair(self.plans["primary_sound_pair"], self.plans["middle_sound_pair"])
        self.assertEqual(result["result"], "pass", result["violations"])

    def test_model_cannot_widen_immutable_stage_rules(self) -> None:
        case = next(item for item in self.case_data["cases"] if item["case_id"] == "model_widens_stage_rules")
        plan = apply_mutations(self.plans[case["base_plan"]], case["mutations"], self.plans)
        result = validate_plan(
            plan,
            self.schema,
            self.plans[case["base_plan"]],
            self.policies[case["base_plan"]],
        )
        self.assertIn("IMMUTABLE_CONTEXT_CHANGED", {item["code"] for item in result["violations"]})

    def test_source_support_regressions_have_specific_gate_codes(self) -> None:
        expected_codes = {
            "explanation_term_support_incomplete": "EXPLANATION_TERM_UNSUPPORTED",
            "middle_transfer_fact_support_incomplete": "TRANSFER_FACT_SUPPORT_INCOMPLETE",
        }
        for case_id, expected_code in expected_codes.items():
            case = next(item for item in self.case_data["cases"] if item["case_id"] == case_id)
            plan = apply_mutations(self.plans[case["base_plan"]], case["mutations"], self.plans)
            result = validate_plan(
                plan,
                self.schema,
                self.plans[case["base_plan"]],
                self.policies[case["base_plan"]],
            )
            self.assertIn(expected_code, {item["code"] for item in result["violations"]}, case_id)

    def test_model_prompt_does_not_send_gold_segments_or_transfer(self) -> None:
        payload = json.loads(prompts(self.plans["primary_sound"], self.policies["primary_sound"])[1]["content"])
        self.assertNotIn("segments", payload)
        self.assertNotIn("transfer", payload)
        self.assertEqual(payload["generation_policy"], self.policies["primary_sound"])

    def test_model_prompt_allows_declared_prerequisites_to_support_basic_terms(self) -> None:
        system_prompt = prompts(self.plans["primary_sound"], self.policies["primary_sound"])[0]["content"]
        self.assertIn("visual.terms 中的每个术语", system_prompt)
        self.assertIn("prerequisite_term_support", system_prompt)
        self.assertIn("影响答案的事实判断仍必须引用 claim", system_prompt)

    def test_declared_prerequisite_can_support_a_basic_visual_term(self) -> None:
        plan = json.loads(json.dumps(self.plans["primary_sound"]))
        plan["segments"][0]["visual"]["terms"].append("振动")
        result = validate_plan(plan, self.schema, self.plans["primary_sound"], self.policies["primary_sound"])
        self.assertEqual(result["result"], "pass", result["violations"])

    def test_prerequisite_does_not_license_an_unmapped_conclusion_term(self) -> None:
        plan = json.loads(json.dumps(self.plans["primary_sound"]))
        plan["segments"][0]["fact_refs"] = []
        plan["segments"][0]["visual"]["terms"] = ["音调"]
        result = validate_plan(plan, self.schema, self.plans["primary_sound"], self.policies["primary_sound"])
        codes = {item["code"] for item in result["violations"]}
        self.assertIn("SEGMENT_FACTS_MISSING", codes)
        self.assertIn("EXPLANATION_TERM_UNSUPPORTED", codes)

    def test_official_full_plan_payload_disables_thinking(self) -> None:
        payload = official_request_payload(
            "deepseek-v4-pro",
            prompts(self.plans["primary_sound"]),
            max_tokens=8000,
            stream=False,
        )
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["max_tokens"], 8000)

    def test_official_full_plan_rejects_non_deepseek_host(self) -> None:
        validate_official_base_url("https://api.deepseek.com/v1")
        with self.assertRaises(RuntimeError):
            validate_official_base_url("https://example.invalid/v1")

    def test_full_plan_latency_percentiles(self) -> None:
        latencies = [14731, 21805, 13333, 14435]
        self.assertEqual(percentile(latencies, 0.50), 14583)
        self.assertEqual(percentile(latencies, 0.80), 17561)
        self.assertEqual(percentile(latencies, 0.95), 20744)

    def test_mutation_does_not_change_base_fixture(self) -> None:
        original = self.plans["primary_sound"]["segments"][0]["narration"]
        apply_mutations(
            self.plans["primary_sound"],
            [{"op": "set", "path": "segments.0.narration", "value": "changed"}],
            self.plans,
        )
        self.assertEqual(self.plans["primary_sound"]["segments"][0]["narration"], original)


if __name__ == "__main__":
    unittest.main()
