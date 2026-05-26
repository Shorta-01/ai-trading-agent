# `packages/portfolio` — predictors

**Phase:** 1a (reality components)
**Task:** T-002
**Scope:** fourteen modules in `packages/portfolio/src/portfolio_outlook_portfolio/` that implement the per-asset forecasting stack: math primitives, predictor protocol, four deterministic predictors plus an AI-TS adapter, an ensemble combiner with per-predictor feedback weighting, a walk-forward backtester, Kelly sizing, and the prediction-diary outcome evaluator.

This file is descriptive. It states what the code at HEAD does today, with `path/to/file.py:NNN` citations and short excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

- `baseline_forecast.py` — single-predictor GBM closed-form distribution + label-input shape.
- `baseline_label_translator.py` — locked Dutch action labels from forecast + risk profile + has_position.
- `_predictor_math.py` — shared numpy / scipy primitives.
- `predictor_protocol.py` — `PredictorProtocol`, `PredictionDistribution`, `BacktestWindowScore`.
- `predictor_backtester.py` — walk-forward harness + persistence helpers.
- `predictor_feedback.py` — per-predictor outcome labels + inverse-Brier weights with water-filling clip.
- `gbm_predictor.py` — thin protocol adapter over `baseline_forecast`.
- `momentum_predictor.py` — 12-1 composite momentum.
- `mean_reversion_predictor.py` — RSI + Bollinger + Hurst exponent.
- `qvm_factor_predictor.py` — cross-sectional QVM (Quality / Value / Momentum) factor.
- `ai_ts_predictor.py` — LLM-as-forecaster adapter (provider-injected).
- `ensemble_combiner.py` — weighted average over surviving predictors + agreement factor.
- `kelly_sizing.py` — fractional-Kelly + risk-parity caps.
- `prediction_diary_eval.py` — per-horizon outcome labels (right / wrong / inconclusive / early / no_data).

## `baseline_forecast.py` — GBM closed-form distribution

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/baseline_forecast.py`

### Public surface

- `HistoricalBar(bar_date: date, close_price: Decimal)` frozen dataclass (`:64-70`).
- `BaselineForecast` frozen dataclass — 21 fields including `p10/p50/p90_price`, `prob_gain`, `prob_loss_gt_5pct`, `confidence_score`, `direction_label`, `direction_label_nl`, `status`, `blocking_reason` (`:73-101`).
- `compute_baseline_forecast(*, bars, current_price, horizon_trading_days=21, trading_days_per_year=252, minimum_bars_required=60, drift_window_days=None, regime_shift_enabled=False, regime_shift_threshold_pct=5.0, garch_enabled=False)` (`:286-456`).
- Constants `DEFAULT_TRADING_DAYS_PER_YEAR=252`, `DEFAULT_HORIZON_TRADING_DAYS=21`, `MINIMUM_BARS_REQUIRED=60`, `MODEL_CODE="baseline_gbm"`, `MODEL_VERSION="v1.0.0"` (`:34-38`).
- Hard-coded standard-normal quantiles `Z_10=-1.2815515655446004`, `Z_50=0.0`, `Z_90=1.2815515655446004` (`:59-61`).

### Collaborators

Lazy-imports `_predictor_math as _pm` inside `_log_returns`, `_sample_mean`, `_sample_stdev`. No other portfolio module imports at module load.

### Notable choices

- **Lognormal GBM with closed-form quantiles** — no Monte Carlo, no bootstrap. `_normal_cdf` uses `math.erf`.
- **Hybrid Decimal/float boundary** documented in the module header (`:18-21`): "uses `Decimal` for prices and `float` only for the GBM math (`exp/log/sqrt/erf` aren't defined on `Decimal`); each `float` step is narrow and wrapped back into `Decimal` before returning." Boundary helper `_decimal(value, places=6)` uses `Decimal(repr(value)).quantize(quant, rounding=ROUND_HALF_UP)` (`:104-108`).
- Five deterministic blocking reasons returning zero-filled `BaselineForecast` with `status="blocked"`: `invalid_horizon`, `invalid_current_price`, `insufficient_history`, `invalid_bar_price`, `zero_volatility` (`:300-375`).
- Confidence is sample-size heuristic: 0.40 at 60 bars, linear to 0.95 at 252 bars (`_confidence_from_sample_size`, `:193-204`).
- Direction thresholds locked at ±2% (slight) / ±10% (strong) over the horizon (`:174-190`).
- `garch_enabled` is wired but **raises `NotImplementedError`** (`:353-358`).

```python
# baseline_forecast.py:399-405
s0 = float(current_price)
drift_log = (mu_annual - 0.5 * sigma_annual**2) * horizon_years
diffusion_log = sigma_annual * math.sqrt(horizon_years)

p10 = s0 * math.exp(drift_log + diffusion_log * Z_10)
p50 = s0 * math.exp(drift_log + diffusion_log * Z_50)
p90 = s0 * math.exp(drift_log + diffusion_log * Z_90)
```

## `baseline_label_translator.py` — locked Dutch action labels

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/baseline_label_translator.py`

### Public surface

Ten locked Dutch label constants (`LABEL_KOPEN`, `LABEL_LANGZAAM_BIJKOPEN`, `LABEL_HOUDEN`, `LABEL_BEKIJKEN`, `LABEL_VERMINDEREN`, `LABEL_VERKOPEN`, `LABEL_VERMIJDEN`, `LABEL_CASH_HOUDEN`, `LABEL_GEEN_ACTIE`, `LABEL_GEBLOKKEERD`, `:33-56`). Three risk-profile constants (`RISK_PROFILE_VOORZICHTIG`, `RISK_PROFILE_GEBALANCEERD`, `RISK_PROFILE_GROEI`, `:62-70`). `SuggestionInputs(forecast, risk_profile, has_position, gate_failures=())` (`:91-100`); `SuggestionDecision(action_label_nl, confidence_label, score, rationale, drivers, blockers, status, blocking_reason)` (`:103-118`). `translate_forecast_to_label(inputs) -> SuggestionDecision` (`:179-253`). Confidence thresholds `Decimal("0.70")` / `Decimal("0.50")` (`:76-77`).

### Collaborators

Imports `BaselineForecast` from `.baseline_forecast`. No other portfolio modules.

### Notable choices

- Module banner: "AI never decides the label. Pure Python rules over evidence-gated inputs." (`:11`)
- Three-stage precedence: gate failures → control_needed `"Bekijken"`; forecast not ready → `"Geblokkeerd"`; otherwise decision tree on `has_position` (`:192-238`).
- Held-position rules are conservative: `strong_down` × `Hoog` → `Verkopen`; `strong_down` × `Middel` → `Verminderen`; ambiguous defaults to `Houden` (`:256-288`).
- Cold-start rules even stricter: `Kopen` requires `strong_up` × `Groei` × `Hoog`; all other up → `Bekijken`; all down → `Vermijden` (`:291-325`).

```python
# baseline_label_translator.py:306-314
if direction == "strong_up":
    if (
        risk_profile == RISK_PROFILE_GROEI
        and confidence_label == CONFIDENCE_LABEL_HIGH
    ):
        return LABEL_KOPEN
    if confidence_label == CONFIDENCE_LABEL_HIGH:
        return LABEL_BEKIJKEN
    return LABEL_BEKIJKEN
```

## `_predictor_math.py` — shared numerics

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/_predictor_math.py`

### Public surface

`bar_closes_array(bars) -> np.ndarray` (`:24-34`); `log_returns(prices)` masks non-positive endpoints (`:37-54`); `sample_mean`, `sample_stdev` (ddof=1), `population_stdev` (ddof=0) (`:57-80`); `normal_cdf(z)` scipy-backed (`:83-86`); `Z_10/Z_50/Z_90` via `scipy.stats.norm.ppf` (`:90-92`); `decimal_from_float(value, places=6)`, `clipped_probability(value)` (`:95-105`).

### Collaborators

Imports `HistoricalBar` from `baseline_forecast`. Heavy deps: `numpy`, `scipy.stats`.

### Notable choices

- Module banner: "V1.1 §22.1 lock relaxes the heavy-dep boundary inside `packages/portfolio`. ... Callers stay pure-Python at the dataclass boundary; numpy / pandas arrays never leak past the predictor." (`:3-7`)
- Explicitly stateless: "no randomness, no I/O, no `datetime.now()`" (`:10-11`).
- `log_returns` masks non-positive endpoints rather than failing the whole series (`:48-54`).
- Both `sample_stdev` (ddof=1) and `population_stdev` (ddof=0) exposed because different predictor paths use different conventions.

```python
# _predictor_math.py:46-54
if prices.size < 2:
    return np.empty(0, dtype=np.float64)
valid_mask = (prices[:-1] > 0) & (prices[1:] > 0)
if not valid_mask.any():
    return np.empty(0, dtype=np.float64)
valid_prev = prices[:-1][valid_mask]
valid_curr = prices[1:][valid_mask]
out: np.ndarray = np.log(valid_curr / valid_prev)
return out
```

## `predictor_protocol.py` — protocol + value objects

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/predictor_protocol.py`

### Public surface

Direction-label constants (`strong_up`, `slight_up`, `flat`, `slight_down`, `strong_down`, `:33-37`); status constants (`ready`, `blocked`, `:43-44`); blocking-reason codes (`:47-50`). `PredictorInputs(historical_bars, current_price, horizon_trading_days, asset_metadata={})` (`:53-67`). `PredictionDistribution` frozen dataclass — the locked predictor output shape; self-validates in `__post_init__` (`:70-113`). `PredictorProtocol` (`:116-125`) with `model_code`, `model_version`, `predict`. `BacktestWindowScore` frozen dataclass (`:128-146`). `PredictorResearchProtocol` extends with `backtest_window_score` (`:149-176`).

### Collaborators

`HistoricalBar` from `baseline_forecast`. Used by every concrete predictor.

### Notable choices

- "This module is pure Python: the protocol carries no I/O, no provider factories, no `datetime.now()`. Predictors must be deterministic given the same inputs." (`:16-19`)
- Direction labels classify the **distribution**, not the action — translator is a separate concern (`:30-32`).

```python
# predictor_protocol.py:95-102
def __post_init__(self) -> None:
    if not self.model_code.strip():
        raise ValueError("model_code must be non-empty")
    if not self.model_version.strip():
        raise ValueError("model_version must be non-empty")
    if self.horizon_trading_days <= 0:
        raise ValueError("horizon_trading_days must be positive")
    if self.status not in {STATUS_READY, STATUS_BLOCKED}:
```

## `predictor_backtester.py` — walk-forward harness

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/predictor_backtester.py`

### Public surface

Constants `DEFAULT_WINDOW_DAYS=252`, `DEFAULT_HORIZON_DAYS=21`, `DEFAULT_STEP_DAYS=5`, `MIN_FOLDS_FOR_METRICS=2` (`:59-62`). `FoldOutcome` (`:69-81`). `walk_forward_backtest(predictor, bars, *, window_days, horizon_trading_days, step_days, asset_metadata)` (`:113-193`). `aggregate_window_score(*, predictor, outcomes, window_days)` (`:196-257`). `walk_forward_score(...)` (`:260-283`). `BacktestPersistenceInputs/Outputs` (`:286-304`). `run_predictor_backtest(...)` (`:307-346`). `new_backtest_run_id()` (`:349-352`, returns `f"bt_{uuid4().hex}"`). `backtest_window_score_for_predictor(predictor, inputs, *, window_days, step_days)` (`:355-392`).

### Collaborators

`HistoricalBar` from `baseline_forecast`; direction/status constants + `BacktestWindowScore`, `PredictorInputs`, `PredictorProtocol` from `predictor_protocol`. Uses `numpy`.

### Notable choices

- "Walk-forward, no look-ahead: each fold trains/predicts on `bars[start:end]` and is scored against `bars[end:end+horizon]`." (`:17-21`)
- Brier = mean `(predicted_prob_gain - realised_indicator)²`; hit-rate uses 5-bucket direction collapsed to up/flat/down; Sharpe is unitless `mean / std(ddof=1)`, **not annualised** (`:22-31, :228-239`).
- `_realised_direction` mirrors the ±2%/±10% locked thresholds (`:84-97`).
- Per-fold exceptions caught silently with `except Exception` boundary (`:162-163`). Blocked predictions skipped, not failed (`:164-165`). `<2` folds → metrics `None`.
- `run_predictor_backtest` uses `datetime.now(UTC)` for `finished_at` (`:333`); `new_backtest_run_id` uses `uuid4()`. Both are non-deterministic; the harness body remains deterministic.

```python
# predictor_backtester.py:150-163
for end in range(window_days, last_fold_end + 1, step_days):
    window_bars = bars[end - window_days : end]
    current_price = window_bars[-1].close_price
    try:
        prediction = predictor.predict(
            PredictorInputs(
                historical_bars=window_bars,
                current_price=current_price,
                horizon_trading_days=horizon_trading_days,
                asset_metadata=metadata,
            )
        )
    except Exception:  # noqa: BLE001 — fold-level boundary catch
        continue
```

## `predictor_feedback.py` — outcome labels + inverse-Brier weights

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/predictor_feedback.py`

### Public surface

Outcome labels (`correct`, `partial`, `wrong`, `no_data`, `:39-42`); clip constants `DEFAULT_WEIGHT_CLIP_LOW=0.05`, `DEFAULT_WEIGHT_CLIP_HIGH=0.40` (`:47-48`); `PerPredictorOutcome` (`:51-65`). `compute_per_predictor_outcomes(*, ensemble, realised_return_pct, now=None) -> tuple[PerPredictorOutcome, ...]` (`:116-184`). `compute_inverse_brier_weights(history, *, clip=(0.05, 0.40), fallback_codes=()) -> dict[str, Decimal]` (`:195-269`).

### Collaborators

`EnsembleResult` from `ensemble_combiner` (the combiner's auto-weight path lazy-imports `compute_inverse_brier_weights` to avoid the cycle, `ensemble_combiner.py:233-234`).

### Notable choices

- Module header: "the auto-weighting strategy may down-weight a predictor but never silence it: the lower clip is a non-negative floor so every V1 predictor keeps at least a small share even after a long bad run. The morning chain never goes dark." (`:19-23`)
- Per-predictor weight band locked to **[5%, 40%]** (`:46-48`).
- Direction bucketing collapses 5-bucket to up/flat/down: equal direction → `correct`, same bucket different strength → `partial`, opposite → `wrong` (`:83-105`).
- `_brier` single-fold: `(prob_gain - indicator)²` quantised to 6 decimals (`:108-113`).
- Water-filling clip (`_apply_clip_with_water_filling`, `:272-350`) — two-pass per iteration (upper cap → redistribute → lower floor → redistribute), max 20 iterations. Falls back to equal-weight when `N × clip_low > 1` or `N × clip_high < 1`.
- `compute_per_predictor_outcomes` accepts injectable `now` but discards the value (`_ = now if now is not None else datetime.now(UTC)`, `:134`) — the function stays fully deterministic.

```python
# predictor_feedback.py:305-312
# ---- Upper cap pass ----
for code, value in current.items():
    if code in high_pinned or code in low_pinned:
        continue
    if value > clip_high:
        current[code] = clip_high
        high_pinned.add(code)
        changed = True
```

## `gbm_predictor.py` — protocol adapter over baseline GBM

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/gbm_predictor.py`

### Public surface

`GBM_MODEL_CODE` (= `"baseline_gbm"`), `GBM_MODEL_VERSION` (= `"v1.0.0"`); `class GbmPredictor(*, minimum_bars_required=60, drift_window_days=None, regime_shift_enabled=False, regime_shift_threshold_pct=5.0, garch_enabled=False)` (`:58-131`). Implements `PredictorResearchProtocol` (`predict`, `backtest_window_score`).

### Collaborators

`compute_baseline_forecast`, `MINIMUM_BARS_REQUIRED`, `DEFAULT_REGIME_SHIFT_THRESHOLD_PCT`, model code/version from `baseline_forecast`. Protocol value objects from `predictor_protocol`. Lazy-imports `backtest_window_score_for_predictor` from `predictor_backtester`.

### Notable choices

- "Thin wrapper around the existing `compute_baseline_forecast`. The math is unchanged; this module only adapts the output shape so the ensemble combiner can treat GBM as one predictor among five." (`:1-6`)
- Direction-label translation: GBM emits `"neutral"`, protocol uses `"flat"`. `_GBM_DIRECTION_MAP` handles the rename; unknown labels (including the GBM-internal `"blocked"`) default to `DIRECTION_FLAT` so the protocol's `__post_init__` validation passes for blocked rows (`:36-55`).

```python
# gbm_predictor.py:36-42
_GBM_DIRECTION_MAP: dict[str, str] = {
    "strong_up": DIRECTION_STRONG_UP,
    "slight_up": DIRECTION_SLIGHT_UP,
    "neutral": DIRECTION_FLAT,
    "slight_down": DIRECTION_SLIGHT_DOWN,
    "strong_down": DIRECTION_STRONG_DOWN,
}
```

## `momentum_predictor.py` — 12-1 composite momentum

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/momentum_predictor.py`

### Public surface

`MODEL_CODE="momentum_v1"`, `MODEL_VERSION="v1.0.0"` (`:58-59`); constants `MOMENTUM_MIN_BARS=250`, `LOOKBACK_12M=252`, `LOOKBACK_1M=21`, `LOOKBACK_6M=126`, `MAX_ANNUAL_DRIFT_PCT=25.0` (`:63-75`); direction thresholds `10.0`/`2.0` over baseline 21d horizon (`:79-81`). Skip-the-week variant constants `LOOKBACK_WEEK=5`, `LOOKBACK_11_WEEKS=55`, `SHORT_HORIZON_CUTOFF_DAYS=21` (`:85-87`). `class MomentumPredictor(*, minimum_bars_required=250, max_annual_drift_pct=25.0, trading_days_per_year=252, horizon_scaled_thresholds=False, skip_week_short_horizon=False)` (`:302-462`).

### Collaborators

`_predictor_math as _pm`, `HistoricalBar` + horizon/year defaults from `baseline_forecast`; protocol value objects from `predictor_protocol`; lazy `backtest_window_score_for_predictor`. Uses `numpy`.

### Notable choices

- Composite of two factors: (1) 12-1 momentum (cumulative log-return over 12 months, skipping the most recent month — Jegadeesh & Titman, Asness/Moskowitz/Pedersen) (`:229-243`); (2) Time-series momentum (6-month log return / (6-month SD × √126) — Moskowitz/Ooi/Pedersen) (`:246-266`).
- Normalises 12-1 by dividing by `log(1.25)` (≈0.223) so +25% annualised maps to +1.0; both components clipped [-1, +1] and averaged. Returns `0.0` when both are `None` (`:269-285`).
- Score → annual-drift: `annual_drift_pct = MAX_ANNUAL_DRIFT_PCT × score` (capped at ±25%) (`:381`); then horizon-scaled.
- Distribution width from trailing 6-month log-return SD, scaled by `√horizon` (`:390-403`).
- Confidence: 0.4 at 250 bars → 0.85 at 504 bars — lower max than GBM (0.95). Module comment: "momentum is more fragile to regime changes" (`:288-299`).
- V1.1 Slice 27 opt-ins (default off): `horizon_scaled_thresholds` scales ±2/±10 by `√(horizon/21)`; `skip_week_short_horizon` swaps to an 11-week skip-1-week variant when `horizon < 21` (`:145-194, :369-376`).
- Hard-coded Z values inline (`±1.2815515655446004`) rather than imported from `_predictor_math`.

```python
# momentum_predictor.py:229-243
def _compute_12_1_momentum(prices: Sequence[float]) -> float | None:
    """Return the cumulative log-return over the trailing 12 months,
    skipping the most recent month."""

    if len(prices) <= LOOKBACK_12M:
        return None
    end_index = len(prices) - 1 - LOOKBACK_1M
    start_index = end_index - (LOOKBACK_12M - LOOKBACK_1M)
    if start_index < 0:
        return None
    start_price = prices[start_index]
    end_price = prices[end_index]
    if start_price <= 0 or end_price <= 0:
        return None
    return math.log(end_price / start_price)
```

## `mean_reversion_predictor.py` — RSI + Bollinger + Hurst

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/mean_reversion_predictor.py`

### Public surface

`MODEL_CODE="mean_reversion_v1"`, `MODEL_VERSION="v1.0.0"` (`:60-61`); constants `RSI_PERIOD=14`, `BOLLINGER_PERIOD=20`, `HURST_WINDOW=100`, `HURST_CHUNK_SIZES=(10, 20, 50, 100)`, `MEAN_REVERSION_MIN_BARS=130`, `BOLLINGER_Z_CAP=3.0`, `RSI_NEUTRAL=50.0`, `RSI_SCALE=50.0`, `THRESHOLD_STRONG_PCT=10.0`, `THRESHOLD_SLIGHT_PCT=2.0` (`:64-80`). `class MeanReversionPredictor(*, minimum_bars_required=130, trading_days_per_year=252, hurst_asymmetric_target=False)` (`:348-524`).

### Collaborators

`_predictor_math as _pm`, `HistoricalBar` + horizon defaults from `baseline_forecast`; protocol value objects from `predictor_protocol`. Uses `numpy`.

### Notable choices

- Three signals:
  - **RSI(14) with Wilder smoothing** (`_compute_rsi`, `:128-147`)
  - **Bollinger 20-day SMA + z-score** (`_compute_bollinger`, `:153-166`)
  - **Hurst exponent via rescaled-range (R/S)** on trailing 100-bar log-return series (`_compute_hurst`, `:172-222`)
- Composite **pull factor** = `((rsi_strength + bollinger_strength) / 2) × hurst_confidence`, where `rsi_strength = min(1, |RSI-50|/50)`, `bollinger_strength = min(1, |z|/3)`, `hurst_confidence = max(0, 1 - 2H)`. When Hurst can't be estimated, `hurst_confidence` defaults to **0.3** (`:425-438`).
- V1 default target: `current + pull × (SMA_20 - current)` (`:454`).
- V1.1 Slice 28 opt-in `hurst_asymmetric_target=False`: blends SMA-pull with 20-day trend-extrapolation between H=0.45 (full reversion) and H=0.55 (full trend); past H=0.55 the target is pure trend extrapolation (`:272-328`).
- Distribution width: trailing `min(126, len(prices))` log-return SD × `√horizon` (`:459-472`).
- RSI is the **textbook Wilder** path, not Cutler's.

```python
# mean_reversion_predictor.py:435-438
hurst_confidence = (
    max(0.0, 1.0 - 2.0 * hurst) if hurst is not None else 0.3
)
pull = base_strength * hurst_confidence
```

## `qvm_factor_predictor.py` — cross-sectional QVM factor

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/qvm_factor_predictor.py`

### Public surface

`MODEL_CODE="qvm_factor_v1"`, `MODEL_VERSION="v1.0.0"` (`:57-58`); constants `QVM_MIN_BARS=130`, `QVM_MIN_UNIVERSE_SIZE=5`, `QVM_MIN_UNIVERSE_SIZE_V1_1=30`, `MAX_ANNUAL_DRIFT_PCT=25.0`; ratio sanity clips `PE_CLIP=(1.0,80.0)`, `PB_CLIP=(0.1,25.0)`, `EV_EBITDA_CLIP=(1.0,60.0)`; blocking reasons `insufficient_universe`, `symbol_not_in_universe`, `insufficient_factors` (`:61-86`). `FundamentalsEntry(symbol, sector, pe_ratio, pb_ratio, ev_ebitda, roic_pct, gross_margin_pct, return_6m_pct, return_12m_pct)` (`:89-106`). `UniverseFundamentals(entries)` with `by_symbol()` (`:109-116`). `class QvmFactorPredictor(*, universe, target_symbol, minimum_bars_required=130, max_annual_drift_pct=25.0, trading_days_per_year=252, minimum_universe_size=5, sector_neutral_zscore=False, soft_clip_composite=False)` (`:362-564`).

### Collaborators

`_predictor_math as _pm`, `DEFAULT_TRADING_DAYS_PER_YEAR` from `baseline_forecast`; protocol value objects. Uses `numpy` and `statistics.fmean` / `statistics.pstdev`.

### Notable choices

- Cross-sectional z-score against the **injected universe**. Quality = mean(ROIC, gross margin); Value = mean of inverted+clipped P/E, P/B, EV/EBITDA; Momentum = mean(6m, 12m return). Composite = average of available factor z-scores (`:152-201, :462-474`).
- V1 default: hard ±2 clip → linear map [-1, +1] (`composite_z / 2.0`). V1.1 Slice 28 opt-in `soft_clip_composite=True` → `tanh(composite_z / 2.0)` (`_soft_clip_tanh`, `:275-286, :475-480`).
- V1.1 Slice 28 opt-in `sector_neutral_zscore=True`: subtracts per-sector mean before z-scoring against the de-meaned distribution (AQR / Asness convention). Entries without a sector fall back to global mean (`_sector_neutral_factor_score_for_symbol`, `:227-272`).
- Distribution width uses `statistics.pstdev` (population SD, not sample) — slight inconsistency vs Momentum/MeanReversion which use `sample_stdev` (`:491-494`).
- Universe-size constants split: dataclass default is the **V1 floor of 5** (to keep small-universe sanity tests working); the V1.1 §22.5-locked floor of 30 is enforced at the **apps/api** boundary via the `qvm_min_universe_size` setting (`:65-71`).
- Confidence: `0.4 + 0.4 × (factor_count/3) × min(1, universe_size/50)` — max 0.8 (`:353-359`).
- Backtester caveat: "QVM is a cross-sectional factor predictor. The walk-forward harness re-uses the injected universe snapshot at every fold — the universe itself is not time-rolled. Slice 28 (QVM rebuild) will lift this to a snapshot-per-fold model." (`:553-557`)

```python
# qvm_factor_predictor.py:474-480
composite_z = statistics.fmean(factor_scores)
# V1 default: hard ±2 clip → linear map onto [-1, +1].
# V1.1 Slice 28 soft-tanh: maps onto (-1, +1) via tanh, no kink.
if self._soft_clip_composite:
    composite_clipped = _soft_clip_tanh(composite_z)
else:
    composite_clipped = max(-1.0, min(1.0, composite_z / 2.0))
```

## `ai_ts_predictor.py` — LLM-as-forecaster adapter

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/ai_ts_predictor.py`

### Public surface

`MODEL_CODE="ai_ts_v1"`, `MODEL_VERSION="v1.0.0"` (`:48-49`); blocking-reason constants `provider_unavailable`, `provider_error`, `invalid_quantiles`, `invalid_prob_gain`, `invalid_confidence` (`:51-55`). `TsModelProviderInputs` (`:58-72`); `TsModelProviderResult(p10_price, p50_price, p90_price, prob_gain, expected_return_pct, confidence_score, model_provider_code, model_name, model_version, explanation_nl)` (`:75-94`); `TsModelProviderProtocol` (`:97-100`); `TsModelProviderUnavailable(reason, detail_nl)` (`:103-108`). `class AiTsPredictor(*, provider: TsModelProviderProtocol | TsModelProviderUnavailable)` (`:177-296`).

### Collaborators

`HistoricalBar` from `baseline_forecast`; protocol constants + value objects; lazy `backtest_window_score_for_predictor`. **No AI dependency in this package** — actual providers live in `apps/api`.

### Notable choices

- Provider returns `p10_price / p50_price / p90_price / prob_gain / expected_return_pct / confidence_score` directly (`:75-94`); the AI emits a probability distribution that feeds the ensemble (one vote alongside the four deterministic predictors per module docstring `:3-7`).
- Multi-stage validation at the boundary: monotone quantiles `p10 ≤ p50 ≤ p90`; `prob_gain ∈ [0,1]`; `confidence_score ∈ [0,1]`. Violations → `status=blocked` with a structured blocking reason (`:152-174, :246-254`).
- Provider exceptions caught at the boundary (`except Exception as exc: ... reason=BLOCKING_REASON_PROVIDER_ERROR`, `:236-244`).
- `TsModelProviderUnavailable` is a sentinel — when injected, every prediction blocks cleanly with `provider_unavailable` so the ensemble combiner drops the AI vote (`:219-225`).
- `prob_loss` derived as `max(0, 1 - prob_gain)`; the provider isn't asked for it directly (`:256`).

```python
# ai_ts_predictor.py:152-163
def _validate_result(
    result: TsModelProviderResult,
) -> tuple[str, str | None] | None:
    """Return ``(blocking_reason, detail_nl)`` if the provider output
    violates the locked contract, otherwise ``None``."""

    if not (result.p10_price <= result.p50_price <= result.p90_price):
        return (
            BLOCKING_REASON_INVALID_QUANTILES,
            "Provider gaf kwantielen die niet monotoon stijgen "
            "(p10 ≤ p50 ≤ p90).",
        )
```

## `ensemble_combiner.py` — weighted average + agreement factor

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/ensemble_combiner.py`

### Public surface

`ENSEMBLE_MODEL_CODE="ensemble_v1"`, `ENSEMBLE_MODEL_VERSION="v1.0.0"` (`:45-46`); direction thresholds `10.0`/`2.0` (`:49-50`); weight-strategy constants `WEIGHT_STRATEGY_EQUAL="equal_weight"`, `WEIGHT_STRATEGY_AUTO="auto"` (`:54-58`). `EnsembleContribution(model_code, model_version, weight_raw, weight_normalised, prediction)` (`:61-74`); `EnsembleResult(forecast, contributions, blocked_model_codes)` (`:77-83`). `compute_ensemble_forecast(predictors, inputs, *, weights=None, weight_strategy="equal_weight", brier_history=None) -> EnsembleResult` (`:166-331`).

### Collaborators

Direction/status constants + protocol value objects from `predictor_protocol`. Lazy-imports `compute_inverse_brier_weights` from `predictor_feedback` when `weight_strategy="auto"`.

### Notable choices

- Pipeline: (1) call every predictor; (2) drop blocked ones; (3) resolve weights for survivors; (4) weighted average of `p10/p50/p90/prob_gain/expected_return_pct/confidence_score` in float; (5) re-derive direction from combined expected_return_pct via ±2%/±10% (`:207-282`).
- Equal-weight by default. Operator can pass `weights={code: Decimal}`; unknown codes silently ignored; missing or non-positive default to 1.0 (`:225-253`).
- `weight_strategy="auto"`: lazy imports `compute_inverse_brier_weights` (cycle avoidance) and passes surviving codes via `fallback_codes`; auto-weights take precedence over static weights for those codes (`:230-248`).
- Confidence is `base_weighted_confidence × agreement_factor`: 1.0 when all surviving predictors agree on direction (all up or all down); 0.4 when mixed positive+negative; 0.6 otherwise (`_agreement_factor`, `:145-163`, applied at `:278-281`).
- Block sentinels: `no_predictors`, `all_predictors_blocked`, `zero_total_weight` (`:199-263`).

```python
# ensemble_combiner.py:267-275
def _weighted_avg(values: list[Decimal]) -> float:
    return float(
        sum(v * w for v, w in zip(values, norm_weights, strict=True))
    )

p10 = _weighted_avg([p.p10_price for p in ready])
p50 = _weighted_avg([p.p50_price for p in ready])
p90 = _weighted_avg([p.p90_price for p in ready])
prob_gain = _weighted_avg([p.prob_gain for p in ready])
```

## `kelly_sizing.py` — fractional Kelly + risk-parity caps

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/kelly_sizing.py`

### Public surface

`DEFAULT_KELLY_FRACTION: Final[float] = 0.5` (`:51`); `DEFAULT_PER_ASSET_CAP_PCT: Final[float] = 5.0` (`:52`); `DEFAULT_PER_SECTOR_CAP_PCT: Final[float] = 30.0` (`:53`). `KellyInputs(prob_gain, expected_return_pct, downside_loss_pct, kelly_fraction=0.5)` (`:56-63`); `KellyResult(fraction, fraction_raw_kelly, per_asset_cap_hit, per_sector_cap_hit, explanation_nl)` (`:66-74`); `RiskParityInputs(...)` (`:132-139`). Functions: `compute_fractional_kelly_fraction` (`:90-129`); `apply_risk_parity_caps` (`:142-216`); `size_buy_with_kelly` (`:219-256`).

### Collaborators

None — pure stdlib.

### Notable choices

- **Code default is `0.5` (half-Kelly).** `DEFAULT_KELLY_FRACTION = 0.5` (`:51`); module docstring says "fractional Kelly (default ½ Kelly)" (`:4-5`); `compute_fractional_kelly_fraction` docstring says "Return the half-Kelly fraction" (`:97`); test `test_default_kelly_fraction_is_half_kelly` asserts `DEFAULT_KELLY_FRACTION == 0.5` (`test_kelly_sizing.py:117`).
- Kelly formula: classic asymmetric `f* = (p×b − q×L) / (b×L)` (`:118-126`). Returns `Decimal("0.000000")` on any of: `kelly_fraction ≤ 0`, `expected_return_pct ≤ 0`, `downside_loss_pct ≤ 0`, `prob_gain ≤ 0`, denominator ≤ 0, numerator ≤ 0. Module rationale: "Negative-EV bet collapses to 0 — Kelly's estimation risk is real, and we prefer 'do nothing' over 'bet the farm on a noisy edge'." (`:23-25`)
- Caps are deterministic clips that "never raise the Kelly fraction, only ever reduce it." (`:35-39`)
- Per-sector cap is **dynamic**: `per_sector_cap_pct − current_sector_exposure_pct` (clipped at 0). When `current_sector_exposure_pct` is `None`, the per-sector cap is skipped (`:165-174`).
- `size_buy_with_kelly` returns whole shares via `ROUND_DOWN` (`:253`).
- **No conviction-scaling step** inside `kelly_sizing.py`; that step (if applied) lives in the caller.

```python
# kelly_sizing.py:118-129
p = float(prob_gain)
q = max(0.0, 1.0 - p)
b = float(expected_return_pct) / 100.0
L = float(downside_loss_pct) / 100.0
numerator = p * b - q * L
denominator = b * L
if denominator <= 0 or numerator <= 0:
    return Decimal("0.000000")
raw = numerator / denominator
scaled = raw * kelly_fraction
bounded = max(0.0, min(1.0, scaled))
return _decimal_pct(bounded)
```

## `prediction_diary_eval.py` — per-horizon outcome labels

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/prediction_diary_eval.py`

### Public surface

Outcome labels `right`, `wrong`, `inconclusive`, `early`, `no_data` (`:31-35`); `DEFAULT_INCONCLUSIVE_TOLERANCE_PCT = Decimal("0.25")` (`:39`). `HorizonEvaluation(realized_price, realized_return_pct, outcome_label)` (`:42-46`); `DiaryEvaluation(horizon_1d, horizon_1w, horizon_1m, explanation_nl)` (`:49-54`). `evaluate_diary_outcomes(...)` (`:116-175`).

### Collaborators

None — pure stdlib (`Decimal` only).

### Notable choices

- "outcome labels are computed by a pure-Python rule engine — AI never assigns the label." (`:5-7`)
- Three locked horizons: 1d, 1w, 1m. Each evaluated independently — "a 1d horizon can be `no_data` while 1w is `right`." (`:130-132`)
- Per-horizon classification order (`_classify_horizon`, `:63-113`):
  1. `realized_price is None or ≤ 0` → `no_data`
  2. `|return_pct| ≤ inconclusive_tolerance_pct` (default 0.25%) → `inconclusive`
  3. forecast direction (`prob_gain > 0.5`) != realised direction (`return > 0`) → `wrong`
  4. Direction matched: if gain forecast and `realized_price ≥ issued_p50_price` → `right`; else `early`. Mirror for loss.
- `early` is "direction matched but magnitude undershot the p50 target" (`:18-20`).
- The dataclass accepts p10/p90 fields but `_classify_horizon` does not actually use them — only p50.

```python
# prediction_diary_eval.py:99-108
if forecast_gain:
    if realized_price >= issued_p50_price:
        label = OUTCOME_RIGHT
    else:
        label = OUTCOME_EARLY
else:
    if realized_price <= issued_p50_price:
        label = OUTCOME_RIGHT
    else:
        label = OUTCOME_EARLY
```

## Cross-cutting observations

- **Five-predictor ensemble:** GBM (`baseline_gbm`), Momentum (`momentum_v1`), Mean-Reversion (`mean_reversion_v1`), QVM (`qvm_factor_v1`), AI TS (`ai_ts_v1`). All implement `PredictorProtocol`; all four deterministic plus the AI shim implement the optional `PredictorResearchProtocol` via the shared `backtest_window_score_for_predictor` helper. The ensemble combiner's model code is `ensemble_v1`.
- **No block bootstrap anywhere.** GBM is analytic (closed-form quantiles via fixed Z values). Momentum, Mean-Reversion, QVM build distributions as `current × exp(drift + sd × Z)` with the same hard-coded Z values.
- **Decimal at the boundary, float inside.** Every predictor inverts to floats for `math.exp / math.log / math.sqrt / math.erf`, then quantises back to 6-decimal Decimal via `Decimal(str(value)).quantize(Decimal("0.000001"))` (or `Decimal(repr(value))` for GBM). The 6-decimal precision is universal.
- **Hard-coded Z values vs scipy-derived Z values:** `_predictor_math.py:90-92` derives `Z_10` and `Z_90` from `scipy.stats.norm.ppf`, but `baseline_forecast.py`, `momentum_predictor.py`, `mean_reversion_predictor.py`, `qvm_factor_predictor.py`, and `ensemble_combiner.py` all hard-code the literal `1.2815515655446004`. Same value to 16 digits; documentary note only.
- **AI-TS surface receives `p10/p50/p90/prob_gain/expected_return_pct/confidence_score` from the provider** (`ai_ts_predictor.py:75-94`) — i.e. the LLM emits a probability distribution that feeds the ensemble. Module docstring (`ai_ts_predictor.py:3-7`) describes this as "one vote alongside the four deterministic predictors". Validation enforces shape (monotone quantiles, bounded probabilities) and a `TsModelProviderUnavailable` sentinel blocks cleanly when no provider is configured.
- **Determinism enforced everywhere except backtester audit fields:** `_predictor_math.py:10-11` and `predictor_protocol.py:16-19` explicitly forbid `datetime.now()` and randomness inside predictors. The walk-forward harness uses `datetime.now(UTC)` only for the `finished_at` audit timestamp (`predictor_backtester.py:333`), and `new_backtest_run_id` uses `uuid4()` (`:352`).

## Open questions / uncertainty

- `kelly_sizing.DEFAULT_KELLY_FRACTION = 0.5` (`kelly_sizing.py:51`), confirmed by the assertion in `test_kelly_sizing.py:117`. The intent file `docs/intent/_trading-system-doctrine.md` §5.1 specifies "defaulting to 0.25 Kelly". Whether the code default is intentional (and the doctrine is out of date) or vice versa is for Phase 1c gap-analysis to decide — this Phase 1a doc only records the code state.
- The doctrine §5.1 also references a "per-trade risk budget and a system-derived stop-loss level" as the base inputs to Kelly; `kelly_sizing.py`'s signatures use `prob_gain`, `expected_return_pct`, `downside_loss_pct`. Whether `downside_loss_pct` is the system-derived stop-loss level (just with a different name) or a separate concept is out of scope for this doc.
- `ai_ts_predictor.py` is a Case-B-style adapter (LLM emits the distribution that feeds the ensemble) per the three-case framework in `docs/intent/ai-usage.md`. The doctrine's response for Case-B is "remove from the ensemble". The reality here is that the predictor exists and is wired; Phase 1c will assess the gap.
- `compute_per_predictor_outcomes` accepts but discards a `now` parameter (`predictor_feedback.py:134`). Whether this is leftover from an earlier API or intentionally accepted-but-ignored for future use is unclear from the code alone.
- `prediction_diary_eval._classify_horizon` accepts `issued_p10_price` and `issued_p90_price` as arguments but does not use them (`:63-113`). Module docstring at `:15-16` suggests a banded-inconclusive concept that the code doesn't actually implement; tolerance is computed against `inconclusive_tolerance_pct` only.
- `qvm_factor_predictor.py` uses `statistics.pstdev` (population SD) where Momentum / Mean-Reversion use `sample_stdev` (ddof=1). Whether the inconsistency is intentional is unclear without further cross-module reading.
