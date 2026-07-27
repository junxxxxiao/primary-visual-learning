# 小学互动视觉家教

面向小学 3–4 年级数学与科学的可打断互动视觉家教。孩子可以拍下不会的内容，或直接提出一个“为什么”；系统通过可操作的 PPT 式视觉讲解帮助孩子验证想法，并允许在当前场景中随时追问、改变条件、创建关联主题和返回原现场。

当前仓库处于“产品方案 v4 与固定声音价值 Demo 已完成，准备开展家庭体验验证和 P0 技术切片”的阶段。现有 Demo 使用固定教学夹具，不代表真实 OCR、儿童语音识别、AI 知识核验、动态视觉生成、视觉沙箱、场景恢复或端到端延迟已经实现。

## 当前状态

- 已完成：产品与竞品调研、完整中低保真可点击原型、PRD v4、固定声音高保真价值 Demo、声音价值 Demo 规范、技术验证 v2；
- 当前公开体验：[声音互动体验 Demo](https://junxxxxiao.github.io/primary-visual-learning/)；
- 下一阶段：家庭体验验证、社交媒体种子家庭招募、P0 技术切片；
- 尚未开始：生产技术栈初始化、真实模型与媒体服务接入、端到端 MVP 开发；
- 原型预设任务：声音问题 `更用力拨同一根弦，音调会更高吗？`，以及固定图片输入的完全平方公式数学真题；
- 关联追问：`如果没有空气呢？`；
- 迁移任务：同一音叉被更用力敲击时，音调是否改变。

## 事实源优先级

当文档或实现存在冲突时，按以下顺序处理：

1. [最新 PRD](docs/product/2026-07-22-primary-visual-tutor-prd-v4.md)；
2. [当前可点击原型](prototype/)；
3. [声音价值 Demo 规范](docs/design/2026-07-22-sound-value-demo-spec.md)与[中低保真原型规范](docs/design/2026-07-17-low-mid-fidelity-prototype-spec.md)；
4. 已完成技术切片的决策记录；
5. 早期产品、交互和竞品材料。

早期文档用于理解决策背景，不作为与新版 PRD 并列的需求源。

## 仓库结构

```text
.
├── README.md                      # 项目总览和工作入口
├── CONTRIBUTING.md                # Git、分支、提交和数据安全规范
├── apps/                          # 后续微信小程序、Web、API 等应用
├── packages/                      # 后续场景运行时、Schema、内容等共享包
├── prototype/                     # 当前声音 Demo 与历史研究原型
│   ├── index.html                 # GitHub Pages 默认入口
│   ├── sound-demo.html            # 当前高保真声音 Demo
│   ├── legacy.html                # 旧中低保真研究原型
│   └── assets/audio/              # 固定合成音效与旁白
├── docs/
│   ├── product/                   # 当前 PRD 与后续产品规格
│   ├── technical/                 # 技术验证与架构决策
│   ├── design/                    # 当前原型规范和设计约束
│   ├── research/                  # 竞品、用户与可用性研究
│   └── archive/                   # 已被新版规格取代的历史文档
├── design/
│   └── high-fidelity/             # 本地可运行高保真设计与交付清单
├── spikes/                        # 可独立运行的技术切片
│   ├── _template/                 # 新切片模板
│   └── shared/                    # 跨切片夹具和 Schema
└── tests/                         # 后续单元、集成、E2E 和评测说明
```

各目录的职责和进入条件见目录内 README。

## 体验 Demo

在线访问：<https://junxxxxiao.github.io/primary-visual-learning/>

旧中低保真研究原型仍可通过 <https://junxxxxiao.github.io/primary-visual-learning/legacy.html> 访问，仅用于历史和逻辑对照。

### 本地预览

原型不需要安装依赖或连接后端。

```bash
python3 -m http.server 4173 --directory prototype
```

打开 <http://127.0.0.1:4173/>。

如果已经从仓库根目录启动了静态服务，则打开 <http://127.0.0.1:4173/prototype/>。

常用直达参数：

- `?screen=entry`：公开入口；
- `?screen=lesson`：核心讲解；
- `?screen=experiment`：琴弦实验；
- `?screen=vacuum`：关联主题；
- `?screen=fork`：迁移验证；
- `?screen=result`：体验结果；
- `&viewport=phone`：固定 `390 × 844` 手机审阅画布；
- `&viewport=tablet`：固定平板审阅画布；
- `&preset=math`：切换到固定数学真题预设；
- 不传 `viewport`：按真实浏览器窗口自适应。

完整说明见 [prototype/README.md](prototype/README.md)。

## 核心文档

### 产品与设计

- [小学互动视觉家教 PRD v4.0](docs/product/2026-07-22-primary-visual-tutor-prd-v4.md)
- [声音高保真价值 Demo 规范](docs/design/2026-07-22-sound-value-demo-spec.md)
- [中低保真研究原型规范](docs/design/2026-07-17-low-mid-fidelity-prototype-spec.md)
- [高保真设计工作区](design/high-fidelity/README.md)

### 技术

- [技术验证 v2](docs/technical/2026-07-22-primary-visual-tutor-technical-validation-v2.md)
- [系统级 ADR](docs/adr/)
- [技术切片工作区](spikes/README.md)
- [切片模板](spikes/_template/README.md)

### 研究与历史

- [学习机线下调研](docs/research/2026-07-15-learning-machine-field-research.md)
- [历史文档索引](docs/archive/2026-07/README.md)

## 推荐工作流

### 1. 产品和交互变更

1. 先修改 PRD 中对应需求或明确记录待决策项；
2. 更新 `prototype/` 的交互；
3. 同步更新原型规范；
4. 记录人工验证范围和未验证项；
5. 使用 `docs:` 或 `prototype:` 类型提交。

### 2. 技术切片

1. 从 `spikes/_template/` 复制一个独立切片；
2. 使用技术验证文档中的 TS 编号；
3. 固定输入、输出 Schema、指标和通过门槛；
4. 运行结果写入切片自己的 `results/`；
5. 在 `decisions.md` 记录通过、有条件通过或不通过；
6. 将影响同步回 PRD、高保真状态矩阵和架构决策。

不要把技术切片直接扩写成生产代码；通过后再决定进入 `apps/` 或 `packages/` 的实现边界。

### 3. 高保真设计

必读输入：

1. 最新 PRD；
2. 当前可点击原型；
3. 当前原型规范；
4. 技术验证文档及已完成切片的决策；
5. 第一轮家庭可用性测试；
6. AI 核验内容、文案包及其核验状态；
7. 品牌、角色、目标设备和平台限制。

如果 P0 技术切片尚未完成，可以先做视觉方向和关键屏幕，不建议立即完成全部开发级高保真页面。

本项目不使用 Figma。高保真设计统一以 `design/high-fidelity/` 下可在浏览器运行、可编辑并纳入版本控制的 HTML、CSS、JavaScript 和设计资产为准。评审时提供本地预览地址、关键页面直达参数和必要截图；设计预览用于高保真表达与交付，不属于生产应用，也不用于提前锁定生产框架。

### 4. 完整链路开发

完成 P0 技术门槛后，再初始化真实应用和共享包。建议按垂直切片推进：

1. 固定声音夹具端到端闭环；
2. 真实语音 / 文字输入；
3. 受控讲解计划与场景运行时；
4. 追问、快照、主题分支和恢复；
5. 迁移验证与探索记录；
6. 家长记录、隐私和删除；
7. 分数第二主题；
8. 真实家庭测试和稳定性优化。

## Git 与提交

仓库当前使用 `main`。首次正式提交前，应先人工检查整理后的目录和文档链接。

推荐分支：

- Codex 工作：`codex/<topic>`；
- 产品文档：`docs/<topic>`；
- 原型：`prototype/<topic>`；
- 技术切片：`spike/ts-xx-<topic>`；
- 高保真设计：`design/<topic>`；
- 产品开发：`feature/<topic>`。

推荐提交前缀：

- `docs:` 产品、研究和技术文档；
- `prototype:` 中低保真原型；
- `spike:` 技术切片；
- `design:` 设计资产和规范；
- `feat:` 产品功能；
- `fix:` 缺陷；
- `test:` 测试和评测；
- `chore:` 工程维护。

详细规范见 [CONTRIBUTING.md](CONTRIBUTING.md)。Demo 仍是产品体验与交互验收基准，不作为生产应用架构；后续完整产品在完成技术切片和实现决策后进入 `apps/` 与 `packages/`。

## 数据与安全边界

- 不向仓库提交真实儿童语音、照片、姓名、学校、班级或其他身份信息；
- 技术切片默认使用合成夹具、去标识化样本或审核测试数据；
- 密钥只能放在本地环境变量中，不得进入 Git；
- 原始媒体与结构化学习记录必须分开管理；
- 原型截图和样例均为固定演示内容，不代表真实儿童记录；
- 删除、内容审核和版本修订必须有可审计决策记录。

## 路线图

- [x] 前期产品与竞品调研
- [x] 完整中低保真原型
- [x] PRD v4 与领域词汇
- [x] 声音价值 Demo 规范与执行 Brief
- [x] 技术验证 v2 与系统 ADR
- [x] 完成并发布声音高保真价值 Demo
- [ ] 社交媒体问卷与种子家庭招募
- [ ] P0 技术切片 TS-00、TS-02、TS-04A、TS-04B、TS-03、TS-05、TS-06
- [ ] 完整产品高保真视觉方向与关键屏幕
- [ ] 首个端到端声音主题 MVP
- [ ] 分数主题与受控内容扩展
- [ ] 真实家庭试用、效果和付费价值验证

## 明确边界

当前原型：

- 不申请真实麦克风或相机权限；
- 不保存真实儿童语音、照片或身份信息；
- 不调用真实 OCR、ASR、模型诊断、TTS 或动态场景服务；
- 5–8 秒和 15 秒状态只用于等待耐受与降级文案研究；
- 近期学习画像为明确标注的研究演示，不代表生产能力。
