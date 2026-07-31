# TS-06A 分段协议与离线运行时

> 状态：`harness_ready`（14/14 deterministic synthetic 场景通过；未调用外部候选）  
> 对应验证文档：`docs/technical/2026-07-28-primary-visual-tutor-technical-validation-v3.md`

## 唯一验证问题

确定性离线运行时能否接收独立准备的讲解 segment，保持 session 与 manifest 隔离，在不绕过知识、视觉和缓存准入门禁的前提下重叠视觉与音频准备，并正确处理播放顺序、取消、超时、迟到响应和硬降级？

## 被测对象与授权

- 被测对象：TS-06A 本地协议、虚拟时钟和状态机 harness；
- 供应商：无；
- 固定版本：`lesson-manifest/1.0`、`segment-envelope/1.0`、`segment-event/1.0`、`stage-timing/1.0`；
- 调用方式：本地 Python 3 标准库，确定性离线执行；
- 固定参数：segment readiness timeout 8,000ms，lesson hard deadline 45,000ms；
- 调用预算：外部请求 0，Token 0，外部成本 CNY 0；
- 数据边界：仅 synthetic `gold_fixture` / `adversarial_fixture`，无教材正文、儿童数据或生产日志；
- 用户确认记录：2026-07-31，用户确认只做离线协议与模拟调度，最终状态仅为 `harness_ready`；
- 当前状态：`harness_ready`。

本轮没有候选模型、TTS 服务或浏览器运行时。所有夹具都不是 `candidate_output`，不得计入候选能力分母。

## 不验证什么

- 不验证真实模型或 TTS 的延迟、流式行为、质量、成本和稳定性；
- 不验证真实视觉生成、TS-04A 沙箱、TS-04B 布局门禁或 TS-04C 动画质量；
- 不验证 TS-07 的真实音频、字幕、动画 cue、暂停、恢复和拖动；
- 不验证浏览器、设备、网络、生产并发或故障恢复；
- 不用 synthetic 时间证明 TS-06 的 8s/30s 产品延迟目标已经通过。

## 假设

如果讲解计划、视觉、音频和准入结果使用稳定的 segment 身份与事件协议独立到达，那么运行时可以按关键路径而非局部耗时相加计算墙钟时间，并在重复、乱序、取消、超时和旧版本事件存在时仍保证每段最多播放一次、严格按 manifest 顺序播放且失败产物不进入有效缓存。

## 输入与输出契约

- `schemas/lesson-manifest.schema.json`：问题级 session、知识包身份和有序 segment 清单；
- `schemas/segment-envelope.schema.json`：独立 segment 的旁白、cue、视觉/音频/准入/降级引用和完整身份；
- `schemas/segment-event.schema.json`：封闭事件集合、幂等 ID、身份元组、虚拟单调时间和缓存状态；
- `spikes/shared/schemas/stage-timing.schema.json`：跨切片统一 trace。

运行时只在 envelope、visual、audio 和 admission 四项全部就绪时派生 `segment_playable`：

```text
segment_playable = max(segment_ready, visual_ready, audio_ready, admission_ready)
```

`segment_playable`、`fallback` 和 `lesson_complete` 是运行时拥有的派生事件；外部输入不能直接声明这些状态。

## 固定夹具

`fixtures/base-protocol.json` 只包含 synthetic 协议模板；运行器生成 manifest/envelope 哈希并在任何事件处理前校验。`fixtures/scenarios.json` 包含：

- 6 个 `gold_fixture`：完整计划串行、segment 并行、首段独立、缓存准入、后段先就绪、单段降级后继续；
- 8 个 `adversarial_fixture`：重复/冲突重复、跨 session/旧 manifest、取消后迟到、缺音频超时、准入后取消、45 秒硬降级、伪造运行时事件、Schema 缺字段。

运行时单元测试另覆盖 manifest 哈希篡改、非连续 ordinal、event payload hash 篡改和 envelope/hash 绑定。

## 证据来源

全部输入为 synthetic，`verification_status=synthetic_unverified`。`knowledge_package_hash`、视觉/音频 artifact hash 和 admission 引用仅用于验证身份传播及门禁行为，不表示上游知识、视觉或音频真实通过。

本切片没有已核验教材 claim，不消费或生成可发布知识包，也不升级任何来源状态。

## 运行环境与方式

记录环境：macOS 26.5.2 arm64、Python 3.9.6、虚拟单调时钟、无外部服务。

从仓库根目录运行：

```bash
python3 -m unittest discover -s spikes/ts-06a-progressive-segment-runtime/tests -v
python3 spikes/ts-06a-progressive-segment-runtime/run_validation.py
python3 -m unittest discover -s spikes/shared/tests -v
```

第二条命令会重写 `results/summary.json` 和 `results/audit.json`。

## 指标与结果

| 指标 | 门槛 | 当前结果 |
|---|---:|---:|
| gold fixture 预期终态到达率 | 100% | 6/6，100% |
| 已知 adversarial 行为检出率 | 100% | 8/8，100% |
| 全部固定场景 | 100% | 14/14，100% |
| 跨 session / 旧版本 / 取消 / 超时缓存污染 | 0 | 0 |
| 非法 StageTiming trace | 0 | 0 |
| manifest 顺序外启动 | 0 次成功 | 违规启动被拦截 |
| 45 秒未就绪硬降级 | 100% | 1/1，45,000ms 精确触发 |
| 并行关键路径计算 | 不得相加重叠 span | 2,400ms 关键路径，3,900ms 局部工作和 |

首个可播放时间、首段/视觉/音频就绪和 fallback 均写入相同虚拟单调时钟。这里的毫秒数只证明计算方式和状态转换，不是实际产品延迟。

结构化汇总见 `results/summary.json`，逐事件、派生事件、完整 trace 和状态快照见 `results/audit.json`。

## 决策

结论为 `harness_ready`。离线协议和调度 harness 足以作为 TS-03/TS-04C 分段候选及 TS-07 真实时间轴的集成入口，但没有真实候选运行，因此不能标记为 `candidate_run_complete`、`conditional_pass` 或 `pass`。

完整影响与限制见 `decisions.md`。

## 已知限制

- 当前状态机是技术切片，不是生产运行时；
- 上游 artifact 和门禁结果都是 synthetic opaque references；
- 未测网络背压、真实 SSE、进程并发、供应商取消语义和计费浪费；
- 未测音画 cue 偏差、累计漂移、浏览器前后台和设备切换；
- 真实候选运行前仍须重新确认供应商、模型/服务版本、调用参数、预算和数据边界。
