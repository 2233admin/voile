# Contributing to Voile

Voile -- the immovable great library. Chat message analysis and knowledge archiving system.

## Branch Naming

```
feat/xar-{N}-short-desc     -- new capability
fix/xar-{N}-short-desc      -- bug fix
docs/xar-{N}-short-desc     -- documentation only
refactor/xar-{N}-short-desc -- internal restructure, no behavior change
test/xar-{N}-short-desc     -- test additions or fixes
```

Examples:
- `feat/xar-25-contribution-docs`
- `fix/xar-12-qq-reconnect-loop`
- `refactor/xar-8-storage-layer`

## Commit Convention

```
feat: add QQ group filter by keyword
fix: handle empty WeChat message body
refactor: extract vector search into kernel crate
docs: update dev setup for Docker Compose v2
test: add pytest coverage for digest agent
chore: bump ruff to 0.4
```

One logical change per commit. Do not mix feat and refactor in the same commit.

## Pull Request Requirements

**Title format:** `feat(XAR-N): short description` (replace feat with fix/docs/refactor as appropriate)

**PR body must include:**
1. Linear issue link -- `Closes XAR-N` or `Refs XAR-N`
2. What changed and why (2-5 sentences)
3. How to test it manually (if behavior changes)

**CI must be green before requesting review.** Do not mark a PR as ready while CI is failing.

**Review policy:** 1 approval required. The reviewer merges after approval (not the author).

**Merge strategy:** Squash merge for feat/fix branches. Merge commit for long-running feature branches that need history.

## Code Style

| Layer | Formatter | Linter | Config |
|-------|-----------|--------|--------|
| Python (core/) | ruff format | ruff check | pyproject.toml |
| Go (gateway/) | gofmt | go vet + staticcheck | default |
| Rust (kernel/) | rustfmt | clippy | rustfmt.toml |

Run before pushing:

```bash
# Python
ruff format core/ && ruff check core/

# Go
cd gateway && gofmt -w . && go vet ./...

# Rust
cd kernel && cargo fmt && cargo clippy -- -D warnings
```

CI runs all three. A formatter diff fails the build.

## Issue Templates

### Bug Report

When filing a bug, include:

- **Layer affected:** Python / Go / Rust / all
- **Steps to reproduce:** numbered list, minimal
- **Expected behavior:** what should happen
- **Actual behavior:** what actually happens
- **Environment:** OS, Python/Go/Rust versions, Docker version
- **Logs:** paste the relevant error output (trim to <50 lines)

Title format: `[BUG] short description of symptom`

### Feature Request

When proposing a feature, include:

- **Problem statement:** what user need or gap this addresses
- **Proposed solution:** high-level description (not implementation detail)
- **Layer(s) involved:** which of Python/Go/Rust would change
- **Alternatives considered:** what else you thought about
- **Definition of done:** how we know it works

Title format: `[FEAT] short description`

## Development Workflow

1. Pick or create a Linear issue (XAR-N)
2. Branch off `main`: `git checkout -b feat/xar-N-desc`
3. Make changes, run local tests (see DEV_SETUP.md)
4. `ruff`/`gofmt`/`rustfmt` pass locally
5. Push and open PR against `main`
6. CI passes, request review
7. Reviewer approves, squash merge

## Testing Requirements

- **Python:** `pytest` must pass with no failures. New business logic needs at least one test.
- **Go:** `go test ./...` must pass. New HTTP handlers need at least a smoke test.
- **Rust:** `cargo test` must pass. New kernel functions need a unit test with at least one edge case.

Coverage is not enforced by gate but is tracked. Do not reduce coverage without a documented reason.

## What Not to Do

- Do not commit secrets, API keys, or personal QQ/WeChat IDs
- Do not add print-debugging to production code paths
- Do not bump dependency versions without checking for breaking changes in the changelog
- Do not open a PR with "WIP" unless you explicitly mark it as a draft
