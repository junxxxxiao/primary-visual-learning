#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
TS02_EXPORT = ROOT.parent / "ts-02-knowledge-validation" / "results" / "knowledge-packages.json"

PACKAGE_BY_FIXTURE = {
    "primary_sound": "primary_sound_valid",
    "primary_sound_pair": "primary_sound_valid",
    "middle_perfect_square": "middle_perfect_square_valid",
    "middle_sound_pair": "middle_sound_pair_valid",
}

CLAIM_ID_MIGRATIONS = {
    "primary_sound": {
        "sound-force-amplitude": "force-amplitude-pitch",
        "sound-pitch-frequency": "pitch-frequency-loudness-amplitude",
    },
    "primary_sound_pair": {"pair-relation": "force-amplitude-pitch"},
    "middle_perfect_square": {
        "square-identity": "perfect-square-identities",
        "square-bound": "complete-square-bound",
        "fence-model": "fence-transfer",
    },
    "middle_sound_pair": {
        "pair-relation": "force-amplitude-frequency",
        "perception-map": "wave-perception-map",
    },
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def migrate(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: migrate(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [migrate(item, replacements) for item in value]
    if isinstance(value, str):
        return replacements.get(value, value)
    return value


def main() -> int:
    exports = load(TS02_EXPORT)["packages"]
    plans_path = ROOT / "fixtures" / "plans.json"
    policies_path = ROOT / "fixtures" / "policies.json"
    cases_path = ROOT / "fixtures" / "cases.json"
    plans_data = load(plans_path)
    policies_data = load(policies_path)
    cases_data = load(cases_path)

    for fixture_id, package_case_id in PACKAGE_BY_FIXTURE.items():
        plan = migrate(plans_data["plans"][fixture_id], CLAIM_ID_MIGRATIONS[fixture_id])
        plan["knowledge"] = exports[package_case_id]
        plans_data["plans"][fixture_id] = plan
        policies_data["policies"][fixture_id] = migrate(
            policies_data["policies"][fixture_id],
            CLAIM_ID_MIGRATIONS[fixture_id],
        )

    for case in cases_data["cases"]:
        fixture_id = case["base_plan"]
        case.update(migrate(case, CLAIM_ID_MIGRATIONS[fixture_id]))

    write(plans_path, plans_data)
    write(policies_path, policies_data)
    write(cases_path, cases_data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
