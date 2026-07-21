# 共享 Schema

本目录后续维护切片间的稳定数据契约，例如：

- `QuestionEnvelope`
- `DiagnosisEnvelope`
- `LessonPlan`
- `SceneDefinition`
- `SceneCommand`
- `Snapshot`
- `InteractionEvent`
- `LearningEvidence`

规则：

1. 所有 Schema 有显式版本；
2. 不兼容变更增加主版本；
3. 示例和校验测试随 Schema 提交；
4. 场景命令必须使用白名单和参数范围；
5. 模型输出未经校验不得进入运行时；
6. Schema 中不包含不必要的儿童身份信息。

初始字段建议见 [技术验证文档](../../../docs/technical/2026-07-17-primary-visual-tutor-technical-validation.md#5-共同数据契约)。
