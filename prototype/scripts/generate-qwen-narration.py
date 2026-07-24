#!/usr/bin/env python3
"""Generate the fixed Demo narration with Qwen TTS and save local WAV files."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import wave
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROTOTYPE_DIR = SCRIPT_DIR.parent
DEFAULT_MANIFEST = SCRIPT_DIR / "narration-content.json"
DEFAULT_ENV_FILE = PROTOTYPE_DIR / ".env"
DEFAULT_AUDIO_DIR = PROTOTYPE_DIR / "assets" / "audio"


def load_local_env(path: Path) -> None:
    """Load simple KEY=VALUE pairs without adding another runtime dependency."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"").strip("'")
        if key and value:
            os.environ.setdefault(key, value)


def value_at(container: Any, key: str, default: Any = None) -> Any:
    if isinstance(container, dict):
        return container.get(key, default)
    return getattr(container, key, default)


def response_audio(response: Any) -> tuple[bytes, str]:
    output = value_at(response, "output")
    audio = value_at(output, "audio")
    if not audio:
        raise RuntimeError("DashScope response did not include output.audio")

    url = value_at(audio, "url")
    encoded = value_at(audio, "data")
    if isinstance(audio, str) and audio.startswith(("http://", "https://")):
        url = audio

    if url:
        request = urllib.request.Request(str(url), headers={"User-Agent": "sound-value-demo/1.0"})
        with urllib.request.urlopen(request, timeout=60) as download:
            return download.read(), download.headers.get_content_type()
    if encoded:
        return base64.b64decode(encoded), "application/octet-stream"
    raise RuntimeError("DashScope response audio had neither a URL nor base64 data")


def convert_to_wav(audio_bytes: bytes, content_type: str, destination: Path) -> None:
    suffix_by_type = {
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/aac": ".aac",
        "audio/ogg": ".ogg",
    }
    input_suffix = suffix_by_type.get(content_type, ".audio")
    if audio_bytes.startswith(b"RIFF"):
        input_suffix = ".wav"
    elif audio_bytes.startswith(b"ID3") or audio_bytes[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}:
        input_suffix = ".mp3"
    afconvert = shutil.which("afconvert")
    if not afconvert:
        raise RuntimeError("afconvert was not found; this generator currently targets macOS")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="qwen-tts-") as temporary_directory:
        temporary = Path(temporary_directory)
        source = temporary / f"source{input_suffix}"
        converted = temporary / "converted.wav"
        source.write_bytes(audio_bytes)
        subprocess.run(
            [afconvert, "-f", "WAVE", "-d", "LEI16@44100", str(source), str(converted)],
            check=True,
            capture_output=True,
            text=True,
        )
        validate_wav(converted)
        os.replace(converted, destination)


def validate_wav(path: Path) -> None:
    with wave.open(str(path), "rb") as wav_file:
        if wav_file.getnframes() <= 0 or wav_file.getframerate() <= 0:
            raise RuntimeError(f"Generated audio is empty: {path.name}")


def promote_variants(clips: list[dict[str, str]], suffix: str) -> None:
    sources: list[tuple[Path, Path]] = []
    for clip in clips:
        source = DEFAULT_AUDIO_DIR / f"narration-{clip['name']}-{suffix}.wav"
        destination = DEFAULT_AUDIO_DIR / f"narration-{clip['name']}.wav"
        if not source.exists():
            raise RuntimeError(f"Versioned audio is missing: {source.name}")
        validate_wav(source)
        sources.append((source, destination))

    for source, destination in sources:
        temporary = destination.with_suffix(".wav.promoting")
        shutil.copy2(source, temporary)
        validate_wav(temporary)
        os.replace(temporary, destination)
        print(f"Promoted {source.name} -> {destination.name}")


def generate_clip(
    dashscope: Any,
    manifest: dict[str, Any],
    clip: dict[str, str],
    api_key: str,
    output_suffix: str = "",
) -> Path:
    name = clip["name"]
    instructions = clip.get("instructions", manifest["instructions"])
    response = dashscope.MultiModalConversation.call(
        model=manifest["model"],
        api_key=api_key,
        text=clip["text"],
        voice=manifest["voice"],
        instructions=instructions,
        optimize_instructions=True,
        stream=False,
    )

    status_code = value_at(response, "status_code", 200)
    if status_code != 200:
        request_id = value_at(response, "request_id", "unknown")
        code = value_at(response, "code", "unknown")
        message = value_at(response, "message", "DashScope request failed")
        raise RuntimeError(f"DashScope error {status_code} ({code}, request {request_id}): {message}")

    audio_bytes, content_type = response_audio(response)
    suffix = f"-{output_suffix}" if output_suffix else ""
    destination = DEFAULT_AUDIO_DIR / f"narration-{name}{suffix}.wav"
    convert_to_wav(audio_bytes, content_type, destination)
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--only", action="append", default=[], help="Generate one named clip; repeat as needed")
    parser.add_argument("--voice", help="Override the manifest voice for a local comparison")
    parser.add_argument(
        "--output-suffix",
        default="",
        help="Write a separate candidate such as narration-main-1-candidate-2.wav",
    )
    parser.add_argument(
        "--promote-suffix",
        default="",
        help="Promote an already-generated versioned batch to the active narration filenames",
    )
    parser.add_argument(
        "--include-approved",
        action="store_true",
        help="Include clips that already declare an approved_file",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration without calling DashScope")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for option_name, suffix in (("--output-suffix", args.output_suffix), ("--promote-suffix", args.promote_suffix)):
        if suffix and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", suffix):
            raise RuntimeError(f"{option_name} must use lowercase letters, numbers, and hyphens")
    if args.output_suffix and args.promote_suffix:
        raise RuntimeError("Use either --output-suffix or --promote-suffix, not both")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.voice:
        manifest["voice"] = args.voice
    clips = manifest["clips"]
    if args.only:
        selected = set(args.only)
        clips = [clip for clip in clips if clip["name"] in selected]
        missing = selected - {clip["name"] for clip in clips}
        if missing:
            raise RuntimeError(f"Unknown clip name(s): {', '.join(sorted(missing))}")
    if not args.include_approved:
        clips = [clip for clip in clips if not clip.get("approved_file")]

    names = [clip["name"] for clip in clips]
    if len(names) != len(set(names)):
        raise RuntimeError("Narration manifest contains duplicate clip names")
    if args.dry_run:
        print(f"Validated {len(clips)} clips · model={manifest['model']} · voice={manifest['voice']}")
        return 0
    if args.promote_suffix:
        promote_variants(clips, args.promote_suffix)
        return 0

    load_local_env(args.env_file)
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is missing. Copy prototype/.env.example to prototype/.env "
            "and fill it locally, or export DASHSCOPE_API_KEY in the current shell."
        )

    try:
        import dashscope
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "dashscope is not installed. Run: python3 -m pip install -r "
            "prototype/scripts/requirements-tts.txt"
        ) from error

    dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
    for index, clip in enumerate(clips, start=1):
        print(f"[{index}/{len(clips)}] Generating {clip['name']}…", flush=True)
        destination = generate_clip(dashscope, manifest, clip, api_key, args.output_suffix)
        print(f"      wrote {destination.relative_to(PROTOTYPE_DIR)}", flush=True)
    print("Qwen narration generation complete.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
