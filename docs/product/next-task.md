# Task 126 — Real IBKR connection, account-mode display, and durable Portefeuille grid

## Goal

Ship the first end-to-end runtime task that proves the foundation works. After this task, the user opens the dashboard, sees the colour-coded account-mode badge (Paper / Echte rekening) based on the real IBKR account the worker is connected to, and sees a Portefeuille grid populated with real positions and cash pulled from IBKR via TWS API. All data is persisted in Postgres tagged with the IBKR account ID, and survives a worker restart. This is the foundation every subsequent runtime task depends on.

No scheduling. No advice generation. No watchlist sync. No action drafts. No AI. Just: the IBKR connection works, the mode is detected and displayed honestly, and real broker data appears on a Dutch UI screen for the first time in the project's history.

## Owner-locked answers to open questions (2026-05-25)

1. **Precedence**: Task 126 takes precedence over the V1.1 / V1.2 prediction-engine staging. The V1.0–V1.8 roadmap in `asset-value-prediction-engine-roadmap.md` was authored under assumptions (paper-only V1, IBKR sync runtime-functional) that no longer hold. The prediction-engine V1.1 baseline cannot start until real broker data flows through durable storage; Task 126 reorders ahead. No replacement of the prediction-engine scope, just reordering.
2. **Worker activation**: Activate `apps/worker` as the IBKR session owner. This was locked in Task 122 preflight. The TWS API session is long-lived and callback-based; it must live in the worker, not in a FastAPI request handler. The API only reads the worker's state from durable storage. No IBKR network calls inside HTTP request handlers.
3. **Driver**: Inspect all five `pyproject.toml` files and `packages/storage/src/ai_trading_agent_storage/__init__.py`. If `psycopg`, `psycopg2-binary`, or `asyncpg` is already present, do not add another. If none is present, add `psycopg[binary]>=3.2` to `packages/storage`, `apps/api`, and `apps/worker`. Confirm `DATABASE_URL=postgresql://...` resolves end-to-end before integration tests.
4. **PR sequencing**: Single PR for the whole task (target 800–1400 LoC). If implementation exceeds ~1500 LoC during development, split into sequential **126a** (storage migration + worker gateway + worker tests + Dockerfile fixes) and **126b** (API routes + frontend badge + portefeuille wiring + frontend tests). Not parallel — 126a must merge before 126b opens.
5. **Doc discipline**: The brief is this file (`docs/product/next-task.md`). Codex must NOT create any new doctrine or audit file. Updates to `current-state.md`, `task-history.md`, and the new `## Task 126 product locks` section in `locked-decisions.md` happen inside the implementation PR. Analysis or design notes go in the PR description, not a separate file.

## Locked references (read these before starting)

- `docs/product/locked-decisions.md` — particularly the Task 88I block (AssetMaster + AssetListing, usable-cash contract, paper-only enforcement is being removed per this task), and the audit/Decimal/no-fake-data rules.
- `docs/product/release-1-functional-workflow-blueprint.md` — §IBKR sync engine.
- `docs/product/ibkr-tws-gateway-integration-preflight-task-122.md` — TWS API choice, worker-owned session, paper-only assertion (the assertion is being replaced; see "New locks from product brainstorm" below).
- `docs/product/current-state.md` — current Portefeuille status after Task 125C-B.
- `docs/product/version-1-backlog.md` — §F IBKR sync engine.

## New locks from product brainstorm (commit these into `locked-decisions.md` as part of this task, in a new `## Task 126 product locks` section)

1. **The software supports one configured IBKR account at a time. Account mode (Paper or Live) is whatever IBKR reports for that account. The software does NOT enforce paper-only.** The earlier paper-only-V1 lock is hereby retired. The user chooses which IBKR account to configure in Instellingen; the software works against whatever is configured.
2. **Account-mode detection is two-tier and audit-logged.** Primary detection: account ID prefix (`DU*` and `DF*` → Paper, anything else → Live). Behavioural cross-check at connect time: attempt a known paper-incompatible operation; the result must match the prefix-derived mode or the connection refuses with a Dutch error. Both checks write audit rows.
3. **Account-mode is visible everywhere via a persistent colour-coded indicator.** Neutral colour for Paper, amber/warm for Live. Indicator appears in the top strip of every screen. On app startup, the strip flashes the mode colour for ~500ms.
4. **Dutch wording in the rest of the UI is mode-neutral.** No "paper-order" vs "ECHTE order" text in the action flow. The indicator is the load-bearing cue.
5. **Every database row across the system carries `ibkr_account_id`.** Switching the configured account filters the dashboard but preserves all history.
6. **Per-submission mode verification** (reserved for future action-draft task; not implemented yet but the schema and field must be present so the audit log can record `account_mode_at_event` from Task 126 onward).
7. **No more in-memory module-level mutable stores in production paths.** When durable storage is unavailable, the system fails closed (returns a clear Dutch error), never falls back to an in-memory dict.

## In scope

### Worker — real IBKR connection

- Add `ib_insync>=0.9.86` to `apps/worker/pyproject.toml`.
- Add `psycopg[binary]>=3.2` to `apps/worker/pyproject.toml` and `apps/api/pyproject.toml` and `packages/storage/pyproject.toml`. Confirm `DATABASE_URL=postgresql://...` works end-to-end.
- New module: `apps/worker/src/portfolio_outlook_worker/ibkr_gateway.py`.
  - `class IbkrGateway`:
    - `connect(host, port, client_id, account_id) -> IbkrConnectionResult`. Uses `ib_insync.IB().connect()`. On success: calls `reqManagedAccts`, derives mode from prefix, runs behavioural cross-check (attempt `reqContractDetails` for a contract type known to be unavailable on paper accounts — e.g. a specific futures contract), asserts the two methods agree. Stores `account_id`, `account_mode`, `connection_id`, `verified_at` in worker state. Writes audit rows for both checks.
    - `disconnect()`.
    - `is_connected() -> bool`.
    - `get_account_mode() -> Literal["paper", "live", "unknown"]`. Re-reads from live session each call (no caching).
    - `fetch_account_summary() -> AccountSummary`. Reads `AvailableFunds`, `NetLiquidationValue`, `BuyingPower`, `TotalCashValue` per currency, with timestamps. Returns Decimal values.
    - `fetch_positions() -> list[Position]`. Per position: conid, symbol, exchange, currency, quantity (Decimal), avg_cost (Decimal), market_price (Decimal), market_value (Decimal), unrealized_pnl (Decimal), as_of timestamp.
    - All methods: typed Pydantic v2 returns, Decimal-only, no float.
- Configuration in `apps/worker/src/portfolio_outlook_worker/config.py`:
  - `IBKR_HOST` (default `127.0.0.1`).
  - `IBKR_PORT` (default `7497` for paper TWS, `7496` for live TWS — but do NOT hardcode mode from port).
  - `IBKR_CLIENT_ID` (default `1`).
  - `IBKR_ACCOUNT_ID` (required at runtime; if unset, sync refuses to run with Dutch error).
  - `IBKR_ENABLED` (default `false` — preserves the "disabled by default" Task 120 lock).

### Storage — extend snapshot tables with account_id and account_mode

- New migration `0045_ibkr_account_id_and_mode_tagging` (next slot after V1.1 Slice 32's `0044`):
  - Add `ibkr_account_id TEXT NOT NULL` to all five IBKR snapshot tables (`ibkr_sync_runs`, `ibkr_account_cash_snapshots`, `ibkr_position_snapshots`, `ibkr_open_order_snapshots`, `ibkr_execution_snapshots`). Backfill with the value from `os.getenv("IBKR_ACCOUNT_ID")` or a placeholder if any row exists; safe for empty tables.
  - `account_mode TEXT NOT NULL CHECK (account_mode IN ('paper','live','unknown'))` is already on `ibkr_sync_runs`; widen the CHECK to include `'unknown'` if the existing constraint is narrower.
  - Add `verified_at TIMESTAMPTZ` to `ibkr_sync_runs`.
  - Add index `ix_ibkr_<table>_account_id` per snapshot table.
- New table `ibkr_connection_audit`:
  - Columns: `id BIGSERIAL PK`, `event_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `ibkr_account_id TEXT NOT NULL`, `event_type TEXT NOT NULL CHECK (event_type IN ('connect_attempt','connect_success','connect_refused','mode_check_prefix','mode_check_behavioural','disconnect','session_error'))`, `account_mode_detected TEXT`, `details_json JSONB`, `connection_id TEXT`.
  - Append-only. No update or delete.
- Repository: `IbkrConnectionAuditRepository` in `packages/storage`, with `append(event) -> AuditEntry` and `list_recent(account_id, limit) -> list[AuditEntry]`. No update/delete methods.

### API — replace in-memory STORE with durable read

- In `apps/api/src/portfolio_outlook_api/ibkr_sync.py`:
  - **Delete the module-level `STORE = InMemoryIbkrSyncStore()` entirely.**
  - All routes read from durable storage repositories. No in-memory fallback. If the storage layer is unavailable, return HTTP 503 with a Dutch error body: `{"detail": "Opslag is niet beschikbaar. Synchronisatie kan niet worden uitgevoerd."}`. Fail closed.
  - `/ibkr/sync/run` (existing route, manual trigger) now: (a) verifies the gateway is connected (read worker state from durable storage), (b) writes a snapshot row tagged with `ibkr_account_id` and `account_mode`, (c) returns the snapshot to the caller. No IBKR network call inside the route — the API only reads worker-persisted state.
  - New route `GET /ibkr/connection/status` → returns `{connected: bool, account_id: str | null, account_mode: "paper"|"live"|"unknown", verified_at: timestamp | null, error: str | null}`. Reads from worker state via the persistence layer.
  - New route `GET /ibkr/connection/audit?limit=20` → returns the last N rows from `ibkr_connection_audit`.

### Frontend — account-mode indicator and real Portefeuille grid

- `apps/web/components/AccountModeBadge.tsx`:
  - Polls `/ibkr/connection/status` every 30 seconds.
  - Renders a persistent strip at the top of every page (already mounted in `app/layout.tsx`).
  - Three visual states:
    - **Paper:** neutral blue background, text `"Paper-rekening: {DU...masked}"`. White text on `#1e40af` background.
    - **Live:** amber background, text `"Echte rekening: {U...masked}"`. Dark text on `#f59e0b` background.
    - **Unknown / Disconnected:** grey background, text `"Geen IBKR-verbinding"`. White on `#6b7280`.
  - Account ID is masked: show only the prefix and last 4 chars (e.g. `DU•••4567`).
  - On first mount: 500ms flash of full saturated mode colour, then settle to steady state.
- Update `apps/web/app/portefeuille/page.tsx`:
  - Replace any placeholder content with a real grid populated from `/ibkr/sync/positions/latest` and `/ibkr/sync/cash/latest`.
  - Columns: Symbool, Beurs, Aantal, Gem. kostprijs, Huidige prijs, Waarde (EUR), Niet-gerealiseerde W/V, Verversingsdatum.
  - All money values displayed with Decimal precision, no float rendering.
  - Above the grid: cash summary card showing `AvailableFunds`, `NetLiquidationValue`, `TotalCashValue` per currency, with timestamp.
  - Empty state (no positions): Dutch message `"Geen posities in deze rekening."` with a help icon explaining how to connect IBKR. No fake placeholder positions.
  - Disconnected state (worker reports no IBKR connection): full-page banner `"IBKR-verbinding ontbreekt. Controleer Instellingen of activeer de verbinding."`. Grid hidden.

### Dockerfile fixes (required to make this task actually runnable)

- Fix `apps/api/Dockerfile`:
  - Build context must be the monorepo root.
  - Copy `packages/domain/`, `packages/storage/`, `packages/portfolio/` into the image before installing `apps/api`.
  - `pip install --no-cache-dir -e ../../packages/domain ../../packages/storage ../../packages/portfolio` then `pip install --no-cache-dir .`.
- Fix `apps/worker/Dockerfile` the same way (plus copy `packages/portfolio` even though worker may not strictly need it — it does need domain and storage).
- Fix `apps/web/Dockerfile`:
  - Replace `CMD ["npm", "run", "dev", ...]` with a production-shaped build: `RUN npm run build` followed by `CMD ["npm", "start"]`.
- Verify `cd infra/docker && docker compose up --build` brings up all services with green healthchecks.

### Tests

- `packages/storage/tests/test_ibkr_account_id_migration.py`: assert migration `0045` adds the columns, the check constraint exists, the index exists, the audit table exists.
- `packages/storage/tests/test_ibkr_connection_audit_repository.py`: append-only behaviour, list_recent ordering, no update/delete methods.
- `apps/worker/tests/test_ibkr_gateway.py`: with `ib_insync` mocked, assert `connect()` calls `reqManagedAccts`, derives mode from prefix correctly for `DU1234567` (paper) and `U7654321` (live), runs behavioural check, refuses connection if prefix and behavioural disagree, writes audit rows for both checks.
- `apps/worker/tests/test_ibkr_gateway_decimal.py`: assert all monetary returns preserve Decimal precision through the gateway boundary.
- `apps/api/tests/test_ibkr_sync_routes_no_inmemory.py`: assert that hitting `/ibkr/sync/run` when storage is unavailable returns HTTP 503 with the Dutch error body. No in-memory fallback path exists.
- `apps/api/tests/test_ibkr_connection_status_route.py`: assert the route returns the expected typed shape with `connected`, `account_id`, `account_mode`, `verified_at`, `error`.
- Frontend test (Vitest + React Testing Library): `apps/web/components/AccountModeBadge.test.tsx` covers three visual states and the account-ID masking.
- Frontend Playwright smoke test: visit `/portefeuille`, assert the badge is visible in the top strip, assert the empty-state Dutch message appears when worker is disconnected.

## Out of scope (do NOT do)

- No scheduling code. APScheduler stays where V1 put it.
- No watchlist sync. Volglijst stays in its current state.
- No starter-watchlist generation.
- No advice generation, no Decision Package code, no suggestion engine.
- No action drafts, no IBKR submission flow.
- No discovery loop.
- No morning briefing screen assembly.
- No market-data fetching. Position prices come from the IBKR snapshot directly (IBKR returns `marketPrice` on positions), not from a separate provider.
- No AI runtime of any kind.
- No Belgian tax module changes.
- No expansion of `docs/product/asset-value-prediction-engine-roadmap.md` or `docs/product/probabilistic-asset-outlook-doctrine.md`. This is runtime, not doctrine.
- No new readiness-contract fields.
- Do NOT add a "paper-only enforcement" check anywhere.

## Acceptance criteria

1. From a fresh checkout, `cd infra/docker && docker compose up --build` brings up Postgres, the API, the worker, and the web app with all healthchecks green.
2. With `IBKR_ENABLED=true` and valid TWS credentials in `.env.local`, the worker connects to IBKR, runs both mode checks (prefix + behavioural), and the `ibkr_connection_audit` table contains a `connect_success` row tagged with the account ID and detected mode.
3. Hitting `/ibkr/sync/run` writes a real position+cash snapshot to Postgres, tagged with `ibkr_account_id` and `account_mode`. Restarting the worker and hitting `/ibkr/sync/positions/latest` returns the same snapshot — data is durable.
4. Opening `/portefeuille` in the web app shows:
   - The account-mode badge in the top strip with the correct mode colour, masked account ID.
   - The cash summary card with real EUR/USD/etc. balances and a timestamp.
   - The positions grid with real positions (or the empty-state Dutch message if the account has none).
5. With `IBKR_ENABLED=false` or no connection, `/portefeuille` shows the disconnected banner in Dutch, and the grid is hidden.
6. Migration 0045 adds the columns, check constraint, index, and audit table. `alembic upgrade head` and `alembic downgrade -1` both succeed against a real Postgres container.
7. The module-level `STORE = InMemoryIbkrSyncStore()` in `apps/api/.../ibkr_sync.py` is deleted. `grep -r "STORE = InMemoryIbkrSyncStore" apps/api/` returns nothing.
8. CI green on all six jobs (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`).
9. `mypy --strict` clean on all five Python packages.
10. New tests added (worker gateway, storage migration, API routes, frontend badge) all pass.
11. `locked-decisions.md` updated with the new `## Task 126 product locks` section. The earlier paper-only-V1 line is moved (not deleted) to a "Retired locks" section at the bottom with the date and the reason.

## Anti-patterns to avoid

- No new module-level mutable state. No `STORE = ...` at module top level anywhere in the API or worker.
- No in-memory fallback. If durable storage is unavailable, fail closed with HTTP 503 and a Dutch error. Do not "degrade gracefully" to an in-memory dict.
- No "Paper-rekening: TEST" or "ECHTE order" wording in user-facing strings outside the AccountModeBadge component. Mode is visible through the badge only.
- No mode-based gating of functionality. The software does not refuse to submit live orders. The user is responsible for their account configuration.
- No new readiness-contract fields. `analysis_ready`, `suggestions_allowed`, `action_drafts_allowed` etc. are not touched in this task.
- No new doctrine document. No expansion of `final-solution-vision.md` or any roadmap doc. Update `current-state.md` and `task-history.md` per the existing project-tracking pattern, nothing more.
- No use of `float` for any monetary value. Decimal everywhere, end-to-end.
- No emoji in code, docs, or UI strings. The project uses plain Dutch.

## Suggested PR title

`Task 126: real IBKR connection, account-mode badge, durable Portefeuille grid`

## Estimated size

**M (target)** — one PR, 800–1400 LoC across worker, storage, API, web, plus tests and a migration. If it exceeds ~1500 LoC during development, split into sequential **126a** (storage migration + worker gateway + worker tests + Dockerfile fixes) and **126b** (API routes + frontend badge + portefeuille wiring + frontend tests).
