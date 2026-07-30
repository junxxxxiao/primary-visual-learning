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
- **全局自适应与分层滚动契约**：研究原型、高保真设计和后续实际产品开发都必须遵循 `docs/adr/0006-adaptive-page-and-nested-scroll-contract.md`。页面文档是主要纵向滚动区；灰色讲解画布仅在内容超高时条件性滚动并在边界后把同方向手势交还页面；手机小知抽屉锁定背景并只滚动消息区，平板常驻对话栏独立滚动。导航、播放器、小知挂件和当前任务主操作必须持续可见、可触达且位于共享安全区域。固定手机审阅模式、真实短屏、平板和宽屏必须使用同一共享组件并分别验收，不得把这些约束降级为 Demo 专属规则。
- **手机安全区**：所有 C 端手机页面的背景和共享外壳必须从画布顶部开始，不显示、定义或消费独立的顶部安全区空白带，入口、提问、确认、校准、预测、加载、讲解、迁移、结果、弹层和固定 `?viewport=phone` 审阅画布均不得例外。不得在单页用临时负偏移规避。底部 Home Indicator 安全区继续由共享 `--phone-safe-bottom` Token 统一处理。
- **真实移动视口溢出审计**：手机验收不能只检查固定 `390 × 844` 画布；还必须检查带浏览器工具栏的真实可视高度，并逐状态比较 `scrollWidth/clientWidth`、`scrollHeight/clientHeight` 和关键组件边界框。必须分别验证页面、条件性画布和小知对话区的滚动起点、中段、终点、边界传递与 Overlay 锁定；核心操作必须可达，禁止用父级 `overflow: hidden` 掩盖超高内容。
- **主设计风格一致性**：所有新增前端内容必须先复用项目现有设计 Token、组件形态、色彩、描边、圆角、阴影、字体层级和图标语言，并与当前主高保真设计保持一致；不得为单个页面临时引入不属于主设计系统的新视觉语言。新增组件在实现前后都要与相邻页面及同类组件进行视觉对照。
- **全局视觉场景布局契约**：生成或修改任何固定、人工编排、动态生成或静态降级视觉场景时，必须遵循 `docs/adr/0003-visual-scene-layout-contract.md`，不得在学科、题目或页面分支中另建较弱的局部规则。手机竖屏与平板必须分别组织信息层级、运动方向、主体尺寸、画面密度和安全留白；不得把桌面横向构图直接压缩到手机，也不得让主体集中在局部而产生大面积无意义空白。
- **讲解画布硬边界门禁**：所有可视内容及完整运动轨迹必须位于共享讲解画布安全内边界，不得覆盖标题区、播放器或画布外区域。圆弧、圆角、气泡、瓶体等非矩形容器还必须声明并检查内部安全内容区，文字和图形落在容器包围盒内但越过实际可见轮廓同样判定失败。响应式实现必须通过重排、缩放和安全留白让内容完整适配，不能用 `overflow: hidden`、`clip` 或遮罩裁切来伪装通过。验收必须覆盖手机与平板的起始、关键过程、最终、暂停、恢复、交互后和减少动态效果状态：既比较全部可视元素及运动包络与画布及局部安全内边界，也比较相关容器的 `scrollWidth/scrollHeight` 与 `clientWidth/clientHeight`；任一越界或隐藏裁切即失败。每个视口和状态都必须产出可定位违规的机器可读 `pass/fail`；失败场景不得展示或缓存，应先重排或重新生成，仍失败时使用通过同一契约的渐进静态图解。
- **讲解播放契约**：所有问题、通识与学科预设必须遵循 `docs/adr/0005-lesson-runtime-state-and-timeline-contract.md`，使用问题级隔离会话和同一播放器与时序控制，不得在预设分支中直接启动、重置或跨接独立时间轴。每个讲解子片段在自动连播、手动点选、主题切换和返回原主题时都必须先完整展示起始画面并静置 `1s`，再同步启动旁白、进度和动画；暂停必须冻结当前旁白、进度和已出现画面，恢复时从同一位置继续，不得清空或重播。所有讲解动画页的标题区必须使用同一状态组：字幕开关位于段数标签正上方，段数标签只显示 `当前段 / 总段`，不得混入“自动播放”“已暂停”“关联讲解”等状态或场景文案；底部播放器只保留播放控制、分段进度和当前段标识，顶部导航不得放置字幕入口。验收必须覆盖真实音频与视觉降级两条时间轴。
- **受限交互不串台**：共享交互外壳在某个预设中需要“可见但不可操作”时，必须在提交边界统一阻断点击、键盘、长按、录音确认等所有入口，不得只禁用单个按钮。数学预设的小知录音 UI 可以打开，但确认后保持原页面和录音状态，不提交追问、不进入声音或真空主题；共享组件回归检查必须覆盖该提交边界。
- **C 端信息边界**：系统逻辑、开发状态、实现细节、内部保存字段和调试说明不得直接展示给 C 端用户。面向用户的文案只保留完成任务所需的自然提示；是否需要展示某项信息应先从用户理解和操作价值判断。
- Technical slices must test one falsifiable question and record fixtures, schemas, metrics, thresholds, failures, results, and a decision.
- Every completed slice must state its effect on the PRD, high-fidelity design, architecture, data, and privacy.
- Record what was verified and what remains unverified.

## 技术验证授权门禁

- 开始涉及模型、供应商、外部服务或其他候选实现的技术验证前，必须明确被测对象、候选供应商、模型或服务版本、调用方式、固定参数、调用预算和数据边界。
- 如果上述选择会实质影响验证结果、成本、隐私或架构结论，且用户尚未明确指定，代理必须先询问用户，不得自行选择，也不得用当前对话模型或其他未授权对象代替。
- 被测对象未确定时可以搭建测试框架，但状态只能记录为 `harness_ready`；不得表述为“已验证”“通过”或“有条件通过”，门禁自测结果也不得作为候选对象的能力证据。
- 人工、Codex 或其他非被测模型生成的夹具必须标记为 `gold_fixture` 或 `adversarial_fixture`，不得计入候选对象的正式评测分母。
- 只有通过已确认调用方式获得、可追溯到固定候选对象的输出可以标记为 `candidate_output`。结果必须记录供应商、版本、固定参数、运行时间、响应哈希、Token 或等价用量、成本和失败样例；无法取得的字段必须明确标记为未验证。
- 技术切片状态必须按证据推进：`not_started` → `harness_ready` → `candidate_run_complete` → `human_review_complete` → `conditional_pass|pass|fail`。不得跳过候选对象运行或所需人工评审直接给出最终结论。

## 证据来源门禁

- 任何开发、测试、技术切片或产品流程把事实标记为 `verified`、`verified_atom`、`temporary_verified`、可发布或等价状态前，必须存在上游产物，逐条保存来源标识、版本、页码或稳定定位、证据摘录、来源文件哈希、审核方法和内容包哈希。
- 下游流程只能消费上游导出的密封知识包，不得手工新增 claim、替换来源、复用无关 `source_refs` 或自行升级核验状态。消费前必须重新校验包哈希、来源文件哈希、页码和证据摘录；任一不一致必须在外部调用、展示、缓存或正式评测前失败。
- 来源名称、文件名、既有状态字段和引用 ID 不是证据。修改 claim 或发现知识缺口时必须打开对应原文核对；没有支持当前结论的证据时，应回到知识核验流程补齐，或明确降级为未核验/阻断，不得为了让测试通过而给旧来源挂新结论。
- 合成材料只能证明测试管线和门禁行为，必须明确标记为 synthetic，不得表述为真实教材、权威外部资料或生产知识证据。真实产品结论仍须使用已授权、可追溯的真实来源并完成规定人工审核。
- 哈希、页码和摘录存在性只能证明可追溯与防篡改，不能证明证据在学科语义上支持 claim。非 synthetic 的已核验/可发布包还必须携带独立语义审核通过产物；作者自审、字段自报或仅字符串匹配不得替代。
- 修改知识、评测 oracle、gold fixture 或来源映射时，必须增加能复现本次错误的负向回归，并同时验证上游发布和至少一个下游消费入口；只验证 Schema 或引用存在性不算完成。

## Safety boundaries

- Never commit real child voice recordings, photos, identity data, credentials, or production logs.
- Use synthetic or de-identified fixtures by default.
- Do not present prototype behavior or technical demonstrations as evidence of accuracy, stability, learning efficacy, or production readiness.
- Preserve content sources, review status, and version traceability.

## Git and verification

Follow `CONTRIBUTING.md` for branch names, commit messages, and pull-request checks. Run the verification required by the affected directory and report any checks that could not be run.

- **分支基线门禁**：创建或继续功能分支前必须先执行 `git fetch origin main`，新分支直接从 `origin/main` 创建；已有分支必须用 `git merge-base --is-ancestor origin/main HEAD` 检查是否包含远端主线。未包含时先合入或变基最新主线并完成冲突审计，不得把未刷新的本地 `main` 当成最新基线。开始修改前记录基线 SHA，验收时再次检查，避免已合并修复在旧分支中回归。

## Agent skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `junxxxxiao/primary-visual-learning`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default canonical triage labels. See `docs/agents/triage-labels.md`.

### Domain docs

Use a single-context layout with root `CONTEXT.md` and system-wide ADRs under `docs/adr/`. See `docs/agents/domain.md`.
