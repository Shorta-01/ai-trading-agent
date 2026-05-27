```yaml
id: T-021
title: Write reality doc for portfolio valuation and cost basis
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/portfolio-valuation.md
decision_ref: docs/decisions/0011-portfolio-valuation-architecture.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/466
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/portfolio-valuation-and-cost-basis.md` does not exist (verified). Pure synthesis — every code site is cited in T-002 + T-005 reality docs or inspected here:
  - T-002 `portfolio-money-and-accounting.md` — `valuation_cost_basis_pl.py`, `valuation_conversion_totals.py`, `lots.py` (helpers).
  - T-005 `api-actions-suggestions-and-watchlists.md` — `portfolio_valuation_readiness.py` builder.
  - `apps/api/src/portfolio_outlook_api/status_routes.py:572-628` — `GET /portfolio/valuation/readiness` route + sibling `GET /portfolio/valuation/reconciliation-readiness:631` + `GET /ibkr/portfolio/positions:480`.
  - `packages/domain/src/portfolio_outlook_domain/lots.py:11-72` — `PaperLot` + `FifoLotAllocation` (intent-only, no storage adapter).
  - `packages/storage/src/ai_trading_agent_storage/metadata.py` — `ibkr_position_snapshots` table (aggregate, not per-lot), `market_data_latest_snapshots`, `fx_rate_snapshots`.
  - `apps/web/components/PortefeuilleRealtimeSection.tsx` + `ValuationTraceDetails.tsx` + `PositionPlTraceDetails.tsx` (frontend valuation surfaces).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the end-to-end portfolio valuation + cost-basis workflow doc.
  - `portfolio-valuation-and-cost-basis.md` — sync run produces `ibkr_position_snapshots` (aggregate w/ `average_cost`) → `market_data_latest_snapshots` provides last price (with freshness gate) → `fx_rate_snapshots` provides per-pair FX (with freshness + validation gates) → `calculate_position_cost_basis_and_unrealized_pl` derives cost basis + unrealized P&L → `calculate_conversion_totals` converts to base currency → API `GET /portfolio/valuation/readiness` exposes the trace → frontend `<PortefeuilleRealtimeSection>` polls 30s and renders Decimal-as-string verbatim.
- **Step 3 (one-line change):** write one cited workflow reality doc tracing portfolio valuation end-to-end from IBKR sync ingest → per-position row → portfolio totals.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; storage shape documented (aggregate vs intent's per-lot); cost-basis derivation cited (`quantity × average_cost_per_unit`); market value + freshness gate cited; unrealized P&L derivation cited; FX conversion + per-pair freshness/validation gates cited; API surface (3 routes) cited; frontend polling cadence + Decimal-as-string discipline cited; 10 intent-vs-reality gaps surfaced (per-lot storage missing, `PaperLot` unpersisted, FIFO not wired, display-method setting unimplemented, live-mid for sizing absent, performance-review screen absent, currency exposure not first-class, belgian-tax disposal price not recorded, corporate actions not handled, multi-currency cash base-currency heuristic); no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — belgian tax computation (T-022), AI explanation (T-023), predictor backtest (T-024), reconciliation passes (T-020 — already merged sibling).

## Goal

Produce one workflow reality doc tracing portfolio valuation + cost-basis end-to-end — from IBKR sync ingest (`ibkr_position_snapshots`) through cost-basis derivation (`quantity × average_cost_per_unit`), market value application (gated on `freshness_status="fresh"`), unrealized P&L computation, FX conversion (gated on `validation_status="valid"` + `freshness_status="fresh"`), to API `GET /portfolio/valuation/readiness` and the frontend `<PortefeuilleRealtimeSection>` 30-second polling surface. The doc must surface the large architectural drift between intent §1 (per-lot storage with `lot_id`, `acquisition_date`, `unit_cost_local/eur`, `fx_rate_at_acquisition`) and the as-shipped aggregate `average_cost`-only storage, plus the orphaned `PaperLot` + `FifoLotAllocation` domain types that have no persistence path.

## Context

`depends_on:` T-002 (portfolio package modules), T-005 (API routes). T-002 covered the calculation modules at module level; T-005 covered the API readiness builder. T-021 stitches them into the end-to-end "from `ibkr_position_snapshots` row to a Dutch-rendered `<PortefeuilleRealtimeSection>`" story and exposes the intent-vs-reality drift.

## Touch scope

Create:
- `docs/reality/workflows/portfolio-valuation-and-cost-basis.md`

Read: T-002 + T-005 reality docs + intent doc + valuation modules + API routes + frontend components.

## Acceptance criteria

- [ ] Output file exists at the locked filename.
- [ ] Storage shape documented — `ibkr_position_snapshots` aggregate per-conid PK + `average_cost` only (vs intent's per-lot mandate); migration anchor cited.
- [ ] Cost-basis derivation documented (`valuation_cost_basis_pl.py:152` `cost_basis = quantity × average_cost_per_unit`); the 8 status enum values cited.
- [ ] Market value derivation + freshness gate documented (`portfolio_valuation_readiness.py:288-296` stale short-circuit; `:297` market_value = `quantity × snapshot.last_price`).
- [ ] Unrealized P&L derivation documented (`valuation_cost_basis_pl.py:163` `unrealized_pl = native_market_value - cost_basis`; `:168` percent gated on `cost_basis > 0`).
- [ ] FX conversion documented (`valuation_conversion_totals.py:179-191` per-pair freshness + validation gates; required-pair derivation via base-currency heuristic).
- [ ] API surface (3 routes: `GET /portfolio/valuation/readiness`, `GET /portfolio/valuation/reconciliation-readiness`, `GET /ibkr/portfolio/positions`) cited with file:line.
- [ ] Frontend polling cadence (30s) + Decimal-as-string verbatim discipline cited (`PortefeuilleRealtimeSection.tsx:32, :36-39`).
- [ ] 10 intent-vs-reality gaps surfaced.
- [ ] No source modification.

## Out of scope

- Belgian tax computation (T-022 future — disposal price + execution-time FX recording).
- AI explanation (T-023 future).
- Predictor backtest + leaderboard (T-024 future).
- IBKR reconciliation passes (T-020 — already merged sibling; corporate-action drift surfaces via D-class in reconciliation, but no D-class tier exists in code per T-020).
- Performance review screen (queue T-021b future — only doctrine-level intent today).

## Verification

- File exists.
- `ibkr_position_snapshots` PK + columns cited (`metadata.py:2170-2191`); confirms aggregate-only shape.
- `PaperLot` + `FifoLotAllocation` cited as unpersisted (`packages/domain/.../lots.py:11-72`); grep proof no `save_lot()` / `get_lot()` repository methods exist.
- Cost-basis line cited (`valuation_cost_basis_pl.py:152`).
- Market value freshness gate cited (`portfolio_valuation_readiness.py:288-296`).
- FX gate cited (`valuation_conversion_totals.py:179-191`).
- 3 API routes cited with file:line.
- Frontend polling interval cited (`PortefeuilleRealtimeSection.tsx:32`).

## Notes

T-021 surfaces the most architecturally significant intent-vs-reality gap in the valuation surface: per-lot storage is mandated by intent §1 ("Always store individual lots") but the storage layer ships only the aggregate `ibkr_position_snapshots` view from IBKR. The `PaperLot` + `FifoLotAllocation` domain types are designed for this but have no persistence path — they are referenced only by tests + the portfolio `lots.py` pure helpers (46 LOC). Phase 1c will likely recommend either (a) wiring `PaperLot` persistence into a new `position_lots` table or (b) deferring per-lot tracking to a later phase and amending intent. T-021 documents the gap without proposing a fix.
