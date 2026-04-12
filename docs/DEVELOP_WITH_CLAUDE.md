# Developing Voile with Claude Code

Reference for using Claude Code effectively in the Voile three-layer architecture.

## Architecture Overview

```
Python (core/)   -- business logic, agents, storage, schemas
Go (gateway/)    -- real-time message ingestion, HTTP API, link archiver
Rust (kernel/)   -- text cleaning, ANN vector search
```

The three layers communicate through:
- Go -> Python: HTTP POST to core API or direct DB write
- Python -> Rust: subprocess call or FFI (kernel exposes a C ABI)
- No direct Go <-> Rust calls

## Layer Responsibilities

### Python (core/)

Owns:
- Agent logic (digest, summarize, tag, classify)
- Storage models (SQLAlchemy or raw SQL against Postgres/SQLite)
- Schema definitions (Pydantic)
- Importers (qq_import, wechat_import)
- Scheduled tasks and pipelines

Does NOT own:
- Real-time socket connections to QQ/WeChat
- High-volume string processing (delegate to kernel/)
- HTTP routing for ingest endpoints

### Go (gateway/)

Owns:
- WebSocket connection to NapCatQQ (OneBot v11)
- HTTP polling/webhook from WeFlow (WeChat)
- `/ingest/qq` and `/ingest/wechat` HTTP endpoints
- Link archiver (fetch, store, deduplicate URLs found in messages)
- Message queue producer (Redis streams)

Does NOT own:
- Business logic or message interpretation
- Database schema migrations
- Vector embedding or search

### Rust (kernel/)

Owns:
- Text normalization (strip emoji, normalize CJK whitespace, deduplicate)
- Tokenization for CJK text
- ANN vector search index (HNSW or flat)
- High-throughput batch operations called from Python via subprocess or FFI

Does NOT own:
- Network I/O
- Database access
- Agent orchestration

### Cross-Layer Boundaries

| Operation | Who does it |
|-----------|-------------|
| Receive raw QQ event | Go |
| Write raw message to DB | Go (direct) or Python (via queue consumer) |
| Clean message text | Rust (called by Python) |
| Generate digest | Python agent |
| Search by vector | Rust index, queried by Python |
| Expose REST API for UI | Go or Python (separate concerns -- Go for ingest, Python for query) |

## When to Add Code to Which Layer

**Add to Python (core/) when:**
- It is business logic -- deciding what to do with a message
- It touches the database schema or runs a query
- It is a new agent or pipeline step
- It calls an LLM API

**Add to Go (gateway/) when:**
- It is a new message source adapter (new platform connector)
- It is a new HTTP endpoint that receives raw events
- It needs to handle high-concurrency I/O without blocking

**Add to Rust (kernel/) when:**
- It processes text at scale (>10k messages per batch)
- It is a CPU-bound algorithm (regex, tokenize, embed scoring)
- It is a data structure used in hot paths (inverted index, ANN graph)

If unsure: prototype in Python, move to Rust only if profiling shows it is a bottleneck.

## File Naming Conventions

| Layer | Files | Names |
|-------|-------|-------|
| Python (core/) | lowercase_snake_case.py | Classes: PascalCase, modules: snake_case |
| Go (gateway/) | lowercase_snake_case.go, tests: file_test.go | Packages: lowercase single word |
| Rust (kernel/) | snake_case.rs, tests inline via #[cfg(test)] | Structs/Enums: PascalCase, fns: snake_case |

Directory structure follows the shape shown in DEV_SETUP.md:
- `core/agents/` -- one file per agent (digest.py, tagger.py)
- `core/storage/` -- models.py, db.py
- `core/schemas/` -- one file per domain object
- `gateway/cmd/<name>/main.go` -- one binary per connector
- `gateway/internal/<feature>/` -- ingest, archiver, queue
- `kernel/src/<module>.rs` -- clean, tokenize, index; all re-exported via lib.rs

## Testing Conventions

| Layer | Command | Notes |
|-------|---------|-------|
| Python | `pytest` | Mock LLM calls -- no real API hits in tests. DB defaults to SQLite in-memory. |
| Go | `go test ./...` (add `-race` before PR) | Unit tests: no build tag. Integration tests: `//go:build integration`. Use `httptest` for handlers. |
| Rust | `cargo test` | Unit tests inline via `#[cfg(test)]`. Integration tests in `tests/`. Use `proptest` for text-processing edge cases. |

## Claude Code Prompt Conventions

### Referencing the Architecture

Always specify the layer when asking for changes:

```
# Good
"In the Python layer (core/agents/), add a new agent that ..."
"In the Go gateway, add a new endpoint /ingest/telegram that ..."
"In the Rust kernel, add a function that strips HTML tags from text"

# Avoid
"Add a new feature that cleans messages"  -- ambiguous which layer
```

### Requesting a New Agent (Python)

```
Add a new Python agent in core/agents/. 
Name: <AgentName>Agent
Input: <describe the input schema or Pydantic model>
Output: <describe what it returns or writes>
Dependencies: <list any external calls -- LLM, DB, kernel>
Test: add a test in tests/test_<name>.py with at least one happy-path case
```

### Requesting a New DB Model (Python)

```
Add a new SQLAlchemy model in core/storage/models.py.
Table name: <snake_case>
Fields:
  - id: int primary key
  - <field>: <type>, <nullable/required>, <description>
Also add the corresponding Pydantic schema in core/schemas/<name>.py.
Do not add a migration file -- I will run alembic separately.
```

### Requesting a New Gateway Endpoint (Go)

```
Add a new HTTP endpoint in gateway/internal/ingest/.
Route: POST /ingest/<source>
Input: JSON body, fields: <list fields>
Behavior: validate input, write to Redis stream "<stream-name>", return 200 OK or 4xx on error
Test: add a handler test using httptest
```

### Requesting a New Kernel Function (Rust)

```
Add a new public function in kernel/src/<module>.rs.
Signature: fn <name>(input: &str) -> <return type>
Behavior: <describe precisely, include edge cases>
Expose it in lib.rs.
Test: add at least two unit tests -- one normal case, one edge case (empty string or unicode boundary)
```

### General Guidance

- When changing cross-layer interfaces, state both sides explicitly: "Update the Go endpoint AND the Python consumer that reads from the queue."
- When asking for refactors, specify "do not change external behavior, only internal structure."
- When asking Claude to add tests, say "do not call real external services -- mock or stub them."
- If you want Claude to read existing code before writing, say "first read core/agents/digest.py, then add..."

## Common Pitfalls

- The Rust kernel is called from Python via subprocess. If you change the kernel CLI interface (args, stdout format), update the Python caller in the same PR.
- Go uses `go.mod` in `gateway/`, not the repo root. Run `go` commands from inside `gateway/`.
- Python tests that need a DB use SQLite in-memory by default. Do not assume Postgres is available in CI.
- AstrBot plugin lives in `plugins/astrbot_plugin_voile/`. It is a dependency consumer, not a core module -- do not add business logic there.
