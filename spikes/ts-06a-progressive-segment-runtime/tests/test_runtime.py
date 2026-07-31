from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

from run_validation import (  # noqa: E402
    evaluate_scenario,
    load_schemas,
    materialize_events,
    materialize_protocol,
)
from src.runtime import (  # noqa: E402
    ProgressiveRuntime,
    envelope_hash,
    event_payload_hash,
    manifest_hash,
)
from src.schema_validation import validate  # noqa: E402


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = json.loads((ROOT / "fixtures" / "base-protocol.json").read_text(encoding="utf-8"))
        cls.scenarios = json.loads((ROOT / "fixtures" / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]
        cls.schemas = load_schemas()

    def test_materialized_contracts_are_schema_valid_and_hash_bound(self) -> None:
        manifest, envelopes = materialize_protocol(self.base, 2, "gold_fixture")
        self.assertEqual(validate(manifest, self.schemas["manifest"]), [])
        self.assertEqual(manifest["manifest_hash"], manifest_hash(manifest))
        for envelope in envelopes.values():
            self.assertEqual(validate(envelope, self.schemas["envelope"]), [])
            self.assertEqual(envelope["envelope_hash"], envelope_hash(envelope))

    def test_manifest_tampering_fails_before_runtime_start(self) -> None:
        manifest, envelopes = materialize_protocol(self.base, 1, "adversarial_fixture")
        manifest["lesson_id"] = "lesson-tampered"
        with self.assertRaisesRegex(ValueError, "manifest hash"):
            ProgressiveRuntime(manifest, envelopes, self.schemas, trace_id="tamper")

    def test_manifest_rejects_non_contiguous_ordinals(self) -> None:
        manifest, envelopes = materialize_protocol(self.base, 2, "adversarial_fixture")
        manifest["segments"][1]["ordinal"] = 3
        manifest["manifest_hash"] = manifest_hash(manifest)
        envelopes["seg-02"]["ordinal"] = 3
        envelopes["seg-02"]["envelope_hash"] = envelope_hash(envelopes["seg-02"])
        with self.assertRaisesRegex(ValueError, "ordinals"):
            ProgressiveRuntime(manifest, envelopes, self.schemas, trace_id="bad-ordinal")

    def test_parallel_join_uses_critical_path(self) -> None:
        scenario = next(item for item in self.scenarios if item["scenario_id"] == "gold-segment-parallel")
        result = evaluate_scenario(scenario, self.base, self.schemas)
        self.assertTrue(result["pass"], result["checks"])
        self.assertEqual(result["snapshot"]["milestones"]["first_segment_playable"], 3000)
        self.assertEqual(result["work_metrics"]["critical_path_ms"], 2400)
        self.assertGreater(result["work_metrics"]["summed_work_ms"], 2400)

    def test_later_ready_segment_cannot_start_first(self) -> None:
        scenario = next(item for item in self.scenarios if item["scenario_id"] == "gold-later-ready-first")
        result = evaluate_scenario(scenario, self.base, self.schemas)
        self.assertTrue(result["pass"], result["checks"])
        self.assertIn("event.playback_out_of_order", result["observed_codes"])
        self.assertEqual(result["snapshot"]["started_segments"], ["seg-01", "seg-02"])

    def test_cancelled_segment_rejects_late_cache_admission(self) -> None:
        scenario = next(item for item in self.scenarios if item["scenario_id"] == "adversarial-cancel-late-response")
        result = evaluate_scenario(scenario, self.base, self.schemas)
        self.assertTrue(result["pass"], result["checks"])
        self.assertEqual(result["snapshot"]["valid_cache_entries"], [])

    def test_cancel_after_admission_removes_valid_cache_entry(self) -> None:
        scenario = next(item for item in self.scenarios if item["scenario_id"] == "adversarial-cancel-after-admission")
        result = evaluate_scenario(scenario, self.base, self.schemas)
        self.assertTrue(result["pass"], result["checks"])
        self.assertEqual(result["snapshot"]["valid_cache_entries"], [])

    def test_every_fixed_scenario_meets_its_oracle(self) -> None:
        failures = []
        for scenario in self.scenarios:
            result = evaluate_scenario(scenario, self.base, self.schemas)
            if not result["pass"]:
                failures.append((scenario["scenario_id"], result["checks"], result["observed_codes"]))
        self.assertEqual(failures, [])

    def test_event_payload_hash_tampering_is_rejected_without_mutation(self) -> None:
        scenario = next(item for item in self.scenarios if item["scenario_id"] == "gold-cache-admission")
        manifest, envelopes = materialize_protocol(self.base, 1, scenario["fixture_kind"])
        runtime = ProgressiveRuntime(manifest, envelopes, self.schemas, trace_id="tamper-event")
        event = materialize_events(scenario, manifest, envelopes)[0]
        tampered = copy.deepcopy(event)
        tampered["payload"] = {"unexpected": True}
        record = runtime.process(tampered)
        self.assertEqual(record["code"], "event.payload_hash_mismatch")
        self.assertFalse(record["state_mutated"])

    def test_invalid_high_timestamp_event_cannot_trigger_deadline(self) -> None:
        scenario = next(item for item in self.scenarios if item["scenario_id"] == "gold-cache-admission")
        manifest, envelopes = materialize_protocol(self.base, 1, scenario["fixture_kind"])
        runtime = ProgressiveRuntime(manifest, envelopes, self.schemas, trace_id="invalid-time")
        event = materialize_events(scenario, manifest, envelopes)[0]
        event["offset_ms"] = 45000
        event.pop("session_id")
        record = runtime.process(event)
        self.assertEqual(record["code"], "event.schema_invalid")
        self.assertEqual(runtime.now_ms, 0)
        self.assertEqual(runtime.result.derived_events, [])

    def test_invalid_readiness_payload_does_not_start_timeout_window(self) -> None:
        scenario = next(item for item in self.scenarios if item["scenario_id"] == "gold-cache-admission")
        manifest, envelopes = materialize_protocol(self.base, 1, scenario["fixture_kind"])
        runtime = ProgressiveRuntime(manifest, envelopes, self.schemas, trace_id="invalid-readiness")
        events = materialize_events(scenario, manifest, envelopes)
        runtime.process(events[0])
        runtime.process(events[1])
        invalid_visual = copy.deepcopy(events[3])
        invalid_visual["payload"] = {"artifact_hash": "invalid"}
        invalid_visual["payload_hash"] = event_payload_hash(invalid_visual)
        record = runtime.process(invalid_visual)
        self.assertEqual(record["code"], "event.visual_artifact_missing")
        self.assertIsNone(runtime.segments["seg-01"].first_readiness_offset_ms)


if __name__ == "__main__":
    unittest.main()
