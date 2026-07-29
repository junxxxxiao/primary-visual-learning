# 共享 Schema

本目录后续维护切片间的稳定数据契约，例如：

- `QuestionEnvelope`
- `StageProfile`
- `DiagnosisEnvelope`
- `LessonPlan`
- `SceneDefinition`
- `SceneCommand`
- `Snapshot`
- `InteractionEvent`
- `LearningEvidence`
- `StageTiming`

规则：

1. 所有 Schema 有显式版本；
2. 不兼容变更增加主版本；
3. 示例和校验测试随 Schema 提交；
4. 场景命令必须使用白名单和参数范围；
5. 模型输出未经校验不得进入运行时；
6. Schema 中不包含不必要的儿童身份信息。

`stage-timing.schema.json` 是所有切片共用的分段计时契约。里程碑只标记时间点，不伪装成耗时；`question_confirmed` 是用户感知等待的零时刻。用户阅读、修改和决定是否确认的时间必须标为 `user_action_excluded`，不得计入系统生成性能。并行 span 使用同一单调时钟记录，端到端耗时不得由局部耗时简单相加。

初始字段建议见 [技术验证 v3](../../../docs/technical/2026-07-28-primary-visual-tutor-technical-validation-v3.md#2-公共契约)。
