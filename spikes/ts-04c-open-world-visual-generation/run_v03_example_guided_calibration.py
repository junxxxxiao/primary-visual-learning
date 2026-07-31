#!/usr/bin/env python3
"""Run the authorized V4 Flash v0.3 calibration with a complete format example."""
from __future__ import annotations

import run_v03_calibration as runner
from src.v03_example_prompt import build_messages


RUN_LABEL = "official-open-world-v03-flash-example-guided-calibration-round-1"
PROMPT_PROFILE = {
    "name": "v03-complete-format-example/0.1",
    "format_example_kind": "gold_fixture",
    "format_example_source": "synthetic_format_only",
    "format_example_sha256": "5322f17e9a6df778b29e3ed30ee8bd17973f29c286414307fa2440b9f38e3fe0",
    "prompt_builder_sha256": "83ab2171804d3b96603c444349164d3ecb361a350e13418cfc684de731407266",
}


if __name__ == "__main__":
    raise SystemExit(runner.main(run_label=RUN_LABEL, prompt_builder=build_messages, prompt_profile=PROMPT_PROFILE))
