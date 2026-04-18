# QQ 数据库解密 - 快速开始

## 一键解密

```bash
# 克隆仓库
git clone https://github.com/2233admin/voile.git
cd voile

# 运行解密脚本
python scripts/decrypt_qq_db.py <你的QQ号> <密钥>
```

## 获取密钥

1. 克隆密钥提取工具：
```bash
git clone https://github.com/yllhwa/qq-win-db-key.git
cd qq-win-db-key
```

2. 以管理员身份运行 PowerShell 脚本：
```powershell
.\windows_ntqq_get_key.ps1
```

3. 按提示登录 QQ，脚本会自动提取密钥

## 示例

```bash
# 假设你的 QQ 号是 1497479966，密钥是 a'~b]{jmezG49em]
python scripts/decrypt_qq_db.py 1497479966 "a'~b]{jmezG49em]"
```

输出：
```
=== QQ NT 数据库解密工具 ===
QQ 号: 1497479966

[1/4] 查找数据库文件...
数据库: C:\Users\...\nt_msg.db
大小: 374,000,000 字节

[2/4] 移除 1024 字节文件头...
✓ 文件头已移除

[3/4] 生成解密脚本...
✓ SQL 脚本已生成

[4/4] 执行解密...
✓ 解密成功！
解密后数据库: ./qq_decrypt_1497479966/nt_msg_decrypted.db
文件大小: 358,000,000 字节

统计消息数量...
私聊消息: 12,602 条
群聊消息: 392,775 条
总计: 405,377 条

=== 完成 ===
```

## 详细文档

查看 [docs/QQ_DATABASE_DECRYPT.md](../docs/QQ_DATABASE_DECRYPT.md) 获取：
- 完整的技术细节
- 数据库结构说明
- 常见问题解答
- 手动解密步骤

## 故障排除

### 问题：HMAC 校验失败
**解决**：确保密钥正确，并且已移除 1024 字节文件头

### 问题：找不到数据库文件
**解决**：手动指定数据库路径
```bash
python scripts/decrypt_qq_db.py 1497479966 "密钥" --db-path "C:\path\to\nt_msg.db"
```

### 问题：sqlcipher 命令未找到
**解决**：
- Windows: 下载 [sqlcipher.exe](https://www.zetetic.net/sqlcipher/downloads/) 放到当前目录
- Linux: `sudo apt install sqlcipher`
- macOS: `brew install sqlcipher`

## 团队协作

解密后的数据库可以：
1. 导入到 voile 的 PostgreSQL 数据库
2. 使用 DB Browser for SQLite 查看
3. 编写 SQL 查询分析消息

## 安全提示

- 密钥和解密后的数据库包含敏感信息
- 不要将密钥提交到 Git
- 解密后的数据库建议加密存储
- 遵守相关法律法规和用户协议
