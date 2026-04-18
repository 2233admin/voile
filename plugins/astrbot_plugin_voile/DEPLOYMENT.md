# AstrBot 部署配置示例

## Docker Compose 配置

```yaml
version: '3.8'

services:
  astrbot:
    image: soulter/astrbot:latest
    container_name: astrbot
    restart: unless-stopped
    volumes:
      - ./astrbot/data:/app/data
      - ./astrbot/plugins:/app/plugins
      - ./voile:/voile  # 挂载 voile 代码
    environment:
      # Voile 配置
      - VOILE_DB_URL=postgresql://voile:voile_pass@postgres:5432/voile
      - VOILE_REDIS_URL=redis://redis:6379/0
      
      # AstrBot 配置
      - ASTRBOT_CONFIG_PATH=/app/data/config.json
    depends_on:
      - postgres
      - redis
    networks:
      - voile_network

  postgres:
    image: postgres:15
    container_name: voile_postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=voile
      - POSTGRES_PASSWORD=voile_pass
      - POSTGRES_DB=voile
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5434:5432"
    networks:
      - voile_network

  redis:
    image: redis:7-alpine
    container_name: voile_redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - voile_network

volumes:
  postgres_data:
  redis_data:

networks:
  voile_network:
    driver: bridge
```

## AstrBot 配置文件

`astrbot/data/config.json`:

```json
{
  "platform": {
    "aiocqhttp": {
      "enable": true,
      "host": "0.0.0.0",
      "port": 8080,
      "access_token": "",
      "secret": ""
    }
  },
  "plugins": {
    "voile_sink": {
      "enable": true,
      "config": {}
    }
  }
}
```

## 环境变量文件

`.env`:

```bash
# Voile 数据库
VOILE_DB_URL=postgresql://voile:voile_pass@192.168.50.130:5434/voile

# Voile Redis
VOILE_REDIS_URL=redis://192.168.50.130:6379/0

# PostgreSQL
POSTGRES_USER=voile
POSTGRES_PASSWORD=voile_pass
POSTGRES_DB=voile

# AstrBot
ASTRBOT_LOG_LEVEL=INFO
```

## NapCatQQ 配置

`napcat/config/onebot11.json`:

```json
{
  "http": {
    "enable": true,
    "host": "0.0.0.0",
    "port": 3000,
    "secret": "",
    "enableHeart": true,
    "enablePost": true,
    "postUrls": [
      "http://astrbot:8080"
    ]
  },
  "ws": {
    "enable": false
  },
  "reverseWs": {
    "enable": false
  },
  "debug": false,
  "heartInterval": 30000,
  "messagePostFormat": "array",
  "enableLocalFile2Url": true,
  "musicSignUrl": "",
  "reportSelfMessage": false,
  "token": ""
}
```

## 完整部署脚本

`deploy.sh`:

```bash
#!/bin/bash
set -e

echo "=== Voile + AstrBot 部署脚本 ==="

# 1. 克隆仓库
if [ ! -d "voile" ]; then
    echo "克隆 Voile 仓库..."
    git clone http://192.168.50.130:3000/xartpro/voile.git
fi

cd voile

# 2. 创建目录结构
echo "创建目录结构..."
mkdir -p astrbot/data
mkdir -p astrbot/plugins
mkdir -p napcat/config

# 3. 复制插件
echo "复制 AstrBot 插件..."
cp -r plugins/astrbot_plugin_voile astrbot/plugins/

# 4. 安装 Voile core
echo "安装 Voile core..."
pip install -e .

# 5. 创建配置文件
echo "创建配置文件..."
cat > .env << EOF
VOILE_DB_URL=postgresql://voile:voile_pass@postgres:5432/voile
VOILE_REDIS_URL=redis://redis:6379/0
POSTGRES_USER=voile
POSTGRES_PASSWORD=voile_pass
POSTGRES_DB=voile
EOF

# 6. 启动服务
echo "启动服务..."
docker compose up -d

# 7. 等待数据库就绪
echo "等待数据库就绪..."
sleep 10

# 8. 初始化数据库
echo "初始化数据库..."
python -c "
from core.storage.db import Database
db = Database('postgresql://voile:voile_pass@localhost:5434/voile')
print('数据库初始化完成')
"

# 9. 检查服务状态
echo "检查服务状态..."
docker compose ps

echo ""
echo "=== 部署完成 ==="
echo "AstrBot: http://localhost:8080"
echo "PostgreSQL: localhost:5434"
echo "Redis: localhost:6379"
echo ""
echo "查看日志: docker compose logs -f astrbot"
```

## 健康检查脚本

`health_check.sh`:

```bash
#!/bin/bash

echo "=== Voile 健康检查 ==="

# 检查 Docker 容器
echo "1. 检查容器状态..."
docker compose ps

# 检查数据库连接
echo ""
echo "2. 检查数据库连接..."
psql -h localhost -p 5434 -U voile -d voile -c "SELECT COUNT(*) FROM messages;" 2>&1

# 检查 Redis 连接
echo ""
echo "3. 检查 Redis 连接..."
redis-cli -h localhost -p 6379 PING

# 检查最近消息
echo ""
echo "4. 最近消息统计..."
psql -h localhost -p 5434 -U voile -d voile -c "
SELECT 
    platform,
    COUNT(*) as count,
    MAX(created_at) as latest
FROM messages
GROUP BY platform;
" 2>&1

# 检查 AstrBot 日志
echo ""
echo "5. AstrBot 最近日志..."
docker compose logs --tail=20 astrbot

echo ""
echo "=== 检查完成 ==="
```

## 监控脚本

`monitor.sh`:

```bash
#!/bin/bash

# 实时监控消息入库
watch -n 1 '
echo "=== Voile 实时监控 ==="
echo ""
echo "消息总数:"
psql -h localhost -p 5434 -U voile -d voile -t -c "SELECT COUNT(*) FROM messages;"
echo ""
echo "各平台消息数:"
psql -h localhost -p 5434 -U voile -d voile -c "SELECT platform, COUNT(*) FROM messages GROUP BY platform;"
echo ""
echo "最近 5 条消息:"
psql -h localhost -p 5434 -U voile -d voile -c "SELECT platform, channel_id, LEFT(content, 50) as content, created_at FROM messages ORDER BY created_at DESC LIMIT 5;"
'
```

## 备份脚本

`backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

echo "=== 备份 Voile 数据 ==="

# 备份数据库
echo "备份数据库..."
docker exec voile_postgres pg_dump -U voile voile > "$BACKUP_DIR/voile_$DATE.sql"

# 备份配置
echo "备份配置..."
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" .env astrbot/data/config.json

# 清理旧备份（保留最近 7 天）
echo "清理旧备份..."
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "备份完成: $BACKUP_DIR"
ls -lh $BACKUP_DIR | tail -5
```

## 故障恢复

### 恢复数据库

```bash
# 停止服务
docker compose stop astrbot

# 恢复数据库
cat backups/voile_20260418_120000.sql | docker exec -i voile_postgres psql -U voile voile

# 重启服务
docker compose start astrbot
```

### 重置数据库

```bash
# 删除所有数据
docker compose down -v

# 重新启动
docker compose up -d

# 重新初始化
python -c "from core.storage.db import Database; Database('postgresql://voile:voile_pass@localhost:5434/voile')"
```

---

**最后更新**: 2026-04-18  
**维护者**: XartPro Team
