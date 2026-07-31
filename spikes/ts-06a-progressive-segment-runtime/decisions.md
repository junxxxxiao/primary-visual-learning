# TS-06A 决策

- 日期：2026-07-31
- 状态：`harness_ready`
- 结论：确定性分段协议与离线运行时 14/14 synthetic 场景通过；未运行真实模型、TTS、视觉或浏览器候选
- 负责人：Codex 实现并运行，用户确认验证范围

## 核心证据

- `lesson-manifest/1.0`、`segment-envelope/1.0` 和 `segment-event/1.0` 三份合同均由固定 Schema 与规范化 SHA-256 身份约束；
- 6/6 gold fixture 到达预期终态；
- 8/8 adversarial fixture 检出预期违规且未污染播放或有效缓存；
- 11 个单元测试通过，包含哈希篡改、非连续 ordinal、关键路径、乱序播放、取消、无效高时间戳和 readiness payload 篡改；
- 14/14 StageTiming trace 通过共享 `stage-timing/1.0` Schema；
- 并行夹具的墙钟关键路径为 2,400ms，重叠局部工作和为 3,900ms，汇总未错误相加；
- 45 秒硬降级在虚拟时钟 45,000ms 精确触发一次；
- 外部请求、Token、候选输出和外部成本均为 0。

证据见 `results/summary.json` 和 `results/audit.json`。

## 失败与修正记录

首轮固定场景为 11/13。取消和超时后的迟到响应虽然均被阻断且缓存污染为 0，但错误码被笼统归类为 lesson terminal。运行时改为优先保留精确的 `event.stale_segment_terminal`，未修改对应 oracle，复跑后为 13/13。

语义审计随后增加连续 ordinal、只允许依赖更早 segment、严格 cue 顺序、“准入后取消清除有效缓存”和“非法事件校验前不得推进虚拟时间或开启 timeout”门禁。最终为 14/14 场景、11/11 单元测试通过。

## 未通过指标与失败样例

当前离线 harness 门槛无未通过项。真实候选指标尚未开始，不属于“通过”：

- 真实 `question_confirmed -> first_meaningful_content` P80 `<8s` 未验证；
- 全新互动场景 P80 `<30s` 未验证；
- 真实 TTS/字幕/视觉 cue P95 `<250ms` 未验证；
- 供应方取消率、浪费 Token、成本、并发和缓存收益未验证。

## 影响

- 对 PRD：不改变用户流程或延迟承诺；仍保留首个有意义内容、互动就绪和硬降级目标；
- 对高保真设计：不改变当前 Demo；未来加载、播放和降级状态应消费统一 segment 状态，不自行推断后端阶段；
- 对架构：允许后续候选围绕 manifest/envelope/event 合同集成；不代表本切片代码可直接进入 `apps/` 或 `packages/`；
- 对数据：仅 synthetic unverified 夹具，不产生学习结果、知识发布状态或生产缓存；
- 对隐私：无儿童媒体、身份数据、教材正文、凭据或生产日志，未发生外部请求。

## 下一步

1. TS-03 后续候选输出可独立校验的 manifest 与首个 segment；
2. TS-04C 后续候选按 segment 生成声明式视觉，并逐段通过 TS-04A/TS-04B 门禁；
3. TS-07 接入真实 TTS、字幕和视觉 cue，验证播放、暂停、恢复、拖动与累计漂移；
4. TS-06 使用真实统一 trace 对比串行、分段串行和分段并行，最终判定 8s/30s/45s 指标；
5. 每次真实候选运行前单独冻结并确认供应商、版本、参数、预算和数据边界。
