# TS-04C 真实生成视觉表现与讲解一致性

> 状态：`fail`（唯一受控修复后 1/10 浏览器门禁通过，低于 90% 门槛）；正式轮未开始
> 对应验证文档：`docs/technical/2026-07-28-primary-visual-tutor-technical-validation-v3.md`

## 唯一验证问题

冻结版本的候选生成模型能否把 TS-03 的完整讲解计划转换为可运行、可理解、与旁白和知识结论一致，并同时通过 TS-04A 沙箱与 TS-04B 教学/布局门禁的视觉场景？

## 被测对象与授权

- 当前完整题校准候选：DeepSeek 官方 `deepseek-v4-flash`；
- 调用方式：官方兼容 Chat Completions API，本地配置文件提供地址与密钥；
- 固定参数：temperature 0、thinking disabled、JSON object、最多 5,000 输出 Token、60 秒超时、零自动重试、零修复；
- 本轮预算：1 请求、25,000 总 Token 上限；实际 1 请求、4,709 Token；
- 数据边界：仅发送一道 synthetic unverified 问题及三条合成 claim，不发送教材正文、儿童数据或生产日志；
- 用户确认记录：2026-07-31，用户要求先测试一道完整题目讲解；沿用此前确认的 DeepSeek 官方 Flash 配置；
- 当前状态：`candidate_run_complete`；合同通过，但本地教学语义门禁失败，人工评审未完成。

允许的状态为 `not_started | harness_ready | candidate_run_complete | human_review_complete | conditional_pass | pass | fail`。被测对象未确认时可以搭建测试框架，但不得将门禁自测表述为候选对象已经验证或通过。

## 不验证什么

- 不验证生产扩展性；
- 不验证完整 UI；
- 不验证真实配音、字幕、动画同步（TS-07）；
- 不验证儿童理解、学习效果或全年级泛化；
- 不验证生产扩展性、稳定性或成本可接受性。

## 假设

如果生成场景携带完整讲解上下文并接受一次受控修复，那么机器门禁应阻断越界、隐藏裁切和事实/旁白不一致，人工审核可独立判断展示资格。

## 输入与输出契约

- 输入：TS-03 `lesson-plan/1.3` 计划、TS-02 密封知识包、TS-04B `visual-scene/1.0` 场景声明；调用前必须校验来源与内容包哈希。
- 输出：真实沙箱场景代码、`visual-scene/1.0` 声明、静态降级、机器门禁结果和 `StageTiming` 局部 trace。
- 复用：`../ts-04b-visual-scene-gate/schemas/visual-scene.schema.json`，不得另建较弱的布局规则。

## 固定夹具

- 校准轮：小学声音、初中数学各 5 个合成 `gold_fixture` 计划；不计入正式分母。
- 正式轮：两学段各 20 个冻结输入，候选输出才可标记 `candidate_output`；失败样本保留在隔离评审区。
- 对抗样例：复用 TS-04B 的事实相反、越界、运动包络、隐藏裁切和超时案例，标记 `adversarial_fixture`。
- 不含真实儿童数据；真实来源只能通过 TS-02 密封包传入。

每个夹具必须标记来源类型：

- `gold_fixture`：人工、Codex 或其他非被测对象编写的正向基准；
- `adversarial_fixture`：故意构造的负向或攻击样例；
- `candidate_output`：通过已确认调用方式获得的候选对象真实输出。

`gold_fixture` 和 `adversarial_fixture` 只用于验证测试框架，不得计入候选对象的正式评测分母。

## 证据来源

凡输入、oracle 或输出包含已核验/可发布事实，必须记录并机器校验：上游产物版本、来源标识、稳定定位或页码、证据摘录、来源文件哈希、审核方法和内容包哈希。下游切片不得手工拼装或升级知识状态，必须消费上游导出的密封包，并在任何外部调用前重新验证内容与来源。

合成夹具必须明确标记为 synthetic，只能证明管线或门禁行为。没有真实来源和规定人工审核时，不得把合成夹具结论写成真实教材、权威资料或生产知识已验证。

哈希、页码和摘录存在性只验证可追溯与防篡改。非 synthetic 的已核验/可发布事实还必须提供独立语义审核通过产物，不能由夹具作者自审或用字符串命中代替。

## 运行环境

待候选对象确认后记录设备、浏览器、运行时、模型/服务版本、固定参数和依赖。当前仅搭建本地门禁 harness。

## 运行方式

```bash
# 候选对象确认后补充生成入口；当前仅运行合同与门禁 harness
python3 -m unittest discover -s tests -v
```

## 指标

| 指标 | 定义 | 门槛 |
|---|---|---|
| 机器门禁预期符合率 | 固定正负夹具中按预期通过/阻断的比例 | 100% |
| 首次生成通过率 | 正式轮首次生成同时通过 TS-04A/04B 的样本数 / 40 | >=70% |
| 修复后通过率 | 一次受控修复后通过样本数 / 失败样本 | >=90% |
| 静态降级覆盖率 | 未通过样本拥有合规降级 / 未通过样本 | 100% |
| 全新生成 + 检查 P80 | 正式轮完整墙钟时间 P80 | <=30s |

## 结果

结果写入 `results/summary.json`、模型汇总和浏览器汇总。唯一受控修复轮 10/10 收到响应并通过紧凑契约；10 个候选共运行 160 个手机/平板状态，最终仅 1/10 通过完整门禁。不能把该结果外推为全年级模型能力；正式轮未开始。

### 单道完整陌生题校准（2026-07-31）

- 题目：`往水里加盐，鸡蛋为什么会慢慢浮起来？`，标记为 synthetic unverified；
- 模型一次请求生成 4 个连续片段，总讲解时长 32 秒；模型合同通过，耗时 11,587ms，总 Token 4,709；
- 本地编译与画布回归通过：手机和平板共 56/56 个关键状态通过，无空白场景、画布越界或页面溢出；暂停位置保持在 367ms，恢复后继续到 733ms；
- 教学语义门禁失败：第三段声明“浮力 > 重力”，却生成等长的浮力与重力箭头；第四段旁白说明最终平衡，却没有生成等长的平衡受力箭头；
- 本轮没有受控修复或第二次模型调用。完整题候选不可展示或缓存，TS-04C 状态不推进到 `human_review_complete`。

随后将这两个失败转为通用关系门禁回归。上游 synthetic `gold_fixture` 独立声明段序、对象语义、度量与 `gt | eq | lt` 关系，本地门禁不再扫描旁白或图形标签。旧候选重放仍稳定产生两个机器可定位违规：第三段为 `visual.required_relation_mismatch`，第四段为 `visual.required_relation_operand_missing`。关系包保存独立 SHA-256，原候选输入及其哈希未修改；本次没有外部请求或模型修复，因此只证明错误画面可以在展示和缓存前被阻断，不改变 TS-04C 的 `fail` 结论。

本地评审隔离入口为 `full-question-review.html`；该页面用于查看失败候选，不是 C 端产品页。机器结果见 `results/full-question-local-gate-egg-saltwater-v01.json` 与 `results/full-question-browser-gate-egg-saltwater-v01.json`。

门禁自测、候选对象运行和人工评审必须分别记录。候选输出至少保存供应商、固定版本、参数、运行时间、响应哈希、Token 或等价用量、成本和失败；无法取得的字段明确标记为未验证。

## 决策

在 `decisions.md` 记录状态推进、失败样例、PRD/高保真/架构/数据隐私影响。候选调用前必须补齐供应商、版本、参数、预算和用户确认记录。

## 已知限制

列出样本、设备、知识范围和供应方限制。
# TS-04C 混合 DSL / Motion Canvas 方案实验

> 状态：`conditional_pass`（仅限 Motion Canvas 3.17.2 本地运行时链路）；未调用模型

## 实验目标

验证模型继续输出受限 DSL，由本地可信编译器把 DSL 转成可审计的 Motion Canvas adapter 计划，能否解决 v0.4 暴露的两个通用表达问题：对象移动时关系线自动跟随，以及数学函数线由公式和定义域确定，而不是由模型直接猜像素端点。

## 安全边界

- 模型输出仍然是声明式 JSON；本实验不接收 JavaScript、HTML、CSS 或任意表达式；
- 编译器只允许 `point`、`box`、`anchor` 三种节点、五种固定锚点、动态 connector 和数值 function line；
- 生成的 Motion Canvas adapter source 仅作为审计产物，代码从不 `eval`；
- Motion Canvas 依赖已固定并安装在 `motion-canvas-runtime/`；未调用外部模型或媒体服务；
- 这是技术可行性 harness，不代表 Motion Canvas 集成、动画质量或产品可用性已经验证。

## 运行

```bash
node tests/hybrid-scene-compiler.test.js
python3 -m json.tool fixtures/hybrid-scene-v01.json >/dev/null
python3 -m http.server 4188
```

打开 <http://127.0.0.1:4188/hybrid-harness.html>，拖动进度条观察连接线起点是否随手电筒移动。右侧显示受控 adapter 文本，便于审计其没有任意执行入口。

用户可见预览入口：<http://127.0.0.1:4188/hybrid-preview.html>。该页面隐藏 adapter 代码，只显示讲解画布、中文标签、片段切换、旁白文案和播放进度；它仍是预览 harness，不是完整产品页。

## 当前结果

- 离线编译测试通过：动态 connector 端点跟随、函数线数值计算、未知节点拒绝和非法节点类型拒绝；
- Chromium 演示通过：50% 进度时连接线跟随移动对象，两条函数线按固定斜率/截距/定义域绘制；
- 用户预览页通过：影子片段展示动态边界光线；直线片段去掉坐标系外框，标注 x/y 轴，由两条公式自动求出交点并显示标签；页面不展示调试代码；
- Motion Canvas 3.17.2 真实播放器通过：两个场景成功加载并播放，影子关系线随节点移动，直线场景显示公式线和交点 `(2,5)`；
- 已导出两个场景共 158 张 PNG，并检查 390×844 手机和 768×1024 平板预览无横向溢出；
- 仍未验证：视频导出、帧率稳定性、真实 TTS、模型输出和完整教学质量。

真实运行时实验记录见 `motion-canvas-experiment-decision.md`，项目入口位于 `motion-canvas-runtime/`。

混合 DSL 陌生问题校准结果见 `results/model-deepseek-v4-flash-official-hybrid-dsl-v01-flash-calibration-round-1.json` 和 `results/hybrid-dsl-local-gate-v01-flash-calibration-round-1.json`。7/10 通过模型合同，7/7 合同通过样本通过本地编译；人工评审尚未开始。打开 `hybrid-candidate-review.html` 查看候选动画。
