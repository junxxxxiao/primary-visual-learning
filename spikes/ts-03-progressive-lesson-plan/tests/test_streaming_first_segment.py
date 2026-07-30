from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from run_streaming_first_segment import (  # noqa: E402
    official_request_payload,
    parse_sse_data,
    validate_official_base_url,
)


class StreamingParserTests(unittest.TestCase):
    def test_ignores_non_data_lines(self) -> None:
        self.assertIsNone(parse_sse_data(b"event: message\n"))

    def test_parses_json_data_event(self) -> None:
        event = {"choices": [{"delta": {"content": "{"}}]}
        line = "data: " + json.dumps(event) + "\n"
        self.assertEqual(parse_sse_data(line), event)

    def test_recognizes_done_event(self) -> None:
        self.assertEqual(parse_sse_data("data: [DONE]\n"), "done")

    def test_official_payload_disables_thinking_and_streams_json(self) -> None:
        fixture = {
            "fixture_id": "primary_sound",
            "stage_profile": {},
            "stage_rules": {},
            "knowledge": {},
            "core_relation": "test",
            "primary_object": "test",
        }
        payload = official_request_payload("deepseek-v4-pro", fixture, {})

        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertTrue(payload["stream"])
        self.assertEqual(payload["temperature"], 0)

    def test_official_base_url_accepts_deepseek_host(self) -> None:
        validate_official_base_url("https://api.deepseek.com")
        validate_official_base_url("https://api.deepseek.com/v1")

    def test_official_base_url_rejects_aggregator(self) -> None:
        with self.assertRaises(RuntimeError):
            validate_official_base_url("https://example.invalid/v1")


if __name__ == "__main__":
    unittest.main()
