# TS-04C 决策

- 日期：2026-07-30
- 结论：`fail`；DeepSeek 官方 `deepseek-v4-pro` 唯一受控修复轮 10/10 响应并通过紧凑契约，但修复后仅 1/10 通过完整浏览器门禁，远低于 90% 门槛。正式轮未开始。
- 基线：`origin/main` at `5e002d1d4e04ec70e71ecd6c3b3b8af299d1e34f`
- 负责人：Codex 技术切片执行

## 核心证据

紧凑轮改为模型只生成一份响应式代码和元数据，本地程序在手机/平板各 8 状态运行代码并生成 TS-04B 声明。唯一修复轮模型结果见 `results/model-deepseek-v4-pro-official-compact-repair-round-1.json`：10/10 响应且紧凑契约 10/10。最终浏览器结果见 `results/browser-official-compact-repair-round-1-browser-repair-round-2.json`：10 个候选、160 次状态运行、仅 1 个候选通过完整门禁。

## 未通过指标与失败样例

修复模型阶段：响应 `10/10`、紧凑契约 `10/10`、P80 `31,151ms`、总 Token `68,394`、成本未独立取得。最终浏览器阶段：候选 `10`、状态运行 `160`、单状态 P80 `35ms`；18 次仍为生成代码错误，另有字体/图形过小、事实/旁白不一致和声明结构异常，最终展示资格 `1/10`（10%，门槛 >=90%）。

## 影响

- 对 PRD：保持 TS-04C 的 40 例正式轮、两学段分别报告和硬降级门槛。
- 对高保真设计：要求手机 `390 × 844` 与平板分别审阅，失败场景不得展示或缓存。
- 对架构：确认 TS-03 计划、TS-04A 沙箱、TS-04B 布局门禁之间的输入契约边界。
- 对数据和隐私：仅允许 TS-02 密封知识包和合成/去标识化夹具；不保存真实儿童媒体。

## 下一步

本候选配置停止继续修复，不进入正式 40 例或人工展示审核。后续若继续 TS-04C，必须作为新的候选方案决策，例如更受限的声明式视觉 DSL/受信任绘图组件，或由用户重新确认其他模型/服务；不能把第二次修复混入本轮。
# 混合 DSL / Motion Canvas 方案实验

- 日期：2026-07-31
- 状态：`harness_ready`
- 结论：受限 DSL 可以在不执行模型 JavaScript 的情况下编译成可审计的 Motion Canvas adapter 计划；动态 connector 和公式 function line 的核心关系已在离线与浏览器演示中成立，但尚未验证真实 Motion Canvas 依赖。

## 已验证

- 手电筒移动到中点时，connector 起点由本地编译器重新解析并跟随节点；
- `y=2x+1` 与 `y=-x+7` 由 slope、intercept 和 domain 计算线段端点；
- 未知节点、非法节点类型和非法锚点在编译前拒绝；
- adapter source 明确标记为审计文本，未使用 `eval`；
- 浏览器唯一控制台错误为无关的 favicon 404。
- 新增用户可见预览页，隐藏 adapter 代码并展示影子、直线两个讲解片段；公式标签修复后不再出现 `undefined`，坐标系去掉外框并标注 x/y 轴，交点由两条公式自动求得。
- 在用户确认后固定并安装 Motion Canvas 3.17.2（FFmpeg 插件 1.1.0），建立 `motion-canvas-runtime/` 隔离项目；真实播放器成功加载并播放影子、直线两个 synthetic 场景。

## 未验证

- 真正 Motion Canvas 包的固定版本和运行兼容性；
- Motion Canvas 沙箱、AST/依赖边界、资源和帧率；
- 真实 DeepSeek 候选是否能稳定生成新混合接口；
- 手机/平板 8 状态、统一时间轴、TTS 和静态降级。
- 用户预览页的完整教学质量、响应式排版和人工评审。
- 正式 PNG/视频导出和传递依赖漏洞的处理。

## 混合 DSL 陌生问题校准（2026-07-31）

- 候选：DeepSeek 官方 `deepseek-v4-flash`；temperature 0；关闭 thinking；JSON object；每次最多 5,000 Token；60 秒；10 请求/100,000 Token；零重试、零修复。
- 数据边界：沿用 10 道 synthetic unverified 陌生问题，不发送教材正文、儿童数据或生产日志。
- 模型响应与 DSL 合同通过：7/10；失败 3 例，分别为节点尺寸超过上限 1 例、多个节点尺寸超过上限 1 例、函数线定义域/截距超过上限 1 例。
- 本地可信编译器通过：7/7 个合同通过候选均可编译；动态连接线、timeline 节点引用和函数线均通过编译门禁。
- 人工评审：尚未开始。评审入口为 `hybrid-candidate-review.html`。
- 当前状态：`candidate_run_complete`，不能表述为教学质量通过或 TS-04C 通过。

## 对架构的影响

- 保留模型到声明式 DSL 的安全 seam；
- 将动态关系重算放在本地 adapter，而不是让模型输出逐帧 JavaScript；
- 若要进入下一技术切片，应另立候选接口版本并先固定 Motion Canvas 依赖、沙箱方式、调用预算和数据边界。

## 单道完整陌生题校准（2026-07-31）

- 被测对象：DeepSeek 官方 `deepseek-v4-flash`；temperature 0；thinking disabled；JSON object；5,000 最大输出 Token；60 秒；1 请求/25,000 Token；零自动重试、零修复。
- 数据：一道 synthetic unverified 鸡蛋盐水题，只发送三条合成 claim；没有教材正文、儿童数据或生产日志。
- 候选结果：一次请求成功，响应模型 `deepseek-v4-flash`，11,587ms，prompt 2,764 Token、completion 1,945 Token、总计 4,709 Token；响应哈希 `sha256:35b944f7cc6f8253bd8569975ff84f33e37265c200daebfd625f20e887348a1d`；成本未由响应独立取得，标记为未验证。
- 合同结果：4 段完整讲解、32 秒、15 个对象、7 个动作，Schema、问题绑定、fact refs 与时间范围通过。
- 浏览器结果：手机和平板 56/56 个布局状态通过；无空白、无画布越界、无页面横向或纵向溢出；暂停冻结与原位恢复通过。唯一控制台错误是无关的 favicon 404。
- 语义结果：`fail`。第三段用等长箭头表达“浮力 > 重力”；第四段讲“浮力与重力平衡”但没有平衡箭头。失败候选仅保留在隔离评审页，不展示或缓存。
- 状态：保持 `candidate_run_complete`，不进入 `human_review_complete`，不将本地可信渲染器或合成材料计为陌生题泛化证据。

### 影响与未验证

- PRD：无需求变更；仍要求陌生题完整讲解与失败硬降级。
- 高保真设计：无产品页变更；评审 harness 仅验证片段串接和响应式布局。
- 架构：证明一次请求可在 11.6 秒内给出 4 段计划，但需要新增跨对象的教学语义门禁，不能只依赖 Schema 与边界检查。
- 数据和隐私：仅 synthetic unverified；无真实来源、教材或儿童数据。
- 未验证：真实教材证据、真实 TTS、音画同步、儿童理解、第二道题、跨学科泛化、成本和生产稳定性。

## 关系语义门禁补强（2026-07-31）

- 核心问题：候选输出可以同时满足 JSON 合同、布局边界和时间轴要求，却让图形数量关系与上游 claim/旁白矛盾；这属于教学语义错误，不是渲染失败。
- 修复边界：新增独立的 `visual-relation-requirements/0.1` synthetic `gold_fixture`，由上游计划声明段序、对象语义选择器、度量和 `gt | eq | lt`，本地 `validateRequiredVisualRelations` 在展示与缓存前检查。门禁不读取候选旁白或标签，模型不能通过措辞变化绕过。
- 回归结果：原候选第三段的 `120 > 120` 被标记为 `visual.required_relation_mismatch`；第四段缺少两根平衡箭头，被标记为 `visual.required_relation_operand_missing`。两条负向回归通过，原候选仍不可展示或缓存。
- 证据边界：原完整题输入、候选输出及已有哈希不变；新增关系包有独立哈希并标记 `synthetic_unverified`。未调用外部模型，没有新的 `candidate_output`，也没有生成质量提升证据。
- 影响：PRD、高保真、数据和隐私边界不变；架构上将跨对象数量关系加入可信本地门禁。TS-04C 保持 `fail`，陌生问题的生成质量仍需新的候选输出与人工评审才能验证。
