# Task 179

Slice 24 — V1.1 predictor refactor base. The first implementation
slice of the V1.1 expansion queue. Locked via §22 in
`version-1-product-experience-locks.md`.

Scope:
- Add `numpy`, `pandas`, `statsmodels` as runtime dependencies of
  `packages/portfolio` (the V1.1 §22.1 boundary relaxation).
  `packages/storage` stays stdlib + SQLAlchemy + Alembic;
  `apps/api` keeps the existing dep set.
- Migrate the internals of the five existing predictors
  (`baseline_forecast`, `gbm_predictor`, `momentum_predictor`,
  `mean_reversion_predictor`, `qvm_factor_predictor`,
  `ai_ts_predictor`) to use `numpy.ndarray` / `pandas.Series` for
  the log-return + rolling-statistics math. **Behavior identical**:
  the existing pytest suite must pass without modification; only
  the implementation changes.
- Decimal-only money math stays at the dataclass boundary
  (`PredictionDistribution`'s fields, repository contracts,
  `OrderSubmissionInputs`). Numpy/pandas frames never leak past
  the predictor implementation.
- Introduce `PredictorResearchProtocol` extending
  `PredictorProtocol` with two optional methods:
  `backtest_window_score(bars, horizon, window_days) -> dict` and
  `link_diary_outcome(model_code, diary_entry_id) -> None`. The
  existing predictors implement no-op stubs; Slice 25 wires them.
- Storage migration `0041_predictor_backtest_runs` adds an audit
  table for backtest invocations:
  `(run_id, model_code, model_version, started_at, finished_at,
  status, window_days, bars_used, brier_score, hit_rate,
  sharpe_ratio, blocking_reason, safe_for_action_drafts,
  safe_for_orders)`. Status set locked to
  `{running, succeeded, failed, skipped}`; safety booleans
  hard-False; per-run repo follows the standard SqlAlchemy pattern.
- New settings `predictor_backtest_enabled` (default False);
  no UI change in this slice.
- Tests cover: every existing predictor test still passes;
  storage migration applies + downgrade ordering correct;
  `PredictorResearchProtocol` stub-call works.

No new routes; no UI change; manual approval gate stays. The
morning chain keeps running on the existing predictors.

When Slice 24 ships, Slice 25 (backtesting framework) is unblocked.
