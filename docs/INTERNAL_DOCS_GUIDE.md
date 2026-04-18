# Voile 内部文档使用指南

## 文档位置

### GitHub (公开)
- 仓库: https://github.com/2233admin/voile
- 包含: QQ 解密、基础架构、开源依赖

### Gitea (内部)
- 仓库: http://192.168.50.130:3000/xartpro/voile
- 包含: 完整文档（包括微信解密等内部方案）

## 文档结构

```
voile/
├── CLAUDE.md                           # Claude Code 工作指南
├── README.md                           # 项目说明
├── docs/
│   ├── MAINTENANCE_GUIDE.md           # 系统维护完整指南 ⭐
│   ├── QQ_DATABASE_DECRYPT.md         # QQ 解密文档
│   ├── WECHAT_DATABASE_DECRYPT.md     # 微信解密文档（内部）⭐
│   └── DOCUMENTATION_UPDATE_SUMMARY.md # 文档更新记录
└── scripts/
    ├── README.md                       # 脚本快速开始
    ├── decrypt_qq_db.py               # QQ 解密工具
    ├── decrypt_wechat_db.py           # 微信解密工具（内部）⭐
    └── import_*_history.py            # 历史导入脚本
```

⭐ = 内部文档/工具

## 给 Claude Code 的说明

### 首次使用项目

1. **克隆仓库**
   ```bash
   # 内部使用 Gitea
   git clone http://192.168.50.130:3000/xartpro/voile.git
   cd voile
   ```

2. **阅读核心文档**
   - 先读 `CLAUDE.md` - 了解项目结构和工作规范
   - 再读 `docs/MAINTENANCE_GUIDE.md` - 理解完整架构
   - 根据任务查看具体文档

3. **理解数据流**
   ```
   消息源 → 接入层 → 标准化 → 存储 → 分析 → 归档
   ```

### 维护和改进系统

1. **查找相关文档**
   - QQ 相关: `docs/QQ_DATABASE_DECRYPT.md`
   - 微信相关: `docs/WECHAT_DATABASE_DECRYPT.md`
   - 架构问题: `docs/MAINTENANCE_GUIDE.md`
   - 代码规范: `CLAUDE.md`

2. **修改代码**
   - 遵循 `CLAUDE.md` 中的代码风格
   - 参考现有实现模式
   - 添加测试和文档

3. **故障排查**
   - 查看 `docs/MAINTENANCE_GUIDE.md` 的故障排查章节
   - 检查日志: `docker compose logs -f`
   - 验证配置文件

### 添加新功能

1. **参考现有实现**
   - 查看 `docs/MAINTENANCE_GUIDE.md` 的"常见维护任务"
   - 参考类似功能的代码
   - 保持架构一致性

2. **更新文档**
   - 修改代码时同步更新文档
   - 添加新功能要更新 `MAINTENANCE_GUIDE.md`
   - 提交时说明文档变更

## 文档维护

### 更新文档

```bash
# 1. 修改文档
vim docs/MAINTENANCE_GUIDE.md

# 2. 提交
git add docs/MAINTENANCE_GUIDE.md
git commit -m "docs: 更新维护指南 - 添加 XXX 说明"

# 3. 推送到 Gitea
git push origin main
```

### 文档版本

每次重大更新后：
1. 更新文档底部的"最后更新"日期
2. 增加版本号
3. 在 `DOCUMENTATION_UPDATE_SUMMARY.md` 记录变更

## 安全提示

### 敏感信息

以下内容**不要**推送到 GitHub：
- 微信解密相关文档和脚本
- 内部 API 密钥和凭证
- 生产环境配置
- 解密后的数据库文件

### 内部工具

标记为"内部"的工具和文档：
- 仅在 Gitea 上维护
- 不要公开分享
- 使用时注意数据安全

## 团队协作

### 提问和反馈

- **技术问题**: Gitea Issues
- **文档改进**: 直接提交 PR
- **紧急问题**: 联系项目负责人

### 知识分享

- 发现新的解决方案 → 更新 `MAINTENANCE_GUIDE.md`
- 遇到新的问题 → 添加到故障排查章节
- 改进工具脚本 → 更新对应文档

## 快速参考

### 常用命令

```bash
# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f

# QQ 解密
python scripts/decrypt_qq_db.py <QQ号> <密钥>

# 微信解密
python scripts/decrypt_wechat_db.py <微信ID> <密钥>

# 运行测试
pytest

# 代码检查
ruff check core/ plugins/
```

### 常用查询

```sql
-- 最近消息
SELECT * FROM raw_messages ORDER BY created_at DESC LIMIT 10;

-- 统计
SELECT platform, COUNT(*) FROM raw_messages GROUP BY platform;

-- 查找用户消息
SELECT * FROM raw_messages WHERE user_id = '123456';
```

## 相关链接

- [GitHub 仓库](https://github.com/2233admin/voile) - 公开版本
- [Gitea 仓库](http://192.168.50.130:3000/xartpro/voile) - 完整版本
- [Linear 项目](https://linear.app/xartpro/project/不动的大图书馆-5a06f255e3b4) - 任务管理

---

**最后更新**: 2026-04-18  
**维护者**: XartPro Team
