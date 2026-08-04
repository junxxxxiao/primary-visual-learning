#!/usr/bin/env python3
"""Diagnostic replay of frozen v0.1 responses against v0.2; not candidate evidence."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from run_calibration import load_gate


ROOT = Path(__file__).resolve().parent
ROUND1 = ROOT / "results" / "model-deepseek-v4-pro-official-open-world-calibration-round-1.json"
OUTPUT = ROOT / "results" / "diagnostic-replay-round1-against-v0.2.json"


def main() -> int:
    fixtures = json.loads((ROOT / "fixtures" / "calibration-inputs.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas" / "open-visual-scene-v0.2.schema.json").read_text(encoding="utf-8"))
    round1 = json.loads(ROUND1.read_text(encoding="utf-8"))
    samples = {sample["sample_id"]: sample for sample in fixtures["samples"]}
    gate = load_gate()
    records = []

    for call in round1["call_results"]:
        raw_path = ROOT / "results" / "raw" / "deepseek-v4-pro" / round1["run_label"] / f"{call['sample_id']}.json"
        response = json.loads(raw_path.read_text(encoding="utf-8"))
        candidate = json.loads(response["choices"][0]["message"]["content"])
        replay = deepcopy(candidate)
        replay["schema_version"] = "open-visual-scene/0.2"
        violations = gate.gate_candidate(replay, samples[call["sample_id"]], schema)
        records.append({"sample_id": call["sample_id"], "v0_1_gate_pass": call["gate_pass"], "v0_2_diagnostic_gate_pass": not violations, "violations": violations})

    result = {
        "kind": "diagnostic_replay",
        "candidate_output": False,
        "source_run": ROUND1.name,
        "schema_version": "open-visual-scene/0.2",
        "mutation": "schema_version_only",
        "metrics": {"pass_count": sum(record["v0_2_diagnostic_gate_pass"] for record in records), "sample_count": len(records)},
        "records": records,
        "limits": ["This replay changes the declared schema version after generation and is not candidate evidence.", "It only tests whether v0.2 removes known interface-caused failures."],
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result={OUTPUT} pass={result['metrics']['pass_count']}/{result['metrics']['sample_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
