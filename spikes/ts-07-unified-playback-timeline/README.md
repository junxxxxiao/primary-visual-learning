# TS-07 统一播放时间轴最小成本审计

> 状态：`conditional_pass`；候选门槛通过且已完成人工评审，真机及非 Chrome 环境留待后续验证
>
> 性质：直接审计现有高保真 Demo 的抛弃式技术切片，不是生产运行时
>
> 实现基线：`origin/main` at `4b91022b7ca933340477d3b55eba5f863593deaa`

## 唯一验证问题

现有数学与声音高保真 Demo 已证明固定讲解体验可以工作。本切片只回答剩余差量问题：现有 Chrome Demo 的真实音频时间轴及其视觉降级，能否在最小压力操作下达到 `<250ms` 的同步与位置连续性门槛？

## 被测对象与授权

- 被测对象：`prototype/sound-demo.html` 现有共享播放器；
- 浏览器：Google Chrome `150.0.7871.188`，候选结果同时保存实际 User-Agent；
- 音频：仓库现有 `prototype/assets/audio/narration-math-1.wav`，约 20.16 秒；
- 调用方式：本地 HTTP、同源黑盒审计、Playwright CLI 驱动可见控件；
- 固定参数：播放速率 1.0，5 次真实音频运行、5 次故障降级运行、每次 10 次定位；
- 调用预算：0 次外部请求、0 Token、0 元；
- 数据边界：仓库固定音频和 synthetic 审计指令，不含儿童数据、教材文件、凭据或生产日志；
- 用户确认记录：2026-08-04，用户确认候选配置，并要求用最小成本只测试现有 Demo 尚未证明的问题。

## 不重复验证

不重复数学/声音完整流程、手机/平板布局、触控尺寸、滚动、减少动态效果和 UI 截图验收。既有 Demo 证据只说明固定体验可行，不进入本轮量化分母。

## 测量

- 真实音频：25 个字幕 cue、10 个视觉 cue、5 次暂停恢复、50 次定位；
- 降级路径：播放约 10 秒后让同一音频元素请求不存在的本地文件，触发现有公开 `error` 处理，共 5 次；
- 门槛：正常 cue、暂停恢复、定位和降级交接均 `<250ms`，定位现场一致，降级必须单调继续且不回滚字幕/画面；
- 自测：迟到 cue、错误暂停、错误定位、现场不一致、降级跳回、非单调和现场回滚均必须被门禁拒绝。

## 运行

先启动只监听本机的审计服务器：

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

## 结果

- 字幕 cue P95：约 `36.2ms`，通过；
- 视觉 cue P95：约 `37.0ms`，通过；
- 暂停恢复 P95：约 `62.1ms`，通过；
- 50 次定位 P95：约 `107.2ms`，最大约 `108.2ms`，完整现场一致，通过；
- 首轮降级交接 P95：约 `9965.3ms`，5/5 非单调且字幕/画面回滚，用作修复前红态；
- 共享播放器改为让视觉降级继承最后有效音频进度和已解码时长，未重新生成语音或动画；
- 修复后只复测 5 次降级：交接 P95 约 `38.7ms`，最大约 `40.8ms`，5/5 单调继续、无字幕/画面回滚、每次仅一个错误事件；
- 声音主讲解和真空主题各 1 次非正式分母冒烟检查通过，并确认降级暂停能保持、恢复后继续前进。

修复前原始证据见 `results/browser-candidate.json`，修复后降级证据见 `results/browser-fallback-retest.json`，共享冒烟见 `results/browser-shared-smoke.json`，独立复算见 `results/summary.json`，共享计时记录见 `results/timing.json`。

人工评审人 `junxxxxiao` 于 2026-08-04 独立运行复算脚本，确认输出符合预期，并接受 Safari、微信 WebView、真机等未验证边界。评审证据见 [PR #5 评论](https://github.com/junxxxxiao/primary-visual-learning/pull/5#issuecomment-5177367523)。证据状态为 `human_review_complete`，切片结论为 `conditional_pass`；本结论不将 Demo 提升为生产架构。

## 边界

- 只修改现有 Demo 共享播放器的降级交接，并同步 PRD、原型说明和高保真规范；
- 没有生成语音、动画或候选内容；
- 没有验证 Safari、微信 WebView、真机、后台限流、网络缓冲、长讲解或生产会话隔离；
- synthetic visual cue 只验证现有固定场景的时间投影，不是 TS-04C 证据；
- TS-04C 尚未合入当前基线且当前结论为 `fail`，本切片不证明完整 P0 链路。
