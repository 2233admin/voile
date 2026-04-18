# AstrBot 插件维护指南

## 概述

`astrbot_plugin_voile` 是 Voile 系统的消息接收器，负责：
- 接收来自 AstrBot 的实时消息事件
- 转换为 Voile 统一 Schema
- 存储到数据库
- 提取 URL 并推送到 Redis 队列

## 插件架构

```
AstrBot (OneBot v11 / WeChat)
    ↓
astrbot_plugin_voile (消息接收器)
    ↓
core.storage.db (数据库层)
    ↓
PostgreSQL / SQLite
```

## 文件结构

```
plugins/astrbot_plugin_voile/
├── __init__.py          # 插件主代码
├── metadata.yaml        # 插件元数据
├── README.md           # 插件说明（本文件）
└── requirements.txt    # 依赖（可选）
```

## 核心代码说明

### 1. 插件注册

```python
@register(
    "voile_sink",
    "2233admin",
    "Sink QQ/WeChat messages into Voile storage and push URLs to Redis",
    PLUGIN_VERSION,
)
class VoileSink(Star):
    ...
```

- **插件 ID**: `voile_sink`
- **作者**: `2233admin`
- **版本**: `0.2.0`

### 2. 平台映射

```python
_PLATFORM_MAP = {
    "aiocqhttp": "qq",      # OneBot v11 (NapCatQQ / Lagrange)
    "nakuru": "qq",
    "wechat": "wechat",
    "wecom": "wechat",
}
```

AstrBot 的平台名称映射到 Voile 的 Platform 枚举。

### 3. 消息处理流程

```python
@filter.all()
async def on_message(self, event: AstrMessageEvent) -> None:
    # 1. 检测平台
    platform = detect_platform(event)
    
    # 2. 提取消息信息
    content = event.message_str
    sender_id = event.get_sender_id()
    channel_id = event.session_id
    message_id = event.message_id
    timestamp = event.timestamp
    
    # 3. 提取 URL
    urls = extract_urls(content)
    
    # 4. 创建 Message 对象
    msg = Message(
        platform=platform,
        channel_id=channel_id,
        user_id=sender_id,
        message_id=message_id,
        content=content,
        urls=urls,
        created_at=timestamp
    )
    
    # 5. 存储到数据库
    inserted = self._db.upsert(msg)
    
    # 6. 推送 URL 到 Redis（如果有）
    if inserted and urls:
        self._push_urls(urls)
```

## 环境变量配置

在 AstrBot 的 `.env` 文件或系统环境变量中配置：

```bash
# 数据库连接
VOILE_DB_URL=postgresql://voile:voile_pass@192.168.50.130:5434/voile

# Redis 连接（可选，用于 URL 队列）
VOILE_REDIS_URL=redis://192.168.50.130:6379/0
```

### 数据库 URL 格式

**PostgreSQL** (生产环境):
```
postgresql://用户名:密码@主机:端口/数据库名
```

**SQLite** (开发环境):
```
sqlite:///voile.db
```

## 部署步骤

### 1. 安装 Voile Core

```bash
# 克隆 Voile 仓库
git clone http://192.168.50.130:3000/xartpro/voile.git
cd voile

# 安装 core 模块
pip install -e .
```

### 2. 复制插件到 AstrBot

```bash
# 复制插件目录
cp -r plugins/astrbot_plugin_voile /path/to/astrbot/plugins/

# 或创建符号链接
ln -s /path/to/voile/plugins/astrbot_plugin_voile /path/to/astrbot/plugins/
```

### 3. 配置环境变量

编辑 AstrBot 的 `.env` 文件：

```bash
# 添加 Voile 配置
VOILE_DB_URL=postgresql://voile:voile_pass@192.168.50.130:5434/voile
VOILE_REDIS_URL=redis://192.168.50.130:6379/0
```

### 4. 重启 AstrBot

```bash
# 如果使用 Docker
docker compose restart astrbot

# 如果直接运行
python main.py
```

### 5. 验证插件加载

查看 AstrBot 日志：

```bash
# 应该看到类似输出
[INFO] 加载插件: voile_sink v0.2.0
[INFO] Voile Sink 插件已启动
```

## 数据库 Schema

### messages 表

```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    channel_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    message_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    raw_payload JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    urls JSONB DEFAULT '[]'
);

CREATE INDEX idx_messages_platform ON messages(platform);
CREATE INDEX idx_messages_channel_id ON messages(channel_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

### 示例数据

```json
{
  "id": 1,
  "platform": "qq",
  "channel_id": "group_123456",
  "user_id": "789012",
  "message_id": "qq_msg_123456789",
  "message_type": "text",
  "content": "这是一条测试消息 https://example.com",
  "raw_payload": {
    "post_type": "message",
    "message_type": "group",
    "group_id": 123456
  },
  "created_at": "2026-04-18T12:00:00+00:00",
  "urls": ["https://example.com"]
}
```

## 测试

### 单元测试

```python
# tests/test_astrbot_plugin.py
import pytest
from datetime import datetime, UTC
from core.schemas.message import Message, Platform
from core.storage.db import Database

def test_message_storage():
    db = Database("sqlite:///:memory:")
    
    msg = Message(
        platform=Platform.QQ,
        channel_id="group_123",
        user_id="user_456",
        message_id="msg_789",
        content="测试消息",
        created_at=datetime.now(UTC)
    )
    
    # 第一次插入应该成功
    assert db.upsert(msg) == True
    
    # 重复插入应该跳过
    assert db.upsert(msg) == False
```

### 集成测试

发送测试消息到 QQ 群，检查数据库：

```sql
-- 查看最近消息
SELECT * FROM messages 
ORDER BY created_at DESC 
LIMIT 10;

-- 统计各平台消息数
SELECT platform, COUNT(*) 
FROM messages 
GROUP BY platform;
```

## 故障排查

### 问题 1: 插件未加载

**症状**: AstrBot 日志中没有 voile_sink 插件

**排查**:
```bash
# 检查插件目录
ls -la /path/to/astrbot/plugins/astrbot_plugin_voile/

# 检查 metadata.yaml
cat /path/to/astrbot/plugins/astrbot_plugin_voile/metadata.yaml

# 检查 AstrBot 日志
tail -f /path/to/astrbot/logs/astrbot.log
```

**解决**:
- 确保插件目录结构正确
- 确保 `__init__.py` 和 `metadata.yaml` 存在
- 重启 AstrBot

### 问题 2: 数据库连接失败

**症状**: 日志中出现数据库连接错误

**排查**:
```bash
# 测试数据库连接
psql -h 192.168.50.130 -p 5434 -U voile -d voile

# 检查环境变量
echo $VOILE_DB_URL
```

**解决**:
- 检查数据库服务是否运行
- 验证连接字符串正确
- 检查防火墙规则

### 问题 3: 消息未入库

**症状**: 发送消息后数据库中没有记录

**排查**:
```python
# 添加调试日志
import logging
logger = logging.getLogger(__name__)

@filter.all()
async def on_message(self, event: AstrMessageEvent) -> None:
    logger.info(f"收到消息: {event.message_str}")
    logger.info(f"平台: {event.platform_meta.name if event.platform_meta else 'unknown'}")
    # ... 其他代码
```

**解决**:
- 检查平台映射是否正确
- 验证消息格式
- 查看详细错误日志

### 问题 4: Redis 连接失败

**症状**: URL 未推送到 Redis

**排查**:
```bash
# 测试 Redis 连接
redis-cli -h 192.168.50.130 ping

# 检查队列
redis-cli -h 192.168.50.130 LLEN voile:url_queue
```

**解决**:
- Redis 连接失败不影响消息存储（best-effort）
- 检查 Redis 服务状态
- 验证 VOILE_REDIS_URL 配置

## 性能优化

### 1. 批量插入

当前实现是单条插入，高并发时可以优化为批量：

```python
class VoileSink(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self._message_buffer = []
        self._buffer_size = 100
        
    async def on_message(self, event: AstrMessageEvent) -> None:
        msg = self._create_message(event)
        self._message_buffer.append(msg)
        
        if len(self._message_buffer) >= self._buffer_size:
            await self._flush_buffer()
    
    async def _flush_buffer(self):
        # 批量插入
        self._db.bulk_upsert(self._message_buffer)
        self._message_buffer.clear()
```

### 2. 异步处理

使用异步任务处理 URL 推送：

```python
import asyncio

async def _push_urls_async(self, urls: list[str]) -> None:
    await asyncio.to_thread(self._push_urls, urls)
```

### 3. 连接池

使用连接池减少数据库连接开销：

```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

## 监控指标

### 关键指标

- **消息接收速率**: 每秒处理的消息数
- **数据库写入延迟**: 消息入库耗时
- **重复消息率**: 被跳过的重复消息比例
- **URL 提取率**: 包含 URL 的消息比例

### 监控实现

```python
import time
from collections import defaultdict

class VoileSink(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self._metrics = defaultdict(int)
        self._start_time = time.time()
    
    async def on_message(self, event: AstrMessageEvent) -> None:
        start = time.time()
        
        # 处理消息
        inserted = self._db.upsert(msg)
        
        # 记录指标
        self._metrics['total'] += 1
        if inserted:
            self._metrics['inserted'] += 1
        else:
            self._metrics['duplicates'] += 1
        
        if urls:
            self._metrics['with_urls'] += 1
        
        elapsed = time.time() - start
        self._metrics['total_time'] += elapsed
    
    def get_stats(self) -> dict:
        uptime = time.time() - self._start_time
        return {
            'uptime': uptime,
            'total_messages': self._metrics['total'],
            'inserted': self._metrics['inserted'],
            'duplicates': self._metrics['duplicates'],
            'with_urls': self._metrics['with_urls'],
            'avg_latency': self._metrics['total_time'] / max(self._metrics['total'], 1),
            'messages_per_second': self._metrics['total'] / uptime
        }
```

## 维护任务

### 定期清理

```sql
-- 删除 30 天前的消息
DELETE FROM messages 
WHERE created_at < NOW() - INTERVAL '30 days';

-- 清理重复消息（保留最新的）
DELETE FROM messages a
USING messages b
WHERE a.message_id = b.message_id
  AND a.id < b.id;
```

### 数据库优化

```sql
-- 重建索引
REINDEX TABLE messages;

-- 更新统计信息
ANALYZE messages;

-- 清理死元组
VACUUM FULL messages;
```

## 升级指南

### 从 v0.1.0 升级到 v0.2.0

1. **更新代码**
   ```bash
   cd /path/to/voile
   git pull
   pip install -e .
   ```

2. **数据库迁移**
   ```bash
   # 如果有 schema 变更
   alembic upgrade head
   ```

3. **重启服务**
   ```bash
   docker compose restart astrbot
   ```

## 相关文档

- [Voile 维护指南](../../docs/MAINTENANCE_GUIDE.md)
- [AstrBot 官方文档](https://github.com/Soulter/AstrBot)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)

## 联系方式

- **问题反馈**: Gitea Issues
- **技术支持**: XartPro Team

---

**最后更新**: 2026-04-18  
**插件版本**: v0.2.0  
**维护者**: 2233admin
