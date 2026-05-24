# Task 171

Slice 16 — QVM (Quality + Value + Momentum) factor predictor. Third
step of the V1 §21.4 ensemble lock.

Scope:
- Extend the `EodhdClient` in `apps/api` with a `fetch_fundamentals(symbol)`
  helper that pulls the JSON fundamentals endpoint (financial highlights,
  earnings, balance sheet ratios) for one ticker. Stdlib `urllib`-only,
  injectable HTTP fetcher (same pattern as the existing bar/quote calls).
- Storage migration adding `asset_fundamentals_snapshots` table: one row
  per (symbol, fetched_at) carrying ROIC, gross_margin, P/E, P/B,
  EV/EBITDA, return_6m_pct, return_12m_pct, dividend_yield, sector,
  raw_payload_hash; locked safety booleans hard-False.
- New pure-Python `QvmFactorPredictor` in `packages/portfolio`
  implementing the predictor protocol:
  * Quality score = z-score of (ROIC + gross_margin) within the
    snapshot universe
  * Value score = z-score of (-P/E + -P/B + -EV/EBITDA), each clipped
    to a sane range first
  * Momentum score = z-score of (return_6m + return_12m)
  * Composite QVM = average of the three; mapped to a horizon-return
    projection (same conservative cap as Momentum: ±25 % annualised).
- The cross-sectional z-scores require a *universe snapshot*; in this
  slice the predictor accepts an injected `UniverseFundamentals`
  fixture so it remains pure-Python. Slice 17 will wire the daily
  scan that populates the universe.
- Tests cover the QVM math against synthetic universes and the predictor
  blocking when the symbol is absent from the universe snapshot.

No orchestrator change yet; the QVM predictor joins the ensemble once
Slice 17 wires the universe scan into `forecast_sync`.
