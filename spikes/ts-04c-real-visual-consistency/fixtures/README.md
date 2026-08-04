# TS-04C 夹具

`full-question-egg-saltwater-v01.json` 是一道 synthetic unverified 完整题输入，只用于验证问题级讲解生成、分段串接和门禁行为，不是教材或权威知识证据。

`full-question-egg-saltwater-v01.visual-relations.json` 是独立的 `gold_fixture` 关系要求包，仍标记为 `synthetic_unverified`。它把第三段“浮力大于重力”和第四段“浮力等于重力”转换为可测的箭头高度关系，用于复现并阻断当前候选的语义错误；它不证明这些合成 claim 是真实教材事实。

正式夹具尚未导入。计划复用 TS-03 的四个 `gold_fixture` 讲解计划，并在候选对象确认后扩展为小学/初中各 20 个冻结输入；TS-04B 的失败案例作为 `adversarial_fixture`。

当前目录不含真实儿童媒体、受控教材正文或候选模型输出。
