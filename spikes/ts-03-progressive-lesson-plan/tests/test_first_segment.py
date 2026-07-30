from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.first_segment import validate_first_segment  # noqa: E402


class FirstSegmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plans = json.loads((ROOT / "fixtures" / "plans.json").read_text(encoding="utf-8"))["plans"]
        cls.policies = json.loads((ROOT / "fixtures" / "policies.json").read_text(encoding="utf-8"))["policies"]
        cls.schema = json.loads((ROOT / "schemas" / "first-segment.schema.json").read_text(encoding="utf-8"))

    def output_for(self, fixture_id: str) -> dict:
        fixture = self.plans[fixture_id]
        return {"schema_version": "first-segment/1.2", "fixture_id": fixture_id, "segment": copy.deepcopy(fixture["segments"][0])}

    def test_gold_first_segments_pass(self) -> None:
        for fixture_id, fixture in self.plans.items():
            result = validate_first_segment(
                self.output_for(fixture_id),
                fixture,
                self.schema,
                self.policies[fixture_id],
            )
            self.assertEqual(result["result"], "pass", (fixture_id, result["violations"]))

    def test_explanation_can_state_the_answer(self) -> None:
        output = self.output_for("primary_sound")
        output["segment"]["phase"] = "explanation"
        output["segment"]["narration"] = "答案是音调不变，只会更响。"
        result = validate_first_segment(
            output,
            self.plans["primary_sound"],
            self.schema,
            self.policies["primary_sound"],
        )
        self.assertEqual(result["result"], "pass", result["violations"])

    def test_early_narration_is_rejected(self) -> None:
        output = self.output_for("primary_sound")
        output["segment"]["cues"][1]["at_ms"] = 500
        result = validate_first_segment(
            output,
            self.plans["primary_sound"],
            self.schema,
            self.policies["primary_sound"],
        )
        self.assertIn("START_HOLD_TOO_SHORT", {item["code"] for item in result["violations"]})


if __name__ == "__main__":
    unittest.main()
