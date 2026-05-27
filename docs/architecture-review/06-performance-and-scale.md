# Architecture Review 06 — Performance and Scale

**Scope.** Verdict-driven assessment of the performance + scale architecture. 8 architectural choices covering server deployment, concurrency, caching, frontend refresh, background work, code organisation for hot paths, observability, and CDN/edge. Synthesises perf findings from T-037 / T-038 / T-039 / T-040 + adds new infra-perf observations. Recommendations belong in Track 1c.

**Reality docs referenced**: T-024 §3.1 (synchronous backtest API), T-037 §2-§3 (async incoherence + threadpool), T-038 §5+§8 (no state mgmt + polling), T-039 §7-§8 (pool tuning + caching), T-040 §5 (no test parallelism — adjacent but distinct).

## 0. Verdict matrix at a glance

| # | Architectural choice | Verdict |
|---|----------------------|---------|
| 1 | Single-worker uvicorn (`apps/api/Dockerfile:25` — no `--workers`, no Gunicorn) | **Risky** |
| 2 | Threadpool-40 + DB-pool-5 mismatch (synthesises T-037 §2 + T-039 §7) | **Risky** |
| 3 | Zero caching layer (no Redis, no in-process LRU) | **Outdated** |
| 4 | Polling-everywhere frontend (18 setInterval sites) | **Outdated** |
| 5 | No background job queue (synchronous backtest + report generation) | **Outdated** |
| 6 | Largest modules (`status_routes.py` 4014 LOC, `sql_repositories.py` 6617 LOC, `apiClient.ts` 1879 LOC) | **Acceptable** |
| 7 | No profiling / APM / distributed tracing | **Risky** |
| 8 | No CDN / no static-asset caching / no edge runtime | **Acceptable** |

**Distribution**: 0 state-of-the-art + 2 acceptable + 3 outdated + 3 risky. **No state-of-the-art rating on perf** — the codebase prioritised correctness over performance, and the verdicts reflect that.

**Pattern: stacked scale ceilings**. Each choice is independently acceptable at single-user scale; combined, they cap throughput at ~100 RPS.

## 1. Single-worker uvicorn deployment

### Current implementation

`apps/api/Dockerfile:25`:
```dockerfile
CMD ["uvicorn", "portfolio_outlook_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**No `--workers` flag.** uvicorn defaults to `workers=1` — a single Python process. All requests hit one event loop + one Starlette threadpool.

No Gunicorn wrapper, no `--workers 4`, no `uvicorn[standard]` worker manager, no orchestration via Kubernetes HPA.

### State-of-the-art alternative

For production FastAPI:
- **`uvicorn --workers N`** where `N = (CPU cores × 2) + 1` per standard formula. Each worker is a separate process with its own event loop.
- **`gunicorn -k uvicorn.workers.UvicornWorker --workers N`** — preferred wrapper. Gunicorn handles graceful restarts, worker recycling, pre-fork. The de-facto FastAPI production deploy.
- **`uvicorn[standard]`** with `loop=uvloop` for ~30% perf boost per worker.

### Verdict — Risky

Single-worker uvicorn:
- **One Python process == one GIL** for the entire API. CPU-bound code (Pydantic validation, JSON serialization, anything that holds the GIL) serializes across all concurrent requests.
- **No worker isolation** — a crash takes down the entire API (no fallback workers).
- **No graceful restart** — `kill -HUP` restarts the only worker, dropping in-flight requests.

For single-user paper trading: fine. For any multi-user scenario or any production deploy: a hard ceiling.

T-037 §2 documented the 40-thread Starlette threadpool. That threadpool exists *within* the single worker. 40 threads × 1 worker = 40 concurrent request capacity, all sharing one GIL.

### Performance implication

**Hard throughput cap**. With one Python process:
- Pure-Python ops (Pydantic validate, JSON encode) serialize on the GIL.
- I/O ops (DB queries, HTTP calls) can interleave because the GIL releases on I/O.
- Effective concurrency ≈ I/O concurrency, not CPU concurrency.

A 4-CPU machine running 1 uvicorn worker is using 25% of available CPU at best.

### Improvement direction (for Track 1c)

`gunicorn -k uvicorn.workers.UvicornWorker --workers 4` (or formula-based). Track 1c.

## 2. Threadpool-40 + DB-pool-5 mismatch

### Current implementation

Synthesises two prior findings:
- **T-037 §2**: FastAPI runs 179 sync routes in Starlette's default threadpool of 40 threads.
- **T-039 §7**: SQLAlchemy `create_engine` uses default `pool_size=5, max_overflow=10` — max 15 simultaneous DB connections.

When 40 threads simultaneously hit DB-touching routes, **15 of them connect; 25 of them wait on the connection pool**. Most API routes touch DB at least once (`SqlAlchemy*Repository` calls). T-021 §3 documented `GET /portfolio/valuation/readiness` does 4-5 SQL queries per call.

### State-of-the-art alternative

Two paths:
- **Match the pool to the threadpool**: `pool_size=40, max_overflow=10`. Adds memory cost on the Postgres side (each connection ~5-10 MB).
- **Go async**: `async def` routes + `psycopg[binary,async]` + `pool_size=20`. Async routes don't hold connections during the await; pool throughput multiplies.
- **Add a connection broker**: pgBouncer in front of Postgres. Decouples app pool from DB connection count.

### Verdict — Risky

The mismatch is the **dominant perf bottleneck** in the API:
- At ≤5 concurrent DB-touching requests: no contention.
- At 6-15: max_overflow saturates; latency spikes.
- At 16+: requests wait on `pool_timeout` (30s default); eventually 503.

This is the kind of bug that's invisible in single-user dev + invisible in unit tests + appears the first time concurrent users land on the dashboard. T-039 §7 originating finding; T-041 elevates it from "tuning issue" to "stacked scale ceiling".

T-021 §3 cross-reference: the readiness endpoint that polls every 30s does 4-5 queries per call. Two open tabs polling = 8-10 connections held; three tabs = pool saturation.

### Performance implication

Under 5 concurrent calls: ~50ms/request typical (4-5 DB queries + serialisation). Above 5: queuing delay scales linearly. Above 15: hard fail.

### Improvement direction (for Track 1c)

Critical pre-production tuning per T-039 §7: `pool_size=15, max_overflow=5, pool_pre_ping=True, pool_recycle=300, pool_timeout=5`. Track 1c.

## 3. Zero caching layer

### Current implementation

Grep proof:
- `grep -rn "functools.lru_cache\|cachetools\|redis" apps/api/src apps/worker/src` returns **0** production caching uses (1 false-positive match in a docstring per T-039 §8 inventory).
- No `redis` in pyproject dependencies.
- No `@lru_cache` decorators on hot read paths.
- No HTTP response caching headers.

Every request re-derives state from Postgres. Dashboard polls re-query the same data every 30-60 seconds.

T-039 §8 documented: a single dashboard tab polls `/system/status` + `/portfolio/valuation/readiness` + `/reconciliation/status` + `/forecast/latest` every 30s — ~5 cache-able reads × 2 calls/min = 10 redundant DB hits per minute per tab.

### State-of-the-art alternative

- **Redis** for: shared cache, rate-limiting state, session state, queue backing. Standard.
- **In-process `functools.lru_cache`** for: pure functions of stable inputs (e.g., enum mappings, locked rate tables per T-022 §1). Free.
- **HTTP cache headers**: `Cache-Control: private, max-age=10` on read endpoints. Browser-side dedup.
- **Postgres materialized views**: pre-computed reads. Heavier.

### Verdict — Outdated

For a poll-heavy frontend (T-038 §8) talking to a small DB pool (T-039 §7), absence of caching makes the pool saturation problem dramatically worse. Each redundant poll holds a connection.

The codebase ships with zero caching primitives. This is 2015-era simplicity — fine for a prototype, hostile to any traffic pattern.

Note: T-024 §3.4 documented the **inverse-Brier auto-weight computation** in `GET /predictor/leaderboard` reads + computes per request. A `@lru_cache` on this would be a clear local win.

### Performance implication

~5-10× more Postgres queries than necessary for read-heavy workflows. T-041 §2's pool saturation magnifies the cost.

### Improvement direction (for Track 1c)

Add Redis for the polled read paths + `@lru_cache` on pure transforms. Track 1c.

## 4. Polling-everywhere frontend

### Current implementation

Synthesises T-038 §8:
- 18 independent `setInterval` sites in the frontend.
- Each component owns its own polling cycle (no shared cache, no dedup).
- Intervals: 30s (`<PortefeuilleRealtimeSection>` T-021 §3), 60s (`<ColdStartBanner>` T-025 §1.2), various other rhythms.

Cross-tab independence: T-025 §9.10 documented that two open tabs both polling `/watchlist/confirmation-state` produce 2× the API traffic of one tab.

### State-of-the-art alternative

- **TanStack Query** with `refetchInterval`: deduplicates polls across all subscribers + automatic cache. Per-window single request stream.
- **Server-Sent Events (SSE)**: server pushes updates when state changes; eliminates polling.
- **WebSockets**: bidirectional; overkill for one-way status updates.

T-038 §5 documented this gap; T-041 elevates to perf scope.

### Verdict — Outdated

The poll-everywhere pattern is straightforward to understand but it scales poorly:
- N tabs × M polling components × 1/interval = baseline traffic regardless of state changes.
- No "nothing changed, skip" semantics — every poll re-runs the full read.
- Combined with §2 (small DB pool) + §3 (no caching) → poll-induced pool saturation.

This is the **largest single user-facing scaling lever**: replacing poll with a shared query layer halves API traffic immediately.

### Performance implication

At 5 components × 30s polls × 10 open tabs = ~100 requests/minute baseline just for status. Each hits Postgres directly (§3).

### Improvement direction (for Track 1c)

TanStack Query. Same recommendation as T-038 §5. T-041 elevates to "perf-critical" priority.

## 5. No background job queue

### Current implementation

T-024 §3.1 documented `POST /predictor/backtest/run`:
- Accepts the backtest request.
- **Synchronously** invokes `run_predictor_backtest` (the 409-LOC walk-forward harness).
- Holds the API thread for the duration (potentially seconds to minutes depending on bars).
- Returns the completed run.

Grep proof:
- `grep -rn "celery\|rq\|dramatiq\|temporalio" apps/api/pyproject.toml apps/worker/pyproject.toml` returns 0 matches.
- No background-worker process beyond the APScheduler-driven worker (T-031 / T-032 / T-033).
- No queue broker (no Redis with RQ, no RabbitMQ).

Long-running ops that hit the API directly:
- Backtest run (`POST /predictor/backtest/run`).
- Annual tax report generation (T-022 §8 — currently not implemented, but if it were, would hit the same architecture).
- AI explanation generation (T-023 §1, currently synchronous; per call ~1-3 seconds).

### State-of-the-art alternative

- **Celery + Redis/RabbitMQ**: industry-standard Python background queue. Workers in separate processes.
- **RQ + Redis**: lighter than Celery; sufficient for most use cases.
- **Dramatiq**: modern alternative to Celery; better defaults.
- **Postgres-based**: `pgmq` or app-level "jobs" table with a polling consumer.

Even APScheduler (already in the codebase per T-031) could host immediate-job execution alongside cron-job execution.

### Verdict — Outdated

Synchronous long-ops on a sync FastAPI threadpool means each long-op holds a thread for its duration:
- A 30-second backtest holds 1 of 40 threads → -2.5% concurrent capacity for 30 seconds.
- Multiple concurrent backtests (operator + scheduled trigger + API client) → multi-thread occupation.

T-024 §3.1's feature gate (`predictor_backtest_enabled=False` default) reduces the exposure today, but the architectural choice remains.

### Performance implication

Long-running ops compete for the same threadpool as quick reads. Pool starvation during heavy ops.

### Improvement direction (for Track 1c)

Add a background queue (RQ + Redis is simplest). Move backtest + future annual-report-generation + AI explanation to async background. Track 1c.

## 6. Largest modules

### Current implementation

Largest by LOC:
- `packages/storage/src/ai_trading_agent_storage/sql_repositories.py`: 6617 LOC (T-039 §6).
- `packages/storage/src/ai_trading_agent_storage/repository_contracts.py`: 4353 LOC.
- `apps/api/src/portfolio_outlook_api/status_routes.py`: 4014 LOC.
- `packages/storage/src/ai_trading_agent_storage/metadata.py`: 3116 LOC (T-039 §2).
- `apps/api/src/portfolio_outlook_api/research_sources.py`: 1429 LOC.
- `packages/domain/src/portfolio_outlook_domain/enums.py`: 1180 LOC.
- `apps/web/lib/apiClient.ts`: 1879 LOC (T-038 §6).

Total: 22,608 LOC across 7 files = ~32% of identified production source.

### State-of-the-art alternative

- **One module per domain area / aggregate**: typical 200-800 LOC per file. Files become navigable.
- **Generated code in dedicated files**: e.g., enum.py with 1180 LOC could be auto-generated from a single source of truth.

The current pattern: a few mega-files + many medium files. Mega-files were already verdicted outdated in T-039 §2 + §6.

### Verdict — Acceptable

Module size is a code-organisation issue (T-039 already verdicted), not a runtime-perf issue. Python module loading is O(LOC) but happens once at startup; the 71k-LOC total ~1-second startup is well within tolerable bounds.

T-041 verdicts the perf-implication specifically:
- **Startup time**: ~1-2 seconds for the API (acceptable).
- **Memory**: each loaded module stays resident. ~100 MB Python runtime is typical.
- **Hot reload during dev**: large files take longer to re-parse on edit.

The runtime perf cost is minimal. T-041 lists this for completeness; the real cost is dev velocity (T-039 §6 + §2 already verdicted outdated for that reason).

### Performance implication

Negligible at runtime. Dev-cycle cost (Pyright/mypy/IDE indexing) is real but not catastrophic.

### Improvement direction (for Track 1c)

Per T-039 §2 + §6: split by domain. Same recommendation; T-041 confirms low-priority for perf alone.

## 7. No profiling / APM / distributed tracing

### Current implementation

Grep proof:
- `grep -rn "newrelic\|datadog\|opentelemetry\|sentry\|profile\|cProfile" apps/api/pyproject.toml apps/worker/pyproject.toml` returns 0 matches.
- No structured-log instrumentation (per T-007 worker reality: `logger = logging.getLogger(__name__)` standard logging).
- No `/metrics` Prometheus endpoint.
- No `/health` endpoint with timing data.
- No request-ID injection / correlation IDs.

When the system slows down, the only diagnostic surface is:
- Application logs (text-based, unstructured).
- Postgres' own slow-query log (operator-side, not application-visible).
- `worker_run_audit` rows (per T-031 / T-032 / T-033) — captures wall-clock duration per fire, no per-step breakdown.

### State-of-the-art alternative

- **OpenTelemetry**: distributed tracing. FastAPI auto-instrumentation via `opentelemetry-instrumentation-fastapi`. Standard.
- **Sentry**: error tracking + performance monitoring. Lightweight integration.
- **Datadog / New Relic / Honeycomb**: full APM. Heavier.
- **Prometheus + Grafana**: metrics endpoint + dashboards. Open-source self-hosted.
- **Structured logging** (`structlog`): JSON logs with context vars. Foundation for everything else.

For a 2025 web service, some form of telemetry is mainstream. The codebase has none.

### Verdict — Risky

Two risks:
1. **Operational blindness**: when (not if) a perf regression lands, identifying the slow query / slow route / slow function requires manual log spelunking.
2. **Slow-burn issues invisible**: pool saturation (§2), cache misses (§3), poll storms (§4) — none of these surface in audit-row data. They'd require a perf-monitoring layer to detect.

The single-user paper-trading scope hides this risk today. At any scaling, telemetry becomes essential.

### Performance implication

Adding OTel instrumentation has ~1-5% overhead. The diagnostic value vastly outweighs the cost.

### Improvement direction (for Track 1c)

Add `opentelemetry-instrumentation-fastapi` + `opentelemetry-instrumentation-sqlalchemy` + an OTel collector. Free open-source path. Track 1c.

## 8. No CDN / static-asset caching / no edge runtime

### Current implementation

T-009 frontend infra inventory + `apps/web/next.config.ts`:
- No `Cache-Control` headers set programmatically.
- No `next/image` configuration with CDN domain.
- No deployment to Vercel Edge / Cloudflare Workers / similar.
- No service worker.
- Self-hosted (per T-009 `infra/docker/`).

The frontend bundle (Next.js production build output) ships from the same origin as the API. Every page load fetches the bundle from the origin Postgres-host machine.

### State-of-the-art alternative

- **Vercel** deploys: Edge Network CDN by default. `next start` runs on Edge Functions.
- **Cloudflare Workers + Pages**: similar pattern, different provider.
- **Self-hosted CDN** (CloudFront, Fastly): cache-Control + invalidation.
- **Service Worker**: offline-first dashboard, asset caching.

### Verdict — Acceptable

For single-user single-location deployment, no CDN is fine. The user is on one network; round-trip to the origin is ~10-50ms. CDN overhead would be larger than the savings.

For multi-user deployment: CDN becomes essential. But that's a scaling decision, not a default-deploy concern.

T-038 §1's Next.js 15 + App Router is CDN-friendly out of the box; the choice to not deploy to a CDN is operator-side, not architectural.

### Performance implication

Self-hosted: ~50-200ms first-load for the JS bundle. With a CDN: ~20-50ms. For a single user logging in once a day, the difference is invisible.

### Improvement direction (for Track 1c)

Optional for now. If multi-user adoption happens, deploy via Vercel or Cloudflare Pages. Track 1c.

## 9. Observations across the 8 questions

### 9.1 Pattern: stacked scale ceilings

Each of §1 (single-worker), §2 (small pool), §3 (no caching), §4 (poll-heavy), §5 (sync long-ops) is independently acceptable at single-user scale. **Combined**, they cap the API at ~100 RPS. The ceilings compound:
- Pool saturation (§2) at modest concurrency
- × No caching (§3) means every poll hits the pool
- × Poll-heavy frontend (§4) means many redundant queries
- × Single worker (§1) means one GIL serializing everything
- × Long ops blocking the threadpool (§5) when scheduled jobs fire

### 9.2 Pattern: zero observability

§7 (no APM) + the missing test coverage of T-040 §4 means the codebase has limited visibility into what's slow OR what's tested. Two adjacent observability gaps.

### 9.3 Pattern: defensible at intended scale, fragile beyond

The codebase is built for single-user paper trading. At that scale, every "outdated" + "risky" verdict here is invisible. At any scaling (2+ concurrent users, multiple browser tabs, or a public-facing deployment), every one of them becomes a P0.

T-041 doesn't recommend immediate fixes — Phase 1c will decide what scale the system targets and whether to invest. T-041 surfaces the choices that determine the ceiling.

### 9.4 What's clearly good

- Decimal-as-string + MONEY_NUMERIC (T-039 §5) eliminates a class of perf-corruption bugs.
- 53-migration linear Alembic chain (T-039 §3) means no schema-perf surprises.
- 1% mock ratio (T-040 §2) means real perf characteristics show up in tests.

### 9.5 What's clearly outdated

- Polling-everywhere frontend.
- Zero caching layer.
- Synchronous long-ops on the API thread.

### 9.6 What's risky

- Single-worker uvicorn.
- Threadpool-40 + pool-5 mismatch.
- No profiling / APM / tracing.

## 10. Summary table

| # | Question | Verdict | Track-1c priority |
|---|----------|---------|--------------------|
| 1 | Single-worker uvicorn | **Risky** | **High** (pre-prod: gunicorn + workers) |
| 2 | Threadpool-40 + pool-5 mismatch | **Risky** | **High** (pre-prod: pool tuning) |
| 3 | Zero caching layer | Outdated | **High** (Redis) |
| 4 | Polling-everywhere frontend | Outdated | **High** (TanStack Query) |
| 5 | No background job queue | Outdated | Medium (RQ + Redis) |
| 6 | Largest modules | Acceptable | Low (T-039 §2/§6 already covers) |
| 7 | No profiling / APM | **Risky** | **High** (OpenTelemetry) |
| 8 | No CDN / edge | Acceptable | Low (scale-decision) |

**Recommendations deferred to Track 1c.** Five of eight are **High** priority — perf is the most-improvement-needed track of the architecture review so far.

## 11. References

- `apps/api/Dockerfile:25` (single-worker uvicorn CMD)
- `apps/api/main.py` (FastAPI app init)
- `apps/web/Dockerfile`, `apps/worker/Dockerfile`
- `infra/docker/docker-compose.yml` (compose stack with Postgres)
- `apps/api/src/portfolio_outlook_api/status_routes.py:1-4014` (largest API module)
- `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:1-6617` (largest storage module)
- `packages/storage/src/ai_trading_agent_storage/metadata.py:1-3116` (88-table single-file schema)
- `apps/web/lib/apiClient.ts:1-1879` (largest frontend module)
- T-024 §3.1 (synchronous backtest run)
- T-037 §2 (Starlette threadpool of 40 + 0 async routes)
- T-037 §3 (AsyncIO unused)
- T-038 §5 (no state management)
- T-038 §8 (18 polling sites)
- T-039 §7 (SQLAlchemy pool defaults)
- T-039 §8 (single Postgres + no caching)
- T-040 §4 (no test coverage measurement — adjacent observability gap)
- T-021 §3 (`<PortefeuilleRealtimeSection>` 30s polling + 4-5 SQL queries per call)
- T-025 §9.10 (poll-cycle independence across tabs)
- T-031 / T-032 / T-033 (system-tick workflows + `worker_run_audit` as the only perf-data source)
