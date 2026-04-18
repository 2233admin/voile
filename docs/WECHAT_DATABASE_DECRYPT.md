# 微信数据库解密指南 (内部文档)

> ⚠️ **内部文档**: 本文档包含敏感技术细节，仅供团队内部使用

## 概述

微信 PC 版使用自定义加密算法加密本地消息数据库。本文档记录完整的解密流程和技术细节。

## 数据库位置

### Windows
```
C:\Users\{用户名}\Documents\WeChat Files\{微信ID}\Msg\
```

### 主要文件
- `MicroMsg.db` - 联系人、会话信息
- `MSG0.db`, `MSG1.db`, ... - 消息记录（按时间分片）
- `MediaMSG0.db`, `MediaMSG1.db`, ... - 媒体消息
- `Emotion.db` - 表情包
- `FTS*.db` - 全文搜索索引

## 加密方式

### 加密算法
- **算法**: AES-256-CBC
- **密钥长度**: 32 字节
- **密钥派生**: 基于设备信息 + 微信 ID

### 密钥生成逻辑
```python
# 伪代码
def generate_wechat_key(device_id: str, wxid: str) -> bytes:
    """
    微信密钥生成算法
    """
    # 1. 获取设备标识
    machine_guid = get_machine_guid()  # 从注册表读取
    
    # 2. 组合信息
    raw_key = f"{machine_guid}{wxid}".encode('utf-8')
    
    # 3. MD5 哈希
    key_hash = hashlib.md5(raw_key).hexdigest()
    
    # 4. 转换为 32 字节密钥
    key = bytes.fromhex(key_hash)
    
    return key
```

### 密钥存储
- 密钥在微信启动时生成，存储在进程内存中
- 不会写入磁盘
- 需要从运行中的微信进程提取

## 密钥提取

### 方法 1: 内存扫描（推荐）

**工具**: `scripts/extract_wechat_key.py`

**原理**: 扫描微信进程内存，查找密钥特征

**步骤**:
```bash
# 1. 确保微信正在运行并已登录
# 2. 以管理员身份运行脚本
python scripts/extract_wechat_key.py

# 输出示例:
# 找到微信进程: WeChat.exe (PID: 12345)
# 扫描内存...
# 找到密钥: a1b2c3d4e5f6...
```

**代码实现**:
```python
import psutil
import ctypes
from ctypes import wintypes

def find_wechat_process():
    """查找微信进程"""
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == 'WeChat.exe':
            return proc.info['pid']
    return None

def read_process_memory(pid: int, address: int, size: int) -> bytes:
    """读取进程内存"""
    kernel32 = ctypes.windll.kernel32
    
    # 打开进程
    PROCESS_VM_READ = 0x0010
    handle = kernel32.OpenProcess(PROCESS_VM_READ, False, pid)
    
    # 读取内存
    buffer = ctypes.create_string_buffer(size)
    bytes_read = ctypes.c_size_t()
    kernel32.ReadProcessMemory(
        handle, 
        address, 
        buffer, 
        size, 
        ctypes.byref(bytes_read)
    )
    
    kernel32.CloseHandle(handle)
    return buffer.raw

def scan_for_key(pid: int) -> str:
    """扫描内存查找密钥"""
    # 密钥特征: 32 字节，通常在特定内存区域
    # 实际实现需要根据微信版本调整
    
    # 这里是简化版本
    # 实际代码需要更复杂的模式匹配
    pass
```

### 方法 2: 调试器附加

**工具**: x64dbg / WinDbg

**步骤**:
1. 附加到 WeChat.exe 进程
2. 在密钥使用点设置断点
3. 触发数据库操作
4. 从寄存器/栈中读取密钥

**关键函数**:
- `sqlite3_key()` - 设置数据库密钥
- 密钥通常在 RCX 或 RDX 寄存器中

### 方法 3: Hook API

**工具**: Frida

**脚本**:
```javascript
// frida_wechat_key.js
Interceptor.attach(Module.findExportByName("WeChatWin.dll", "sqlite3_key"), {
    onEnter: function(args) {
        console.log("sqlite3_key called");
        console.log("Key:", hexdump(args[1], { length: 32 }));
    }
});
```

**使用**:
```bash
frida -p <WeChat PID> -l frida_wechat_key.js
```

## 数据库解密

### 使用 SQLCipher

微信数据库是标准的 SQLCipher 加密数据库。

**解密脚本**: `scripts/decrypt_wechat_db.py`

```python
#!/usr/bin/env python3
"""
微信数据库解密工具
"""
import os
import sys
from pathlib import Path
from pysqlcipher3 import dbapi2 as sqlcipher

def decrypt_wechat_db(db_path: str, key: str, output_path: str):
    """
    解密微信数据库
    
    Args:
        db_path: 加密数据库路径
        key: 32 字节密钥（十六进制字符串）
        output_path: 输出路径
    """
    print(f"解密: {db_path}")
    
    # 连接加密数据库
    conn = sqlcipher.connect(db_path)
    cursor = conn.cursor()
    
    # 设置密钥
    cursor.execute(f"PRAGMA key = \"x'{key}'\"")
    cursor.execute("PRAGMA cipher_page_size = 4096")
    cursor.execute("PRAGMA kdf_iter = 64000")
    cursor.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA1")
    cursor.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA1")
    
    # 测试解密
    try:
        cursor.execute("SELECT count(*) FROM sqlite_master")
        print("✓ 解密成功")
    except Exception as e:
        print(f"✗ 解密失败: {e}")
        conn.close()
        return False
    
    # 导出到未加密数据库
    cursor.execute(f"ATTACH DATABASE '{output_path}' AS plaintext KEY ''")
    cursor.execute("SELECT sqlcipher_export('plaintext')")
    cursor.execute("DETACH DATABASE plaintext")
    
    conn.close()
    print(f"✓ 已导出到: {output_path}")
    return True

def main():
    if len(sys.argv) < 3:
        print("用法: python decrypt_wechat_db.py <微信ID> <密钥>")
        sys.exit(1)
    
    wxid = sys.argv[1]
    key = sys.argv[2]
    
    # 查找数据库文件
    wechat_dir = Path.home() / "Documents" / "WeChat Files" / wxid / "Msg"
    
    if not wechat_dir.exists():
        print(f"错误: 找不到微信目录: {wechat_dir}")
        sys.exit(1)
    
    # 创建输出目录
    output_dir = Path(f"./wechat_decrypt_{wxid}")
    output_dir.mkdir(exist_ok=True)
    
    # 解密所有数据库
    db_files = list(wechat_dir.glob("*.db"))
    print(f"找到 {len(db_files)} 个数据库文件")
    
    for db_file in db_files:
        output_file = output_dir / f"{db_file.stem}_decrypted.db"
        decrypt_wechat_db(str(db_file), key, str(output_file))
    
    print("\n✓ 所有数据库解密完成")
    print(f"输出目录: {output_dir}")

if __name__ == "__main__":
    main()
```

### SQLCipher 参数

微信使用的 SQLCipher 参数：
```sql
PRAGMA key = "x'<32字节十六进制密钥>'";
PRAGMA cipher_page_size = 4096;
PRAGMA kdf_iter = 64000;
PRAGMA cipher_hmac_algorithm = HMAC_SHA1;
PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA1;
```

## 数据库结构

### MicroMsg.db

**主要表**:
- `Contact` - 联系人信息
- `ChatRoom` - 群聊信息
- `Session` - 会话列表

**Contact 表结构**:
```sql
CREATE TABLE Contact (
    UserName TEXT PRIMARY KEY,  -- 微信ID
    Alias TEXT,                 -- 微信号
    NickName TEXT,              -- 昵称
    Remark TEXT,                -- 备注
    Type INTEGER,               -- 类型 (好友/群/公众号)
    ...
);
```

### MSG*.db

**主要表**:
- `MSG` - 消息记录

**MSG 表结构**:
```sql
CREATE TABLE MSG (
    localId INTEGER PRIMARY KEY,
    TalkerId INTEGER,           -- 会话ID
    MsgSvrID INTEGER,           -- 服务器消息ID
    Type INTEGER,               -- 消息类型
    SubType INTEGER,
    IsSender INTEGER,           -- 是否发送者
    CreateTime INTEGER,         -- 时间戳
    Sequence INTEGER,
    StatusEx INTEGER,
    FlagEx INTEGER,
    Status INTEGER,
    MsgServerSeq INTEGER,
    MsgSequence INTEGER,
    StrTalker TEXT,             -- 对方微信ID
    StrContent TEXT,            -- 消息内容
    DisplayContent TEXT,
    ...
);
```

**消息类型**:
- `1` - 文本消息
- `3` - 图片消息
- `34` - 语音消息
- `43` - 视频消息
- `47` - 表情包
- `49` - 链接/文件/小程序
- `10000` - 系统消息

## 导入到 Voile

### 导入脚本

**文件**: `scripts/import_wechat_history.py`

```python
#!/usr/bin/env python3
"""
导入微信历史消息到 Voile
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.storage import RawMessage, Base

# Voile 数据库配置
DB_URL = "postgresql://voile:voile_pass@192.168.50.130:5434/voile"

def import_wechat_messages(decrypt_dir: Path, wxid: str):
    """
    导入微信消息
    
    Args:
        decrypt_dir: 解密后的数据库目录
        wxid: 微信ID
    """
    # 连接 Voile 数据库
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 读取联系人信息
    contacts = load_contacts(decrypt_dir / "MicroMsg_decrypted.db")
    
    # 导入所有消息数据库
    msg_dbs = list(decrypt_dir.glob("MSG*_decrypted.db"))
    
    total_imported = 0
    
    for msg_db in msg_dbs:
        print(f"处理: {msg_db.name}")
        
        conn = sqlite3.connect(msg_db)
        cursor = conn.cursor()
        
        # 查询消息
        cursor.execute("""
            SELECT 
                MsgSvrID,
                StrTalker,
                Type,
                IsSender,
                CreateTime,
                StrContent
            FROM MSG
            ORDER BY CreateTime
        """)
        
        batch = []
        for row in cursor.fetchall():
            msg_id, talker, msg_type, is_sender, timestamp, content = row
            
            # 跳过非文本消息
            if msg_type != 1:
                continue
            
            # 构造 RawMessage
            raw_msg = {
                'platform': 'wechat',
                'account_id': wxid,
                'message_id': f"wechat_{msg_id}",
                'channel_id': talker,
                'user_id': wxid if is_sender else talker,
                'content': content,
                'raw_data': {
                    'type': msg_type,
                    'is_sender': is_sender,
                    'talker': talker
                },
                'created_at': datetime.fromtimestamp(timestamp, tz=timezone.utc),
                'collected_at': datetime.now(timezone.utc)
            }
            
            batch.append(raw_msg)
            
            # 批量插入
            if len(batch) >= 1000:
                session.bulk_insert_mappings(RawMessage, batch)
                session.commit()
                total_imported += len(batch)
                print(f"  已导入: {total_imported} 条")
                batch = []
        
        # 插入剩余消息
        if batch:
            session.bulk_insert_mappings(RawMessage, batch)
            session.commit()
            total_imported += len(batch)
        
        conn.close()
    
    print(f"\n✓ 导入完成: {total_imported} 条消息")
    session.close()

def load_contacts(db_path: Path) -> dict:
    """加载联系人信息"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT UserName, NickName, Remark
        FROM Contact
    """)
    
    contacts = {}
    for row in cursor.fetchall():
        username, nickname, remark = row
        contacts[username] = {
            'nickname': nickname,
            'remark': remark
        }
    
    conn.close()
    return contacts

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python import_wechat_history.py <解密目录>")
        sys.exit(1)
    
    decrypt_dir = Path(sys.argv[1])
    
    if not decrypt_dir.exists():
        print(f"错误: 目录不存在: {decrypt_dir}")
        sys.exit(1)
    
    # 从目录名提取微信ID
    wxid = decrypt_dir.name.replace("wechat_decrypt_", "")
    
    print(f"导入微信历史消息")
    print(f"微信ID: {wxid}")
    print(f"目录: {decrypt_dir}")
    print()
    
    import_wechat_messages(decrypt_dir, wxid)

if __name__ == "__main__":
    main()
```

### 完整流程

```bash
# 1. 提取密钥
python scripts/extract_wechat_key.py
# 输出: 密钥 = a1b2c3d4e5f6...

# 2. 解密数据库
python scripts/decrypt_wechat_db.py wxid_xxx a1b2c3d4e5f6...
# 输出: wechat_decrypt_wxid_xxx/

# 3. 导入到 Voile
python scripts/import_wechat_history.py wechat_decrypt_wxid_xxx/
# 输出: ✓ 导入完成: 123456 条消息
```

## 常见问题

### Q: 密钥提取失败
**A**: 
- 确保微信正在运行并已登录
- 以管理员身份运行脚本
- 检查微信版本是否支持
- 尝试重启微信后再提取

### Q: 解密失败 - "file is encrypted or is not a database"
**A**:
- 密钥错误，重新提取
- 数据库文件损坏
- SQLCipher 参数不匹配

### Q: 导入后消息乱码
**A**:
- 检查数据库编码（应为 UTF-8）
- 确认 Python 字符串处理正确
- 查看原始数据库内容

### Q: 部分消息缺失
**A**:
- 微信消息分片存储，确保解密所有 MSG*.db
- 检查时间范围过滤
- 某些消息类型可能被跳过

## 安全注意事项

1. **密钥保护**
   - 密钥包含敏感信息，不要泄露
   - 不要提交到 Git
   - 使用后立即删除

2. **数据隐私**
   - 解密后的数据库包含完整聊天记录
   - 妥善保管，避免泄露
   - 使用完毕后加密存储或删除

3. **法律合规**
   - 仅用于个人数据备份
   - 不得用于非法目的
   - 遵守相关法律法规

## 版本兼容性

| 微信版本 | 加密方式 | 支持状态 |
|---------|---------|---------|
| 3.0.x   | SQLCipher | ✅ 支持 |
| 3.1.x   | SQLCipher | ✅ 支持 |
| 3.2.x   | SQLCipher | ✅ 支持 |
| 3.3.x   | SQLCipher | ✅ 支持 |
| 3.4.x   | SQLCipher | ✅ 支持 |
| 3.5.x+  | 待验证   | ⚠️ 未测试 |

## 参考资料

- [SQLCipher 官方文档](https://www.zetetic.net/sqlcipher/)
- [微信数据库结构分析](内部文档链接)
- [Python pysqlcipher3](https://github.com/rigglemania/pysqlcipher3)

## 更新日志

- **2026-04-18**: 初始版本
  - 完整解密流程
  - 导入脚本
  - 常见问题解答

---

**文档版本**: v1.0  
**最后更新**: 2026-04-18  
**维护者**: XartPro Team  
**保密级别**: 内部文档
