# Voile Project - Claude Code Instructions

> 本文件为 Claude Code 提供项目上下文和工作指南

## 项目概述

Voile 是一个聊天消息分析和知识归档系统，用于：
- 收集 QQ/微信消息（实时 + 历史）
- 智能分析（主题、情感、人物画像）
- 知识归档（Obsidian 集成）

## 技术栈

- **Python 3.11+**: 核心业务逻辑
- **Go 1.22+**: API 网关
- **Rust**: 文本处理（gRPC）
- **PostgreSQL**: 主数据库
- **Docker Compose**: 服务编排

## 项目结构

```
voile/
├── core/          # Python 核心模块
│   ├── storage.py      # 数据模型和 ORM
│   ├── agents/         # 分析 agents
│   └── obsidian/       # Obsidian 集成
├── gateway/       # Go API 网关
├── kernel/        # Rust 文本处理
├── plugins/       # AstrBot 插件
├── scripts/       # 工具脚本
│   ├── decrypt_qq_db.py       # QQ 解密
│   ├── decrypt_wechat_db.py   # 微信解密
│   └── import_*_history.py    # 历史导入
└── docs/          # 文档
    ├── MAINTENANCE_GUIDE.md        # 维护指南
    ├── QQ_DATABASE_DECRYPT.md      # QQ 解密文档
    └── WECHAT_DATABASE_DECRYPT.md  # 微信解密文档
```

## 工作原则

### 1. 代码风格

**Python**:
- 使用 `ruff` 进行代码检查
- 使用 `mypy` 进行类型检查
- 遵循 PEP 8
- 使用类型注解

**Go**:
- 使用 `gofmt` 格式化
- 遵循 Go 标准库风格
- 错误处理要明确

**Rust**:
- 使用 `cargo fmt`
- 使用 `cargo clippy`
- 遵循 Rust 最佳实践

### 2. 提交规范

使用 Conventional Commits:
- `feat:` - 新功能
- `fix:` - 修复 bug
- `docs:` - 文档更新
- `refactor:` - 重构
- `test:` - 测试相关
- `chore:` - 构建/工具相关

示例:
```
feat(gateway): 添加微信消息路由
fix(storage): 修复消息重复插入问题
docs: 更新 QQ 解密文档
```

### 3. 测试要求

- 新功能必须有测试
- 修复 bug 要添加回归测试
- 运行 `pytest` 确保测试通过
- 关键路径要有集成测试

### 4. 文档更新

修改代码时同步更新：
- 代码注释
- API 文档
- 用户文档（docs/）
- MAINTENANCE_GUIDE.md（如果涉及架构变更）

## 常见任务

### 添加新的消息源

1. 在 `gateway/` 创建适配器
2. 实现消息格式转换
3. 更新 `core/storage.py` 的 platform 枚举
4. 更新 AstrBot 插件
5. 添加测试
6. 更新文档

### 修改分析逻辑

1. 修改 `core/agents/` 中的对应 agent
2. 更新测试用例
3. 在测试环境验证
4. 更新文档

### 数据库迁移

```bash
# 创建迁移
alembic revision -m "描述"

# 编辑迁移文件
# alembic/versions/xxx_描述.py

# 执行迁移
alembic upgrade head
```

### 添加新的解密脚本

1. 在 `scripts/` 创建脚本
2. 遵循现有脚本的结构
3. 添加详细的文档字符串
4. 在 `docs/` 创建对应文档
5. 更新 README.md

## 关键文件说明

### core/storage.py
- 定义数据模型
- SQLAlchemy ORM
- 统一消息 Schema

### plugins/astrbot_plugin_voile/
- AstrBot 插件入口
- 消息接收和处理
- 格式转换

### gateway/
- Go API 网关
- 消息路由
- 协议适配

### scripts/decrypt_*.py
- 数据库解密工具
- 独立运行
- 详细的错误处理

## 数据库 Schema

### raw_messages 表

```python
class RawMessage(Base):
    __tablename__ = 'raw_messages'
    
    id = Column(Integer, primary_key=True)
    platform = Column(String(20))        # 'qq' or 'wechat'
    account_id = Column(String(100))     # 账号ID
    message_id = Column(String(100))     # 唯一消息ID
    channel_id = Column(String(100))     # 群号/会话ID
    user_id = Column(String(100))        # 发送者ID
    content = Column(Text)               # 消息内容
    raw_data = Column(JSON)              # 原始数据
    created_at = Column(DateTime)        # 消息时间
    collected_at = Column(DateTime)      # 收集时间
```

## 环境变量

在 `.env` 文件中配置：

```bash
# 数据库
DATABASE_URL=postgresql://voile:password@localhost:5432/voile

# Redis
REDIS_URL=redis://localhost:6379/0

# Obsidian
OBSIDIAN_HOST_PATH=/path/to/vault

# WeFlow (内部)
WEFLOW_API_URL=http://localhost:8081
WEFLOW_API_KEY=your_key
```

## 调试技巧

### 查看日志
```bash
# 所有服务
docker compose logs -f

# 特定服务
docker compose logs -f gateway
```

### 数据库查询
```sql
-- 最近消息
SELECT * FROM raw_messages 
ORDER BY created_at DESC 
LIMIT 10;

-- 统计
SELECT platform, COUNT(*) 
FROM raw_messages 
GROUP BY platform;
```

### Python 调试
```python
# 添加断点
import pdb; pdb.set_trace()
```

## 部署

### 开发环境
```bash
docker compose up -d
```

### 生产环境
```bash
# NAS 部署
ssh admin@192.168.50.130
cd /volume1/docker/voile
docker compose -f docker-compose.prod.yml up -d
```

## 安全注意事项

1. **敏感信息**
   - 不要提交密钥到 Git
   - 使用 `.env` 文件
   - `.gitignore` 已配置

2. **数据库密钥**
   - QQ/微信解密密钥仅本地使用
   - 解密后的数据库妥善保管
   - 使用完毕后删除

3. **API 凭证**
   - WeFlow API key 存储在 `.env`
   - 不要硬编码在代码中

## 故障排查

### 消息收集中断
1. 检查 Docker 容器状态
2. 查看日志
3. 检查网络连接
4. 验证数据库连接

### 解密失败
1. 验证密钥正确性
2. 检查文件头（QQ 需要移除 1024 字节）
3. 确认 SQLCipher 参数
4. 查看详细错误日志

### 性能问题
1. 检查数据库索引
2. 优化批量插入
3. 使用 Redis 缓存
4. 异步处理分析任务

## 相关文档

- [维护指南](docs/MAINTENANCE_GUIDE.md) - 完整的系统维护文档
- [QQ 解密](docs/QQ_DATABASE_DECRYPT.md) - QQ 数据库解密详解
- [微信解密](docs/WECHAT_DATABASE_DECRYPT.md) - 微信数据库解密详解（内部）

## 联系方式

- **问题反馈**: Gitea Issues
- **文档更新**: 直接提交 PR
- **紧急问题**: 联系项目负责人

## Claude Code 特别说明

### 理解项目时
1. 先阅读 `docs/MAINTENANCE_GUIDE.md` 了解整体架构
2. 查看 `core/storage.py` 理解数据模型
3. 参考现有代码的实现模式

### 修改代码时
1. 保持与现有代码风格一致
2. 添加必要的类型注解和文档字符串
3. 更新相关测试
4. 同步更新文档

### 添加功能时
1. 先在 `docs/MAINTENANCE_GUIDE.md` 中查找类似功能
2. 遵循现有的架构模式
3. 考虑向后兼容性
4. 添加完整的文档

### 调试问题时
1. 查看 `docs/MAINTENANCE_GUIDE.md` 的故障排查章节
2. 检查日志文件
3. 验证配置文件
4. 使用调试工具

---

**最后更新**: 2026-04-18  
**文档版本**: v1.0
