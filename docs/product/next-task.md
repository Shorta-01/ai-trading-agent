# Task 180

Slice 25 — V1.1 backtesting framework. Builds on the Slice 24
predictor refactor base (numpy + pandas internals, the audit table
`predictor_backtest_runs`, and `PredictorResearchProtocol`).

Scope:
- New `predictor_backtester` module in `packages/portfolio` with a
  pandas-based walk-forward harness:
  `walk_forward_backtest(predictor, bars, *, window_days, horizon, step)
  -> Iterable[BacktestWindowScore]`. Slides a `window_days`-wide
  fitting/refit window forward by `step` bars; at each fold the
  predictor's `predict(...)` is called on the in-window history and
  the realised horizon outcome is scored against the predicted
  distribution.
- Per-predictor scoring: Brier-score on the predicted probabilities
  (`prob_gain` vs realised gain/loss), hit-rate on the direction
  label (was the realised price direction in the predicted
  category?), and Sharpe-ratio on the expected-return vector vs.
  realised returns.
- Each fold writes one `PredictorBacktestRunRecord` via the Slice
  24 repository; aggregate over folds produces the
  `BacktestWindowScore` returned to the caller.
- Implement `backtest_window_score(...)` on each of the five V1
  predictors (`GbmPredictor`, `MomentumPredictor`,
  `MeanReversionPredictor`, `QvmFactorPredictor`, `AiTsPredictor`).
  AI predictor + QVM may degrade gracefully when their dependencies
  (provider, universe) aren't available — return a `skipped` row
  rather than failing the whole batch.
- New routes:
  * `POST /predictor/backtest/run` — gated on
    `predictor_backtest_enabled`; runs a single
    `{model_code, asset_symbol, window_days}` backtest and persists
    the audit row.
  * `GET /predictor/backtest/latest` — returns the leaderboard
    (most recent row per `model_code`) with Dutch summary text.
- Tests:
  * Walk-forward harness correctness (fold boundaries; can't
    leak future data into the window).
  * Each predictor's `backtest_window_score(...)` produces a row
    with the right `model_code`/`model_version`/`bars_used`.
  * Endpoint gating + happy-path persistence.

No new schema beyond the Slice-24 audit table. No new predictor
behaviour change. Manual approval gate stays; safety booleans
hard-False on every row.

When Slice 25 ships, Slice 26 (feedback loop + auto-weighting)
is unblocked.
