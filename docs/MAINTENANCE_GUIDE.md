# Voile 系统维护指南

> 本文档面向使用 Claude Code 的开发者，帮助你快速理解和维护 Voile 消息分析系统

## 📋 目录

1. [系统概览](#系统概览)
2. [架构设计](#架构设计)
3. [消息收集管道](#消息收集管道)
4. [历史消息导入](#历史消息导入)
5. [数据处理流程](#数据处理流程)
6. [常见维护任务](#常见维护任务)
7. [故障排查](#故障排查)
8. [改进建议](#改进建议)

## 系统概览

### 核心功能
Voile 是一个聊天消息分析和知识归档系统，主要功能：
- 📥 **消息收集**：实时收集 QQ/微信消息
- 📚 **历史导入**：解密并导入本地数据库的历史消息
- 🔍 **智能分析**：主题提取、情感分析、人物画像
- 📝 **知识归档**：结构化存储到 Obsidian 知识库

### 技术栈
- **Python 3.11+**: 核心业务逻辑、数据处理
- **Go 1.22+**: API 网关、消息路由
- **Rust**: 文本清洗、向量检索（gRPC）
- **PostgreSQL**: 主数据库
- **Redis**: 缓存和消息队列
- **Docker Compose**: 服务编排

### 部署位置
- **生产环境**: NAS (192.168.50.130)
- **开发环境**: 本地 Docker
- **代码仓库**: 
  - GitHub: https://github.com/2233admin/voile (公开)
  - Gitea: http://192.168.50.130:3000/xartpro/voile (内部)

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      消息来源层                              │
├─────────────────────────────────────────────────────────────┤
│  实时收集:                    历史导入:                      │
│  • NapCatQQ (OneBot v11)     • QQ nt_msg.db (加密)          │
│  • WeFlow (HTTP API)         • WeChat 数据库 (加密)         │
└─────────────────┬───────────────────────┬───────────────────┘
                  │                       │
                  v                       v
┌─────────────────────────────────────────────────────────────┐
│                      接入层                                  │
├─────────────────────────────────────────────────────────────┤
│  • Go API Gateway (:8080)                                   │
│  • QQ Gateway (OneBot → 统一格式)                           │
│  • WeChat Sync (WeFlow → 统一格式)                          │
│  • 解密脚本 (decrypt_qq_db.py, decrypt_wechat_db.py)       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              v
┌─────────────────────────────────────────────────────────────┐
│                      消息处理层                              │
├─────────────────────────────────────────────────────────────┤
│  • AstrBot Plugin (消息接收器)                              │
│  • core.storage (SQLAlchemy ORM)                           │
│  • 统一 Schema 转换                                         │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              v
┌─────────────────────────────────────────────────────────────┐
│                      存储层                                  │
├─────────────────────────────────────────────────────────────┤
│  • PostgreSQL (raw_messages 表)                            │
│  • Redis (缓存、队列)                                       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              v
┌─────────────────────────────────────────────────────────────┐
│                      分析层                                  │
├─────────────────────────────────────────────────────────────┤
│  Python Agents:              Rust Kernel (gRPC):            │
│  • 主题提取                  • TextCleaner (:50051)         │
│  • 情感分析                  • VectorIndex (:50052)         │
│  • 人物画像                                                 │
│  • 决策日志                                                 │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              v
┌─────────────────────────────────────────────────────────────┐
│                      输出层                                  │
├─────────────────────────────────────────────────────────────┤
│  • Obsidian Vault (Markdown 知识库)                        │
│  • 主题地图、人物档案、决策记录、链接归档                    │
└─────────────────────────────────────────────────────────────┘
```

### 数据流向

```
消息源 → 接入层 → 标准化 → 存储 → 分析 → 归档
  ↓        ↓        ↓       ↓      ↓      ↓
实时/历史  格式转换  Schema  PG    AI处理  Obsidian
```

## 消息收集管道

### 1. QQ 实时消息收集

**组件**: NapCatQQ + Go QQ Gateway + AstrBot

**流程**:
```
QQ客户端 → NapCatQQ (OneBot v11) → Go Gateway (:8080) → AstrBot Plugin → PostgreSQL
```

**配置文件**:
- `lagrange/appsettings.json` - QQ 账号配置
- `gateway/config.yaml` - 网关配置
- `plugins/astrbot_plugin_voile/` - AstrBot 插件

**启动命令**:
```bash
docker compose --profile qq up -d
```

**数据格式** (OneBot v11):
```json
{
  "post_type": "message",
  "message_type": "group",
  "group_id": 123456,
  "user_id": 789012,
  "message": "消息内容",
  "time": 1713417600
}
```

### 2. 微信实时消息收集

**组件**: WeFlow + Go WeChat Sync + AstrBot

**流程**:
```
微信客户端 → WeFlow (HTTP API) → Go WeChat Sync → AstrBot Plugin → PostgreSQL
```

**配置文件**:
- `gateway/wechat_config.yaml` - WeFlow 连接配置
- `.env` - WeFlow API 地址和凭证

**WeFlow 部署**:
```bash
# WeFlow 运行在独立容器
docker run -d \
  --name weflow \
  -p 8081:8081 \
  -v /path/to/wechat:/data \
  weflow:latest
```

**数据格式** (WeFlow):
```json
{
  "type": "text",
  "from": "wxid_xxx",
  "to": "wxid_yyy",
  "content": "消息内容",
  "timestamp": 1713417600
}
```

### 3. 统一消息 Schema

所有消息最终转换为统一格式存储在 `raw_messages` 表：

```python
class RawMessage(Base):
    __tablename__ = 'raw_messages'
    
    id = Column(Integer, primary_key=True)
    platform = Column(String(20))        # 'qq' or 'wechat'
    account_id = Column(String(100))     # QQ号 or 微信ID
    message_id = Column(String(100))     # 唯一消息ID
    channel_id = Column(String(100))     # 群号/会话ID
    user_id = Column(String(100))        # 发送者ID
    content = Column(Text)               # 消息内容
    raw_data = Column(JSON)              # 原始数据
    created_at = Column(DateTime)        # 消息时间
    collected_at = Column(DateTime)      # 收集时间
```

## 历史消息导入

### 1. QQ 历史消息导入

**数据库位置**:
```
C:\Users\{用户名}\Documents\Tencent Files\{QQ号}\nt_qq\nt_db\nt_msg.db
```

**加密方式**: SQLCipher (修改参数)

**解密流程**:

```bash
# 步骤 1: 提取密钥
git clone https://github.com/yllhwa/qq-win-db-key.git
cd qq-win-db-key
.\windows_ntqq_get_key.ps1  # 需要管理员权限

# 步骤 2: 解密数据库
cd /path/to/voile
python scripts/decrypt_qq_db.py <QQ号> <密钥>

# 步骤 3: 导入到 Voile
python scripts/import_qq_history.py qq_decrypt_<QQ号>/nt_msg_decrypted.db
```

**关键技术点**:
- 数据库有 1024 字节特殊头部需要移除
- SQLCipher 参数: `kdf_iter=4000`, `HMAC_SHA1`
- 密钥从 `wrapper.node` 提取，16 字符可见字符串

**详细文档**: `docs/QQ_DATABASE_DECRYPT.md`

### 2. 微信历史消息导入

**数据库位置**:
```
C:\Users\{用户名}\Documents\WeChat Files\{微信ID}\Msg\
```

**加密方式**: 自定义加密算法

**解密流程**:

```bash
# 步骤 1: 提取密钥
python scripts/extract_wechat_key.py

# 步骤 2: 解密数据库
python scripts/decrypt_wechat_db.py <微信ID> <密钥>

# 步骤 3: 导入到 Voile
python scripts/import_wechat_history.py wechat_decrypt_<微信ID>/
```

**关键技术点**:
- 密钥存储在内存中，需要从进程提取
- 数据库文件分散在多个 `.db` 文件中
- 需要合并多个数据库的消息

**详细文档**: `docs/WECHAT_DATABASE_DECRYPT.md` (内部文档)

## 数据处理流程

### 1. 消息接收 (AstrBot Plugin)

**代码位置**: `plugins/astrbot_plugin_voile/`

**核心逻辑**:
```python
class VoilePlugin(Plugin):
    async def on_message(self, event: MessageEvent):
        # 1. 提取消息信息
        platform = self.detect_platform(event)
        message_data = self.extract_message(event)
        
        # 2. 转换为统一格式
        raw_message = RawMessage(
            platform=platform,
            account_id=message_data['account_id'],
            message_id=message_data['message_id'],
            channel_id=message_data['channel_id'],
            user_id=message_data['user_id'],
            content=message_data['content'],
            raw_data=message_data['raw'],
            created_at=message_data['timestamp'],
            collected_at=datetime.now(timezone.utc)
        )
        
        # 3. 存储到数据库
        session.add(raw_message)
        session.commit()
        
        # 4. 触发分析任务
        await self.trigger_analysis(raw_message.id)
```

### 2. 消息分析 (Python Agents)

**代码位置**: `core/agents/`

**分析流程**:
```python
# 主题提取
topics = topic_agent.extract_topics(message.content)

# 情感分析
sentiment = sentiment_agent.analyze(message.content)

# 人物画像更新
persona_agent.update_profile(message.user_id, message.content)

# 决策日志识别
if decision_agent.is_decision(message.content):
    decision_agent.log_decision(message)
```

### 3. 知识归档 (Obsidian Writer)

**代码位置**: `core/obsidian/`

**归档结构**:
```
Obsidian Vault/
├── Topics/              # 主题地图
│   ├── 技术讨论.md
│   └── 产品规划.md
├── Personas/            # 人物档案
│   ├── 张三.md
│   └── 李四.md
├── Decisions/           # 决策日志
│   └── 2026-04-18-架构调整.md
└── Links/               # 链接归档
    └── 技术文章.md
```

## 常见维护任务

### 1. 添加新的消息源

**步骤**:
1. 在 `gateway/` 创建新的适配器
2. 实现消息格式转换
3. 在 `core/storage.py` 添加 platform 类型
4. 更新 AstrBot 插件识别逻辑
5. 添加测试用例

**示例**: 添加 Telegram 支持
```python
# gateway/telegram_adapter.go
func (a *TelegramAdapter) ConvertMessage(msg TelegramMessage) UnifiedMessage {
    return UnifiedMessage{
        Platform: "telegram",
        MessageID: msg.ID,
        // ... 其他字段
    }
}
```

### 2. 修改分析逻辑

**步骤**:
1. 修改 `core/agents/` 中的对应 agent
2. 更新测试用例
3. 在测试环境验证
4. 部署到生产环境

**示例**: 改进主题提取
```python
# core/agents/topic_agent.py
def extract_topics(self, content: str) -> List[str]:
    # 使用更好的 NLP 模型
    doc = self.nlp(content)
    topics = [chunk.text for chunk in doc.noun_chunks]
    return self.filter_topics(topics)
```

### 3. 数据库迁移

**步骤**:
```bash
# 1. 创建迁移脚本
alembic revision -m "add new column"

# 2. 编辑迁移文件
# alembic/versions/xxx_add_new_column.py

# 3. 执行迁移
alembic upgrade head

# 4. 验证
psql -h 192.168.50.130 -U voile -d voile -c "\d raw_messages"
```

### 4. 性能优化

**常见优化点**:
- 添加数据库索引
- 批量插入消息
- 使用 Redis 缓存
- 异步处理分析任务

**示例**: 批量插入
```python
# 优化前
for msg in messages:
    session.add(RawMessage(**msg))
    session.commit()

# 优化后
session.bulk_insert_mappings(RawMessage, messages)
session.commit()
```

## 故障排查

### 1. 消息收集中断

**症状**: 新消息不再入库

**排查步骤**:
```bash
# 1. 检查 Docker 容器状态
docker compose ps

# 2. 查看日志
docker compose logs -f gateway
docker compose logs -f astrbot

# 3. 检查网络连接
curl http://localhost:8080/health

# 4. 检查数据库连接
psql -h 192.168.50.130 -U voile -d voile -c "SELECT 1"
```

**常见原因**:
- NapCatQQ 掉线 → 重启容器
- WeFlow API 失效 → 检查 WeFlow 服务
- 数据库连接池耗尽 → 增加连接数
- 磁盘空间不足 → 清理日志

### 2. 解密失败

**症状**: HMAC 校验失败、无法读取数据库

**排查步骤**:
```bash
# 1. 验证密钥
python scripts/verify_key.py <数据库路径> <密钥>

# 2. 检查文件头
hexdump -C nt_msg.db | head -20

# 3. 尝试不同参数
python scripts/decrypt_qq_db.py --debug <QQ号> <密钥>
```

**常见原因**:
- 密钥错误 → 重新提取
- 文件头未移除 → 检查脚本
- SQLCipher 版本不匹配 → 更新工具

### 3. 分析任务堆积

**症状**: 消息入库但未分析

**排查步骤**:
```bash
# 1. 检查任务队列
redis-cli -h 192.168.50.130 LLEN analysis_queue

# 2. 查看 worker 状态
docker compose logs -f worker

# 3. 检查 CPU/内存
docker stats
```

**解决方案**:
- 增加 worker 数量
- 优化分析算法
- 使用更快的模型

## 改进建议

### 短期改进 (1-2 周)

1. **完善监控**
   - 添加 Prometheus metrics
   - 配置 Grafana 仪表盘
   - 设置告警规则

2. **优化导入速度**
   - 并行处理多个数据库
   - 使用 COPY 命令批量导入
   - 添加进度条显示

3. **增强错误处理**
   - 添加重试机制
   - 记录详细错误日志
   - 自动恢复机制

### 中期改进 (1-2 月)

1. **支持增量导入**
   - 记录上次导入位置
   - 只导入新消息
   - 避免重复处理

2. **改进分析质量**
   - 使用更好的 NLP 模型
   - 添加上下文理解
   - 支持多语言

3. **Web 管理界面**
   - 查看消息统计
   - 管理导入任务
   - 配置分析规则

### 长期改进 (3-6 月)

1. **分布式架构**
   - 消息队列 (RabbitMQ/Kafka)
   - 分布式存储
   - 负载均衡

2. **AI 增强**
   - 接入大语言模型
   - 自动生成摘要
   - 智能问答

3. **多租户支持**
   - 用户隔离
   - 权限管理
   - 配额限制

## 开发环境设置

### 本地开发

```bash
# 1. 克隆仓库
git clone http://192.168.50.130:3000/xartpro/voile.git
cd voile

# 2. 安装依赖
pip install -e ".[dev]"

# 3. 启动服务
docker compose up -d

# 4. 运行测试
pytest

# 5. 代码检查
ruff check core/ plugins/
mypy core/
```

### 调试技巧

**Python 调试**:
```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用 ipdb
import ipdb; ipdb.set_trace()
```

**查看实时日志**:
```bash
# 所有服务
docker compose logs -f

# 特定服务
docker compose logs -f gateway

# 带时间戳
docker compose logs -f --timestamps
```

**数据库查询**:
```sql
-- 查看最近消息
SELECT * FROM raw_messages 
ORDER BY created_at DESC 
LIMIT 10;

-- 统计各平台消息数
SELECT platform, COUNT(*) 
FROM raw_messages 
GROUP BY platform;

-- 查找特定用户消息
SELECT * FROM raw_messages 
WHERE user_id = '123456' 
ORDER BY created_at DESC;
```

## 联系方式

- **项目负责人**: [你的名字]
- **技术支持**: [团队联系方式]
- **问题反馈**: Gitea Issues
- **文档更新**: 直接提交 PR

## 相关文档

- [QQ 数据库解密详解](QQ_DATABASE_DECRYPT.md)
- [微信数据库解密详解](WECHAT_DATABASE_DECRYPT.md) (内部)
- [API 文档](API_REFERENCE.md)
- [部署指南](DEPLOYMENT.md)

---

**最后更新**: 2026-04-18  
**文档版本**: v1.0  
**维护者**: XartPro Team
