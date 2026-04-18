# QQ NT 数据库解密指南

本文档记录了如何解密 Windows 版 QQ NT 的本地消息数据库。

## 概述

QQ NT 使用 SQLCipher 加密本地消息数据库。数据库文件位于：
```
C:\Users\{用户名}\Documents\Tencent Files\{QQ号}\nt_qq\nt_db\nt_msg.db
```

## 前置要求

1. **获取解密密钥**
   - 使用 [qq-win-db-key](https://github.com/yllhwa/qq-win-db-key) 项目的 PowerShell 脚本
   - 脚本会自动启动 QQ 并通过调试器提取密钥
   - 密钥格式示例：`a'~b]{jmezG49em]`（16字符）

2. **工具准备**
   - SQLCipher 命令行工具（或 DB Browser for SQLCipher）
   - Python 3.x（用于移除文件头）

## 解密步骤

### 1. 获取密钥

```powershell
# 克隆 qq-win-db-key 项目
git clone https://github.com/yllhwa/qq-win-db-key.git
cd qq-win-db-key

# 运行 PowerShell 脚本（需要管理员权限）
.\windows_ntqq_get_key.ps1
```

脚本会：
- 自动检测 QQ 安装路径
- 启动 QQ 进程并附加调试器
- 提示你登录 QQ
- 提取并显示加密密钥

### 2. 移除数据库文件头

QQ NT 数据库有 1024 字节的特殊头部，必须先移除：

**方法 1：使用 Python**
```python
# 移除 1024 字节头部
with open('nt_msg.db', 'rb') as f:
    data = f.read()[1024:]
with open('nt_msg_clean.db', 'wb') as f:
    f.write(data)
```

**方法 2：使用 Linux/Git Bash**
```bash
tail -c +1025 nt_msg.db > nt_msg_clean.db
```

### 3. 配置 SQLCipher 参数

创建 SQL 脚本 `decrypt.sql`：

```sql
PRAGMA key = "你的密钥";
PRAGMA cipher_page_size = 4096;
PRAGMA kdf_iter = 4000;
PRAGMA cipher_hmac_algorithm = HMAC_SHA1;
PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512;
ATTACH DATABASE 'nt_msg_decrypted.db' AS plaintext KEY '';
SELECT sqlcipher_export('plaintext');
DETACH DATABASE plaintext;
```

**关键参数说明**：
- `cipher_page_size = 4096` - 页面大小
- `kdf_iter = 4000` - 密钥派生迭代次数（注意：不是 256000）
- `cipher_hmac_algorithm = HMAC_SHA1` - HMAC 算法（不是 SHA512）
- `cipher_kdf_algorithm = PBKDF2_HMAC_SHA512` - KDF 算法

### 4. 执行解密

```bash
sqlcipher nt_msg_clean.db < decrypt.sql
```

成功后会生成 `nt_msg_decrypted.db`，这是一个未加密的标准 SQLite 数据库。

## 数据库结构

解密后的数据库包含以下主要表：

### 消息表
- `c2c_msg_table` - 私聊消息（C2C = Client to Client）
- `group_msg_table` - 群聊消息
- `c2c_temp_msg_table` - 临时会话消息
- `discuss_msg_table` - 讨论组消息

### 其他表
- `recent_contact_v3_table` - 最近联系人
- `nt_uid_mapping_table` - UID 映射
- `draft_storage_table_v1` - 草稿存储
- `msg_unread_info_table` - 未读消息信息

### 消息表字段（部分）

`c2c_msg_table` 和 `group_msg_table` 的主要字段：
- `40001` - 消息 ID（主键）
- `40002` - 会话 ID / 群号
- `40010` - 消息时间戳
- `40020` - 发送者 UID
- `40021` - 接收者 UID
- `40050` - 消息类型
- `40090` - 消息内容（文本）
- `40800` - 消息元数据（BLOB）

## 常见问题

### Q: HMAC 校验失败
**A:** 确保：
1. 已移除 1024 字节文件头
2. 使用正确的 SQLCipher 参数（特别是 `kdf_iter = 4000` 和 `HMAC_SHA1`）
3. 密钥正确（从 wrapper.node 提取的原始字符串）

### Q: 密钥格式
**A:** 
- 直接使用从 PowerShell 脚本获取的原始字符串
- 不需要转换为十六进制
- 不需要添加 `x'...'` 前缀

### Q: SQLCipher 版本
**A:** QQ NT 使用修改过的 SQLCipher 参数，不是标准的 v3 或 v4 配置

## 自动化脚本

参考 `scripts/decrypt_qq_db.sh` 获取完整的自动化解密脚本。

## 参考资料

- [QQDecrypt - QQ 数据库解密工具](https://qqbackup.github.io/QQDecrypt/)
- [qq-win-db-key - Windows QQ 密钥提取](https://github.com/yllhwa/qq-win-db-key)
- [Android QQ NT 版数据库解密](https://blog.yllhwa.com/blog/android_qq_nt_database/)
- [SQLCipher API 文档](https://www.zetetic.net/sqlcipher/sqlcipher-api/)

## 许可证

本文档基于实际解密经验编写，供学习和研究使用。请遵守相关法律法规和 QQ 用户协议。

## 更新日志

- 2026-04-18: 初始版本，验证适用于 QQ NT 9.9.29
