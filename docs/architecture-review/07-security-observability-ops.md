# Architecture Review 07 — Security, Observability, Operations

**Scope.** Verdict-driven assessment of the security + observability + operations posture. 8 architectural choices covering authentication, network middleware, rate limiting, secrets, audit trails, logging, healthchecks/metrics, and backup/DR. Recommendations belong in Track 1c.

**Reality docs referenced**: T-006 (API infra — no auth in scope), T-007 (worker heartbeat), T-009 (.env handling), T-019 / T-020 (8+ audit tables), T-041 §7 (no APM — perf-side verdict carry-forward), T-053 (bandit baseline), T-054 (pip-audit fastapi CVE), T-058 (npm audit next umbrella).

## 0. Verdict matrix at a glance

| # | Architectural choice | Verdict |
|---|----------------------|---------|
| 1 | Zero authentication / authorization on API routes | **Risky** |
| 2 | No CORS / CSRF / TrustedHost middleware | **Risky** |
| 3 | No API rate limiting (only outbound EODHD-side detection) | **Outdated** |
| 4 | Plain-text env vars (no SecretStr, no vault integration) | **Outdated** |
| 5 | Append-only audit tables (8+ `*_audit` + UNIQUE idempotency keys) | **State-of-the-art** |
| 6 | Unstructured logging (`logging.basicConfig` only, no structlog) | **Outdated** |
| 7 | One `/health` endpoint, no `/ready`, no `/metrics`, no Prometheus | **Risky** |
| 8 | No backup / DR tooling (no pg_dump scripts, no restore procedures) | **Risky** |

**Distribution**: 1 state-of-the-art + 0 acceptable + 3 outdated + 4 risky. **Most risky verdicts of any architecture-review doc so far.** The codebase has near-perfect audit-trail discipline (§5) bolted onto near-zero network/operational defense.

## 1. Zero authentication / authorization

### Current implementation

Grep proof:
- `grep -rn "Depends\|HTTPBearer\|OAuth2\|JWT\|fastapi.security\|authenticate" apps/api/src` → **0** matches in production code.
- No `from fastapi.security import ...` imports anywhere.
- No `Authorization: Bearer ...` header handling.
- No session cookies, no CSRF tokens, no user model.
- No `current_user: User = Depends(get_current_user)` patterns.

T-006 documented the API surface; no auth was in scope. AGENTS.md §3.2 ("no order without explicit user approval") is enforced **client-side only** via the JA / BEVESTIG / Annuleer / Bevestig tokens (T-026 / T-025 / T-027 / T-028). The API itself accepts any incoming request as authentic.

### State-of-the-art alternative

For a multi-user FastAPI deployment in 2025:
- **OAuth2 + JWT**: industry standard for stateless authn. FastAPI has first-class `OAuth2PasswordBearer` support.
- **Session cookies with SameSite=Lax + CSRF tokens**: traditional but proven; better UX than bearer tokens.
- **Identity provider integration**: Auth0, Clerk, Supabase Auth, AWS Cognito. Outsources auth.
- **mTLS for service-to-service**: client certificate authentication.

For a single-user / single-tenant local app:
- **No auth + bind to 127.0.0.1**: acceptable. The host firewall is the boundary.
- **No auth + Tailscale / Cloudflare Tunnel**: acceptable for remote access by the operator.

### Verdict — Risky

The verdict depends entirely on **deployment topology**:
- **Localhost only**: zero auth is acceptable. The user runs the system on their own machine.
- **LAN exposed**: zero auth is **risky** — anyone on the LAN can call `POST /action-draft/{id}/approve` and approve orders (T-026 §4 already noted this).
- **Public internet**: zero auth is **catastrophic** — the API has 179 routes including order submission, settings mutation, watchlist confirmation. All open.

The codebase has no documented deployment-topology constraint. Per T-009 inventory, `infra/docker/docker-compose.yml` binds the API to all interfaces. There is no architecture-level enforcement that prevents wider exposure.

AGENTS.md mandates "every AI output must be schema-validated" but says nothing about user authn. The 4 audit tokens (BEVESTIG / JA / Annuleer / Bevestig) are user-action gates, not authn — they protect against accidental clicks, not against impersonation.

### Performance implication

Zero auth = zero overhead. Adding JWT validation = ~1ms per request. Negligible.

### Improvement direction (for Track 1c)

Define the deployment topology. If localhost-only, document it + bind to 127.0.0.1 explicitly. If anything broader, add OAuth2/JWT minimum. Track 1c.

## 2. No CORS / CSRF / TrustedHost middleware

### Current implementation

Grep proof:
- `grep -rn "CORSMiddleware\|TrustedHostMiddleware\|CSRF\|csrftoken" apps/api/src` → **0** matches.
- `grep -n "app.add_middleware\|middleware" apps/api/src/portfolio_outlook_api/main.py` → **0** matches.

`apps/api/src/portfolio_outlook_api/main.py` does NOT add any middleware. The FastAPI app accepts requests from any Origin header.

### State-of-the-art alternative

For an API consumed by a same-origin frontend:
- **`TrustedHostMiddleware`** with `allowed_hosts=["yourdomain.com"]` rejects requests with mismatching Host header.
- **`CORSMiddleware`** with `allow_origins=["https://yourdomain.com"]` controls cross-origin browser requests.
- **CSRF tokens** for any state-mutating request (POST/PUT/DELETE) if session cookies are used.

If the deployment is localhost-only:
- `TrustedHostMiddleware(allowed_hosts=["127.0.0.1", "localhost"])` — defends against DNS rebinding attacks even on localhost.

### Verdict — Risky

Two specific risks:
1. **DNS rebinding**: a malicious webpage can resolve `evil.attacker.com` to `127.0.0.1` and then issue cross-origin requests against the local API. Without `TrustedHostMiddleware`, the API answers. Combined with §1 (no auth), the attacker can call any route.
2. **CSRF (if cookies are added)**: not currently exposed because there are no cookies, but the moment auth is added, CSRF becomes a concern.

The risk surfaces are dormant today (no cookies, no public exposure) but the architecture provides zero defense-in-depth.

### Performance implication

Negligible (~0.1ms middleware overhead).

### Improvement direction (for Track 1c)

Add `TrustedHostMiddleware` minimum. Track 1c.

## 3. No API rate limiting

### Current implementation

Grep proof:
- `grep -rn "slowapi\|rate_limit\|RateLimit\|throttle" apps/api/src` → 5 matches, all in `market_data_sync.py` for **outbound** EODHD rate-limit handling. **Zero inbound rate limiting on API routes.**
- No `slowapi` or `fastapi-limiter` in dependencies.

A bug or malicious caller can:
- Call `POST /action-draft/{id}/approve` 1000 times per second (T-026 §9.2 already flagged "no idempotency key").
- Call `POST /predictor/backtest/run` to trigger thousands of synchronous backtests (T-024 §3.1 — though feature-gated off).
- Spam `GET /portfolio/valuation/readiness` to exhaust the DB pool (T-039 §7).

### State-of-the-art alternative

- **`slowapi`** (Starlette/FastAPI port of Flask-Limiter): decorator-based rate limits per route.
- **`fastapi-limiter`** + Redis: distributed rate limits across multiple workers.
- **Caddy / nginx / Cloudflare** in front of FastAPI: rate limiting at the edge.

For a local-only app: rate limiting prevents accidental loops in scripts / tests / bugs. Cheap insurance.

### Verdict — Outdated

In 2025, rate limiting is a standard middleware most APIs ship with. The codebase's defense against runaway clients is "trust the caller". Combined with §1 (no auth) + §2 (no CORS), a runaway in-browser script polling `POST /action-draft/{id}/approve` would be silently approving orders.

T-039 §7 + T-041 §2 already documented the DB pool saturation risk. Rate limiting would soft-cap the trigger.

### Performance implication

Rate-limit check ≈ 0.1ms per request. Negligible.

### Improvement direction (for Track 1c)

Add `slowapi` with per-route limits — especially for mutation routes. Track 1c.

## 4. Plain-text env vars (no SecretStr, no vault integration)

### Current implementation

Per T-061 + grep:
- `grep -rn "SecretStr\|get_secret\|aws.*secret\|vault" apps/api/src apps/worker/src packages/*/src` → **0** matches.
- Env vars (per T-061 inventory): `DATABASE_URL`, `CLAUDE_AI_API_KEY`, `EODHD_API_KEY`, `IBKR_*`, etc.
- T-061 §3 documented: `Anthropic()` SDK reads `ANTHROPIC_API_KEY` directly from OS env, NOT from the typed Pydantic field. The Pydantic field is a presence-gate only.
- `.env.example` shipped (T-009 §1 documented the bare-keys silent-drop finding).
- No `.env` checked into git (correct).
- No HashiCorp Vault, no AWS Secrets Manager, no Doppler integration.

When a `claude_ai_api_key` value flows through code:
- Loaded from env via `pydantic-settings` (plain str field).
- Passed through logs if logged (no `SecretStr` masking).
- Visible in `repr()` output, error tracebacks, etc.

### State-of-the-art alternative

- **`SecretStr`** (Pydantic): wraps secret values; `repr()` shows `**********`. Prevents accidental log leakage.
- **Vault / Secrets Manager**: external store. Code reads at startup; never persists locally.
- **Sealed Secrets / SOPS**: encrypted-at-rest in git. Decrypt at deploy time.

For a personal-use single-user app, env vars are the standard pattern. The risk is accidental leakage (log files, error reports, crash dumps).

### Verdict — Outdated

`SecretStr` is free to adopt and eliminates a class of leakage bugs. The codebase's pattern is what Python web apps looked like ~2018.

T-023 §1.1 documented that the `Anthropic()` SDK auto-reads `ANTHROPIC_API_KEY` from OS env — this means even if Pydantic wraps the typed field in `SecretStr`, the SDK separately reads the raw env. The pattern is upstream-imposed, not just codebase choice.

### Performance implication

Negligible.

### Improvement direction (for Track 1c)

Migrate API-key fields to `SecretStr`. Low-effort, high-defensive-value change. Track 1c.

## 5. Append-only audit tables — the standout state-of-the-art piece

### Current implementation

Per T-019 + T-020 + T-007:
- **8+ named `*_audit` tables** in `metadata.py`:
  - `ibkr_connection_audit` (T-006).
  - `scheduled_run_audit` / `worker_run_audit` (T-031 + T-032).
  - `cold_start_seed_audit` (T-012).
  - `watchlist_confirmation_audit` (T-025 — `actor="user"`).
  - `provider_call_audit` (EODHD + Anthropic).
  - `action_draft_audit` (T-018).
  - `ibkr_submission_audit` + `ibkr_submission_lifecycle` (T-019).
  - `reconciliation_audit` + `reconciliation_run_audit` + `unmatched_execution_audit` (T-020).
  - `manual_review_queue` (T-020).

Plus:
- **Append-only by doctrine**: per T-019 §5 + T-020 §6 — rows are inserted, never updated (except for two flip-points: `reconciliation_run_audit.complete_run` flipping `completed_at`, and `manual_review_queue.acknowledge` flipping `resolution_status`).
- **UNIQUE constraints for idempotency**: `ibkr_executions(ibkr_exec_id)`, `unmatched_execution_audit(ibkr_exec_id)`, `reconciliation_run_audit(reconciliation_run_id)`, etc.
- **Hash-chain provenance**: T-017 §5 — decision packages SHA-256 + `previous_package_hash` chain. T-018 — action drafts inherit DP hash.
- **Content-addressed event identity**: T-019 §6 — IBKR callbacks identified by `ibkr_exec_id` + `ibkr_perm_id`.

The intent (AGENTS.md): "Every decision must be logged", "All data must be backed up and restorable". The audit-chain implementation directly satisfies the "logged" half.

### State-of-the-art alternative

This IS state-of-the-art for financial-system audit:
- **Event sourcing**: append-only event log with state derived from event replay. Strongest form but heavyweight.
- **Temporal tables**: SQL standard for system-versioned history. Postgres support via extensions or app-level pattern.
- **Audit Triggers**: database-level triggers populating audit tables. Cheaper to maintain but harder to type-check.

The codebase uses **application-level append-only audit** — explicit `repo.append(AuditEntry(...))` calls from the business-logic side. Pattern is exactly right for the codebase's size + the need for forensic reconstruction.

### Verdict — State-of-the-art

This is the **single brightest spot** in the security + observability surface. The audit-chain discipline is rigorous:
- Every state change writes an audit row (per T-019 / T-020 documentation).
- UNIQUE constraints prevent duplicate processing.
- Hash chains enable forensic reconstruction of "what did the system know at time X".
- Dutch human-readable `details_dutch` + `notes_dutch` fields preserve narrative.

T-040 §2's 1% mock ratio reinforces this — the audit-chain code paths are tested with real DB writes.

The single critique-direction is asymmetry: the audit-trail discipline is matched by no other security layer. Authentication is the gap that makes the audit trail less actionable: knowing WHAT happened is rigorous; knowing WHO did it relies on `actor="user"` hard-coded strings (T-025 §7 + T-026 §5).

### Performance implication

Each state change has 1-3 extra inserts (per audit row). For the codebase's transaction volume, negligible.

### Improvement direction (for Track 1c)

None. Keep the discipline. Optionally: add a `request_id` / `actor_id` field once auth lands (§1) to enrich the audit trail.

## 6. Unstructured logging

### Current implementation

Grep proof:
- `grep -rn "structlog\|json_logger\|loguru" apps/api/src apps/worker/src` → 0 matches.
- `apps/worker/src/portfolio_outlook_worker/main.py:32`: `logging.basicConfig(level=logging.INFO)`.
- Per-module: `logger = logging.getLogger(__name__)` standard Python logging.
- Log output: plain text to stdout.

No structured logging means:
- Logs are unparseable by log-aggregation tools (Loki, Datadog Logs, ELK) without custom regex.
- No request-correlation IDs.
- No automatic context vars (user, account_id, run_id, etc.).
- Error context (exception, stack, args) is `logger.exception(...)`-style — text only.

### State-of-the-art alternative

- **`structlog`**: structured JSON logs with context vars. Standard Python pattern in 2025.
- **`loguru`**: simpler API, ships with sensible defaults.
- **`logging` + `python-json-logger`**: incremental upgrade path from stdlib.

For an observability-conscious codebase, structured logs are non-negotiable in 2025.

### Verdict — Outdated

The codebase's audit-chain discipline (§5) is the structured-logging equivalent **for state changes**. For everything else (errors, info events, debug traces), the codebase uses plain `logging.basicConfig`. This is 2015 Python.

The combination — append-only audit for state + unstructured logs for everything else — means the codebase has parseable history of WHAT happened but not parseable diagnostics for WHY a thing slow / errored / hung.

Each `logger.exception(...)` call in T-031 §3.1 / T-031 §3.4 ("exception silently swallowed") would benefit from structured context: `logger.exception("market_data_runner failed", extra={"account_id": ..., "run_id": ..., "step": "market_data"})`.

### Performance implication

Negligible.

### Improvement direction (for Track 1c)

Adopt `structlog`. The migration is incremental — old `logger.info(...)` calls still work; new calls add context vars.

## 7. One `/health` endpoint, no `/ready`, no `/metrics`

### Current implementation

`apps/api/src/portfolio_outlook_api/main.py:111`:
```python
@app.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    return get_health_response()
```

Plus `/ibkr/session/manual-readonly-status-check/readiness`, `/portfolio/setup/status`, `/portfolio/valuation/readiness` — domain-specific readiness probes, but **no generic `/ready` for app-level readiness**.

Missing:
- **`/ready`**: indicates the app is ready to accept traffic (DB pool warm, schema up-to-date, deps loaded). Distinct from `/health` which is liveness.
- **`/metrics`**: Prometheus-format metrics endpoint. Industry-standard for monitoring.
- **`/version`** (or `/build-info`): the running git SHA + build time. Useful for ops.

The worker has a `scheduler_state` heartbeat row (T-007 §4) that the API surfaces — that's the closest thing to a metrics endpoint. T-031 §4 + T-032 §4 + T-033 §4 all use `worker_run_audit` as the data source.

### State-of-the-art alternative

- **`/health`** (liveness) + **`/ready`** (readiness) + **`/metrics`** (Prometheus) is the Kubernetes-standard trio.
- **`prometheus-fastapi-instrumentator`** auto-generates the Prometheus exporter.
- **OpenTelemetry** (per T-041 §7) — broader tracing + metrics + logs.

### Verdict — Risky

For a Docker-deployed app, the absence of `/ready` and `/metrics` means:
- **No way for a load balancer or orchestrator to distinguish "starting up" from "broken"**: a load balancer probing `/health` during DB-migration startup gets a 200 before the schema is ready.
- **No way to monitor per-request latency / error rate / throughput** from outside the app.
- **No SLO measurement**: with no metrics, there's no way to define + measure "API p99 < 100ms".

Combined with §6 (unstructured logs), the codebase has minimal external observability. The single `/health` endpoint is necessary but insufficient.

### Performance implication

Adding `/metrics` has ~0.5ms overhead per request (for instrumentation hooks). Negligible.

### Improvement direction (for Track 1c)

Add `/ready` + `/metrics` (via `prometheus-fastapi-instrumentator`). Couples with T-041 §7 OpenTelemetry recommendation. Track 1c.

## 8. No backup / DR tooling

### Current implementation

Grep proof:
- `grep -rn "pg_dump\|backup\|restore" infra/ scripts/` → 0 matches.
- No backup-runner cron job.
- No documented restore procedure.
- No DR runbook.
- `infra/docker/docker-compose.yml` runs a local Postgres for dev; no production deployment manifests visible.

AGENTS.md explicitly mandates:
- "All data must be backed up and restorable"
- "A backup is not trusted until restore is tested"

These mandates have **no enforcement code in the repository**. The intent is recorded; the implementation is absent.

T-009 inventoried infra/docker; no backup tooling surfaced. T-061 documented credentials infra; no DR pattern documented.

### State-of-the-art alternative

For a Postgres-backed Docker app in 2025:
- **`pg_dump` scheduled cron**: minimal. Stores dumps to local disk or S3.
- **`pgBackRest`**: incremental + point-in-time recovery. Production-grade.
- **Managed Postgres** (AWS RDS, Cloud SQL, Supabase): automated backups + restore. Outsources the problem.
- **WAL-G**: WAL-shipped continuous backup to S3.

For local-only deployments: even a `pg_dump > backup-$(date).sql` cron is better than nothing.

### Verdict — Risky

Two specific risks:
1. **AGENTS.md intent vs reality gap**: the mandate exists in writing; the implementation doesn't. Anyone relying on AGENTS.md as a guarantee of system properties is misled.
2. **Data loss risk**: every state-change row in the audit tables (§5) and every position / forecast / DP is in one Postgres instance. A drive failure, accidental `DROP TABLE`, or `git reset --hard` after an Alembic-run on prod could lose everything.

The single-user paper-trading scope reduces the immediate impact (re-syncing from IBKR could reconstruct positions), but the audit chains (§5) — which are the system's forensic record — would be permanently lost.

### Performance implication

`pg_dump` of a multi-GB DB is ~minutes; runs in the background. Negligible operational cost.

### Improvement direction (for Track 1c)

Add `pg_dump` to a daily cron. Document a restore procedure in a runbook. Test the restore. Track 1c — critical for any production posture.

## 9. Observations across the 8 questions

### 9.1 Pattern: audit-trail discipline + network-defense void

The asymmetry is the dominant story of T-042. The codebase has **state-of-the-art audit trails** (§5) — every state change captured, idempotency-keyed, hash-chained, forensically reconstructable. The same codebase has **zero authentication, zero CORS, zero rate limiting, zero secret masking, zero structured logging, no metrics endpoint, no backup tooling**. The discipline is at the trust-but-verify layer; the trust layer itself is absent.

### 9.2 Pattern: intent stronger than implementation

AGENTS.md sets clear mandates:
- "Every decision must be logged" — **satisfied** by §5 audit tables.
- "All data must be backed up and restorable" — **not satisfied** (§8).
- "A backup is not trusted until restore is tested" — **not satisfied** (§8).
- "No advice without audit trail" — **satisfied** by §5.

The mandates that are satisfied are well-satisfied. The mandates that are not satisfied are entirely absent. There's no middle ground.

### 9.3 Pattern: every gap is dormant at intended scope, severe beyond

At single-user / localhost / paper-trading: §1-§4 + §6-§8 are all invisible. At any broader deployment: each becomes a security incident waiting to happen.

### 9.4 What's clearly good

- 8+ append-only audit tables with UNIQUE idempotency keys (§5).
- Hash-chain provenance for decision packages + action drafts.
- Append-only-by-doctrine discipline applied consistently.

### 9.5 What's clearly outdated

- Plain-text env vars (no SecretStr).
- Unstructured logging (`logging.basicConfig` only).
- No API rate limiting.

### 9.6 What's risky

- Zero authentication on the API.
- No CORS / CSRF / TrustedHost middleware.
- Minimal healthcheck surface (no /ready, no /metrics).
- No backup / DR tooling.

## 10. Summary table

| # | Question | Verdict | Track-1c priority |
|---|----------|---------|--------------------|
| 1 | Zero authentication | **Risky** | **Critical** (define deployment topology) |
| 2 | No CORS / CSRF middleware | **Risky** | **High** (TrustedHostMiddleware) |
| 3 | No rate limiting | Outdated | Medium (slowapi) |
| 4 | Plain-text env vars | Outdated | Medium (SecretStr) |
| 5 | Append-only audit tables | State-of-the-art | None (preserve) |
| 6 | Unstructured logging | Outdated | Medium (structlog) |
| 7 | Minimal healthchecks | **Risky** | **High** (/ready + /metrics) |
| 8 | No backup / DR | **Risky** | **Critical** (AGENTS.md mandate violated) |

**Recommendations deferred to Track 1c.** Two **Critical** priority items (auth topology + backups) — the highest urgency level in the architecture review so far.

## 11. References

- `apps/api/src/portfolio_outlook_api/main.py:111` (the single /health endpoint)
- `apps/api/src/portfolio_outlook_api/main.py` (no middleware adds)
- `apps/worker/src/portfolio_outlook_worker/main.py:32` (`logging.basicConfig`)
- `packages/storage/src/ai_trading_agent_storage/metadata.py` (8+ `*_audit` tables)
- `infra/docker/docker-compose.yml` (compose stack, no backup/DR)
- T-006 `api-infrastructure-and-ai.md` (API infra; no auth in scope)
- T-007 `worker-orchestration-and-scheduling.md` (worker heartbeat)
- T-009 `infra-docker-and-compose.md` (env handling + .env.example finding)
- T-017 `decision-package-composition.md` (SHA-256 hash chain)
- T-019 `ibkr-order-submission-lifecycle.md` (3 audit tables)
- T-020 `ibkr-reconciliation-passes-a-b-c.md` (4 audit tables)
- T-025-T-028 (user-action tokens are client-side gates, not authn)
- T-031-T-035 (`worker_run_audit` heartbeat surface)
- T-041 `06-performance-and-scale.md` §7 (no APM — perf-side verdict)
- T-053 bandit baseline (1 B101 assert pattern)
- T-054 pip-audit baseline (1 HIGH fastapi MAL CVE)
- T-058 npm audit baseline (1 HIGH next umbrella)
- T-061 `settings-and-credentials-infrastructure.md` (env var inventory + `ANTHROPIC_API_KEY` auto-read finding)
- AGENTS.md (the mandates partially-satisfied by §5, unsatisfied by §8)
