#!/usr/bin/env python3
"""Validate only the two user-authorized chapter ranges."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from controlled_sources import validate_controlled_sources  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--science-pdf", required=True)
    parser.add_argument("--math-pdf", required=True)
    args = parser.parse_args()

    manifest = json.loads((ROOT / "fixtures/controlled-sources.json").read_text(encoding="utf-8"))
    paths = {
        "controlled-primary-science-grade4-volume1": args.science_pdf,
        "controlled-middle-math-grade8-volume1": args.math_pdf,
    }
    result = validate_controlled_sources(manifest, paths)
    output = ROOT / "results/controlled-summary.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"verdict={result['verdict']}")
    for claim in result["evidence_results"]:
        print(f"{claim['claim_id']}: expected={claim['expected']} observed={claim['observed']}")
    print(f"current_full_math_demo_package={result['package_decisions']['current_full_math_demo_package']}")
    return 0 if result["verdict"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
