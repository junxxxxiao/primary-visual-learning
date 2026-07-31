# Motion Canvas 真实运行时实验决策

状态：`conditional_pass`（仅限本地运行时链路）

## 目的

把当前已经通过离线编译和浏览器预览的受限 DSL，接入真实 Motion Canvas 运行时，验证“本地可信编译器 -> 场景代码 -> 渲染帧”的链路是否成立。

这一步只验证运行时接入，不重新评估 TS-04C 的模型质量，也不把预览 harness 当成产品动画。

## 待确认的被测对象

| 项目 | 当前值 |
|---|---|
| 供应商/项目 | Motion Canvas |
| 包 | `@motion-canvas/core`、`@motion-canvas/2d`、`@motion-canvas/vite-plugin`、`@motion-canvas/create` |
| 固定版本 | `3.17.2`；`@motion-canvas/ffmpeg@1.1.0` |
| 安装方式 | 本地 npm 安装，已获准联网下载依赖 |
| 运行方式 | 隔离实验目录，禁止执行模型生成 JavaScript |
| 实验预算 | 2 个 synthetic 场景，本地播放器检查；未进行模型调用 |
| 数据边界 | 仅使用现有 synthetic/gold fixtures，不上传真实儿童数据或 API 凭据 |

## 实验范围

1. 用现有 `fixtures/hybrid-preview-scenes.json` 编译两个场景：影子、两条直线。
2. 输出固定尺寸的少量 PNG 帧，检查动态 connector、公式线和交点是否与预览一致。
3. 记录包版本、Node 版本、渲染耗时、失败日志和输出哈希。
4. 不执行 `eval`，不接受模型 JavaScript，不接入真实 TTS，不进入正式候选评测。

## 通过条件

- 两个合成场景均能在固定版本下完成渲染；
- 渲染结果不越过画布边界，动态 connector 和公式线关系正确；
- 失败时保留可复现日志，不宣称 Motion Canvas 已适合生产。

## 进入实验前必须补齐

- ~~固定包版本和安装授权~~（已完成）；
- Node/npm 运行版本和正式帧导出预算仍待记录；
- ~~是否允许为该隔离实验联网安装依赖~~（已完成）；
- 输出帧数量和磁盘预算仍待记录。

## 本轮结果

- `npm run build` 通过，Vite 正常编译 1091 个模块；
- Motion Canvas 3.17.2 播放器成功加载 `shadow` 与 `lines` 两个场景；
- 影子场景播放中，关系线跟随手电筒位置变化；
- 直线场景显示 `y=2x+1`、`y=-x+7` 和编译器推导的交点 `(2,5)`；
- 已导出 158 张 PNG（两个场景各 79 张），代表帧哈希和机器结果见 `motion-canvas-runtime/results/runtime-v01.json`；
- 390×844 手机和 768×1024 平板预览均无横向溢出；
- 未验证视频导出、帧率稳定性、真实 TTS、真实模型输出和教学质量；
- npm audit 报告 3 个传递依赖漏洞（1 low、1 moderate、1 high），未执行 `audit fix --force`，避免改变实验版本。
