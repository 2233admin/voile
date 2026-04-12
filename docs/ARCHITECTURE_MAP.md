# 仓库职责与产品架构映射

> XAR-58 | 版本: 2026-04-12 | 状态: 初版

---

## 1. 仓库职责拆分

| 维度 | voile | obsidian-llm-wiki (vault-mind) |
|------|-------|-------------------------------|
| 定位 | 聊天消息分析 + 知识归档系统 | Obsidian Vault 知识操作系统 |
| 输入 | QQ/微信消息流 | Obsidian vault 中的 Markdown 文件 |
| 输出 | 结构化 DB + Obsidian Markdown | 编译后的知识图谱 + MCP 查询接口 |
| 运行时 | 长驻服务（多进程） | MCP server (stdio) / Obsidian 插件 |
| 语言 | Python + Go + Rust | TypeScript + Python |
| 关系 | **上游**: 产出 Markdown 到 vault | **下游**: 消费 vault 中的 Markdown |

两者的边界 = **Obsidian vault 目录**。Voile 写文件到 vault，vault-mind 读文件并编译。


## 2. 产品五层架构

```
+================================================================+
|                     产品架构 (五层)                              |
+================================================================+
|                                                                 |
|  [输入层]  NapCatQQ / WeFlow / WeChatMsg / 手动导入              |
|     |      QQ OneBot WebSocket / 微信 HTTP / CSV / SQLite        |
|     v                                                           |
|  [处理层]  Go gateway (协议适配 + 链接抓取)                      |
|     |      Rust kernel (文本清洗 gRPC:50051 + ANN gRPC:50052)    |
|     v                                                           |
|  [记忆层]  Python core (SQLAlchemy 2.0)                          |
|     |      messages / message_topics / message_sentiments / links|
|     |      SQLite (dev) / PostgreSQL (prod)                      |
|     v                                                           |
|  [落盘层]  Python agents -> ObsidianWriter -> Obsidian vault     |
|     |      topics/ personas/ decisions/ links/                   |
|     v                                                           |
|  [操作层]  vault-mind MCP (编译/查询/图谱)                       |
|            人工在 Obsidian 中阅读、修正、补充                     |
|                                                                 |
+================================================================+
```

### 2.1 输入层

负责从不同平台获取原始消息。

| 来源 | 协议 | 入口 | 说明 |
|------|------|------|------|
| QQ 群聊 | OneBot v11 WebSocket | Go `cmd/qq/` | NapCatQQ 适配器推送事件 |
| 微信 | HTTP 轮询 | Go `cmd/wechat/` | WeFlow API |
| QQ 历史 | JSON 文件导入 | Python `importers/qq_import.py` | qq-chat-exporter 导出格式 |
| 微信历史 | CSV / SQLite | Python `importers/wechat_import.py` | WeChatMsg 导出格式 |

所有来源最终产出统一的 `Message` (Pydantic v2) 对象。

### 2.2 处理层

协议适配和底层文本处理。

- **Go gateway** (`gateway/`): 4 个独立二进制
  - `cmd/qq/` -- QQ WebSocket 接入
  - `cmd/wechat/` -- 微信同步
  - `cmd/archiver/` -- 链接抓取服务 (HTTP :8888)
  - `cmd/api/` -- 统一 REST API (:8080)

- **Rust kernel** (`kernel/`): 2 个 gRPC 服务
  - `TextCleaner` (:50051) -- 中文文本清洗、分句、URL 抽取
  - `VectorIndex` (:50052) -- HNSW ANN 向量检索 (Insert/Search/Delete)

### 2.3 记忆层

Python `core/storage/db.py` -- SQLAlchemy 2.0 Mapped[] ORM。

| 表 | 写入者 | 读取者 |
|----|--------|--------|
| messages | importers / AstrBot plugin | 所有 agent |
| message_topics | TopicWorker | PersonaAgent |
| message_sentiments | SentimentWorker | PersonaAgent |
| links | LinkArchiver | (未来查询接口) |

### 2.4 落盘层

Python `core/obsidian/writer.py` -- `ObsidianWriter` 类，4 个写入方法：

| 方法 | 输出目录 | 调用者 |
|------|---------|--------|
| write_link() | links/ | LinkArchiver |
| write_topic_card() | topics/ | TopicWorker |
| write_persona() | personas/ | PersonaAgent |
| write_decision() | decisions/ | DecisionTracker |

写入方式 = 直接文件系统操作 (`Path.write_text()`)，不通过 vault-mind MCP。

### 2.5 操作层

- vault-mind MCP server 提供 `vault_read/vault_write/vault_search/vault_graph`
- 人工在 Obsidian Desktop 中阅读、修正、标注
- vault-mind compiler 对 vault 做 chunk、embed、cross-link


## 3. 完整数据流

### 3.1 实时消息流

```
NapCatQQ (QQ群)                WeFlow (微信)
     |                              |
     v                              v
Go: cmd/qq          Go: cmd/wechat
(OneBot WS)         (HTTP poll)
     |                              |
     +-------> Go: cmd/api <--------+
               (REST :8080)
                    |
                    v
           AstrBot Plugin
           (消息事件 sink)
                    |
      +-------------+-------------+
      |                           |
      v                           v
  core.storage.upsert()     Redis voile:url_queue
  (-> messages 表)               |
      |                           v
      v                      LinkArchiver
  TopicWorker               (-> links 表)
  SentimentWorker           (-> Obsidian links/)
  (-> message_topics 表)
  (-> message_sentiments 表)
      |
      v
  PersonaAgent              DecisionTracker
  (聚合 topics+sentiments)  (滑动窗口检测)
  (-> Obsidian personas/)   (-> Obsidian decisions/)
      |
      v
  Obsidian vault (文件系统)
      |
      v
  vault-mind MCP (编译/查询)
```

### 3.2 历史导入流

```
qq-chat-exporter JSON    WeChatMsg CSV/SQLite
         |                       |
         v                       v
  importers/qq_import.py   importers/wechat_import.py
         |                       |
         +-------> Message ------+
                     |
                     v
              core.storage.upsert()
              (-> messages 表)
                     |
              (后续与实时流相同)
```

### 3.3 单条消息的完整生命周期

```
1. 输入    QQ群消息 -> OneBot WS -> Go gateway -> REST API
2. 抽取    AstrBot plugin 解析 -> Message(Pydantic) 归一化
3. 存储    core.storage.upsert() -> messages 表 (去重 by message_id)
4. 分析    TopicWorker: 话题标注 -> message_topics
           SentimentWorker: 情感标注 -> message_sentiments
           LinkArchiver: URL 元数据 -> links
5. 聚合    PersonaAgent: 用户画像 -> Obsidian personas/
           DecisionTracker: 决策提取 -> Obsidian decisions/
6. 落盘    ObsidianWriter -> vault 目录 (topics/personas/decisions/links/)
7. 编译    vault-mind compiler -> 知识图谱 (异步, vault-mind 仓库职责)
8. 查询    vault-mind MCP -> vault_search / vault_graph
9. 修正    人工在 Obsidian 编辑 -> vault-mind 增量编译
```


## 4. 技术栈分工

```
+-------------------+--------------------+-------------------+
|   Go (gateway/)   |  Python (core/)    |  Rust (kernel/)   |
+-------------------+--------------------+-------------------+
| 协议适配          | 业务逻辑           | 性能敏感计算       |
| WebSocket 接入    | Schema 定义        | 文本清洗           |
| HTTP 轮询         | ORM / 存储         | ANN 向量检索       |
| 链接抓取          | Agent 分析循环     |                   |
| REST API 网关     | Obsidian 写入      |                   |
| 高并发 IO         | LLM/NLP 调用       | 批量并行处理       |
+-------------------+--------------------+-------------------+
```

选型理由：
- Go: WebSocket/HTTP 高并发，编译为单二进制易部署
- Python: NLP 生态（transformers/sklearn/pydantic），开发速度
- Rust: 文本清洗和 ANN 对延迟敏感，Rust 保证内存安全 + 零拷贝


## 5. 是否拆出第三个 ingest/pipeline 仓库

**当前结论: 不拆。**

### 5.1 不拆的理由

- 输入层（importers + AstrBot plugin）代码量小（< 200 行/文件）
- 处理层（Go gateway）已经是独立二进制，但共享 proto 定义
- 拆仓库会增加 proto 同步成本、CI 复杂度、部署编排

### 5.2 触发拆分的条件（满足任意 2 条即启动拆分讨论）

| 条件 | 指标 |
|------|------|
| 平台数 > 3 | 当前 2 个 (QQ/WeChat)，增加 Discord/Telegram/Slack 等 |
| gateway 代码 > 5000 行 | 当前约 2000 行 |
| 需要独立发布节奏 | gateway 需要比 core 更频繁地发版 |
| 需要独立扩缩容 | gateway 需要水平扩展而 core 不需要 |
| 团队分工 | 有专人负责 ingest 层 |

### 5.3 如果拆，怎么拆

```
voile-ingest/          <-- 新仓库
  gateway/             <-- 现在的 Go gateway
  plugins/             <-- AstrBot 插件
  importers/           <-- Python 历史导入
  proto/               <-- gRPC 接口定义 (单一事实源)

voile/                 <-- 保留
  core/                <-- storage + agents + obsidian
  kernel/              <-- Rust 性能层

obsidian-llm-wiki/     <-- 不变
  vault-mind/          <-- MCP + compiler
```


## 6. 面向产品视角的架构解释

Voile 解决的问题: **群聊消息是最大的知识浪费**。

每天群里讨论了什么、谁说了什么、做了什么决定、分享了什么链接 -- 这些信息在聊天记录里沉没。Voile 把它们捞出来，变成结构化的知识。

产品流程（用人话说）:

1. **接入**: 群聊消息自动流入系统（QQ/微信都支持）
2. **理解**: 系统自动识别话题变化、分析情感倾向、抓取分享的链接
3. **归档**: 自动生成 Obsidian 笔记 -- 话题卡片、用户画像、决策记录、链接档案
4. **利用**: 在 Obsidian 中阅读、搜索、修正；通过 vault-mind 做知识图谱查询

**类比**: Voile 是群聊的"速记员 + 图书管理员"，vault-mind 是"图书馆的索引系统"。

Voile 负责"听到什么、记下来"；vault-mind 负责"记下来的东西怎么查、怎么关联"。
