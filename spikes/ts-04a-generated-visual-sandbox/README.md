# TS-04A 生成视觉代码沙箱

> 状态：有条件通过（固定 Chromium 攻击矩阵通过）
>
> 性质：抛弃式技术可行性 spike，不是生产实现
>
> 对应验证文档：`docs/technical/2026-07-28-primary-visual-tutor-technical-validation-v3.md`
>
> 实现基线：`origin/main` at `27c80343836dcd88b10b8abd9ceacf57d1567a95`

## 唯一可证伪问题

在固定 Chromium 浏览器和规定攻击夹具中，Worker 兼容的生成视觉 JavaScript 能否只接收脱敏输入，在无主 DOM、网络、存储和设备权限的环境中运行；超时、事件洪泛、超大输出或崩溃时能否在预算内终止并完整销毁，同时保留主讲解模拟状态和代码哈希、策略版本？

任一禁止能力可成功访问、任一超限代码未终止、任一伪造消息进入主页面、任一崩溃修改主状态、任一执行后残留 iframe，或任一产物缺少代码哈希/策略版本，答案即为“否”。

## 不验证什么

- 不验证生成内容的教学正确性、视觉布局、动画轨迹或缓存；这些属于 TS-04B；
- 不验证生成模型、视觉质量、端到端延迟或 45 秒硬降级；
- 不验证生产级浏览器漏洞、跨浏览器一致性、操作系统进程级内存配额或专业渗透测试；
- 不支持生成代码直接操作 DOM；候选执行格式限定为 Worker + `OffscreenCanvas` API；
- 不初始化 `apps/` 或 `packages/`，不把本 spike 当作生产架构。

## 候选架构

1. 主页面校验 `visual-sandbox-input/1.0`，递归拒绝已知儿童身份、声音、照片、原话和历史字段。
2. 主页面创建不含 `allow-same-origin` 的 `sandbox="allow-scripts"` iframe，并用 Permissions Policy 禁止相机、麦克风、剪贴板和定位。
3. iframe 的 CSP 禁止网络、图片、媒体、子 frame、对象和表单；动态求值只在该不透明源 iframe 的 Worker 内用于装载生成代码。
4. 生成代码只在 Dedicated Worker 中运行，只有 `OffscreenCanvas` 和受限 `emit` API；网络、嵌套 Worker、存储及 RTC 入口被裁剪。
5. iframe 使用私有 `MessagePort`、不可见运行令牌、事件名白名单、32 个事件上限和 8KB payload 上限过滤输出。
6. 250ms 固定执行预算到期即终止 Worker；完成、失败或超限后关闭端口并移除 iframe。

这个方案收窄了“视觉代码”的格式：生成器必须输出 Worker 兼容的 Canvas 程序，而不是任意 DOM 页面。该约束换取主 DOM 隔离和可终止性，是否满足后续视觉表达范围仍需 TS-04B 验证。

## 固定夹具

`fixtures/attacks.json` 固定 11 个用例：

- 1 个良性 `OffscreenCanvas` 绘制；
- 网络/资源、存储/Cookie/主 DOM、相机/麦克风/剪贴板、Worker/iframe 逃逸；
- 原始 `postMessage` 伪造、白名单事件洪泛、超大输出；
- 无限循环、持续内存增长和主动崩溃。

浏览器运行器另执行 3 个非法输入和 20 次重复创建/销毁。全部数据均为合成数据，不含儿童数据、教材正文、密钥或外部服务调用。

## 输入与输出契约

- `schemas/sandbox-input.schema.json`：脱敏视觉参数 `visual-sandbox-input/1.0`；
- `schemas/sandbox-result.schema.json`：执行结果 `visual-sandbox-output/1.0`；
- `../shared/schemas/stage-timing.schema.json`：跨切片共用分段耗时事件 `stage-timing/1.0`；
- 每次结果包含 `code_hash`、`policy_version`、状态、机器可读原因、耗时和已接受事件；本切片另记录 `sandbox.create`、`sandbox.worker_boot`、`sandbox.execute`、`sandbox.terminate`、`sandbox.destroy`。

## 运行环境

- macOS；
- Headless Chrome `150.0.0.0`；
- Python 标准库本地静态服务器；
- Playwright CLI 浏览器会话；
- 不访问外网，不调用模型或第三方服务，运行成本为 0。

## 运行方式

启动本地验证页：

```bash
python3 spikes/ts-04a-generated-visual-sandbox/run_server.py --port 4174
```

打开 `http://127.0.0.1:4174/`。页面会自动执行完整矩阵，并在“机器可读结果”中输出 JSON。使用 Playwright CLI 复核：

```bash
/Users/jun/.codex/skills/playwright/scripts/playwright_cli.sh open http://127.0.0.1:4174/
/Users/jun/.codex/skills/playwright/scripts/playwright_cli.sh snapshot
```

## 指标与结果

| 指标 | 门槛 | 本轮 |
|---|---:|---:|
| 固定攻击夹具 | 11/11 | 11/11 |
| 禁止能力成功访问 | 0 | 0 |
| 超限/崩溃状态符合 oracle | 5/5 | 5/5 |
| 非法脱敏输入拒绝 | 3/3 | 3/3 |
| 重复创建/销毁 | 20/20 | 20/20 |
| 残留 iframe | 0 | 0 |
| 主讲解模拟状态保留 | 1/1 | 1/1 |
| 代码哈希与策略版本 | 11/11 | 11/11 |

原始安全运行中，无限循环和持续内存增长分别在 259ms、264ms 返回 `execution_budget`。后续计时补跑将 250ms 执行预算的起点明确为 `worker-ready`，把 iframe 创建和 Worker 启动单独计量，避免设备启动波动误触发执行超时。

计时补跑协议为 `ts04a-browser-protocol/1.1`，契约为 `stage-timing/1.0`。20 次生命周期样本的 P50/P80/P95/max 为 128/191/231/254ms；31 次 Worker 启动的 P50/P80/P95/max 为 41.2/51.7/88.6/200.9ms；两个超时用例的实际 `sandbox.execute.timeout` 为 251.5ms 和 252.4ms。详细安全结果见 `results/summary.json`，独立计时证据见 `results/timing-summary.json`。

本切片不使用平均值作门槛。分位数、最大值和失败率是主指标，平均值只能作为补充；并行阶段共用单调时钟，禁止相加。本轮样本仅用于定位沙箱局部耗时，不负责判断用户端总等待，TS-06 才负责从 `question_confirmed` 到首个有效内容、可交互及降级就绪的端到端判定。

## 决策

结论为**有条件通过**。固定 Chromium 夹具支持继续开展 TS-04B，但不得据此声称已达到生产安全。完整影响和限制见 `decisions.md`。

## 已验证与未验证

已验证：固定 Chromium 中的能力裁剪、消息鉴权、输入/输出边界、执行时间终止、崩溃隔离、重复销毁、可追溯字段，以及沙箱五个局部阶段可按共享契约记录。

未验证：Safari、iOS、Android、微信 WebView、跨源服务器响应头组合、浏览器零日与旁路、进程级 CPU/堆内存硬配额、超大 structured clone 前置成本、长期压力、辅助功能、视觉正确性、真实设备性能、并发负载、端到端用户等待和生产监控。
