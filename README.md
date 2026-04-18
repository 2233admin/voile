<div align="center">
  <img src="assets/logo.svg" width="180" alt="Voile logo"/>

  # Voile, the Magic Library

  **Chat message analysis and knowledge archiving system**

  *Named after the Voile, the Magic Library in Touhou Project*

  [![CI](https://github.com/2233admin/voile/actions/workflows/ci.yml/badge.svg)](https://github.com/2233admin/voile/actions/workflows/ci.yml)
  ![Python](https://img.shields.io/badge/Python-3.11+-7c3aed)
  ![Go](https://img.shields.io/badge/Go-1.22+-00add8)
  ![Rust](https://img.shields.io/badge/Rust-stable-orange)
</div>

---

Voile ingests QQ messages (and WeChat via internal tools), normalizes them into a unified schema,
and compiles them into structured knowledge -- topic maps, persona profiles,
decision logs, and link archives -- stored in Obsidian and queryable via gRPC.

## Architecture

```
Real-time Collection:
[NapCatQQ]  [WeChat (internal)]
     |           |
  [Go: QQ gw] [Go: WeChat sync]
          \       /
       [Go: API gateway :8080]
              |
    [Python: AstrBot plugin]  <-- message sink (XAR-16)
              |
              v

Historical Import:
[QQ nt_msg.db] --decrypt--> [scripts/decrypt_qq_db.py]
              |
              v

Unified Pipeline:
    [Python: core.storage]    <-- SQLAlchemy, SQLite/Postgres
              |
     +---------+---------+
     |                   |
[Python agents]     [Rust kernel]
topic / sentiment   TextCleaner gRPC :50051
persona / decision  VectorIndex gRPC :50052
     |
[Obsidian vault]
```

## Project structure

```
voile/
├── core/          Python: schemas, storage, obsidian writer, analysis agents
├── gateway/       Go: QQ gateway, WeChat sync, unified REST API, link fetcher
├── kernel/        Rust: text cleaner + ANN engine (gRPC)
├── kernel/proto/  voile.proto -- single source of truth for all gRPC interfaces
├── plugins/       AstrBot plugin: astrbot_plugin_voile
├── scripts/       Utility scripts for message import and database operations
│   ├── decrypt_qq_db.py    # QQ database decryption tool
│   ├── decrypt_qq_db.sh    # Bash version
│   └── README.md           # Quick start guide
├── docs/          Architecture and development guides
│   └── QQ_DATABASE_DECRYPT.md  # Complete QQ decryption documentation
└── assets/        SVG logo and static assets
```

## Features & Status

| Feature | Description | Status |
|---------|-------------|--------|
| **Real-time Collection** | QQ message streaming via OneBot | ✅ Done |
| **Historical Import** | QQ local database decryption & import | ✅ Done |
| **Storage Foundation** | Unified schema, PostgreSQL, SQLAlchemy ORM | ✅ Done |
| **Analysis Pipeline** | Topic extraction, sentiment, persona tracking | ✅ Done |
| **Knowledge Archive** | Obsidian vault integration, decision logs | ✅ Done |
| **Vector Search** | Rust-based ANN engine via gRPC | 🚧 In Progress |
| **CI/CD & Monitoring** | Automated testing, deployment, observability | 🚧 In Progress |

## Quick start

```bash
# 1. Copy env template and set your Obsidian vault path
cp .env.example .env
# edit .env: set OBSIDIAN_HOST_PATH

# 2. Start core stack (Redis, Postgres, Rust gRPC, Go gateway, Python workers)
docker compose up -d

# 3. (Optional) QQ login via Lagrange.OneBot
#    Fill in your QQ number in lagrange/appsettings.json (Uin field)
docker compose --profile qq up -d

# Dev: run tests + linters
pip install -e ".[dev]"
pytest
ruff check core/ plugins/ tests/
mypy core/
```

## Message Sources

Voile supports multiple message ingestion methods:

### 📱 Real-time Message Collection

**QQ (via NapCatQQ)**
- OneBot v11 protocol adapter
- Real-time message streaming
- Supports text, images, files, and rich media
- Setup: `docker compose --profile qq up -d`

**WeChat**
- Internal integration (contact team for access)

### 📚 Historical Message Import

**QQ Local Database**

Import years of QQ chat history from local encrypted database:

```bash
# 1. Extract encryption key (Windows only, requires admin)
git clone https://github.com/yllhwa/qq-win-db-key.git
cd qq-win-db-key
.\windows_ntqq_get_key.ps1  # Follow prompts to login QQ

# 2. Decrypt and import to Voile
cd /path/to/voile
python scripts/decrypt_qq_db.py <QQ号> <密钥>
```

**What you get:**
- ✅ All private chat messages (C2C)
- ✅ All group chat messages
- ✅ Message metadata (timestamps, senders, types)
- ✅ Ready for Voile analysis pipeline

**Technical details:** [docs/QQ_DATABASE_DECRYPT.md](docs/QQ_DATABASE_DECRYPT.md)

### 🔄 Import Pipeline

```
[Encrypted DB] → [Decrypt Script] → [SQLite] → [Voile Importer] → [PostgreSQL] → [Analysis]
```

All imported messages are normalized into Voile's unified schema and processed through the same analysis pipeline as real-time messages.

## Dependencies

Integrates with existing open-source projects -- no reinventing wheels:

- [NapCatQQ](https://github.com/NapNeko/NapCatQQ) -- OneBot v11 QQ adapter
- [AstrBot](https://github.com/Soulter/AstrBot) -- plugin host for message events

WeChat integration uses internal tools (contact team for access).

## Linear board

[XartPro / Voile](https://linear.app/xartpro/project/不动的大图书馆-5a06f255e3b4)
