# Architecture Review 02 — Python Stack

**Scope.** Verdict-driven assessment of the Python language + library choices: Python version, web framework, async runtime, validation library, ORM/Core choice, database driver, IBKR adapter, scheduler. 8 architectural questions with the locked 5-part format (current implementation + state-of-the-art alternative + verdict + performance implication + concrete improvement direction). Recommendations belong in Track 1c.

**Reality docs referenced**: T-001 (domain types — Pydantic v2), T-002 (portfolio types — Pydantic v2), T-003 (SQLAlchemy Core), T-004 (`ibapi==9.81.1.post1`), T-005 / T-006 (FastAPI routes), T-007 (APScheduler), T-023 (anthropic SDK), T-036 (monorepo overlap).

## 0. Verdict matrix at a glance

| # | Architectural choice | Verdict |
|---|----------------------|---------|
| 1 | Python 3.12 floor + `requires-python = ">=3.12"` | **State-of-the-art** |
| 2 | FastAPI with **0 async routes / 179 sync routes** | **Risky** |
| 3 | AsyncIO essentially unused (only `lifespan` async) | **Outdated** |
| 4 | Pydantic v2 + Pydantic Settings + `extra="forbid"` | **State-of-the-art** |
| 5 | SQLAlchemy 2.0 Core (88 `Table(`, 0 `Mapped[]` ORM) | **Acceptable** |
| 6 | `psycopg[binary]` v3 (sync driver) + SQLite for tests | **Acceptable** |
| 7 | `ibapi==9.81.1.post1` exact pin | **Risky** |
| 8 | APScheduler 3.10.4+ for cron + intervals | **Acceptable** |

**Distribution**: 2 state-of-the-art + 3 acceptable + 1 outdated + 2 risky. Stronger middle and tail than monorepo structure — language fundamentals are modern, but two risky calls (sync-handler concentration + brittle ibapi pin) need attention.

## 1. Python 3.12 floor

### Current implementation

All 5 pyproject files declare `requires-python = ">=3.12"`:
- `apps/api/pyproject.toml`
- `apps/worker/pyproject.toml`
- `packages/domain/pyproject.toml`
- `packages/portfolio/pyproject.toml`
- `packages/storage/pyproject.toml`

`target-version = "py312"` in each ruff config; `python_version = "3.12"` in each mypy config. CI matrix would use 3.12.

Python 3.12 GA: October 2023. Python 3.13 GA: October 2024 (during this codebase's active development). Python 3.14 expected October 2025.

### State-of-the-art alternative

Tracking the latest **stable** Python release (currently 3.13 with 3.14 in beta as of this audit). 3.13 brings:
- The free-threaded build (PEP 703) — opt-in but available; removes GIL concerns.
- The JIT (PEP 744 experimental).
- `PYTHON_GIL=0` for opting in.

For a sync-handler-heavy codebase (§2), 3.13's free-threaded build is a directly relevant perf option.

### Verdict — State-of-the-art

3.12 was current at codebase inception (2024 H1). The locked floor protects against syntax / behavior regressions when running on 3.11. The codebase doesn't pin to 3.12 max — `>=3.12` allows 3.13 + 3.14 to run, which is the right call.

The codebase missed exactly one Python release cycle (didn't proactively jump to 3.13), which is well within normal practice.

### Performance implication

3.12 is ~5% faster than 3.11 (per Python release notes). 3.13 with JIT may be 10-30% faster for hot loops. For a sync-handler API at low RPS, this is academic.

### Improvement direction (for Track 1c)

Optional: bump CI matrix to test on 3.13 + 3.14. Not urgent.

## 2. FastAPI with 0 async routes / 179 sync routes

### Current implementation

Grep proof:
- `grep -rn "^@router\." apps/api/src/portfolio_outlook_api/` returns **179** route decorations.
- `grep -A1 "^@router\." apps/api/src/portfolio_outlook_api/ | grep -c "^async def"` returns **0**.

Every single FastAPI route in the codebase is defined as `def`, not `async def`. The only `async def` in `apps/api/` is the `lifespan` startup hook (`main.py:81`). Worker (`apps/worker/`) has zero `async def`.

FastAPI's documented behavior for sync route functions: they are scheduled into a Starlette threadpool (default 40 threads). Async routes run on the main asyncio event loop. The threadpool has a hard upper bound; at sustained traffic exceeding the thread count, requests queue.

### State-of-the-art alternative

The state-of-the-art for FastAPI specifically is:
- **`async def` for I/O-bound routes** (the vast majority of API endpoints) + an async DB driver (`psycopg[binary,async]` or `asyncpg`).
- **`def` for CPU-bound or sync-third-party routes** (e.g., a route that calls `ibapi` which is sync-only).

A typical modern FastAPI codebase has 80-90% async routes + 10-20% sync routes. Zero-async is anomalous.

### Verdict — Risky

The risk is two-fold:
1. **Throughput ceiling**: 40 threads × ~10ms-per-DB-query ≈ ~4,000 RPS theoretical max. T-006 / T-021 documented multiple routes that do multi-query reads (e.g., `GET /portfolio/valuation/readiness` does 4-5 SQL queries per call) — actual ceiling is lower. At single-user / low-RPS, this is invisible; at any scale spike, it becomes the wall.
2. **Operational opacity**: a sync handler on a thread doesn't surface in async tracing tools (e.g., asyncio's `slow_callback_duration` warnings). Operational diagnostics assume async-first; the codebase doesn't fit the assumed shape.

The codebase clearly works at the intended scale (single user, low frequency). The verdict reflects the architectural ceiling and the tooling-assumption mismatch, not a present bug.

### Performance implication

**Significant for any horizontal scaling.** A single sync route takes a threadpool slot for its entire duration including DB I/O. Async routes would yield the event loop during I/O, freeing capacity for other concurrent requests.

T-021 §3 documented that `GET /portfolio/valuation/readiness` is polled every 30 seconds by the frontend; 5 SQL queries per call. With a sync handler + 40 threads + 1 user, latency is fine. With 100 users polling, the threadpool would saturate.

### Improvement direction (for Track 1c)

Either:
- Migrate to `async def` + an async DB driver (`asyncpg` or `psycopg[binary,async]`). Significant refactor — 179 routes + the storage layer.
- Stay sync but use Gunicorn (multi-process) instead of uvicorn (single-process). Sidesteps the GIL via process boundaries.

Track 1c will decide.

## 3. AsyncIO essentially unused

### Current implementation

Outside the FastAPI `lifespan` hook at `apps/api/src/portfolio_outlook_api/main.py:81`, AsyncIO is unused. Specifically:
- 0 `async def` in worker.
- 0 use of `asyncio.gather`, `asyncio.create_task`, `asyncio.Queue`, etc.
- HTTP client `httpx` is used in sync mode (per T-014 EODHD client).
- DB queries are sync via `psycopg[binary]` + SQLAlchemy Core's sync `Connection`.

The codebase imports `asyncio` only where FastAPI forces it (the lifespan return type).

### State-of-the-art alternative

For an I/O-bound app with HTTP + DB calls, AsyncIO is the standard concurrency primitive in 2024. Alternatives: `anyio` (FastAPI's underlying lib), `trio` (cleaner cancellation), `gevent` (greenlet-based, retro).

Sync-everywhere is correct when the bottleneck is CPU or when third-party libs are sync-only. For this codebase, the dominant ops are DB + HTTP — both classic async wins. The choice to stay sync is intentional but undocumented.

### Verdict — Outdated

The sync-everywhere pattern is pre-2020 Python. By 2024 standards, an I/O-bound web service should be async-first unless it has a specific reason not to be (e.g., heavy use of sync-only libraries — `ibapi` is sync-only, but only the worker touches it). The API has no such constraint.

The codebase isn't broken by this choice — it's just not using the modern Python concurrency model. T-002 (Belgian tax pure math), T-001 (domain types) are sync because they're CPU/pure-logic; appropriate. But the API + storage layers being sync is the dated call.

### Performance implication

Same as §2 — single-user fine, scale wall above ~100 RPS.

### Improvement direction (for Track 1c)

If §2 migrates to async, §3 follows. If not, keep status quo and use process-based scaling.

## 4. Pydantic v2 + Pydantic Settings + `extra="forbid"`

### Current implementation

Per T-001 / T-002:
- Pydantic ≥ 2.9.0 across all packages.
- All domain models inherit from `DomainBaseModel` which sets `extra="forbid"` (T-001 §1.2 documented this).
- `Pydantic Settings ≥ 2.6.0` for `Settings` classes (T-061 §2).
- Field validators using the v2 `@field_validator` syntax (per `packages/domain/src/portfolio_outlook_domain/settings.py:161-182`).
- `ConfigDict` used where models override the base default.

Pydantic v2 is the rewrite (Rust-based core); ~10x faster than v1.

### State-of-the-art alternative

This IS the state-of-the-art for Python data validation in 2024. Alternatives are: `msgspec` (faster than Pydantic v2 by ~2-3x; less feature-rich), `attrs` + `cattrs` (older, mature, less ergonomic), `dataclass-wizard` (lighter).

For FastAPI ecosystem compatibility + Pydantic's network effect, Pydantic v2 is the right call. `msgspec` would force giving up FastAPI's first-class Pydantic integration.

### Verdict — State-of-the-art

`extra="forbid"` enforces "no unknown fields land in our domain", which AGENTS.md "schema-validated output" maps to directly. Field validators catch Decimal-vs-float at boundaries. Settings inheritance keeps config typed.

No critique — this is one of the clearest "modern" parts of the stack.

### Performance implication

Pydantic v2's Rust core makes validation cheap. JSON parsing + validation is now bounded by JSON parser speed, not validation overhead. For this codebase's throughput, validation is not in any hot path.

### Improvement direction (for Track 1c)

None.

## 5. SQLAlchemy 2.0 Core (88 `Table(`, 0 `Mapped[]` ORM)

### Current implementation

Per T-003:
- 88 `Table(...)` declarations in `packages/storage/src/ai_trading_agent_storage/metadata.py`.
- 0 declarative-ORM uses (no `Mapped[...]`, no `class X(Base): __tablename__ = ...`).
- Repository pattern: `SqlAlchemy*Repository` classes call `Connection.execute(stmt)` with Core expression-language statements.
- Alembic 1.13+ for migrations (53+ migrations per T-003).
- Result rows accessed by tuple/dict, not object attributes.

The codebase uses SQLAlchemy strictly as a "type-safe SQL builder + connection pool" — not as an ORM.

### State-of-the-art alternative

- **SQLAlchemy 2.0 ORM with `Mapped[]`**: declarative-mapped types; objects with attribute access; eager-load patterns. Default for most Python codebases in 2024.
- **SQLModel** (FastAPI's "sister" library): Pydantic models with SQLAlchemy persistence in one class. Trendy in 2023-2024 FastAPI stacks.
- **Tortoise ORM**: async-native, simpler API. Used in async-first FastAPI codebases.

SQLAlchemy Core is the **pre-1.4** style by name but remains supported and used. It's not deprecated; it's just less common than the ORM in 2024 Python.

### Verdict — Acceptable

The choice is intentional per T-003 §1: "Core is preferred because the storage layer is the boundary; Pydantic models do the domain typing, SQLAlchemy provides connection + SQL building only". The trade-off:
- **Pro**: zero ORM magic; explicit SQL; cleaner separation between Pydantic domain types and storage representations.
- **Con**: more boilerplate (manual mapping from row tuple to dataclass); no eager-load helpers; lower mindshare in 2024 Python.

The pattern works. It's not modern-default but it's defensible.

### Performance implication

Core is slightly faster than ORM (no object hydration overhead). For this codebase's query volume, negligible.

### Improvement direction (for Track 1c)

None required. If ORM patterns become attractive (e.g., for nested-load optimization), migrate per-table; the Core base is compatible with adding ORM on top.

## 6. `psycopg[binary]` v3 (sync driver) + SQLite for tests

### Current implementation

`psycopg[binary]>=3.2` in `apps/api/pyproject.toml`, `apps/worker/pyproject.toml`, `packages/storage/pyproject.toml`. Per the comment in `apps/api/pyproject.toml:30-31`:

> "picks psycopg (v3) automatically when `DATABASE_URL=postgresql://`"

Tests use SQLite (per T-003 + reality findings — Postgres-only would block local CI). The SQLAlchemy Core API abstracts the driver — same code path for SQLite + Postgres.

`psycopg` v3 (not v2): supports both sync + async; v2 is sync-only and in maintenance mode.

### State-of-the-art alternative

- **`psycopg[binary,async]`** or **`asyncpg`** for async DB queries. Required if §2 migrates to async-route patterns.
- **`aiosqlite`** for async SQLite tests if production-side goes async.

`psycopg[binary]` v3 in sync mode is the right call for §5 + §2 (sync everywhere). The trade-off is that adding async DB queries later requires a driver swap or driver-mode extension.

### Verdict — Acceptable

The driver matches the codebase's sync-everywhere model. Picking v3 (not v2) is forward-looking — v2 is in maintenance mode. If/when async migration happens, `psycopg[binary,async]` is the natural next step.

The SQLite-for-tests choice is the standard FastAPI/SQLAlchemy testing pattern. The risk is that test-only behaviors (e.g., transaction isolation) differ between SQLite and Postgres; T-003 §3 documented this concern.

### Performance implication

Sync `psycopg` v3 is slightly faster than v2. For low query volume, negligible.

### Improvement direction (for Track 1c)

If §2 → async, swap to `psycopg[binary,async]`. Else no change.

## 7. `ibapi==9.81.1.post1` exact pin

### Current implementation

`apps/api/pyproject.toml`:
```
"ibapi==9.81.1.post1",
```

Per T-004:
- Exact version pin (not `>=`).
- The `ibapi` library is Interactive Brokers' official Python adapter.
- `9.81.1.post1` is the only IBKR-released version that satisfies the codebase's expected API surface (per T-004 §1).
- Worker also depends on `ibapi` via `apps/worker/pyproject.toml`.

`ibapi` characteristics:
- **Sync-only API**: callback-based, runs in a single thread (the IBKR EReader thread).
- **No formal type stubs**: T-051 documented `[mypy.overrides] module = ["ibapi", "ibapi.*"] ignore_missing_imports = true`.
- **Distributed via pip but not super-actively maintained** — the IBKR team ships a new version every 6-12 months; CHANGELOG is minimal.

### State-of-the-art alternative

- **`ib-insync`**: a community wrapper around `ibapi` that adds an asyncio-friendly API + type hints + retry logic. Most active community-IB project. Acquired by IBKR + paused officially in 2024-2025 timeframe — community forks exist.
- **`ib-async`**: a fork of `ib-insync` post-acquisition; async-native.
- **Direct WebSocket API**: IBKR exposes a WebSocket API as well; some teams build directly on top.

### Verdict — Risky

Two specific risks:
1. **Exact pin without fallback**: `==9.81.1.post1` will break installs the moment that specific version disappears from PyPI. IBKR has been known to retire old wheels. A `>=9.81.1.post1,<10` constraint would be safer.
2. **Sync-only + single-thread**: T-019 § + T-020 § document that the worker shares a single IBKR session across all order operations. Combined with the lock-sharing model (T-031 / T-032), all IBKR-touching code is serialised on one thread + one connection. Any IBKR API hang halts all submission + reconciliation work.

Plus the maintenance status of `ibapi` itself: minimal updates, narrow community. If `ib-async` is becoming the de-facto standard, the codebase may need to follow at some point.

### Performance implication

For single-user paper trading: negligible. For any scaling: the single-thread IBKR session is a hard ceiling; multiple users on the same worker share one IBKR connection.

### Improvement direction (for Track 1c)

Relax pin to `>=9.81.1.post1,<10`. Evaluate `ib-async` as a forward migration target. Decision belongs in Track 1c.

## 8. APScheduler 3.10.4+ for cron + intervals

### Current implementation

Per T-007 + T-031 + T-032:
- `apscheduler>=3.10.4` in `apps/worker/pyproject.toml` + `apps/api/pyproject.toml`.
- Worker scheduler registers 3 jobs: pre_briefing (06:00 cron), hourly (7-21 cron), heartbeat (interval).
- API scheduler (T-032 §5) registers 1 job: morning chain via `SCHEDULER_DAILY_BRIEFING_CRON`.
- APScheduler uses Postgres advisory locks for single-flight (per T-019 §2.3 + T-020 §2.3 originating findings).

APScheduler v3.x: pure-Python, in-process scheduler. v4.x (the rewrite): more modular but with breaking API changes.

### State-of-the-art alternative

- **Celery + Beat**: distributed task queue with cron scheduling. Production standard for >2-process deployments.
- **Temporal / Cadence**: durable-execution workflows. Stronger guarantees (replay-on-failure) but heavier setup.
- **Cloud-native cron**: AWS EventBridge, Kubernetes CronJob, etc. — external scheduler invoking HTTP webhooks.
- **APScheduler v4**: same library, rewritten. Not widely adopted yet.

For a single-worker-process app with 3-4 cron jobs, APScheduler v3 is right-sized. Celery would be overkill at this scale.

### Verdict — Acceptable

The choice fits the scale. APScheduler v3 is mature (used since ~2014), stable, well-documented. The single-flight pattern via Postgres advisory locks is sound.

Two minor concerns:
- **APScheduler v4 migration cost** — eventually. Not urgent.
- **In-process scheduler ties scheduling to worker process lifetime**: if the worker crashes mid-fire, the fire is lost (no retry queue). Celery + Beat would buffer; APScheduler doesn't.

### Performance implication

Negligible. Scheduling overhead is microseconds per fire.

### Improvement direction (for Track 1c)

None required at current scale. If/when scaling to multi-worker, evaluate Celery or APScheduler v4.

## 9. Observations across the 8 questions

### 9.1 Pattern: async commitment incoherent

The codebase uses FastAPI (async-first framework) with 0 async routes (§2), psycopg in sync mode (§6), and no async patterns in worker (§3). The framework expects async; the codebase delivers sync. Either commit fully to async or pick a sync-first framework (Flask + Gunicorn). The current middle ground gets neither the async perf benefits nor the sync simplicity.

### 9.2 Pattern: modern language, conservative libraries

Python 3.12 (§1) and Pydantic v2 (§4) are leading-edge. SQLAlchemy Core (§5) and APScheduler (§8) are conservative-but-supported. The mix is intentional and defensible — leading-edge language with proven libraries minimises risk.

### 9.3 Pattern: third-party pins differ

The codebase uses lower-bound pins (`>=`) for nearly all deps except `ibapi==9.81.1.post1` (§7). The exact pin reflects IBKR-side reality (limited version compatibility) but creates a single point of failure if PyPI ever retires that wheel.

### 9.4 What's clearly good

- Python 3.12 floor.
- Pydantic v2 with `extra="forbid"` discipline.
- `mypy --strict` universally enabled (per T-036 §6 cross-ref + T-051 baseline).
- SQLAlchemy Core for explicit SQL boundary.

### 9.5 What's clearly outdated

- AsyncIO unused beyond the FastAPI lifespan hook.

### 9.6 What's risky

- 179 sync routes on async framework — throughput ceiling at scale.
- `ibapi==9.81.1.post1` exact pin — supply-chain fragility.

## 10. Summary table

| # | Question | Verdict | Track-1c priority |
|---|----------|---------|--------------------|
| 1 | Python 3.12 floor | State-of-the-art | None |
| 2 | FastAPI sync routes | **Risky** | **Medium** (scale ceiling) |
| 3 | AsyncIO unused | Outdated | Low (couples to §2 decision) |
| 4 | Pydantic v2 | State-of-the-art | None |
| 5 | SQLAlchemy Core | Acceptable | Low |
| 6 | psycopg v3 sync | Acceptable | Low (couples to §2) |
| 7 | ibapi exact pin | **Risky** | **High** (supply chain) |
| 8 | APScheduler | Acceptable | Low |

**Recommendations deferred to Track 1c.**

## 11. References

- `apps/api/pyproject.toml` (FastAPI, Pydantic, Pydantic Settings, psycopg, ibapi, anthropic, apscheduler, uvicorn)
- `apps/worker/pyproject.toml` (Pydantic, SQLAlchemy, psycopg, apscheduler, ibapi)
- `packages/domain/pyproject.toml` (Pydantic v2 only)
- `packages/portfolio/pyproject.toml`
- `packages/storage/pyproject.toml` (alembic, SQLAlchemy, psycopg)
- `apps/api/src/portfolio_outlook_api/main.py:81` (the lone `async def lifespan`)
- `packages/storage/src/ai_trading_agent_storage/metadata.py` (88 `Table(` declarations)
- T-001 `domain-primitives-and-money.md`, `domain-portfolio-and-policy.md`, `domain-research-and-suggestions.md`, `domain-runtime-and-integration.md` (Pydantic v2 + DomainBaseModel)
- T-002 `portfolio-money-and-accounting.md`, `portfolio-predictors.md`, etc. (Pydantic models in portfolio)
- T-003 `storage-package-and-migrations.md` (SQLAlchemy Core + Alembic)
- T-004 `api-ibkr-submission-and-watchlists.md` (ibapi==9.81.1.post1 + sync-thread model)
- T-005 / T-006 (179 FastAPI routes)
- T-007 `worker-orchestration-and-scheduling.md` (APScheduler)
- T-019 / T-020 / T-031 / T-032 (single-flight lock + thread serialisation)
- T-023 `ai-explanation-and-budget.md` (anthropic SDK)
- T-036 `01-monorepo-structure.md` (per-package config duplication — cross-ref)
- T-051 mypy --strict baseline
