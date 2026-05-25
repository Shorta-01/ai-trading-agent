# Task 126b — API connection routes, AccountModeBadge, and real Portefeuille grid

## Goal

Ship the user-visible half of Task 126. After this task, the user opens the dashboard and sees a persistent colour-coded account-mode badge (Paper neutral-blue or Live amber) at the top of every screen, with the masked IBKR account ID. Opening `/portefeuille` shows real cash balances and positions from the durable storage that Task 126a (PR #400/#401) populates from IBKR. Data survives a worker restart and renders correctly. The doc trail (`current-state.md`, `task-history.md`, `locked-decisions.md`) is updated to reflect Tasks 126a + 126b.

Task 126a (the worker half) is already merged. This task is strictly the API routes + frontend + doc trail. No new worker changes. No scheduler. No advice. No action drafts. No AI.

## Locked references (read these before starting)

- `docs/product/locked-decisions.md` — particularly the Task 88I block, the audit/Decimal/no-fake-data rules, and the (now stale) paper-only-V1 line that this task is responsible for retiring properly in the doc trail.
- `docs/product/release-1-functional-workflow-blueprint.md` — §IBKR sync engine.
- `docs/product/ibkr-tws-gateway-integration-preflight-task-122.md` — TWS API choice, worker-owned session.
- `docs/product/current-state.md` — note that this doc was NOT updated when Task 126a merged; this brief fixes that.
- The Task 126 product locks from the previous brief, summarised below.

## Product locks already decided (carry forward from Task 126 brainstorm, must land in `locked-decisions.md` as part of this PR if not already there)

1. The software supports one configured IBKR account at a time. Account mode (Paper or Live) is whatever IBKR reports. **Paper-only-V1 lock is retired.** Move the old line to a "Retired locks" section at the bottom of `locked-decisions.md` with the date and reason.
2. Account-mode detection is two-tier (prefix + behavioural cross-check), already implemented in the worker by Task 126a. This task just exposes the result through the API and the frontend.
3. Account mode is visible everywhere via the persistent colour-coded indicator. **Dutch wording in the rest of the UI is mode-neutral.**
4. Every database row carries `ibkr_account_id`. Switching accounts in Settings filters the dashboard but preserves history.
5. Belgian tax module runs only in live mode (not relevant for this task but lock it in the doc).
6. No more module-level mutable state in production paths.

## In scope

### API — new routes that read worker state from durable storage

- `GET /ibkr/connection/status`:
  - Returns: `{connected: bool, account_id: str | null, account_mode: "paper" | "live" | "unknown", verified_at: ISO8601 | null, error: str | null}`.
  - Account ID returned masked (prefix + last 4 chars only, e.g. `DU•••4567`).
  - Reads from the durable storage rows the worker writes.
  - On storage unavailable: HTTP 503 with Dutch body `{"detail": "Opslag is niet beschikbaar."}`. No in-memory fallback.

- `GET /ibkr/connection/audit?limit=20`:
  - Returns the last N rows from `ibkr_connection_audit`.
  - Each row typed via Pydantic v2 model.
  - Read-only; append-only table (no PUT/DELETE).

- `GET /ibkr/sync/positions/latest`:
  - Returns the latest snapshot row of positions for the current configured account.
  - Position fields: `conid`, `symbol`, `exchange`, `currency`, `quantity (Decimal)`, `avg_cost (Decimal)`, `market_price (Decimal)`, `market_value (Decimal)`, `unrealized_pnl (Decimal)`, `as_of (ISO8601)`.

- `GET /ibkr/sync/cash/latest`:
  - Returns the latest cash summary: `{available_funds, net_liquidation_value, total_cash_value, buying_power}` per currency, all Decimal, plus `as_of (ISO8601)`.

- All four routes typed end-to-end with Pydantic v2. Decimal preserved through JSON serialisation. mypy --strict clean.

### Frontend — AccountModeBadge component, mounted globally

- Polls `/ibkr/connection/status` every 30 seconds (plain `useEffect` + `fetch`).
- Persistent strip mounted in `apps/web/app/layout.tsx`, visible on every page.
- Three visual states:
  - **Paper:** background `#1e40af`, white text, content `"Paper-rekening: {DU•••XXXX}"`.
  - **Live:** background `#f59e0b`, dark text (`#1f2937`), content `"Echte rekening: {U•••XXXX}"`.
  - **Disconnected / Unknown:** background `#6b7280`, white text, content `"Geen IBKR-verbinding"`.
- 500ms first-mount flash; ARIA labels.

- Portefeuille page:
  - Cash summary card (per-currency table with timestamp).
  - Positions grid (Dutch columns: Symbool, Beurs, Aantal, Gem. kostprijs, Huidige prijs, Waarde (EUR), Niet-gerealiseerde W/V, Verversingsdatum).
  - Empty state: `"Geen posities in deze rekening."`.
  - Disconnected state: full-page banner `"IBKR-verbinding ontbreekt. Controleer Instellingen of activeer de verbinding."`.
  - Loading state: skeleton rows.

### Doc trail update

- `current-state.md` header → "na Task 126b"; entries for 126a + 126a-hotfix + 126b.
- `task-history.md` — Task 126a + hotfix + 126b rows.
- `locked-decisions.md` — Task 126 product locks section + Retired locks (paper-only-V1).
- `next-task.md` — replaced with this 126b brief.

### Tests

- API: `test_ibkr_connection_status_route.py`, `test_ibkr_connection_audit_route.py`, `test_ibkr_sync_latest_routes.py` (includes the Decimal-preservation integration test).
- Vitest: `apps/web/components/AccountModeBadge.test.tsx` (3 visual states + masking + flash + polling).
- Playwright: `apps/web/tests/e2e/portefeuille.spec.ts` (badge visible, cash card, positions grid, empty state, disconnected banner).

### CI integration

- `web` job gains `npm test` (Vitest) + `npx playwright install --with-deps chromium` + `npm run test:e2e` (Playwright chromium-only).

## Out of scope (do NOT do)

- No new worker changes.
- No scheduler.
- No watchlist sync.
- No advice generation, no Decision Package code, no suggestion engine.
- No action drafts.
- No discovery loop.
- No morning briefing screen assembly.
- No AI runtime.
- No new readiness contract fields.
- No new doctrine documents.

## Acceptance criteria

1. From a fresh checkout, `cd infra/docker && docker compose up --build` brings up Postgres, the API, the worker, and the web app with all healthchecks green.
2. With `IBKR_ENABLED=true` and valid paper TWS credentials in `.env.local`, the worker connects and writes its snapshot. `/ibkr/connection/status` returns `{connected: true, account_id: "DU...", account_mode: "paper", verified_at: <recent>, error: null}`.
3. Opening `/portefeuille` shows the colour-coded badge, the cash summary card, and the positions grid (with rows or the empty-state Dutch message).
4. Any other page also shows the badge.
5. With `IBKR_ENABLED=false`, badge shows disconnected and `/portefeuille` shows the disconnected banner.
6. `docs/product/current-state.md` reads "na Task 126b" and documents 126a, hotfix, 126b.
7. `docs/product/locked-decisions.md` has the new section + Retired locks at the bottom.
8. CI green on all six jobs. Web job runs Vitest + Playwright.
9. `mypy --strict` clean on all five Python packages.
10. All new tests pass.
11. Decimal preservation: `quantity=Decimal("12.5")` + `avg_cost=Decimal("640.123456")` round-trip the API JSON without precision loss (dedicated integration test).

## Suggested PR title

`Task 126b: API connection routes, AccountModeBadge, real Portefeuille grid`

## Estimated size

**M** — one PR, 800–1200 LoC.
