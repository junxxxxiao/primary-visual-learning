from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.validator import (  # noqa: E402
    ValidatedSceneCache,
    apply_mutations,
    validate_all_layout_states,
    validate_scene_structure,
    validate_teaching,
)


class ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = json.loads((ROOT / "fixtures" / "base-scenes.json").read_text())["scenes"]
        cls.cases = json.loads((ROOT / "fixtures" / "cases.json").read_text())["cases"]

    def test_valid_scenes_cover_both_viewports_and_all_states(self) -> None:
        for scene in self.base.values():
            self.assertEqual(validate_scene_structure(scene), [])
            self.assertEqual(validate_teaching(scene)["result"], "pass")
            results = validate_all_layout_states(scene)
            self.assertEqual(len(results), 16)
            self.assertTrue(all(result["result"] == "pass" for result in results))

    def test_every_negative_fixture_is_rejected(self) -> None:
        for case in self.cases:
            if case["expected"] != "fail":
                continue
            scene = apply_mutations(self.base[case["base_scene"]], case.get("mutations", []))
            rejected = (
                bool(validate_scene_structure(scene))
                or validate_teaching(scene)["result"] == "fail"
                or any(result["result"] == "fail" for result in validate_all_layout_states(scene))
            )
            self.assertTrue(rejected, case["case_id"])

    def test_failed_scene_cannot_enter_cache(self) -> None:
        cache = ValidatedSceneCache()
        self.assertFalse(cache.write(self.base["sound"], "phone", admitted=False))
        self.assertEqual(cache.size, 0)

    def test_each_cache_identity_change_invalidates(self) -> None:
        fields = (
            "learning_goal",
            "knowledge_version",
            "teaching_contract_version",
            "layout_contract_version",
            "scene_version",
            "code_hash",
            "test_version",
        )
        for field in fields:
            cache = ValidatedSceneCache()
            scene = self.base["sound"]
            self.assertTrue(cache.write(scene, "phone", admitted=True))
            changed = copy.deepcopy(scene)
            changed[field] += "+changed"
            self.assertEqual(cache.read(changed, "phone").status, "invalidated", field)


if __name__ == "__main__":
    unittest.main()
