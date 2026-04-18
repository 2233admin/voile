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

Voile ingests QQ and WeChat messages, normalizes them into a unified schema,
and compiles them into structured knowledge -- topic maps, persona profiles,
decision logs, and link archives -- stored in Obsidian and queryable via gRPC.

## Architecture

```
[NapCatQQ]  [WeFlow]
     |           |
  [Go: QQ gw] [Go: WeChat sync]
          \       /
       [Go: API gateway :8080]
              |
    [Python: AstrBot plugin]  <-- message sink (XAR-16)
              |
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
-- core/          Python: schemas, storage, obsidian writer, analysis agents
-- gateway/       Go: QQ gateway, WeChat sync, unified REST API, link fetcher
-- kernel/        Rust: text cleaner + ANN engine (gRPC)
-- kernel/proto/  voile.proto -- single source of truth for all gRPC interfaces
-- plugins/       AstrBot plugin: astrbot_plugin_voile
-- assets/        SVG logo and static assets
-- docs/          Architecture and development guides
```

## Phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Message ingestion + storage foundation | Done |
| 2 | Analysis and archiving pipeline | Done |
| 3 | Persona, decision tracking, CI/CD | In Progress |

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

## QQ History Import

To import historical QQ messages from local database:

1. **Extract database key** using [qq-win-db-key](https://github.com/yllhwa/qq-win-db-key)
2. **Decrypt database** with our automated script:
   ```bash
   python scripts/decrypt_qq_db.py <QQ号> <密钥>
   ```
3. See [docs/QQ_DATABASE_DECRYPT.md](docs/QQ_DATABASE_DECRYPT.md) for detailed guide

## Dependencies

Integrates with existing open-source projects -- no reinventing wheels:

- [NapCatQQ](https://github.com/NapNeko/NapCatQQ) -- OneBot v11 QQ adapter
- [AstrBot](https://github.com/Soulter/AstrBot) -- plugin host for message events
- [WeFlow](https://github.com/greycodee/wechat-backup) -- WeChat HTTP API
- [WeChatMsg](https://github.com/LC044/WeChatMsg) -- WeChat history export

## Linear board

[XartPro / Voile](https://linear.app/xartpro/project/不动的大图书馆-5a06f255e3b4)
