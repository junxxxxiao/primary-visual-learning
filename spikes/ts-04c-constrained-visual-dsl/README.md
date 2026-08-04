# TS-04C-v2 受限视觉 DSL

> 状态：`fail`
>
> 性质：TS-04C 失败后的独立候选方案；候选与本地渲染证据已冻结，不代表产品可用性
>
> 基线：`origin/main` at `5e002d1d4e04ec70e71ecd6c3b3b8af299d1e34f`

## 唯一验证问题

受限 JSON 场景规格能否在不执行模型生成代码的前提下，由可信本地编译器生成同一份响应式场景，并通过手机/平板各 8 状态的 TS-04A 沙箱与 TS-04B 布局门禁？

## 被测对象与授权

- 当前被测对象：DeepSeek 官方 API `deepseek-v4-pro` 生成 `visual-dsl/0.1`，以及可信编译器和渲染器
- 固定参数：`thinking.type=disabled`、`temperature=0`、无自动重试、每例最多一次修复
- 调用预算：10 个初始请求，总上限 100,000 Token；本轮未触发修复
- 数据边界：TS-03 合成 `gold_fixture` 的标识与受控 claim ID；无教材正文或儿童数据
- 当前状态：`fail`；产品视觉审阅已触发停止条件

## 输入与输出

- 输入：`schemas/visual-dsl.schema.json`；只允许受限场景类型、标签、事实 ID、色彩 Token 和互动模式。
- 输出：可信编译器生成的沙箱代码，以及本地测量生成的 `visual-scene/1.0` 声明。
- 模型不能提供 JavaScript、HTML、CSS、任意表达式或布局边界。

## 运行

```bash
python3 prepare_fixtures.py
python3 -m unittest discover -s tests -v
python3 run_calibration.py
python3 run_browser_server.py 4185
```

打开：

```text
http://127.0.0.1:4185/spikes/ts-04c-constrained-visual-dsl/browser-harness.html
```

人工评审工作台：

```text
http://127.0.0.1:4185/spikes/ts-04c-constrained-visual-dsl/human-review.html
```

工作台同时显示真实可信渲染器生成的手机与平板画面。每位评审者需要使用非实名代号，逐场访问全部 8 状态并填写教学、视觉和状态完整性结论；严重事实错误会直接阻断该场景。草稿只保存在当前浏览器，提交后生成独立的 `results/human-review-*.json`，不会自动修改切片结论。

至少需要一份 `subject_matter` 和一份 `product_visual` 评审产物。两份结果必须一起复核；单份结果即使达到 9/10 且无严重错误，也不能单独把状态推进为 `human_review_complete`。

## 门槛

- 10/10 `gold_fixture` 符合 DSL 合同；
- 160/160 手机/平板状态完成沙箱执行、非空画布和布局测量；
- 10/10 通过 TS-04B 教学/布局门禁；
- 本地单状态检查 P80 <=250ms；
- 这些结果只证明 harness 能力，不计入候选模型正式分母。

## 本地门禁结果

2026-07-30 的 `gold_fixture` 浏览器轮次达到上述本地门槛：10/10 个场景、手机与平板共 160/160 个状态运行通过，单状态耗时 P80 为 33ms、最大 59ms。机器可读证据见 `results/browser-gold-harness-round-1.json`。

## 候选校准结果

DeepSeek 官方 `deepseek-v4-pro` 首轮 10/10 输出通过 DSL 合同，无需修复；模型耗时 P80 3,076ms，总用量 12,496 Token。加强内容完整性门禁后，候选手机/平板共 160/160 状态通过，内容缺失为 0，单状态耗时 P80 34ms。对应证据见 `results/model-deepseek-v4-pro-official-dsl-calibration-round-1.json` 和 `results/browser-official-dsl-calibration-round-1-browser-round-2.json`。

## 人工审阅与停止结论

2026-07-31，产品负责人逐个查看 10 个校准动画后判定 10/10 均不可展示，并指出每例旁白都只有一个短段落。机器门禁的 10/10 与 160/160 仍然有效，但只证明场景能够按合同绘制、没有被当前检查发现越界，不证明讲解质量。

根因是 `visual-dsl/0.1` 只提供 `comparison`、`sequence`、`area_model`、`wave` 四种浅模板。可信渲染器只能把标签放入矩形、流程块或波形，不能表达陌生问题所需的领域过程、公式变形、对象关系和多拍时间线。因此本候选结论为 `fail`，不再启动独立学科评审和正式 40 例。声音与数学 Demo 只保留为质量参照，不计入候选分母。
