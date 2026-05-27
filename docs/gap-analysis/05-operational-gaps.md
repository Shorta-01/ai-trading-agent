# Gap Analysis 05 — Operational Gaps

**Scope.** Operational / security / observability / deployment gaps. Distinct from T-044 (missing features), T-045 (incomplete implementations), T-046 (quant), T-047 (AI integration). Each entry uses the Track 1c 6-part format.

**Dominant gap-pair**: **define deployment topology + add auth layer** (Critical pre-deploy blocker) + **add backup tooling** (Critical — AGENTS.md mandate explicitly violated). These two combined define whether the system can leave its current "localhost paper-trading scope" without becoming a security incident waiting to happen.

## 0. Gap matrix at a glance

15 operational gap entries.

| # | Gap | Effort | MoSCoW |
|---|-----|--------|--------|
| 1 | Authentication topology undefined + zero auth on 179 routes | L | **Must** |
| 2 | Backup / DR tooling absent (AGENTS.md mandate violated) | M | **Must** |
| 3 | Single-worker uvicorn deployment | S | **Must** |
| 4 | SQLAlchemy pool tuning vs Starlette threadpool mismatch | S | **Must** |
| 5 | No `TrustedHostMiddleware` / CORS / CSRF middleware | S | **Must** |
| 6 | No API rate limiting | M | Should |
| 7 | Plain-text env vars / no `SecretStr` for API keys | S | Should |
| 8 | Unstructured logging (no `structlog`) | M | Should |
| 9 | Healthchecks: no `/ready`, no `/metrics`, no Prometheus | M | Should |
| 10 | No background job queue (Celery / RQ / Dramatiq) | L | Should |
| 11 | Zero caching layer (no Redis, no in-process LRU) | M | Should |
| 12 | No APM / OpenTelemetry / distributed tracing | M | Should |
| 13 | No CDN / no static-asset caching headers | S | Could |
| 14 | Settings Categories 1 + 3 + 4 + 5 infrastructure absent | L | Should |
| 15 | Connection-lost ghost-order recovery via Pass A reconciliation (not wired) | M | **Must** |

**Distribution**: 6 Must + 8 Should + 1 Could. **Effort**: 6 S + 6 M + 3 L. **Most Musts of any Track 1c doc so far** (matches T-042's 4-risky verdict severity).

## 1. Authentication topology undefined + zero auth on 179 routes

- **Name**: Define deployment topology + add authentication layer.
- **Why it matters**: T-042 §1 documented: 179 FastAPI routes. Zero `Depends(...)` for authentication. Zero JWT / OAuth2 / cookie session handling. No user model. The 4 user-action tokens (BEVESTIG / JA / Annuleer / Bevestig) are **client-side gates only** (T-026 §4 originating). Any caller who reaches the API can call any route, including order submission. The verdict depends entirely on **deployment topology**, which is currently undocumented. At localhost-only: acceptable. At LAN exposed: anyone on the LAN can approve orders. At public internet: catastrophic.
- **Where it would live**: Two-part decision + implementation: (a) **Decision**: lock the deployment topology in a new `docs/intent/deployment-topology.md` (localhost-only vs LAN vs public). (b) **If localhost-only**: bind uvicorn to `127.0.0.1` in `apps/api/Dockerfile:25` + document the constraint. (c) **If anything wider**: add `fastapi-users` or `OAuth2PasswordBearer` + JWT validation + user model + `Depends(get_current_user)` on all 179 routes.
- **Effort**: **Large**. Topology decision: small. Implementation: small for localhost-only path; large for auth implementation. Worst-case: full auth path.
- **Dependency**: This decision blocks T-044 §1 (performance review screen access), T-044 §7 (user-initiated reconciliation trigger), all 4 user-action token routes. Without a topology, every route's accessibility is undefined.
- **MoSCoW**: **Must**. Architectural blocker for ANY non-localhost deployment.
- **Originating reality**: T-042 §1 + T-043 §3.1 (cross-track critical priority).

## 2. Backup / DR tooling absent (AGENTS.md mandate violated)

- **Name**: Add backup tooling + restore procedure + test the restore.
- **Why it matters**: AGENTS.md explicitly mandates: **"All data must be backed up and restorable"** + **"A backup is not trusted until restore is tested"**. T-042 §8 grep-proved: no `pg_dump` scripts, no backup-runner cron job, no documented restore procedure, no DR runbook anywhere in the repo. **The mandate is recorded; the enforcement is entirely absent.** Combined with T-042 §5's audit-trail rigor — the system records every state change forensically but cannot survive a drive failure. The audit chains (the strongest part of the codebase per T-043 §2) would be permanently destroyed.
- **Where it would live**: New `infra/backup/` directory: `pg_dump_cron.sh` + `restore.sh` + `RUNBOOK.md`. Daily cron via system crontab (or APScheduler if shared infra). Backup destination: S3-compatible bucket + local mirror. Test the restore in CI via Testcontainers (T-040 §1 / §4 cross-ref).
- **Effort**: **Medium** — pg_dump scripting + S3 integration + test-restore-in-CI is medium scope.
- **Dependency**: None code-wise. Operational decision on backup destination.
- **MoSCoW**: **Must**. AGENTS.md mandate is explicit. Intent stronger than implementation is the dominant Track 1b finding (T-043 §1).
- **Originating reality**: T-042 §8 + T-043 §3.2 (cross-track critical priority).

## 3. Single-worker uvicorn deployment

- **Name**: Replace `uvicorn portfolio_outlook_api.main:app` with Gunicorn + multi-worker uvicorn.
- **Why it matters**: T-041 §1 documented `apps/api/Dockerfile:25` runs uvicorn with no `--workers` flag — single Python process, one GIL, one Starlette threadpool of 40 threads. **Effective concurrency = I/O concurrency, not CPU concurrency.** A 4-CPU machine runs 1 uvicorn worker = 25% CPU utilisation ceiling. CPU-bound ops (Pydantic validation, JSON encoding, Decimal math) serialize on the GIL across all concurrent requests.
- **Where it would live**: `apps/api/Dockerfile:25` — replace CMD with `gunicorn -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000 portfolio_outlook_api.main:app`. Or `uvicorn --workers 4` (uvicorn ≥ 0.30 supports this natively). Worker count formula: `(CPU cores × 2) + 1` per standard recommendation.
- **Effort**: **Small** — single Dockerfile line change + add `gunicorn` to `apps/api/pyproject.toml` dependencies. Tests should validate startup with multiple workers.
- **Dependency**: Item 4 (pool tuning) — without sufficient DB connections, more workers just queue on the DB. The two items are paired pre-prod work.
- **MoSCoW**: **Must**. Pre-prod blocker.
- **Originating reality**: T-041 §1 + T-043 §3.3.

## 4. SQLAlchemy pool tuning vs Starlette threadpool mismatch

- **Name**: Tune SQLAlchemy `create_engine` to match the Starlette threadpool capacity.
- **Why it matters**: T-039 §7 + T-041 §2 documented the dominant perf bottleneck: SQLAlchemy `create_engine` uses default `pool_size=5, max_overflow=10` (max 15 connections); Starlette schedules 179 sync routes (T-037 §2) into a 40-thread pool. **At 6-15 concurrent DB-touching requests: max_overflow saturates, latency spikes. At 16+ requests: 30-second `pool_timeout` wait → 503.** T-021 §3's `GET /portfolio/valuation/readiness` does 4-5 SQL queries per call — 2 tabs polling triggers pool saturation. Pool saturation is the throughput ceiling, not Postgres throughput.
- **Where it would live**: `packages/storage/src/ai_trading_agent_storage/connection_provider.py` — extend `create_engine(database_url)` call with tuned kwargs: `pool_size=15, max_overflow=5, pool_pre_ping=True, pool_recycle=300, pool_timeout=5`.
- **Effort**: **Small** — kwargs update + tests confirming the pool size + recycle behavior.
- **Dependency**: Item 3 (Gunicorn + workers) — multi-worker × pool_size = total DB connections. If workers=4 × pool_size=15 = 60 connections (Postgres max is typically 100 default; needs awareness).
- **MoSCoW**: **Must**. Pre-prod blocker; T-043 §3.4 cross-track critical.
- **Originating reality**: T-039 §7 + T-041 §2 + T-043 §3.4.

## 5. No `TrustedHostMiddleware` / CORS / CSRF middleware

- **Name**: Add minimum-viable middleware: `TrustedHostMiddleware` always; CORS + CSRF if cookies/auth added.
- **Why it matters**: T-042 §2 grep-proved: no middleware adds in `apps/api/src/portfolio_outlook_api/main.py`. The FastAPI app accepts requests with any `Host` header. **DNS-rebinding attack**: a malicious webpage resolves `evil.attacker.com` to `127.0.0.1` and issues cross-origin requests against the local API — the API answers. Combined with item 1 (no auth), the attacker can call any route from a victim's browser visiting a malicious page.
- **Where it would live**: `apps/api/src/portfolio_outlook_api/main.py` — add `app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)`. For localhost-only: `allowed_hosts=["127.0.0.1", "localhost"]`. For wider deployments: configured per env.
- **Effort**: **Small** — middleware add + settings field + tests.
- **Dependency**: Item 1 (topology decision drives `allowed_hosts` value).
- **MoSCoW**: **Must**. Defense-in-depth even for localhost-only (DNS rebinding doesn't care about network topology).
- **Originating reality**: T-042 §2.

## 6. No API rate limiting

- **Name**: Add `slowapi` rate limiting on mutation routes.
- **Why it matters**: T-042 §3 documented: zero inbound API rate limits. A bug or malicious caller can spam `POST /action-draft/{id}/approve` 1000 times/second (T-026 §9.2 no idempotency key). Or spam `GET /portfolio/valuation/readiness` to exhaust the DB pool (item 4). Or trigger thousands of backtests (T-024 §3.1). With no rate limit, the only defense is the OS-level connection limit.
- **Where it would live**: `apps/api/pyproject.toml` adds `slowapi` dep. New `apps/api/src/portfolio_outlook_api/rate_limit.py` defining per-route limits. `Depends(slowapi)` decorator on mutation routes.
- **Effort**: **Medium** — middleware setup + per-route configuration + Redis backing (for multi-worker rate limit coordination) + tests.
- **Dependency**: Item 11 (Redis for caching) provides the natural backing store for distributed rate limits.
- **MoSCoW**: Should — defense-in-depth.
- **Originating reality**: T-042 §3.

## 7. Plain-text env vars / no `SecretStr`

- **Name**: Migrate API-key + secret-bearing fields to Pydantic `SecretStr`.
- **Why it matters**: T-042 §4 grep-proved: zero `SecretStr` usage. Env vars (`DATABASE_URL`, `CLAUDE_AI_API_KEY`, `EODHD_API_KEY`, `IBKR_*`) flow as plain `str` through code. `repr()` outputs, error tracebacks, crash dumps, and accidental log statements can expose secrets verbatim. Per T-061 §3 + T-023 §1.1, `Anthropic()` SDK reads `ANTHROPIC_API_KEY` from OS env directly — even SecretStr-wrapping the Pydantic field doesn't fully solve (need T-047 §10 to explicitly pass `api_key=...`).
- **Where it would live**: `apps/api/src/portfolio_outlook_api/config.py` — change field types from `str | None` to `SecretStr | None` for `claude_ai_api_key`, `eodhd_api_key`, IBKR-related credentials. Update call sites that consume `.get_secret_value()`.
- **Effort**: **Small** — type change + call-site updates + tests.
- **Dependency**: T-047 §10 (Anthropic SDK direct injection) is the paired fix — without it, SecretStr wraps a value the SDK still reads from raw env.
- **MoSCoW**: Should — defensive hygiene.
- **Originating reality**: T-042 §4.

## 8. Unstructured logging

- **Name**: Migrate to `structlog` with JSON output + context vars.
- **Why it matters**: T-042 §6 grep-proved: only `logging.basicConfig(level=logging.INFO)` at `apps/worker/src/portfolio_outlook_worker/main.py:32`. Plain-text logs unparseable by Loki / Datadog Logs / ELK without custom regex. No request-correlation IDs, no automatic context vars (user, account_id, run_id). When the system slows down or errors, diagnostics rely on `grep | sort | uniq -c` over text logs.
- **Where it would live**: `apps/api/pyproject.toml` + `apps/worker/pyproject.toml` add `structlog`. New `apps/api/src/portfolio_outlook_api/logging_config.py` (and worker equivalent). Replace `logger = logging.getLogger(__name__)` with `logger = structlog.get_logger()`. Add request-correlation middleware that sets `bind_contextvars(request_id=...)`.
- **Effort**: **Medium** — incremental migration is supported (structlog interops with stdlib); but achieving full structured logs across 70+ kLOC takes effort.
- **Dependency**: Item 12 (OpenTelemetry) — both benefit from shared context-var infrastructure.
- **MoSCoW**: Should — observability foundation for items 9 + 12.
- **Originating reality**: T-042 §6.

## 9. Healthchecks: no `/ready`, no `/metrics`, no Prometheus

- **Name**: Add `/ready` (readiness) + `/metrics` (Prometheus) endpoints.
- **Why it matters**: T-042 §7 documented: single `/health` endpoint at `apps/api/src/portfolio_outlook_api/main.py:111` returns liveness only. **No way for a load balancer / orchestrator to distinguish "starting up" from "ready"**. No `/metrics` means no SLO measurement, no per-request latency / error rate / throughput dashboards. The single-user paper-trading scope hides this; any production posture requires both endpoints.
- **Where it would live**: `apps/api/src/portfolio_outlook_api/main.py` — add `@app.get("/ready")` checking DB migration readiness + IBKR gateway optional status. Add `apps/api/pyproject.toml` dep `prometheus-fastapi-instrumentator` + `Instrumentator().instrument(app).expose(app)` on startup.
- **Effort**: **Medium** — endpoints are small; the readiness logic (what counts as "ready") is the design question. Metrics instrumentation is bolt-on via the library.
- **Dependency**: None.
- **MoSCoW**: Should — operations enabler.
- **Originating reality**: T-042 §7.

## 10. No background job queue

- **Name**: Add a background job queue (RQ + Redis) for long-running operations.
- **Why it matters**: T-041 §5 documented: synchronous long-ops hold API threadpool slots for their duration. `POST /predictor/backtest/run` invokes `run_predictor_backtest` (T-024 §3.1) synchronously — a 30-second backtest holds 1 of 40 threads. Future annual tax report generation (T-044 §3 = T-022 §8) + AI explanation generation (T-023 §1.4, currently synchronous) would compound. With a background queue, long-ops move to dedicated workers; API thread returns immediately with a job-id.
- **Where it would live**: New `infra/redis/` (Redis backing). `apps/worker/` extension to run RQ workers. API routes return `{job_id, status_url}` immediately; clients poll `GET /jobs/{id}/status`.
- **Effort**: **Large** — Redis infra + RQ setup + job-status API + per-job-type worker logic + tests + UI status-polling integration.
- **Dependency**: Item 11 (Redis for caching) provides the natural same-Redis backing.
- **MoSCoW**: Should — needed for AI background work + tax report + future scheduled tasks.
- **Originating reality**: T-041 §5.

## 11. Zero caching layer

- **Name**: Add Redis caching for read-heavy endpoints.
- **Why it matters**: T-039 §8 + T-041 §3 documented: every request re-derives state from Postgres. Dashboard polls re-query the same data every 30-60 seconds. A single dashboard tab polls 4-5 read endpoints every 30s = ~10 redundant DB hits/minute. Combined with item 4 (pool saturation), redundant queries compound the bottleneck. T-024 §3.4's inverse-Brier auto-weight in `GET /predictor/leaderboard` is a clear `@lru_cache` candidate. Browser-side `Cache-Control: private, max-age=10` would dedup at the edge.
- **Where it would live**: New `apps/api/src/portfolio_outlook_api/cache.py` wrapping Redis. Decorators / dependencies for common read paths. Plus `@lru_cache` for pure transforms (enum maps, locked rate tables per T-022 §1).
- **Effort**: **Medium** — Redis client + cache decorator pattern + per-endpoint TTL + invalidation on mutations + tests.
- **Dependency**: Item 10 (background queue uses same Redis). Item 4 (pool tuning is the immediate fix; caching is the medium-term lever).
- **MoSCoW**: Should — ~10× DB-query reduction.
- **Originating reality**: T-039 §8 + T-041 §3 + T-038 §5 (frontend TanStack Query side — T-044 territory).

## 12. No APM / OpenTelemetry / distributed tracing

- **Name**: Adopt OpenTelemetry instrumentation for tracing + metrics.
- **Why it matters**: T-041 §7 + T-040 §9.3 documented: when (not if) a perf regression lands, identifying the slow query / slow route / slow function requires manual log spelunking. Pool saturation (item 4), cache misses (item 11), poll storms (T-044 §10) — none of these surface in audit-row data. Combined with T-040 §4 (no test coverage measurement), the codebase has minimal visibility into "what's slow" or "what's tested".
- **Where it would live**: `apps/api/pyproject.toml` + `apps/worker/pyproject.toml` add `opentelemetry-instrumentation-fastapi` + `opentelemetry-instrumentation-sqlalchemy` + `opentelemetry-exporter-otlp`. Auto-instrumentation captures FastAPI routes + SQLAlchemy queries + outbound HTTP. Plus a collector / Jaeger / Tempo backend.
- **Effort**: **Medium** — auto-instrumentation is config-driven; the collector backend setup is medium. Custom spans for hot paths add value.
- **Dependency**: Item 8 (structlog) — both benefit from shared context-var infrastructure.
- **MoSCoW**: Should — operations enabler.
- **Originating reality**: T-041 §7 + T-043 §5.2 (Track 1c high-priority).

## 13. No CDN / no static-asset caching headers

- **Name**: Deploy frontend assets via CDN (Vercel/Cloudflare) OR add `Cache-Control` headers.
- **Why it matters**: T-041 §8 documented: self-hosted Next.js build ships from the same origin as the API. Every page load fetches the bundle from the origin. No `next/image` CDN configuration. For single-user single-location: ~50-200ms first-load is acceptable. For multi-user or remote-access scenarios: CDN reduces this to ~20-50ms.
- **Where it would live**: Deployment-side decision (Vercel / Cloudflare Pages / CloudFront in front of the Docker container). OR in-code: `next.config.ts` headers configuration for static assets.
- **Effort**: **Small** — config-driven if CDN deploy is chosen; deployment-architecture decision otherwise.
- **Dependency**: Item 1 (topology decision) — CDN only meaningful for non-localhost.
- **MoSCoW**: Could — scale-decision; not critical to v1.
- **Originating reality**: T-041 §8.

## 14. Settings Categories 1 + 3 + 4 + 5 infrastructure absent

- **Name**: Build out settings infrastructure for Categories 1 (credentials) + 3 (thresholds) + 4 (notifications) + 5 (on-demand triggers).
- **Why it matters**: T-029 §8 + T-061 §2 documented the 5-category settings split. Category 2 (trading) has a UI (1 of 11 fields per T-044 §15). **Categories 1 + 3 + 4 + 5 are absent or scattered.** Several T-044/T-046/T-047 gaps depend on this infrastructure: AI budget extensions (T-047 §6), speculative-classification thresholds (T-044 §12), reconciliation tier thresholds (T-046 §14 cross-ref), user-trigger reconciliation (T-044 §7), on-demand backtest button (T-046 §12).
- **Where it would live**: Settings schema extension (per-category tables or extended `trading_settings` JSON) + API routes per category + dashboard UI navigation across categories. Audit trail (per T-042 §5 standard).
- **Effort**: **Large** — five-category settings is non-trivial infra.
- **Dependency**: Blocks T-044 §7, §12, §15 + T-046 §7, §14 + T-047 §6.
- **MoSCoW**: Should — many downstream Track 1c items depend.
- **Originating reality**: T-029 §8 + T-044 §15 + T-061 §2.

## 15. Connection-lost ghost-order recovery via Pass A reconciliation (not wired)

- **Name**: Ensure ghost-order recovery path is operational by wiring Pass A.
- **Why it matters**: T-019 §4 + T-020 §3 + T-045 §2 documented the corner case: if the IBKR socket drops mid-`place_order`, the order may or may not have been received. Pass A reconciliation (T-020 §3) is the documented recovery path — Pass A scans IBKR's recent executions for fills the worker missed. **But Pass A is also not wired** (T-035 + T-045 §2). Two compounding wiring gaps: T-045 §1+§2 wire the ticks, but specifically Pass A's role in ghost-order recovery is operationally critical and worth surfacing separately.
- **Where it would live**: T-045 §2 already covers wiring `IbkrReconciler.tick()`. T-048 §15 surfaces this as the **operational rationale** for the wiring fix — not just a routine reconciler tick, but the recovery path for IBKR socket failures.
- **Effort**: **Medium** — same as T-045 §2 (IbkrReconciler wiring); the additional work is testing the connection-lost-during-place_order scenario specifically to confirm Pass A heals it.
- **Dependency**: T-045 §1 (SubmissionSweep wiring) + T-045 §2 (IbkrReconciler wiring) — both items.
- **MoSCoW**: **Must**. The ghost-order risk is asymmetric (we sent an order, we don't know if it landed) and the only recovery is a Pass A scan that doesn't currently run.
- **Originating reality**: T-019 §4 + T-020 §3 + T-035 §6.5 + T-045 §2.

## 16. Cross-reference: gap coverage across Track 1c siblings

| Gap | Covered in T-048 | Cross-ref to | Reason |
|-----|------------------|--------------|--------|
| Trading settings full surface 10/11 fields (T-044 §15) | Item 14 (referenced) | T-044 §15 | UI surface covered there |
| User-initiated reconciliation trigger (T-044 §7) | Item 14 (referenced) | T-044 §7 | Surface lives in Category 5 |
| Auth on AI routes | Item 1 (implicit) | T-047 (implicit) | All routes under item 1's umbrella |
| Single `place_order` authority (T-045 §13) | No | T-045 §13 | Code-asymmetry; not operational |
| Quant infrastructure (T-046 §6-§13) | No | T-046 | Quant-specific |
| Case-B AnthropicTsModelProvider (T-047 §1) | No | T-047 §1 | AI-specific |

## 17. Summary

15 operational gap entries. **Distribution**: 6 Must + 8 Should + 1 Could. **Most Musts of any Track 1c doc** — matches T-042's risky-verdict concentration. Effort: 6 S + 6 M + 3 L.

The 6 Must items define the **pre-production readiness floor**:

- **Item 1**: Auth topology (L) — architectural blocker; everything else assumes a topology.
- **Item 2**: Backup tooling (M) — AGENTS.md mandate explicitly violated.
- **Item 3**: Multi-worker uvicorn (S) — pre-prod blocker.
- **Item 4**: Pool tuning (S) — pre-prod blocker.
- **Item 5**: `TrustedHostMiddleware` (S) — defense-in-depth even for localhost.
- **Item 15**: Ghost-order recovery via Pass A wiring (M) — financial-system safety floor.

**Combined Must-effort**: 1 L + 2 M + 3 S. The Large is item 1 (auth — but only large if non-localhost; otherwise small documentation work). The other 5 Musts are quick wins.

Sequencing recommendation: items 3 + 4 + 5 first (all Small, all pre-prod blockers). Then item 15 + items 1 + 2 (the critical-decision items). Then the 8 Shoulds (observability + caching + queues + settings infra) in MoSCoW order.

## 18. References

- T-019 `ibkr-order-submission-lifecycle.md` §4 (connection-lost ghost-order risk — item 15)
- T-020 §3 (Pass A reconciliation as recovery — item 15)
- T-021 §3 (poll-induced pool saturation — item 4)
- T-023 §1.1 + T-047 §10 (Anthropic SDK env-var read — item 7 paired fix)
- T-024 §3.1 (synchronous backtest — item 10)
- T-026 §4 (client-side JA token enforcement — item 1)
- T-029 §8 (settings 5-category split — item 14)
- T-035 §6.5 (ghost-order escape paths — item 15)
- T-039 §7 (SQLAlchemy pool defaults — item 4)
- T-039 §8 (no caching layer — item 11)
- T-040 §4 (no coverage — adjacent observability)
- T-041 §1 (single-worker uvicorn — item 3)
- T-041 §2 (threadpool/pool mismatch — item 4)
- T-041 §3 (zero caching — item 11)
- T-041 §5 (no background queue — item 10)
- T-041 §7 (no APM — item 12)
- T-041 §8 (no CDN — item 13)
- T-042 §1-§8 (T-048's primary source — 4 risky verdicts)
- T-043 §3 (Track 1c critical priorities — items 1 + 2)
- T-044 §7, §12, §15 (settings Category 5 + actions-area — item 14)
- T-045 §1, §2, §13 (operational items already-covered in T-045)
- T-061 §2 (settings infrastructure — item 14)
- AGENTS.md (the backup-mandate violator — item 2)
- `apps/api/Dockerfile:25` (single-worker uvicorn — item 3)
- `apps/api/src/portfolio_outlook_api/main.py` (no middleware adds — item 5)
- `apps/api/src/portfolio_outlook_api/main.py:111` (single `/health` — item 9)
- `packages/storage/src/ai_trading_agent_storage/connection_provider.py` (default pool — item 4)
