## V1.1 status

**V1.1 is in flight.** V1 (Slices 1–22) is feature-complete and the
morning chain runs end-to-end against the locked paper-account
configuration. V1.1 refactors the prediction stack and widens four
non-prediction areas, all locked via §22 in
`version-1-product-experience-locks.md`.

The V1 predictor stack stays running through the entire V1.1
refactor — each refactor slice ships behind a per-slice flag and the
morning chain never goes dark.

## V1.1 slice queue (Slices 23–34, locked via §22)

- Slice 23 — Task 178: **V1.1 doctrine amendment**. Lock the V1.1 scope into `version-1-product-experience-locks.md §22`; create this backlog + `version-1-1-scope-register.md`; add the placeholder `CLAUDE_AI_BUDGET_MONTHLY_EUR` setting and the commented-out numpy/pandas/statsmodels declarations in `pyproject.toml`. Docs-only; no behavior change.
- Slice 24 — Task 179 ✅ **completed**: Predictor refactor base. Heavy deps activated (`numpy>=2.0.0` + `pandas>=2.2.0` + `statsmodels>=0.14.0` in `packages/portfolio`'s runtime dependencies). New `_predictor_math` module centralises numpy-backed primitives (`bar_closes_array`, `log_returns`, `sample_mean`, `sample_stdev`, `population_stdev`, `normal_cdf`, `Z_10/50/90`, `decimal_from_float`, `clipped_probability`). All four deterministic predictors (`baseline_forecast`, `momentum_predictor`, `mean_reversion_predictor`, `qvm_factor_predictor`) routed through the shared module; behaviour identical (existing pytest suite passes unchanged). `PredictorResearchProtocol` extends `PredictorProtocol` with `backtest_window_score(inputs, *, window_days) -> BacktestWindowScore`. Storage migration `0041_predictor_backtest_runs` + `PredictorBacktestRunRecord` (status set `{running, succeeded, failed, skipped}`, hit_rate ∈ [0, 1] when set, non-negative Brier, safety booleans hard-False) + `SqlAlchemyPredictorBacktestRunRepository` (save / update / list with filter). `claude_ai_budget_monthly_eur` + `universe_set` + `predictor_backtest_enabled` settings declared from Slice 23 stay; no new env vars in this slice.
- Slice 25 — Task 180: **Backtesting framework**. Pure-Python (pandas-based) walk-forward backtester. Per-predictor Sharpe + hit-rate + Brier-score over rolling 90d windows. New routes `POST /predictor/backtest/run` + `GET /predictor/backtest/latest`. The leaderboard becomes the operator's first feedback surface.
- Slice 26 — Task 181: **Feedback loop + auto-weighting**. Persist per-predictor outcomes in the Prediction Diary (new column on diary entries referencing `model_code`). Compute the rolling Brier-score helper. Ensemble combiner gains `weight_strategy=equal_weight | auto`; `auto` weights by inverse-Brier (clipped to [0.05, 0.40] per predictor).
- Slice 27 — Task 182: **GBM + Momentum rebuild**. Regime-aware GBM (1y drift cap + regime-shift detector). Horizon-scaled direction thresholds (`±X% × √(horizon/21)`). Momentum: skip-the-week instead of skip-the-month for shorter horizons; volatility-adjusted composite score.
- Slice 28 — Task 183: **Mean-Rev + QVM rebuild**. Hurst-asymmetric Mean-Rev target (trending assets revert less). QVM: minimum universe raised to 30 (rejecting tiny universes); sector-neutral z-scoring; tanh-soft-clip instead of hard ±2.
- Slice 29 — Task 184: **Real AI explanation provider**. Real Anthropic Claude HTTP client. Claude Haiku default. Prompt caching mandatory. Budget cap enforced at the call boundary (refuses + logs once `CLAUDE_AI_BUDGET_MONTHLY_EUR` is exceeded). Stub provider stays as fallback.
- Slice 30 — Task 185: **Real AI TS predictor**. Real Claude numerical-forecast provider via structured output. Daily-only invocation (no on-demand). Optional TimesFM HTTP adapter behind a flag for comparison.
- Slice 31 — Task 186: **Universe scan expansion + operator-selectable set**. Lock-universe registry adds `EU600` + `ALL_5K`. New `UNIVERSE_SET` env var (default `SP500`). Per-set EODHD-call caching + storage paging.
- Slice 32 — Task 187: **Conditional orders + GTC/OPG/IOC**. Extend `LOCKED_ORDER_TYPES` with `CONDITIONAL`. Extend TIF to `{DAY, GTC, OPG, IOC}`. New draft fields for price / time / margin / volume / execution conditions. Per-type dry-run safety codes. `ibapi.Order.conditions` + `Order.tif` wiring.
- Slice 33 — Task 188: **UX upgrade**. Predictor-leaderboard panel; backtest-history panel; Decision Package diff between morning runs; Dutch microcopy review across the existing Portefeuille surface.
- Slice 34 — Task 189: **V1.1 release readiness**. Updated readiness scorecard with V1.1 blockers; V1.1 acceptance test (end-to-end against stub providers); runbook update. Locks the V1.1 expansion queue closed.

## Out of V1.1 scope (post-V1.1 widening)

- Multi-account portfolios.
- Mobile app.
- Real-time intraday predictor evaluation.
- Briefing item source distinction (portfolio / watchlist / universe_scan_candidate).
- Real-money path (V1.1 stays paper-first; a separate scope discussion locks any live-money slice).
- New predictor families beyond the V1 five (volatility-as-prediction, options-implied probs, sentiment-from-research-as-predictor, PEAD post-earnings-drift) — deferred to V1.2 once V1.1's feedback loop measures the existing five.
