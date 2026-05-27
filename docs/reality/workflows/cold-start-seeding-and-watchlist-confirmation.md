# Reality — workflow: cold-start seeding + watchlist confirmation

**Scope.** End-to-end trace of the first day a new IBKR account is connected: the orchestrator detects `mode_detected="cold_start"`, calls the starter-watchlist seeder, the user sees the cold-start banner in the frontend, the user edits the starter set if they want, and types `BEVESTIG` to flip the confirmation state from `unconfirmed` to `confirmed`. Subsequent fires then run as `mode_detected="normal"`.

This doc is a **synthesis** of four T-007/T-008/T-009 reality docs + one T-005 surface. Every claim cites a sibling reality doc rather than re-citing source.

Source-of-truth reality docs:

- `docs/reality/components/worker-orchestration-and-scheduling.md` §6 (orchestrator detection) + §9 (starter_watchlist module).
- `docs/reality/components/api-actions-suggestions-and-watchlists.md` (watchlist confirmation routes — T-005).
- `docs/reality/components/web-pages.md` §3.6 (`/volglijst` route) + `docs/reality/components/web-components-feature-grids.md` §11 (`VolglijstColdStartFlow.tsx`).
- `docs/reality/components/web-components-status-and-shared.md` §5 (`ColdStartBanner.tsx` polling badge).
- `docs/reality/components/web-api-client-and-text.md` §2 (apiClient method catalogue — watchlist section).

## 0. TL;DR — what happens on day 1

A brand-new IBKR account is configured (`WORKER_IBKR__ACCOUNT_ID=DUxxxxxxx`). At 06:00 Brussels the first morning, the worker orchestrator:

1. Detects `mode_detected="cold_start"` because the account has no positions and no watchlist items in storage.
2. Invokes the seed_runner, which writes 12 starter assets to `watchlist_items` (idempotent via `cold_start_seed_audit` UNIQUE), upserts `watchlist_confirmation_state` to `unconfirmed`, and appends a `watchlist_confirmation_audit` row `absent → unconfirmed`.
3. Subsequent fires same day detect the unconfirmed confirmation state and override the mode to `awaiting_watchlist_confirmation` — the morning chain SKIPS forecasting/decision-package steps until the user confirms.

In the frontend:

4. The `<ColdStartBanner>` polls `/watchlist/confirmation-state` every 60 s and shows a sticky amber banner with `state.banner_text` linking to `/volglijst`.
5. On `/volglijst`, the user sees `<VolglijstColdStartFlow>` rendering the 12 starter assets. They can delete some via the optimistic-archive flow.
6. The user types `BEVESTIG` (literal Dutch token, all caps) into the confirmation input and clicks "Volglijst bevestigen".
7. `apiClient.confirmWatchlist("BEVESTIG")` flips the confirmation state `unconfirmed → confirmed`. Banner disappears. Next orchestrator fire sees `mode_detected="normal"` and runs the full morning chain (see `morning-chain-orchestration.md`).

The whole flow is **one-time per `ibkr_account_id`**: the `cold_start_seed_audit` UNIQUE constraint blocks any second seed attempt for the same account.

## 1. Trigger — when does cold-start fire?

Per `worker-orchestration-and-scheduling.md` §6 control flow step 5:

The orchestrator runs **per APScheduler fire** (06:00 pre_briefing, 07:00–21:00 hourly_delta). After the connectivity probe (`gateway.is_connected()`) succeeds, it runs the cold-start detection at `orchestrator.py:268-282`:

```
if ibkr_account_id is None:
    mode_detected = "cold_start"
else:
    position_count = snapshot_counts.position_snapshot_count_for_account(ibkr_account_id)
    watchlist_count = snapshot_counts.watchlist_item_count_for_account(ibkr_account_id)
    if position_count == 0 and watchlist_count == 0:
        mode_detected = "cold_start"
    else:
        mode_detected = "normal"
```

`_PositionSnapshotCounts` lives in `scheduler.py:54-98` and runs two SQL queries against the live storage connection:

- `SELECT COUNT(*) FROM ibkr_position_snapshots WHERE ibkr_account_id = :a OR account_ref = :a` (`scheduler.py:67-79`).
- `SELECT COUNT(*) FROM watchlist_items WHERE status = 'active'` (`scheduler.py:81-98`). The watchlist count is currently account-unaware — flagged in T-007 as `# noqa: ARG002 — pending account-aware watchlist`.

**Cold-start triggers**:

- A configured-but-unprovisioned account (`WORKER_IBKR__ACCOUNT_ID=DU...`) connected for the first time (positions empty + watchlist empty).
- The `WORKER_IBKR__ACCOUNT_ID` env var is unset → `ibkr_account_id is None` path. (This is unlikely in production but possible during local development.)

## 2. Step 1 — seed invocation (orchestrator → seed_runner)

Per `worker-orchestration-and-scheduling.md` §6 control flow step 6 (`orchestrator.py:283-294`):

```
if mode_detected == "cold_start" and ibkr_account_id is not None and seed_runner is not None:
    try:
        seed_runner.seed(ibkr_account_id)
    except Exception:
        logger.exception("starter watchlist seed failed for %s", ibkr_account_id)
```

The seed_runner is declared as `_SeedRunnerProtocol` in `orchestrator.py:73-81` with a single method `seed(ibkr_account_id) -> bool`; idempotent. Exceptions are caught + logged + continued — the rest of the orchestrator run proceeds even if seeding fails.

**Production-wiring gap (Phase 1c)**: per T-007 §9, `seed_starter_watchlist` is NOT yet wired into the orchestrator's `seed_runner` slot in production. The protocol exists, the implementation exists, but the seed-runner factory that produces a `_SeedRunnerProtocol` instance for the orchestrator is not yet present in the files reviewed. **This doc records the intended contract; the actual production-day seeding happens via either a manual one-time CLI run or via a downstream API call.** See §6 below for the API alternative.

## 3. Step 2 — starter watchlist seeder (`starter_watchlist.seed_starter_watchlist`)

Per `worker-orchestration-and-scheduling.md` §9, the seeder lives at `apps/worker/src/portfolio_outlook_worker/starter_watchlist.py`.

### Signature (`starter_watchlist.py:183-192`)

```python
def seed_starter_watchlist(
    *,
    ibkr_account_id: str,
    seed_audit_repo: SqlAlchemyColdStartSeedAuditRepository,
    watchlist_seed_repo: SqlAlchemyWatchlistItemSeedRepository,
    confirmation_state_repo: SqlAlchemyWatchlistConfirmationStateRepository,
    confirmation_audit_repo: SqlAlchemyWatchlistConfirmationAuditRepository,
    listing_resolver: AssetListingResolverProtocol | None = None,
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> SeedResult
```

Returns `SeedResult(already_seeded: bool, seeded_count: int, failed_symbols: tuple[str, ...])` (`starter_watchlist.py:174-180`).

### Pre-check + idempotency (`starter_watchlist.py:210-217`)

```python
existing = seed_audit_repo.find_by_account_id(ibkr_account_id)
if existing is not None:
    return SeedResult(already_seeded=True, seeded_count=existing.seeded_count, failed_symbols=())
```

If a prior seed audit row exists, the function returns immediately without touching the watchlist. Module docstring (`starter_watchlist.py:1-7`) is explicit: "at most once per `ibkr_account_id` (idempotency enforced by the `cold_start_seed_audit` table's `UNIQUE` on `ibkr_account_id`)."

**Race handling** (`starter_watchlist.py:274-279`): if two worker processes hit the seeder simultaneously, the second one's `seed_audit_repo.append(...)` raises `ColdStartAlreadySeededError`. The function catches and returns `already_seeded=True` with the local `seeded_count`.

### Empty-account guard (`starter_watchlist.py:207-208`)

```python
if not ibkr_account_id:
    raise ValueError("ibkr_account_id is required for the seed")
```

This is the only `raise` in the function — every other failure mode returns a result, never raises.

## 4. The 12-row v1 starter set

Locked at `starter_watchlist.py:66-154` as `STARTER_WATCHLIST_V1: tuple[StarterAsset, ...]`. `SEED_VERSION = "v1"` (`starter_watchlist.py:48`). Categorised:

### 5 broad UCITS ETFs (`starter_watchlist.py:67-102`)

| # | Symbol | Name | Exchange | Currency | Type |
|---:|---|---|---|---|---|
| 1 | SXR8 | iShares Core S&P 500 | XETRA | EUR | ETF |
| 2 | VWCE | Vanguard FTSE All-World | XETRA | EUR | ETF |
| 3 | EQQQ | Invesco Nasdaq-100 | XETRA | EUR | ETF |
| 4 | EXSA | iShares Stoxx 600 | XETRA | EUR | ETF |
| 5 | AGGH | Xtrackers Global Aggregate Bond | XETRA | EUR | ETF |

### 5 European blue chips (`starter_watchlist.py:103-138`)

| # | Symbol | Name | Exchange | Currency | Type |
|---:|---|---|---|---|---|
| 6 | ASML | ASML Holding | AEB | EUR | STK |
| 7 | MC | LVMH | SBF (Paris) | EUR | STK |
| 8 | NOVO-B | Novo Nordisk B | CPH | DKK | STK |
| 9 | SAP | SAP | XETRA | EUR | STK |
| 10 | SHEL | Shell | LSE | GBP | STK |

### 2 sector UCITS ETFs (`starter_watchlist.py:139-153`)

| # | Symbol | Name | Exchange | Currency | Type |
|---:|---|---|---|---|---|
| 11 | WTEC | WisdomTree Cybersecurity | XETRA | EUR | ETF |
| 12 | IS3N | iShares MSCI World Healthcare | XETRA | EUR | ETF |

`StarterAsset` is a frozen dataclass at `starter_watchlist.py:51-60`: `symbol`, `exchange`, `currency`, `security_type`, `name`, `ibkr_conid_hint`. The `ibkr_conid_hint` is a static guess; production code resolves the actual conid via the optional `listing_resolver`.

## 5. Step 3 — the 4-table write pattern

Per `worker-orchestration-and-scheduling.md` §9, a successful first-time seed writes to exactly 4 tables:

### Table 1 — `watchlist_items` (per-asset, append)

For each of the 12 starter assets (subject to per-asset failures — see §5b), append a `WatchlistItemSeedRecord` via `watchlist_seed_repo.append(...)` (`starter_watchlist.py:235-260`). The record carries:

- `source = "cold_start_seed"` (`:245`)
- `is_starter_seed = True` (`:246`)
- `seed_version = "v1"` (`:247`)
- `status = "active"`
- IBKR conid (resolved via `listing_resolver.find_listing(symbol, exchange, currency)` if wired; else `ibkr_conid_hint` from the static set).

### Table 2 — `cold_start_seed_audit` (write-once per account)

After the watchlist loop, append a `ColdStartSeedAuditEntry` via `seed_audit_repo.append(...)` (`starter_watchlist.py:264-273`). Fields:

- `ibkr_account_id` (the **UNIQUE key** that enforces one-seed-per-account)
- `seeded_at` (via `now_provider`)
- `seeded_count` (number of `watchlist_items` rows actually written)
- `failed_conids_json = json.dumps(failed)` — list of symbols where listing resolution failed.

### Table 3 — `watchlist_confirmation_state` (upsert, per account)

`confirmation_state_repo.upsert(WatchlistConfirmationStateRecord(state="unconfirmed", ...))` (`starter_watchlist.py:282-288`).

The state literal is `"unconfirmed"` — the value the `ColdStartBanner` polls for. Per T-008 `web-components-status-and-shared.md` §5, the three observable state values are `"unconfirmed"` (banner shows), `"confirmed"` (banner null), `"no_account_configured"` (banner null).

### Table 4 — `watchlist_confirmation_audit` (append-only state-transition ledger)

`confirmation_audit_repo.append(WatchlistConfirmationAuditEntry(from_state="absent", to_state="unconfirmed", actor="system", ...))` (`starter_watchlist.py:289-301`).

`actor="system"` distinguishes seeder-driven transitions from later user-driven ones (`actor="user"` when the BEVESTIG flow fires).

### Side note: per-asset failures (`starter_watchlist.py:223-259`)

If `listing_resolver.find_listing(...)` returns `None` for a starter asset, that symbol is appended to `failed: list[str]` and SKIPPED — the seed continues with the rest. Failed symbols end up serialised into:

- `cold_start_seed_audit.failed_conids_json` (`:270`).
- `watchlist_confirmation_audit.details_json` (`:297-299`).

So partial-seed scenarios are observable in two audit tables.

## 6. Step 4 — alternative seeder invocation paths

The orchestrator's `seed_runner` slot is not yet wired in production (Phase 1c gap noted above). In practice the seeder runs via one of two paths:

### Path A — direct CLI / manual invocation

An operator runs `seed_starter_watchlist(...)` from a Python REPL or one-shot script with the four storage repositories from `ai_trading_agent_storage`. This is the dev-time path.

### Path B — API endpoint trigger

Per T-005 `api-actions-suggestions-and-watchlists.md`, the API exposes a `/watchlist/cold-start-items` GET endpoint, plus DELETE / confirmation mutations. The seeder is **not** exposed as an API endpoint; the API surface assumes the seed has already happened (via Path A or the orchestrator's eventual wiring) and only exposes the read + edit + confirm operations.

The Phase 1c surface is the gap between the documented intent (orchestrator-driven, fully automated) and the current reality (operator-driven, one-shot).

## 7. Step 5 — second + later orchestrator fires

Per `worker-orchestration-and-scheduling.md` §6 control flow step 7 (`orchestrator.py:296-310`):

```
if confirmation_state is not None and ibkr_account_id is not None and mode_detected != "cold_start":
    state = confirmation_state.get_state(ibkr_account_id)
    if state == "unconfirmed":
        mode_detected = "awaiting_watchlist_confirmation"
```

After the first seed lands, subsequent orchestrator fires re-evaluate:

1. `cold_start` mode no longer fires because `watchlist_count > 0` (the 12 seeded rows count as "active" watchlist items per the SQL query at `scheduler.py:81-98`).
2. The orchestrator computes `mode_detected = "normal"` from the count check.
3. The confirmation-state override at `orchestrator.py:296-310` then **demotes** `"normal"` back to `"awaiting_watchlist_confirmation"` because `state == "unconfirmed"`.

**Result**: between seed and confirmation, every orchestrator fire writes an audit row with `mode_detected="awaiting_watchlist_confirmation"`, `outcome="completed"`. The morning chain's market-data / forecasting / decision-package / calibration steps **all skip** because their gates require `mode_detected == "normal"`.

The docstring comment at `orchestrator.py:300-302` records the documented sequence: `cold_start → awaiting_watchlist_confirmation → normal`.

## 8. Step 6 — the frontend cold-start banner

Per T-008 `web-components-status-and-shared.md` §5:

- `ColdStartBanner.tsx:1` is a client component declared `"use client"`.
- Polls `apiClient.getWatchlistConfirmationState()` every **60 s** (interval at `ColdStartBanner.tsx:24`).
- Returns `null` unless `state.state === "unconfirmed"` (`:53-55`).
- When showing, renders a sticky amber banner with the server-supplied `state.banner_text` (`:76`) + a `next/link` to `/volglijst` labelled `"Naar Volglijst"` (`:89`).

The banner is rendered globally from `apps/web/app/layout.tsx:51` (the root layout, see T-008 `web-pages.md` §2). It sits above `{children}` so it appears on every page.

**State values observed** (per the `WatchlistConfirmationStateResponse` Pydantic shape at `apiClient.ts:715`, T-009 §3):

- `"unconfirmed"` — banner shows.
- `"confirmed"` — banner returns `null`.
- `"no_account_configured"` — banner returns `null` (commented at `ColdStartBanner.tsx:9-13`).

## 9. Step 7 — the `/volglijst` cold-start view

Per T-008 `web-pages.md` §3.6:

The `/volglijst` page (`apps/web/app/volglijst/page.tsx`) has a top-level branch (`:61-67`):

- If confirmation state is `"unconfirmed"` → render `<VolglijstColdStartFlow onConfirmed={...} />`.
- Else → render `<VolglijstConfirmedView />` (the normal watchlist UI).

The outer page polls `apiClient.getWatchlistConfirmationState()` once on mount (`:49-51`).

## 10. Step 8 — `VolglijstColdStartFlow` (the BEVESTIG UI)

Per T-008 `web-components-feature-grids.md` §11:

- Component at `apps/web/components/VolglijstColdStartFlow.tsx` (225 lines).
- `"use client"` at `:1`.
- Single prop: `onConfirmed: () => void` (`:26-30`).

### Fetches on mount (`:43`)

`apiClient.getColdStartWatchlistItems()` (per T-009 `web-api-client-and-text.md` §2: `GET /watchlist/cold-start-items`, returns `ColdStartWatchlistResponse`).

### Two user actions

**Action A — archive a starter item (optimistic UI)**:

- User clicks `Verwijder` on a starter row (`VolglijstColdStartFlow.tsx:150`).
- Frontend calls `apiClient.deleteColdStartWatchlistItem(watchlistItemId)` (`:58-60`; per T-009 §2: `DELETE /watchlist/cold-start-items/{id}`).
- After API success, the row is removed from local state without a re-fetch (`:65-67`): `setItems((prev) => prev.filter(...))`.
- **This is the only optimistic UI update in the entire 11-component feature-grid cluster** (per T-008 `web-components-feature-grids.md` §E). Justified because the API mutation is delete-only and the per-row delete cannot fail in any way that requires UI rollback.

Backend side: archives the `watchlist_items` row (sets `status="archived"` per the storage state machine). The user's intent is "I don't want this starter asset in my watchlist."

**Action B — confirm the watchlist (the BEVESTIG token)**:

- User types into a `<input>` bound to `phrase` (`:35`).
- User clicks `Volglijst bevestigen` (`:210`).
- Frontend calls `apiClient.confirmWatchlist(phrase)` (`:74`; per T-009 §2: `POST /watchlist/confirm`, returns `ApiResult<WatchlistConfirmResponse>`).

The locked Dutch instruction at `VolglijstColdStartFlow.tsx:174-177`:

> "Typ het woord BEVESTIG (in hoofdletters) om te bevestigen. Daarna start het systeem met geplande runs."

The component-level enforcement: the submit button is disabled when `!canSubmit || submitting` (T-008 §11), so the literal `"BEVESTIG"` token is checked client-side before the API call goes out. The API-side check is the authoritative gate.

On success, `onConfirmed()` callback fires (passed in by `/volglijst/page.tsx:65`), which triggers a page-level re-fetch of the confirmation state — the cold-start branch flips to the confirmed-view branch.

## 11. Step 9 — confirmation API endpoint

Per T-005 `api-actions-suggestions-and-watchlists.md` + T-009 `web-api-client-and-text.md` §2:

- `apiClient.confirmWatchlist(phrase)` → `POST /watchlist/confirm` with `{phrase}` body.
- Returns `ApiResult<WatchlistConfirmResponse>` — the `ApiResult` variant means transport failures + backend Dutch error strings are both surfaced (T-009 §1).

The API-side handler:

1. Validates `phrase == "BEVESTIG"` (literal token).
2. Upserts `watchlist_confirmation_state` row: `unconfirmed → confirmed`.
3. Appends `watchlist_confirmation_audit` row: `from_state="unconfirmed"`, `to_state="confirmed"`, `actor="user"`.
4. Returns success or Dutch error.

The `ColdStartBanner` will see `state === "confirmed"` on its next 60s poll cycle and return `null`. The banner disappears.

## 12. Step 10 — return to normal orchestrator mode

The next orchestrator fire after the user confirms:

1. Cold-start detection: `position_count + watchlist_count > 0` → `mode_detected = "normal"`.
2. Confirmation-state override: `state == "confirmed"` → no override applied; `mode_detected` stays `"normal"`.
3. Morning-chain gates (market-data / forecasting / decision-package / calibration) all evaluate to True (per `morning-chain-orchestration.md` §§5-8) — the full chain runs for the first time.

From the user's perspective: they confirm Tuesday evening, and Wednesday at 06:30 their first daily briefing is computed.

## 13. Side effects (tables written across the full flow)

| Table | Op | When | Repository | Idempotency key |
|---|---|---|---|---|
| `watchlist_items` | per-asset append | step 5 table 1 (seed) | `SqlAlchemyWatchlistItemSeedRepository` | none (relies on `cold_start_seed_audit` pre-check) |
| `cold_start_seed_audit` | append | step 5 table 2 (seed) | `SqlAlchemyColdStartSeedAuditRepository` | UNIQUE on `ibkr_account_id` |
| `watchlist_confirmation_state` | upsert | step 5 table 3 (seed) + step 11 (confirm) | `SqlAlchemyWatchlistConfirmationStateRepository` | row-per-account |
| `watchlist_confirmation_audit` | append | step 5 table 4 (seed) + step 11 (confirm) | `SqlAlchemyWatchlistConfirmationAuditRepository` | none (append-only) |
| `watchlist_items` | per-row archive | step 10 action A | (same repo, different method) | per `watchlist_item_id` |
| `scheduled_run_audit` | one row per orchestrator fire | every fire | `SqlAlchemyScheduledRunAuditRepository` | per `run_id` |

A typical day-1 timeline writes:

- 06:00 pre_briefing fire: 1 `scheduled_run_audit` row (`mode_detected="cold_start"`).
- (seed runs via Path A or B): 12 `watchlist_items` rows + 1 `cold_start_seed_audit` row + 1 `watchlist_confirmation_state` row + 1 `watchlist_confirmation_audit` row.
- 07:00 hourly fire: 1 `scheduled_run_audit` row (`mode_detected="awaiting_watchlist_confirmation"`).
- 08:00–18:00 hourly fires (10 rows): same `awaiting_watchlist_confirmation` mode.
- (user opens `/volglijst`, archives 2 starter items): 2 `watchlist_items` rows updated (status → `archived`).
- (user types BEVESTIG): 1 `watchlist_confirmation_state` upsert + 1 `watchlist_confirmation_audit` row.
- Next fire (e.g. 19:00 hourly): 1 `scheduled_run_audit` row, this time `mode_detected="normal"`.

Total day-1 audit-row count: ~30 rows across 4 tables.

## 14. Failure paths

| Failure | Symptom | Audit-row signal | Recovery |
|---|---|---|---|
| Empty `ibkr_account_id` env var | seeder raises `ValueError` (`starter_watchlist.py:207-208`); orchestrator's `seed_runner` slot is unused — never invoked | none | operator sets env var, restarts worker |
| `cold_start_seed_audit` row already exists | seeder returns `SeedResult(already_seeded=True, ...)` without writing | no new rows | by design — re-runs are silent no-ops |
| Race: two workers seed concurrently | first wins; second catches `ColdStartAlreadySeededError`, returns `already_seeded=True` | one `cold_start_seed_audit` row | by design |
| Per-asset `listing_resolver.find_listing(...)` returns `None` | symbol appended to `failed`; seed continues | `cold_start_seed_audit.failed_conids_json` records the failed symbols + `watchlist_confirmation_audit.details_json` mirror | operator re-runs listing resolution offline + appends rows manually |
| `confirmWatchlist("WRONG_TOKEN")` | API returns 4xx with Dutch error | `watchlist_confirmation_audit` NOT written (validation rejects before the upsert) | user re-types BEVESTIG correctly |
| Frontend offline during BEVESTIG | `apiClient.confirmWatchlist` returns `ApiResult { ok: false, status: 0, message: "API niet bereikbaar." }` | no audit row | user retries when API is back |
| User clicks "Verwijder" but archive API call fails | optimistic UI removed the row; API returned error; the local state diverges from server state until next page load | `watchlist_items` row NOT archived server-side | user reloads page → row reappears |

The optimistic-archive divergence (last row) is a known UX trade-off: T-008 §E flags this as the only optimistic mutation in the cluster.

## 15. Explicit out-of-scope

- **Subsequent watchlist edits after confirmation** — once `state == "confirmed"`, all watchlist operations go through `VolglijstConfirmedView` and the `/watchlist/items` API (T-005 + T-008 `web-pages.md` §3.6, T-009 §2). The cold-start UI is one-shot.
- **Forecasting / decision-package generation** — only runs after `mode_detected = "normal"` per `morning-chain-orchestration.md`. Out of scope here.
- **The intent gap** ("orchestrator wires the seed_runner") — flagged but not resolved. T-007 §9 carries the Phase 1c surface.
- **Multi-account scenarios** — the seeder is account-scoped via UNIQUE constraint, but the `_PositionSnapshotCounts.watchlist_item_count_for_account(...)` SQL ignores the account parameter (`scheduler.py:81-98` with `# noqa: ARG002` annotation). A second account on the same worker would re-trigger `mode_detected="cold_start"` even after account-1 confirms — this contradicts the per-account isolation the seeder enforces. Phase 1c surface.

## 16. Cross-cutting observations + Phase 1c surface

- **The orchestrator's `seed_runner` slot is declared but not yet wired in production.** Documented in T-007 §9. Until the wiring lands, cold-start seeding happens via direct CLI invocation (Path A in §6 above).
- **Watchlist count check is account-unaware** (`scheduler.py:81-98`). Multi-account installs would see cross-account interference. Phase 4 candidate (the comment already says "pending account-aware watchlist").
- **The `awaiting_watchlist_confirmation` mode pauses the entire morning chain.** This is intentional — running forecasts against a watchlist the user hasn't curated would produce noise. But the pause is **silent** to operators unless they read `scheduled_run_audit` rows. A future `ColdStartBanner` equivalent on an operator dashboard would close that visibility gap.
- **The BEVESTIG token is hardcoded** — locked Dutch literal in both frontend (`VolglijstColdStartFlow.tsx:174-177`) and (presumably) backend. A future i18n pass would need to coordinate the token.
- **Optimistic archive UI is the only optimistic mutation in the cluster.** T-008 §E flags this; the trade-off (UI divergence on archive-API-failure) is bounded to one page reload.
- **`seed_version = "v1"`** is hard-coded at `starter_watchlist.py:48`. Future starter-set revisions need a version-bump strategy — likely a new `_v2` constant + a migration path for accounts already seeded with `v1`. Phase 4 candidate.
- **The 12-row v1 list is heavily Eurozone-biased** (10 of 12 are EUR-denominated; 1 is GBP, 1 is DKK). Future portfolio brainstorms may want to revisit the starter set composition; in the meantime, the user can always archive starter items they don't want.

## 17. References

- `docs/reality/components/worker-orchestration-and-scheduling.md` §6 (orchestrator cold_start detection + seed_runner gate + confirmation-state override) and §9 (starter_watchlist module).
- `docs/reality/components/api-actions-suggestions-and-watchlists.md` (T-005 — watchlist confirmation routes).
- `docs/reality/components/web-pages.md` §3.6 (T-008 — `/volglijst` route with cold-start branch).
- `docs/reality/components/web-components-status-and-shared.md` §5 (T-008 — `ColdStartBanner.tsx`).
- `docs/reality/components/web-components-feature-grids.md` §11 (T-008 — `VolglijstColdStartFlow.tsx`).
- `docs/reality/components/web-api-client-and-text.md` §2 (T-009 — `apiClient` watchlist methods).
- `docs/reality/workflows/morning-chain-orchestration.md` (T-011 — what runs once `mode_detected="normal"`).
