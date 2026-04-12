# GitHub 轮子优先级与接入策略 (XAR-66)

当前状态：Phase 1（消息摄取 + 存储基础）进行中，Phase 2-3 待开始。
策略维度：直接借力 / 结构参考 / 长期观察。

---

## 第一优先级 — 直接影响主结构

> 现在就要想清楚如何接入或规避，否则 Phase 2 会返工。

| 项目 | GitHub | 用途 | 策略 | 当前建议 |
|------|--------|------|------|---------|
| LangGraph | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 有状态 agent 工作流图，节点=agent，边=控制流，内置 checkpointing | **直接借力** | Phase 2 引入分析 pipeline 时，用 LangGraph 管理 topic/persona/decision agent 的执行顺序与状态；避免手写 DAG |
| Temporal | [temporalio/temporal](https://github.com/temporalio/temporal) | 持久化工作流引擎，长时任务重试/回放/版本管理 | **结构参考** | Phase 2 先用简单队列（Redis + 自有调度）；若消息分析管道出现持久化/重试需求，Phase 3 再评估引入；不提前引入 |
| Letta (MemGPT) | [cpacker/MemGPT](https://github.com/cpacker/MemGPT) | 分层记忆（in-context / external / archival），agent 自主控制记忆进出 | **结构参考** | Phase 2 设计 persona/decision agent 时，对照 Letta 的记忆类型分层（情景记忆/语义记忆/程序性记忆）做 Obsidian 笔记分类；不引依赖，自实现 |
| MemOS | [MemTensor/MemOS](https://github.com/MemTensor/MemOS) | 统一记忆操作系统接口，管理多类型 agent 记忆 | **结构参考** | Phase 2 obsidian writer 的笔记类型设计（topic-map / persona-profile / decision-log / link-archive）对标 MemOS 记忆分类；不引依赖 |
| OpenMemory | [mem0ai/OpenMemory](https://github.com/mem0ai/OpenMemory) | 本地优先记忆 MCP server，向 LLM 暴露持久记忆 | **接口参考** | vault-mind 已是同等定位；对比 OpenMemory 的 MCP 工具命名（`search_memory`/`add_memory`）优化 vault-mind 接口语义；不替换 |

---

## 第二优先级 — Obsidian / 本地生态

> Phase 2 开始写 obsidian writer 时必须确认兼容性，避免格式冲突。

| 项目 | GitHub | 用途 | 策略 | 当前建议 |
|------|--------|------|------|---------|
| Claudian | [obsidian-claudian](https://github.com/search?q=claudian+obsidian) | Obsidian 插件，Claude 直接操作 vault | **竞品观察** | 关注其 vault 操作 API 设计；Voile 走 vault-mind MCP 路线不走插件路线，架构不冲突但定位重叠 |
| obsidian-memory-mcp | [cyanheads/obsidian-mcp-server](https://github.com/cyanheads/obsidian-mcp-server) | 把 Obsidian vault 暴露为 MCP 资源 | **接口参考** | 对比 vault-mind；重点看其 frontmatter 读写约定，确保 Voile 输出格式与社区约定兼容 |
| obsidian-mcp-server | [MarkusPfundstein/mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian) | 另一个 Obsidian MCP 实现，REST API 封装 | **接口参考** | 同上；两个实现对比能看出 Obsidian MCP 的事实标准是什么 |
| QuickAdd | [chhoumann/quickadd](https://github.com/chhoumann/quickadd) | Obsidian 快速捕获/模板填充 | **直接借力** | Voile 输出的结构化笔记让 QuickAdd 的 macro 能直接触发二次处理；obsidian writer 的 frontmatter schema 要与 QuickAdd macro 变量名约定兼容 |
| Templater | [SilentVoid13/Templater](https://github.com/SilentVoid13/Templater) | Obsidian 高级模板引擎 | **直接借力** | Phase 2 obsidian writer 产出笔记时，预留 Templater 变量位（`<% tp.date.now() %>` 等）；不自建模板引擎 |
| knowledge-graph (Graphify) | [SkepticMystic/graph-analysis](https://github.com/SkepticMystic/graph-analysis) | Obsidian 知识图谱分析/可视化 | **直接借力** | Voile 的 topic map 用双链（`[[概念]]`）格式写入 Obsidian，图谱插件自动可视化；不建前端 |

---

## 第三优先级 — 多 Agent 抽象参考

> 不需要现在引入，Phase 3+ 扩展时参考架构模式。

| 项目 | GitHub | 用途 | 策略 | 当前建议 |
|------|--------|------|------|---------|
| AutoGen | [microsoft/autogen](https://github.com/microsoft/autogen) | 多 agent 对话框架，agent 间相互调用/协作 | **结构参考** | Phase 3 多 agent 协作设计时，参考 AutoGen 的消息路由和 human-in-the-loop 模式；不直接引入（太重） |
| CrewAI | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | 角色化多 agent 框架（crew/role/task） | **长期观察** | 高层抽象适合明确角色分工的场景；Voile 当前 agent 职责已清晰（topic/persona/decision），不需额外框架层 |
| OpenAI Agents SDK | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | 官方 agent 框架，handoff/guardrails/tracing | **结构参考** | handoff 模式（消息先过 topic agent，再移交 persona agent）对 Voile pipeline 设计有参考价值；tracing 模块可参考调试链路设计 |
| Google ADK | [google/adk-python](https://github.com/google/adk-python) | Google Agent Development Kit | **长期观察** | 与 A2A 协议配套；Voile 不在 Google 栈，暂不考虑；若未来有跨系统 agent 通信需求再评估 |
| A2A Protocol | [google/A2A](https://github.com/google/A2A) | Agent 间标准化通信协议（任务委派/状态同步） | **长期观察** | 当前 Voile 单机 pipeline 无跨 agent 通信；Phase 4+ 若引入外部 agent 协作再接入 |

---

## 第四优先级 — 长期观察

> 不影响当前三个 phase，定期 check 生态动向即可。

| 项目 | GitHub | 用途 | 观察点 |
|------|--------|------|-------|
| GBrain | (待确认仓库) | 图结构长期记忆 | 图记忆方向竞品；关注其图遍历算法是否可移植到 Voile topic map |
| Hermes Agent | [HKUDS/Hermes](https://github.com/HKUDS/Hermes) | 图 agent 任务规划 + 记忆检索 | 学术项目，工程成熟度低；待论文复现验证后再评估 |
| DeerFlow | [bytedance/DeerFlow](https://github.com/bytedance/DeerFlow) | 字节 Deep Research agent 框架 | 研究型 agent 设计模式参考；与 Voile 定位（消息归档）不直接重叠 |
| Vibe Kanban | (待查) | AI 驱动看板工具 | 与 Voile 产品方向无直接关联；作为 AI native 产品 UX 参考观察 |
| TradingAgents-CN | [TradingAgents-CN](https://github.com/TauricResearch/TradingAgents) | 中文量化交易多 agent 框架 | 与 Voile 无关联；如需整合量化数据到 vault，届时参考其数据接口 |

---

## 不该重复造的轮子（执行层面）

| 能力 | 现有方案 | Voile 的正确做法 |
|------|---------|----------------|
| Obsidian vault 读写 | vault-mind MCP (已集成) | obsidian writer 直接调 vault-mind MCP 工具，不绕开 |
| 向量语义检索 | vault-mind 的 memU 适配器 | Phase 2 如需语义搜索，通过 vault-mind MCP 调；不自建向量库 |
| agent 工作流状态管理 | LangGraph | Phase 2 直接用，不手写 DAG 调度器 |
| Obsidian 图谱可视化 | graph-analysis 等插件 | 双链格式写入即可，不建前端可视化 |
| 消息平台适配 | NapCatQQ / AstrBot / WeFlow | 已锁定，不碰 |

---

## Voile 必须自己做深的壁垒

| 能力 | 为什么不能外包 |
|------|--------------|
| **中文聊天消息语义分析** | 通用 NLP 工具不理解 QQ/微信语境（表情包语义、群聊上下文、中文网络用语） |
| **跨消息知识编译 pipeline** | 从散碎消息 -> 结构化知识条目是 Voile 的核心差异化，无现成工具覆盖 |
| **Obsidian frontmatter schema 设计** | topic-map / persona-profile / decision-log 的 schema 决定 vault 的可查询性，必须自己定义 |
| **Go gateway 消息规范化层** | 统一 OneBot v11 + WeChat 两套异构协议是基础设施，无通用轮子 |
| **Rust 文本清洗（TextCleaner）** | 中文聊天噪声（撤回消息/引用嵌套/at 标记/表情 ID）的处理逻辑高度定制 |

---

## Phase 1-3 实际接入时间线建议

| Phase | 当前状态 | 应接入的轮子 | 暂缓的轮子 |
|-------|---------|------------|----------|
| Phase 1（进行中）| 消息摄取 + 存储 | vault-mind MCP（已有）、NapCatQQ/AstrBot（已有） | 全部 agent 框架 |
| Phase 2（下一步）| 分析 + 归档 pipeline | **LangGraph**（agent 编排）、QuickAdd/Templater 格式兼容性确认 | Temporal、AutoGen、CrewAI |
| Phase 3（计划中）| Persona、decision tracking、CI/CD | **结构参考** MemOS/Letta 记忆分类、OpenAI Agents SDK tracing 调试 | A2A、GBrain、Hermes |
| Phase 4+（未规划）| 多 agent 协作 / 跨系统 | AutoGen、Temporal、A2A | — |
