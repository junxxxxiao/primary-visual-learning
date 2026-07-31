#!/usr/bin/env python3
"""Prepare the ten contract-passing v0.3 example-guided candidates for Chromium."""
from __future__ import annotations

import json
from pathlib import Path

from run_calibration import load_gate


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "results" / "model-deepseek-v4-flash-official-open-world-v03-flash-example-guided-calibration-round-1.json"
OUTPUT = ROOT / "results" / "candidates-v4-flash-v03-example-guided.json"


def main() -> int:
    fixtures = json.loads((ROOT / "fixtures" / "calibration-inputs.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas" / "open-visual-scene-v0.3.schema.json").read_text(encoding="utf-8"))
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    samples = {sample["sample_id"]: sample for sample in fixtures["samples"]}
    if source.get("schema_version") != "open-visual-scene/0.3":
        raise RuntimeError("Expected a frozen open-visual-scene/0.3 candidate run")
    if source.get("metrics", {}).get("contract_pass") != {"numerator": 10, "denominator": 10}:
        raise RuntimeError("Browser preparation requires the frozen 10/10 contract result")
    if source.get("prompt_profile", {}).get("name") != "v03-complete-format-example/0.1":
        raise RuntimeError("Browser preparation requires the complete-example prompt profile")

    candidates = {entry["sample_id"]: entry["candidate"] for entry in source.get("candidates", [])}
    if len(candidates) != 10 or set(candidates) != set(samples):
        raise RuntimeError("Expected ten unique candidates covering the frozen calibration set")
    gate = load_gate()
    entries = []
    for sample in fixtures["samples"]:
        candidate = candidates[sample["sample_id"]]
        violations = gate.gate_candidate(candidate, sample, schema)
        if violations:
            raise RuntimeError(f"Candidate failed deterministic replay: {sample['sample_id']}: {violations}")
        entries.append({
            "sample_id": sample["sample_id"],
            "fixture_kind": sample["fixture_kind"],
            "source_attempt": "initial",
            "question": sample["question"],
            "learning_goal": sample["learning_goal"],
            "candidate": candidate,
        })
    result = {
        "artifact_kind": "candidate_output_set",
        "model": "deepseek-v4-flash",
        "schema_version": "open-visual-scene/0.3",
        "prompt_profile": source["prompt_profile"],
        "candidate_count": 10,
        "entries": entries,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result={OUTPUT} candidates={len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
