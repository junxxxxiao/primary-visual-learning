# TS-07 统一播放时间轴最小成本审计

> 状态：`harness_ready`；高频连续切段复测超时，未产生新的候选运行与人工结论
>
> 性质：直接审计现有高保真 Demo 的抛弃式技术切片，不是生产运行时
>
> 实现基线：`origin/main` at `4b91022b7ca933340477d3b55eba5f863593deaa`

## 唯一验证问题

现有数学与声音高保真 Demo 已证明固定讲解体验可以工作。本切片只回答剩余差量问题：现有 Chrome Demo 的真实音频时间轴及其视觉降级，能否在最小压力操作下达到 `<250ms` 的同步与位置连续性门槛？

## 被测对象与授权

- 被测对象：`prototype/sound-demo.html` 现有共享播放器；
- 浏览器：Google Chrome `150.0.7871.188`，候选结果同时保存实际 User-Agent；
- 音频：复测时已授权 `prototype/assets/audio/narration-math-1.wav`（约 20.16 秒）和 `prototype/assets/audio/narration-math-2.wav`（约 23.76 秒）；
- 调用方式：本地 HTTP、同源黑盒审计、Playwright CLI 驱动可见控件；
- 固定参数：播放速率 1.0，5 次真实音频运行、50 次段内定位、1 轮在数学第 1/2 段间交替的 10 次切段定位、5 次故障降级运行；
- 调用预算：0 次外部请求、0 Token、0 元；
- 数据边界：仓库固定音频和 synthetic 审计指令，不含儿童数据、教材文件、凭据或生产日志；
- 用户确认记录：2026-08-04，用户确认候选配置，并要求用最小成本只测试现有 Demo 尚未证明的问题。

## 不重复验证

不重复数学/声音完整流程、手机/平板布局、触控尺寸、滚动、减少动态效果和 UI 截图验收。既有 Demo 证据只说明固定体验可行，不进入本轮量化分母。

## 测量

- 真实音频：25 个字幕 cue、10 个视觉 cue、5 次暂停恢复、50 次定位；
- 切段路径：通过可见播放器控件在数学第 1/2 段间交替 10 次，并在每次切段时定位到 5、10 或 15 秒；
- 降级路径：播放约 10 秒后让同一音频元素请求不存在的本地文件，触发现有公开 `error` 处理，共 5 次；
- 门槛：正常 cue、暂停恢复、段内定位、切段定位和降级交接均 `<250ms`；切段绝对误差趋势斜率不得大于 `0ms/次`；现场与当前段一致；每次降级必须恰好发生一次真实音频到视觉时钟的状态转换，单调继续且不回滚字幕/画面；
- 自测：迟到 cue、错误暂停、错误定位、现场不一致、切段累计漂移、切段超限、重复降级转换、降级跳回、非单调和现场回滚均必须被门禁拒绝。

## 运行

先执行候选授权与输入哈希预检。授权为 `pending`、manifest 或任一输入变化时必须失败：

```bash
python3 spikes/shared/candidate_evidence_gate.py validate \
  --repo-root . \
  --manifest spikes/ts-07-unified-playback-timeline/candidate-manifest.json \
  --stage preflight
```

预检通过后启动只监听本机的审计服务器。服务器会再次执行同一门禁，并在保存正式复测结果时自动生成 `candidate-run.json`：

```bash
python3 spikes/ts-07-unified-playback-timeline/run_audit_server.py --port 4197
```

打开以下地址，通过 `Run candidate audit` 按钮运行正式轮：

```text
http://127.0.0.1:4197/spikes/ts-07-unified-playback-timeline/audit-harness.html
```

结果保存后独立复算指标、哈希和结构门禁：

```bash
python3 spikes/ts-07-unified-playback-timeline/run_validation.py
```

此时没有当前 `candidate-human-review.json` 时，状态最多为 `candidate_run_complete`。人工评审文件必须晚于候选完成并绑定当前 manifest 与结果哈希，之后才能进入最终决定。

## 结果

- 字幕 cue P95：约 `36.2ms`，通过；
- 视觉 cue P95：约 `37.0ms`，通过；
- 暂停恢复 P95：约 `62.1ms`，通过；
- 50 次定位 P95：约 `107.2ms`，最大约 `108.2ms`，完整现场一致，通过；
- 首轮降级交接 P95：约 `9965.3ms`，5/5 非单调且字幕/画面回滚，用作修复前红态；
- 共享播放器改为让视觉降级继承最后有效音频进度和已解码时长，未重新生成语音或动画；
- 修复后差量复测包含 10 次第 1/2 段交替定位：P95 约 `123.7ms`、最大约 `132.9ms`、漂移斜率约 `2.20ms/次`，10/10 当前段与字幕/画面/进度一致；
- 修复后 5 次降级交接 P95 约 `25.1ms`，最大约 `25.7ms`，5/5 单调继续、无字幕/画面回滚，每次恰好一次真实音频到视觉时钟的状态转换；
- 声音主讲解和真空主题各 1 次非正式分母冒烟检查通过，并确认降级暂停能保持、恢复后继续前进。
- 上述切段与降级数据属于二次门禁收紧前的历史诊断证据；授权后的正式复测在快速切换到数学第 2 段并定位 10 秒时超时，未保存结果，也未生成 `candidate-run.json`。

修复前原始证据见 `results/browser-candidate.json`，修复后降级证据见 `results/browser-fallback-retest.json`，共享冒烟见 `results/browser-shared-smoke.json`，独立复算见 `results/summary.json`，共享计时记录见 `results/timing.json`。

人工评审人 `junxxxxiao` 于 2026-08-04 对首轮修复证据接受过 `conditional_pass`，证据见 [PR #5 评论](https://github.com/junxxxxiao/primary-visual-learning/pull/5#issuecomment-5177367523)。二次审查新增了跨段音频哈希、真实时钟转换事件和更严格的非递增漂移门禁；旧人工评审早于这些新证据，不能沿用。用户决定暂缓高频连续切段压力场景并以 `harness_ready` 合并测试框架与失败记录。

## 边界

- 只修改现有 Demo 共享播放器的降级交接，并同步 PRD、原型说明和高保真规范；
- 没有生成语音、动画或候选内容；
- 没有验证 Safari、微信 WebView、真机、后台限流、网络缓冲、长讲解或生产会话隔离；
- 未覆盖 ADR-0005 的自动连播切段、主题切换及返回原主题、每段起始画面精确静置 1 秒、减少动态效果和前后台恢复；
- 未覆盖旧会话延迟事件、问题切换、受限命令和刷新后的兼容快照恢复；
- 高频连续切段定位仍未通过，不代表正常顺序播放存在已复现问题；
- synthetic visual cue 只验证现有固定场景的时间投影，不是 TS-04C 证据；
- TS-04C 尚未合入当前基线且当前结论为 `fail`，本切片不证明完整 P0 链路。
