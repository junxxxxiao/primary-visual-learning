#!/usr/bin/env python3
"""Merge the seven initial and three repaired Flash candidates for browser gating."""
from __future__ import annotations

import json
from pathlib import Path

from run_calibration import load_gate


ROOT = Path(__file__).resolve().parent
INITIAL = ROOT / "results" / "model-deepseek-v4-flash-official-open-world-v02-flash-calibration-round-1.json"
REPAIR = ROOT / "results" / "model-deepseek-v4-flash-official-open-world-v02-flash-repair-round-1.json"
OUTPUT = ROOT / "results" / "candidates-v4-flash-v02-repaired.json"


def main() -> int:
    fixtures = json.loads((ROOT / "fixtures" / "calibration-inputs.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas" / "open-visual-scene-v0.2.schema.json").read_text(encoding="utf-8"))
    initial = json.loads(INITIAL.read_text(encoding="utf-8"))
    repair = json.loads(REPAIR.read_text(encoding="utf-8"))
    samples = {sample["sample_id"]: sample for sample in fixtures["samples"]}
    repair_ids = {entry["sample_id"] for entry in repair["candidates"]}
    merged = {entry["sample_id"]: (entry["candidate"], "initial") for entry in initial["candidates"]}
    merged.update({entry["sample_id"]: (entry["candidate"], "repair") for entry in repair["candidates"]})
    if len(initial["candidates"]) != 7 or len(repair_ids) != 3 or set(merged) != set(samples):
        raise RuntimeError("Expected a frozen 7 initial + 3 repair candidate set covering all ten samples")

    gate = load_gate()
    entries = []
    for sample in fixtures["samples"]:
        candidate, attempt = merged[sample["sample_id"]]
        violations = gate.gate_candidate(candidate, sample, schema)
        if violations:
            raise RuntimeError(f"Merged candidate failed gate: {sample['sample_id']}: {violations}")
        entries.append({
            "sample_id": sample["sample_id"],
            "fixture_kind": sample["fixture_kind"],
            "source_attempt": attempt,
            "question": sample["question"],
            "learning_goal": sample["learning_goal"],
            "candidate": candidate,
        })
    result = {
        "artifact_kind": "candidate_output_set",
        "model": "deepseek-v4-flash",
        "schema_version": "open-visual-scene/0.2",
        "initial_pass": 7,
        "repair_pass": 3,
        "candidate_count": 10,
        "entries": entries,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result={OUTPUT} candidates={len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
