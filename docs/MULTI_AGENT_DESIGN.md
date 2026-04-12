# Multi-Agent 角色分工与协作边界

> XAR-57 | 版本: 2026-04-12 | 状态: 初版

---

## 1. 现有 Agent 清单

Voile 当前有 5 个 agent，均位于 `core/agents/`，独立运行、互不调用。

| Agent | 文件 | XAR | 输入 | 输出 | 调度 |
|-------|------|-----|------|------|------|
| TopicWorker | topic_worker.py | XAR-18 | messages 表中未标记的消息 | message_topics 表 + Obsidian topics/ | 轮询 5s |
| SentimentWorker | sentiment_worker.py | XAR-19 | messages 表中未标记的消息 | message_sentiments 表 | 轮询 10s |
| LinkArchiver | link_archiver.py | XAR-17 | Redis `voile:url_queue` | links 表 + Obsidian links/ | 轮询 1s |
| PersonaAgent | persona_agent.py | XAR-20 | messages + message_topics + message_sentiments | Obsidian personas/ | 轮询 24h |
| DecisionTracker | decision_tracker.py | XAR-21 | messages 表最近 7 天 | Obsidian decisions/ | 轮询 6h |

### 1.1 各 Agent 详细职责

**TopicWorker** -- 话题漂移检测
- 输入: `messages` 表中 `message_id` 不在 `message_topics` 中的行，按 channel 分组
- 处理: 用 sentence-transformers (bge-small-zh-v1.5) 或 TF-IDF fallback 生成 embedding，相邻消息 cosine < 0.5 判定为话题漂移
- 输出: 写 `message_topics` 表（topic_label, segment_start, similarity_score），新话题同时写 Obsidian `topics/{topic_label}.md`
- 依赖: DB 读写，可选 Obsidian vault 路径

**SentimentWorker** -- 情感分析
- 输入: `messages` 表中 `message_id` 不在 `message_sentiments` 中的行
- 处理: 三级 fallback -- Erlangshen-Roberta-110M > SnowNLP > 规则词表（30 正 / 30 负）
- 输出: 写 `message_sentiments` 表（label: positive/negative/neutral, score 0-1）
- 额外: `daily_report(channel_id, date)` 聚合接口

**LinkArchiver** -- 链接归档
- 输入: Redis 队列 `voile:url_queue`（由 Go gateway 推入）
- 处理: 调 Go archiver HTTP `/fetch` 获取元数据，fallback 直接 HTTP GET 抽取 `<title>`
- 输出: 写 `links` 表 + Obsidian `links/{slug}.md`

**PersonaAgent** -- 用户画像
- 输入: 指定 channel 内所有 user_id，最近 N 天消息 + 已有的 topic/sentiment 标注
- 处理: 统计 top_topics(频率前5)、sentiment_trend(众数)、active_hours(前3)、sample_quotes(最近3条)
- 输出: Obsidian `personas/{user_id}.md`
- 特点: 是唯一跨表聚合的 agent（读 messages + message_topics + message_sentiments）

**DecisionTracker** -- 决策追踪
- 输入: 指定 channel 最近 7 天消息
- 处理: 20 条滑动窗口，检测提议词 + 结论词共现 -> 提取决策段
- 输出: Obsidian `decisions/{date}-{slug}.md`


## 2. 角色定义（目标态）

现有 5 个 agent 可以映射到以下 4 种角色：

```
+-----------------------------------------------------------+
|  角色        | 现有 Agent           | 职责范围              |
|--------------|----------------------|-----------------------|
|  档案员      | LinkArchiver         | 抓取、存储、归档外部   |
|  (Archivist) | + ObsidianWriter     | 资源，写入持久化层     |
|              |                      |                       |
|  分析员      | TopicWorker          | 从消息流中抽取结构化   |
|  (Analyst)   | SentimentWorker      | 信号（话题、情感）     |
|              |                      |                       |
|  画像师      | PersonaAgent         | 聚合多维信号为用户     |
|  (Profiler)  |                      | 画像                   |
|              |                      |                       |
|  记录员      | DecisionTracker      | 识别决策过程，提取     |
|  (Recorder)  |                      | 结论并归档             |
+-----------------------------------------------------------+
```

### 未来可增加的角色

| 角色 | 触发条件 | 职责 |
|------|---------|------|
| 审校员 (Reviewer) | 当 Obsidian 产出需要人工确认时 | 对 agent 产出做质量把关，标记置信度低的结果 |
| 研究员 (Researcher) | 当链接归档需要深度摘要时 | 对 URL 内容做深度阅读、摘要、关键信息抽取 |
| 执行代理 (Executor) | 当需要触发外部动作时 | 发通知、调 API、触发编译管线 |

**判断原则**: 只在现有角色无法自然扩展时才引入新角色。一个 if 分支能解决的不开新 agent。


## 3. 权限与共享记忆

### 3.1 数据通道矩阵

```
               DB(SQLAlchemy)   Redis Queue   Obsidian Vault   gRPC(Kernel)
TopicWorker        R/W              -             W                -
SentimentWorker    R/W              -             -                -
LinkArchiver       R/W              R             W                -
PersonaAgent       R                -             W                -
DecisionTracker    R                -             W                -
```

### 3.2 共享记忆方式

当前所有 agent 的共享记忆 = **数据库**。这是正确的：

1. **DB 是唯一的事实源 (source of truth)**
   - `messages` 表: 所有 agent 的输入
   - `message_topics` / `message_sentiments`: 分析员的输出，画像师的输入
   - `links` 表: 档案员的输出

2. **Obsidian vault 是只写的落盘层**
   - Agent 只往 vault 写，不从 vault 读
   - Vault 是给人看的，不是给 agent 看的

3. **Redis 是单向队列**
   - Go gateway -> Redis -> LinkArchiver，单消费者
   - 不用做 agent 间通信

### 3.3 权限隔离原则

- 每个 agent 只写自己负责的表/目录
- 跨表读取可以，跨表写入禁止
- PersonaAgent 是唯一允许跨表读的（聚合角色）
- 如果未来需要 agent 间协调，通过 DB 状态表实现，不通过直接调用


## 4. 第一阶段：保持单 Agent 循环

当前架构 = 每个 agent 独立 `run_forever()` 循环。**这是对的，不要急着改。**

### 4.1 现阶段保持不变的理由

- 5 个 agent 之间没有实时依赖（PersonaAgent 读的是已落库的结果，延迟无所谓）
- 没有 agent 间的消息传递需求
- 没有需要多 agent 协商的决策
- 单 agent 循环 debug 简单，部署简单

### 4.2 留到后续协作阶段的特性

| 特性 | 触发条件 | 阶段 |
|------|---------|------|
| Agent 编排器 | 3+ agent 有执行顺序依赖 | Phase 3+ |
| 共享状态机 | 需要"话题分析完 -> 立即触发情感分析"的流水线 | Phase 3+ |
| 审校回环 | Obsidian 产出需要置信度过滤 | Phase 3+ |
| 冲突仲裁 | 两个 agent 对同一消息产出矛盾结论 | Phase 4+ |

### 4.3 从单循环到协作的渐进路径

```
Phase 1-2 (现在):  独立循环，DB 共享
                   TopicWorker ---+
                   SentimentWorker ---+--> DB <-- PersonaAgent
                   LinkArchiver ---+       ^
                   DecisionTracker --------+

Phase 3 (触发条件: 需要流水线):  事件驱动
                   消息入库 -> 发 DB event -> topic+sentiment 并行
                                           -> 完成后触发 persona 更新

Phase 4 (触发条件: 需要质量把关):  审校回环
                   agent 产出 -> reviewer 检查 -> 低置信度标记 -> 人工队列
```


## 5. 避免上下文割裂

### 5.1 统一 DB Schema

所有 agent 共享同一个 `core/storage/db.py` 定义的 ORM：

- `MessageRecord` -- 统一消息格式（平台无关）
- `MessageTopic` -- 话题标注（message_id 外键语义）
- `MessageSentiment` -- 情感标注
- `LinkRecord` -- 链接元数据

**规则**: 新增 agent 如果需要持久化，必须在 `db.py` 中加表，不能自建 SQLite。

### 5.2 统一消息格式

`core/schemas/message.py` 定义了 `Message` (Pydantic v2)，是所有平台适配器的输出契约。
下游 agent 永远只看 `MessageRecord`，不看 `raw_payload`。

### 5.3 防止割裂的具体措施

| 风险 | 防御 |
|------|------|
| Agent 各自维护 embedding 模型 | TopicWorker 用 bge-small-zh，其他 agent 需要 embedding 时复用同一模型 |
| Agent 各自定义消息过滤逻辑 | 统一用 `message_id NOT IN (已处理表)` 模式 |
| Obsidian 输出格式不一致 | 统一通过 `ObsidianWriter` 写入，不直接 open() |
| 时间处理不一致 | 统一 UTC，`created_at` 全部 timezone-aware |


## 6. 多 Agent 何时真正有产品价值

多 Agent 协作的前提是单 Agent 已经不够用。判断标准：

### 6.1 不需要多 Agent 协作的场景

- 话题分析 + 情感分析 = 两个独立管道，并行跑就行
- 链接归档 = 独立的 IO 密集任务
- 这些场景用 `asyncio.gather` 或多进程足矣

### 6.2 需要多 Agent 协作的场景

1. **跨信号聚合**: "最近一周讨论 X 话题时情感明显偏负面" -- 需要 TopicWorker + SentimentWorker 的结果联合查询
   - 现状: PersonaAgent 已经在做，但粒度粗
   - 触发条件: 用户需要按话题维度看情感趋势

2. **决策上下文增强**: DecisionTracker 检测到决策，需要把相关链接、涉及人物画像附上
   - 触发条件: 决策日志需要比"滑动窗口关键词匹配"更丰富的上下文

3. **审校闭环**: Agent 产出的 Obsidian 笔记需要人工确认后再标记为"已验证"
   - 触发条件: Obsidian vault 中低质量笔记太多，需要置信度过滤

**底线**: 在 Phase 2 结束之前，不引入 agent 编排层。先把每个 agent 做到独立可靠。


## 7. 边界清单

| 规则 | 说明 |
|------|------|
| Agent 不调用 Agent | 当前禁止 agent 间直接调用，通过 DB 间接协作 |
| Agent 不读 Obsidian | Obsidian 是 write-only sink，不是 agent 的输入源 |
| Agent 不调 LLM API | 当前所有分析用本地模型/规则，不调外部 LLM |
| 新 Agent 必须注册 ORM | 持久化必须通过 `core/storage/db.py`，不自建存储 |
| ObsidianWriter 是唯一出口 | 所有 vault 写入通过 `core/obsidian/writer.py` |
| 每个 Agent 一个 run_forever | 独立进程/线程，不共享事件循环 |
