#!/usr/bin/env python3
"""Seal the ten TS-03 segments used by the TS-04C calibration round."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TS03 = ROOT.parent / "ts-03-progressive-lesson-plan"


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> int:
    plans_path = TS03 / "fixtures" / "plans.json"
    plans_payload = json.loads(plans_path.read_text(encoding="utf-8"))
    plans = plans_payload["plans"]
    samples = []
    stage_counts = {"primary": 0, "middle": 0}

    for fixture_id in ("primary_sound", "primary_sound_pair", "middle_perfect_square", "middle_sound_pair"):
        plan = plans[fixture_id]
        stage = plan["stage_profile"]["school_stage"]
        claims = {claim["claim_id"]: claim for claim in plan["knowledge"]["claims"]}
        for segment in plan["segments"]:
            sample_id = f"{fixture_id}.{segment['segment_id']}"
            sample = {
                "sample_id": sample_id,
                "fixture_kind": "gold_fixture",
                "source_kind": "synthetic_gold_fixture",
                "school_stage": stage,
                "stage_profile": plan["stage_profile"],
                "core_relation": plan["core_relation"],
                "learning_goal": segment["goal"],
                "narration": segment["narration"],
                "cues": segment["cues"],
                "visual_contract": segment["visual"],
                "static_fallback": segment["static_fallback"],
                "claims": [claims[claim_id] for claim_id in segment["fact_refs"]],
                "source_fixture_hash": sha256_text(json.dumps(plan, ensure_ascii=False, sort_keys=True)),
                "source_plan_schema": plan["schema_version"],
                "source_run_label": "ts03-gold-fixtures",
            }
            sample["input_hash"] = sha256_text(json.dumps(sample, ensure_ascii=False, sort_keys=True))
            samples.append(sample)
            stage_counts[stage] += 1

    if stage_counts != {"primary": 5, "middle": 5}:
        raise RuntimeError(f"Calibration split must remain 5/5, got {stage_counts}")
    payload = {
        "fixture_version": "ts04c-calibration-inputs/0.1",
        "source_fixture": str(plans_path.relative_to(ROOT.parent.parent)),
        "source_fixture_hash": sha256_text(plans_path.read_text(encoding="utf-8")),
        "sample_count": len(samples),
        "stage_counts": stage_counts,
        "samples": samples,
    }
    output = ROOT / "fixtures" / "calibration-inputs.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"sealed {len(samples)} calibration samples -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
