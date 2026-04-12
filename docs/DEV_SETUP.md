# Dev Setup

Target: QQ messages landing in the database within 30 minutes.

## Prerequisites

- Windows 10/11 or Linux
- Docker Desktop
- Python 3.11+
- Go 1.22+
- Rust stable

## 1. Clone & Install

```bash
git clone https://github.com/2233admin/voile.git
cd voile
pip install -e ".[dev]"
pytest  # all green = env OK
```

## 2. Start Infrastructure

```bash
docker compose up redis postgres -d
```

## 3. NapCatQQ Setup (QQ adapter)

NapCatQQ implements OneBot v11 over WebSocket.

- Download: https://github.com/NapNeko/NapCatQQ
- In NapCatQQ settings, enable WebSocket server on `ws://127.0.0.1:3001`
- Scan QR code to log in

## 4. AstrBot Setup (message sink)

AstrBot receives QQ events and forwards them to the gateway via the voile plugin.

```bash
pip install astrbot
```

Copy the plugin into AstrBot:

```bash
cp -r plugins/astrbot_plugin_voile/ /path/to/astrbot/plugins/
```

Set environment variables before starting AstrBot:

```
VOILE_DB_URL=sqlite:///voile.db
VOILE_REDIS_URL=redis://localhost:6379/0
```

Start AstrBot (refer to its own docs for the exact command).

## 5. WeFlow Setup (WeChat adapter, optional)

WeFlow exposes a WeChat HTTP API.

- Download and start WeFlow: https://github.com/greycodee/wechat-backup
- Default listen address: `http://127.0.0.1:5030`

## 6. Start Go Gateway

Open three terminals from the repo root:

```bash
# Terminal 1 -- API gateway
cd gateway
go run ./cmd/api -addr :8080

# Terminal 2 -- QQ connector
go run ./cmd/qq -napcat ws://127.0.0.1:3001 -downstream http://127.0.0.1:8080/ingest/qq

# Terminal 3 -- WeChat connector (optional)
go run ./cmd/wechat -weflow http://127.0.0.1:5030
```

## 7. Verify

Send a QQ message to any monitored group, then:

```bash
python -c "
from core.storage import Database
db = Database()
print(db.recent('YOUR_GROUP_ID', 5))
"
```

You should see the message rows printed.

## 8. Import Historical Data

```bash
# QQ history (qq-chat-exporter JSON format)
python -m core.importers.qq_import your_export.json --db sqlite:///voile.db

# WeChat history (WeChatMsg CSV format)
python -m core.importers.wechat_import your_export.csv --format csv --db sqlite:///voile.db
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Redis connection refused | `docker compose up redis -d` |
| Postgres connection refused | `docker compose up postgres -d` |
| NapCatQQ cannot connect | Confirm WebSocket server is enabled and listening on `ws://127.0.0.1:3001` |
| AstrBot plugin not loaded | Check that `astrbot_plugin_voile/` is directly under AstrBot's `plugins/` directory |
| pytest failures | Re-run `pip install -e ".[dev]"`, then retry |
| Go build errors | Ensure Go 1.22+ -- run `go version` to confirm |
