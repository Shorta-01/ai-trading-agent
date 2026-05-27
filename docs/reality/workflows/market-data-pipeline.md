# Reality — workflow: market-data pipeline (research + execution)

**Scope.** End-to-end trace of how market data enters the system, where it's persisted, how freshness is evaluated, and which downstream consumers depend on it. Two distinct paths:

1. **Research path** — EODHD EOD bars + FX rates → worker `market_data_step.py` → `market_data_snapshots` + `fx_rate_snapshots` + `market_data_bars` tables. Powers forecasting (T-011 morning chain), portfolio valuation, and the Decision Package composer.
2. **Execution path** — IBKR live quotes → API `IbkrMarketDataAdapter.fetch_latest_snapshot` → `market_data_latest_snapshots` table. Powers order ticket construction (live `last_price` for LMT order pricing).

The two paths **converge in storage** at `market_data_latest_snapshots` (a "latest per asset" cache) but operate on different freshness scales. The locked freshness policy at `packages/domain/.../market_data_foundation.py:103-106` (fresh=15 min, near_stale=30 min) is the single arbiter, applied at read-time by `evaluate_market_data_readiness`.

**Sibling reality docs (read for module-level detail):**

- `docs/reality/components/worker-forecasting-and-decision-package.md` §7-§8 — worker `market_data_step.py` + `providers/eodhd.py` (T-007).
- `docs/reality/components/api-forecasting-and-market-data.md` — API `market_data_*` modules incl. `market_data_sync.py`, `market_data_runtime_routes.py`, `market_data_readiness.py`, `eodhd_client.py` (T-005).
- `docs/reality/components/storage-package-and-migrations.md` — `market_data_snapshots`, `market_data_latest_snapshots`, `fx_rate_snapshots`, `market_data_bars` tables (T-003).
- `docs/reality/workflows/morning-chain-orchestration.md` §5 — primary consumer of EODHD market data (T-011).
- `docs/reality/workflows/ibkr-readonly-sync-positions-cash.md` — adjacent IBKR flow (read-only sync); does NOT touch market data (T-013).

## 0. TL;DR

Two flows write to overlapping tables:

**A. EODHD daily flow** — worker's morning chain calls `market_data_step.fetch_market_data_for_account` (T-007 §7) at 06:00 + 07:00 Brussels. EODHD `fetch_eod(symbol, exchange, date)` + `fetch_fx(base, quote, date)` populate `market_data_snapshots` + `fx_rate_snapshots`. **Idempotent** on `(ibkr_conid, as_of_date, provider)` for snapshots and `(base, quote, as_of_date, provider)` for FX. Driven by `compose_action_draft_*` + the Decision Package composer that need yesterday's close to compute notional values.

**B. IBKR live-quote flow** — API endpoint `/market-data/snapshots/latest/{ibkr_conid}` (T-005) invokes `IbkrMarketDataAdapter.fetch_latest_snapshot(identity)`. Writes one row to `market_data_latest_snapshots` per fetch. **Not yet wired in production** — the IBKR market-data settings (`apps/api/.../config.py:96-104`) default to `ibkr_market_data_enabled=False`; the live-quote path is a separate IBKR socket from the read-only sync (T-013).

**Convergence**: forecasting consumes EODHD-written rows via `forecasting_step.close_provider` (T-007 §4); portfolio valuation consumes both EODHD `market_data_snapshots` AND IBKR `market_data_latest_snapshots` via the `market_data_latest_snapshots` cache.

**Hard safety floor**: every row written through `IbkrMarketDataAdapter` carries `safe_for_analysis=False`, `safe_for_suggestions=False`, `safe_for_action_drafts=False` (`ibkr_market_data.py` last 5 lines) — market-data is data, not advice. Same floor applies to the EODHD path via the `MarketDataLatestSnapshotRecord` dataclass defaults.

## 1. The two paths at a glance

| Path | Trigger | Source | Worker / API | Frequency | Tables written | Consumers |
|---|---|---|---|---|---|---|
| **EODHD research** | morning_chain `market_data` step + manual API `POST /market-data/sync` | EODHD `/eod/{sym}.{exch}` + `/eod/{base}{quote}.FOREX` | Worker (`market_data_step.py`) + API (`market_data_sync.py`) | Daily at 06:00 + 07:00 Brussels (worker); on-demand (API) | `market_data_snapshots`, `fx_rate_snapshots`, `market_data_bars`, `market_data_latest_snapshots` | forecasting, DP composer, portfolio valuation |
| **IBKR live-quote execution** | `/market-data/snapshots/latest/{conid}` route | IBKR TWS live quotes via `ib_insync` | API (`ibkr_market_data.py:IbkrMarketDataAdapter`) | On-demand per route call | `market_data_latest_snapshots` | order ticket construction (Phase 4) |

## 2. The locked freshness policy

`packages/domain/src/portfolio_outlook_domain/market_data_foundation.py:103-106`:

```python
@dataclass(frozen=True)
class MarketDataReadinessPolicy:
    fresh_within: timedelta = timedelta(minutes=15)
    near_stale_within: timedelta = timedelta(minutes=30)
```

Applied by `evaluate_market_data_readiness(snapshot, now, policy)` (`market_data_foundation.py:118-166`).

### 2.1 The 5-state freshness enum

`market_data_foundation.py:79-84`:

| State | When emitted |
|---|---|
| `missing_snapshot` | `snapshot is None` |
| `fresh` | `age ≤ 15 min` (per `policy.fresh_within`) |
| `near_stale` | `15 min < age ≤ 30 min` (per `policy.near_stale_within`) |
| `stale` | `age > 30 min` |
| `unusable` | (declared in enum at `:84` but no logic in this file emits it — handled at higher layers) |

The `age` reference timestamp is `snapshot.provider_as_of or snapshot.received_at or snapshot.stored_at` (`market_data_foundation.py:132`) — picks the most-authoritative timestamp available, with `provider_as_of` (when IBKR/EODHD stamped the data) preferred over `received_at` (when we got the response) over `stored_at` (when we persisted it).

### 2.2 Valuation readiness derived from freshness

`MarketDataValuationReadinessStatus` (6-state, `:87-93`):

| State | Condition |
|---|---|
| `not_ready` | placeholder default (unused in `evaluate_market_data_readiness`) |
| `ready_for_status_only` | placeholder default |
| `ready_for_valuation_preview` | freshness ∈ `{fresh, near_stale}` AND price available |
| `blocked_missing_snapshot` | `snapshot is None` |
| `blocked_stale_snapshot` | `freshness == stale` (`age > 30min`) |
| `blocked_missing_price` | freshness ok but no `last_price` and no bid+ask pair |

### 2.3 Price-basis fallback

`market_data_foundation.py:144-152`:

```python
if snapshot.last_price is not None:
    basis = MarketDataPriceBasis.LAST           # use last
    price = snapshot.last_price
elif snapshot.bid_price is not None and snapshot.ask_price is not None:
    basis = MarketDataPriceBasis.MIDPOINT       # use (bid+ask)/2
    price = (snapshot.bid_price + snapshot.ask_price) / Decimal("2")
else:
    basis = MarketDataPriceBasis.UNAVAILABLE
    price = None
```

4-state `MarketDataPriceBasis` enum (`:96-100`): `last` / `midpoint` / `close` / `unavailable`. (`close` is declared but `evaluate_market_data_readiness` doesn't emit it — likely used by downstream code for EOD-only snapshots.)

The fallback is **Decimal-end-to-end**: the midpoint arithmetic uses `Decimal("2")` not `float`, preserving precision per the project's Decimal-as-string doctrine (T-002 `portfolio-money-and-accounting.md`).

## 3. Path A — EODHD research flow

### 3.1 Worker entry point (T-007 §7)

`apps/worker/src/portfolio_outlook_worker/market_data_step.py:92-103`:

```python
def fetch_market_data_for_account(
    *,
    ibkr_account_id: str,
    asset_universe: _AssetUniverseProtocol,
    snapshot_repo: SqlAlchemyMarketDataEodSnapshotRepository,
    fx_rate_repo: SqlAlchemyFxRateRepository,
    eodhd_client: EodhdClient,
    target_date: date,
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC),
    base_currency: str = "EUR",
) -> MarketDataFetchResult
```

Called from the morning chain (T-011 §5) when `mode_detected == "normal"` AND `run_type in ("pre_briefing", "morning_briefing")`.

### 3.2 EODHD client (T-007 §8)

`apps/worker/.../providers/eodhd.py` (415 lines):

- Two endpoints implemented: `fetch_eod(symbol, exchange, as_of_date)` (`:143-167`) → `GET /eod/{symbol}.{exchange}?api_token=...&fmt=json&from=...&to=...`; and `fetch_fx(base, quote, as_of_date)` (`:169-190`) → `GET /eod/{base}{quote}.FOREX?...`.
- **No fundamentals / splits / dividends endpoints** despite ADR 0003's "EODHD All-In-One data tier required" intent (`docs/decisions/0003-forecast-engine-architecture.md:29`). T-007 §1 flags this as the largest intent-vs-reality gap in the worker.
- Retry once on 5xx with 2 s backoff; no retry on 4xx (`:206-269`).
- Rate limiter: 10 r/s default token-bucket (`:90-112`).
- API key passed as `api_token` query param; **stripped from audit rows** (`:288-289`).
- Decimal-as-string throughout: `_decimal_required(value) → Decimal(str(value))` (`:375-378`), no float intermediates.

### 3.3 API mirror (T-005)

`apps/api/src/portfolio_outlook_api/eodhd_client.py` (505 lines) — separate code path from the worker's `providers/eodhd.py`. T-005 documents the API-side client.

`apps/api/.../market_data_adapter_factory.py:20-55` (`build_market_data_provider`) gates the API path on 4 conditions:

1. `settings.market_data_sync_enabled` must be True.
2. `settings.market_data_provider.lower() == "eodhd"`.
3. `settings.eodhd_enabled` must be True.
4. `settings.eodhd_api_key` must be present.

If any gate fails → returns `None` → callers must report "not configured" rather than fall back to fake data (per the factory's docstring at `market_data_adapter_factory.py:3-5`).

### 3.4 Per-asset flow (worker side)

Per T-007 §7 — for each asset in the resolved universe:

1. **Duplicate skip** — `seen_conids` set (`market_data_step.py:122-126`).
2. **Idempotency check** — `snapshot_repo.get_for_date(ibkr_conid, as_of_date, provider=PROVIDER_CODE)`; if exists, skip (`:129-135`).
3. **Fetch EOD** — `eodhd_client.fetch_eod(symbol, exchange, target_date)` (`:138-143`).
4. **Persist snapshot** — `snapshot_repo.append(MarketDataEodSnapshotEntry(...))` (`:166-185`) with `snapshot_id=f"mdsnap_{uuid4().hex}"`, OHLCV + adj_close + `provider_response_hash`.
5. **Track currency** — add `asset.currency_local` to `needed_currencies` (`:120, :127`).

After all snapshots: iterate `sorted(needed_currencies)`; for each non-EUR currency:

6. **Idempotency check** — `fx_rate_repo.get_rate(currency, base_currency, as_of_date, provider)` (`:209-216`).
7. **Fetch FX** — `eodhd_client.fetch_fx(currency, base_currency, target_date)` (`:219-222`).
8. **Persist FX** — `fx_rate_repo.upsert(FxRateRecord(base, quote, as_of_date, rate, ingested_ts, provider))` (`:245-254`).

**Returns** `MarketDataFetchResult(snapshots_attempted, snapshots_succeeded, snapshots_failed, fx_rates_attempted, fx_rates_succeeded, fx_rates_failed)` (`:70-89`). The step **never raises** — every failed fetch is logged + counted into the failure counters.

## 4. Path B — IBKR live-quote execution flow

### 4.1 Adapter

`apps/api/src/portfolio_outlook_api/ibkr_market_data.py:46-113`:

```python
class IbkrMarketDataAdapter:
    def __init__(self, settings: IbkrMarketDataSettings) -> None:
        self._settings = settings

    def fetch_latest_snapshot(self, identity: MarketDataIdentity) -> MarketDataFetchResult:
        ...
```

Configured via `IbkrMarketDataSettings` (frozen dataclass, `:19-29`) which is hydrated from `Settings` by `settings_from_runtime` (`:32-43`). All 9 fields come from API config (`apps/api/.../config.py:96-104`):

- `enabled: bool = False` ← `ibkr_market_data_enabled`
- `host: str | None = None` ← `ibkr_market_data_host`
- `port: int | None = None` ← `ibkr_market_data_port`
- `client_id: int | None = None` ← `ibkr_market_data_client_id`
- `readonly: bool = True` ← `ibkr_market_data_readonly` (default True, **same read-only enforcement as the sync flow per T-013 §3**)
- `account_mode: str = "paper"` ← `ibkr_market_data_account_mode`
- `market_data_type: str = "delayed"` ← `ibkr_market_data_type`
- `snapshot_timeout_seconds: int = 5` ← `ibkr_market_data_snapshot_timeout_seconds`
- `provider_code: str = "ibkr"` ← `ibkr_market_data_provider_code`

**Default is `enabled=False`** — the IBKR live-quote path is opt-in. Most Phase 1 environments will see this path inactive.

### 4.2 Identity validation pre-check

Before any fetch, `block_if_identity_invalid(identity)` (`market_data_foundation.py:63-76`) returns an early `MarketDataFetchResult` if:

- `identity.ibkr_conid.strip() == ""` → `MISSING_IDENTITY` (Dutch: "Contract ontbreekt: geen gevalideerde conid beschikbaar.")
- `not identity.identity_validated` → `IDENTITY_NOT_VALIDATED` (Dutch: "Contract niet gevalideerd: snapshot-aanvraag geblokkeerd.")

This is the **execution-side equivalent of the tier-two paper-account guard** (T-013 §3.2) — every IBKR market-data call is gated on having a validated `ibkr_conid` first.

### 4.3 The 12 fetch outcomes

`MarketDataFetchStatus` enum (`market_data_foundation.py:10-22`):

```
SUCCESS, NOT_CONFIGURED, MISSING_IDENTITY, IDENTITY_NOT_VALIDATED,
PROVIDER_PERMISSION_MISSING, PACING_LIMITED, NO_SNAPSHOT, PROVIDER_ERROR,
STORAGE_ERROR, STALE_SNAPSHOT, SNAPSHOT_AVAILABLE, PROVIDER_NOT_CONFIGURED
```

12 distinct fetch outcomes — every IBKR market-data request lands in exactly one. Each maps to a Dutch `message_nl` returned to the API caller via `MarketDataFetchResult`.

### 4.4 The hard `safe_for_*=False` floor

Per `apps/api/.../ibkr_market_data.py` (last 5 fields of the `MarketDataLatestSnapshotRecord` constructor):

```python
freshness_status="fresh",
explanation_nl=explanation_nl,
...
safe_for_analysis=False,
safe_for_suggestions=False,
safe_for_action_drafts=False,
```

**Even live IBKR quotes are flagged as "not safe for analysis/suggestions/action_drafts" at the record level.** Downstream consumers (forecasting, DP composer, action-draft sizing) must explicitly ignore these flags or apply their own safety logic. This is consistent with the project's "raw data is never advice" doctrine (AGENTS.md §13).

## 5. Storage tables

Per T-003 `storage-package-and-migrations.md` + `packages/storage/src/ai_trading_agent_storage/metadata.py`:

| Table | Migration | Op | Key | Foreign-keys | Read sites |
|---|---|---|---|---|---|
| `market_data_snapshots` | `0021_market_data_storage_foundation.py` | per-asset EOD append (Path A only) | composite (`ibkr_conid`, `as_of_date`, `provider`) | — | EOD historical reads |
| `market_data_latest_snapshots` | `0024_market_data_latest_snapshots.py` | per-asset latest (Path A and Path B converge here) | composite (`ibkr_conid`, `provider`) | — | portfolio valuation, order ticket construction, frontend `<PortefeuilleRealtimeSection>` |
| `fx_rate_snapshots` | (in 0021) | per-currency-pair EOD upsert (Path A only) | composite (`base`, `quote`, `as_of_date`, `provider`) | — | EUR conversion in DP composer, valuation totals |
| `market_data_bars` | `0027_market_data_bars_and_asset_forecasts.py` | historical OHLCV (Path A only, for forecasting close-history loads) | composite (`ibkr_conid`, `as_of_date`) | — | `close_provider.list_recent_closes` in T-007 §4 |

**Migration 0048** (`0048_market_data_eod_and_fx_runtime.py`) is the runtime-wiring migration that joined the snapshot tables to the morning-chain flow.

### 5.1 Convergence at `market_data_latest_snapshots`

Both paths write to this table; the consumer simply reads "the latest row for this `ibkr_conid`" without needing to know which path wrote it. The `provider_code` column distinguishes (`"eodhd"` vs `"ibkr"`) — a row from each path can coexist.

A consumer doing "get me the price right now for valuation" reads this table; the `freshness_status` column tells them whether the price is `fresh`, `near_stale`, `stale`, or `missing_snapshot` — applying the `MarketDataReadinessPolicy` from §2 transparently.

## 6. API surface

Per T-005 `api-forecasting-and-market-data.md` + the modules:

### 6.1 `market_data_sync.py` (522 lines)

The on-demand API trigger. Mirrors the worker's `market_data_step.py` but addressable via HTTP. T-005 documents the endpoints; key gates per `market_data_adapter_factory.py:20-55`.

### 6.2 `market_data_readiness.py` (376 lines)

Per T-005, the readiness scorecard for the market-data surface — invoked by `release_readiness.py` (T-006 §8) to determine whether `BLOCKER_MARKET_DATA_SYNC_DISABLED` should fire.

### 6.3 `market_data_runtime_routes.py` (373 lines)

Per T-005, the routes that expose `market_data_latest_snapshots` reads to the frontend. Key route: `GET /market-data/snapshots/latest/{ibkr_conid}` (T-009 §2 — `apiClient.getMarketDataLatestSnapshotStatus` at `apiClient.ts:1877`).

### 6.4 Frontend consumers (T-008)

Per T-008 `web-components-feature-grids.md` §7 (`<PortefeuilleRealtimeSection>`):

- `apiClient.getMarketDataByAccount()` (`apiClient.ts:1497`) — one of 4 endpoints polled every 30 s; reads enriched market-data status for each held position.
- T-008 `web-pages.md` §3.6 — `<VolglijstConfirmedView>` calls `apiClient.getMarketDataLatestSnapshotStatus(conid)` per row (`page.tsx:131`) to render the freshness pill in the Volglijst grid.

The frontend renders 3 freshness pills via `<PriceFreshnessBadge>` (T-008 `web-components-status-and-shared.md` §12):

- `fresh` → `"Vers"`, bg `#15803d` fg `#ffffff`.
- `stale` → `"Verouderd"`, bg `#f59e0b` fg `#1f2937`.
- `unavailable` → `"Niet beschikbaar"`, bg `#6b7280` fg `#ffffff`.

Note the frontend pill set is 3 states (`fresh / stale / unavailable`) while the storage enum is 5 states (`missing_snapshot / fresh / near_stale / stale / unusable`). The mapping is at API serialisation time — `near_stale` is rolled up to `stale` for UI purposes (the 30-minute and 15-minute distinction matters for valuation-readiness gating but not for UX).

## 7. End-to-end timelines

### 7.1 EODHD daily flow (Path A) — 07:00 morning fire

| t (s) | Tier | Action | Storage write |
|---|---|---|---|
| 0 | Worker | Orchestrator step 8 — market_data gate evaluates True (T-011 §5) | — |
| 0.05 | Worker | `fetch_market_data_for_account` called with N-asset universe + target_date | — |
| 0.1 | Worker → EODHD | `GET /eod/SXR8.XETRA?from=2026-05-25&to=2026-05-25` for each asset (concurrent, rate-limited to 10 r/s) | — |
| 0.2-N | Worker → DB | INSERT `market_data_snapshots` row per asset (idempotent skip if already present) | N rows |
| N+0.5 | Worker → EODHD | `GET /eod/USDEUR.FOREX?...` for each non-EUR currency in `needed_currencies` | — |
| N+0.8 | Worker → DB | UPSERT `fx_rate_snapshots` row per currency pair | M rows |
| N+1.0 | Worker | Returns `MarketDataFetchResult(snapshots_attempted=N, snapshots_succeeded=N, ...)` | — |
| N+1.0 | Worker | Orchestrator folds dict under audit key `"market_data"` (T-011 §10 audit assembly) | — |

For N=12 starter watchlist (T-012 §4) at ~10 r/s EODHD rate limit, total wall-clock is roughly 2-3 seconds.

### 7.2 IBKR live-quote flow (Path B) — single API request

| t (ms) | Tier | Action | Storage write |
|---|---|---|---|
| 0 | Frontend | `GET /market-data/snapshots/latest/{conid}` triggered (e.g. from Volglijst row) | — |
| ~10 | API | Route enters; calls `IbkrMarketDataAdapter.fetch_latest_snapshot(identity)` | — |
| ~20 | API | `block_if_identity_invalid(identity)` — pre-check (§4.2) | — |
| ~30 | API → IBKR | `ib.reqMktData(contract)` with `snapshotTimeoutSeconds=5` (default) | — |
| ~500-5000 | IBKR | Returns quote or timeout | — |
| ~5050 | API → DB | INSERT `market_data_latest_snapshots` row with `safe_for_*=False` | 1 row |
| ~5060 | API | Returns `MarketDataFetchResult(status=SUCCESS, snapshot=..., message_nl=...)` | — |

Wall-clock is dominated by IBKR's pacing (up to 5 seconds for delayed market data per `snapshot_timeout_seconds`).

## 8. Failure paths

Per `MarketDataFetchStatus` (§4.3) — 12 distinct outcomes:

| Status | Path | Cause | Action |
|---|---|---|---|
| `SUCCESS` | both | normal | row persisted |
| `NOT_CONFIGURED` | Path B | `IbkrMarketDataSettings.enabled=False` | adapter returns early; no row |
| `MISSING_IDENTITY` | Path B | empty `ibkr_conid` | `block_if_identity_invalid` returns Dutch error |
| `IDENTITY_NOT_VALIDATED` | Path B | identity not yet validated | same as above |
| `PROVIDER_PERMISSION_MISSING` | both | provider rejected (e.g. EODHD subscription tier doesn't include endpoint) | row not persisted; error counted |
| `PACING_LIMITED` | Path B | IBKR pacing kicks in | request blocked; client must back off |
| `NO_SNAPSHOT` | Path B | request returned no data | row not persisted |
| `PROVIDER_ERROR` | both | HTTP error / connection lost | error logged into `MarketDataFetchResult.message_nl` |
| `STORAGE_ERROR` | both | DB write failed | error counted; data is lost |
| `STALE_SNAPSHOT` | both | the latest snapshot we have is past `policy.near_stale_within` | consumer must decide whether to use it |
| `SNAPSHOT_AVAILABLE` | both | snapshot exists but not necessarily fresh | consumer decides |
| `PROVIDER_NOT_CONFIGURED` | Path A | `eodhd_api_key` missing | factory returns `None`; caller reports |

**Path A is "never raises"** at the worker step level (`market_data_step.py:13-15` per T-007 §7). Path B propagates errors back as Dutch `MarketDataFetchResult.message_nl` strings; the route handler decides whether to surface a 4xx.

## 9. Cross-cuts + Phase 1c surface

The following observations are inputs for Phase 1c gap analysis:

1. **ADR 0003 "All-In-One" gap re-confirmed** — only EOD + FX are wired; no fundamentals, splits, dividends, intraday bars (T-007 §1 originating finding; reinforced here). The EODHD subscription supports all of these but the client code calls only 2 endpoints.
2. **IBKR live-quote path is opt-in and default-off.** `ibkr_market_data_enabled=False` (`apps/api/.../config.py:96`) means most Phase 1 environments will never exercise Path B. The live-quote path exists in code but is effectively dormant until Phase 4 wires order ticket construction.
3. **Freshness pill mapping loses granularity at API serialisation.** Storage has 5 states; UI has 3. The `near_stale` → `stale` rollup means a 16-minute-old snapshot looks identical to a 6-hour-old one to the user. Phase 4 candidate: surface `near_stale` as a separate pill.
4. **The two paths share the convergence table but not the freshness model.** EODHD EOD data is 12+ hours old by definition; IBKR live quotes can be seconds old. Applying `fresh_within=15min` to an EOD row makes it "stale" immediately at fetch time. T-007 §4 has a separate 3-day staleness threshold for forecasting that effectively bypasses this. **Need a per-data-domain freshness policy** (e.g. EOD = 24h fresh; live = 15min fresh).
5. **Hard `safe_for_*=False` floor on all market-data rows.** Even fresh live IBKR quotes are flagged as "not safe for action drafts" — consumers must apply their own safety logic. This is correct by doctrine but means the flags carry no information (always False). Phase 4: either make the flags meaningful or remove them.
6. **No rate-limit coordination between worker and API EODHD clients.** Worker has its own 10 r/s rate limiter (T-007 §8); API has its own. Two parallel sync paths could exhaust the EODHD quota together. Phase 4 candidate.
7. **Migrations 0021 + 0024 + 0027 + 0048** are the market-data storage evolution chain. T-003 documents the migration ordering; T-014 documents the runtime that ended up writing to these tables.
8. **EODHD API key is read 4 places** (per T-061 §7 settings inventory): the API consumer (`market_data_adapter_factory.py:44`), the worker consumer (`providers/eodhd.py:131`), the `release_readiness.py` blocker check (`:135`), and the status route gate (`status_routes.py:3836, 3854`). T-061 already documents this; T-014 cross-references.

## 10. Out of scope

- **ADR 0003 closure** — adding fundamentals / splits / dividends / intraday endpoints to the EODHD client.
- **Order submission** (T-019 future) — even though Path B's live quotes are intended to feed order ticket construction, the actual order-submission flow lives in `apps/api/.../ibkr_ibapi_order_submission_client.py:525` (camelCase `placeOrder`) and `apps/worker/.../ibkr_submission/submitter.py:240` (snake-case `place_order`). Separate doctrine drift documented in T-007 §5.
- **Reconciliation** (T-020 future) — no reconciliation pass currently covers `market_data_*` rows. The 3 reconciliation passes (T-007 §§9-11) cover orders + executions only.
- **Per-data-feature toggles from settings intent** (T-061 §8) — fundamentals/earnings-calendar/macro/alternative toggles exist in the intent but no code wiring. The on/off gate for the whole pipeline is `market_data_sync_enabled` (single boolean, no per-feature granularity).

## 11. References

- `docs/reality/components/storage-package-and-migrations.md` — 4 market-data tables + migration chain (T-003).
- `docs/reality/components/api-forecasting-and-market-data.md` — API market-data routes + `eodhd_client.py` (T-005).
- `docs/reality/components/worker-forecasting-and-decision-package.md` §7-§8 — worker `market_data_step.py` + `providers/eodhd.py` (T-007).
- `docs/reality/components/web-components-feature-grids.md` §7 — `<PortefeuilleRealtimeSection>` consumer (T-008).
- `docs/reality/components/web-components-status-and-shared.md` §12 — `<PriceFreshnessBadge>` (T-008).
- `docs/reality/components/web-api-client-and-text.md` §2 — `apiClient.getMarketDataByAccount` + `getMarketDataLatestSnapshotStatus` (T-009).
- `docs/reality/components/settings-and-credentials-infrastructure.md` §7 — `eodhd_api_key` consumer inventory (T-061).
- `docs/reality/workflows/morning-chain-orchestration.md` §5 — primary consumer of Path A (T-011).
- `docs/reality/workflows/cold-start-seeding-and-watchlist-confirmation.md` — adjacent flow that uses the 12-asset starter watchlist as Path A's universe (T-012).
- `docs/reality/workflows/ibkr-readonly-sync-positions-cash.md` — adjacent flow; **does not touch market-data tables** (T-013).
- `docs/decisions/0003-forecast-engine-architecture.md:29` — ADR locking EODHD All-In-One requirement (intent for §1).
