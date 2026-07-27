# 协作与 Git 规范

## 基本原则

- `main` 保持可审阅、可运行；
- 一次提交只处理一个清晰主题；
- 产品事实、原型、技术决策和代码变更保持可追踪；
- 不提交真实儿童敏感数据、密钥和未经授权的第三方内容；
- 不用技术演示结果替代稳定性、准确率或学习效果证据。

## 分支命名

- Codex：`codex/<topic>`
- 文档：`docs/<topic>`
- 原型：`prototype/<topic>`
- 技术切片：`spike/ts-xx-<topic>`
- 设计：`design/<topic>`
- 功能：`feature/<topic>`
- 修复：`fix/<topic>`

分支名称使用小写英文、数字和短横线。

### 分支基线检查

创建功能分支前先刷新远端主线，并直接从 `origin/main` 创建：

```bash
git fetch origin main
git switch -c codex/<topic> origin/main
```

继续已有功能分支前必须检查是否包含远端最新主线：

```bash
git fetch origin main
git merge-base --is-ancestor origin/main HEAD
```

若检查失败，说明远端 `main` 有当前分支尚未包含的提交。开始新修改前先合入或变基 `origin/main`，逐项解决共享文件冲突并运行对应回归矩阵。不得仅检查本地 `main`，也不得在已知基线落后的情况下用局部补丁代替完整缺失审计。任务记录和 PR 描述应写明开始实现时的 `origin/main` SHA。

## 提交信息

使用简短的 Conventional Commit 风格：

```text
docs: add high-fidelity input checklist
prototype: refine mobile tutor drawer
spike: validate scene snapshot recovery
design: add child typography tokens
feat: persist exploration events
fix: preserve parent record filter on expand
test: add golden sound fixture evaluation
chore: initialize workspace structure
```

提交正文应说明：

1. 为什么修改；
2. 修改了什么；
3. 如何验证；
4. 哪些内容未验证；
5. 是否影响 PRD、技术决策、数据或隐私。

## Pull Request 检查

- [ ] 变更范围单一且标题清楚；
- [ ] 相关 PRD、原型规范或技术决策已同步；
- [ ] UI 变更符合 ADR-0004，并验证固定手机、真实短屏、平板和宽屏的滚动归属、固定操作可见性与边界；
- [ ] 讲解或动画变更符合 ADR-0003，逐状态检查画布边界、非矩形内部安全区和隐藏裁切；
- [ ] 讲解播放、追问或恢复变更符合 ADR-0005，验证问题级会话隔离、单一时间轴、暂停恢复和媒体降级；
- [ ] 新交互包含正常、加载、失败和降级状态；
- [ ] 技术切片包含固定夹具、指标和通过标准；
- [ ] 测试或人工验证方法已记录；
- [ ] 不包含密钥和真实儿童敏感数据；
- [ ] 新增文件位于正确目录；
- [ ] README 和相对链接没有失效；
- [ ] 大型二进制设计资产有明确来源和用途。

## 技术切片的提交边界

每个切片使用独立分支和目录。至少提交：

- `README.md`：验证问题、范围、运行方法和门槛；
- `fixtures/`：合成或去标识化夹具；
- `schemas/`：输入输出契约；
- `src/` / `scripts/`：最小实现；
- `results/summary.json`：可复核指标；
- `decisions.md`：通过、有条件通过或不通过。

切片代码通过后，再以独立 PR 提取到 `apps/` 或 `packages/`，避免把临时代码直接当成生产架构。

## 设计提交边界

仓库提交本地可运行的高保真页面、设计规范、Token、资源清单和必要的关键截图或导出。本项目不使用 Figma；`design/high-fidelity/` 中的 HTML、CSS、JavaScript 和本地设计资产是可编辑、可审阅的设计交付源。大量临时导出放在 `design/high-fidelity/exports/`，默认不进入 Git。

每次高保真交付应说明：

- 对应 PRD 版本；
- 对应原型版本；
- 已覆盖设备和状态；
- 仍受哪些技术切片结论影响；
- 资产版权与来源；
- 本地打开或运行方式、关键页面直达参数和浏览器验证结果。

## 数据安全

禁止提交：

- 真实儿童原始语音和照片；
- 姓名、学校、班级、联系方式和账号标识；
- 未经授权的课堂录屏或教材扫描；
- API Key、Token、证书和生产日志；
- 可反推出儿童身份的原始评测数据。

需要保存评测证据时，使用合成夹具、去标识化摘要和受控的外部安全存储，在仓库中只记录版本、哈希和访问说明。
