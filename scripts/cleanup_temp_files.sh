#!/bin/bash
# 整理桌面和项目临时文件

set -e

echo "=== 整理临时文件 ==="

# 创建归档目录
ARCHIVE_DIR="$HOME/Desktop/archived_$(date +%Y%m%d)"
VOILE_ARCHIVE="$HOME/Downloads/voile/.archive"

mkdir -p "$ARCHIVE_DIR"
mkdir -p "$VOILE_ARCHIVE"

echo "归档目录: $ARCHIVE_DIR"
echo "Voile 归档: $VOILE_ARCHIVE"
echo ""

# ============================================
# 1. 整理桌面文件
# ============================================

echo "1. 整理桌面文件..."

cd "$HOME/Desktop"

# Forgejo 相关文档（已完成部署，可以归档）
if ls forgejo*.txt FORGEJO*.txt 2>/dev/null; then
    echo "  归档 Forgejo 文档..."
    mkdir -p "$ARCHIVE_DIR/forgejo-docs"
    mv forgejo*.txt FORGEJO*.txt "$ARCHIVE_DIR/forgejo-docs/" 2>/dev/null || true
fi

# Gitea 相关文档
if ls gitea*.txt 2>/dev/null; then
    echo "  归档 Gitea 文档..."
    mkdir -p "$ARCHIVE_DIR/gitea-docs"
    mv gitea*.txt "$ARCHIVE_DIR/gitea-docs/" 2>/dev/null || true
fi

# n8n 脚本（已完成，可以归档）
if ls *n8n*.sh 2>/dev/null; then
    echo "  归档 n8n 脚本..."
    mkdir -p "$ARCHIVE_DIR/n8n-scripts"
    mv *n8n*.sh "$ARCHIVE_DIR/n8n-scripts/" 2>/dev/null || true
fi

# 空文件和测试文件
if [ -f "新建 文本文档.txt" ]; then
    echo "  删除空文件..."
    rm "新建 文本文档.txt" 2>/dev/null || true
fi

if [ -f "1.txt" ]; then
    echo "  删除测试文件..."
    rm "1.txt" 2>/dev/null || true
fi

# 保留的重要文档（不移动）
echo "  保留重要文档:"
echo "    - Claude Code 完整配置说明.txt"
echo "    - Claw Code 配置完成.txt"
echo "    - Multi-Agent Skill 说明.txt"
echo "    - github-recovery-codes.txt"

# ============================================
# 2. 整理 Voile 项目临时文件
# ============================================

echo ""
echo "2. 整理 Voile 项目临时文件..."

cd "$HOME/Downloads/voile"

# 临时 SQL 脚本（解密测试用，已完成）
if ls decrypt_*.sql 2>/dev/null; then
    echo "  归档临时 SQL 脚本..."
    mkdir -p "$VOILE_ARCHIVE/sql-tests"
    mv decrypt_commands.sql decrypt_commands_hex.sql decrypt_correct.sql \
       decrypt_raw.sql decrypt_v3.sql "$VOILE_ARCHIVE/sql-tests/" 2>/dev/null || true
    # 保留 decrypt_final.sql（最终版本）
    echo "    保留: decrypt_final.sql"
fi

# 临时 Python 脚本（测试版本）
echo "  归档临时 Python 脚本..."
mkdir -p "$VOILE_ARCHIVE/python-tests"

# 移动测试版本的解密脚本
if [ -f "decrypt_qq_manual.py" ]; then
    mv decrypt_qq_manual.py "$VOILE_ARCHIVE/python-tests/" 2>/dev/null || true
fi
if [ -f "decrypt_qq_simple.py" ]; then
    mv decrypt_qq_simple.py "$VOILE_ARCHIVE/python-tests/" 2>/dev/null || true
fi

# 移动临时测试脚本
if [ -f "test_weflow.sh" ]; then
    mv test_weflow.sh "$VOILE_ARCHIVE/python-tests/" 2>/dev/null || true
fi
if [ -f "test_weflow_api.py" ]; then
    mv test_weflow_api.py "$VOILE_ARCHIVE/python-tests/" 2>/dev/null || true
fi
if [ -f "collect_messages.py" ]; then
    mv collect_messages.py "$VOILE_ARCHIVE/python-tests/" 2>/dev/null || true
fi
if [ -f "update_config.py" ]; then
    mv update_config.py "$VOILE_ARCHIVE/python-tests/" 2>/dev/null || true
fi

# 保留的脚本（正式版本）
echo "  保留正式脚本:"
echo "    - scripts/decrypt_qq_db.py (正式版)"
echo "    - scripts/decrypt_qq_db.sh (正式版)"
echo "    - decrypt_qq_db.py (临时位置，待移动)"
echo "    - import_qq_history.py (待完善)"

# ============================================
# 3. 清理解密临时数据
# ============================================

echo ""
echo "3. 清理解密临时数据..."

# 检查解密工作目录
if [ -d "qq_decrypt_1497479966" ]; then
    SIZE=$(du -sh qq_decrypt_1497479966 | cut -f1)
    echo "  发现 QQ 解密数据: $SIZE"
    echo "  建议: 数据已导入后可以删除"
    echo "  命令: rm -rf qq_decrypt_1497479966"
fi

# 检查临时数据库文件
if ls nt_msg*.db 2>/dev/null; then
    echo "  发现临时数据库文件:"
    ls -lh nt_msg*.db
    echo "  建议: 已完成解密可以删除"
fi

# ============================================
# 4. 更新 .gitignore
# ============================================

echo ""
echo "4. 更新 .gitignore..."

# 确保临时文件被忽略
cat >> .gitignore << 'EOF'

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
EOF

echo "  已更新 .gitignore"

# ============================================
# 5. 生成整理报告
# ============================================

echo ""
echo "=== 整理完成 ==="
echo ""
echo "归档位置:"
echo "  桌面归档: $ARCHIVE_DIR"
echo "  Voile 归档: $VOILE_ARCHIVE"
echo ""
echo "保留的重要文件:"
echo "  桌面:"
echo "    - Claude Code 完整配置说明.txt"
echo "    - Claw Code 配置完成.txt"
echo "    - Multi-Agent Skill 说明.txt"
echo "    - github-recovery-codes.txt"
echo ""
echo "  Voile 项目:"
echo "    - scripts/decrypt_qq_db.py (正式版)"
echo "    - scripts/decrypt_qq_db.sh (正式版)"
echo "    - decrypt_final.sql (最终 SQL)"
echo ""
echo "待处理:"
echo "  1. 移动 decrypt_qq_db.py 到 scripts/ (如果需要)"
echo "  2. 完善 import_qq_history.py"
echo "  3. 删除解密临时数据 (qq_decrypt_1497479966/)"
echo ""
echo "查看归档:"
echo "  ls -la $ARCHIVE_DIR"
echo "  ls -la $VOILE_ARCHIVE"
