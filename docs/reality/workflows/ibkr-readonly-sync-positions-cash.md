# Reality — workflow: IBKR read-only sync (positions + cash)

**Scope.** End-to-end trace of the IBKR read-only data-feed loop — from user-triggered or scheduled "sync now" call → API `POST /ibkr/sync/run` → worker `IbkrGateway.connect` with tier-two paper-account guard → read-only IBKR API calls (`managedAccounts`, `accountSummary`, `positions`, `reqOpenOrders`, `reqExecutions`) → persisted snapshot rows in 4 storage tables → frontend display via `<PortefeuilleRealtimeSection>` + `<AccountModeBadge>`.

This is the **only currently-implemented IBKR data path** in the project. Order submission lives in a separate flow (T-019, future); reconciliation lives in another (T-020, future).

**Sibling reality docs (read these for module-level detail):**

- `docs/reality/components/api-ibkr-sync-and-snapshot.md` — 9 sync modules (T-004).
- `docs/reality/components/api-ibkr-connection-and-status.md` — connection routes, status, read-model, tws_readonly modules (T-004).
- `docs/reality/components/worker-orchestration-and-scheduling.md` §7 — `IbkrGateway.connect` lifecycle (T-007).
- `docs/reality/components/web-components-feature-grids.md` §7 — `PortefeuilleRealtimeSection` (T-008).
- `docs/reality/components/web-components-status-and-shared.md` §1 — `AccountModeBadge` (T-008).
- `docs/reality/components/web-api-client-and-text.md` §2 — 12 IBKR-related `apiClient.*` methods (T-009).

## 0. TL;DR

The IBKR read-only sync is a **pull loop**: a sync_run is triggered (manually via `POST /ibkr/sync/run` or implicitly by the worker on a future scheduler tick), connects to TWS read-only, queries `managedAccounts` + `accountSummary` + `positions` + open orders + executions, persists each call's payload as a snapshot row keyed by `sync_run_id`, and finalises the `ibkr_sync_runs` row with `status="success" | "failed" | "partial"`. The frontend polls the latest sync_run + snapshots every 30 s and renders positions, cash, and a paper/live/disconnected mode pill.

The whole flow is **architecturally read-only** at three layers:

1. **The IBKR client interface** — `IbClientProtocol` in `apps/worker/src/portfolio_outlook_worker/ibkr_gateway.py:53-75` exposes only read methods (`connect`, `disconnect`, `isConnected`, `managedAccounts`, `reqContractDetails`, `accountSummary`, `positions`). **No `placeOrder` / `cancelOrder` in this protocol.**
2. **The TWS connect call** — `client.connect(host, port, clientId=client_id, readonly=True)` at `apps/worker/src/portfolio_outlook_worker/ibkr_gateway.py:221`. The `readonly=True` flag instructs `ib_insync` to refuse any order-modifying call.
3. **The tier-two paper-account guard** — combines a prefix check (`DU`/`DF` → paper) with a behavioural check (probe a live-only contract); a disagreement between the two refuses the connect and writes a `connect_refused` audit row.

No part of this flow touches `place_order` or `cancel_order`. Those live in `ibkr_submission/submitter.py:240` (worker) and `ibkr_ibapi_order_submission_client.py:525` (API) — see T-007 `worker-actions-and-reconciliation.md` §5 + T-004 cluster docs for that surface.

## 1. Trigger model

Two trigger paths:

### 1.1 User-triggered manual sync (most common today)

The user clicks "Synchroniseer snapshots" in `/portefeuille` (per T-008 `web-pages.md` §3.2, the button at `apps/web/app/portefeuille/page.tsx:267-268`). The frontend calls:

```ts
await apiClient.runIbkrSync()  // POST /ibkr/sync/run
```

Per T-009 `web-api-client-and-text.md` §2, this is the `runIbkrSync` method at `apps/web/lib/apiClient.ts:1712`. The API endpoint synchronously kicks off a sync_run and returns a status (per T-004 `api-ibkr-sync-and-snapshot.md`).

### 1.2 Scheduler-driven sync (Phase 4 — not yet wired)

The intent is that the worker's APScheduler triggers a sync_run periodically (e.g. every 5 minutes during market hours). Per T-007 `worker-orchestration-and-scheduling.md` §4, the worker scheduler currently has 3 APScheduler jobs (pre_briefing, hourly_delta, heartbeat) — **no sync_run job is registered today**. The sync is currently manual-only.

## 2. The API endpoint — `POST /ibkr/sync/run`

Per T-004 `api-ibkr-sync-and-snapshot.md`:

The route lives in `apps/api/src/portfolio_outlook_api/ibkr_sync.py` (~461 lines). The endpoint:

1. Gates on `settings.ibkr_enabled` AND `settings.ibkr_sync_enabled` (per T-006 §2: `apps/api/.../config.py:86-115` — IBKR + IBKR-sync field groups). Both default `False`.
2. Gates on storage availability — opens `StorageConnectionProvider.checked_connection(require_writable=True)` (per T-009 `infra-docker-and-compose.md` storage-readiness flow).
3. Reads `settings.ibkr_sync_host`, `settings.ibkr_sync_port`, `settings.ibkr_sync_client_id`, `settings.ibkr_sync_account_mode` — all from the API's `Settings` class (`apps/api/.../config.py:105-116`).
4. Inserts an `ibkr_sync_runs` row with `status="running"` (see §4 for the table shape).
5. Invokes the sync adapter (per `ibkr_sync_adapter_factory.py`).
6. The adapter opens a TWS connection via the worker's `IbkrGateway` pattern (see §3).
7. Persists each subsequent IBKR API response as a snapshot row keyed by `sync_run_id`.
8. Finalises the `ibkr_sync_runs` row with the outcome.

The route returns `{status: string}` to the frontend per `apiClient.ts:1712` (`FetchState<{status: string}>` per T-009 §2).

## 3. The connect lifecycle — tier-two paper-account guard

Per T-007 `worker-orchestration-and-scheduling.md` §7 (`apps/worker/src/portfolio_outlook_worker/ibkr_gateway.py`, 558 lines).

The `IbkrGateway.connect(host, port, client_id, account_id)` method (`ibkr_gateway.py:187-352`) is the **single connect path** for read-only sync. The same method is also called from the worker's startup probe (T-007 `worker-orchestration-and-scheduling.md` §2 — `main.py:71-76`).

### 3.1 Constants

- `_PAPER_PREFIXES = ("DU", "DF")` at `ibkr_gateway.py:44`. Per Task 126 §2, IBKR paper accounts always start with `DU` or `DF`.
- `AccountMode = Literal["paper", "live", "unknown"]` at `ibkr_gateway.py:39`.

### 3.2 Connect sequence (per `ibkr_gateway.py:187-352`)

The 9-step lifecycle, each step writing an `ibkr_connection_audit` row via `_append_audit` (`:502-528`):

| Step | Site | Action | Audit row |
|---|---|---|---|
| 1 | `:197-206` | Account-id presence check | `connect_refused` (`"IBKR_ACCOUNT_ID ontbreekt…"`) on failure |
| 2 | `:208-217` | Write `connect_attempt` audit row | `connect_attempt` |
| 3 | `:219-221` | `client.connect(host, port, clientId=client_id, readonly=True)` — **the `readonly=True` is the IBKR-side read-only flag** | — |
| 4 | `:222-245` | Connect-failure catch (any exception from `connect()`) | `connect_refused` with `{"reason": "tws_connect_failed", "message": ...}` on failure |
| 5 | `:247-273` | `managedAccounts()` validation — confirms TWS reports the configured `account_id` | `connect_refused` with `{"reason": "account_not_managed"}` on failure |
| 6 | `:275-284` | **Tier-one prefix check**: `_mode_from_prefix(account_id)` — `DU`/`DF` → `paper`; else `live` | `mode_check_prefix` with `account_mode_detected=prefix_mode` |
| 7 | `:286-295, :468-500` | **Tier-two behavioural check**: probe a live-only contract `Future(symbol="MES", lastTradeDateOrContractMonth="20990101", exchange="CME")` via `client.reqContractDetails(probe)`. Empty list → `paper`; non-empty → `live`; exception → `paper` | `mode_check_behavioural` with `account_mode_detected=behavioural_mode` |
| 8 | `:297-324` | **Disagreement guard**: if `prefix_mode != behavioural_mode` → disconnect + refuse | `connect_refused` with `{"reason": "mode_check_disagreement", "prefix_mode": ..., "behavioural_mode": ...}` |
| 9 | `:326-352` | Success path — assign `connection_id`, cache `_ib`, `_account_mode`, return `IbkrConnectionResult(connected=True, ..., audit_ids=(5 ids))` | `connect_success` with `{"verified_at": <iso>}` |

### 3.3 Why this matters

The tier-two guard ensures the system **never accidentally trades against a live account by misconfiguration**. A live IBKR account configured with the worker's expectations (e.g. someone moves the env file from a paper machine to a live machine without updating the account_id) would fail tier-one (`DU`/`DF` prefix absent → `live`) and tier-two would agree (`live`) — connection proceeds but `account_mode="live"`. Per T-007 §5, the worker's `submitter.py:285` then refuses to issue any `place_order` because the safety-check pipeline blocks live mode in V1.

A misconfigured paper account that somehow doesn't have a `DU`/`DF` prefix would fail tier-one (`unknown`) and the disagreement guard refuses the connect outright.

### 3.4 Read-only `IbClientProtocol`

`apps/worker/.../ibkr_gateway.py:53-75` declares the IBKR client interface as a structural Protocol with only the **read** methods:

- `connect`, `disconnect`, `isConnected`
- `managedAccounts`
- `reqContractDetails`
- `accountSummary`
- `positions`

**No `placeOrder` / `cancelOrder` / `reqOpenOrders` / `reqExecutions` in this protocol.** The protocol exists to make the gateway testable without the real `ib_insync.IB` — the underlying SDK client (per `ibkr_gateway.py:531-542`) does support order methods, but the gateway never calls them.

## 4. Persisted state — 5 storage tables

Per `packages/storage/src/ai_trading_agent_storage/metadata.py`:

### 4.1 `ibkr_sync_runs` — the sync_run lifecycle row

One row per sync attempt. Columns include `sync_run_id` (FK target — 4 child tables reference it), `ibkr_account_id`, `started_at`, `completed_at`, `status` (`running` / `success` / `failed` / `partial`), `error_text`. Per T-004 `api-ibkr-sync-and-snapshot.md`:

- Inserted on `POST /ibkr/sync/run` start.
- Updated to `success` / `failed` / `partial` at the end of the sync.
- Read by `GET /ibkr/sync/status` (the latest row per account).
- Read by `GET /ibkr/sync/runs` (history).

State transitions: `running` → (`success` | `failed` | `partial`). No re-entry from terminal states.

### 4.2 `ibkr_position_snapshots`

Per `metadata.py`, each row carries a `sync_run_id` FK + position data (conid, symbol, exchange, quantity, avg_cost, etc.). Index `ix_ibkr_position_snapshots_ibkr_account_id` (`metadata.py`) covers the `(account_id)` query path used by `_PositionSnapshotCounts.position_snapshot_count_for_account` (T-007 `worker-orchestration-and-scheduling.md` §4, `scheduler.py:67-79`).

This is the **table the orchestrator's cold-start detection reads** to decide between `mode_detected="cold_start"` and `mode_detected="normal"` (T-007 §6 step 5). After the first successful sync_run, any rows here count toward "non-zero positions" → cold-start does not fire.

### 4.3 `ibkr_cash_snapshots`

Per `metadata.py`, each row carries `sync_run_id` FK + cash data (currency, available_funds, net_liquidation, total_cash, buying_power). One row per currency observed in the sync.

Cited by T-008 `web-components-feature-grids.md` §7 — the `<CashSummaryCard>` sub-component of `<PortefeuilleRealtimeSection>` renders these.

### 4.4 `ibkr_open_orders`

Per T-004 `api-ibkr-sync-and-snapshot.md`, open-orders snapshot rows produced by `reqOpenOrders` calls. Each row references the sync_run. Read by `apiClient.getIbkrOpenOrders()` at `apiClient.ts:1442` (T-009 §2).

### 4.5 `ibkr_executions`

Per T-007 `worker-actions-and-reconciliation.md` §7 (and `metadata.py`), executions table with **UNIQUE on `ibkr_exec_id`** (`metadata.py:0`). The sync's `reqExecutions` calls write rows here.

This table is **read by reconciliation Pass A** (T-007 §9) to detect IBKR-side fills that have no matching local action_draft. For the sync flow, it's a pure data-feed write; the reconciliation pass is independent.

### 4.6 Storage table inventory summary

| Table | Op per sync | Key | Foreign-key | Audit-trail link |
|---|---|---|---|---|
| `ibkr_sync_runs` | 1 insert + 1 update | `sync_run_id` | — | the parent row 4 others FK |
| `ibkr_position_snapshots` | N inserts (one per position) | composite (sync_run_id, conid) | `sync_run_id` | — |
| `ibkr_cash_snapshots` | M inserts (one per currency) | composite (sync_run_id, currency) | `sync_run_id` | — |
| `ibkr_open_orders` | K inserts | composite (sync_run_id, perm_id) | `sync_run_id` | — |
| `ibkr_executions` | E inserts | UNIQUE on `ibkr_exec_id` | `account_id` | read by reconciliation Pass A |
| `ibkr_connection_audit` | 5-6 inserts per connect attempt | `audit_id` (uuid) | — | every step of `IbkrGateway.connect` writes one row |

## 5. The frontend display

Per T-008 + T-009:

### 5.1 `<AccountModeBadge>` — mode pill (top status bar)

Per T-008 `web-components-status-and-shared.md` §1:

- Polls `apiClient.getIbkrConnectionStatus()` (`GET /ibkr/connection/status`, T-009 §2) every **30 s** (interval at `AccountModeBadge.tsx:18`).
- Renders one of 3 pills per the locked state vocabulary (`Mode = "paper" | "live" | "disconnected"` at `AccountModeBadge.tsx:21`):
  - `paper` — `"Paper-rekening: ${id}"`, bg `#1e40af` (T-008 §1 visuals).
  - `live` — `"Echte rekening: ${id}"`, bg `#f59e0b`.
  - `disconnected` — `"Geen IBKR-verbinding"`, bg `#6b7280`.

The mode is derived server-side from the latest `ibkr_connection_audit` rows + the cached `_account_mode` field in `IbkrGateway` (per T-007 §7 — `get_account_mode()` at `ibkr_gateway.py:383-393`).

### 5.2 `<PortefeuilleRealtimeSection>` — positions + cash grids

Per T-008 `web-components-feature-grids.md` §7 (`apps/web/components/PortefeuilleRealtimeSection.tsx`):

- Client component, polls 4 endpoints in parallel via `Promise.all`:
  - `apiClient.getIbkrConnectionStatus()` (`apiClient.ts:1470`)
  - `apiClient.getIbkrSyncPositionsLatest()` (`apiClient.ts:1476`)
  - `apiClient.getIbkrSyncCashLatest()` (`apiClient.ts:1478`)
  - `apiClient.getMarketDataByAccount()` (`apiClient.ts:1497`)
- Polling cadence: **30 s** (interval at `PortefeuilleRealtimeSection.tsx:99-101`).
- **Exemplary Decimal-as-string preservation** (T-008 §D): `formatNumber` (`:36-39`) passes Decimal strings verbatim — no `Number()` conversion, no precision loss.
- Renders `<CashSummaryCard>` (per-currency rows from `ibkr_cash_snapshots`) + `<PositionsGrid>` (one row per `ibkr_position_snapshots` row enriched with market-data freshness from `MarketDataByAccountResponse`).

### 5.3 `/portefeuille` page

Per T-008 `web-pages.md` §3.2, the page hosts:

- `<PortefeuilleRealtimeSection>` at the top.
- A "Synchroniseer snapshots" button (`apps/web/app/portefeuille/page.tsx:267-268`) wired to `apiClient.runIbkrSync()` (the manual trigger from §1.1).
- Several read-only panels below (open orders, executions, action drafts, decision packages — these consume the same `ibkr_*` storage tables via different `apiClient` methods).

The page calls **18 distinct `apiClient` endpoints** per mount (T-008 §3.2 documents the full list). The IBKR-related subset is 6 of those 18: `getIbkrSyncStatus`, `getIbkrPositions`, `getIbkrCash`, `getIbkrOpenOrders`, `getIbkrExecutions`, `runIbkrSync`.

## 6. The 12 `apiClient.*` IBKR methods

Per T-009 `web-api-client-and-text.md` §2 (IBKR section):

| # | Method | File:line | HTTP + path |
|---:|---|---|---|
| 1 | `getIbkrStatus()` | `apiClient.ts:1437` | `GET /broker/ibkr/status` |
| 2 | `getIbkrSyncStatus()` | `:1438` | `GET /ibkr/sync/status` |
| 3 | `getIbkrPositions()` | `:1440` | `GET /ibkr/portfolio/positions` |
| 4 | `getIbkrCash()` | `:1441` | `GET /ibkr/account/cash` |
| 5 | `getIbkrOpenOrders()` | `:1442` | `GET /ibkr/orders/open` |
| 6 | `getIbkrExecutions()` | `:1443` | `GET /ibkr/executions` |
| 7 | `getIbkrAccountMode()` | `:1469` | `GET /ibkr/account/mode` |
| 8 | `getIbkrConnectionStatus()` | `:1470` | `GET /ibkr/connection/status` |
| 9 | `getIbkrConnectionAudit(limit=20)` | `:1472` | `GET /ibkr/connection/audit?limit=N` |
| 10 | `getIbkrSyncPositionsLatest()` | `:1476` | `GET /ibkr/sync/positions/latest` |
| 11 | `getIbkrSyncCashLatest()` | `:1478` | `GET /ibkr/sync/cash/latest` |
| 12 | `runIbkrSync()` | `:1712` | `POST /ibkr/sync/run` |

11 are GETs; 1 is a POST (the manual trigger). All return `FetchState<T>` (T-009 §1) — failures collapse to `{ ok: false, reason: "not_reachable" }`.

## 7. End-to-end timeline — one user-triggered sync

A user clicks "Synchroniseer snapshots" on `/portefeuille`. Wall-clock:

| t | Tier | Action | Storage write |
|---|---|---|---|
| 0 ms | Frontend | `runIbkrSync()` POST sent | — |
| ~10 ms | API | `POST /ibkr/sync/run` handler enters; gates on settings | — |
| ~20 ms | API | `StorageConnectionProvider.checked_connection(require_writable=True)` | — |
| ~30 ms | API → Storage | INSERT `ibkr_sync_runs` row with `status="running"` | 1 row |
| ~50 ms | API → Worker-side | Adapter spawns `IbkrGateway.connect(host, port, client_id, account_id)` | — |
| ~60 ms | Audit | INSERT `ibkr_connection_audit` `connect_attempt` row | 1 row |
| ~200 ms | TWS | `client.connect(readonly=True)` returns | — |
| ~250 ms | Audit | INSERT `mode_check_prefix` row | 1 row |
| ~350 ms | TWS | `reqContractDetails(MES future)` probe completes | — |
| ~400 ms | Audit | INSERT `mode_check_behavioural` row | 1 row |
| ~450 ms | Audit | INSERT `connect_success` row (matches → success path) | 1 row |
| ~500 ms | TWS | `managedAccounts()` + `accountSummary()` + `positions()` | — |
| ~600 ms | Storage | INSERT N `ibkr_position_snapshots` rows + M `ibkr_cash_snapshots` rows | N+M rows |
| ~700 ms | TWS | `reqOpenOrders()` + `reqExecutions()` (if configured) | — |
| ~800 ms | Storage | INSERT K + E rows into `ibkr_open_orders` + `ibkr_executions` | K+E rows |
| ~850 ms | Worker | `gateway.disconnect()` → INSERT `disconnect` audit row | 1 row |
| ~900 ms | Storage | UPDATE `ibkr_sync_runs` row to `status="success"`, `completed_at=now` | — |
| ~910 ms | API | Returns `{ status: "success" }` to frontend | — |
| ~920 ms | Frontend | `runIbkrSync()` resolves; subsequent 30 s poll picks up the new snapshot | — |

**Total audit-row writes per sync**: 6 connection-audit rows (attempt, prefix, behavioural, success, plus any inter-step row, plus disconnect) + 1 sync_runs row (insert+update). **Total snapshot writes**: N positions + M cash + K open orders + E executions, all FK-referenced to the same `sync_run_id`.

Net wall-clock for a typical sync (paper account, 5–10 positions, 2 currencies): ~1 second end-to-end.

## 8. Failure paths

| Failure | Step | Resulting `ibkr_sync_runs.status` | Audit signal |
|---|---|---|---|
| Storage disabled at API entry | API gate (step 2) | n/a — sync_run row never inserted | API response with 503 + Dutch message |
| `settings.ibkr_enabled=False` | API gate | n/a | API response with `{"status": "ibkr_disabled"}` or similar |
| Empty `account_id` env var | `IbkrGateway.connect` step 1 | `failed` | `connect_refused` with "IBKR_ACCOUNT_ID ontbreekt…" |
| `client.connect()` raises (network, port wrong) | step 3 | `failed` | `connect_refused` with `{"reason": "tws_connect_failed"}` |
| `managedAccounts` doesn't include configured `account_id` | step 5 | `failed` | `connect_refused` with `{"reason": "account_not_managed", "managed_accounts": [...]}` |
| Tier-1 / tier-2 mode disagreement | step 8 | `failed` | `connect_refused` with `{"reason": "mode_check_disagreement", "prefix_mode": ..., "behavioural_mode": ...}` |
| `positions()` raises mid-sync | step 6 | `partial` (some snapshot rows already written) | error logged; `ibkr_sync_runs.error_text` populated |
| `reqExecutions()` raises (optional) | step 7 | `partial` or `success` depending on what got written | execution rows may be incomplete |
| Storage commit fails on `ibkr_sync_runs` update | step 9 | row stays in `running` state | observable via stale row in `GET /ibkr/sync/runs` history |

The "row stays in `running`" failure mode is the only path that doesn't self-clean. Reconciliation Pass C (T-007 `worker-actions-and-reconciliation.md` §11) has a 24 h timeout for action drafts in `awaiting_reply_timeout` — but **the `ibkr_sync_runs` table is NOT covered by reconciliation**. A stale `running` row would have to be cleaned up manually. Phase 4 candidate: add a sync_run staleness timeout to the reconciler.

## 9. Cross-cuts + Phase 1c surface

The following observations are inputs for Phase 1c gap analysis:

1. **Sync trigger is manual-only today.** No APScheduler job exists for periodic sync (T-007 §4 documents the 3 jobs — pre_briefing / hourly / heartbeat). The intent is that hourly_delta runs would refresh the sync, but no `sync_runner` slot exists in the orchestrator's gate list (T-007 §6 lists 5 gates: market_data, forecasting, decision_package, calibration, seed — no sync).
2. **The orchestrator's cold-start detection depends on `ibkr_position_snapshots`** (T-007 `worker-orchestration-and-scheduling.md` §6 step 5 — `_PositionSnapshotCounts.position_snapshot_count_for_account` at `scheduler.py:67-79`). Without a recent sync_run, the orchestrator sees an empty positions table and defaults to `cold_start` even if the user has positions at IBKR. The sync must be triggered manually at least once.
3. **The `ibkr_sync_runs` table is not covered by reconciliation.** A stale `running` row would persist forever. Phase 4 candidate: extend reconciliation Pass C or add a sync_run timeout sweeper.
4. **Tier-two paper-account guard is the only safety layer at connect time.** No further check happens before each `accountSummary` / `positions` call — once the connection is established + verified, all subsequent reads are trusted. This is consistent with the read-only protocol (no writes possible), but worth documenting.
5. **The frontend polls 30 s while the backend has no push channel.** A successful sync_run that lands at t=15s is invisible to the badge until t≈45s. Acceptable for a paper-account UX, but a real-money UX would want a push channel. Phase 4 candidate.
6. **No `place_order` / `cancel_order` in `IbClientProtocol`** (per T-007 §7 + §5) confirms the read-only architecture, but the API side has `placeOrder` directly at `ibkr_ibapi_order_submission_client.py:525` — a doctrine drift that T-007 §5 flags. The read-only sync flow does NOT touch the API's order-submission client; that's a separate code path entirely.
7. **`MES` future probe at `ibkr_gateway.py:486` is the tier-two behavioural check.** It relies on IBKR's contract-database behaviour: live accounts see CME futures (`MES`); paper accounts don't (or see them differently). If IBKR ever changes their paper-account contract surface, the behavioural check would break — surfacing as a `mode_check_disagreement` refusal on previously-working accounts. Phase 4 candidate: add a fallback probe + a versioned compatibility check.
8. **`apiClient.getIbkrAccountMode()` is a separate endpoint from `getIbkrConnectionStatus()`** (T-009 §2). The latter is what `<AccountModeBadge>` polls; the former is exposed but no observed UI calls it. Could be dead code — flagging for T-057-equivalent dead-code follow-up.

## 10. Explicit out-of-scope

- **Order submission flow** (T-019 will cover) — `apps/api/.../ibkr_ibapi_order_submission_client.py:525` (camelCase `placeOrder` API site), `apps/worker/.../ibkr_submission/submitter.py:240` (snake_case `place_order` worker site). Per T-007 §5 this is a doctrine drift.
- **Reconciliation passes A/B/C** (T-020 will cover) — Pass A reads `ibkr_executions` written by this sync flow but the reconciler tick is independent.
- **TWS read-only runtime adapter** (`ibkr_tws_readonly_*` modules) — separate from the sync flow; the read-only runtime is a long-lived session, the sync flow is a per-trigger short-lived one. Per T-004 `api-ibkr-connection-and-status.md` §`ibkr_tws_readonly_runtime.py` (`~507 lines`).
- **Action draft state machine** (T-018 will cover) — consumes positions + cash from the sync but doesn't drive it.
- **AI explanation / forecasting** (T-011 morning chain) — consumes positions + cash + market data; doesn't trigger the sync.

## 11. References

- `docs/reality/components/api-ibkr-sync-and-snapshot.md` — 9 sync modules (T-004).
- `docs/reality/components/api-ibkr-connection-and-status.md` — connection routes + status + read-model + tws_readonly (T-004).
- `docs/reality/components/api-ibkr-submission-and-watchlists.md` — out-of-scope sibling (T-004).
- `docs/reality/components/worker-orchestration-and-scheduling.md` §7 — `IbkrGateway.connect` lifecycle (T-007).
- `docs/reality/components/worker-actions-and-reconciliation.md` §5 — out-of-scope (worker submitter) + §7 — `ibkr_executions` UNIQUE + §9 — Pass A consumer of executions (T-007).
- `docs/reality/components/web-pages.md` §3.2 — `/portefeuille` page (T-008).
- `docs/reality/components/web-components-feature-grids.md` §7 — `PortefeuilleRealtimeSection` (T-008).
- `docs/reality/components/web-components-status-and-shared.md` §1 — `AccountModeBadge` (T-008).
- `docs/reality/components/web-api-client-and-text.md` §2 — IBKR `apiClient` methods (T-009).
- `docs/reality/workflows/morning-chain-orchestration.md` (T-011) — downstream consumer of synced data.
- `docs/reality/workflows/cold-start-seeding-and-watchlist-confirmation.md` (T-012) — the orchestrator detection that depends on `ibkr_position_snapshots`.
