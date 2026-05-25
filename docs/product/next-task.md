# Task 182

Slice 27 — V1.1 GBM + Momentum rebuild. The first of two
predictor-quality rebuild slices. Slice 26 (feedback loop) is now
live; this slice replaces the audit-flagged weaknesses in two of
the four deterministic predictors.

Scope:
- **GBM rebuild** (`baseline_forecast.py` + `gbm_predictor.py`):
  - Cap the drift estimation window to the most recent 1 trading
    year (252 bars) instead of using the entire history. The
    rebuild keeps the full series for volatility estimation but
    confines drift to recent regime.
  - Add a regime-shift detector: if the rolling 60d drift differs
    by more than 2σ from the long-window drift, down-weight the
    long window's contribution (interpolated blend).
  - Optional GARCH(1,1) volatility from `statsmodels` when the
    series is long enough; falls back to the rolling-SD baseline
    otherwise. Behind a new `gbm_garch_enabled` setting (default
    False) so the morning chain stays stable until the rebuild
    proves out via the Slice 25 backtest leaderboard.
- **Momentum rebuild** (`momentum_predictor.py`):
  - Horizon-scaled direction thresholds: `±X% × √(horizon/21)` so
    a 5d horizon's "slight" bucket is much narrower than a 60d
    horizon's.
  - Skip-the-week variant: for short horizons (< 21 days) use the
    11-1-week momentum (skip the last week instead of the last
    month). Reduces the look-ahead bias that hurts short-horizon
    accuracy.
  - Volatility-adjusted composite score: divide the 12-1 momentum
    by the long-window SD so the score is genuinely unitless.
- New `gbm_regime_shift_threshold_pct` setting (default 5.0%
  above which the regime-shift detector triggers).
- Tests: regime-shift behaviour (no-shift vs shift series),
  horizon-scaled thresholds (5d / 21d / 60d distinct
  classifications), backwards-compat for the existing predictor
  tests (which should still pass with the rebuild defaults).
- The rebuilt predictors keep the same `PredictorProtocol`
  shape; the Slice 25 backtester scores them automatically so
  the leaderboard surfaces whether the rebuild actually improves
  Brier-score.

When Slice 27 ships, Slice 28 (Mean-Rev + QVM rebuild) is
unblocked.

Manual approval gate stays; safety booleans hard-False on every
persisted record.
