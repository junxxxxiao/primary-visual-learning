#!/usr/bin/env python3
"""Create ten synthetic gold DSL fixtures from the frozen TS-04C sample ids."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "ts-04c-real-visual-consistency" / "fixtures" / "calibration-inputs.json"

SCENES = {
    "primary_sound.opening-explanation": ("comparison", "同一根琴弦", ["轻拨", "用力拨"], "science-green", "signal-coral"),
    "primary_sound.compare": ("comparison", "振幅与音调", ["振幅变大", "音调不变"], "science-green", "focus-yellow"),
    "primary_sound.separate": ("sequence", "分清两个变化", ["用力", "振幅", "响度"], "science-green", "signal-coral"),
    "primary_sound_pair.pair-opening-explanation": ("comparison", "橡皮筋对比", ["轻拨", "用力拨"], "science-green", "signal-coral"),
    "primary_sound_pair.pair-reveal": ("sequence", "观察变化", ["振幅变大", "声音更响", "音调不变"], "science-green", "focus-yellow"),
    "middle_perfect_square.model": ("area_model", "建立面积模型", ["2x+y=总长", "A=x*y"], "math-blue", "focus-yellow"),
    "middle_perfect_square.complete": ("area_model", "完成配方", ["展开", "配方", "最大值"], "math-blue", "signal-coral"),
    "middle_perfect_square.justify": ("sequence", "解释最大值", ["平方非负", "负平方不大于0", "顶点取最大"], "math-blue", "focus-yellow"),
    "middle_sound_pair.wave-compare": ("wave", "波形对比", ["振幅增大", "周期不变"], "math-blue", "signal-coral"),
    "middle_sound_pair.wave-explain": ("wave", "波形与听感", ["振幅", "响度", "频率"], "math-blue", "focus-yellow"),
}


def main() -> int:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    specs = []
    for sample in source["samples"]:
        scene_type, title, labels, primary, accent = SCENES[sample["sample_id"]]
        facts = [claim["claim_id"] for claim in sample["claims"]]
        specs.append({
            "fixture_kind": "gold_fixture",
            "source_input_hash": sample["input_hash"],
            "spec": {
                "schema_version": "visual-dsl/0.1",
                "sample_id": sample["sample_id"],
                "scene_id": sample["sample_id"].replace(".", "-"),
                "scene_type": scene_type,
                "title": title,
                "labels": labels,
                "facts": facts,
                "color_tokens": {"primary": primary, "accent": accent},
                "interaction": "compare" if scene_type in {"comparison", "wave"} else "none",
                "static_fallback": {"steps": sample["static_fallback"]["steps"], "fact_refs": sample["static_fallback"]["fact_refs"]},
            },
        })
    output = {"fixture_version": "visual-dsl-gold/0.1", "sample_count": len(specs), "specs": specs}
    (ROOT / "fixtures" / "specs.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(specs)} DSL fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
