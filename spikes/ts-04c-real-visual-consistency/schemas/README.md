# TS-04C Schema

`full-question-lesson.schema.json` 约束一道完整题的 4 段讲解、通用受限图元和局部时间轴；它不允许 JavaScript、HTML、SVG、外部资源或任意表达式。

`visual-relation-requirements.schema.json` 约束上游讲解计划交给本地门禁的对象关系要求。关系包独立于候选输出，使用段序、语义选择器、可测属性和 `gt | eq | lt` 运算符描述必须成立的视觉关系；模型不能通过改写旁白或标签绕过检查。

本切片复用：

- TS-03 `schemas/lesson-plan.schema.json`（`lesson-plan/1.3`）；
- TS-04B `schemas/visual-scene.schema.json`（`visual-scene/1.0`）；
- `spikes/shared/schemas/stage-timing.schema.json`（`stage-timing/1.0`）。

候选生成输出契约确认后再增加本切片专属 Schema。
