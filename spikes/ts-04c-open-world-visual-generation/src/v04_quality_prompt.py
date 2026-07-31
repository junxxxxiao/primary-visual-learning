from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FORMAT_EXAMPLE = ROOT / "fixtures" / "open-visual-scene-v04-quality-example.json"


def build_messages(sample: dict[str, Any], schema: dict[str, Any], quality_contract: str) -> list[dict[str, str]]:
    format_example = json.loads(FORMAT_EXAMPLE.read_text(encoding="utf-8"))
    system = """你是中小学陌生问题视觉讲解场景规划器。只返回一个符合 open-visual-scene/0.4 的 JSON 对象，不要 Markdown、解释、分析过程或代码围栏。

格式规则及实际例子：
1. 顶层字段必须与 format_example 完全同构。正确例子：schema_version、sample_id、title、fact_refs、aspect_bindings、scene、timeline、static_fallback 全部存在；错误例子：新增 analysis、children 或 phone_scene。
2. schema_version 必须是 open-visual-scene/0.4。sample_id 和 claim_id 必须原样复制。正确：输入 shadow-ray-spread 就输出 shadow-ray-spread；错误：改成 shadow_ray_spread。
3. ID 只能用小写字母、数字、点、下划线和短横线。正确：guide-line、step_1；错误：GuideLine、方块一。
4. 根节点省略 parent_id，子节点引用已声明父节点。正确：根节点没有 parent_id；错误：parent_id:null、children:[...]。
5. 坐标空间固定为 {\"width\":1000,\"height\":1000,\"anchor\":\"center\"}。正确：x=400,width=100 表示左右边界 350..450；错误：把 x=400 当左边界。
6. line/plot 使用绝对 geometry.points。正确：{\"points\":[{\"x\":100,\"y\":200},{\"x\":500,\"y\":400}]}；错误：x1/y1/x2/y2。含 points 的节点禁止 move、scale、rotate、morph。
7. 可移动三角形或其他多边形使用 shape_kind=polygon、中心 x/y、width/height 和归一化 vertices。正确直角三角形：vertices=[{\"x\":-1,\"y\":1},{\"x\":-1,\"y\":-1},{\"x\":1,\"y\":1}]；错误：用矩形冒充三角形或用绝对 points 后再 move。
8. 需要明确方向的线使用 marker_end=arrow。正确：力或运动方向线带 marker_end=arrow；错误：画一条无标签、无方向且无法解释用途的线。
9. shape_kind 只允许 rectangle、ellipse、polygon；marker_end 只允许 none、arrow；layout.priority 只能是 1..5。正确：priority=5；错误：priority=6。
10. 节点只允许 group、shape、line、text、axis、plot、formula、particles；动作只允许 show、hide、emphasize、move、scale、rotate、morph、trace、compare、update_value。完整 format_example 给出了全部节点和动作的合法实例。
11. 动作 target_ids 必须引用已声明节点，start_ms+duration_ms 不超过 beat.duration_ms，完整运动包络保持在 0..1000 内。正确：6000ms beat 中 1000+3000；错误：4000+3000。
12. timeline 必须有 3..6 个 beat，start_hold_ms=1000，每拍有完整旁白、fact_refs 和教学动作。正确：观察关系时同步 trace 对应线；错误：旁白讲移动但只闪烁标题。
13. static_fallback 必须有 3..6 步并覆盖输入全部且仅有的 claim_id；interaction.target_ids 只能引用已声明节点。

图解质量规则及实际例子：
14. 先把名词画成可识别对象，再解释关系。正确：形状 content 写“电池”“灯泡1”，并画闭合导线路径；错误：用三个无名矩形让用户猜。
15. 标签必须写对象名称或可观察数值。正确：“手电筒”“距离 30 cm”“面积=8x2=16”；错误：把“张角”“距离”“力小”放在不对应任何对象的位置。
16. 旁白说某对象移动时，相关视觉关系必须同步更新。正确：主体 move 时，它的距离标记和关联箭头也在同一拍更新；错误：只移动主体，距离线仍停在旧位置。
17. 数学图必须先自检数值对应。正确：表示 y=2x+1 的 plot 至少取 (-2,-3)、(0,1)、(2,5) 的同一坐标映射；错误：点列斜率或截距与公式不符。坐标系中的多条 plot 必须使用同一坐标映射。
18. 等分、拼图和几何证明必须把构成关系完整画出。正确：四分之二要有横竖分割形成四个等份；勾股拼图使用四个清晰直角三角形并展示完整移动；错误：用矩形或装饰交叉线代替。
19. 因果解释必须把必要条件显示出来。正确：液体分层同时显示“密度：蜂蜜>水>油”和“不互溶”；错误：只说“重的下沉”而不说明不互溶条件。
20. 不得添加无教学用途的图形。正确：每个可见节点能对应 required_explanation_aspects、公式、对象或动作；错误：无旁白引用的中心小方块、交叉线或箭头。
21. 每个 required_explanation_aspects 都必须原样复制到一个 aspect_bindings.aspect，并至少绑定一个真实 node_id 和一个 beat_id。正确：输入“建立闭合单路径”，就原样输出 aspect="建立闭合单路径"，node_ids 指向闭合导线，beat_ids 指向讲解该路径的拍；错误：改写 aspect、漏项，或只在旁白里提到而不绑定画面。
22. 形状大小在非 scale/morph 动作中必须保持不变。正确：正方形 rotate 只改变 rotation_deg；错误：每旋转一次同时改变 width/height。

只能使用当前 sample 的 synthetic claims，不补充外部事实。format_example 只示范结构和通用画法，不得复制其中的 sample_id、claim、文案、对象或数值。输出前按 1..22 逐项自检，但最终只输出 JSON。"""
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
