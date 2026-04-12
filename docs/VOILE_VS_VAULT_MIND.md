# Voile 与 vault-mind 的关系与边界

> XAR-60 | 版本: 2026-04-12 | 状态: 初版

---

## 1. 一句话定位

- **Voile**: 聊天消息的"采集 + 分析 + 落盘"管线。从 QQ/微信抓消息，跑分析，写 Markdown。
- **vault-mind**: Obsidian vault 的"编译 + 查询"操作系统。读 Markdown，建知识图谱，暴露 MCP 接口。

两者的边界 = **Obsidian vault 目录中的 Markdown 文件**。

```
Voile 写 -->  [Obsidian vault]  <-- vault-mind 读
              (Markdown 文件)
```


## 2. 各自负责什么

### 2.1 Voile 负责

| 职责 | 具体实现 |
|------|---------|
| QQ/微信消息接入 | Go gateway (OneBot WS / WeFlow HTTP) |
| 消息归一化 | Pydantic Message schema |
| 消息持久化 | SQLAlchemy 2.0 -> SQLite/PostgreSQL |
| 话题漂移检测 | TopicWorker (embedding cosine similarity) |
| 情感分析 | SentimentWorker (transformers/snownlp/rules) |
| 链接抓取归档 | LinkArchiver (Go archiver + Redis queue) |
| 用户画像生成 | PersonaAgent (跨表聚合) |
| 决策过程提取 | DecisionTracker (关键词滑动窗口) |
| Markdown 落盘 | ObsidianWriter -> vault 文件系统 |
| 文本清洗 | Rust TextCleaner gRPC |
| 向量检索 | Rust VectorIndex gRPC (HNSW ANN) |

### 2.2 Voile 不负责

| 不做的事 | 由谁做 |
|---------|--------|
| 知识图谱构建 | vault-mind compiler |
| vault 搜索 / 查询接口 | vault-mind MCP |
| Markdown 之间的 cross-link | vault-mind link discovery |
| vault 健康度检查 | vault-mind /vault-health |
| 知识冲突解决 | vault-mind /vault-reconcile |
| Obsidian 插件 UI | obsidian-vault-bridge |

### 2.3 vault-mind 负责

| 职责 | 具体实现 |
|------|---------|
| MCP server (stdio) | @modelcontextprotocol/sdk |
| Adapter 体系 | filesystem / memU / GitNexus |
| 知识编译 | chunking + LLM embedding + link discovery |
| 统一查询 | vault_read / vault_write / vault_search / vault_graph |
| Vault 自愈 | lint / health / reconcile |
| Agent 调度 | agent scheduler (编译管线) |

### 2.4 vault-mind 不负责

| 不做的事 | 由谁做 |
|---------|--------|
| 消息采集 | Voile gateway |
| 消息分析 (话题/情感) | Voile agents |
| 往 vault 写原始归档 | Voile ObsidianWriter |
| 数据库存储 | Voile core.storage |
| 实时消息流处理 | Voile AstrBot plugin |


## 3. 前后衔接关系

```
  Voile (上游)                    vault-mind (下游)
  ============                    =================

  消息采集                        |
     |                            |
  消息分析                        |
     |                            |
  Markdown 落盘                   |
     |                            |
     +---- vault 目录 ------>  vault-mind 读取
                                  |
                               知识编译
                                  |
                               MCP 查询接口
                                  |
                               Agent / 人工使用
```

### 3.1 接口契约

Voile 和 vault-mind 之间没有 API 调用，没有 RPC，没有消息队列。

**唯一的接口 = 文件系统上的 Markdown 文件。**

Voile 的 `ObsidianWriter` 保证产出的文件格式：
- 有 YAML frontmatter（date, title, url, user_id 等）
- 有标准的目录结构（topics/, personas/, decisions/, links/）
- UTF-8 编码

vault-mind 的 compiler 消费这些文件时，按 frontmatter 分类、按目录路由。

### 3.2 不耦合的好处

- Voile 可以不装 vault-mind 也能跑（Obsidian 笔记直接看）
- vault-mind 可以不装 Voile 也能跑（手动写的笔记也编译）
- 两者可以独立发版、独立部署、独立测试


## 4. 完整链路

### 4.1 从消息到知识的全链路

```
+-------+     +----------+     +---------+     +----------+     +---------+
| 输入  | --> | 抽取     | --> | 落盘    | --> | 修正     | --> | 再利用  |
+-------+     +----------+     +---------+     +----------+     +---------+
  QQ群消息      归一化           Obsidian        人工编辑         vault-mind
  微信消息      Message          Markdown        补充标签         MCP 查询
  历史导入      schema           文件             纠正错误         知识图谱
                话题/情感                        添加关联         Agent 消费
                用户画像
                决策提取
                链接归档
```

### 4.2 各环节详细说明

**输入**
- 实时: NapCatQQ (OneBot v11 WS) / WeFlow (HTTP poll) -> Go gateway -> AstrBot plugin
- 批量: qq-chat-exporter JSON / WeChatMsg CSV/SQLite -> Python importers

**抽取**
- Message schema 归一化（platform, channel_id, user_id, content, created_at）
- TopicWorker: 相邻消息 embedding cosine < 0.5 = 话题漂移
- SentimentWorker: 三级 fallback (Erlangshen > SnowNLP > 规则词表)
- LinkArchiver: Go archiver 抓取 -> title/summary/tags
- PersonaAgent: 聚合 top_topics + sentiment_trend + active_hours
- DecisionTracker: 20 条滑动窗口检测提议词 + 结论词共现

**落盘**
- ObsidianWriter 写到 vault 的 4 个目录:
  - `topics/{topic_label}.md` -- 话题卡片
  - `personas/{user_id}.md` -- 用户画像
  - `decisions/{date}-{slug}.md` -- 决策记录
  - `links/{slug}.md` -- 链接档案

**人工修正**
- 在 Obsidian Desktop 中打开 vault
- 修正自动生成的话题标签
- 补充 persona 的描述
- 标记错误的决策提取
- 添加手动笔记和双向链接

**再利用**
- vault-mind compiler 增量编译修正后的 Markdown
- vault-mind MCP 暴露 vault_search / vault_graph
- Agent 通过 MCP 查询知识（如 Claude Code skill）
- 下一轮 Voile agent 可以参考已编译的知识（未来特性）


## 5. 是否需要第三个 ingest/pipeline 仓库

**当前结论: 不需要。**

### 5.1 现状分析

- 输入层代码（importers + AstrBot plugin）< 500 行，在 Voile 仓库内管理合理
- Go gateway 虽然是独立语言栈，但共享 proto 定义，放一起便于维护
- 两个仓库（voile + obsidian-llm-wiki）的职责已经清晰

### 5.2 触发条件

满足以下任意 2 条，启动拆分讨论：

| # | 条件 | 当前状态 |
|---|------|---------|
| 1 | 输入平台 > 3 个 | 2 个 (QQ/WeChat) |
| 2 | gateway 代码 > 5000 行 | ~2000 行 |
| 3 | 需要独立发布节奏 | 不需要 |
| 4 | 需要独立扩缩容 | 不需要 |
| 5 | 有专人负责 ingest | 没有 |
| 6 | ingest 层有独立的 CI/CD 需求 | 没有 |

### 5.3 如果拆，建议的切分方式

```
voile-ingest/          新仓库: 输入 + 协议适配
  gateway/             Go: QQ/WeChat/API/Archiver
  plugins/             AstrBot 插件
  importers/           历史导入脚本
  proto/               gRPC 接口定义

voile/                 保留: 分析 + 落盘
  core/                storage + agents + obsidian

obsidian-llm-wiki/     不变: 编译 + 查询
  vault-mind/          MCP server + compiler
```


## 6. 边界清单

| # | 事项 | 负责方 | 说明 |
|---|------|--------|------|
| 1 | QQ/微信消息接入 | Voile | Go gateway 负责所有平台协议 |
| 2 | 消息归一化 | Voile | Message Pydantic schema |
| 3 | 消息持久化 (DB) | Voile | SQLAlchemy ORM, SQLite/PG |
| 4 | 话题漂移检测 | Voile | TopicWorker |
| 5 | 情感分析 | Voile | SentimentWorker |
| 6 | 链接抓取 | Voile | Go archiver + LinkArchiver |
| 7 | 用户画像 | Voile | PersonaAgent |
| 8 | 决策提取 | Voile | DecisionTracker |
| 9 | Markdown 写入 vault | Voile | ObsidianWriter 直接写文件系统 |
| 10 | 文本清洗 (gRPC) | Voile | Rust TextCleaner |
| 11 | 向量检索 (gRPC) | Voile | Rust VectorIndex |
| 12 | Vault 知识编译 | vault-mind | Chunking + embedding + link discovery |
| 13 | Vault MCP 查询接口 | vault-mind | vault_read/write/search/graph |
| 14 | Vault 健康检查 | vault-mind | /vault-health, /vault-lint |
| 15 | 知识冲突解决 | vault-mind | /vault-reconcile |
| 16 | Obsidian 插件 UI | obsidian-vault-bridge | WebSocket + 双层安全门 |
| 17 | 人工修正/标注 | 人 | 在 Obsidian Desktop 中操作 |
| 18 | proto 定义维护 | Voile | kernel/proto/voile.proto 是单一事实源 |
| 19 | Redis 队列 | Voile | voile:url_queue 由 gateway 推入 |
| 20 | AstrBot 插件 | Voile | 实时消息 sink |


## 7. 数据流图

```
              +==========================================+
              |              输入源                       |
              |  NapCatQQ    WeFlow    历史导入(CSV/JSON) |
              +=====+===========+=============+==========+
                    |           |             |
                    v           v             v
              +-----+-----------+-------------+----------+
              |         Go Gateway / Importers            |
              |   QQ WS | WeChat HTTP | qq/wechat import |
              +-----+--------------------------------+---+
                    |                                |
                    v                                v
              +-----+------+              +---------+--------+
              | AstrBot    |              | Redis            |
              | Plugin     |              | voile:url_queue  |
              +-----+------+              +---------+--------+
                    |                                |
                    v                                v
              +-----+------+              +---------+--------+
              | messages   |              | LinkArchiver     |
              | 表 (DB)    |              | -> links 表      |
              +--+----+----+              | -> Obsidian      |
                 |    |                   |    links/        |
        +--------+    +--------+          +------------------+
        |                      |
        v                      v
  +-----+-------+    +--------+--------+
  | TopicWorker |    | SentimentWorker |
  | -> topics表 |    | -> sentiments表 |
  | -> Obsidian |    +--------+--------+
  |    topics/  |             |
  +-----+-------+            |
        |                     |
        +----------+----------+
                   |
                   v
        +----------+----------+     +------------------+
        | PersonaAgent        |     | DecisionTracker  |
        | -> Obsidian         |     | -> Obsidian      |
        |    personas/        |     |    decisions/     |
        +----------+----------+     +--------+---------+
                   |                         |
                   +------------+------------+
                                |
                                v
                   +------------+------------+
                   |    Obsidian Vault       |
                   |  (Markdown 文件系统)    |
                   +------------+------------+
                                |
               Voile 的职责到此为止
              ==========================================
               vault-mind 的职责从这里开始
                                |
                                v
                   +------------+------------+
                   |  vault-mind Compiler    |
                   |  chunk + embed + link   |
                   +------------+------------+
                                |
                                v
                   +------------+------------+
                   |  vault-mind MCP Server  |
                   |  vault_search/graph     |
                   +------------+------------+
                                |
                                v
                   +------------+------------+
                   |  Agent / 人工查询       |
                   +-------------------------+
```


## 8. 给非技术人员的解释

**问题**: 群聊每天产生大量有价值的信息 -- 讨论的话题、分享的链接、做出的决定、每个人的观点。但这些信息沉在聊天记录里，找不到、用不了。

**解决方案**: 两个系统配合工作 --

**Voile（速记员）**:
- 自动"监听"QQ群和微信群的消息
- 自动分析：这段在聊什么话题？情绪怎么样？谁分享了什么链接？做了什么决定？
- 把分析结果写成 Obsidian 笔记（话题卡片、用户画像、决策记录、链接档案）

**vault-mind（图书管理员）**:
- 接收 Voile 写好的笔记
- 建立索引，让笔记之间互相关联
- 提供搜索和查询接口 -- "上周关于 X 话题讨论了什么？" "谁经常谈论 Y？"

**人的角色**:
- 打开 Obsidian，看自动生成的笔记
- 修正不准确的地方（比如话题标签不对）
- 补充自己的理解和批注
- 通过 vault-mind 搜索历史知识

**一句话**: Voile 把聊天变成笔记，vault-mind 把笔记变成知识库。
