# Reality — infra: Docker + Compose

**Scope.** The three per-app Dockerfiles, the Compose skeleton under `infra/docker/`, the `.env.example` environment-variable contract, and the deployment-intent doctrine. Sibling docs cover the build/CI/scripts layer (`build-ci-and-scripts.md`) and the web client itself (`web-api-client-and-text.md`).

Intent reference: `docs/deployment.md`.

## In-scope files

| File | Lines | Role |
|---|---:|---|
| `apps/api/Dockerfile` | 25 | Single-stage Python image for the FastAPI service |
| `apps/web/Dockerfile` | 27 | Three-stage Node 22 Alpine image for Next.js |
| `apps/worker/Dockerfile` | 21 | Single-stage Python image for the worker |
| `infra/docker/docker-compose.yml` | 70 | Four-service local skeleton (api / worker / web / postgres) |
| `infra/docker/.env.example` | — | Environment-variable contract (committed) |
| `infra/docker/README.md` | 79 | Operator runbook |

Intent: `docs/deployment.md` (197 lines).

## 1. Deployment doctrine (`docs/deployment.md`)

### Target environment + portability

- "Eerste deploymentdoel: Raspberry Pi 5 + NVMe SSD + Docker Compose + bedraad netwerk + actieve koeling + externe backups." (`docs/deployment.md:4`).
- "Latere migratie naar mini PC/zwaardere server zonder code rewrite." (`:7`).
- "Portabiliteit naar linux/arm64 en linux/amd64." (`:11`).
- "Geen Raspberry Pi-specific application logic may be introduced." (`:42`).

### Mandatory principles

- "Docker Compose als standaard runtime." (`docs/deployment.md:10`).
- "Gebruik van env-files en named volumes." (`:12`).
- "Geen hardcoded lokale paden." (`:13`).
- "Geen secrets in code." (`:14`).

### Backups

- "Dagelijkse backups + periodieke restore-tests; een backup geldt pas als betrouwbaar na geslaagde restore-test." (`:17`).
- "Database backups must be encrypted." (`:31`).
- "Trusted-backup status requires a successful restore test, not only a backup file." (`:32`).

### V1 release readiness gate (Task 177 / Slice 22) — `docs/deployment.md:50-90`

For the morning chain to run end-to-end against IBKR paper, the doc locks the following env-var contract:

- **Storage**: `STORAGE_ENABLED=true`, `STORAGE_DATABASE_URL=postgresql+psycopg://…`, `STORAGE_WRITES_ENABLED=true` (`:62-64`).
- **EODHD**: `EODHD_ENABLED=true`, `EODHD_API_KEY=<sleutel>` (`:67-68`).
- **IBKR**: `IBKR_ENABLED=true`, `IBKR_SYNC_ENABLED=true`, `IBKR_SYNC_HOST` / `IBKR_SYNC_PORT` / `IBKR_SYNC_CLIENT_ID` (`:71-73`).
- **Scheduler**: `SCHEDULER_ENABLED=true`, `SCHEDULER_TIMEZONE=Europe/Brussels`, `SCHEDULER_DAILY_BRIEFING_CRON="30 6 * * *"` (`:76-78`).
- **Six morning-chain leg flags** (`:81-86`): `MARKET_DATA_SYNC_ENABLED`, `FORECAST_SYNC_ENABLED`, `SUGGESTIONS_SYNC_ENABLED`, `DECISION_PACKAGES_SYNC_ENABLED`, `ACTION_DRAFTS_SYNC_ENABLED`, `DAILY_BRIEFING_SYNC_ENABLED`.
- **Audit-path flags**: `RECONCILIATION_SYNC_ENABLED=true`, `PREDICTION_DIARY_SYNC_ENABLED=true` (`:89-90`).
- **V1.1 §22**: `ENSEMBLE_WEIGHT_STRATEGY`, `PREDICTOR_BACKTEST_ENABLED`, `UNIVERSE_SET`, `UNIVERSE_SCAN_CACHE_TTL_HOURS` (`:152-155`), `CLAUDE_AI_BUDGET_MONTHLY_EUR` (default €50, `:160-161`), `CLAUDE_AI_API_KEY` (env-only, `:162`).

### Operator runbook

- "De manual approval-gate blijft altijd actief; een groene scorecard autoriseert geen order." (`docs/deployment.md:108-109`).
- "Geen draft vertrekt zonder approval." (`:98`).
- Action drafts are submitted via `POST /action-drafts/{id}/submit-to-ibkr-paper` (`:99-100`).

### Scope locks

- V1 scope-lock at Slice 22 — `docs/deployment.md:111-117`.
- V1.1 scope-lock at Slice 34 — `:190-197`.

## 2. `infra/docker/README.md` — operator runbook

Key invariants:

- "Deze map bevat een lokale development-skeleton voor AI-Trading-Agent." (`infra/docker/README.md:3`).
- Service topology (verbatim list, `:6-9`): `api` (FastAPI shell), `worker` (worker shell zonder jobs), `web` (eenvoudige Next.js UI), `postgres` (lokale PostgreSQL development service — **infrastructure only**).
- "TimescaleDB is bewust uitgesteld naar een latere taak om de foundation eenvoudig en stabiel te houden." (`:11`).

### Secret rules

- "`.env` is local-only and must never be committed." (`:29`).
- "Replace the placeholder password before running PostgreSQL." (`:30`).
- "Never use placeholder credentials in production." (`:31`).

### Phase boundaries (verbatim from `:65-72`)

> Geen live trading / Geen brokerkoppeling / Geen AI-calls / Geen externe marktdata-calls / **Geen database-integratie in API/worker runtime** / **Geen migraties** / Geen portfolio/setup persistence.

The README also states explicitly: "PostgreSQL can run locally for infrastructure preparation, but the application does **not** write to it yet." (`infra/docker/README.md:74`).

### Stale README finding — Phase 1c gap

The "Geen migraties" + "Geen database-integratie" claims at `infra/docker/README.md:65-79` **contradict the V1 readiness requirement at `docs/deployment.md:62-64`** (`STORAGE_ENABLED=true`, `STORAGE_WRITES_ENABLED=true`, `STORAGE_DATABASE_URL=postgresql+psycopg://…`). The README is locked to an earlier task (Task 22/23 era — Alembic skeleton landed but no migrations were run) and was never refreshed for the V1 readiness gate. Phase 4 task: refresh `infra/docker/README.md` to match the V1 contract.

### Operational commands documented

- `docker compose up -d postgres` (`:36`).
- `docker compose ps` (`:42`).
- `docker compose exec postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"` (`:48`).
- `docker compose down` (`:54`), `docker compose down -v` with warning that this deletes the volume (`:60, :63`).

## 3. `infra/docker/docker-compose.yml` — service-by-service catalogue (70 lines)

Compose v3.x-style file (no top-level `version:` since Compose 1.27+). Four services + one named volume.

### Service `api` (`infra/docker/docker-compose.yml:2-22`)

| Field | Value | File:line |
|---|---|---|
| Build context | `../..` (monorepo root) | `:6` |
| Dockerfile | `apps/api/Dockerfile` | `:7` |
| `env_file` | `.env.example` | `:8-9` |
| Env `API_ENVIRONMENT` | `${ENVIRONMENT:-development}` | `:11` |
| Env `API_PAPER_ONLY_MODE` | `${PAPER_ONLY_MODE:-true}` | `:12` |
| Ports | `${API_PORT:-8000}:8000` | `:13-14` |
| `depends_on` | `postgres: service_healthy` | `:15-17` |
| Healthcheck | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"` | `:19` |
| Healthcheck interval / timeout / retries | 30 s / 5 s / 3 | `:20-22` |
| `restart` | not set (defaults to `no`) | — |
| `networks` | not set (default) | — |
| Volumes | none | — |

### Service `worker` (`docker-compose.yml:24-37`)

| Field | Value | File:line |
|---|---|---|
| Build context | `../..` | `:26` |
| Dockerfile | `apps/worker/Dockerfile` | `:27` |
| `env_file` | `.env.example` | `:28-29` |
| Env `WORKER_ENVIRONMENT` | `${ENVIRONMENT:-development}` | `:31` |
| Env `WORKER_PAPER_ONLY_MODE` | `${PAPER_ONLY_MODE:-true}` | `:32` |
| Ports | none | — |
| `depends_on` | `api: service_healthy`, `postgres: service_healthy` | `:33-37` |
| Healthcheck | none | — |
| `restart` | not set | — |

### Service `web` (`docker-compose.yml:39-49`)

| Field | Value | File:line |
|---|---|---|
| Build context | `../..` | `:41` |
| Dockerfile | `apps/web/Dockerfile` | `:42` |
| `env_file` | `.env.example` | `:43-44` |
| Ports | `${WEB_PORT:-3000}:3000` | `:45-46` |
| `depends_on` | `api: service_healthy` | `:47-49` |
| Healthcheck | none | — |
| `restart` | not set | — |

### Service `postgres` (`docker-compose.yml:51-67`)

| Field | Value | File:line |
|---|---|---|
| Image | `postgres:16.4` | `:52` |
| `env_file` | `.env.example` | `:53-54` |
| Env `POSTGRES_DB` | `${POSTGRES_DB:-ai_trading_agent}` | `:56` |
| Env `POSTGRES_USER` | `${POSTGRES_USER:-ai_trading_agent}` | `:57` |
| Env `POSTGRES_PASSWORD` | `${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in infra/docker/.env (local only, never commit)}` — **fail-fast** if unset | `:58` |
| Ports | `5432:5432` (hard-coded host-side; no env override) | `:59-60` |
| Volumes | `postgres_data:/var/lib/postgresql/data` | `:61-62` |
| Healthcheck | `pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}` (CMD-SHELL) | `:64` |
| Healthcheck interval / timeout / retries | 30 s / 5 s / 5 | `:65-67` |
| `restart` | not set | — |

### Named volume

- `postgres_data` declared at `docker-compose.yml:70` (referenced by postgres service at `:61-62`).

### Health gating cascade

`postgres.healthcheck` → `api.depends_on.postgres.service_healthy` (`:15-17`) → `api.healthcheck` → `worker.depends_on.api.service_healthy` (`:33-37`) and `web.depends_on.api.service_healthy` (`:47-49`). Coherent topology — but web has no healthcheck of its own, worker has neither healthcheck nor restart policy.

## 4. `.env.example` — environment-variable contract

Bare keys (no `API_` / `WORKER_` prefix). Lines documented from the agent inventory:

| File:line | Variable | Value | Classification |
|---|---|---|---|
| `:1` | `POSTGRES_DB` | `ai_trading_agent` | Infrastructure (Postgres DB name) |
| `:2` | `POSTGRES_USER` | `ai_trading_agent` | Infrastructure (Postgres role) |
| `:3` | `POSTGRES_PASSWORD` | `replace-with-local-password-do-not-commit` | Secret placeholder (compose `:58` forces override) |
| `:4` | `API_PORT` | `8000` | Infrastructure (host port) |
| `:5` | `WEB_PORT` | `3000` | Infrastructure (host port) |
| `:6` | `ENVIRONMENT` | `development` | App-level (mapped into `API_ENVIRONMENT` + `WORKER_ENVIRONMENT`) |
| `:7` | `PAPER_ONLY_MODE` | `true` | App-level (mapped into `API_PAPER_ONLY_MODE` + `WORKER_PAPER_ONLY_MODE`) |
| `:14` | `STORAGE_ENABLED` | `true` | App-level (no prefix added by compose) |
| `:15` | `STORAGE_DATABASE_URL` | commented placeholder | Secret-adjacent |
| `:16` | `STORAGE_WRITES_ENABLED` | `true` | App-level |
| `:19` | `EODHD_ENABLED` | `true` | App-level |
| `:20` | `EODHD_API_KEY` | commented | Secret (no committed default) |
| `:23` | `IBKR_ENABLED` | `true` | App-level |
| `:24` | `IBKR_SYNC_ENABLED` | `true` | App-level |
| `:25` | `IBKR_SYNC_ACCOUNT_MODE` | `paper` | App-level |
| `:26-28` | `IBKR_SYNC_HOST` / `IBKR_SYNC_PORT` / `IBKR_SYNC_CLIENT_ID` | commented (`127.0.0.1` / `4002` / `42`) | Infrastructure |
| `:31-33` | `SCHEDULER_ENABLED` / `SCHEDULER_TIMEZONE` / `SCHEDULER_DAILY_BRIEFING_CRON` | `true` / `Europe/Brussels` / `30 6 * * *` | App-level |
| `:36-41` | `*_SYNC_ENABLED` (6 morning-chain legs) | `true` | App-level |
| `:44-45` | `RECONCILIATION_SYNC_ENABLED` / `PREDICTION_DIARY_SYNC_ENABLED` | `true` | App-level |
| `:52` | `CLAUDE_AI_BUDGET_MONTHLY_EUR` | `50` | App-level |
| `:56` | `CLAUDE_AI_API_KEY` | commented | Secret (no committed default) |
| `:57-58` | `CLAUDE_AI_EXPLANATION_MODEL` / `CLAUDE_AI_EXPLANATION_MAX_OUTPUT_CHARS` | `claude-haiku-4-5-20251001` / `2000` | App-level |
| `:61` | `UNIVERSE_SET` | `SP500` | App-level |
| `:64` | `PREDICTOR_BACKTEST_ENABLED` | `false` | App-level |

### Doctrine alignment (no secrets in code)

`.env.example` contains **no real secrets** — `EODHD_API_KEY`, `CLAUDE_AI_API_KEY`, `STORAGE_DATABASE_URL` are all commented out (`.env.example:15, :20, :56`). Password placeholder has explicit "do-not-commit" suffix (`:3`). Matches `docs/deployment.md:14` ("Geen secrets in code") and `infra/docker/README.md:29-31`.

## 5. Env-var → Settings-class mapping (and the critical mismatch)

The `.env.example` uses **bare keys** (no `API_` / `WORKER_` prefix). Both Settings classes declare prefix requirements:

- `apps/api/src/portfolio_outlook_api/config.py:255` — `env_prefix="API_"` (see `docs/reality/components/api-infrastructure-and-ai.md` §2).
- `apps/worker/src/portfolio_outlook_worker/config.py:79` — `env_prefix="WORKER_"` (see `docs/reality/components/worker-orchestration-and-scheduling.md` §3).

`docker-compose.yml` rewrites **only two** of the bare keys:

- `ENVIRONMENT` → `API_ENVIRONMENT` (`docker-compose.yml:11`) and `WORKER_ENVIRONMENT` (`:31`).
- `PAPER_ONLY_MODE` → `API_PAPER_ONLY_MODE` (`:12`) and `WORKER_PAPER_ONLY_MODE` (`:32`).

**Every other variable** in `.env.example:14-64` is loaded via `env_file` (`:8-9, :28-29, :43-44, :53-54`) without prefix rewriting. Because `pydantic-settings` uses `extra="ignore"` (`apps/api/.../config.py:257`, `apps/worker/.../config.py:81`), these bare keys are **silently dropped**.

### Consequence — V1 readiness cannot be satisfied as-shipped

Concrete examples of the mismatch:

| `.env.example` key | Compose rewrite | API field expected env var | Result |
|---|---|---|---|
| `STORAGE_ENABLED=true` (`:14`) | none | `API_STORAGE__ENABLED` | dropped → `storage.enabled=False` (default at `apps/api/.../config.py:13`) |
| `STORAGE_DATABASE_URL=…` (`:15`) | none | `API_STORAGE__DATABASE_URL` (nested via `env_nested_delimiter="__"`) | dropped → `storage.database_url=None` |
| `IBKR_ENABLED=true` (`:23`) | none | `API_IBKR_ENABLED` | dropped → `ibkr_enabled=False` |
| `EODHD_API_KEY=…` (`:20`) | none | `API_EODHD_API_KEY` | dropped → `eodhd_api_key=None` |
| `SCHEDULER_ENABLED=true` (`:31`) | none | `API_SCHEDULER_ENABLED` | dropped → `scheduler_enabled=False` |
| `CLAUDE_AI_API_KEY=…` (`:56`) | none | `API_CLAUDE_AI_API_KEY` | dropped → `claude_ai_api_key=None` |

The same goes for the six morning-chain `*_SYNC_ENABLED` flags and the V1.1 §22 vars.

**Phase 1c finding (major):** `infra/docker/` cannot satisfy the V1 readiness gate documented in `docs/deployment.md:62-90` as-shipped. The release-readiness scorecard at `apps/api/.../release_readiness.py` (see `api-infrastructure-and-ai.md` §8) would emit `BLOCKER_STORAGE_NOT_CONFIGURED`, `BLOCKER_EODHD_NOT_CONFIGURED`, `BLOCKER_IBKR_NOT_ENABLED`, `BLOCKER_SCHEDULER_DISABLED`, and the six morning-chain blockers, regardless of `.env.example` contents.

**Fix candidates** for Phase 4: either (a) rename every key in `.env.example` to its prefixed form (`API_STORAGE__ENABLED`, `WORKER_STORAGE__ENABLED`, etc.), or (b) extend `docker-compose.yml` `environment:` blocks to remap each bare key into its prefixed alias. Option (a) is simpler but couples the `.env.example` to the two-service split; option (b) keeps the bare keys readable for operators.

### Second `.env`-loading gap

`docker-compose.yml`'s `env_file` references point at the **committed** `.env.example`, not the local `.env` (`:9, :29, :44, :54`). The README workflow at `infra/docker/README.md:18-26` instructs operators to `cp .env.example .env` and edit — but Compose's `env_file` is permanently pinned to the committed file. The local `.env` is only consumed by Compose's `${VAR:-default}` interpolation, which is used for exactly **6 substitutions**: `ENVIRONMENT`, `PAPER_ONLY_MODE`, `POSTGRES_DB`, `POSTGRES_USER`, `API_PORT`, `WEB_PORT`, plus the required `POSTGRES_PASSWORD` (`docker-compose.yml:11-14, :31-32, :46, :56-58`).

**A locally edited `.env` value for `EODHD_API_KEY` will NOT reach the container** — the operator must also update `.env.example` (which would commit a secret) or rewrite the compose file to use `${EODHD_API_KEY}` interpolation explicitly.

## 6. `apps/api/Dockerfile` (25 lines)

Single-stage build, monorepo-root context.

| Concern | Value | File:line |
|---|---|---|
| Base image | `python:3.12-slim` | `apps/api/Dockerfile:5` |
| System deps | none installed | (absent) |
| `WORKDIR` | `/app` | `:7` |
| COPY order | packages first (`domain`, `storage`, `portfolio`) then API source — cache-friendly | `:11-13, :20-21` |
| Package install | `pip install --no-cache-dir -e ./packages/{domain,storage,portfolio}` | `:14-17` |
| API install | `pip install --no-cache-dir ./apps/api` (non-editable; no `[dev]` extras) | `:22` |
| User | **root** (no `USER`) | (absent) |
| EXPOSE | `8000` | `:24` |
| CMD | `["uvicorn", "portfolio_outlook_api.main:app", "--host", "0.0.0.0", "--port", "8000"]` | `:25` |
| ENTRYPOINT | not set | — |
| Healthcheck | lives in `docker-compose.yml:19`, not in Dockerfile | — |

**Phase 1c observations**: no multi-stage build → editable installs ship into the final image; no non-root user (contradicts hardening best-practice for the Pi 5 target); no `pip install --upgrade pip`; no `psycopg` system deps (presumably OK because `psycopg[binary]` is used, but unverified here).

## 7. `apps/web/Dockerfile` (27 lines)

**Three-stage build** (`deps` / `builder` / `runner`), all on `node:22-alpine`.

| Stage | File:line | Purpose |
|---|---|---|
| `deps` (`:5`) | `:5-9` | `npm ci` / `npm install` against the committed lockfile |
| `builder` (`:11`) | `:11-15` | Copy `node_modules` from `deps` + full `apps/web/` source, run `npm run build` |
| `runner` (`:18`) | `:18-27` | Final stage: copies `.next`, `public`, `package.json`, `node_modules` from `builder` |

| Concern | Value | File:line |
|---|---|---|
| Base image (all stages) | `node:22-alpine` | `:5, :11, :18` |
| System deps | none installed (no `apk add`) | (absent) |
| `WORKDIR` (all stages) | `/app` | `:6, :12, :19` |
| `deps` install | `if [ -f package-lock.json ]; then npm ci; else npm install; fi` | `:8` |
| Build command | `npm run build` | `:15` |
| Runner env | `NODE_ENV=production`, `NEXT_TELEMETRY_DISABLED=1` | `:20-21` |
| User | **root** in all stages | (absent) |
| EXPOSE | `3000` | `:26` |
| CMD | `["npm", "start"]` | `:27` |
| Healthcheck | none (no compose-level healthcheck for `web` either) | — |

### Phase 1c observation: no `output: "standalone"`

`apps/web/next.config.ts:3-6` lacks `output: "standalone"` (cross-reference `web-api-client-and-text.md` §5). As a consequence the runner stage at `apps/web/Dockerfile:25` copies the **entire** `node_modules` directory rather than the trimmed `.next/standalone` tree. This inflates the final image — directly counter to the Raspberry Pi 5 target lock at `docs/deployment.md:4`.

**Phase 4 candidate**: add `output: "standalone"` to `next.config.ts` and switch the runner stage to `COPY --from=builder /app/.next/standalone ./`.

## 8. `apps/worker/Dockerfile` (21 lines)

Single-stage build, monorepo-root context. Almost identical layout to `apps/api/Dockerfile`.

| Concern | Value | File:line |
|---|---|---|
| Base image | `python:3.12-slim` | `apps/worker/Dockerfile:5` |
| System deps | none | (absent) |
| `WORKDIR` | `/app` | `:7` |
| Package install | `pip install --no-cache-dir -e ./packages/{domain,storage,portfolio}` | `:12-15` |
| Worker install | `pip install --no-cache-dir ./apps/worker` (non-editable) | `:19` |
| User | **root** | (absent) |
| EXPOSE | none (worker has no HTTP listener) | — |
| CMD | `["python", "-m", "portfolio_outlook_worker.main"]` | `:21` |
| ENTRYPOINT | not set | — |
| Healthcheck | none (in Dockerfile nor compose) | — |

Header comment cites parity intent (`apps/worker/Dockerfile:1-3`): "any shared dataclass changes don't break the worker build" — hence the editable install of `portfolio`.

## 9. Cross-service patterns + gaps

### Common base, no shared layer

API + worker both ship `python:3.12-slim` (`apps/api/Dockerfile:5`, `apps/worker/Dockerfile:5`) and both independently install the three editable packages — there is no shared base layer.

### Volume sharing

Only `postgres` owns a volume (`postgres_data`, `docker-compose.yml:61-62, :70`). **No shared volume between API and worker** — e.g. no `var/` mount for the research-archive directories declared in `apps/api/.../config.py:23` (`archive_dir: "var/research-source-archive"`) and `:64` (`extracted_text_archive_dir: "var/research-extracted-text"`). Research archives are **not persisted across container restarts**.

### Network strategy

- **No explicit network declared.** All services rely on Compose's default bridge network.
- Inter-service DNS via Compose default: `api`/`postgres`/etc. resolve by service name.
- **No isolation** between data tier and app tier.

### Port observations

- API `${API_PORT:-8000}:8000`, web `${WEB_PORT:-3000}:3000`, postgres `5432:5432`. Postgres port is **hardcoded** (no env knob) — contradicts the "geen hardcoded paden" spirit of `docs/deployment.md:13` (port, not path, but same principle).

### Restart policy

- **No `restart:` declared on any service.** Compose default `no` applies → no auto-restart on failure. Contradicts the production framing in `docs/deployment.md:4-10`.

### Healthcheck coverage

- `postgres` has a healthcheck (`docker-compose.yml:64`).
- `api` has a healthcheck (`:19`).
- **`worker` has none.** **`web` has none.**

## 10. Gaps surfaced for Phase 4

Recorded in priority order:

1. **Settings prefix mismatch** (most serious — see §5). `.env.example` ships bare keys; Compose only prefixes 2 of them; the rest are silently dropped by `extra="ignore"`. V1 readiness cannot be satisfied as-shipped.
2. **`env_file` points at the committed example, not local `.env`** (§5). Operator workflow says "edit `.env`"; Compose says "load `.env.example`". The two don't meet.
3. **No IBKR Gateway service** in compose. `.env.example:26-28` documents host `127.0.0.1:4002` (paper TWS), but no `tws-gateway` service exists. Worker container cannot reach IBKR without `network_mode: host` or a TWS service definition — neither is configured.
4. **`infra/docker/README.md` is stale** (§2). Claims "Geen migraties / Geen database-integratie" but V1 readiness requires both.
5. **Next.js standalone output not enabled** (§7). Heavy image — bad for Pi 5 target.
6. **No restart policies** on any service (§9). A transient OOM on Pi 5 leaves the system down.
7. **Worker + web have no healthcheck** (§9). The Compose dependency cascade is half-built.
8. **Postgres port is hardcoded `5432:5432`** (§9). Should be `${POSTGRES_PORT:-5432}:5432`.
9. **All containers run as root** (§§6, 7, 8). Standard hardening lever unused.
10. **Research archives are not persisted** across restarts (§9). Either configure a named volume or document the loss.
