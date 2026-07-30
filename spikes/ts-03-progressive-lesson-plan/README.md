# TS-03 渐进讲解与迁移规划

> 状态：`pass`；DeepSeek 官方 round 5 为 4/4 返回、Schema 4/4，修正前置知识术语误报后合同 4/4，人工学科与产品审核 4/4 通过
>
> 性质：抛弃式技术可行性 spike，不是生产实现
>
> 对应验证文档：`docs/technical/2026-07-28-primary-visual-tutor-technical-validation-v3.md`
>
> 实现基线：`origin/main` at `da6698bc1927fa41c3a105d403a6ac6749a70fd3`

## 被测对象与授权

- 被测对象：`deepseek-v4-pro` 候选讲解规划模型
- 供应商：历史 `round-3` 使用 PackyAPI 聚合入口；后续首段和完整候选轮使用 DeepSeek 官方 API，两者结果分别记录、不得互相外推
- 固定版本：请求模型标识 `deepseek-v4-pro`，实际响应模型标识与响应哈希逐例记录
- 调用方式：OpenAI 兼容 `POST /chat/completions`
- 固定参数：`temperature=0`、JSON object 输出、零自动重试；官方轮次固定 `thinking.type=disabled`，首段诊断另固定 `stream=true`
- 调用预算：固定 4 个合成样例、最多 4 次请求
- 数据边界：只发送仓库内合成知识、学段规则、问题和输出 Schema；不发送受控教材正文或儿童数据
- 用户确认记录：2026-07-29，用户明确指定 `deepseek-v4-pro` 和 PackyAPI；2026-07-30，用户更新本地配置并明确要求改用 DeepSeek 官方 API 复测
- 当前状态：`pass`；official full round 5 已按 `lesson-plan/1.3` 执行，冻结输出经前置知识感知门禁免费复判后为 4/4，人工学科与产品审核为 4/4

## 唯一可证伪问题

冻结模型能否只使用 TS-02 已核验知识，在保留明确学段规则的前提下，为小学声音、初中完全平方公式和同一声音关系的小学/初中配对夹具生成 2–4 段渐进讲解；用户确认问题后首段直接提供实质讲解，每段同时包含完整旁白、时间线 cue、视觉场景合同与静态降级，并生成要求结论和原因、失败后更换对象的迁移任务？

本分支先回答其前置问题：一个不信任模型自报状态的确定性门禁，能否接受 4 个合规冻结计划，并拦截已知顺序、学段、答案泄露、换皮迁移、静态降级和来源引用违规。真实模型未运行时，不得把门禁通过写成 TS-03 通过。

## 不验证什么

- 不验证儿童是否真正理解、学习效果或家庭使用价值；
- 不验证 TS-04C 的真实视觉代码、安全沙箱、布局实测或主设计语言质量；
- 不验证 TS-07 的真实配音、字幕、动画和进度同步；
- 不验证生产延迟、并发、缓存、供应商稳定性或全年级泛化；
- 不把人工编写的正向计划当作真实模型能力证据；
- 不初始化 `apps/` 或 `packages/`，不锁定生产框架。

## 合同与职责

- `schemas/lesson-plan.schema.json` 当前为 `lesson-plan/1.3`，要求 2–4 段且全部为 `explanation` phase、完整 `StageProfile`、学段规则、TS-02 密封知识包、完整旁白、时间线、视觉合同、逐段静态降级和带实质差异维度的两级迁移任务；
- 三个模型运行入口会在产生 API 费用前重新校验 TS-02 导出内容、知识包哈希、来源清单哈希、来源文件哈希、页码和证据摘录；TS-03 不再允许手工新增 claim 或升级核验状态；
- `src/validator.py` 从计划内容重新计算门禁结果，不接受 `valid`、`stage_fit` 等模型自报布尔值；
- 结构门禁负责可确定检查：Schema、段落顺序、起始画面静置 1 秒、声明前置知识、术语/公式/视觉密度、解释段术语的 claim 支持、迁移对象与难度；
- 学科人工复核仍须判断旁白是否真正完整、事实引用是否语义支持、渐进顺序是否有效、迁移是否只换皮；确定性字段不能替代这一 oracle；
- 视觉产物必须在 TS-04C 继续通过 TS-04A 安全边界和 TS-04B 教学/布局门禁。

## 固定夹具

`fixtures/plans.json` 包含 4 个标记为 `gold_fixture` 的合成冻结正向计划：

1. 小学四年级声音：同一琴弦的力度、振幅、响度与音调；
2. 初中八年级数学：靠墙围栏、完全平方和最大面积；
3. 小学声音配对：橡皮筋的可观察比较；
4. 初中声音配对：示波器上的振幅与频率比较。

小学/初中配对使用同一 `core_relation`，但前置知识、术语、公式密度、视觉密度、观察方式和迁移难度必须分别声明。它们不能只是替换年级标签。

`fixtures/cases.json` 共 24 例：4 个 `gold_fixture` 正向计划和 20 个 `adversarial_fixture` 负向变体。负向类别覆盖关键顺序、1 秒起始静置、未声明前置知识、越级术语、模型自行放宽学段规则、公式/视觉超密、缺少静态降级、无来源 fact、解释段术语缺少 claim 支持、迁移换皮、迁移预曝光、未批准对象/题目、迁移 claim 支持不足、差异维度不足、失败后未换对象、迁移难度错误和仅替换学段标签。旧的预测答案泄露夹具已随产品流程取消，不再属于当前正确性门禁。这些夹具只验证门禁，不进入候选模型正式评测分母；API 返回的 4 份计划才标记为 `candidate_output`。

所有内容均为合成夹具，不含真实儿童身份、语音、图片、对话、生产日志或受控教材正文。

## 运行

确定性合同门禁：

```bash
python3 spikes/ts-02-knowledge-validation/run.py
python3 spikes/ts-03-progressive-lesson-plan/sync_knowledge.py
python3 -m unittest discover -s spikes/shared/tests -v
python3 -m unittest discover -s spikes/ts-03-progressive-lesson-plan/tests -v
python3 spikes/ts-03-progressive-lesson-plan/run_validation.py
```

顺序不可交换：先由 TS-02 重新生成密封包，再同步 TS-03，最后验证共享来源门禁和讲解合同。直接编辑 `fixtures/plans.json` 中的 `knowledge` 会被调用前门禁拒绝。

结果写入：

- `results/audit.json`：逐例违规码与双学段配对审计；
- `results/timing.json`：符合共享 `stage-timing/1.0` 的局部 span；
- `results/summary.json`：指标、门槛、环境和当前决策。

真实模型仅在本地 `.env.local` 配置后运行：

```bash
python3 spikes/ts-03-progressive-lesson-plan/run_model.py
python3 spikes/ts-03-progressive-lesson-plan/run_streaming_first_segment.py
```

运行器固定为 4 次、零自动重试，只发送仓库内合成 `StageProfile`、学段规则、claims 和问题，不发送受控教材正文或儿童数据。原始响应写入 Git 忽略的 `results/raw/`；每轮汇总写入 `results/model-<model>-<run-label>.json`。非流式接口只能在整份响应返回时同时看到首段与完整计划，因此不能据此证明首段早于完整计划可用。

## 指标与候选门槛

| 指标 | 当前合同结果 | TS-03 门槛 |
|---|---:|---:|
| 正向计划 Schema 合法 | 4/4 | >=99% |
| 关键顺序通过 | 4/4 | >=90% |
| 学段上下文完整 | 4/4 | 100% |
| 仅替换学段标签被接纳 | 0/1 | 0 |
| 换皮迁移被接纳 | 0/2 | 0 |
| 缺少静态降级被接纳 | 0/1 | 0 |
| 无来源关键 fact 被接纳 | 0/1 | 0 |
| 全部正负夹具符合预期 | 24/24 | 24/24 |

当前数字只证明确定性门禁能区分这些已知夹具。真实模型必须在同一冻结配置下生成 4 份计划，通过机器门禁后，再由独立学科/产品人员按完整旁白和迁移 rubric 复核；否则本切片保持待完成。

## 当前结果

产品于 2026-07-30 取消讲解前预测。当前合同已升级到 `lesson-plan/1.3`：全部段落为 `explanation`，首段可直接呈现有来源支持的结论；4 个预测泄露负向夹具和对应指标退出当前门禁。确定性合同门禁 `24/24` 符合预期，双学段配对审计通过，共享 StageTiming Schema 合法。它只证明测试框架覆盖当前已知失败模式，不是候选模型能力证据。

2026-07-30 经用户明确确认 4 次付费请求后，使用新版 `lesson-plan/1.3` 合同执行 DeepSeek 官方 API `official-full-round-5`。固定使用 `deepseek-v4-pro`、`thinking.type=disabled`、`temperature=0`、JSON object 输出、单例 60 秒超时和零自动重试：

| 指标 | 正式结果 | 门槛 / 判断 |
|---|---:|---:|
| 请求完成 | 4/4 | 完成 |
| Schema 合法 | 4/4 | >=99%，通过 |
| 合同门禁通过 | 原始 3/4；规则修正后 4/4 | 通过 |
| 双学段配对 | pass | 通过 |
| 人工学科与产品审核 | 4/4 | 通过 |
| 完整计划延迟 P80 | 21,132ms | 非流式 C 端等待明显超预算 |
| 已记录 Token | 21,206 | 4 例合计 |
| 自动重试 | 0 | 符合固定配置 |

4 例均返回且 Schema 合法。原门禁把 `primary_sound` 第 1 段的基础术语“振动”判为缺少 claim 支持；复核确认该术语已由本段声明的 `science.sound.vibration.basic` 前置知识授权。门禁现通过受控 `prerequisite_term_support` 映射放行基础术语，同时继续要求影响答案的事实判断引用 claim。未修改任何 round 5 候选输出，也没有新增模型请求；冻结响应按修正规则免费复判为合同 4/4，双学段配对通过。2026-07-30，`jun` 同时以学科与产品角色审核 4 例，记录为 4/4 通过、允许 TS-03 通过且无需新模型轮次；同一人承担两个角色，不等同于双人交叉复核。原始结果见 `results/model-deepseek-v4-pro-official-full-round-5.json`，复判见 `results/model-deepseek-v4-pro-official-full-round-5-gate-recheck.json`，结构化人工结论见 `results/model-deepseek-v4-pro-official-full-round-5-human-review.json`。

供人工审核使用的统一中文整理稿见 `results/official-full-round-5-human-review-zh.md`。该文档按问题、知识依据、分段旁白、画面、静态降级和迁移题组织，并保留原始响应哈希与审核填写区；它不替代冻结原始响应。

人工审核同时指出：生成内容可能过于简单、简洁，三个声音案例尤其偏向“结论 + 对比”，机制解释深度弱于数学案例。该观察不推翻本轮 4/4 人工通过结论，但 TS-03 没有证明真实儿童认为讲解充分或能够理解。后续应检查“结论、原因/机制、可观察证据、条件边界、迁移”是否形成完整推理链，并在家庭测试中验证理解；不得用最低字数或机械增加段落代替教学质量判断。

旧 `lesson-plan/1.2` 合同下的 `official-full-round-4` 只保留为历史证据，不再代表当前合同结果。

历史 PackyAPI `round-3` 仅完成 1/4，另外 3 例约 60 秒超时；更早两轮分别因入口 403 和运行器未捕获超时而无效。它们保留为供应商入口对照，不代表当前官方候选结果。

正式轮失败后又执行了一个不覆盖原结论的 `first-segment-round-1` 诊断：每次只要求生成一个可立即播放的首段，最大输出从完整计划的 8,000 Token 降到 3,000 Token，单例观察上限为 30 秒。4/4 请求均在 30 秒内没有返回可校验 JSON，首段门禁通过 `0/4`，`first_meaningful_ready` P80 无法形成，远未达到 8 秒目标。这说明仅把完整计划拆成较小的非流式首段请求仍不足以改善 C 端等待；结果见 `results/model-deepseek-v4-pro-first-segment-round-1.json`。

随后使用相同首段合同执行 `stream-first-segment-round-1`。4/4 请求均在 1.4–1.7 秒收到响应头和首个 SSE 事件，首个推理增量 P80 为 1,761ms；但每例在 30 秒内只产生约 1,500–1,865 个推理事件和 6,400–6,700 个推理字符，正文字符均为 0，首段可用仍为 `0/4`。因此 PackyAPI 连接和首包不是主要瓶颈；当前 `deepseek-v4-pro` 配置没有在 C 端预算内从推理阶段进入可展示正文。结果见 `results/model-deepseek-v4-pro-stream-first-segment-round-1.json`。

2026-07-30 按官方文档切换到 `https://api.deepseek.com`，并显式设置 `thinking={"type":"disabled"}` 后执行 `official-stream-first-segment-round-1`。4/4 在 30 秒内完成并通过首段 Schema 与合同门禁；首个 SSE 事件 P80 为 392ms，首个正文 P80 为 2,094ms，完整可用首段 P80 为 6,806ms，达到 `<8,000ms` 门槛。响应模型均标识为 `deepseek-v4-pro`，且没有推理增量，说明官方关闭思考参数生效。结果见 `results/model-deepseek-v4-pro-official-stream-first-segment-round-1.json`。这证明“官方 API + 关闭思考 + 流式首段”在本次固定 4 例中可达到首段体验门槛，但该诊断本身不替代完整 2–4 段计划与人工教学复核。

随后以同一官方配置执行完整计划 `official-full-round-1`：4/4 请求完成，Schema `4/4`、合同门禁 `4/4`、双学段配对门禁通过；完整计划延迟 P50/P80/P95 分别为 14,583/17,561/20,744ms，共使用 15,278 Token。机器阶段达到 `candidate_run_complete`。但逐份 AI 辅助语义预审发现 3/4 有阻断问题，包括首段用同义改写泄露答案、静态降级提前标出频率不变、靠墙围栏到靠墙花圃的换皮迁移，以及迁移题在讲解中已展示完整答案。候选输出集预审结论为 `fail`；该预审不能冒充独立真人学科/产品复核，因此 round 1 当时不能让 TS-03 通过，并继续阻断 TS-04C。机器结果见 `results/model-deepseek-v4-pro-official-full-round-1.json`，预审见 `results/model-deepseek-v4-pro-official-full-round-1-review.json`。

修正首段 phase、全可见文本禁答断言、受控迁移策略和差异维度后执行 `official-full-round-2`。4/4 均在 60 秒内返回，但 4 例都遗漏首段静态降级的 claim 引用，Schema 与合同门禁均为 `0/4`；完整计划延迟 P80 为 23,308ms，共使用 18,274 Token。语义预审仍发现小学与初中声音配对的首段画面泄露答案、claim 外推，以及数学 retry 擅自加入未提供的物理公式。round 2 结论为 `fail`，不进入独立人工复核。结果见 `results/model-deepseek-v4-pro-official-full-round-2.json` 和 `results/model-deepseek-v4-pro-official-full-round-2-review.json`。

round 3 后，旧合同门禁曾新增“大幅振动”类首段视觉泄露断言与解释段术语 claim 支持检查；`middle_sound_pair` 的听感映射 claim 和两道迁移题引用也已补齐。当时本地门禁为 `28/28`，但这些修正没有通过新的模型轮验证。产品取消讲解前预测后，4 个预测泄露夹具退出当前合同，当前新合同门禁为 `24/24`。

随后复核发现，上述听感映射曾错误引用两份只讨论声音传播介质的合成材料。该修改已废弃：TS-02 新增明确标记为 synthetic 的初中声音波形来源和逐条证据，发布为 `source_scope=synthetic_fixture` 密封包；TS-03 从 `lesson-plan/1.2` 起只消费该导出，当前讲解合同为 `lesson-plan/1.3`。共享门禁会拦截手改 claim、错包、过期来源哈希、缺失页码和找不到的证据摘录。当前结果仍只证明合成测试链路，不证明真实教材或生产知识有效。

完整影响、限制与下一步见 `decisions.md`。
