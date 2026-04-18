# Voile 系统运维手册

> 本文档记录 Voile 系统在本地环境的实际部署情况，包括服务位置、配置、数据路径等

## 📋 环境概览

### 主机信息

| 项目 | 信息 |
|------|------|
| **主机名** | WIN-JR7M28KP4N8 |
| **操作系统** | Windows 11 Pro for Workstations 10.0.26200 |
| **用户** | Administrator |
| **本机 IP** | 192.168.50.54 |
| **角色** | 开发和测试环境 |

### 网络拓扑

```
本地开发机 (192.168.50.54)
    ↓
局域网 (192.168.50.0/24)
    ↓
NAS 服务器 (192.168.50.130)
    ├── Gitea (3000)
    ├── PostgreSQL (5434)
    ├── n8n (5678)
    └── Forgejo Actions Runners
```

## 🗂️ 数据位置

### 桌面数据

**路径**: `C:\Users\Administrator\Desktop\`

**重要文件**:
- `Claude Code 完整配置说明.txt` - Claude Code 配置文档
- `Claw Code 配置完成.txt` - Claw Code 配置记录
- `Claude Opus 4.6 System Card.pdf` - Claude 模型文档

**快捷方式**:
- `ChatLab.lnk` - ChatLab 应用
- `Claude Code (原版).lnk` - Claude Code 原版
- `Claw Code.lnk` - Claw Code
- `Clawd on Desk.lnk` - Clawd 桌面版
- `ComfyUI.lnk` - ComfyUI
- `DeepL.lnk` - DeepL 翻译

### 项目代码

**Voile 项目**:
- **路径**: `C:\Users\Administrator\Downloads\voile\`
- **Git 远程**:
  - GitHub: https://github.com/2233admin/voile (公开)
  - Gitea: http://192.168.50.130:3000/xartpro/voile (内部)
- **当前分支**: main
- **最新提交**: 449ea08 (docs(astrbot): 完善 AstrBot 插件文档和部署配置)

**其他项目**:
- `C:\Users\Administrator\Downloads\` - 下载目录，包含各种项目

### QQ 数据

**QQ 安装位置**:
- **路径**: `C:\Program Files\Tencent\QQNT\`
- **版本**: 9.9.29-47354
- **wrapper.node**: `C:\Program Files\Tencent\QQNT\versions\9.9.29-47354\resources\app\wrapper.node`

**QQ 数据目录**:
- **路径**: `C:\Users\Administrator\Documents\Tencent Files\1497479966\`
- **消息数据库**: `nt_qq\nt_db\nt_msg.db` (加密)
- **账号**: 1497479966

**解密数据** (临时):
- **工作目录**: `C:\Users\Administrator\Downloads\voile\qq_decrypt_1497479966\`
- **解密后数据库**: `nt_msg_decrypted.db` (358MB)
- **消息统计**:
  - 私聊消息: 12,602 条
  - 群聊消息: 392,775 条
  - 总计: 405,377 条

### 微信数据

**微信安装位置**:
- **路径**: `C:\Program Files\Tencent\WeChat\` (待确认)

**微信数据目录**:
- **路径**: `C:\Users\Administrator\Documents\WeChat Files\{微信ID}\` (待确认)
- **消息数据库**: `Msg\MSG*.db` (加密)

### Claude Code 配置

**配置目录**:
- **全局配置**: `C:\Users\Administrator\.claude\`
- **项目配置**: `C:\Users\Administrator\.claude\projects\C--Program-Files-Microsoft-Visual-Studio-18-Insiders\`
- **记忆系统**: `C:\Users\Administrator\.claude\projects\C--Program-Files-Microsoft-Visual-Studio-18-Insiders\memory\`

**重要文件**:
- `memory\voile_project_complete_documentation.md` - Voile 项目完整文档记忆
- `memory\MEMORY.md` - 记忆索引

## 🚀 服务部署

### NAS 服务器 (192.168.50.130)

#### Gitea / Forgejo

| 项目 | 信息 |
|------|------|
| **服务** | Forgejo (Gitea fork) |
| **版本** | 1.25.5 |
| **访问地址** | http://192.168.50.130:3000 |
| **SSH 端口** | 22 (目前不可用) |
| **数据库** | PostgreSQL |
| **仓库路径** | /volume1/docker/gitea/data/git/repositories |
| **用户** | xartpro |

**重要仓库**:
- `xartpro/voile` - Voile 项目（内部完整版）
- 其他项目仓库

#### PostgreSQL

| 项目 | 信息 |
|------|------|
| **版本** | 15+ |
| **端口** | 5434 |
| **数据库** | voile |
| **用户** | voile |
| **密码** | voile_pass |
| **连接字符串** | `postgresql://voile:voile_pass@192.168.50.130:5434/voile` |

**数据库表**:
- `messages` - 消息记录
- `links` - 链接归档
- `message_topics` - 主题标签
- `message_sentiments` - 情感分析

#### n8n

| 项目 | 信息 |
|------|------|
| **版本** | 最新 |
| **端口** | 5678 |
| **访问地址** | http://192.168.50.130:5678 |
| **用途** | 自动化工作流 |

**已配置工作流**:
- Gitea 集成
- 核心自动化任务

#### Redis

| 项目 | 信息 |
|------|------|
| **版本** | 7+ |
| **端口** | 6379 |
| **用途** | 缓存和消息队列 |
| **队列** | `voile:url_queue` - URL 提取队列 |

### 本地服务

#### AstrBot (待部署)

| 项目 | 信息 |
|------|------|
| **状态** | 待部署 |
| **端口** | 8080 (计划) |
| **插件** | astrbot_plugin_voile |
| **配置** | 见 `plugins/astrbot_plugin_voile/DEPLOYMENT.md` |

#### NapCatQQ (待部署)

| 项目 | 信息 |
|------|------|
| **状态** | 待部署 |
| **协议** | OneBot v11 |
| **端口** | 3000 (计划) |
| **目标** | 连接到 AstrBot |

#### WeFlow (待部署)

| 项目 | 信息 |
|------|------|
| **状态** | 待部署 |
| **端口** | 8081 (计划) |
| **用途** | 微信消息 HTTP API |

## 🔧 工具和脚本

### 解密工具

**QQ 解密**:
- **密钥提取**: `qq-win-db-key\windows_ntqq_get_key.ps1`
- **数据库解密**: `voile\scripts\decrypt_qq_db.py`
- **使用方法**: `python decrypt_qq_db.py 1497479966 "a'~b]{jmezG49em]"`

**微信解密**:
- **密钥提取**: `voile\scripts\extract_wechat_key.py` (待创建)
- **数据库解密**: `voile\scripts\decrypt_wechat_db.py` (待创建)

### 导入脚本

**QQ 历史导入**:
- **脚本**: `voile\scripts\import_qq_history.py` (待完善)
- **用法**: `python import_qq_history.py qq_decrypt_1497479966/nt_msg_decrypted.db`

**微信历史导入**:
- **脚本**: `voile\scripts\import_wechat_history.py` (待完善)
- **用法**: `python import_wechat_history.py wechat_decrypt_{微信ID}/`

### 部署脚本

**AstrBot 部署**:
- **脚本**: `voile\plugins\astrbot_plugin_voile\DEPLOYMENT.md`
- **包含**: Docker Compose 配置、部署脚本、监控脚本

## 📊 数据统计

### 已收集数据

| 平台 | 类型 | 数量 | 状态 |
|------|------|------|------|
| QQ | 历史消息 | 405,377 条 | ✅ 已解密 |
| QQ | 实时消息 | 0 条 | ⏳ 待部署 |
| 微信 | 历史消息 | 未知 | ⏳ 待解密 |
| 微信 | 实时消息 | 0 条 | ⏳ 待部署 |

### 存储使用

| 项目 | 大小 | 位置 |
|------|------|------|
| QQ 加密数据库 | 374 MB | `Tencent Files\1497479966\nt_qq\nt_db\` |
| QQ 解密数据库 | 358 MB | `voile\qq_decrypt_1497479966\` |
| Voile 代码库 | ~50 MB | `Downloads\voile\` |
| PostgreSQL 数据 | 未知 | NAS (192.168.50.130) |

## 🔐 凭证和密钥

### 数据库凭证

**PostgreSQL**:
- **主机**: 192.168.50.130:5434
- **数据库**: voile
- **用户**: voile
- **密码**: voile_pass

**Redis**:
- **主机**: 192.168.50.130:6379
- **密码**: 无

### QQ 解密密钥

**账号**: 1497479966
**密钥**: `a'~b]{jmezG49em]`
**提取时间**: 2026-04-18
**有效期**: 密钥可能在 QQ 重启后变化

### 微信解密密钥

**状态**: 待提取
**方法**: 内存扫描 / 调试器附加

### Git 凭证

**GitHub**:
- **用户**: 2233admin
- **仓库**: https://github.com/2233admin/voile
- **认证**: SSH / Token

**Gitea**:
- **主机**: http://192.168.50.130:3000
- **用户**: xartpro
- **仓库**: http://192.168.50.130:3000/xartpro/voile
- **认证**: HTTP (SSH 端口不可用)

## 📝 维护任务

### 日常维护

- [ ] 检查服务状态 (NAS 上的 PostgreSQL, Redis, Gitea)
- [ ] 查看消息收集统计
- [ ] 备份数据库
- [ ] 清理临时文件

### 定期任务

**每周**:
- [ ] 备份 PostgreSQL 数据库
- [ ] 检查磁盘空间使用
- [ ] 更新文档

**每月**:
- [ ] 清理 30 天前的消息
- [ ] 优化数据库索引
- [ ] 检查系统性能

### 待办事项

**高优先级**:
- [ ] 部署 AstrBot + NapCatQQ (QQ 实时消息收集)
- [ ] 部署 WeFlow (微信实时消息收集)
- [ ] 完善历史消息导入脚本
- [ ] 提取微信解密密钥

**中优先级**:
- [ ] 配置 Gitea SSH 访问
- [ ] 设置自动备份任务
- [ ] 添加监控告警
- [ ] 优化数据库性能

**低优先级**:
- [ ] 添加 Web 管理界面
- [ ] 实现增量导入
- [ ] 改进分析算法

## 🔍 故障排查

### 常见问题

**问题 1: 无法连接到 NAS 服务**

```bash
# 检查网络连接
ping 192.168.50.130

# 检查端口
telnet 192.168.50.130 5434  # PostgreSQL
telnet 192.168.50.130 3000  # Gitea
```

**问题 2: QQ 解密失败**

```bash
# 重新提取密钥
cd qq-win-db-key
.\windows_ntqq_get_key.ps1

# 使用新密钥解密
cd voile
python scripts/decrypt_qq_db.py 1497479966 "新密钥"
```

**问题 3: Git 推送失败**

```bash
# 使用 HTTP 而不是 SSH
git remote set-url gitea http://192.168.50.130:3000/xartpro/voile.git
git push gitea main
```

## 📞 联系方式

**项目负责人**: [你的名字]
**团队**: XartPro
**技术支持**: Gitea Issues
**紧急联系**: [联系方式]

## 📚 相关文档

- [Voile 维护指南](docs/MAINTENANCE_GUIDE.md)
- [QQ 数据库解密](docs/QQ_DATABASE_DECRYPT.md)
- [微信数据库解密](docs/WECHAT_DATABASE_DECRYPT.md) (内部)
- [AstrBot 插件文档](plugins/astrbot_plugin_voile/README.md)
- [内部文档使用指南](docs/INTERNAL_DOCS_GUIDE.md)

## 🔄 更新日志

| 日期 | 更新内容 | 更新人 |
|------|---------|--------|
| 2026-04-18 | 创建运维手册，记录当前部署状态 | Claude Code |
| 2026-04-18 | 完成 QQ 数据库解密，405,377 条消息 | Claude Code |
| 2026-04-18 | 完善 AstrBot 插件文档 | Claude Code |

---

**文档版本**: v1.0  
**最后更新**: 2026-04-18  
**维护者**: XartPro Team  
**保密级别**: 内部文档
