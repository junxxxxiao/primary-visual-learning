from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FORMAT_EXAMPLE = ROOT / "fixtures" / "open-visual-scene-v03-format-example.json"


def build_messages(sample: dict[str, Any], schema: dict[str, Any], quality_contract: str) -> list[dict[str, str]]:
    format_example = json.loads(FORMAT_EXAMPLE.read_text(encoding="utf-8"))
    system = """你是中小学陌生问题视觉讲解场景规划器。只返回一个符合 open-visual-scene/0.3 的 JSON 对象，不要 Markdown、解释或代码围栏。

必须逐项遵守以下格式规则，并以输入中的 format_example 为唯一结构示范：
1. 顶层必须包含 schema_version、sample_id、title、fact_refs、scene、timeline、static_fallback；interaction 只能按 Schema 格式出现。只复制结构，不得复制示例的 sample_id、fact_refs、文案或数值。
2. schema_version 必须是 open-visual-scene/0.3。sample_id 和全部 claim_id 必须从当前 sample 原样复制，不得改写、翻译或新增。
3. ID 只能使用小写英文字母、数字、点、下划线和短横线，并以小写字母或数字开头。正确：guide-line、step_1；错误：GuideLine、方块一。
4. 根节点必须省略 parent_id，严禁填写 null。子节点的 parent_id 必须引用已经声明的节点。严禁输出 children，也不得输出 Schema 没有列出的任何字段。
5. scene.coordinate_space 必须精确为 {"width":1000,"height":1000,"anchor":"center"}。geometry.x/y 和动作 to.x/to.y 都是元素中心点；width/height 从中心向两侧各延伸一半。
6. line 和 plot 节点必须使用 geometry.points，例如 {"points":[{"x":100,"y":200},{"x":500,"y":400}]}。严禁使用 x1、y1、x2、y2。含 points 的节点严禁使用 move、scale、rotate 或 morph。
7. layout.priority 只能是 1 到 5 的整数。正确：{"priority":5}；错误：{"priority":6}。flow、allow_reflow、style_token、role 和 type 只能使用 Schema 枚举值。
8. 节点只允许 group、shape、line、text、axis、plot、formula、particles；format_example 分别给出了八种正确实例。
9. 动作只允许 show、hide、emphasize、move、scale、rotate、morph、trace、compare、update_value；format_example 分别给出了十种正确实例。target_ids 必须全部引用已声明节点，to 只能包含 Schema 允许的字段。
10. 每个动作的 start_ms + duration_ms 不得超过所属 beat.duration_ms。完整移动、缩放、旋转和变形包络必须保持在 0..1000 内。
11. timeline 必须包含 3 到 6 个 beat，start_hold_ms 必须是 1000；每个 beat 都必须有完整旁白、事实引用和至少一个动作。旁白、视觉动作与 fact_refs 必须逐拍对应。
12. interaction.target_ids 必须引用已声明节点。static_fallback 必须有 3 到 6 个完整步骤，并使用当前 sample 的全部且仅有的 claim_id。
13. 只能使用当前 sample 的 synthetic claims，不补充外部事实；不得输出 JavaScript、HTML、CSS、SVG 字符串、外部 URL、手机专版或平板专版。

输出前逐字段对照 required_output_schema 和 format_example 自检。format_example 仅示范格式，不是题目内容，也不是可复用答案。"""
    payload = {
        "fixture_kind": sample["fixture_kind"],
        "source_kind": "synthetic_unverified",
        "sample": sample,
        "quality_reference_contract": quality_contract,
        "required_output_schema": schema,
        "format_example": format_example,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]
