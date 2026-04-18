# 临时文件整理报告

**整理日期**: 2026-04-18  
**执行脚本**: `scripts/cleanup_temp_files.sh`

## 整理概览

### 归档位置

1. **桌面归档**: `C:\Users\Administrator\Desktop\archived_20260418\`
2. **Voile 归档**: `C:\Users\Administrator\Downloads\voile\.archive\`

## 整理详情

### 1. 桌面文件

#### 已归档

**Forgejo 文档** (`archived_20260418/forgejo-docs/`):
- `FORGEJO-DEPLOYMENT-FINAL.txt`
- `forgejo-final-status.txt`
- `forgejo-login-info.txt`
- `forgejo-quick-start.txt`
- `forgejo-ready.txt`

**Gitea 文档** (`archived_20260418/gitea-docs/`):
- `gitea-deploy-oneliner.txt`

**n8n 脚本** (`archived_20260418/n8n-scripts/`):
- `import-n8n-workflows.sh`
- `test-n8n-workflows.sh`

#### 已删除

- `新建 文本文档.txt` (空文件)
- `1.txt` (测试文件)

#### 保留

重要配置文档（保留在桌面）:
- `Claude Code 完整配置说明.txt`
- `Claw Code 配置完成.txt`
- `Multi-Agent Skill 说明.txt`
- `github-recovery-codes.txt`

### 2. Voile 项目文件

#### 已归档

**临时 SQL 脚本** (`.archive/sql-tests/`):
- `decrypt_commands.sql`
- `decrypt_commands_hex.sql`
- `decrypt_correct.sql`
- `decrypt_raw.sql`
- `decrypt_v3.sql`

**临时 Python 脚本** (`.archive/python-tests/`):
- `decrypt_qq_db.py` (根目录临时版本)
- `decrypt_qq_manual.py`
- `decrypt_qq_simple.py`
- `test_weflow.sh`
- `test_weflow_api.py`
- `collect_messages.py`
- `update_config.py`

**临时数据库** (`.archive/`):
- `nt_msg_clean.db` (374MB)
- `nt_msg_decrypted.db` (358MB)

#### 保留

**正式脚本**:
- `scripts/decrypt_qq_db.py` - QQ 解密工具（正式版）
- `scripts/decrypt_qq_db.sh` - Bash 版本
- `scripts/cleanup_temp_files.sh` - 整理脚本
- `decrypt_final.sql` - 最终 SQL 脚本

**待完善脚本**:
- `import_qq_history.py` - 历史消息导入（待完善）
- `query.py` - 查询工具
- `run.py` - 运行脚本
- `smoke_test.py` - 冒烟测试

### 3. .gitignore 更新

新增忽略规则:
```gitignore
# 临时归档
.archive/

# 临时脚本（根目录）
/decrypt_*.sql
/decrypt_*.py
/test_*.py
/test_*.sh
/collect_*.py
/update_*.py
/import_*.py
```

## 空间释放

### 桌面

- **归档文件**: ~15 个文件
- **删除文件**: 2 个
- **保留文件**: 4 个重要配置文档

### Voile 项目

- **归档脚本**: 11 个
- **归档数据库**: 732 MB (nt_msg_clean.db + nt_msg_decrypted.db)
- **保留脚本**: 8 个

## 后续建议

### 可以删除的数据

如果已完成导入，可以删除以下大文件：

```bash
# 删除归档的数据库（732 MB）
rm -rf ~/Downloads/voile/.archive/nt_msg*.db

# 删除解密工作目录（如果存在）
rm -rf ~/Downloads/voile/qq_decrypt_1497479966/
```

### 需要完善的脚本

1. **import_qq_history.py**
   - 当前状态: 基础框架
   - 需要: 完善导入逻辑
   - 优先级: 高

2. **微信相关脚本**
   - 需要创建: `extract_wechat_key.py`
   - 需要创建: `decrypt_wechat_db.py`
   - 需要创建: `import_wechat_history.py`
   - 优先级: 中

### 定期整理

建议每周运行一次整理脚本:

```bash
cd ~/Downloads/voile
bash scripts/cleanup_temp_files.sh
```

## 文件位置快速参考

### 重要文档

| 文档 | 位置 |
|------|------|
| Claude Code 配置 | `~/Desktop/Claude Code 完整配置说明.txt` |
| GitHub 恢复码 | `~/Desktop/github-recovery-codes.txt` |
| Voile 维护指南 | `~/Downloads/voile/docs/MAINTENANCE_GUIDE.md` |
| 运维手册 | `~/Downloads/voile/docs/OPERATIONS_MANUAL.md` |

### 正式工具

| 工具 | 位置 |
|------|------|
| QQ 解密 (Python) | `~/Downloads/voile/scripts/decrypt_qq_db.py` |
| QQ 解密 (Bash) | `~/Downloads/voile/scripts/decrypt_qq_db.sh` |
| 整理脚本 | `~/Downloads/voile/scripts/cleanup_temp_files.sh` |

### 归档数据

| 类型 | 位置 |
|------|------|
| 桌面归档 | `~/Desktop/archived_20260418/` |
| Voile 归档 | `~/Downloads/voile/.archive/` |

## 恢复方法

如果需要恢复归档的文件:

```bash
# 查看归档内容
ls -la ~/Desktop/archived_20260418/
ls -la ~/Downloads/voile/.archive/

# 恢复特定文件
cp ~/Desktop/archived_20260418/forgejo-docs/forgejo-ready.txt ~/Desktop/
cp ~/Downloads/voile/.archive/python-tests/test_weflow.py ~/Downloads/voile/
```

## Git 提交

```
e861a9e chore: 添加临时文件整理脚本并更新 gitignore
```

---

**整理人**: Claude Code  
**审核**: 待审核  
**下次整理**: 2026-04-25 (建议)
