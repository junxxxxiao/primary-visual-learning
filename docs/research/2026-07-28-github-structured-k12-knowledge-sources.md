# GitHub 中文 K12 数学与科学结构化知识源评估

> 调研时间：2026-07-28
> 调研目标：寻找可替代教材 PDF OCR/录入的中文小学与初中数学、科学结构化数据
> 筛选口径：只采信仓库 README、固定 commit 文件树、实际数据文件、LICENSE、release 或官方数据下载入口；只有论文、模型代码、爬虫脚本或演示页面而没有可下载数据的项目不算候选。
> 结论性质：数据源可用性与成本评估，不构成版权意见或教学正确性证明。

## 1. 结论

没有找到一个 GitHub 数据源同时满足以下条件：

1. 完整覆盖小学和初中数学、小学科学、初中物理/化学/生物/综合科学；
2. 提供可直接下载的结构化概念、关系、解释或题目；
3. 每条内容可追溯到课程标准、教材版本和页码；
4. 有清晰、允许商业产品使用的数据许可证；
5. 经过权利人或教学审核。

因此，GitHub 结构化数据不能整体替代授权教材或官方课程标准。它们适合三个较窄用途：

- 用结构化图谱快速搭建 taxonomy/先修关系技术切片；
- 用公开题库补充检索、迁移题和评测夹具；
- 与授权教材抽取结果做覆盖率和关系一致性对照。

最有价值的候选是 [RCAE_graph_data](https://github.com/digitalboy/RCAE_graph_data/tree/3fbc956be3e44b2a6b2d424889b96de75019bb6e)，但它只覆盖小学数学和初高中生物，且许可证为 `CC BY-NC 4.0`，不能直接用于商业产品。另一个看似覆盖完整的 [China-K12-knowledge-taxonomy](https://github.com/bewho/China-K12-knowledge-taxonomy) 虽然有 `6,657` 个知识点和先修关系，却是从第三方网页导出的数据、没有仓库 LICENSE，也错误地把无 LICENSE 的 ChinaTextbook 标成 `CC BY 4.0`，不应作为生产事实源。

## 2. 决策总表

| 数据源 | 实际覆盖 | 数据与规模 | 数据许可 | 来源追溯 | `knowledge_atom` 适配度 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| [RCAE_graph_data](https://github.com/digitalboy/RCAE_graph_data/tree/3fbc956be3e44b2a6b2d424889b96de75019bb6e) | 小学数学；初中/高中/竞赛生物 | 2 个 JSON；5,476 节点、22,317 边；17.7 MB | CC BY-NC 4.0 | 声称来自人教/北师大等版本，但无逐页引用 | 高：概念、描述、年级、出版社、关系可直接映射 | **非商业技术切片推荐**；生产需另行授权和教师复核 |
| [China-K12-knowledge-taxonomy](https://github.com/bewho/China-K12-knowledge-taxonomy) | 小学至高中 10 学科，含目标全部科目 | `tokenmap-data.json` 4.27 MB；6,657 知识点、874 个领域簇、9,297 条关系 | 无 LICENSE；上游 tokenmap 授权不明 | 数据从网页内联脚本导出，无逐节点正式来源 | 结构高、治理低 | **仅做 schema/覆盖对照，不得进生产库** |
| [Math23K](https://github.com/SCNU203/Math23k/tree/b1135a5dddc77bcc30b4e8b021b25c68d6e15dea) | 中文小学数学应用题为主 | JSON；23,162 题；5.43 MB | 仓库 MIT；底层题目来源权利说明不足 | 无教材版本/页码 | 中低：适合作为例题和迁移题，不是概念事实 | **评测夹具推荐**；不替代知识主干 |
| [XES3G5M](https://github.com/ai4ed/XES3G5M) | 三年级数学 | 外部下载；7,652 题、约 5 百万交互；JSON/CSV/图片/embedding | 仓库 MIT，README 要求下载即同意 license；数据权利边界仍需确认 | 来自中国 K12 在线平台，无教材页码 | 中高：KC 路径、题目、答案、解析、图片 | **可做单年级数学切片**；先确认数据许可和隐私边界 |
| [C-Eval](https://github.com/SJTU-LIT/ceval/tree/cba65ae93bcf189149ced9f66ae0c958201faed9) | 初中数学/物理/化学/生物；无小学 | CSV/Hugging Face；全体 52 科、13,948 道选择题 | 数据 CC BY-NC-SA 4.0；代码 MIT | 学段和学科明确，无教材页码；测试答案不公开 | 低：适合覆盖评测，不适合解释知识库 | **非商业评测辅助** |
| [M3KE](https://github.com/tjunlp-lab/M3KE) | 小学数学；初中数学/物理/化学/生物/地理 | JSONL；全体 71 任务、20,477 题 | 仓库无 LICENSE | 层级/科目明确，无教材页码；大量测试答案为空 | 低 | **仅作 benchmark 参考，不进入知识库** |
| [Ape210K](https://github.com/Chenny0808/ape210k) | 中文数学应用题，学段/年级未可靠标注 | JSON；210,488 题、56,532 模板 | 无根 LICENSE；README 仅说明代码沿用 OpenNMT-py license | 无教材或课程标准引用 | 低：题目/方程/答案可作训练或评测 | **可研究，不建议纳入生产语料** |
| [EduChat-Math / CMM-Math](https://github.com/ECNU-ICALK/EduChat-Math/tree/ccaedb70) | 1–12 年级数学；1–9 年级 19,548 条 | JSONL + 图片；全体 28,069 条、25.9 MB；7,950 条引用图片 | 无 LICENSE | README 未说明题目来源和标注权利 | 中：题目、答案、逐题解析、年级可映射 | **强评测/例题候选，但未获授权前不得生产使用** |
| [FineMATH](https://github.com/tjunlp-lab/FineMATH/tree/67f1f01) | 小学数学应用题 | JSON；1,584 题、17 类、539 KB | 无 LICENSE | README 仅一句说明，无来源链 | 低 | **仅作题型 taxonomy 参考** |
| [CMATH-Pro](https://github.com/GhostRin001/CMATH-Pro/tree/16422b6) | 1–6 年级数学 | JSONL；1,698 题、342 KB | MIT | 自称由 CMATH 精炼，未建立上游数据权利链 | 中低 | **小型推理回归候选，需补上游授权审计** |
| [Jia-Yee/math-knowledge-graph](https://github.com/Jia-Yee/math-knowledge-graph/tree/4a1498b30cff977ecd355b88ecdc37435058e84c) | 数学全域；3,524 个节点标为小学/初中 | JSON；25,355 节点、58,965 边；约 41.3 MB | MIT | README 明示由 AI 生成，参考源不逐节点绑定 | 表面高、可信度低 | **只参考 schema，不使用内容** |
| [OpenEduKG](https://github.com/OpenEduTech/OpenEduKG/tree/e75824184caaaf1fb11bb3257e5d69bd91ed6174) | 无可验证 K12 数学科学数据 | 仓库主要为文章、演示、医学图谱和学术材料 | 无根 LICENSE | 无 | 无 | **排除：名为知识图谱但没有目标数据** |
| [kechengbiaozhun](https://github.com/7jul/kechengbiaozhun/tree/b0092d5d58c856cf12a2f17e435c3ff057cd0492) | README 声称 2022 义务教育课标 | 仓库只有 README，无课标数据 | 无 LICENSE | 无 | 无 | **排除：空壳** |

## 3. 明确推荐（限定用途）

### 3.1 RCAE_graph_data：非商业图谱切片首选

固定版本：[digitalboy/RCAE_graph_data@3fbc956](https://github.com/digitalboy/RCAE_graph_data/tree/3fbc956be3e44b2a6b2d424889b96de75019bb6e)

仓库内确实存在两个较大的 JSON 数据文件，不是只有可视化代码：

- `china_primary_school_math_knowledge_graph.json`：`2,264` 个节点、`10,227` 条边；
- `生物的节点和边（初中，高中和竞赛）.json`：`3,212` 个节点、`12,090` 条边；
- 两文件合计 `17,725,954` bytes。

小学数学节点包含 description、年级册次（如“小学五年级上册”）、出版社、学科和 UUID。README 声称小学数学来自人教版与北师大版，生物覆盖初中、高中和竞赛。这些字段可以较低成本映射到：

```text
knowledge_atom.title
knowledge_atom.core_fact / description
knowledge_atom.grade_range
knowledge_atom.subject
knowledge_atom.edition_or_publisher
knowledge_atom.prerequisite / related_to
```

但它缺少当前 PRD 要求的来源页码、教材文件 hash、成立条件、例外、常见误解、可观察信号、视觉变量、迁移任务和审核记录。README 也明确承认数据可能不完整或有错误。因此，它适合验证图数据库、先修检索和原子 Schema，不适合直接向儿童生成讲解。

[LICENSE.md](https://github.com/digitalboy/RCAE_graph_data/blob/3fbc956be3e44b2a6b2d424889b96de75019bb6e/LICENSE.md)是 `CC BY-NC 4.0`。如果产品存在商业目的，必须取得额外授权，不能通过“只做向量索引”绕过非商业限制。

### 3.2 Math23K：小学数学例题与迁移评测夹具

固定版本：[SCNU203/Math23k@b1135a5](https://github.com/SCNU203/Math23k/tree/b1135a5dddc77bcc30b4e8b021b25c68d6e15dea)

仓库实际包含 `22,162` 条训练题和 `1,000` 条测试题，共 `23,162` 条、约 `5.43 MB`。记录含原题文本、分词文本、方程和答案。它能补充：

- 数量关系与应用题表述；
- 从文字到方程的映射；
- 相似例题检索；
- 迁移题和解题正确率回归集。

它不提供知识点定义、先修关系、教材版本、页码或教学解释，所以不能替代教材主干。仓库有 MIT LICENSE，但 README 没有充分说明题目收集来源及底层题目权利；正式使用前仍需做数据权利确认。推荐仅把合成/人工复核后的子集作为评测夹具。

## 4. 可辅助数据

### 4.1 XES3G5M：丰富但只覆盖三年级数学

[ai4ed/XES3G5M](https://github.com/ai4ed/XES3G5M) 的 GitHub 仓库只保存说明和 MIT LICENSE，真实数据通过 README 中的 Google Drive 下载。README 给出的规模为 `18,000+` 名三年级学生、约 `8,000` 道题、`5 million+` 交互；澄清段给出 `7,652` 道有效题。

对本项目最有价值的是 `metadata/questions.json`：题目正文、KC routes、答案、选项、详细解析、题型，以及独立图片目录；另有 `kc_routes_map.json` 和题目/KC embedding。这比普通题库更接近候选原子中的“知识点—题目—解析—关系”。

限制也很明确：只有三年级数学；KC 和题目来源于一个在线学习平台而非可定位教材页；仓库没有在 GitHub 内提供数据快照和 hash；下载说明只说“下载即同意 license”。在把 MIT 解释为覆盖题目、解析、图片与交互数据前，应要求数据提供方书面确认。学生交互数据不是本项目知识主干所必需，应默认不导入。

### 4.2 C-Eval：初中科学覆盖率与答题回归

固定版本：[SJTU-LIT/ceval@cba65ae](https://github.com/SJTU-LIT/ceval/tree/cba65ae93bcf189149ced9f66ae0c958201faed9)

C-Eval 全体包含 `52` 个科目、`13,948` 道选择题，数据可从 README 指向的 zip/Hugging Face 直接下载。目标范围中有初中数学、物理、化学、生物，没有小学数学或小学科学。CSV 字段为 question、A/B/C/D、answer；每科 dev 集只有 `5` 个带 explanation 的 few-shot 样例，公开 test 不给答案。

它适合建立“目标年级与科目是否能答对”的小型回归集，不适合作为解释知识库。数据许可证是 [CC BY-NC-SA 4.0](https://github.com/SJTU-LIT/ceval/blob/cba65ae93bcf189149ced9f66ae0c958201faed9/LICENSE-DATA)，商业产品不能直接吸收，ShareAlike 也需要单独评估衍生数据义务。

### 4.3 M3KE：学段覆盖广，但可用标签和许可不足

[tjunlp-lab/M3KE](https://github.com/tjunlp-lab/M3KE) 在仓库内提供 JSONL 数据，README 声明全体 `71` 个任务、`20,477` 道四选一题，覆盖小学数学和初中数学、物理、生物、化学、地理。字段是 id、question、A/B/C/D、answer。

问题在于：仓库没有 LICENSE；每个任务 dev 只有 `5` 个样例，test 示例的 answer 为空；它是模型知识评测集，不是带讲解和来源的课程内容。可用于了解 benchmark 题型，不应复制进生产知识库。

### 4.4 Ape210K：大规模数学题型库，不是课程知识库

[Chenny0808/ape210k](https://github.com/Chenny0808/ape210k) 确实在 `data/` 中提供 train/valid/test JSON，共 `210,488` 道题和 `56,532` 个方程模板，字段包括题目、方程、模板和答案。规模大意味着它能覆盖大量中文数学应用题表达，但没有稳定的年级、教材版本、知识点或来源页。

仓库没有根 LICENSE。README 说模型代码沿用 OpenNMT-py 许可证，不能据此推断题库内容也获得同样授权。全量导入还会增加清洗、去重、分级和审核 token，未必比只选 Math23K 或自建授权评测集更省。

### 4.5 EduChat-Math、FineMATH 与 CMATH-Pro：题目和解析层候选

[ECNU-ICALK/EduChat-Math@ccaedb70](https://github.com/ECNU-ICALK/EduChat-Math/tree/ccaedb70) 的 CMM-Math 数据不是空壳：`data/all_data.jsonl` 有 `28,069` 条、约 `25.9 MB`，训练集 `22,248`、测试集 `5,821`，覆盖 12 个年级；1–9 年级共 `19,548` 条。字段含 question、options、answer、analysis、subject 和 level，每条都有 analysis。仓库还有大量题图，`7,950 / 28,069` 条记录引用图片，完整 checkout 约 `649 MB`。

它是本次找到的最强中文 K12 数学“题目—答案—解析”候选，但没有 LICENSE/COPYING，README 也没有说明题目来源、图片权利和解析标注授权。只有在取得书面许可后，才适合作为例题与迁移题库；即使获授权，它也缺少概念定义、先修关系、课程完整性和教材页引用。

[tjunlp-lab/FineMATH@67f1f01](https://github.com/tjunlp-lab/FineMATH/tree/67f1f01) 实际提供 `1,584` 道中文小学应用题，分 `17` 个命名类别和 `3` 档推理步数，JSON 约 `539 KB`，但 README 只有一句说明且没有 LICENSE。可参考类别设计，不应复制题目。

[GhostRin001/CMATH-Pro@16422b6](https://github.com/GhostRin001/CMATH-Pro/tree/16422b6) 有 `1,698` 道 1–6 年级 JSONL 题，字段为 question、golden、reasoning_step 和 num_digits，仓库是 MIT。它声称由 CMATH 精炼，但 README 没有证明上游 CMATH 题目的来源和再许可权；因此可作为小型推理回归候选，使用前仍需沿上游数据链审计。

## 5. 不推荐

### 5.1 China-K12-knowledge-taxonomy：结构最好，权利与事实源最弱

[bewho/China-K12-knowledge-taxonomy](https://github.com/bewho/China-K12-knowledge-taxonomy) 的 `_raw/tokenmap-data.json` 确实存在，GitHub 显示大小 `4.27 MB`。README 给出 `10` 学科、`874` 个领域簇、`6,657` 个知识点、`7,396` 条先修边和 `1,901` 条关联边，并包含知识点描述和掌握标准。它与 `knowledge_atom` 的结构适配度很高。

但仓库 README 明确说明数据是从 `tokenmap.com.cn/knowledge` 页面的内联 `<script id="DATA">` 导出，仓库没有 LICENSE，也没有 tokenmap 对再分发、商用和衍生使用的授权。更严重的是，README 把 [TapXWorld/ChinaTextbook](https://github.com/TapXWorld/ChinaTextbook) 标成 `CC BY 4.0`，而对后者的固定版本审计结果是 GitHub API `license: null` 且根目录无 LICENSE。这说明该仓库的许可陈述不能直接信任。

结论：可以借鉴 subject/domain/knowledge point/prerequisite/association 的 Schema，也可以在隔离环境中做覆盖率对照；不得缓存进生产检索、不得作为教材事实、不得向用户展示其来源结论。

### 5.2 Jia-Yee/math-knowledge-graph：AI 生成内容造成循环核验

固定版本：[Jia-Yee/math-knowledge-graph@4a1498b](https://github.com/Jia-Yee/math-knowledge-graph/tree/4a1498b30cff977ecd355b88ecdc37435058e84c)

它确实有约 `41.3 MB` JSON、`25,355` 节点和 `58,965` 条边，其中 `3,524` 个节点带小学/初中标签，并使用 MIT License。问题不是格式，而是 README 明示内容由 AI “智能生成”，参考列表没有逐节点引用，样本中还有占位式练习答案/解答。

使用生成式 AI 重新核验 AI 生成的知识图谱，会形成来源循环；为达到儿童讲解所需的准确度，逐节点回溯权威来源的成本接近重新建设知识库，token 优势基本消失。因此只建议参考 Schema 和图数据工具链。

### 5.3 OpenEduKG 和 kechengbiaozhun：没有目标数据

- [OpenEduTech/OpenEduKG@e758241](https://github.com/OpenEduTech/OpenEduKG/tree/e75824184caaaf1fb11bb3257e5d69bd91ed6174) 虽称开放教育知识图谱，实际文件树主要是文章、PPT、演示代码、医学图谱和学术材料，没有可下载的 K12 数学/科学课程图谱，且无根 LICENSE。
- [7jul/kechengbiaozhun@b0092d5](https://github.com/7jul/kechengbiaozhun/tree/b0092d5d58c856cf12a2f17e435c3ff057cd0492) README 声称可搜索 2022 义务教育课程标准，但固定 commit 只有 README，没有标准正文、结构化数据或 LICENSE。

两者都不应进入后续技术评估。

## 6. 是否真的节省 token

结构化数据主要节省 PDF 合并、页面渲染、OCR、公式/图表识别和章节结构恢复的 token，不会消除规范化、去重、来源核验、关系校验、embedding 和发布审核。

以前一份 ChinaTextbook 评估中的标准核心 PDF 路线 `0.8–2.5 亿 token` 为对照：

| 路线 | 原始规模 | 规划处理 token | 相对 PDF 路线 | 代价 |
| --- | ---: | ---: | ---: | --- |
| RCAE 两图谱 | 17.7 MB | 约 800–2,500 万 | 节省约 70%–95% | 只覆盖小学数学+生物；非商业；无页级引用 |
| Math23K | 5.43 MB / 23,162 题 | 约 300–800 万 | 对题库 ingest 大幅节省 | 不是概念库，来源权利不充分 |
| EduChat-Math | 25.9 MB / 28,069 题 | 约 500–1,500 万，另计题图 | 跳过约 1.95 万条 1–9 年级题目的 OCR | 无许可证；28% 记录仍需多模态处理 |
| tokenmap 导出图 | 4.27 MB / 6,657 点 | 约 500–1,500 万 | 结构化程度最高 | 无许可证和逐点来源，不能生产使用 |
| Jia-Yee AI 数学图谱 | 41.3 MB / 25,355 点 | 表面约 2,000–6,000 万 | 可能节省 OCR | 权威回溯会把成本重新推高 |

这些区间包括 JSON 解析后的文本、原子 Schema 转换、关系检查、一次 embedding 和有限自动复核，不包含教师逐条审核。实际 token 取决于中文 tokenizer、描述长度、批大小、提示模板和返工率。

一个关键判断是：**弱来源数据只能节省抽取 token，不能节省事实核验成本**。对于儿童讲解，事实核验、适龄表达和视觉/迁移设计才是更昂贵的部分。把未授权或不可追溯图谱直接导入，会以更低的 ingest 账单换来更高的错误与返工风险。

## 7. 建议的数据分层

不要寻找一个“GitHub 全能知识库”，而应明确三层：

```text
authoritative_source
  官方课程标准 + 已授权教材/数字内容
  提供事实、版本、页码/hash、适用边界

candidate_taxonomy
  RCAE 等结构化图谱的隔离副本
  只用于候选概念、别名和先修关系发现

evaluation_fixture
  Math23K / C-Eval / 经授权的 XES3G5M 子集
  只用于题型、检索召回、迁移与回归测试
```

映射到 `knowledge_atom` 时，任何 GitHub 候选默认设置：

```text
review_status = unverified
rights_status = blocked_or_research_only
source_tier = non_authoritative_candidate
publishable = false
```

只有当一个候选节点被官方课程标准或授权教材的具体版本、页码和 hash 支持，并通过来源、边界和教学检查，才能升级为可发布知识原子。题库中的答案正确也不能替代概念来源核验。

## 8. 推荐下一步

1. 不做全量 GitHub 数据导入；先争取一个小学数学版本和一组小学科学/初中科学授权章节。
2. 用 RCAE 的小学数学子图做非商业离线对照，抽取 `100` 个节点，与授权教材页逐一匹配。
3. 用 Math23K 的人工复核子集建立文字题检索和迁移回归；不保存无法说明权利来源的原题到生产环境。
4. C-Eval 只在非商业研究评测中使用；若产品商业化，改用自研或已授权评测题。
5. 将“结构化来源相较 PDF 是否降低总审核工时”作为技术切片指标，而不只比较 token。

建议通过门槛：`100` 个候选节点中，至少 `98%` 能匹配到权威来源且关系语义正确；每个已升级原子都有教材/课标版本和定位；不存在由无许可证数据复制而来的发布字段。未达到时，停止扩图，回到授权教材的小批量解析路线。

## 9. 已验证与未验证

已验证：

- 上述仓库的 README、实际文件树、数据文件存在性、公开规模说明和 LICENSE 状态；
- RCAE、Math23K 和 Jia-Yee 数据的固定 commit、节点/边或题目数量与字节规模；
- C-Eval 的数据许可、学科范围、下载格式和公开答案边界；
- OpenEduKG 与 kechengbiaozhun 没有可用目标数据；
- tokenmap 导出仓库没有 LICENSE，且对 ChinaTextbook 的许可声明与后者实际仓库状态冲突。

仍未验证：

- 任一数据集中每条内容的教学正确率、现行课程标准匹配率和完整覆盖率；
- XES3G5M 下载协议是否把 MIT 明确扩展到题目、解析、图片和交互数据；
- Math23K、Ape210K 底层题目的复制、改编和商业使用权；
- EduChat-Math、FineMATH、CMATH-Pro 及其上游题目/图片的再许可链；
- 非商业许可证数据参与 embedding、检索或衍生 Schema 时的具体法律边界；
- 真实 tokenizer 和目标模型下的 ingest token、教师审核工时与在线效果。
