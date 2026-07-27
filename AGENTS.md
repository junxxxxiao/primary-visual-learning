# Repository guidelines

## Required reading

Before making changes, read:

1. `README.md` for project status, source-of-truth priority, and workflows.
2. `CONTRIBUTING.md` for Git, commits, review, and data-safety rules.
3. The nearest directory-level `README.md` for area-specific constraints.

## Project phase

This repository is currently validating product assumptions and technical feasibility.

- Do not initialize production applications or prematurely lock frameworks.
- Do not evolve `prototype/` into production code.
- Do not treat code under `spikes/` as production architecture.
- Move validated capabilities into `apps/` or `packages/` only through a separate implementation decision.

## Sources of truth

When requirements conflict, follow this order:

1. Latest PRD under `docs/product/`.
2. Current clickable prototype under `prototype/`.
3. Current prototype specification under `docs/design/`.
4. Completed technical-slice decisions.
5. Archived product and research documents.

Archived documents provide background and are not active requirements.

## Change synchronization

- Product or interaction changes must update the relevant PRD, prototype, and prototype specification together.
- **全局组件一致性**：无论设计还是开发，相同组件必须作为共享组件统一修改，并同步检查所有使用页面；不得只修一个页面的局部副本（例如播放器、返回按钮、抽屉、反馈卡）。
- **共享组件覆盖审计**：修改共享组件前后必须搜索并清理各页面对该组件的旧选择器和局部覆盖；定位类样式必须完整声明 `top/right/bottom/left/transform/size`，不得依赖只覆盖部分属性。验收时至少抽查每个使用页面的计算样式与边界框，不能只看一个代表页面。
- **双端同步与排版兼容**：修改任一端（平板 / 手机、设计 / 实现）的内容、状态或交互后，必须同步检查另一端，并验证响应式排版、溢出、遮挡、焦点和触控尺寸。
- **固定手机审阅视角**：每次涉及 UI 或交互的审阅与验收，都必须同时打开 `?viewport=phone` 视角；该参数固定使用 `390 × 844` 手机画布，不得随桌面浏览器窗口尺寸伸缩。`file://` 与 HTTP 入口不带 `viewport` 时都必须按真实窗口自适应，不得擅自默认到某一设备；固定审阅模式只能由显式参数启用。
- **手机安全区**：所有手机页面必须通过共享安全区 Token 处理系统状态栏、摄像头刘海 / 灵动岛和底部 Home Indicator；真实设备读取 `env(safe-area-inset-*)`，同时在系统值为 `0` 时保留明确的最小顶部 / 底部安全距离，固定 `?viewport=phone` 审阅画布必须模拟安全区。不得在单页用临时偏移规避遮挡。
- **主设计风格一致性**：所有新增前端内容必须先复用项目现有设计 Token、组件形态、色彩、描边、圆角、阴影、字体层级和图标语言，并与当前主高保真设计保持一致；不得为单个页面临时引入不属于主设计系统的新视觉语言。新增组件在实现前后都要与相邻页面及同类组件进行视觉对照。
- **讲解动画响应式构图**：生成或修改讲解演示动画时，必须分别为手机竖屏与平板布局组织信息层级、运动方向、主体尺寸和安全留白；不得把桌面横向构图直接压缩到手机，也不得让主体集中在局部而产生大面积无意义空白。每个动画状态都要检查画面密度、可读性、遮挡、裁切及旁白语义对应关系，并在手机与平板基准视口分别验收。
- **讲解画布硬边界**：所有讲解演示的可视内容（文字、公式、图形、标注、动画主体及其运动轨迹）必须完整位于共享讲解画布内，不得覆盖标题区、播放器或画布外区域；画布必须统一建立布局与绘制隔离。响应式实现必须通过重排、缩放和安全留白让内容完整适配，不能用 `overflow: hidden`、`clip` 或遮罩裁切来伪装通过。验收时必须检查手机与平板的每个子片段起始、过程和最终状态：既比较所有可视元素边界框与画布内边界，也比较所有容器的 `scrollWidth/scrollHeight` 与 `clientWidth/clientHeight`；任一元素越界或任一容器发生隐藏裁切即失败。控制台警告不算门禁，审计必须产出机器可读的 pass/fail，并阻止失败状态通过验收。
- **讲解播放契约**：所有通识与学科预设必须共用同一播放器与时序控制，不得在预设分支中直接启动或重置独立时间轴。每个讲解子片段在自动连播、手动点选、主题切换和返回原主题时都必须先完整展示起始画面并静置 `1s`，再同步启动旁白、进度和动画；暂停必须冻结当前旁白、进度和已出现画面，恢复时从同一位置继续，不得清空或重播。字幕开关只能由共享底部播放器拥有，顶部导航只显示导航、主题和播放状态，不得通过页面选择器或运行时脚本新增字幕入口。验收必须覆盖真实音频与视觉降级两条时间轴。
- **受限交互不串台**：共享交互外壳在某个预设中需要“可见但不可操作”时，必须在提交边界统一阻断点击、键盘、长按、录音确认等所有入口，不得只禁用单个按钮。数学预设的小知录音 UI 可以打开，但确认后保持原页面和录音状态，不提交追问、不进入声音或真空主题；共享组件回归检查必须覆盖该提交边界。
- **C 端信息边界**：系统逻辑、开发状态、实现细节、内部保存字段和调试说明不得直接展示给 C 端用户。面向用户的文案只保留完成任务所需的自然提示；是否需要展示某项信息应先从用户理解和操作价值判断。
- Technical slices must test one falsifiable question and record fixtures, schemas, metrics, thresholds, failures, results, and a decision.
- Every completed slice must state its effect on the PRD, high-fidelity design, architecture, data, and privacy.
- Record what was verified and what remains unverified.

## Safety boundaries

- Never commit real child voice recordings, photos, identity data, credentials, or production logs.
- Use synthetic or de-identified fixtures by default.
- Do not present prototype behavior or technical demonstrations as evidence of accuracy, stability, learning efficacy, or production readiness.
- Preserve content sources, review status, and version traceability.

## Git and verification

Follow `CONTRIBUTING.md` for branch names, commit messages, and pull-request checks. Run the verification required by the affected directory and report any checks that could not be run.

## Agent skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `junxxxxiao/primary-visual-learning`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default canonical triage labels. See `docs/agents/triage-labels.md`.

### Domain docs

Use a single-context layout with root `CONTEXT.md` and system-wide ADRs under `docs/adr/`. See `docs/agents/domain.md`.
