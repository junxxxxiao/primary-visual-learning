#!/usr/bin/env python3
"""Run the authorized V4 Flash v0.4 semantic-quality calibration."""
from __future__ import annotations

import run_v03_calibration as runner
from src.v04_quality_prompt import build_messages


RUN_LABEL = "official-open-world-v04-flash-quality-guided-calibration-round-1"
PROMPT_PROFILE = {
    "name": "v04-semantic-quality-example/0.1",
    "format_example_kind": "gold_fixture",
    "format_example_source": "synthetic_format_only",
    "format_example_sha256": "619d6eaf0ccad12a98441d0186f6ea89dd760475c272511853bb51a8cbc58f5f",
    "prompt_builder_sha256": "42a8ba60d2c0aa1430c129a66332a54f689d6b2b721e6c4d35b101875fef6735",
    "quality_rules": 22,
}


if __name__ == "__main__":
    raise SystemExit(runner.main(
        run_label=RUN_LABEL,
        prompt_builder=build_messages,
        prompt_profile=PROMPT_PROFILE,
        schema_version="open-visual-scene/0.4",
        schema_filename="open-visual-scene-v0.4.schema.json",
        slice_id="TS-04C-v4",
    ))
