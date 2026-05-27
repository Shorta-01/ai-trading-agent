# Portfolio Valuation + Cost Basis — Sync Snapshot to Dashboard

**Scope.** End-to-end trace of how the system values its portfolio — from the IBKR sync snapshot ingest, through cost-basis derivation, market value application (gated on freshness), unrealized P&L computation, FX conversion (gated on per-pair freshness + validation), to the API readiness surface (`GET /portfolio/valuation/readiness`) and the frontend `<PortefeuilleRealtimeSection>` 30-second polling component.

**Intent**: `docs/intent/portfolio-valuation.md` (locked 2026-05-26). **Decision**: `docs/decisions/0011-portfolio-valuation-architecture.md`. **Component reality**: T-002 `docs/reality/components/portfolio-money-and-accounting.md`, T-005 `docs/reality/components/api-actions-suggestions-and-watchlists.md`. **Sibling workflow**: T-013 `docs/reality/workflows/ibkr-readonly-sync-positions-cash.md` (produces the snapshot rows this flow consumes).

## 0. TL;DR

| Step | Site | Outcome |
|------|------|---------|
| Sync snapshot ingested | `ibkr_position_snapshots` table | One row per `(sync_run_id, conid, symbol)` with `quantity` + aggregate `average_cost` |
| Latest sync resolved | `status_routes.py:577` | `read_latest_ibkr_sync_run(settings.storage)` |
| Market data joined by conid | `status_routes.py:605` | `market_repo.list_latest_market_data_snapshots_by_conids(conids)` |
| FX pairs derived from currencies | `status_routes.py:613-619` | `f"{currency}/{base_currency}"` for every non-base position currency |
| Per-position row built | `portfolio_valuation_readiness.py:212-377` | `build_position_row(...)` |
| Cost basis derived | `valuation_cost_basis_pl.py:152` | `cost_basis = quantity × average_cost_per_unit` |
| Unrealized P&L derived | `valuation_cost_basis_pl.py:163` | `unrealized_pl = native_market_value - cost_basis` |
| Conversion totals | `valuation_conversion_totals.py:120-201` | `calculate_conversion_totals(...)` — per-pair gates |
| Response built | `portfolio_valuation_readiness.py:471` | `build_portfolio_valuation_readiness(...)` returns `PortfolioValuationReadinessResponse` |
| Frontend polls | `PortefeuilleRealtimeSection.tsx:32, :99` | `POLL_INTERVAL_MS = 30_000`; Decimal-as-string verbatim |

**Three blocking failure modes** (the `PortfolioValuationStatus` StrEnum at `portfolio_valuation_readiness.py:29-34`): `storage_unavailable | no_latest_ibkr_snapshot | no_positions | missing_market_data | calculation_available`.

## 1. Storage shape — intent vs reality

### 1.1 Intent (locked, `docs/intent/portfolio-valuation.md` §1)

> "Always store individual lots. Lot granularity is the lowest unit of holding; aggregation is a reporting choice on top of lots.
> Each lot carries: `acquisition_date`, `quantity`, `unit_cost_local`, `unit_cost_eur`, `fx_rate_at_acquisition`, `lot_id`.
> Lots never merge in storage."

### 1.2 Reality — aggregate only

The only persisted "position" table is `ibkr_position_snapshots` (`packages/storage/src/ai_trading_agent_storage/metadata.py:2170-2191`):

- **Primary key**: `snapshot_id` (Text).
- **Composite identity**: `(sync_run_id, account_ref, conid, symbol)`.
- **Columns**: `quantity` (MONEY_NUMERIC), `average_cost` (MONEY_NUMERIC), `currency`, `received_at`, `stored_at`.
- **Migration**: `packages/storage/alembic/versions/0025_ibkr_sync_snapshot_storage.py`.

**There is no `acquisition_date`, no `unit_cost_local` vs `unit_cost_eur` split, no `fx_rate_at_acquisition`, no `lot_id`.** IBKR returns one `(conid, quantity, average_cost)` triple per holding; the storage layer persists it as-is. The system stores the **same aggregate the broker returns**.

### 1.3 The orphaned `PaperLot` domain model

`packages/domain/src/portfolio_outlook_domain/lots.py:11-58` defines `PaperLot` with the full intent-§1 field set:

```python
class PaperLot(DomainBaseModel):
    lot_id: LotId
    portfolio_id: PortfolioId
    instrument_id: InstrumentId
    buy_transaction_id: TransactionId
    buy_date: date
    original_quantity: Quantity
    remaining_quantity: Quantity
    buy_price: Money
    buy_currency: CurrencyCode
    fees_allocated: Money | None = None
    cost_basis: Money
    status: LotStatus
```

`FifoLotAllocation` (`packages/domain/src/portfolio_outlook_domain/lots.py:60-72`) defines the FIFO disposal allocation record.

**Neither model has a storage adapter.** Grep across `packages/storage/src/ai_trading_agent_storage/sql_repositories.py` returns zero matches for `save_lot`, `get_lot`, `list_lots_for_portfolio`, or any `PaperLot`-related method. The only consumer is `packages/portfolio/src/portfolio_outlook_portfolio/lots.py:1-46` — 46 LOC of pure helpers (`calculate_remaining_quantity`, `derive_lot_status`, `validate_lot_quantities`, `calculate_allocated_cost_basis`) that operate on in-memory `PaperLot` instances but have no I/O path. Phase 1c gap §10.1.

## 2. The trigger — readiness endpoint, not a sweep

Portfolio valuation has **no scheduler tick**. It is computed on demand each time the API endpoint `GET /portfolio/valuation/readiness` is called. The frontend `<PortefeuilleRealtimeSection>` polls every 30s (§6.1), which effectively turns the endpoint into a polling-driven materialised view.

### 2.1 The 3 readiness API routes

`apps/api/src/portfolio_outlook_api/status_routes.py`:

| Route | Line | Purpose |
|-------|------|---------|
| `GET /portfolio/valuation/readiness` | `status_routes.py:572-628` | Per-position + portfolio-total valuation readiness |
| `GET /portfolio/valuation/reconciliation-readiness` | `status_routes.py:631` | Wraps the readiness response with an additional reconciliation gate |
| `GET /ibkr/portfolio/positions` | `status_routes.py:480` | Raw position snapshot (no derived cost-basis / P&L) |

The reconciliation readiness route (`:631`) reads the same valuation payload and overlays the latest reconciliation-run status (see T-020 §6.1).

## 3. The fetch sequence (`status_routes.py:572-628`)

The route handler `read_portfolio_valuation_readiness` (`:576`) executes the following in a single `checked_connection(require_writable=False)` block:

```text
durable = read_latest_ibkr_sync_run(settings.storage)         # :577 — latest sync_run pointer
if durable.storage_help_nl is not None:                       # :578 — storage error short-circuit
    return build_..._readiness(storage_available=False)
if durable.latest_run is None:                                # :587 — no sync yet
    return build_..._readiness(latest_run=None, ...)

with provider.checked_connection(require_writable=False):     # :599
    positions = repo.list_ibkr_position_snapshots(sync_run_id)        # :602
    cash_snapshots = repo.list_ibkr_account_cash_snapshots(sync_run_id) # :603
    conids = tuple(item.conid for item in positions if item.conid)   # :604
    market_result = market_repo.list_latest_market_data_snapshots_by_conids(conids)  # :605
    market_by_conid = {item.ibkr_conid: item for item in market_result.records}      # :606
    cash_currencies = sorted({item.base_currency for item in cash_snapshots})        # :607
    position_currencies = sorted({...})                                              # :608-610
    valuation_currencies = sorted(set(cash_currencies) | set(position_currencies))   # :611
    base_currency = cash_currencies[0] if len(cash_currencies) == 1 else None        # :612
    required_pairs = (f"{c}/{base_currency}" for c in valuation_currencies if c != base_currency)  # :614-619
    fx_snapshots = repo.list_latest_fx_rate_snapshots_by_pairs(required_pairs)       # :620
return build_portfolio_valuation_readiness(...)               # :621-628
```

### 3.1 Multi-currency cash heuristic — Phase 1c finding

`base_currency = cash_currencies[0] if len(cash_currencies) == 1 else None` (`:612`). If the account holds cash in two currencies (e.g., EUR + USD), the route sets `base_currency=None`, which forces the FX conversion to fail with `conversion_blocked_missing_base_currency`. This is a heuristic, not a setting — the user cannot pin "EUR is my base currency" through any persistent setting. See §10.10.

A more permissive heuristic exists in the builder itself at `portfolio_valuation_readiness.py:544-545`: `elif "USD" in cash_currencies: base_currency = "USD"`. This is asymmetric — USD gets a fallback; EUR does not. (And EUR is the default base per intent §5: "default EUR; configurable in Category 2".)

## 4. Per-position row build (`portfolio_valuation_readiness.py:212-377`)

`build_position_row(PositionRowBuildInput) -> PositionValuationReadinessRow` is the central per-row builder. The 165-LoC function does two passes — one for the no-market-data path, one for the with-market-data path.

### 4.1 First pass — cost basis only (`:213-284`)

Even with no market snapshot, cost basis can sometimes be computed (when `quantity` and `average_cost` are both present from the IBKR snapshot). The first pass calls `calculate_position_cost_basis_and_unrealized_pl(...)` with `native_market_value=None` (`:236-247`) and writes the cost-basis result into the row. If the cost basis is available, the row carries it even though unrealized P&L is blocked with `pl_blocked_missing_market_data` (per `:80-83` status text).

### 4.2 Market snapshot freshness gate (`:285-296`)

```python
snapshot = payload.market_snapshot
if snapshot is None or snapshot.last_price is None:           # :286
    return row                                                  # cost-basis-only row
if snapshot.freshness_status == "stale":                       # :288 — STALE BLOCKS VALUATION
    row.reason_code = "stale_market_data"
    row.status_nl = "Controle nodig"
    row.help_nl = "Prijs is verouderd en kan niet veilig gebruikt worden."
    row.last_market_snapshot_id = snapshot.snapshot_id
    row.market_price = _money(snapshot.last_price)
    return row
```

**Stale market data is treated as missing**, not as data with a stale warning. The row keeps the `market_price` (so the UI can show it) but the `market_value` and `unrealized_pl` fields stay `None`. This is the doctrine §6 freshness gate applied to valuation (T-014 §4 documents the upstream freshness classifier).

### 4.3 Market value derivation (`:297`)

```python
market_value = quantity * snapshot.last_price
```

`market_value` is in the **position's local currency** (USD for a US stock, EUR for a European stock, etc.). Conversion to base currency happens later in `calculate_conversion_totals` (§5).

### 4.4 Cost-basis + unrealized P&L derivation (`valuation_cost_basis_pl.py:95-201`)

`calculate_position_cost_basis_and_unrealized_pl(PositionPlCalculationInput) -> PositionPlCalculationResult` is the central per-position formula module:

| Branch | Line | Outcome |
|--------|------|---------|
| `source_currency is None` | `:102-111` | `cost_basis_missing` / `pl_blocked_incomplete_inputs` |
| `quantity is None` | `:113-122` | `cost_basis_missing` / `pl_blocked_incomplete_inputs` |
| `quantity < 0` | `:124-131` | `cost_basis_blocked_short_position` / `pl_blocked_incomplete_inputs` |
| `quantity == 0` | `:133-140` | `cost_basis_blocked_invalid_quantity` / `pl_blocked_incomplete_inputs` |
| `average_cost_per_unit is None` | `:142-150` | `cost_basis_missing` / `pl_blocked_missing_cost_basis` |
| `cost_basis = quantity × average_cost_per_unit` | `:152` | computed |
| `native_market_value is None` | `:154-161` | `cost_basis_ready` / `pl_blocked_missing_market_data` |
| `unrealized_pl = native_market_value - cost_basis` | `:163` | computed |
| `cost_basis > 0`: `pl_percent = unrealized_pl / cost_basis` | `:167-169` | computed; gated on positive cost basis |
| `converted_*` (base-currency conversion) | `:171-175` | applied if `payload.converted_market_value` AND `payload.converted_cost_basis` set |

### 4.5 The 8 status strings (`valuation_cost_basis_pl.py:58-88`)

Cost-basis statuses: `cost_basis_ready | cost_basis_missing | cost_basis_blocked_invalid_quantity | cost_basis_blocked_short_position`.

Unrealized P&L statuses: `pl_ready | pl_blocked_missing_cost_basis | pl_blocked_missing_market_data | pl_blocked_incomplete_inputs`.

Each maps to a Dutch `status_nl` + `help_nl` (lines `:58-88`) for direct UI consumption.

### 4.6 Trace records — the audit chain

Every derived row carries:
- `cost_basis_input_trace` — `PositionPlInputTrace` (`valuation_cost_basis_pl.py:17-22`) with `latest_sync_run_id`, `position_trace_ids`, `market_snapshot_ids`, `fx_snapshot_ids`.
- `unrealized_pl_input_trace` — same shape; redundantly recorded so the UI can attribute each derived value to its source rows.
- `missing_cost_basis_inputs: list[str]` — empty when ready; populated with field names when blocked.
- `missing_pl_inputs: list[str]` — same.

The trace is rendered by `<PositionPlTraceDetails>` (`apps/web/components/PositionPlTraceDetails.tsx:80`) as a per-row "show your work" expansion — see §6.

## 5. Portfolio totals + FX conversion (`valuation_conversion_totals.py:120-201`)

`calculate_conversion_totals(ConversionTotalsInput) -> ConversionTotalsResult` is invoked once per readiness call (after every position row has been built).

### 5.1 Required-pair derivation (`:174`)

```python
required_pairs = _required_pairs(positions, cash_values, base_currency)
```

The helper builds `f"{source_currency}/{base_currency}"` for every position currency + cash currency that isn't already the base. (Same shape as the route-level pre-fetch at `status_routes.py:614-619`.)

### 5.2 Per-pair gates (`:179-191`)

```python
for pair in required_pairs:
    fx = fx_by_pair.get(pair)
    if fx is None:
        missing_fx_pairs.append(pair)                    # :182 — pair entirely missing
        continue
    if fx.validation_status != "valid":                  # :184 — invalid pair
        invalid_fx_pairs.append(pair)
        continue
    if fx.freshness_status != "fresh":                   # :187 — non-fresh
        if fx.freshness_status == "stale":
            stale_fx_pairs.append(pair)                  # :189 — stale (yellow)
        else:
            invalid_fx_pairs.append(pair)                # :191 — anything else (red)
```

The gates are 3-tier: **invalid** (red, block) → **stale** (yellow, "Controle nodig") → **fresh** (green, proceed). The result carries `missing_fx_pairs`, `stale_fx_pairs`, `invalid_fx_pairs` so the UI can show exactly which pairs are blocking the totals.

### 5.3 Status strings (`:76-113`)

9 statuses: `conversion_not_required | conversion_ready | conversion_blocked_missing_base_currency | conversion_blocked_missing_market_data | conversion_blocked_missing_cash | conversion_blocked_missing_fx | conversion_control_needed_stale_fx | conversion_blocked_invalid_fx | conversion_blocked_incomplete_inputs`. Each maps to a Dutch `status_nl` + `help_nl`.

### 5.4 Total-value outputs

The result carries three booleans + three Decimals:

- `total_market_value_available` + `total_market_value` (sum of converted position values).
- `total_cash_value_available` + `total_cash_value` (sum of converted cash values).
- `total_portfolio_value_available` + `total_portfolio_value` (the two above, summed in base currency).

Plus the per-currency lists so the UI can show partial totals when some pairs block.

## 6. The frontend valuation surface (`apps/web/components/`)

### 6.1 `<PortefeuilleRealtimeSection>` (`PortefeuilleRealtimeSection.tsx:1-...`)

The dashboard's portfolio area. Documented states (`:5-13`):

1. **Disconnected** — full-width Dutch banner; grid hidden.
2. **Connected, empty** — cash card visible; positions table shows empty-state message.
3. **Connected, populated** — cash card + positions grid render the latest persisted snapshot.

Polling: `POLL_INTERVAL_MS = 30_000` (`:32`). The component fetches **4 endpoints in parallel** every 30s (`:80-86`):

- `apiClient.getIbkrConnectionStatus()` — `GET /ibkr/session/status`
- `apiClient.getIbkrSyncPositionsLatest()` — `GET /ibkr/sync/positions/latest`
- `apiClient.getIbkrSyncCashLatest()` — `GET /ibkr/sync/cash/latest`
- `apiClient.getMarketDataByAccount()` — `GET /market-data/by-account`

**NOTE**: `<PortefeuilleRealtimeSection>` does NOT call `GET /portfolio/valuation/readiness` itself. That endpoint is used by other surfaces (the trace-details viewers below). The dashboard panel re-derives display from the raw snapshot + market data feeds, not from the readiness response. See §10.7.

### 6.2 Decimal-as-string verbatim discipline (`:14-18, :36-39`)

> "Decimal precision is preserved end-to-end — every numeric arrives as a string from the API and is rendered verbatim. Empty values surface as 'Niet beschikbaar'."

The `formatNumber` helper (`:36-39`):

```typescript
function formatNumber(value: string | null): string {
  if (value === null || value.trim() === "") return NIET_BESCHIKBAAR;
  return value;
}
```

No `parseFloat`, no `Number(...)`, no rounding. Decimal-as-string discipline from the storage layer (`MONEY_NUMERIC` column) → API (string serialisation) → frontend (verbatim render). Matches the doctrine boundary documented in T-008.

### 6.3 `<ValuationTraceDetails>` (`ValuationTraceDetails.tsx:6, :37-57`)

Renders the `valuation_input_trace` block from the readiness response — `latest_sync_run_id`, `position_trace_ids`, `cash_trace_ids`, `market_snapshot_ids`, `cash_snapshot_ids`, `fx_snapshot_ids`. The `hasBlockers` check (`:37`) decides whether to show the blocking-reason panel. This is the admin-side "show your work" surface for the totals computation.

### 6.4 `<PositionPlTraceDetails>` (`PositionPlTraceDetails.tsx:6, :80`)

The per-row counterpart of §6.3. Renders the per-position `cost_basis_input_trace` + `unrealized_pl_input_trace` — useful when a single position is blocked while others compute cleanly.

## 7. End-to-end timeline — one valuation call

| t | Site | Event |
|---|------|-------|
| 0 | `<PortefeuilleRealtimeSection>` poll tick | 30s `setInterval` fires |
| 0 | `apiClient` | 4 GETs fired in parallel (positions, cash, market data, connection status) |
| 0 | API | `GET /ibkr/sync/positions/latest` etc. — raw rows returned |
| 0 | API (some surface, e.g., admin trace) | `GET /portfolio/valuation/readiness` invoked |
| 0+ε | `status_routes.py:577` | `read_latest_ibkr_sync_run` resolves the latest sync_run pointer |
| 0+ε | `:602-606` | positions, cash, market data joined by `(sync_run_id, conid)` |
| 0+ε | `:607-620` | base-currency heuristic + required-pair derivation + FX snapshot read |
| 0+ε | `portfolio_valuation_readiness.py:471` | `build_portfolio_valuation_readiness` invoked |
| 0+ε | `:212` × N positions | `build_position_row` per position — calls `calculate_position_cost_basis_and_unrealized_pl` |
| 0+ε | `valuation_cost_basis_pl.py:152` | `cost_basis = quantity × average_cost_per_unit` |
| 0+ε | `valuation_cost_basis_pl.py:163` | `unrealized_pl = market_value - cost_basis` (when fresh market data) |
| 0+ε | `valuation_conversion_totals.py:120` | `calculate_conversion_totals` — per-pair gates |
| 0+ε | response | `PortfolioValuationReadinessResponse` returned |
| 30 | `<PortefeuilleRealtimeSection>` | next poll tick |

The path is **synchronous + recomputed-each-call**. No caching layer; no materialised view; no background sweep. Each `GET /portfolio/valuation/readiness` re-reads the same 4 storage tables and re-derives all numbers.

## 8. Failure paths

1. **Storage unreachable** → `storage_unavailable` (`portfolio_valuation_readiness.py:480-508`). Cash, FX, positions all reported as unavailable.
2. **No sync ever run** → `no_latest_ibkr_snapshot` (`:509-537`). `latest_sync_completed_at=None`.
3. **Sync exists, no positions** → `no_positions` (`:538-585`). Cash + FX still reported normally.
4. **All positions blocked on market data** → per-row `market_data_status="missing_market_data"`; totals carry `missing_market_data_conids`.
5. **Multi-currency cash + no `USD` fallback** → `base_currency=None`; totals blocked with `conversion_blocked_missing_base_currency`.
6. **Stale FX pair** → per-pair `stale_fx_pairs` populated; totals carry `conversion_control_needed_stale_fx`.
7. **Invalid FX validation_status** → per-pair `invalid_fx_pairs` populated; totals blocked with `conversion_blocked_invalid_fx`.
8. **Short position (quantity < 0)** → per-row `cost_basis_blocked_short_position` (intent does not explicitly forbid shorts but the calc gates them out; see §10.6).
9. **`quantity == 0`** → per-row `cost_basis_blocked_invalid_quantity` (residual zero-quantity rows from IBKR are not silently dropped — they are surfaced as blocked).

## 9. The valuation-by-purpose intent (locked) vs reality

Intent §4 specifies a 7-row valuation-by-purpose table. Reality coverage:

| Use case | Intent price source | Reality price source | Match? |
|----------|---------------------|----------------------|--------|
| Dashboard portfolio area | Last close | `snapshot.last_price` (latest, not closed) | **No** — uses latest available, not specifically last-close |
| Decision package sizing context | **Live mid-price (IBKR on-demand)** | Snapshot (composer uses ingested data) | **No** — no live-mid fetch in worker (`composer.py:91-100`) |
| Performance review screen | Last close | (screen does not exist — see §10.5) | **N/A** |
| Exposure calculations | Last close | (exposure dimension not computed — see §10.4) | **N/A** |
| Belgian tax period valuation | Last close | (handled outside this flow — T-022 scope) | **Deferred** |
| Belgian tax disposal events | **Actual execution price + exec-time FX** | (execution price recorded in `ibkr_executions`; exec-time FX NOT recorded) | **Partial** — see §10.8 |
| Audit log entries | "Whichever was used; captured explicitly" | Trace records (§4.6) capture snapshot IDs but not the price-purpose | **Partial** — trace identifies snapshot, not its semantic purpose |

The trace surface (§4.6) captures *which snapshot ID* was used, but not *whether that snapshot represented "last close" vs "live mid" vs "intraday latest"* — `MarketDataLatestSnapshotRecord` only has `last_price` + `provider_as_of`, not a price-purpose discriminator.

## 10. Phase 1c surface (10 findings)

1. **Per-lot storage missing** (§1) — intent §1 mandates per-lot rows with `lot_id`, `acquisition_date`, `unit_cost_local/eur`, `fx_rate_at_acquisition`. Reality stores aggregate `average_cost` only. Largest intent-vs-reality drift in the valuation surface.
2. **`PaperLot` + `FifoLotAllocation` unpersisted** (§1.3) — domain models exist; no storage adapter; 0 production callers. The pure-helper module `packages/portfolio/.../lots.py` (46 LOC) is orphaned.
3. **No FIFO depletion on disposal** — intent §1 requires lots be depleted per the active tax method on disposal. No lifecycle handler invokes the depletion logic. The worker `lifecycle_handler.py` (T-019 §6) writes `ibkr_executions` rows but does not touch a `position_lots` table (which doesn't exist).
4. **Display method setting unimplemented** — intent §2 says "Default: weighted average cost. Configurable in Category 2"; with alternatives FIFO and Specific Lot ID. No setting field exists in `settings.py`; no `cost_basis_method` enum; no audit-log field for changes. Re-confirmed via T-061 settings inventory.
5. **No performance review screen** — intent §5 + doctrine §11 mandate a separate performance-review screen with currency-exposure dimension. No frontend page or component matches. Queue T-021b is locked but not started.
6. **Currency exposure not first-class** — intent §5 + doctrine §11 require currency exposure to be tracked as a first-class dimension. Reality: the readiness response groups positions by currency (`cash_currencies`, `position_currencies`) but does not compute per-currency totals, exposure %, or sector breakdown.
7. **Dashboard does not consume `/portfolio/valuation/readiness`** (§6.1) — the `<PortefeuilleRealtimeSection>` re-derives display from raw snapshot + market data, bypassing the central calculation module. The readiness endpoint is consumed only by trace-detail viewers and the reconciliation-readiness wrapper. **Two parallel display paths for the same data.**
8. **Belgian tax disposal price not recorded with execution-time FX** (§9 row 6) — intent §4 requires "Actual execution price + Actual execution-time FX rate" captured at disposal. `ibkr_executions` records `fill_price_local` + `fill_time` but **no `fx_rate_at_fill`** — the execution-time FX is never stored. T-022 will need this when computing realised gains in EUR.
9. **No live mid-price for sizing context** (§9 row 2) — intent §4 mandates "Live mid-price (IBKR on-demand)" for decision package sizing. The action draft composer (`apps/worker/.../composer.py:91-100`) uses the snapshot data, not a live `reqMktData` call. T-017 §4 already flagged this; re-confirmed for T-021.
10. **Multi-currency base-currency heuristic is asymmetric** (§3.1) — `cash_currencies[0] if len(cash_currencies) == 1 else None` with a fallback only for `USD` (`portfolio_valuation_readiness.py:544-545`). No EUR fallback; no persistent "my base currency" setting; user with EUR + USD cash gets `base_currency=None` and totals blocked. Intent §5 says "default EUR; configurable in Category 2" — neither path exists.

## 11. Out of scope (re-confirmed)

- **Belgian tax computation** (T-022 future) — picks up at disposal: realised P&L in EUR, TOB, dividend withholding. T-021 finding §10.8 (no exec-time FX recorded) directly impacts T-022.
- **AI explanation** (T-023 future).
- **Predictor backtest + leaderboard** (T-024 future).
- **Reconciliation passes A/B/C** (T-020 — merged sibling; corporate-action drift surfaces via D-class per intent, but per T-020 §10.3 the 4-tier classification is absent from code).
- **Performance review screen** (queue T-021b future; T-021 finding §10.5 documents the absence).

## 12. References

- `apps/api/src/portfolio_outlook_api/status_routes.py:480, :572-628, :631` (3 routes)
- `apps/api/src/portfolio_outlook_api/portfolio_valuation_readiness.py:1-916` (response models + builder)
- `packages/portfolio/src/portfolio_outlook_portfolio/valuation_cost_basis_pl.py:1-266`
- `packages/portfolio/src/portfolio_outlook_portfolio/valuation_conversion_totals.py:1-350`
- `packages/portfolio/src/portfolio_outlook_portfolio/lots.py:1-46` (orphaned helpers)
- `packages/domain/src/portfolio_outlook_domain/lots.py:1-72` (`PaperLot` + `FifoLotAllocation`)
- `packages/domain/src/portfolio_outlook_domain/portfolio.py:1-39` (`PositionSnapshot`)
- `packages/storage/src/ai_trading_agent_storage/metadata.py:2170-2191` (`ibkr_position_snapshots`), `:1280-1310` (`fx_rate_snapshots`), `:1370-1410` (`market_data_latest_snapshots`)
- `packages/storage/alembic/versions/0025_ibkr_sync_snapshot_storage.py`
- `packages/storage/alembic/versions/0026_fx_rate_snapshot_storage.py`
- `apps/web/components/PortefeuilleRealtimeSection.tsx:1-...` (30s polling component)
- `apps/web/components/ValuationTraceDetails.tsx:1-...` (totals trace renderer)
- `apps/web/components/PositionPlTraceDetails.tsx:1-...` (per-row trace renderer)
- `apps/web/lib/apiClient.ts:1439, :1440, :1477` (TS bindings: `getPortfolioValuationReadiness`, `getIbkrPositions`, `getIbkrSyncPositionsLatest`)
- `docs/intent/portfolio-valuation.md` (locked 2026-05-26)
- `docs/decisions/0011-portfolio-valuation-architecture.md`
- `docs/reality/components/portfolio-money-and-accounting.md` (T-002)
- `docs/reality/components/api-actions-suggestions-and-watchlists.md` (T-005)
- `docs/reality/workflows/ibkr-readonly-sync-positions-cash.md` (T-013 — sibling that produces the snapshot rows this flow consumes)
- `docs/reality/workflows/market-data-pipeline.md` (T-014 — sibling that produces the `market_data_latest_snapshots` + freshness classifier)
