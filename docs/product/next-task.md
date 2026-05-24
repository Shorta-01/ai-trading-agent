# Task 169

Slice 14 — `PredictorProtocol` + Momentum predictor. The first concrete
step of the V1 §21.4 ensemble lock.

Scope:
- Define `PredictorProtocol` in `packages/portfolio`: input
  `PredictorInputs(historical_bars, current_price, horizon_trading_days,
  asset_metadata)`; output `PredictionDistribution(model_code,
  model_version, p10_price, p50_price, p90_price, prob_gain, direction,
  confidence_score, expected_return_pct, blocking_reason)`.
- Migrate the existing lognormal GBM (`compute_baseline_forecast`) to
  implement the protocol; export a `GbmPredictor` class.
- Add a `MomentumPredictor` class (deterministic Python):
  * 12-1 momentum (12-month return excluding most-recent month)
  * Time-series momentum (sign + magnitude of last 6 months vs. trailing volatility)
  * Combines both into a `PredictionDistribution` with the same shape
    GBM returns
- The two predictors must be drop-in interchangeable through the
  protocol; no orchestrator change yet — this slice only defines the
  contract and adds the first new predictor.
- Tests cover both predictors against synthetic series with known
  momentum and known mean-reversion characteristics.

No new tables, no routes, no UI; just the predictor contract +
momentum module. Slice 15 wires the ensemble combiner.
