```yaml
id: T-014
title: Write reality doc for market-data pipeline (research + execution)
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/market-data-pipeline.md` does not exist (verified). T-014 spans both market-data paths; cross-referenced reality docs cite most code, plus three new files read inline:
  - `apps/api/src/portfolio_outlook_api/ibkr_market_data.py` (113 lines, read in full) — `IbkrMarketDataAdapter.fetch_latest_snapshot` for execution-side live quotes.
  - `apps/api/src/portfolio_outlook_api/market_data_adapter_factory.py` (55 lines, read in full) — factory gates: `market_data_sync_enabled AND market_data_provider=="eodhd" AND eodhd_enabled AND eodhd_api_key`.
  - `packages/domain/src/portfolio_outlook_domain/market_data_foundation.py` (166 lines, read in full) — `MarketDataReadinessPolicy(fresh_within=15min, near_stale_within=30min)`, `MarketDataFreshnessStatus` 5-state enum, `evaluate_market_data_readiness` decision logic with price-basis fallback (`last → midpoint → unavailable`).
  - T-007 `worker-forecasting-and-decision-package.md` §7-§8 (worker EODHD step + provider) — already cited.
  - T-005 `api-forecasting-and-market-data.md` (api market-data routes) — already cited.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the end-to-end market-data pipeline workflow doc covering both paths.
  - `market-data-pipeline.md` — two paths (research EODHD via worker + execution IBKR via API), the convergence point at `market_data_latest_snapshots`, the locked freshness policy + 5-state status enum, the price-basis fallback, the hard `safe_for_*=False` floor.
- **Step 3 (one-line change):** write one cited workflow doc tracing both market-data paths end-to-end with cross-references to T-003/T-005/T-007.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; both EODHD research path + IBKR execution path documented; freshness policy + 5-state status enum cited with `market_data_foundation.py` anchors; 4 storage tables enumerated; `market_data_latest_snapshots` as convergence point; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — no proposals for ADR-0003 "All-In-One" gap closure; no fundamentals/splits/dividends implementation; no order-submission flow.

## Goal

Produce one workflow reality doc tracing both market-data paths end-to-end:
1. **Research path** — EODHD EOD bars + FX rates → worker `market_data_step.py` → `market_data_snapshots` + `fx_rate_snapshots` (powers forecasting + portfolio valuation).
2. **Execution path** — IBKR live quotes → API `IbkrMarketDataAdapter` → `market_data_latest_snapshots` (powers order ticket construction).

Plus the convergence point at `market_data_latest_snapshots` and the locked freshness policy.

## Context

`depends_on:` T-003, T-005, T-007. The pipeline has **two distinct paths with different freshness models** — EODHD provides T-1 EOD data (research/forecasting) while IBKR provides intraday live quotes (execution). Both write to overlapping storage tables; the locked freshness policy at `market_data_foundation.py:103-106` (fresh=15min, near_stale=30min) is the single arbiter.

## Touch scope

Create:
- `docs/reality/workflows/market-data-pipeline.md`

Read: T-003 + T-005 + T-007 reality docs + the 3 files inventoried in step 1.

## Acceptance criteria

- [ ] Output file exists.
- [ ] EODHD research path documented (worker `market_data_step.py` + API `eodhd_client.py`).
- [ ] IBKR execution path documented (API `ibkr_market_data.py:IbkrMarketDataAdapter`).
- [ ] Locked freshness policy cited (`MarketDataReadinessPolicy.fresh_within=15min, near_stale_within=30min`).
- [ ] 5-state `MarketDataFreshnessStatus` enum enumerated.
- [ ] 4+ storage tables enumerated: `market_data_snapshots`, `market_data_latest_snapshots`, `fx_rate_snapshots`, `market_data_bars`.
- [ ] No source modification.

## Out of scope

- ADR-0003 "All-In-One" gap closure (T-007 §1 already flags this).
- Fundamentals / splits / dividends endpoint implementation (only EOD + FX are wired today).
- Order submission flow (T-019); reconciliation (T-020).

## Verification

- File exists.
- Both paths cited with `path:line` anchors.
- Freshness policy + price-basis fallback both appear.
- Hard `safe_for_*=False` floor on IBKR adapter output cited.

## Notes

The two paths converge in the storage layer (`market_data_latest_snapshots`) but operate on different freshness scales (EOD = daily, IBKR live = minutes). The locked 15-minute freshness policy applies primarily to the IBKR execution path; the EOD path has its own staleness logic (T-007 §4 — 3-day threshold in forecasting). This split is worth surfacing as a Phase 1c observation.
