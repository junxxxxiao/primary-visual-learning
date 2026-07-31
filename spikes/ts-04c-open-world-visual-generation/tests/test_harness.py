import importlib.util
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    spec = importlib.util.spec_from_file_location("ts04c_v3_validator", ROOT / "validate_harness.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_example_prompt():
    spec = importlib.util.spec_from_file_location("ts04c_v03_example_prompt", ROOT / "src/v03_example_prompt.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_v04_quality_prompt():
    spec = importlib.util.spec_from_file_location("ts04c_v04_quality_prompt", ROOT / "src/v04_quality_prompt.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class OpenWorldHarnessTests(unittest.TestCase):
    def test_offline_harness_is_internally_consistent(self):
        self.assertEqual(load_validator().validate(), [])

    def test_questions_do_not_reuse_demo_topics(self):
        fixture = json.loads((ROOT / "fixtures/calibration-inputs.json").read_text())
        questions = " ".join(sample["question"] for sample in fixture["samples"])
        self.assertNotIn("拨同一根弦", questions)
        self.assertNotIn("完全平方", questions)
        self.assertNotIn("靠墙", questions)

    def test_scene_interface_is_general_and_single_output(self):
        schema = json.loads((ROOT / "schemas/open-visual-scene.schema.json").read_text())
        node_types = schema["$defs"]["node"]["properties"]["type"]["enum"]
        self.assertEqual(len(node_types), 8)
        self.assertNotIn("shadow", node_types)
        self.assertNotIn("circuit", node_types)
        serialized = json.dumps(schema)
        self.assertNotIn("phone_scene", serialized)
        self.assertNotIn("tablet_scene", serialized)

    def test_timeline_requires_complete_multi_beat_explanation(self):
        schema = json.loads((ROOT / "schemas/open-visual-scene.schema.json").read_text())
        timeline = schema["properties"]["timeline"]["properties"]
        self.assertEqual(timeline["start_hold_ms"]["const"], 1000)
        self.assertEqual(timeline["beats"]["minItems"], 3)
        self.assertEqual(timeline["beats"]["maxItems"], 6)
        beat = schema["$defs"]["beat"]
        self.assertIn("narration", beat["required"])
        self.assertIn("actions", beat["required"])
        self.assertIn("fact_refs", beat["required"])

    def test_candidate_gate_accepts_gold_and_rejects_broken_references(self):
        validator = load_validator()
        gate = validator.load_gate()
        fixture = json.loads((ROOT / "fixtures/calibration-inputs.json").read_text())
        cases = json.loads((ROOT / "fixtures/schema-gate-cases.json").read_text())
        schema = json.loads((ROOT / "schemas/open-visual-scene.schema.json").read_text())
        sample = next(item for item in fixture["samples"] if item["sample_id"] == cases["sample_id"])
        self.assertEqual(gate.gate_candidate(cases["valid_scene"], sample, schema), [])
        broken = json.loads(json.dumps(cases["valid_scene"]))
        broken["timeline"]["beats"][1]["actions"][0]["target_ids"] = ["not-declared"]
        self.assertIn("timeline.unknown_target:trace-rays", gate.gate_candidate(broken, sample, schema))

    def test_summary_records_candidate_failure_without_skipping_gates(self):
        summary = json.loads((ROOT / "results/summary.json").read_text())
        self.assertEqual(summary["status"], "fail")
        self.assertEqual(summary["candidate"]["requests_made"], 63)
        self.assertEqual(summary["candidate"]["provider"], "deepseek_official")
        self.assertEqual(summary["candidate"]["model_or_service_version"], "deepseek-v4-flash")
        self.assertTrue(summary["candidate"]["data_boundary_confirmed"])
        self.assertEqual(summary["metrics"]["candidate_output_count"], 10)
        self.assertEqual(summary["schema_version"], "open-visual-scene/0.3")
        self.assertEqual(summary["metrics"]["contract_pass_count"], 7)
        self.assertEqual(summary["metrics"]["cumulative_tokens"], 379391)
        self.assertEqual(summary["metrics"]["v03_contract_pass_count"], 5)
        self.assertEqual(summary["metrics"]["v03_browser_state_runs"], 0)
        self.assertEqual(summary["metrics"]["final_contract_pass_count"], 10)
        self.assertEqual(summary["metrics"]["browser_candidate_pass_count"], 7)
        self.assertEqual(summary["metrics"]["browser_state_runs"], 160)
        self.assertEqual(summary["metrics"]["human_review_count"], 10)
        self.assertEqual(summary["metrics"]["human_review_showable_count"], 1)
        self.assertEqual(summary["metrics"]["human_review_revise_count"], 7)
        self.assertEqual(summary["metrics"]["human_review_reject_count"], 2)
        self.assertEqual(summary["metrics"]["v04_candidate_response_count"], 10)
        self.assertEqual(summary["metrics"]["v04_contract_pass_count"], 5)
        self.assertEqual(summary["metrics"]["v04_browser_state_runs"], 0)
        self.assertEqual(summary["metrics"]["example_guided_contract_pass_count"], 10)
        self.assertEqual(summary["metrics"]["example_guided_browser_pass_count"], 10)

    def test_runner_hard_codes_authorized_budget_and_no_retries(self):
        source = (ROOT / "run_calibration.py").read_text()
        self.assertIn('AUTHORIZED_ORIGIN = "https://api.deepseek.com"', source)
        self.assertIn('"deepseek-v4-pro": "official-open-world-v02-calibration-round-1"', source)
        self.assertIn('"deepseek-v4-flash": "official-open-world-v02-flash-calibration-round-1"', source)
        self.assertIn("MAX_REQUESTS = 10", source)
        self.assertIn("MAX_OUTPUT_TOKENS = 5_000", source)
        self.assertIn("TOKEN_BUDGET = 100_000", source)
        self.assertIn('"automatic_retries": 0', source)
        self.assertIn('SCHEMA_VERSION = "open-visual-scene/0.2"', source)

    def test_v02_deepens_actions_without_weakening_safety(self):
        v01 = json.loads((ROOT / "schemas/open-visual-scene.schema.json").read_text())
        v02 = json.loads((ROOT / "schemas/open-visual-scene-v0.2.schema.json").read_text())
        self.assertEqual(v01["$id"], "open-visual-scene/0.1")
        self.assertEqual(v02["$id"], "open-visual-scene/0.2")
        action_v01 = v01["$defs"]["action"]["properties"]
        action_v02 = v02["$defs"]["action"]["properties"]
        self.assertEqual(action_v01["target_ids"]["maxItems"], 8)
        self.assertEqual(action_v02["target_ids"]["maxItems"], 20)
        self.assertNotIn("height", action_v01["to"]["properties"])
        self.assertIn("height", action_v02["to"]["properties"])
        self.assertEqual(v01["$defs"]["node"]["properties"]["type"], v02["$defs"]["node"]["properties"]["type"])
        self.assertEqual(v01["properties"]["fact_refs"], v02["properties"]["fact_refs"])

    def test_v03_requires_one_coordinate_anchor_and_rejects_ambiguous_geometry(self):
        validator = load_validator()
        gate = validator.load_gate()
        fixture = json.loads((ROOT / "fixtures/calibration-inputs.json").read_text())
        cases = json.loads((ROOT / "fixtures/schema-gate-cases.json").read_text())
        schema = json.loads((ROOT / "schemas/open-visual-scene-v0.3.schema.json").read_text())
        sample = next(item for item in fixture["samples"] if item["sample_id"] == cases["sample_id"])
        scene = deepcopy(cases["valid_scene"])
        scene["schema_version"] = "open-visual-scene/0.3"
        scene["scene"]["coordinate_space"]["anchor"] = "center"
        self.assertEqual(gate.gate_candidate(scene, sample, schema), [])

        ambiguous = deepcopy(scene)
        del ambiguous["scene"]["coordinate_space"]["anchor"]
        self.assertTrue(any("missing required property anchor" in item for item in gate.gate_candidate(ambiguous, sample, schema)))

        top_left_assumption = deepcopy(scene)
        top_left_assumption["scene"]["nodes"][1]["geometry"] = {"x": 850, "y": 100, "width": 20, "height": 800}
        self.assertIn("scene.geometry_out_of_bounds:toy", gate.gate_candidate(top_left_assumption, sample, schema))

    def test_v03_rejects_motion_envelope_crossing_canvas_boundary(self):
        validator = load_validator()
        gate = validator.load_gate()
        fixture = json.loads((ROOT / "fixtures/calibration-inputs.json").read_text())
        cases = json.loads((ROOT / "fixtures/schema-gate-cases.json").read_text())
        schema = json.loads((ROOT / "schemas/open-visual-scene-v0.3.schema.json").read_text())
        sample = next(item for item in fixture["samples"] if item["sample_id"] == cases["sample_id"])
        scene = deepcopy(cases["valid_scene"])
        scene["schema_version"] = "open-visual-scene/0.3"
        scene["scene"]["coordinate_space"]["anchor"] = "center"
        scene["timeline"]["beats"][0]["actions"].append({
            "type": "move", "target_ids": ["toy"], "start_ms": 1000, "duration_ms": 1000,
            "to": {"x": 980, "y": 360},
        })
        self.assertIn(
            "timeline.motion_envelope_out_of_bounds:orient:toy",
            gate.gate_candidate(scene, sample, schema),
        )

        rotating = deepcopy(cases["valid_scene"])
        rotating["schema_version"] = "open-visual-scene/0.3"
        rotating["scene"]["coordinate_space"]["anchor"] = "center"
        rotating["scene"]["nodes"][1]["geometry"] = {"x": 60, "y": 360, "width": 100, "height": 100}
        rotating["timeline"]["beats"][0]["actions"].append({
            "type": "rotate", "target_ids": ["toy"], "start_ms": 1000, "duration_ms": 1000,
            "to": {"rotation_deg": 180},
        })
        self.assertIn(
            "timeline.motion_envelope_out_of_bounds:orient:toy",
            gate.gate_candidate(rotating, sample, schema),
        )

        point_transform = deepcopy(scene)
        point_transform["timeline"]["beats"][1]["actions"].append({
            "type": "move", "target_ids": ["ray-top"], "start_ms": 0, "duration_ms": 1000,
            "to": {"x": 500, "y": 500},
        })
        self.assertIn(
            "timeline.point_transform_undefined:trace-rays:ray-top",
            gate.gate_candidate(point_transform, sample, schema),
        )

    def test_flash_repair_is_bounded_to_three_failed_samples(self):
        source = (ROOT / "run_flash_repair.py").read_text()
        self.assertIn('AUTHORIZED_MODEL = "deepseek-v4-flash"', source)
        self.assertIn("MAX_REPAIR_REQUESTS = 3", source)
        self.assertIn("TOKEN_BUDGET = 30_000", source)
        self.assertIn('source["metrics"]["contract_pass"] != {"numerator": 7, "denominator": 10}', source)
        self.assertIn('"maximum_repairs_per_failed_sample": 1', source)

    def test_v03_runner_freezes_authorized_flash_profile(self):
        source = (ROOT / "run_v03_calibration.py").read_text()
        self.assertIn('AUTHORIZED_MODEL = "deepseek-v4-flash"', source)
        self.assertIn('SCHEMA_VERSION = "open-visual-scene/0.3"', source)
        self.assertIn('RUN_LABEL = "official-open-world-v03-flash-calibration-round-1"', source)
        self.assertIn("MAX_REQUESTS = 10", source)
        self.assertIn("TOKEN_BUDGET = 100_000", source)
        self.assertIn('"automatic_retries": 0', source)
        self.assertIn('"repairs": 0', source)
        self.assertIn("scene.coordinate_space.anchor 必须为 center", source)

    def test_example_guided_prompt_demonstrates_every_strict_output_family(self):
        validator = load_validator()
        gate = validator.load_gate()
        prompt = load_example_prompt()
        schema = json.loads((ROOT / "schemas/open-visual-scene-v0.3.schema.json").read_text())
        wrapper = json.loads((ROOT / "fixtures/open-visual-scene-v03-format-example.json").read_text())
        example = wrapper["example"]
        format_sample = {
            "sample_id": "format.example",
            "claims": [{"claim_id": "format.claim", "status": "synthetic_unverified"}],
        }

        self.assertEqual(wrapper["fixture_kind"], "gold_fixture")
        self.assertEqual(wrapper["source_kind"], "synthetic_format_only")
        self.assertEqual(gate.gate_candidate(example, format_sample, schema), [])
        self.assertEqual({node["type"] for node in example["scene"]["nodes"]}, set(schema["$defs"]["node"]["properties"]["type"]["enum"]))
        actions = {action["type"] for beat in example["timeline"]["beats"] for action in beat["actions"]}
        self.assertEqual(actions, set(schema["$defs"]["action"]["properties"]["type"]["enum"]))

        sample = json.loads((ROOT / "fixtures/calibration-inputs.json").read_text())["samples"][0]
        messages = prompt.build_messages(sample, schema, "quality contract")
        payload = json.loads(messages[1]["content"])
        self.assertEqual(payload["format_example"], wrapper)
        rules = messages[0]["content"]
        for required_text in (
            "line 和 plot 节点必须使用 geometry.points",
            "严禁使用 x1、y1、x2、y2",
            "ID 只能使用小写英文字母、数字、点、下划线和短横线",
            "根节点必须省略 parent_id，严禁填写 null",
            "layout.priority 只能是 1 到 5 的整数",
            "严禁输出 children",
            "只复制结构，不得复制示例的 sample_id、fact_refs、文案或数值",
        ):
            self.assertIn(required_text, rules)

    def test_example_guided_runner_uses_an_independent_frozen_profile(self):
        source = (ROOT / "run_v03_example_guided_calibration.py").read_text()
        self.assertIn('RUN_LABEL = "official-open-world-v03-flash-example-guided-calibration-round-1"', source)
        self.assertIn('"name": "v03-complete-format-example/0.1"', source)
        self.assertIn('"format_example_kind": "gold_fixture"', source)
        self.assertIn('"format_example_source": "synthetic_format_only"', source)
        self.assertIn("prompt_builder=build_messages", source)
        self.assertNotIn("api_key", source.lower())

    def test_v04_quality_contract_supports_generic_semantic_shapes(self):
        validator = load_validator()
        gate = validator.load_gate()
        prompt = load_v04_quality_prompt()
        schema = json.loads((ROOT / "schemas/open-visual-scene-v0.4.schema.json").read_text())
        wrapper = json.loads((ROOT / "fixtures/open-visual-scene-v04-quality-example.json").read_text())
        example = wrapper["example"]
        format_sample = {
            "sample_id": "format.example",
            "claims": [{"claim_id": "format.claim", "status": "synthetic_unverified"}],
        }

        self.assertEqual(schema["$id"], "open-visual-scene/0.4")
        self.assertEqual(gate.gate_candidate(example, format_sample, schema), [])
        block = next(node for node in example["scene"]["nodes"] if node["id"] == "block")
        guide = next(node for node in example["scene"]["nodes"] if node["id"] == "guide-line")
        self.assertEqual(block["shape_kind"], "polygon")
        self.assertEqual(len(block["geometry"]["vertices"]), 3)
        self.assertEqual(guide["marker_end"], "arrow")

        invalid = deepcopy(example)
        invalid["scene"]["nodes"][1].pop("geometry")
        self.assertIn("scene.polygon_missing_vertices:block", gate.gate_candidate(invalid, format_sample, schema))

        bound_sample = deepcopy(format_sample)
        bound_sample["required_explanation_aspects"] = ["必须覆盖的关系"]
        self.assertIn("binding.aspect_coverage_mismatch", gate.gate_candidate(example, bound_sample, schema))

        sample = json.loads((ROOT / "fixtures/calibration-inputs.json").read_text())["samples"][0]
        messages = prompt.build_messages(sample, schema, "quality contract")
        rules = messages[0]["content"]
        for required_text in (
            "可移动三角形或其他多边形",
            "需要明确方向的线使用 marker_end=arrow",
            "相关视觉关系必须同步更新",
            "数学图必须先自检数值对应",
            "不得添加无教学用途的图形",
            "每个 required_explanation_aspects",
        ):
            self.assertIn(required_text, rules)

    def test_v04_runner_freezes_authorized_quality_profile(self):
        source = (ROOT / "run_v04_quality_calibration.py").read_text()
        self.assertIn('RUN_LABEL = "official-open-world-v04-flash-quality-guided-calibration-round-1"', source)
        self.assertIn('"name": "v04-semantic-quality-example/0.1"', source)
        self.assertIn('schema_version="open-visual-scene/0.4"', source)
        self.assertIn('schema_filename="open-visual-scene-v0.4.schema.json"', source)
        self.assertIn('"quality_rules": 22', source)
        self.assertNotIn('"PENDING"', source)
        self.assertNotIn("api_key", source.lower())

    def test_browser_gate_covers_two_viewports_and_eight_states(self):
        renderer = (ROOT / "src/scene-renderer.js").read_text()
        harness = (ROOT / "src/browser-harness.js").read_text()
        server = (ROOT / "run_browser_server.py").read_text()
        self.assertIn('"initial", "key_process", "final", "paused", "resumed", "post_interaction", "reduced_motion", "static_fallback"', renderer)
        self.assertIn('phone: { kind: "phone", width: 390, height: 632 }', harness)
        self.assertIn('tablet: { kind: "tablet", width: 1024, height: 728 }', harness)
        self.assertIn('"browser.logical_bounds"', server)
        self.assertIn('"browser.screen_bounds"', server)
        self.assertIn('"browser.blank_canvas"', server)
        self.assertIn('"v03-example-guided"', harness)
        self.assertIn('"v4-flash-v03-example-guided-browser-round-1"', harness)
        self.assertIn('"v03-example-guided"', server)
        self.assertIn('"open-visual-scene/0.3"', server)

    def test_v03_browser_candidates_replay_the_ten_contract_passes(self):
        source = (ROOT / "prepare_v03_example_guided_browser_candidates.py").read_text()
        self.assertIn('"model-deepseek-v4-flash-official-open-world-v03-flash-example-guided-calibration-round-1.json"', source)
        self.assertIn('{"numerator": 10, "denominator": 10}', source)
        self.assertIn('"v03-complete-format-example/0.1"', source)
        self.assertIn('"open-visual-scene/0.3"', source)


if __name__ == "__main__":
    unittest.main()
