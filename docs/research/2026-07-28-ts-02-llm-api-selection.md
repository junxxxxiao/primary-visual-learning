# TS-02 大模型 API 首轮选型研究

> 日期：2026-07-28
> 范围：中国小学至初中数学 / 科学、中文教材解析、知识核验与讲解生成
> 资料边界：只使用厂商官方模型文档、API 文档、价格页和数据控制说明；外部事实均附官方链接
> 结论性质：测试候选排序，不是生产供应商决策，也不代表模型已达到教育准确性、儿童适配或合规要求

## 1. 结论

TS-02 首轮建议按以下顺序测试 3 个配置：

1. **`qwen3.7-plus-2026-05-26`**：作为境内、可固定日期版本、成本相对可控的基线。官方价格页明确提供该日期快照；在不超过 256K 输入时原价为输入 2 元、非思考或思考输出均 8 元 / 百万 Token，超过 256K 至 1M 时分别为 6 元和 24 元 / 百万 Token。[阿里云百炼模型价格](https://help.aliyun.com/zh/model-studio/model-pricing)
2. **`deepseek-v4-pro`**：作为低成本与第二个独立模型族对照。官方当前 API 只列出 `deepseek-v4-flash` 和 `deepseek-v4-pro`；两者均为 1M 上下文、最大 384K 输出并支持思考 / 非思考、JSON Output 和工具调用，Pro 的缓存未命中输入与输出价格分别为 3 元和 6 元 / 百万 Token。[DeepSeek 模型与价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing)
3. **`gpt-5.6-terra`**：只在调用主体和运行地域满足 OpenAI 官方支持范围的前提下，作为严格结构化输出和跨供应商质量对照。官方将 Terra 定位为智能与成本平衡档，支持 1,050,000 Token 上下文、Structured Outputs、图像输入和 file search；标准短上下文原价为输入 2.50 美元、输出 15 美元 / 百万 Token。[Terra 模型页](https://developers.openai.com/api/docs/models/gpt-5.6-terra) [OpenAI 价格页](https://developers.openai.com/api/docs/pricing) 中国大陆不在 OpenAI 官方 API 支持国家 / 地区清单中，官方说明从清单外访问或提供访问可能导致账号被封禁或暂停。[OpenAI 支持国家与地区](https://developers.openai.com/api/docs/supported-countries)

首轮不要同时上 `qwen3.7-max` 和 `gpt-5.6-sol`。只有当对应平衡档在事实核验、冲突识别或中文教学表达上未达门槛，而且失败样例显示更强推理可能有帮助时，再按 **Qwen Plus -> Qwen Max**、**Terra -> Sol** 做同供应商单变量升级。`qwen3.7-max` 当前别名等同于 `qwen3.7-max-2026-05-20`，官方另提供 `qwen3.7-max-2026-06-08` 等日期版本；原价为输入 12 元、输出 36 元 / 百万 Token。[阿里云百炼模型价格](https://help.aliyun.com/zh/model-studio/model-pricing) `gpt-5.6-sol` 是 OpenAI 5.6 旗舰档，标准短上下文原价为输入 5 美元、输出 30 美元 / 百万 Token。[Sol 模型页](https://developers.openai.com/api/docs/models/gpt-5.6-sol) [OpenAI 价格页](https://developers.openai.com/api/docs/pricing)

阿里云模型目录还列出更新的 `qwen3.8-max-preview`，但官方注明它当前只面向 Token Plan 订阅用户。首轮需要按请求记录实际 Token 与费用并固定可复现配置，因此不把预览订阅型号替代稳定的 `qwen3.7-max` / `qwen3.7-plus` API 组合；待其进入常规 API 计费并提供可固定版本后再重新评估。[阿里云百炼模型目录](https://help.aliyun.com/zh/model-studio/models)

这份排序不依据公开榜单。各厂商官方资料均未提供与本项目相同的“中国小学至初中、指定教材页、知识核验、儿童中文讲解”准确率，因此中文教育质量只能用 TS-02 固定夹具、独立人工审核和重复运行得到。

## 2. 为什么与 TS-02 匹配

本仓库的 [TS-02 切片](../../spikes/ts-02-knowledge-validation/README.md) 已固定 12 个输入包及硬门槛：5 个发布、3 个 `unverified_generated`、4 个阻断，并要求来源页码可追溯、缺学段不猜测、无来源不伪装成已核验、冲突 / OCR 污染 / 提示注入不发布。模型选型需要回答的是“哪一个冻结配置最稳定地遵守这套管线契约”，而不是“哪一个模型通用分数最高”。

所有候选都只能消费经过授权和本地预处理的指定页段，并输出候选核验结果；模型记忆不能成为来源。即使厂商提供百万级上下文，也不应把整套教材无选择地塞入请求，因为 TS-02 仍需保留页码、版本、哈希、证据摘录和版权访问边界。

## 3. 官方能力对比

### 3.1 型号、推理与长上下文

| 候选 | 官方定位与推理控制 | 上下文 / 文档相关能力 | 对 TS-02 的含义 |
|---|---|---|---|
| `gpt-5.6-sol` | GPT-5.6 旗舰档；`gpt-5.6` 别名会路由到 Sol。5.6 支持从 `none` 到 `max` 的 reasoning effort。[GPT-5.6 指南](https://developers.openai.com/api/docs/guides/latest-model.md) | 1,050,000 Token 上下文，最大输入 922K、最大输出 128K；支持文本、图像、file search 与 web search。[Sol 模型页](https://developers.openai.com/api/docs/models/gpt-5.6-sol) Responses 的 PDF `input_file` 会同时抽取文本和页面图像，GPT-5.6 的 `auto` 图像细节默认为 `high`。[OpenAI 文件输入](https://developers.openai.com/api/docs/guides/file-inputs) | 只作为 Terra 失败后的质量上限复测；TS-02 首轮不需要其全部工具面。 |
| `gpt-5.6-terra` | 官方定位为智能与成本平衡档，支持与 Sol 相同的 reasoning effort 机制。[GPT-5.6 指南](https://developers.openai.com/api/docs/guides/latest-model.md) | 与 Sol 相同的 1,050,000 Token 上下文、922K 最大输入、128K 最大输出和文本 / 图像输入。[Terra 模型页](https://developers.openai.com/api/docs/models/gpt-5.6-terra) 同样可使用 Responses PDF 文本与页面图像输入。[OpenAI 文件输入](https://developers.openai.com/api/docs/guides/file-inputs) | 适合作为条件满足后的 OpenAI 平衡档，并验证严格 Schema 是否显著减少发布裁决重试。 |
| `qwen3.7-max` | 官方将其列为最强推理候选；提供 `qwen3.7-max-2026-06-08` 等日期快照，但能力表明确标记不支持结构化输出。[千问文本生成模型](https://help.aliyun.com/zh/model-studio/text-generation-model/) | 1M Token 上下文；模型目录同时提供北京、新加坡、东京、法兰克福和弗吉尼亚入口，以及 OpenAI / Anthropic / DashScope 兼容协议。[阿里云百炼模型目录](https://help.aliyun.com/zh/model-studio/models) | 只复测 Plus 的推理失败样例；输出必须走普通文本加本地解析 / 校验，不能假定 JSON Mode 可用。 |
| `qwen3.7-plus` | 官方定位为能力与成本均衡，提供 `qwen3.7-plus-2026-05-26` 日期快照；能力表明确列出结构化输出支持。[千问文本生成模型](https://help.aliyun.com/zh/model-studio/text-generation-model/) | 1M Token 上下文，官方推荐用于聊天、内容生成、摘要和文档处理；同样提供北京及多个海外地域和三种兼容协议。[千问文本生成模型](https://help.aliyun.com/zh/model-studio/text-generation-model/) [阿里云百炼模型目录](https://help.aliyun.com/zh/model-studio/models) | 首轮境内基线；固定日期快照，避免别名后续漂移。官方“文档处理”场景不是原生 PDF / DOCX 二进制解析证明，TS-02 仍先本地预处理。 |
| `deepseek-v4-pro` | 官方支持思考 / 非思考；思考默认开启，OpenAI 格式可用 `thinking` 和 `reasoning_effort=high|max` 控制。[DeepSeek 思考模式](https://api-docs.deepseek.com/guides/thinking_mode) | 1M 上下文、最大 384K 输出；当前 API 模型表列出 JSON Output、工具调用和上下文缓存。[DeepSeek 模型与价格](https://api-docs.deepseek.com/quick_start/pricing) | 作为低成本、独立模型族核验对照；固定思考开关和 effort 后再比较。 |
| `deepseek-v4-flash` | 与 Pro 使用同一思考开关，官方定位差异主要体现在价格和并发；Flash 每 `user_id` 并发上限 2500，Pro 为 500。[DeepSeek 限流与隔离](https://api-docs.deepseek.com/quick_start/rate_limit) | 与 Pro 同为 1M 上下文和 384K 最大输出。[DeepSeek 模型与价格](https://api-docs.deepseek.com/quick_start/pricing) | 不进首轮质量短名单；可在 Pro 通过后做成本 / 延迟降档测试。 |

### 3.2 结构化 JSON 与发布安全

| 候选族 | 官方保证 | TS-02 处理方式 |
|---|---|---|
| OpenAI GPT-5.6 | 模型页明确列出 Structured Outputs。OpenAI 文档区分 Structured Outputs 与 JSON Mode：前者保证 Schema 遵循，后者只保证有效 JSON；严格 Schema 仍有受支持关键字和结构限制。[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) | 首选 `text.format` 的严格 JSON Schema；仍必须处理拒答、截断和内容过滤，并在本地再次校验。 |
| Qwen 3.7 Plus | `qwen3.7-plus` 能力表列出结构化输出支持；其接口是 `response_format={"type":"json_object"}` 的 JSON Mode，用于返回可解析 JSON，但官方没有在该接口上承诺任意业务 JSON Schema 的严格遵循，并提示部分模型在思考模式下可能返回非严格 JSON。[千问文本生成模型](https://help.aliyun.com/zh/model-studio/text-generation-model/) [千问结构化输出](https://help.aliyun.com/zh/model-studio/qwen-structured-output) | 分别预检思考 / 非思考模式，提示词给出完整 JSON 示例；本地 Schema 校验、原因码枚举校验和有限重试是发布前硬门槛。不要把“JSON Mode”写成“Schema 合法”。 |
| Qwen 3.7 Max | `qwen3.7-max` 能力表明确标记不支持结构化输出。[千问文本生成模型](https://help.aliyun.com/zh/model-studio/text-generation-model/) | 只在 Plus 推理失败时作为升级对照；普通文本响应必须经过独立解析、本地 Schema 校验，失败即机器可读拒绝发布。 |
| DeepSeek V4 | JSON Output 保证有效 JSON，但官方提示该功能可能偶尔返回空内容；直接 JSON Output 文档未承诺业务 Schema 遵循。[DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode) API 参考另提供 Beta 的 strict tool calls，声称可让工具参数遵守函数 JSON Schema。[Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion) | 首轮同时预检直接 JSON Output 与 strict tool call 两条输出路径；只采用实测 Schema 合法率更高且失败可识别的一条。任何空内容、截断或非法枚举都不得进入 `release_decision`。 |

结构化能力只降低格式错误，不证明事实正确。TS-02 仍须把教材解析、来源核验、边界检查、教学检查、迁移检查和最终发布裁决分开记录，不能让一次“严格 JSON”响应同时充当证据与裁判。

### 3.3 中文教育表达

官方资料不足以给任何候选一个“中文教育更准”的事实标签：

- OpenAI 将 Sol 描述为复杂专业工作的旗舰模型、Terra 描述为智能与成本平衡档，但其官方模型页没有给出中国中小学教育准确率。[Sol 模型页](https://developers.openai.com/api/docs/models/gpt-5.6-sol) [Terra 模型页](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
- 阿里云提供中文模型文档、境内地域和千问日期快照，但这些服务属性不是儿童中文讲解质量证据。[阿里云百炼模型目录](https://help.aliyun.com/zh/model-studio/models)
- DeepSeek 的 JSON Output 官方示例包含“解析考试文本”的提示，但示例只说明接口用法，不能作为数学 / 科学核验准确率。[DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode)

因此，中文教育表达应由盲评测量：事实不变性、学段术语、句长、前置知识假设、是否把“音调 / 响度”等近义概念混淆、能否用自然中文解释边界，以及在来源不足时是否明确保持 `unverified_generated`。评分者不得看到供应商名称，模型不得自评。

### 3.4 价格

以下均为 2026-07-28 官方按量原价；促销价、汇率、税费、缓存命中率和工具费用另算：

| 模型 | 输入 / 百万 Token | 输出 / 百万 Token | 备注 |
|---|---:|---:|---|
| `gpt-5.6-sol` | 5.00 美元 | 30.00 美元 | 超过 272K 输入时整次请求输入按 2 倍、输出按 1.5 倍计费。[OpenAI 价格页](https://developers.openai.com/api/docs/pricing) |
| `gpt-5.6-terra` | 2.50 美元 | 15.00 美元 | 同样适用超过 272K 的长上下文倍率。[OpenAI 价格页](https://developers.openai.com/api/docs/pricing) |
| `qwen3.7-max` | 12 元 | 36 元 | 0-1M 输入同档；官方页面另列限时折扣，选型预算采用原价。[那阿里云百炼模型价格](https://help.aliyun.com/zh/model-studio/model-pricing) |
| `qwen3.7-plus` | 2 元（<=256K）；6 元（256K-1M） | 8 元（<=256K）；24 元（256K-1M） | 思考与非思考输出原价相同；官方页面另列限时折扣，预算采用原价。[阿里云百炼模型价格](https://help.aliyun.com/zh/model-studio/model-pricing) |
| `deepseek-v4-pro` | 3 元（缓存未命中）；0.025 元（命中） | 6 元 | 官方注明价格可能调整，应保存评测日价格快照。[DeepSeek 模型与价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing) |
| `deepseek-v4-flash` | 1 元（缓存未命中）；0.02 元（命中） | 2 元 | 仅在 Pro 通过质量门槛后测试降档。[DeepSeek 模型与价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing) |

不能仅用单价选型。TS-02 应按“完整通过一个输入包”的实际费用比较，计入重试、独立核验、思考 Token、Schema 失败、空响应和长上下文倍率。

### 3.5 版本固定与可复现性

| 候选族 | 官方可固定能力 | 风险与记录要求 |
|---|---|---|
| OpenAI GPT-5.6 | 模型页当前只列 `gpt-5.6-sol`、`gpt-5.6-terra` 自身为 snapshot；`gpt-5.6` 是会路由到 Sol 的家族别名。[Sol 模型页](https://developers.openai.com/api/docs/models/gpt-5.6-sol) [Terra 模型页](https://developers.openai.com/api/docs/models/gpt-5.6-terra) | 不用 `gpt-5.6` 别名。官方页面未列日期化 5.6 snapshot，因此冻结能力弱于 Qwen 日期版本；必须保存请求 model、响应 model、配置、prompt / schema 哈希和运行日期。 |
| Qwen 3.7 | 官方价格页同时列别名与日期快照，例如 `qwen3.7-plus-2026-05-26`、`qwen3.7-max-2026-05-20` 和 `qwen3.7-max-2026-06-08`。[阿里云百炼模型价格](https://help.aliyun.com/zh/model-studio/model-pricing) | 首轮直接使用日期快照，不用 `qwen3.7-plus` / `qwen3.7-max` 别名；地域和协议也要固定。 |
| DeepSeek V4 | 当前模型 ID 是 `deepseek-v4-flash` 与 `deepseek-v4-pro`，官方模型页没有列出日期快照选择机制。[DeepSeek 模型与价格](https://api-docs.deepseek.com/quick_start/pricing) | 保存模型 ID、思考模式、effort、响应 model、prompt / schema 哈希和运行日期；若后续文档显示同一 ID 行为变化，整套基线重跑。 |

## 4. 境内服务、数据和合规考虑

### OpenAI

OpenAI API 数据默认不用于训练，除非客户主动选择分享；但默认 abuse monitoring 日志可能包含客户内容并保留最多 30 天，符合条件且获批的客户才可使用 Zero Data Retention 或 Modified Abuse Monitoring。[OpenAI 数据控制](https://developers.openai.com/api/docs/guides/your-data) OpenAI 的 regional processing 列表包含美国、欧洲和阿联酋，不包含中国大陆；GPT-5.6 可用于 Responses 的已列区域存储，但中国大陆没有官方列出的本地推理地域。[OpenAI 数据驻留](https://developers.openai.com/api/docs/guides/your-data#data-residency-controls) 中国大陆也不在 OpenAI API 支持国家 / 地区清单中；官方明确提示从清单外访问或向清单外提供访问可能导致账号被封禁或暂停。[OpenAI 支持国家与地区](https://developers.openai.com/api/docs/supported-countries)

因此，OpenAI 不是中国大陆直接调用候选。只有合法的调用主体与运行地域处于官方支持范围、供应商合同允许，并完成跨境与数据处理审查时，才把 Terra / Sol 用于合成或去标识化夹具的能力对照。真实儿童照片、声音、身份资料或未授权教材不得因模型效果更好就跨境发送。

### 阿里云百炼 / Qwen

官方模型目录提供华北 2（北京）API 入口，并为同一模型列出多个海外地域；地域和 API Key 是分开的调用配置。[阿里云百炼模型目录](https://help.aliyun.com/zh/model-studio/models) 这使境内技术切片可以明确固定北京地域，减少“实际调用到哪个地域”的歧义，但地域可选不等于已满足儿童个人信息、教材版权、算法备案或生成式 AI 服务义务。

百炼官方隐私说明称客户数据不会用于模型训练，传输数据采用 AES-256 加密；同页也明确百炼会依法存储模型与应用调用产生的数据，具体处理以服务协议为准。[百炼合规资质与隐私说明](https://help.aliyun.com/zh/model-studio/privacy-notice) 因此“不用于训练”不能替代留存期限、访问权限和删除机制核对。首轮只用合成夹具和受控页段；生产前仍需核对百炼合同、账号主体、日志访问、删除能力、子处理方和本项目面向公众时的法务义务。

### DeepSeek

官方文档公开的 OpenAI 兼容 Base URL 为 `https://api.deepseek.com`，并提供独立的 Anthropic 兼容入口。[DeepSeek 模型与价格](https://api-docs.deepseek.com/quick_start/pricing) 当前公开 API 文档没有像 OpenAI 数据控制页或阿里云地域目录那样列出可配置的数据驻留地域、默认内容保留期限或 ZDR 开关，因此 API 项目不能只根据 Base URL 推断具体数据处理条件。

DeepSeek 官方隐私政策称，境内运营收集和产生的个人信息存储于中国境内；同时称可能将收集的输入及对应输出用于模型训练和服务优化，用户可关闭“数据用于优化体验”退出。该政策还称产品主要面向成年人，未满 18 周岁应在监护人指导下使用，并称不会主动收集未满 14 周岁儿童个人信息。[DeepSeek 隐私政策](https://cdn.deepseek.com/policies/zh-CN/deepseek-privacy-policy.html) 这些条款与本项目小学用户直接相关：不能把个人端设置自动外推为企业 API 合同保证。

DeepSeek 也应先用合成 / 去标识化夹具；真实儿童或教材数据接入前，必须从 API 合同或供应商书面材料确认企业账户的训练退出是否生效、处理地域、保留、删除、访问控制、监护人路径和安全事件责任。

## 5. 首轮测试顺序与配置

### 5.1 模型顺序

1. `qwen3.7-plus-2026-05-26`：建立境内、日期快照、低成本基线。
2. `deepseek-v4-pro`：验证极低单价能否在相同事实、冲突和儿童中文门槛下保持质量，并形成第二个独立模型族候选。
3. `gpt-5.6-terra`：仅在支持国家 / 地区与合同前置条件满足后，用严格 Structured Outputs 检查格式失败是否显著下降，并提供跨模型族质量对照；前置条件不满足时记录为 `not_runnable`，不得通过代理或未授权转发规避地域限制。
4. 只有特定失败样例需要更强推理时，分别升级到 `qwen3.7-max-2026-06-08` 与 `gpt-5.6-sol`；升级测试重跑全部固定夹具和失败簇，不更换来源、业务 Schema 或评分规则。由于 Qwen Max 不支持结构化输出，允许只替换供应商输出适配层，并把解析失败计入该模型结果。
5. 只有 Pro 全部硬门槛通过后，再用 `deepseek-v4-flash` 做成本 / 延迟降档；Flash 不参与首轮“能力是否成立”的判断。

### 5.2 冻结配置

每个模型至少固定并保存：

- 供应商、地域、Base URL、API 协议、请求 model 和响应 model；
- 思考开关与 effort；不把不同推理预算混在一个模型结果中；
- system / user prompt 原文与 SHA-256；
- 输入页段、来源哈希、页码、证据摘录和 StageProfile；
- JSON Schema 版本、输出路径（Structured Outputs、JSON Mode 或 strict tool call）与本地校验器版本；
- 最大输出 Token、超时、重试次数和停止原因；
- 原始响应哈希、解析结果、原因码、延迟、输入 / 缓存 / 输出 / 思考 Token 与实付费用；
- 运行时间、厂商价格页访问日期和所有失败样例。

每个固定输入包建议先运行 5 次；若同一模型同一冻结配置发生路由分歧、关键事实分歧、Schema 失败或空响应，再把该失败簇扩到 20 次。重复次数是建议的首轮统计设计，不是厂商能力事实。

### 5.3 评分顺序

每次响应按以下顺序判定，前一项失败即不进入后续发布判断：

1. **传输与完成状态**：超时、限流、空响应、截断、拒答。
2. **语法与 Schema**：有效 JSON、必填字段、枚举、额外字段、原因码。
3. **来源忠实度**：每个关键结论必须能回到给定页码和证据摘录；不允许模型记忆补证据。
4. **路由硬门槛**：12/12 oracle 路由、无来源误标已核验为 0、阻断误发布为 0、未核验写正式结果为 0。
5. **独立学科审核**：事实、边界、计算、跨学段来源、危险 / 误导内容。
6. **盲评中文教学表达**：学段适配、术语、自然度、简洁度、是否擅自猜年级或教材。
7. **重复一致性、延迟和完整通过成本**：只在前述硬门槛通过后比较。

模型不能审核自己的最终得分。生成与来源核验至少使用独立请求和隔离上下文；在 OpenAI 调用前置条件满足时，交叉检查 Qwen 生成 / Terra 核验、Terra 生成 / Qwen 核验；否则使用 Qwen / DeepSeek 交叉检查，并以人工 oracle 为最终裁决。三模型多数票仍不能替代教材页证据或教师审核。

## 6. 决策门槛

任何候选出现以下情况即不能成为 TS-02 发布模型：

- 任一无来源关键结论被标记为 `verified_atom` 或 `temporary_verified`；
- 任一阻断夹具被发布；
- 任一 `unverified_generated` 写入正式迁移学习结果；
- 模型从措辞或难度猜测缺失学段；
- 结构化失败被静默修补成另一种业务含义；
- 同一冻结配置重复运行时关键事实或发布路由不稳定，且有限重试不能把失败变成机器可识别状态。

在所有硬门槛通过后，先选“完整通过成本最低且中文盲评不劣于其他候选”的模型作为生成基线，再保留一个不同供应商作为独立核验或故障切换候选。若三个平衡配置都未通过，结论应是 TS-02 真实模型验证失败或需要更强的检索 / 规则 / 人工审核，而不是自动提高推理预算直到演示成功。

## 7. 已确认与未确认

已确认：当前公开 API 型号、上下文上限、结构化输出类型、官方按量价格、Qwen 日期快照、OpenAI 数据控制和公开地域、阿里云地域入口、DeepSeek 当前公开模型 ID。

未确认：任何候选在本项目教材上的事实准确率、中文儿童讲解质量、重复一致性、真实延迟、真实成本、OCR / PDF 泛化、教师认可、学习效果，以及供应商合同层面的儿童数据与教材授权合规。这些必须由后续冻结配置实测和法务 / 隐私审查补齐。
