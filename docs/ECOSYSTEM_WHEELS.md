# 生态轮子清单 (XAR-59)

Voile 所处生态的依赖参考清单。分层整理：直接用、结构参考、长期观察。

---

## 一、协议与连接层

| 项目 | GitHub | 用途 | 与 Voile 关系 |
|------|--------|------|--------------|
| MCP (Model Context Protocol) | [modelcontextprotocol/specification](https://github.com/modelcontextprotocol/specification) | LLM <-> 工具/资源的标准化双向协议 | **直接集成** — vault-mind 已是 MCP server，Voile 分析 agent 通过 MCP 读写 vault |
| A2A (Agent-to-Agent) | [google/A2A](https://github.com/google/A2A) | Google 提出的 agent 间通信协议，标准化任务委派/状态同步 | **长期观察** — Voile 当前单机无 agent 间通信需求；Phase 4+ 多 agent 编排时可接入 |

---

## 二、持久记忆层

| 项目 | GitHub | 用途 | 与 Voile 关系 |
|------|--------|------|--------------|
| GBrain | [google-deepmind/graphcast](https://github.com/google/generative-ai-docs) (待查) | 图结构长期记忆，节点=概念/关系=语义边 | **结构参考** — Voile 的 topic map 图结构可借鉴图遍历算法；不引依赖 |
| Letta (MemGPT) | [cpacker/MemGPT](https://github.com/cpacker/MemGPT) | 分层记忆管理：in-context / external storage / archival；agent 自主控制记忆进出 | **结构参考** — Voile 的 core/storage + obsidian writer 职责与 MemGPT 记忆层架构同构；不重复造分层逻辑，但实现自己的 |
| MemOS | [MemTensor/MemOS](https://github.com/MemTensor/MemOS) | 记忆操作系统：统一接口管理 agent 的多类型记忆（情景/语义/程序性） | **结构参考** — Phase 2 persona/decision tracking 设计时参考其记忆类型分类；不直接依赖 |
| Mem0 | [mem0ai/mem0](https://github.com/mem0ai/mem0) | 个人 AI 记忆层，自动提取/存储/检索用户偏好和历史 | **结构参考** — Voile 的 persona agent 做类似事情（从聊天消息提取人物画像）；不引依赖，Voile 走 Obsidian vault 不走独立向量库 |
| OpenMemory | [mem0ai/OpenMemory](https://github.com/mem0ai/OpenMemory) | Mem0 的本地优先开源版，MCP server 形态 | **可替换参考** — 若 Voile 未来需要暴露记忆 MCP 接口，可参考其接口设计；目前 vault-mind 已覆盖 |
| LLM Wiki (vault-mind) | [2233admin/obsidian-llm-wiki](https://github.com/2233admin/obsidian-llm-wiki) | Headless MCP server，Obsidian vault 编译/查询层 | **直接集成** — Voile 是 vault-mind 的上游生产者；分析结果通过 vault-mind MCP 写入 Obsidian |

---

## 三、多 Agent / 编排层

| 项目 | GitHub | 用途 | 与 Voile 关系 |
|------|--------|------|--------------|
| LangGraph | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 有状态 agent 工作流，图结构定义 agent 间控制流 | **结构参考** — Voile 的 Python agents（topic/sentiment/persona/decision）可用 LangGraph 节点模型管理状态；Phase 2 引入时评估直接借力 |
| Temporal | [temporalio/temporal](https://github.com/temporalio/temporal) | 工作流持久化引擎，长时任务重试/恢复/版本管理 | **结构参考** — Voile 的消息分析管道（摄取->分析->归档）是典型工作流；若管道复杂度上升，Phase 3 可评估引入 |
| Hermes Agent | [HKUDS/Hermes](https://github.com/HKUDS/Hermes) | 基于图的 agent 任务规划与记忆检索 | **长期观察** — 学术项目，工程成熟度待验证；Voile 图记忆方向的竞品参考 |
| AutoGen | [microsoft/autogen](https://github.com/microsoft/autogen) | 多 agent 对话框架，agent 间相互调用/协作 | **结构参考** — Voile 当前单 agent 为主，Phase 4 多 agent 协作时参考消息路由模式 |
| CrewAI | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | 角色化多 agent 框架，定义 crew/role/task/process | **长期观察** — 比 AutoGen 更高层抽象；Voile 轻量 agent 不需要这层；不引依赖 |
| OpenAI Agents SDK | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | OpenAI 官方 agent 框架，handoff/guardrails/tracing | **结构参考** — handoff 模式（agent 把任务移交给专门子 agent）对 Voile 的 topic/persona/decision agent 分工设计有参考价值 |
| Google ADK | [google/adk-python](https://github.com/google/adk-python) | Google Agent Development Kit，多 agent 协作标准工具链 | **长期观察** — 与 A2A 协议配套；Voile 当前不依赖 Google 栈 |

---

## 四、Obsidian 与本地生态层

| 项目 | GitHub | 用途 | 与 Voile 关系 |
|------|--------|------|--------------|
| Claudian | [github.com/claudian](https://github.com/search?q=claudian+obsidian) | Obsidian 插件，Claude 直接操作 vault | **竞品/参考** — Voile 走 vault-mind MCP 路线而非插件路线；关注其 vault 操作 API 设计 |
| Graphify / obsidian-knowledge-graph | [SkepticMystic/graph-analysis](https://github.com/SkepticMystic/graph-analysis) | Obsidian 知识图谱可视化/分析插件 | **直接借力** — Voile 写入 Obsidian 后可直接使用此类插件做图可视化，不需自建前端 |
| obsidian-memory-mcp | [cyanheads/obsidian-mcp-server](https://github.com/cyanheads/obsidian-mcp-server) | 把 Obsidian vault 暴露为 MCP 资源 | **替代参考** — vault-mind 已是这个定位；设计对比时参考其 MCP 工具命名约定 |
| obsidian-mcp-server | [MarkusPfundstein/mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian) | 另一个 Obsidian MCP server 实现，REST API 封装 | **替代参考** — 同上；vault-mind 走 stdio transport 更轻量 |
| QuickAdd | [chhoumann/quickadd](https://github.com/chhoumann/quickadd) | Obsidian 快速捕获/模板填充插件 | **直接借力** — Voile 归档结果写入 vault 后，用户可用 QuickAdd 做二次捕获；Voile 不需复制此功能 |
| Templater | [SilentVoid13/Templater](https://github.com/SilentVoid13/Templater) | Obsidian 高级模板引擎，动态模板/脚本 | **直接借力** — Voile 的 obsidian writer 产出 frontmatter 结构化笔记，Templater 可作为用户侧二次加工层 |
| Web Clipper | [obsidianmd/obsidian-clipper](https://github.com/obsidianmd/obsidian-clipper) | 浏览器剪藏插件，保存网页到 Obsidian | **上游数据源** — Voile 的 link fetcher（gateway/）与 Web Clipper 功能重叠；Web Clipper 侧重手动，Voile 侧重自动从消息中提取链接 |

---

## 五、不该重复造的能力

| 能力 | 现有轮子 | 理由 |
|------|---------|------|
| Obsidian vault CRUD | vault-mind (已集成) / obsidian-mcp-server | 文件系统操作 + frontmatter 解析已有成熟实现 |
| 知识图谱可视化 | Graphify / Obsidian 原生图谱 | 可视化是 Obsidian 生态强项，Voile 只管写数据 |
| 向量检索基础设施 | mem0 / OpenMemory | Voile 如需语义检索，直接调 vault-mind 的 memU 适配器 |
| Agent 框架脚手架 | LangGraph / OpenAI Agents SDK | Voile agents 当前轻量，不需重新造 DAG/状态机 |
| 消息平台适配器 | NapCatQQ / AstrBot / WeFlow | 已在 README 中明确，不碰 |

---

## 六、Voile 必须自己做深的壁垒

| 能力 | 原因 |
|------|------|
| **消息语义分析（topic/sentiment/persona/decision）** | 这是 Voile 的核心价值；通用 NLP 工具不理解中文聊天语境和关系网络 |
| **跨消息关联与知识编译** | 把散碎 QQ/微信消息升级为结构化长期记忆，是 Voile 独有 pipeline |
| **Obsidian 写入格式规范** | frontmatter schema + 笔记模板定义了 vault 的知识组织方式，外部工具无法替代 |
| **Go gateway 的消息规范化** | 统一 OneBot v11 + WeChat 两套异构格式，是 Voile 的数据地基 |
| **Rust kernel 的文本清洗 + ANN** | 中文消息的噪声（表情包/撤回/引用）处理需要定制逻辑 |
