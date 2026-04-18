#!/usr/bin/env bash
#
# QQ NT 数据库解密自动化脚本
# 用法: ./decrypt_qq_db.sh <QQ号> <密钥>
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查参数
if [ $# -lt 2 ]; then
    echo -e "${RED}用法: $0 <QQ号> <密钥>${NC}"
    echo "示例: $0 1497479966 \"a'~b]{jmezG49em]\""
    exit 1
fi

QQ_NUMBER=$1
DB_KEY=$2

# 配置路径
QQ_DB_PATH="C:/Users/$USER/Documents/Tencent Files/$QQ_NUMBER/nt_qq/nt_db/nt_msg.db"
WORK_DIR="./qq_decrypt_$QQ_NUMBER"
CLEAN_DB="$WORK_DIR/nt_msg_clean.db"
DECRYPTED_DB="$WORK_DIR/nt_msg_decrypted.db"
SQL_SCRIPT="$WORK_DIR/decrypt.sql"

echo -e "${GREEN}=== QQ NT 数据库解密工具 ===${NC}"
echo "QQ 号: $QQ_NUMBER"
echo "数据库: $QQ_DB_PATH"
echo ""

# 创建工作目录
mkdir -p "$WORK_DIR"

# 步骤 1: 检查数据库文件
echo -e "${YELLOW}[1/4] 检查数据库文件...${NC}"
if [ ! -f "$QQ_DB_PATH" ]; then
    echo -e "${RED}错误: 数据库文件不存在: $QQ_DB_PATH${NC}"
    exit 1
fi

DB_SIZE=$(stat -c%s "$QQ_DB_PATH" 2>/dev/null || stat -f%z "$QQ_DB_PATH" 2>/dev/null || echo "unknown")
echo "数据库大小: $DB_SIZE 字节"

# 步骤 2: 移除文件头
echo -e "${YELLOW}[2/4] 移除 1024 字节文件头...${NC}"
if command -v python3 &> /dev/null; then
    python3 -c "
with open('$QQ_DB_PATH', 'rb') as f:
    data = f.read()[1024:]
with open('$CLEAN_DB', 'wb') as f:
    f.write(data)
print('✓ 文件头已移除')
"
elif command -v python &> /dev/null; then
    python -c "
with open('$QQ_DB_PATH', 'rb') as f:
    data = f.read()[1024:]
with open('$CLEAN_DB', 'wb') as f:
    f.write(data)
print('✓ 文件头已移除')
"
else
    # 使用 tail 命令
    tail -c +1025 "$QQ_DB_PATH" > "$CLEAN_DB"
    echo "✓ 文件头已移除"
fi

# 步骤 3: 生成 SQL 脚本
echo -e "${YELLOW}[3/4] 生成解密脚本...${NC}"
cat > "$SQL_SCRIPT" << EOF
PRAGMA key = "$DB_KEY";
PRAGMA cipher_page_size = 4096;
PRAGMA kdf_iter = 4000;
PRAGMA cipher_hmac_algorithm = HMAC_SHA1;
PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512;
ATTACH DATABASE '$DECRYPTED_DB' AS plaintext KEY '';
SELECT sqlcipher_export('plaintext');
DETACH DATABASE plaintext;
EOF
echo "✓ SQL 脚本已生成"

# 步骤 4: 执行解密
echo -e "${YELLOW}[4/4] 执行解密...${NC}"
if command -v sqlcipher &> /dev/null; then
    sqlcipher "$CLEAN_DB" < "$SQL_SCRIPT"
elif [ -f "./sqlcipher.exe" ]; then
    ./sqlcipher.exe "$CLEAN_DB" < "$SQL_SCRIPT"
else
    echo -e "${RED}错误: 找不到 sqlcipher 命令${NC}"
    echo "请安装 sqlcipher 或将 sqlcipher.exe 放在当前目录"
    exit 1
fi

# 验证解密结果
if [ -f "$DECRYPTED_DB" ]; then
    DECRYPTED_SIZE=$(stat -c%s "$DECRYPTED_DB" 2>/dev/null || stat -f%z "$DECRYPTED_DB" 2>/dev/null || echo "unknown")
    echo -e "${GREEN}✓ 解密成功！${NC}"
    echo "解密后数据库: $DECRYPTED_DB"
    echo "文件大小: $DECRYPTED_SIZE 字节"

    # 统计消息数量
    echo ""
    echo -e "${YELLOW}统计消息数量...${NC}"
    if command -v sqlcipher &> /dev/null; then
        C2C_COUNT=$(sqlcipher "$DECRYPTED_DB" "SELECT COUNT(*) FROM c2c_msg_table" 2>/dev/null || echo "N/A")
        GROUP_COUNT=$(sqlcipher "$DECRYPTED_DB" "SELECT COUNT(*) FROM group_msg_table" 2>/dev/null || echo "N/A")
    elif [ -f "./sqlcipher.exe" ]; then
        C2C_COUNT=$(./sqlcipher.exe "$DECRYPTED_DB" "SELECT COUNT(*) FROM c2c_msg_table" 2>/dev/null || echo "N/A")
        GROUP_COUNT=$(./sqlcipher.exe "$DECRYPTED_DB" "SELECT COUNT(*) FROM group_msg_table" 2>/dev/null || echo "N/A")
    fi

    echo "私聊消息: $C2C_COUNT 条"
    echo "群聊消息: $GROUP_COUNT 条"
else
    echo -e "${RED}✗ 解密失败${NC}"
    echo "请检查密钥是否正确"
    exit 1
fi

echo ""
echo -e "${GREEN}=== 完成 ===${NC}"
