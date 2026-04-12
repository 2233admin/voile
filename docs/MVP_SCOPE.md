# MVP 范围与非目标

> Refs XAR-55

---

## MVP 定义

MVP 的目标：**用户能把 QQ/微信消息灌进来，系统自动清洗入库，链接自动归档，能按关键词和时间查到东西，能把结果落盘到 Obsidian vault。**

验收标准：一个真实用户（Curry）用自己的 QQ 群跑通全流程，从消息发送到 Obsidian 笔记生成，端到端 < 5 分钟。

---

## MVP 必须做

### 1. 消息入库

| 项目 | 说明 | 涉及层 | 验收标准 |
|------|------|--------|----------|
| QQ 实时消息接收 | NapCatQQ (OneBot v11) -> Go gateway -> DB | Go + Python | 群聊消息 < 3 秒入库 |
| 微信历史消息导入 | WeChatMsg CSV/JSON -> Python importer -> DB | Python | 10 万条消息 < 10 分钟导入完成 |
| 微信实时消息接收 | WeFlow HTTP API -> Go gateway -> DB | Go + Python | 消息 < 5 秒入库 |
| 统一消息 Schema | 所有来源的消息归一到 Pydantic schema | Python | schema 验证通过，字段覆盖：sender/content/timestamp/source/group |

### 2. 文本清洗

| 项目 | 说明 | 涉及层 | 验收标准 |
|------|------|--------|----------|
| 基础文本清洗 | 去重、去空白、normalize CJK 字符 | Rust kernel | 1 万条消息 < 1 秒处理完 |
| Emoji/特殊字符处理 | 保留文字含义，去除装饰性 emoji | Rust kernel | 清洗后文本可读，不丢失语义 |

### 3. 话题提取（基础版）

| 项目 | 说明 | 涉及层 | 验收标准 |
|------|------|--------|----------|
| 话题分段 | 将连续消息流按话题切分 | Python agent | 一个小时的群聊能识别出 3-10 个话题段落 |
| 话题标题生成 | 为每个话题段落生成简短标题 | Python agent | 标题准确反映讨论内容 |
| 话题标签 | 为话题打标签（技术/闲聊/决策/求助等） | Python agent | 分类准确率 > 80% |

### 4. 链接归档

| 项目 | 说明 | 涉及层 | 验收标准 |
|------|------|--------|----------|
| URL 提取 | 从消息内容中提取 URL | Go gateway | 支持 http/https，能处理短链接 |
| 网页正文抓取 | 抓取 URL 对应的网页正文 | Go gateway | 成功率 > 90%（排除需要登录的页面） |
| 链接去重 | 同一 URL 不重复抓取 | Go gateway | 去重逻辑正确 |
| 链接与消息关联 | 链接归档条目关联到发送该链接的原始消息 | Python | 关联关系可查询 |

### 5. 基础查询

| 项目 | 说明 | 涉及层 | 验收标准 |
|------|------|--------|----------|
| 按关键词搜索 | 全文搜索消息内容 | Python + Rust | 返回结果 < 500ms |
| 按时间范围查询 | 查询指定时间段的消息/话题 | Python | 支持日/周/月粒度 |
| 按群组筛选 | 按消息来源群组过滤 | Python | 支持多群组组合查询 |
| 按话题浏览 | 列出指定时间段的话题列表 | Python | 按时间倒序排列 |
| gRPC 查询接口 | 暴露查询能力给外部工具 | Rust + Python | proto 定义完整，接口可用 |

### 6. Obsidian 落盘

| 项目 | 说明 | 涉及层 | 验收标准 |
|------|------|--------|----------|
| 话题笔记生成 | 每个话题生成一篇 Obsidian 笔记 | Python | 笔记含标题、参与者、摘要、原始消息片段 |
| 链接归档笔记 | 每个归档链接生成一篇笔记 | Python | 笔记含标题、正文摘要、来源消息引用 |
| 双链生成 | 话题笔记之间、话题与链接之间自动生成 `[[双链]]` | Python | 链接关系在 Obsidian graph view 可见 |
| Frontmatter | 笔记含标准 frontmatter（date/tags/source/participants） | Python | Obsidian 可按 frontmatter 筛选 |

---

## MVP 明确不做

| 不做的事 | 原因 | 延后到 |
|----------|------|--------|
| 多 Agent 自治编排 | 过度工程，MVP 只需要线性管线 | Phase 3+ |
| 花哨的 Agent 演示 | 用户需要的是结果，不是看 Agent 在忙 | 永不 |
| 情感分析 Agent | 有价值但非核心路径，话题提取优先 | Phase 2 |
| 人物画像 Agent | 有价值但非核心路径 | Phase 2 |
| 决策追踪 Agent | 依赖话题提取和画像的基础能力 | Phase 2 |
| 向量语义搜索 | 关键词搜索够用，向量搜索是锦上添花 | Phase 2 |
| Telegram 接入 | QQ/微信覆盖核心用户，Telegram 可后加 | Phase 2 |
| 图片 OCR | 复杂度高，收益有限 | Phase 3+ |
| 企业合规/审计/权限 | 面向个人和小团队，不做企业功能 | 永不（除非转型） |
| 重型工作流引擎 | 简单的 Python 管线够用，不引入 Airflow/Prefect | 永不（除非规模到了） |
| Web UI | CLI + Obsidian 够用，不做前端 | Phase 3+ |
| 移动端 | 复杂度爆炸，收益有限 | 永不（短期内） |
| 多用户/多租户 | 本地优先架构，一台机器一个用户 | 永不（除非转型） |

---

## 阶段验收标准

### Phase 1 验收（MVP）

- [ ] QQ 消息从 NapCatQQ -> Go gateway -> Python core -> SQLite，延迟 < 3 秒
- [ ] 微信历史消息通过 importer 导入 10 万条 < 10 分钟
- [ ] 消息文本经过 Rust kernel 清洗
- [ ] 话题提取 agent 能将 1 小时群聊切分为 3-10 个话题
- [ ] 链接从消息中提取并抓取正文
- [ ] 按关键词/时间/群组查询消息，返回 < 500ms
- [ ] 话题和链接自动生成 Obsidian 笔记，含 frontmatter 和双链
- [ ] `pytest` / `go test` / `cargo test` 全绿
- [ ] Curry 用自己的 QQ 群跑通端到端流程

### Phase 2 验收（分析增强）

- [ ] 情感分析 agent 能标注消息情感倾向
- [ ] 人物画像 agent 能生成联系人卡片
- [ ] 决策追踪 agent 能识别群聊中的决策点
- [ ] 向量语义搜索可用
- [ ] Telegram adapter 接入

### Phase 3 验收（成熟化）

- [ ] CI/CD 管线完整
- [ ] Docker 一键部署
- [ ] 性能基准测试通过（10 万条消息全流程 < 1 小时）

---

## 可拆 Issue 的定义

每个 MVP 必做项可拆为独立 issue，拆分原则：

| 粒度 | 标准 |
|------|------|
| 一个 issue | 一个可独立测试的功能点 |
| 验收标准 | issue 关闭条件写在 description 里 |
| 层归属 | 标注涉及 Python/Go/Rust 中的哪一层 |
| 依赖关系 | 标注 `blocked by XAR-N`（如果有） |

### 建议拆分

```
# 消息入库
XAR-xx: QQ 实时消息接收（Go gateway -> Redis stream）
XAR-xx: 消息 Redis consumer（Python core -> DB write）
XAR-xx: 微信历史导入 importer（Python）
XAR-xx: 统一消息 Pydantic schema（Python）

# 文本清洗
XAR-xx: Rust text cleaner -- CJK normalize + dedup
XAR-xx: Python -> Rust cleaner 调用桥接

# 话题提取
XAR-xx: 话题分段算法（Python agent）
XAR-xx: 话题标题 + 标签生成（Python agent）

# 链接归档
XAR-xx: URL 提取 + 去重（Go）
XAR-xx: 网页正文抓取（Go）
XAR-xx: 链接-消息关联存储（Python）

# 查询
XAR-xx: 全文搜索接口（Python + Rust）
XAR-xx: 时间/群组筛选（Python）
XAR-xx: gRPC 查询 proto 定义

# Obsidian 落盘
XAR-xx: 话题笔记生成器（Python）
XAR-xx: 链接归档笔记生成器（Python）
XAR-xx: 双链 + frontmatter 生成（Python）
```
