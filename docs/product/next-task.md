# Task 170

Slice 15 — Mean-reversion predictor + ensemble combiner. Second step of
the V1 §21.4 ensemble lock.

Scope:
- New `MeanReversionPredictor` in `packages/portfolio` (deterministic
  Python):
  * RSI (Relative Strength Index, 14-day)
  * Bollinger position (z-score against 20-day moving average)
  * Hurst exponent (rescaled-range estimator, 100-day window) — if
    the Hurst exponent is below 0.5 the series is mean-reverting
  * Combine into a composite reversion score; map to a
    `PredictionDistribution` that pulls the projection back towards
    the moving average rather than chasing momentum.
- New deterministic `ensemble_combiner` module in
  `packages/portfolio`:
  * `compute_ensemble_forecast(predictors, inputs, weights)` runs
    every predictor, drops blocked ones, and combines the surviving
    distributions into one `PredictionDistribution` with model_code
    `ensemble_v1`.
  * Default weighting is equal-weight at launch; the protocol accepts
    an optional `weights: dict[str, Decimal]` so Slice 16+ can move
    to inverse-variance once Diary track-record exists.
  * Per-predictor contributions are exposed via a sibling
    `EnsembleContribution` dataclass for downstream Diary tracking.
- Tests cover the predictor against synthetic mean-reverting series,
  and the combiner against fixtures with mixed ready/blocked
  predictors, weight overrides, and the empty-set edge case.

No orchestrator change yet; Slice 17 wires the ensemble into the
forecast sync.
