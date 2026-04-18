# Voile 项目文档更新总结

## 📅 更新日期
2026-04-18

## 🎯 目标
将 QQ 数据库解密方案完整记录到 voile 项目，让团队成员能够：
1. 理解 Voile 是完整的消息分析系统（不只是实时收集）
2. 快速上手历史消息导入
3. 复用解密工具和文档

## ✅ 完成内容

### 1. 核心文档
- **`docs/QQ_DATABASE_DECRYPT.md`** - 完整技术文档
  - 解密原理和步骤
  - SQLCipher 参数详解
  - 数据库结构说明
  - 常见问题解答
  - 参考资料链接

### 2. 自动化工具
- **`scripts/decrypt_qq_db.py`** - Python 跨平台脚本
  - 自动查找数据库
  - 移除文件头
  - 生成 SQL 脚本
  - 执行解密
  - 统计消息数量
  
- **`scripts/decrypt_qq_db.sh`** - Bash 脚本
  - Linux/macOS/Git Bash 支持
  - 彩色输出
  - 错误处理

- **`scripts/README.md`** - 快速开始指南
  - 一键解密命令
  - 完整示例
  - 故障排除

### 3. 项目说明
- **`README.md`** - 主文档重构
  - 架构图：区分实时收集和历史导入
  - 项目结构：标注工具和文档位置
  - Features & Status：清晰展示功能完成度
  - Message Sources：详细说明两种消息来源
  - Import Pipeline：完整导入流程

### 4. 安全措施
- **`.gitignore`** - 防止敏感文件泄露
  - 解密工作目录
  - 数据库文件
  - SQL 脚本

## 📊 解密成果

成功解密 QQ 数据库：
- **12,602** 条私聊消息
- **392,775** 条群聊消息
- **总计 405,377** 条历史消息

## 🔗 Git 提交记录

```
6afa482 docs: 重构 README - 突出 Voile 作为完整的消息分析系统
e25582b chore: 添加 QQ 解密相关文件到 .gitignore
6fa487e docs: 添加 QQ 数据库解密快速开始指南
efaa689 docs: 添加 QQ NT 数据库解密完整文档和自动化脚本
```

## 🚀 团队使用指南

### 快速开始
```bash
# 1. 克隆仓库
git clone https://github.com/2233admin/voile.git
cd voile

# 2. 获取密钥（Windows，需要管理员权限）
git clone https://github.com/yllhwa/qq-win-db-key.git
cd qq-win-db-key
.\windows_ntqq_get_key.ps1

# 3. 解密数据库
cd ../voile
python scripts/decrypt_qq_db.py <QQ号> <密钥>

# 4. 导入到 Voile（待实现）
# python scripts/import_to_voile.py qq_decrypt_<QQ号>/nt_msg_decrypted.db
```

### 文档位置
- 快速开始：`scripts/README.md`
- 技术细节：`docs/QQ_DATABASE_DECRYPT.md`
- 主项目说明：`README.md`

## 🔑 关键技术点

### QQ NT 数据库加密
- **加密方式**：SQLCipher（修改参数）
- **特殊头部**：1024 字节需要移除
- **关键参数**：
  - `cipher_page_size = 4096`
  - `kdf_iter = 4000`（不是 256000）
  - `cipher_hmac_algorithm = HMAC_SHA1`（不是 SHA512）
  - `cipher_kdf_algorithm = PBKDF2_HMAC_SHA512`

### 密钥提取
- 工具：[qq-win-db-key](https://github.com/yllhwa/qq-win-db-key)
- 方法：调试器附加到 QQ 进程，从 wrapper.node 提取
- 格式：16 字符可见字符串（如 `a'~b]{jmezG49em]`）

## 📈 下一步

1. **实现导入脚本**
   - 读取解密后的 SQLite 数据库
   - 转换为 Voile 统一 schema
   - 批量导入到 PostgreSQL

2. **WeChat 历史导入**
   - 集成 WeChatMsg 工具
   - 编写导入脚本

3. **数据分析**
   - 对历史消息运行分析管道
   - 生成 Obsidian 知识库

## 🎉 成果

- ✅ 完整的技术文档
- ✅ 自动化工具（Python + Bash）
- ✅ 清晰的项目说明
- ✅ 安全措施（gitignore）
- ✅ 成功解密验证（40万+消息）
- ✅ 团队可复用

## 📚 参考资料

- [QQDecrypt 官方文档](https://qqbackup.github.io/QQDecrypt/)
- [qq-win-db-key 工具](https://github.com/yllhwa/qq-win-db-key)
- [Android QQ NT 解密分析](https://blog.yllhwa.com/blog/android_qq_nt_database/)
- [SQLCipher API 文档](https://www.zetetic.net/sqlcipher/sqlcipher-api/)
