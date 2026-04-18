#!/usr/bin/env python3
"""
QQ NT 数据库解密工具
支持 Windows/Linux/macOS

用法:
    python decrypt_qq_db.py <QQ号> <密钥>
    python decrypt_qq_db.py 1497479966 "a'~b]{jmezG49em]"

依赖:
    pip install pysqlcipher3  # 可选，如果安装失败会使用 sqlcipher 命令行
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


class Colors:
    """终端颜色"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color


def print_colored(text, color):
    """彩色打印"""
    print(f"{color}{text}{Colors.NC}")


def find_qq_db(qq_number):
    """查找 QQ 数据库文件"""
    # Windows 路径
    if sys.platform == 'win32':
        user_home = os.path.expanduser('~')
        db_path = Path(user_home) / 'Documents' / 'Tencent Files' / qq_number / 'nt_qq' / 'nt_db' / 'nt_msg.db'
        if db_path.exists():
            return str(db_path)

    # 手动指定路径
    print_colored(f"未找到 QQ 数据库，请手动指定路径", Colors.YELLOW)
    return None


def remove_header(input_path, output_path):
    """移除数据库文件的 1024 字节头部"""
    print_colored("[2/4] 移除 1024 字节文件头...", Colors.YELLOW)

    with open(input_path, 'rb') as f:
        data = f.read()[1024:]

    with open(output_path, 'wb') as f:
        f.write(data)

    print("✓ 文件头已移除")


def create_decrypt_sql(output_path, db_key, decrypted_db):
    """生成解密 SQL 脚本"""
    print_colored("[3/4] 生成解密脚本...", Colors.YELLOW)

    sql_content = f"""PRAGMA key = "{db_key}";
PRAGMA cipher_page_size = 4096;
PRAGMA kdf_iter = 4000;
PRAGMA cipher_hmac_algorithm = HMAC_SHA1;
PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512;
ATTACH DATABASE '{decrypted_db}' AS plaintext KEY '';
SELECT sqlcipher_export('plaintext');
DETACH DATABASE plaintext;
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(sql_content)

    print("✓ SQL 脚本已生成")


def decrypt_with_cli(clean_db, sql_script):
    """使用 sqlcipher 命令行工具解密"""
    # 查找 sqlcipher 可执行文件
    sqlcipher_cmd = None

    # 检查系统路径
    if shutil.which('sqlcipher'):
        sqlcipher_cmd = 'sqlcipher'
    # 检查当前目录
    elif os.path.exists('./sqlcipher.exe'):
        sqlcipher_cmd = './sqlcipher.exe'
    elif os.path.exists('./sqlcipher'):
        sqlcipher_cmd = './sqlcipher'

    if not sqlcipher_cmd:
        print_colored("错误: 找不到 sqlcipher 命令", Colors.RED)
        print("请安装 sqlcipher 或将可执行文件放在当前目录")
        return False

    # 执行解密
    with open(sql_script, 'r', encoding='utf-8') as f:
        result = subprocess.run(
            [sqlcipher_cmd, clean_db],
            stdin=f,
            capture_output=True,
            text=True
        )

    if result.returncode != 0:
        print_colored(f"解密失败: {result.stderr}", Colors.RED)
        return False

    return True


def decrypt_with_python(clean_db, db_key, decrypted_db):
    """使用 pysqlcipher3 解密"""
    try:
        from pysqlcipher3 import dbapi2 as sqlcipher
    except ImportError:
        print_colored("pysqlcipher3 未安装，尝试使用命令行工具...", Colors.YELLOW)
        return False

    conn = sqlcipher.connect(clean_db)
    cursor = conn.cursor()

    # 设置解密参数
    cursor.execute(f"PRAGMA key = '{db_key}'")
    cursor.execute("PRAGMA cipher_page_size = 4096")
    cursor.execute("PRAGMA kdf_iter = 4000")
    cursor.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA1")
    cursor.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")

    # 导出到未加密数据库
    cursor.execute(f"ATTACH DATABASE '{decrypted_db}' AS plaintext KEY ''")
    cursor.execute("SELECT sqlcipher_export('plaintext')")
    cursor.execute("DETACH DATABASE plaintext")

    conn.close()
    return True


def get_message_count(db_path):
    """统计消息数量"""
    try:
        # 尝试使用 sqlite3
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM c2c_msg_table")
        c2c_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM group_msg_table")
        group_count = cursor.fetchone()[0]

        conn.close()
        return c2c_count, group_count
    except Exception as e:
        return None, None


def main():
    """主函数"""
    print_colored("=== QQ NT 数据库解密工具 ===", Colors.GREEN)

    # 检查参数
    if len(sys.argv) < 3:
        print_colored("用法: python decrypt_qq_db.py <QQ号> <密钥>", Colors.RED)
        print('示例: python decrypt_qq_db.py 1497479966 "a\'~b]{jmezG49em]"')
        sys.exit(1)

    qq_number = sys.argv[1]
    db_key = sys.argv[2]

    print(f"QQ 号: {qq_number}")
    print()

    # 步骤 1: 查找数据库
    print_colored("[1/4] 查找数据库文件...", Colors.YELLOW)
    db_path = find_qq_db(qq_number)

    if not db_path:
        db_path = input("请输入数据库文件路径: ").strip()
        if not os.path.exists(db_path):
            print_colored(f"错误: 文件不存在: {db_path}", Colors.RED)
            sys.exit(1)

    db_size = os.path.getsize(db_path)
    print(f"数据库: {db_path}")
    print(f"大小: {db_size:,} 字节")

    # 创建工作目录
    work_dir = Path(f"./qq_decrypt_{qq_number}")
    work_dir.mkdir(exist_ok=True)

    clean_db = work_dir / "nt_msg_clean.db"
    decrypted_db = work_dir / "nt_msg_decrypted.db"
    sql_script = work_dir / "decrypt.sql"

    # 步骤 2: 移除文件头
    remove_header(db_path, clean_db)

    # 步骤 3: 生成 SQL 脚本
    create_decrypt_sql(sql_script, db_key, decrypted_db)

    # 步骤 4: 执行解密
    print_colored("[4/4] 执行解密...", Colors.YELLOW)

    # 先尝试 Python 方式
    success = decrypt_with_python(clean_db, db_key, decrypted_db)

    # 如果失败，尝试命令行方式
    if not success:
        success = decrypt_with_cli(clean_db, sql_script)

    if not success:
        print_colored("解密失败", Colors.RED)
        sys.exit(1)

    # 验证结果
    if not decrypted_db.exists():
        print_colored("解密失败: 未生成输出文件", Colors.RED)
        sys.exit(1)

    decrypted_size = decrypted_db.stat().st_size
    print_colored("✓ 解密成功！", Colors.GREEN)
    print(f"解密后数据库: {decrypted_db}")
    print(f"文件大小: {decrypted_size:,} 字节")

    # 统计消息数量
    print()
    print_colored("统计消息数量...", Colors.YELLOW)
    c2c_count, group_count = get_message_count(decrypted_db)

    if c2c_count is not None:
        print(f"私聊消息: {c2c_count:,} 条")
        print(f"群聊消息: {group_count:,} 条")
        print(f"总计: {c2c_count + group_count:,} 条")

    print()
    print_colored("=== 完成 ===", Colors.GREEN)


if __name__ == "__main__":
    main()
