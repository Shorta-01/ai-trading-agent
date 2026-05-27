# Architecture Review 04 — Data and Storage

**Scope.** Verdict-driven assessment of the data + storage layer: PostgreSQL + SQLite-for-tests strategy, the 88-table schema, the 53-migration Alembic chain, the Decimal-as-string discipline, repository pattern, connection management, and single-DB deployment. 8 architectural questions with the locked 5-part format. Recommendations belong in Track 1c.

**Reality docs referenced**: T-003 (full storage reality), T-037 §5-§6 (SQLAlchemy Core + psycopg already verdicted).

## 0. Verdict matrix at a glance

| # | Architectural choice | Verdict |
|---|----------------------|---------|
| 1 | PostgreSQL prod + SQLite tests (single SQLAlchemy code path) | **Acceptable** |
| 2 | 88 tables in single 3116-LOC `metadata.py` | **Outdated** |
| 3 | 53-migration linear Alembic chain | **State-of-the-art** |
| 4 | 47 JSON columns (selective denormalisation) | **Acceptable** |
| 5 | Decimal-as-string + `MONEY_NUMERIC = Numeric(20, 6)` discipline | **State-of-the-art** |
| 6 | 53 hand-coded `SqlAlchemy*Repository` classes in 6617-LOC `sql_repositories.py` | **Outdated** |
| 7 | No connection pooling configuration (SQLAlchemy defaults) | **Risky** |
| 8 | Single Postgres deployment (no read replicas, no caching layer) | **Risky** |

**Distribution**: 2 state-of-the-art + 2 acceptable + 2 outdated + 2 risky. Even split. The data layer is the strongest part of the codebase by fundamentals (Decimal discipline, append-only audit, hash chains) but has structural-organisation + scale-ceiling weaknesses.

## 1. PostgreSQL prod + SQLite tests

### Current implementation

Per T-003 + T-037 §6:
- Production: PostgreSQL via `psycopg[binary]>=3.2`. `DATABASE_URL=postgresql://...` selects the driver.
- Tests: SQLite via `sqlite:///:memory:` or `sqlite:///./test.db`. SQLAlchemy Core abstracts the SQL dialect — same Python code path for both.
- T-003 §3 documented the cross-dialect concern: SQLite is lenient where Postgres is strict (transaction isolation, JSON operators, CHECK constraint enforcement details).
- The test runner uses the same SQLAlchemy connection provider; only the URL changes.

### State-of-the-art alternative

- **Same**: PostgreSQL prod + SQLite tests with shared SQL abstraction is the most common Python web pattern. Works because SQLAlchemy Core handles dialect differences.
- **Better**: PostgreSQL via Testcontainers / pytest-postgresql for tests — eliminates dialect drift. Slower CI (~5-10s container startup per test session) but production-faithful.
- **Best**: in-process Postgres via `pg-anywhere` or `embedded-postgres-python` — Postgres semantics at SQLite startup speed. Niche.

### Verdict — Acceptable

The pattern works. SQLite enables fast local CI. The dialect concerns T-003 §3 noted are real but bounded — tests catch most behavioral drift before merge.

The trade-off is **transaction-isolation semantics**: SQLite's `SERIALIZABLE` is single-writer; Postgres' default `READ COMMITTED` is multi-writer. Code that works in SQLite may have races in Postgres. T-003 documented this concern; no documented production race so far.

### Performance implication

CI speed: SQLite tests are ~5-10× faster than Postgres-via-Testcontainers. Acceptable trade-off for the audit-friendly pattern.

### Improvement direction (for Track 1c)

Optional: add a Postgres-via-Testcontainers integration test job in CI to catch dialect drift before prod. Track 1c.

## 2. 88 tables in single 3116-LOC `metadata.py`

### Current implementation

`packages/storage/src/ai_trading_agent_storage/metadata.py:1-3116`:
- 88 `Table(...)` declarations (grep proof: `grep -c "^[a-z_]* = Table" metadata.py = 88`).
- 33 `Index(...)` declarations.
- 58 `ForeignKey(...)` declarations.
- 47 JSON columns.
- 89 `MONEY_NUMERIC` columns + 8 `Numeric(20, 6)` columns (Decimal-discipline).
- Per-table CHECK constraints inline.

All 88 tables share a single SQLAlchemy `metadata` instance imported from `alembic_helpers.py`. Adding a table requires editing this one file.

### State-of-the-art alternative

- **One module per domain area**: `metadata/portfolio.py`, `metadata/forecast.py`, `metadata/ibkr.py`, `metadata/audit.py`, etc. Each imports the shared `metadata` instance. Alembic detects table additions across all imported modules.
- **One file per table**: maximum granularity; one `Table(...)` per file. Heavy-weight but search-friendly.
- **Domain-driven design with per-aggregate boundaries**: table groupings match conceptual aggregates (`Decision Package + Action Draft + Submission` in one module; `Forecast + Calibration + Prediction Diary` in another).

The current pattern is what SQLAlchemy looked like in tutorial examples ~2015. By 2025, most codebases of this size split.

### Verdict — Outdated

3116 LOC in one file:
- **Search-hostile**: finding `ibkr_executions` requires `grep` (88 tables, 47 JSON columns, hundreds of inline constraints).
- **Merge-conflict prone**: two PRs adding tables touch the same file.
- **Cognitive overload**: a developer making schema changes loads the entire file context.

T-003 §1 acknowledged "metadata.py is large" but presented it as intentional centralisation. T-039 verdicts the trade-off: centralisation is good for shared metadata instance + Alembic compatibility; bad for navigation + modification velocity.

The file is not broken — it works. But it's grown past the comfortable upper bound for a single Python module (~500-1000 LOC).

### Performance implication

Zero runtime cost. Pure code-organisation issue.

### Improvement direction (for Track 1c)

Split by domain area: `metadata/portfolio.py`, `metadata/forecast.py`, `metadata/ibkr.py`, etc. Each imports the same `metadata` instance. Alembic auto-discovers via `import` chain.

## 3. 53-migration linear Alembic chain

### Current implementation

`packages/storage/alembic/versions/`:
- 53 migration files (`0001_*.py` through `0053_*.py`).
- Linear chain — each migration's `down_revision` points to the previous.
- Filenames are numbered + descriptive: `0035_action_draft_belgian_tob.py`, `0053_reconciliation_audit_and_manual_review.py`.
- Largest migrations: ~13 KB (`0052_ibkr_submission_lifecycle_audit_and_executions.py`).
- T-003 §2 confirmed: no merges, no branches, no squash points.

Modern Alembic 1.13+ via `alembic.ini` + `env.py`. The migration helpers in `packages/storage/src/ai_trading_agent_storage/alembic_helpers.py` provide shared utilities (UNIQUE constraint helpers, CHECK constraint helpers).

### State-of-the-art alternative

- **Same**: linear chain is the standard Alembic pattern. Works for single-team / single-branch development.
- **Branch + merge**: Alembic supports merge points for parallel feature branches. More complex but unblocks parallel migration work.
- **Schema-first with codegen**: tools like `Atlas` (Ariga) or `dbmate` use SQL-first migrations + auto-generate Python models. Niche.

For a single-team codebase, linear chain is correct.

### Verdict — State-of-the-art

53 migrations across the project's lifetime (~6 months of active development per T-003 timeline) = ~9 migrations/month, manageable pace. Numbered + descriptive filenames make `git blame` + chronological audit trivial.

Linear chain enables deterministic deployment: `alembic upgrade head` always applies in the same order. No merge-conflict resolution needed.

The largest single migration (~13 KB) is well-scoped — it adds one feature's worth of tables. Not a megamigration.

### Performance implication

Migration runtime is one-time-per-deploy. With 53 sequential migrations on a fresh DB, full bring-up takes ~10-30 seconds. Acceptable.

### Improvement direction (for Track 1c)

None. This is one of the cleanest parts of the codebase.

## 4. 47 JSON columns

### Current implementation

`metadata.py` has 47 `Column(... JSON ...)` declarations (grep proof). Examples per T-019, T-020, T-023:
- `ibkr_submission_lifecycle.raw_callback_json` — full IBKR callback payload.
- `reconciliation_run_audit.error_details_json` — exception class + message.
- `forecast_predictions.predictor_inputs_json` — input features for forecasting.
- `decision_package_explanations.input_evidence_hash` — JSON-encoded provenance.

The pattern: per-table, the columns that need querying are typed columns (Numeric, Text, DateTime); the columns that need preservation but rarely-querying are JSON.

T-003 §1 documented the discipline: "JSON columns capture full provenance; typed columns enable indexed queries."

### State-of-the-art alternative

- **JSONB-native query patterns**: PostgreSQL's JSONB supports indexed queries (`->` operator, GIN indexes). Many codebases use JSONB primary + selectively-extracted typed columns. The current pattern is the inverse (typed primary + JSON for provenance).
- **EAV (entity-attribute-value)**: separate audit table with `entity_id, attribute_name, attribute_value`. Niche.
- **Append-only event log**: each state change is an event; current state is derived. Pure event-sourcing. Heavy.

For an audit-heavy codebase that needs forensic reconstruction but mostly queries by typed columns, the current pattern is correct.

### Verdict — Acceptable

47 JSON columns is high but defensible. Each JSON column serves a specific purpose (audit provenance, raw callback preservation, error details). They're not overflow buckets for poorly-modelled state.

The risk surfacing in T-019 §6 + T-020 §6 is that JSON columns can drift in shape over time. No CHECK constraints validate JSON structure. A future code change can write `{foo: 1}` where prior rows had `{bar: 1}`; the audit table accepts both silently.

### Performance implication

JSON columns are queried infrequently (mostly for forensic reads). No GIN indexes on any JSON column per T-003 §1 inventory. If JSON content ever becomes a query target, indexes would be needed.

### Improvement direction (for Track 1c)

Optional: Pydantic-validated JSON shapes per column (round-trip through a Pydantic model before insert). Catches shape drift early. Track 1c.

## 5. Decimal-as-string + `MONEY_NUMERIC` discipline

### Current implementation

89 `MONEY_NUMERIC` column declarations + 8 `Numeric(20, 6)` (the underlying type — `MONEY_NUMERIC = Numeric(20, 6)`).

Per T-001 / T-003:
- All money values use `Decimal` in Python.
- Storage type is `Numeric(20, 6)` — 20 digits total, 6 decimal places. Adequate for trillions-of-euros granularity.
- Wire format: JSON strings. Pydantic + Decimal field serialises to a string. Never a float.
- Tests assert string equality on monetary values.

The discipline is documented across T-019 §3 (order builder Decimal → float boundary), T-022 (Belgian tax `Decimal("0.0035")`), T-021 §3 (cost basis = `quantity × average_cost_per_unit` Decimal multiplication).

The only documented Decimal → float boundary crossing is at `ibapi.Order` (T-019 §3) — `ibapi` requires float for the wire protocol; the worker converts at the boundary.

### State-of-the-art alternative

This IS the state-of-the-art for financial systems. Alternatives:
- **128-bit integer cents**: store all money as integer cents. Faster than Decimal, no precision drift. Niche; loses sub-cent precision.
- **Postgres `MONEY` type**: stores currency + amount. Awkward in SQLAlchemy + locale-dependent.
- **Custom Decimal type with rounding policy**: explicit `Decimal('0.01')` quantisation. The current code does this via `_round_eur_cents` helpers (T-022 §1.4).

For Belgian Euro accounting + 6-decimal precision needs (FX rates, percentages, etc.), `Numeric(20, 6)` is exactly right.

### Verdict — State-of-the-art

This is the **single clearest piece of financial-system discipline** in the entire codebase. No floats anywhere except the `ibapi` boundary. No accidental precision drift. JSON serialisation is string-preserving end-to-end.

T-022 §1.4's HALF_UP rounding convention matches IBKR + EUR banking. T-001's `DomainBaseModel` rejects float assignment via Pydantic validators.

T-021's `fmtEUR` helper in the frontend (T-030 §4.2) is the only place where Decimal-as-string gets re-rendered (`Number(value).toFixed(2)` for display) — and even there, it's bounded to presentation rounding, not value derivation.

### Performance implication

Decimal arithmetic in Python is ~10× slower than float arithmetic. For the codebase's volume (thousands of operations per fire, not millions), negligible.

### Improvement direction (for Track 1c)

None. This is the gold standard.

## 6. 53 hand-coded `SqlAlchemy*Repository` classes in 6617-LOC `sql_repositories.py`

### Current implementation

`packages/storage/src/ai_trading_agent_storage/sql_repositories.py:1-6617`:
- 53 `class SqlAlchemy*Repository:` declarations (grep proof).
- Each repository: constructor takes `Connection + readiness_report`; methods are sync, return Pydantic / dataclass records.
- Repositories cited across reality docs: T-019 (3 audit repos), T-020 (4 repos), T-021 (3 repos), T-022 (1 repo), T-023 (2 repos), etc.

The pattern per T-003 §4:
```python
class SqlAlchemyActionDraftRepository:
    def __init__(self, connection, readiness):
        self._conn = connection
        self._readiness = readiness

    def append(self, entry: ActionDraftEntry) -> None:
        stmt = action_drafts.insert().values(...)
        self._conn.execute(stmt)
```

53 such classes × ~5-10 methods each × ~20 LOC per method ≈ 5,000-10,000 LOC. The single-file 6617-LOC count is the result.

### State-of-the-art alternative

- **Generic repository base class** with `append / get_by_id / list_by` methods + per-table subclass overrides. Reduces boilerplate.
- **Repository-per-aggregate**: one repository class per domain aggregate (e.g., `ActionDraftRepository` exposes methods across `action_drafts + action_draft_events + action_draft_history` tables). Better DDD fit.
- **No repository layer**: queries inline at use sites with the Connection. Simpler for small codebases; doesn't scale.
- **SQLAlchemy ORM with declarative mappers**: `session.add(obj)` / `session.query(Model).filter()` patterns. Less code but ORM trade-offs (T-037 §5).

The current 53-repository pattern has all the costs of explicit Repository Pattern (boilerplate) with limited benefits (no shared base, no aggregate grouping).

### Verdict — Outdated

The Repository Pattern is reasonable; the implementation is hand-coded mass.

6617 LOC in one file means:
- Adding a new repository requires editing this one file.
- Searching for a method like `append` across 53 classes is grep-by-line-number.
- Merge conflicts are frequent for any feature touching multiple repositories.

T-003 §4 already noted that repositories have similar structure. A generic base class with type-safe insert/select helpers would reduce the file size significantly.

### Performance implication

Pure code-organisation. Zero runtime cost.

### Improvement direction (for Track 1c)

Two options:
1. **Split per-domain**: `sql_repositories/portfolio.py`, `sql_repositories/forecast.py`, etc. Matches §2's metadata.py split.
2. **Generic base class**: `BaseRepository[TEntry, TTable]` with `append`, `get_by_id`, `list_by` generics. Subclasses add domain-specific queries only.

Track 1c.

## 7. No connection pooling configuration

### Current implementation

`packages/storage/src/ai_trading_agent_storage/connection_provider.py` uses SQLAlchemy's `create_engine(database_url)` with no pool tuning.

SQLAlchemy defaults:
- `pool_size = 5` (max connections in pool).
- `max_overflow = 10` (extra connections when pool exhausted).
- `pool_recycle = -1` (connections never recycled).
- `pool_pre_ping = False` (no liveness check before use).
- `pool_timeout = 30` seconds (waiting for a free connection).

The FastAPI app + worker each instantiate engines; the pool is per-process.

### State-of-the-art alternative

For a Postgres-backed FastAPI / worker app:
- `pool_size = 10-20` (matched to concurrent request count).
- `pool_pre_ping = True` (essential for cloud Postgres which may close idle connections).
- `pool_recycle = 300` (recycle every 5 minutes; defends against firewall-side connection drops).
- `pool_timeout = 5` seconds (fail fast on saturation).
- For multi-instance deployments: pgBouncer in front of Postgres for shared pooling.

### Verdict — Risky

Two specific risks:
1. **`pool_pre_ping = False`** — when Postgres closes an idle connection (RDS does this after 15 min idle), the next query against that connection raises an `OperationalError` instead of getting a fresh connection. With pre_ping enabled, SQLAlchemy detects + replaces silently.
2. **`pool_size = 5` + sync FastAPI threadpool of 40 (T-037 §2)** — 40 threads sharing 5 connections means most requests wait on pool, not on the database. Pool saturation is the real ceiling, not Postgres throughput.

Combined with T-037 §2 (sync routes), the request pipeline is: Starlette threadpool (40) → DB pool (5) → Postgres. The bottleneck is at the DB pool.

T-021 §3 documented `GET /portfolio/valuation/readiness` does 4-5 SQL queries per call (each blocking a pool connection for its query duration). At ~10 concurrent calls, the pool saturates.

### Performance implication

**Pool saturation at modest concurrent load.** Single user with one tab: zero issue. 10+ tabs all polling: visible queuing.

### Improvement direction (for Track 1c)

Tune SQLAlchemy `create_engine` kwargs: `pool_size=15, max_overflow=5, pool_pre_ping=True, pool_recycle=300, pool_timeout=5`. Critical pre-production change.

## 8. Single Postgres deployment (no read replicas, no caching layer)

### Current implementation

Per T-009 `infra-docker-and-compose.md`:
- Single `infra/docker/postgres/` container in `docker-compose.yml` for local.
- Production: single Postgres instance assumed (deployment specifics not in T-009 inventory).
- No read replicas (no `database_read_url` config variant).
- No caching layer (no Redis, Memcached, or in-process LRU caches at the SQL layer).

T-021 §6 documented that the dashboard polls 4-5 endpoints every 30s; each polls Postgres directly. T-028 §2.1 documented that the admin reconciliation page parallel-fetches 4 endpoints after every action; each hits Postgres. No caching tier deduplicates.

### State-of-the-art alternative

For a single-user trading app:
- **Same**: single Postgres is right-sized. No replicas needed.
- **Better**: add Redis for: session state (none currently; no auth either), API response caching (TTL-based), rate-limiting state.
- **Best**: read-replica Postgres for the dashboard read paths + write-primary for action drafts + IBKR submission. Scales reads horizontally.

For a moderate-scale (100+ user) trading app, all three would be needed. For the current single-user paper-trading scope, just adding Redis caching for the read-heavy endpoints would meaningfully reduce Postgres load.

### Verdict — Risky

The risk is throughput ceiling:
- Polling-heavy frontend (T-038 §8 — 18 setInterval sites) × multi-tab × multi-day uptime = many redundant queries against Postgres.
- No caching means every poll cycle re-runs the same SQL.
- Postgres at single instance is the single point of failure for the whole system.

For the intended scope (single user, paper trading, 10-50 RPS sustained), this is fine. At any scaling, it's the first wall.

### Performance implication

**~10× more Postgres queries than necessary** for the dashboard reads. With Redis caching at 5-second TTL on `GET /system/status` (polled every 30s by multiple components), Postgres load drops ~80%.

### Improvement direction (for Track 1c)

Add Redis for read-path caching. Optional + non-breaking. Track 1c.

## 9. Observations across the 8 questions

### 9.1 Pattern: discipline at the value layer; structure-debt at the code layer

The data layer is **rigorously disciplined** at the value level: Decimal-as-string (§5), append-only audit, hash chains, MONEY_NUMERIC pinning, foreign-key constraints (58 of them). At the code-organisation level, it has **scale debt**: 3116-LOC metadata.py, 6617-LOC sql_repositories.py.

The codebase prioritised getting the financial semantics right over organising the code. That's the correct ordering for a financial system — but the structural cost is now visible.

### 9.2 Pattern: missing tiers between Python and Postgres

Most production systems have intermediate tiers: Redis cache, pgBouncer, read replicas, query result caching at the ORM layer. This codebase goes Python → SQLAlchemy → Postgres directly with no caching layer. Simpler architecture, lower ceiling.

### 9.3 Pattern: the migration chain is the cleanest part of the codebase

53 numbered + descriptive Alembic migrations in linear order is one of the system's strongest organisational signals. Compare with `metadata.py` (3116 LOC, one file) — same domain, different structural choices.

### 9.4 What's clearly good

- Decimal-as-string discipline + `MONEY_NUMERIC`.
- 53-migration linear chain.
- Append-only audit pattern with UNIQUE constraints (per T-019, T-020 originating findings).
- Hash-chain provenance (per T-003, T-017).

### 9.5 What's clearly outdated

- 88 tables in single 3116-LOC `metadata.py`.
- 53 repository classes in 6617-LOC `sql_repositories.py`.

### 9.6 What's risky

- No connection pool tuning (defaults too low for FastAPI threadpool of 40).
- Single Postgres + no caching layer (poll-heavy frontend hits DB directly).

## 10. Summary table

| # | Question | Verdict | Track-1c priority |
|---|----------|---------|--------------------|
| 1 | Postgres + SQLite tests | Acceptable | Low (Testcontainers optional) |
| 2 | 88 tables in single file | Outdated | Medium (refactor) |
| 3 | 53-migration linear chain | State-of-the-art | None |
| 4 | 47 JSON columns | Acceptable | Low (Pydantic validation optional) |
| 5 | Decimal-as-string + `MONEY_NUMERIC` | State-of-the-art | None |
| 6 | 53 repositories in single file | Outdated | Medium (split or generic base) |
| 7 | No pool tuning | **Risky** | **High** (pre-prod) |
| 8 | Single Postgres + no caching | **Risky** | **Medium** (Redis) |

**Recommendations deferred to Track 1c.**

## 11. References

- `packages/storage/src/ai_trading_agent_storage/metadata.py:1-3116` (88 tables, 47 JSON columns, 89 MONEY_NUMERIC)
- `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:1-6617` (53 repositories)
- `packages/storage/src/ai_trading_agent_storage/connection_provider.py` (SQLAlchemy default pool)
- `packages/storage/alembic/versions/` (53 numbered migrations)
- `packages/storage/src/ai_trading_agent_storage/alembic_helpers.py`
- `packages/storage/pyproject.toml` (SQLAlchemy + Alembic + psycopg deps)
- T-003 `storage-package-and-migrations.md` (full storage reality)
- T-019 `ibkr-order-submission-lifecycle.md` (`MONEY_NUMERIC` + audit-table patterns)
- T-020 `ibkr-reconciliation-passes-a-b-c.md` (4 audit tables + UNIQUE constraints)
- T-021 `portfolio-valuation-and-cost-basis.md` §3 (multi-query dashboard reads)
- T-022 `belgian-tax-computation.md` §1.4 (Decimal HALF_UP discipline)
- T-023 `ai-explanation-and-budget.md` §4.1 (`claude_ai_budget_usage` table)
- T-037 `02-python-stack.md` §5 (SQLAlchemy Core verdicted acceptable) + §6 (psycopg v3 verdicted acceptable)
- T-038 `03-frontend-stack.md` §8 (18 setInterval sites — drives §8 here)
