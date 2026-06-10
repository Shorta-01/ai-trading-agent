"""Pure-Python baseline forecast engine (V1.1 stage, single asset).

Lognormal Geometric-Brownian-Motion (GBM) baseline:

* Sample daily log returns from the provided historical bars.
* Annualize drift (μ) and volatility (σ) using a configurable trading-day count.
* Project forward over the requested horizon (in trading days) and report:
  p10/p50/p90 price quantiles, P(gain) / P(loss), P(loss > 5%) and similar,
  the annualized volatility, a simple downside-risk score and a confidence
  score driven by sample size.

The doctrine in ``docs/product/probabilistic-asset-outlook-doctrine.md`` is
explicit that V1 must never produce a single exact future price as the primary
output. This module is the deterministic, AI-free baseline that satisfies that
contract — model selection from V1.1 in the staged plan
(``docs/product/asset-value-prediction-engine-roadmap.md``).

The code uses ``Decimal`` for prices and ``float`` only for the GBM math
(``exp/log/sqrt/erf`` aren't defined on ``Decimal``); each ``float`` step is
narrow and wrapped back into ``Decimal`` before returning.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

import numpy as np

DEFAULT_TRADING_DAYS_PER_YEAR: Final[int] = 252
DEFAULT_HORIZON_TRADING_DAYS: Final[int] = 21  # ~1 calendar month
MINIMUM_BARS_REQUIRED: Final[int] = 60
MODEL_CODE: Final[str] = "baseline_gbm"
MODEL_VERSION: Final[str] = "v1.0.0"

# V1.1 Slice 27 rebuild constants.
#
# The Slice 22 audit identified that V1 GBM averages drift over the
# entire bar window — a 1-year history straddling a regime change
# gives a drift that fits neither half. The rebuild adds two opt-in
# behaviours kept off by default until the Slice 25 backtest +
# Slice 26 auto-weighting confirm the lift on real data:
#
# * ``drift_window_days`` caps the drift-estimation window (sigma
#   still uses the full series).
# * ``regime_shift_enabled`` blends the long-window drift with the
#   recent 60-day drift when the two diverge by more than
#   ``regime_shift_threshold_pct``.
DEFAULT_DRIFT_WINDOW_DAYS_V1_1: Final[int] = 252
DEFAULT_REGIME_SHIFT_SHORT_WINDOW: Final[int] = 60
DEFAULT_REGIME_SHIFT_THRESHOLD_PCT: Final[float] = 5.0

# V1.2 §A — RiskMetrics EWMA volatility. ``lambda=0.94`` is the
# JP Morgan RiskMetrics 1996 standard for daily equity returns
# (half-life ≈ 23 trading days). The forecast bands track regime
# changes ~10x faster than the constant full-history sample SD while
# still smoothing single-day noise. Conservative default OFF; operator
# opts in via ``volatility_method="ewma"``.
VOLATILITY_METHOD_SAMPLE_SD: Final[str] = "sample_sd"
VOLATILITY_METHOD_EWMA: Final[str] = "ewma"
DEFAULT_VOLATILITY_METHOD: Final[str] = VOLATILITY_METHOD_SAMPLE_SD
DEFAULT_EWMA_LAMBDA: Final[float] = 0.94
EWMA_LAMBDA_MIN: Final[float] = 0.80
EWMA_LAMBDA_MAX: Final[float] = 0.99

# V1.2 §B — James-Stein / Bayesian drift shrinkage. The sample mean
# of daily log-returns has a standard error so large (σ/√n) that the
# point estimate is mostly noise — a well-known result going back to
# Merton 1980. Shrinking the estimate toward 0 (or a prior) produces
# better out-of-sample calibration. ``shrinkage_factor=0.0`` keeps the
# V1 raw-mean behaviour; ``1.0`` zeroes the drift entirely; a
# practitioner default of 0.7 is recommended once empirical Brier
# scores stabilise.
DEFAULT_DRIFT_SHRINKAGE_FACTOR: Final[float] = 0.0
DRIFT_SHRINKAGE_MIN: Final[float] = 0.0
DRIFT_SHRINKAGE_MAX: Final[float] = 1.0

# Standard-normal quantiles used for p10/p50/p90 — stable constants so the
# math doesn't need an inverse-erf implementation.
Z_10: Final[float] = -1.2815515655446004
Z_50: Final[float] = 0.0
Z_90: Final[float] = 1.2815515655446004

# V1.2 §C — Calibration feedback (conformal-prediction-lite).
# The forecast bands are scaled by an empirical factor read from the
# calibration diary's rolling p10-p90 coverage. If observed coverage is
# below the 80% target, σ is multiplied by the ratio of target-Z to
# observed-Z so the next round's bands honestly cover ~80%. Bounded so a
# single bad lookback can't make σ blow up or collapse the band.
DEFAULT_BAND_SCALE_FACTOR: Final[float] = 1.0
BAND_SCALE_MIN: Final[float] = 0.5  # bands narrower than half = ignore
BAND_SCALE_MAX: Final[float] = 2.0  # bands wider than 2x = ignore
DEFAULT_CALIBRATION_TARGET_COVERAGE: Final[float] = 0.80
CALIBRATION_MIN_SAMPLE_SIZE: Final[int] = 30


@dataclass(frozen=True)
class HistoricalBar:
    """Inputs to the forecaster. ``close_price`` is the value used for the
    log-return calculation."""

    bar_date: date
    close_price: Decimal


@dataclass(frozen=True)
class BaselineForecast:
    """Result of one forecast run for one asset."""

    horizon_days: int
    data_points_used: int
    history_first_bar_date: date | None
    history_last_bar_date: date | None
    current_price: Decimal
    expected_return_pct: Decimal
    p10_price: Decimal
    p50_price: Decimal
    p90_price: Decimal
    prob_gain: Decimal
    prob_loss: Decimal
    prob_loss_gt_5pct: Decimal
    prob_loss_gt_10pct: Decimal
    prob_gain_gt_5pct: Decimal
    prob_gain_gt_10pct: Decimal
    expected_volatility_annual: Decimal
    downside_risk_score: Decimal
    confidence_score: Decimal
    direction_label: str
    direction_label_nl: str
    explanation_nl: str
    status: str
    blocking_reason: str | None
    model_code: str = MODEL_CODE
    model_version: str = MODEL_VERSION


def _decimal(value: float, places: int = 6) -> Decimal:
    """Round a float to a deterministic Decimal at ``places`` precision."""

    quant = Decimal(1).scaleb(-places)
    return Decimal(repr(value)).quantize(quant, rounding=ROUND_HALF_UP)


def _money(value: float) -> Decimal:
    return _decimal(value, places=6)


def _prob(value: float) -> Decimal:
    """Clamp a float to [0,1] and quantize to 6 decimals."""

    if value < 0.0:
        clamped = 0.0
    elif value > 1.0:
        clamped = 1.0
    else:
        clamped = value
    return _decimal(clamped, places=6)


def _normal_cdf(z: float) -> float:
    """Standard-normal CDF using ``math.erf``."""

    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _log_returns(bars: Sequence[HistoricalBar]) -> list[float]:
    """Compute daily log returns from a chronologically sorted bar series.

    V1.1 §22.1 refactor: numpy-backed under the hood via
    ``_predictor_math.log_returns``. Returns an empty list when any
    bar in the series has a non-positive close (the GBM math then
    surfaces ``invalid_bar_price``).
    """

    from . import _predictor_math as _pm

    if len(bars) < 2:
        return []
    closes = _pm.bar_closes_array(bars)
    if closes.size == 0 or (closes <= 0).any():
        return []
    return list(_pm.log_returns(closes))


def _sample_mean(values: Sequence[float]) -> float:
    """V1.1 §22.1 refactor: numpy-backed mean."""

    from . import _predictor_math as _pm

    return _pm.sample_mean(np.asarray(values, dtype=np.float64))


def _sample_stdev(values: Sequence[float], mean: float) -> float:
    """Sample standard deviation (Bessel-corrected). Returns 0.0 for n < 2.

    V1.1 §22.1 refactor: numpy-backed via ``_predictor_math.sample_stdev``.
    The ``mean`` argument is retained for backward signature compatibility
    but is recomputed inside numpy; explicit precomputed means won't drift
    from the recomputed one for normal inputs.
    """

    from . import _predictor_math as _pm

    return _pm.sample_stdev(np.asarray(values, dtype=np.float64))


def _ewma_stdev(values: Sequence[float], lam: float) -> float:
    """RiskMetrics 1996 exponentially-weighted volatility.

    Recursion: ``σ²_t = λ · σ²_{t-1} + (1 - λ) · r²_t``.

    Anchors ``σ²_0`` on the variance of the first ``warmup`` observations
    (default 30) so a short series doesn't start at zero and one-shot
    the recursion. Standard practitioner choice — matches what the
    RiskMetrics technical document specifies for "small sample bias
    correction at the start of the series."

    Returns the *terminal* daily SD: the most recent λ-weighted estimate,
    which is what a one-month-horizon forecast wants as σ_today.

    Returns 0.0 for ``len(values) < 2``. For ``len < warmup`` falls back
    to plain sample SD.
    """

    n = len(values)
    if n < 2:
        return 0.0
    if not EWMA_LAMBDA_MIN <= lam <= EWMA_LAMBDA_MAX:
        raise ValueError(
            f"EWMA lambda {lam} outside [{EWMA_LAMBDA_MIN}, {EWMA_LAMBDA_MAX}]."
        )
    warmup = min(30, max(2, n // 2))
    # Need ≥10 observations AFTER the warmup window for the recursion
    # to mean anything; otherwise the EWMA is anchored variance with
    # one or two updates, which is just noise around the warmup mean.
    # Degrade to sample SD so the forecast still produces a band.
    if n - warmup < 10:
        return _sample_stdev(values, _sample_mean(values))
    # Anchor variance on the warmup window's mean-centred variance.
    warmup_slice = values[:warmup]
    warmup_mean = _sample_mean(warmup_slice)
    var_t = sum((r - warmup_mean) ** 2 for r in warmup_slice) / float(warmup)
    # Roll the recursion forward over the remaining observations.
    one_minus_lam = 1.0 - lam
    for r in values[warmup:]:
        var_t = lam * var_t + one_minus_lam * (r * r)
    if var_t <= 0.0:
        return 0.0
    return math.sqrt(var_t)


def _empirical_band_scale_factor(
    *,
    observed_coverage: float,
    target_coverage: float = DEFAULT_CALIBRATION_TARGET_COVERAGE,
) -> float:
    """Compute the σ-multiplier that makes the next band honestly cover
    ``target_coverage`` based on what actually happened.

    Derivation: under GBM the band ``[p10, p90]`` corresponds to log-
    returns in ``[μ - 1.2816σ, μ + 1.2816σ]``. If the empirical fraction
    of realised log-returns inside that interval is ``c``, then the
    *empirical* z-score that covers ``c`` of the realised distribution
    is ``Φ⁻¹((1+c)/2)`` (the symmetric two-sided quantile). To make the
    next band cover ``target_coverage``, scale σ by ``z_target /
    z_observed``.

    Concrete examples (target = 0.80, z_target = 1.2816):
    - observed = 0.65 (bands too narrow) → z_observed ≈ 0.935 →
      scale ≈ 1.37 (widen by 37%)
    - observed = 0.80 (perfectly calibrated) → scale = 1.0
    - observed = 0.92 (bands too wide) → z_observed ≈ 1.751 →
      scale ≈ 0.73 (narrow by 27%)

    Clamped to ``[BAND_SCALE_MIN, BAND_SCALE_MAX]`` so a single bad
    lookback (e.g. 1/30 inside the band) can't blow up σ to infinity.
    Returns 1.0 (no scaling) for non-finite or out-of-range observed
    coverage — the caller's job to handle "insufficient sample size"
    before calling this.
    """

    if not 0.0 < observed_coverage < 1.0:
        # observed = 0% or 100% are degenerate (Φ⁻¹ undefined / infinite)
        return 1.0
    if not 0.0 < target_coverage < 1.0:
        raise ValueError(
            f"target_coverage {target_coverage} must be in (0, 1)."
        )

    # Two-sided symmetric quantile: P(|Z| ≤ z) = c  ⇔  z = Φ⁻¹((1+c)/2)
    # Inverse standard-normal CDF via the rational approximation used
    # downstream — no external dependencies.
    z_target = _inverse_standard_normal_cdf((1.0 + target_coverage) / 2.0)
    z_observed = _inverse_standard_normal_cdf((1.0 + observed_coverage) / 2.0)
    if z_observed <= 0.0:
        return 1.0
    raw_scale = z_target / z_observed
    return max(BAND_SCALE_MIN, min(BAND_SCALE_MAX, raw_scale))


def _inverse_standard_normal_cdf(p: float) -> float:
    """Beasley-Springer-Moro inverse standard normal CDF (Φ⁻¹).

    Standard rational approximation; |error| < 5e-7 over (0, 1).
    Picked over scipy/statistics dependency so the portfolio package
    stays leaf-pure (no SciPy, no statistics.NormalDist for symmetry
    with the rest of the math here).
    """

    if not 0.0 < p < 1.0:
        raise ValueError(f"Φ⁻¹ argument {p} must be in (0, 1).")
    # Beasley-Springer-Moro coefficients.
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    p_low = 0.02425
    p_high = 1.0 - p_low
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if p > p_high:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(
            ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        ) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    q = p - 0.5
    r = q * q
    return (
        ((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]
    ) * q / (
        ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
    )


def _shrink_drift(raw_mu_annual: float, shrinkage_factor: float) -> float:
    """Apply Bayesian/James-Stein shrinkage to the annualised drift.

    Linear interpolation toward zero:
    ``μ_shrunk = (1 - α) · μ_raw + α · 0 = (1 - α) · μ_raw``.

    Doctrine: the sample mean of daily log-returns has standard error
    σ/√n which dominates the estimate at any practical lookback. A
    rational shrinkage prior is "monthly drift is zero" — the no-skill
    null — which produces calibrated forecasts when n is small.
    Shrinkage factor 0.0 preserves V1 behaviour; 1.0 zeroes the drift
    entirely (pure variance forecast, no directional view).
    """

    if not DRIFT_SHRINKAGE_MIN <= shrinkage_factor <= DRIFT_SHRINKAGE_MAX:
        raise ValueError(
            f"Drift shrinkage {shrinkage_factor} outside "
            f"[{DRIFT_SHRINKAGE_MIN}, {DRIFT_SHRINKAGE_MAX}]."
        )
    return (1.0 - shrinkage_factor) * raw_mu_annual


# Risk-adjusted (horizon-Sharpe) thresholds — the units are "standard
# deviations of horizon-volatility from zero." See
# ``_direction_label_sharpe`` below for the derivation.
#
# A Sharpe of 1.0 means the expected return sits one standard deviation
# above zero, which under a Brownian assumption corresponds to ~84%
# probability the realised return is positive — a defensible
# "strong_up" bar. 0.3 corresponds to ~62% — the lowest defensible
# "slight" bucket. These are the defaults; callers can override via the
# ``sharpe_*_threshold`` kwargs threaded through ``compute_baseline_forecast``.
DEFAULT_SHARPE_STRONG_THRESHOLD: float = 1.0
DEFAULT_SHARPE_SLIGHT_THRESHOLD: float = 0.3
_SHARPE_STRONG_THRESHOLD: float = DEFAULT_SHARPE_STRONG_THRESHOLD
_SHARPE_SLIGHT_THRESHOLD: float = DEFAULT_SHARPE_SLIGHT_THRESHOLD

# Absolute-return fallback thresholds (legacy). Used only when
# horizon-volatility is unavailable. Same numbers as V1 for back-compat.
_ABS_STRONG_THRESHOLD: float = 10.0
_ABS_SLIGHT_THRESHOLD: float = 2.0


def _direction_label(
    expected_return_pct: float,
    *,
    vol_annual: float | None = None,
    horizon_days: int | None = None,
    sharpe_strong_threshold: float = DEFAULT_SHARPE_STRONG_THRESHOLD,
    sharpe_slight_threshold: float = DEFAULT_SHARPE_SLIGHT_THRESHOLD,
) -> tuple[str, str]:
    """Translate the expected return into a Dutch direction label.

    When both ``vol_annual`` (decimal, e.g. 0.20 = 20%/yr) and
    ``horizon_days`` are provided this uses a **risk-adjusted Sharpe**
    threshold via :func:`_direction_label_sharpe`. Otherwise (legacy
    callers / tests with no volatility) it falls back to the V1 fixed
    absolute-return thresholds (±2% / ±10%).

    The Sharpe path is the right one for production: a 10%-expected
    return on a 5%-vol utility is materially different from a
    10%-expected return on a 60%-vol small-cap. The fixed thresholds
    treated them identically.
    """

    if (
        vol_annual is not None
        and vol_annual > 0.0
        and horizon_days is not None
        and horizon_days > 0
    ):
        return _direction_label_sharpe(
            expected_return_pct=expected_return_pct,
            vol_annual=vol_annual,
            horizon_days=horizon_days,
            sharpe_strong_threshold=sharpe_strong_threshold,
            sharpe_slight_threshold=sharpe_slight_threshold,
        )

    if expected_return_pct >= _ABS_STRONG_THRESHOLD:
        return "strong_up", "Sterke stijging verwacht"
    if expected_return_pct >= _ABS_SLIGHT_THRESHOLD:
        return "slight_up", "Lichte stijging verwacht"
    if expected_return_pct > -_ABS_SLIGHT_THRESHOLD:
        return "neutral", "Geen duidelijke richting"
    if expected_return_pct > -_ABS_STRONG_THRESHOLD:
        return "slight_down", "Lichte daling verwacht"
    return "strong_down", "Duidelijke daling verwacht"


def _direction_label_sharpe(
    *,
    expected_return_pct: float,
    vol_annual: float,
    horizon_days: int,
    sharpe_strong_threshold: float = DEFAULT_SHARPE_STRONG_THRESHOLD,
    sharpe_slight_threshold: float = DEFAULT_SHARPE_SLIGHT_THRESHOLD,
) -> tuple[str, str]:
    """Risk-adjusted direction label (Sharpe over the forecast horizon).

    Derivation:
      vol_h_pct = vol_annual * 100 * sqrt(horizon_days / 252)
                  (annual vol scaled to the horizon, expressed as %)
      sharpe_h  = expected_return_pct / vol_h_pct
                  ("standard deviations of horizon-vol from zero")

    Reads as: how confident can the model really be that the move is
    in the predicted direction, accounting for the asset's own
    volatility? A 5%-return forecast on a 5%-vol asset is strong
    evidence; the same 5% on a 30%-vol asset is just noise.
    """

    vol_h_pct = vol_annual * 100.0 * math.sqrt(horizon_days / 252.0)
    if vol_h_pct <= 0.0:
        # Degenerate input — fall back to absolute thresholds.
        return _direction_label(expected_return_pct)
    sharpe = expected_return_pct / vol_h_pct
    if sharpe >= sharpe_strong_threshold:
        return "strong_up", "Sterke stijging verwacht (risico-gecorrigeerd)"
    if sharpe >= sharpe_slight_threshold:
        return "slight_up", "Lichte stijging verwacht (risico-gecorrigeerd)"
    if sharpe > -sharpe_slight_threshold:
        return "neutral", "Geen duidelijke richting (risico-gecorrigeerd)"
    if sharpe > -sharpe_strong_threshold:
        return "slight_down", "Lichte daling verwacht (risico-gecorrigeerd)"
    return "strong_down", "Duidelijke daling verwacht (risico-gecorrigeerd)"


def _confidence_from_sample_size(n: int) -> float:
    """Bounded confidence score: 0.4 at the minimum sample, asymptotes to 0.95
    at one year, capped there. Purely a heuristic — communicates "more bars,
    more confidence" without overclaiming."""

    if n <= MINIMUM_BARS_REQUIRED:
        return 0.40
    if n >= DEFAULT_TRADING_DAYS_PER_YEAR:
        return 0.95
    span = DEFAULT_TRADING_DAYS_PER_YEAR - MINIMUM_BARS_REQUIRED
    progress = (n - MINIMUM_BARS_REQUIRED) / span
    return 0.40 + 0.55 * progress


def _blocked_forecast(
    *,
    current_price: Decimal,
    horizon_days: int,
    bars: Sequence[HistoricalBar],
    reason: str,
    explanation_nl: str,
) -> BaselineForecast:
    first = bars[0].bar_date if bars else None
    last = bars[-1].bar_date if bars else None
    zero = Decimal("0.000000")
    return BaselineForecast(
        horizon_days=horizon_days,
        data_points_used=len(bars),
        history_first_bar_date=first,
        history_last_bar_date=last,
        current_price=current_price,
        expected_return_pct=zero,
        p10_price=current_price,
        p50_price=current_price,
        p90_price=current_price,
        prob_gain=zero,
        prob_loss=zero,
        prob_loss_gt_5pct=zero,
        prob_loss_gt_10pct=zero,
        prob_gain_gt_5pct=zero,
        prob_gain_gt_10pct=zero,
        expected_volatility_annual=zero,
        downside_risk_score=zero,
        confidence_score=zero,
        direction_label="blocked",
        direction_label_nl="Geblokkeerd",
        explanation_nl=explanation_nl,
        status="blocked",
        blocking_reason=reason,
    )


def _annualised_drift_with_regime_blend(
    returns: list[float],
    *,
    short_window: int,
    threshold_pct: float,
    trading_days_per_year: int,
) -> tuple[float, str]:
    """Blend the long-window drift with a short-window drift when the
    two diverge by more than ``threshold_pct`` annualised.

    Returns ``(annualised_drift, explanation_clause)``. When the
    series is shorter than ``short_window`` or the divergence is
    below the threshold, returns the long-window drift unchanged.

    The blend is a simple 50/50 mean of the two windows when the
    regime-shift trigger fires. The 50/50 weight is the conservative
    middle-ground that responds to recent regime changes without
    over-fitting a noisy 60-day window.
    """

    long_mu_daily = _sample_mean(returns)
    long_annual = long_mu_daily * trading_days_per_year
    if len(returns) <= short_window:
        return long_annual, ""
    recent = returns[-short_window:]
    short_mu_daily = _sample_mean(recent)
    short_annual = short_mu_daily * trading_days_per_year
    divergence_pct = abs(short_annual - long_annual) * 100.0
    if divergence_pct < threshold_pct:
        return long_annual, (
            f" Regime-shift detector inactief (divergentie "
            f"{divergence_pct:.2f}% < drempel {threshold_pct:.2f}%)."
        )
    blended = 0.5 * (long_annual + short_annual)
    return blended, (
        f" Regime-shift blend actief: 60d drift "
        f"{short_annual * 100:.2f}%/jaar vs lang {long_annual * 100:.2f}%/jaar; "
        f"50/50 blend → {blended * 100:.2f}%/jaar."
    )


def compute_baseline_forecast(
    *,
    bars: Sequence[HistoricalBar],
    current_price: Decimal,
    horizon_trading_days: int = DEFAULT_HORIZON_TRADING_DAYS,
    trading_days_per_year: int = DEFAULT_TRADING_DAYS_PER_YEAR,
    minimum_bars_required: int = MINIMUM_BARS_REQUIRED,
    drift_window_days: int | None = None,
    regime_shift_enabled: bool = False,
    regime_shift_threshold_pct: float = DEFAULT_REGIME_SHIFT_THRESHOLD_PCT,
    garch_enabled: bool = False,
    sharpe_strong_threshold: float = DEFAULT_SHARPE_STRONG_THRESHOLD,
    sharpe_slight_threshold: float = DEFAULT_SHARPE_SLIGHT_THRESHOLD,
    volatility_method: str = DEFAULT_VOLATILITY_METHOD,
    ewma_lambda: float = DEFAULT_EWMA_LAMBDA,
    drift_shrinkage_factor: float = DEFAULT_DRIFT_SHRINKAGE_FACTOR,
    band_scale_factor: float = DEFAULT_BAND_SCALE_FACTOR,
) -> BaselineForecast:
    """Compute a baseline GBM forecast or return a blocked result.

    Blocking conditions (each maps to a deterministic ``blocking_reason``):

    * ``current_price <= 0`` → ``"invalid_current_price"``
    * ``len(bars) < minimum_bars_required`` → ``"insufficient_history"``
    * ``horizon_trading_days <= 0`` → ``"invalid_horizon"``
    * any non-positive close in the series → ``"invalid_bar_price"``
    * computed volatility ``== 0`` → ``"zero_volatility"`` (a flat series
      can't be projected as a distribution; we refuse rather than fake one)
    """

    if horizon_trading_days <= 0:
        return _blocked_forecast(
            current_price=current_price,
            horizon_days=max(horizon_trading_days, 0),
            bars=bars,
            reason="invalid_horizon",
            explanation_nl="Ongeldige voorspellingshorizon.",
        )
    if current_price <= 0:
        return _blocked_forecast(
            current_price=current_price,
            horizon_days=horizon_trading_days,
            bars=bars,
            reason="invalid_current_price",
            explanation_nl="Huidige prijs ontbreekt of is niet positief.",
        )
    if len(bars) < minimum_bars_required:
        return _blocked_forecast(
            current_price=current_price,
            horizon_days=horizon_trading_days,
            bars=bars,
            reason="insufficient_history",
            explanation_nl=(
                f"Minimaal {minimum_bars_required} historische bars vereist; "
                f"slechts {len(bars)} aanwezig."
            ),
        )

    returns = _log_returns(bars)
    if not returns:
        return _blocked_forecast(
            current_price=current_price,
            horizon_days=horizon_trading_days,
            bars=bars,
            reason="invalid_bar_price",
            explanation_nl="Historische bar bevat ongeldige prijs.",
        )

    # V1.1 §22.5: GARCH(1,1) volatility wiring is intentionally
    # deferred — the setting is declared so the operator surface is
    # stable from Slice 27 onward, but the real GARCH path lands
    # alongside Slice 28's QVM rebuild once Slice 25 backtests have
    # measured the existing baseline.
    if garch_enabled:
        raise NotImplementedError(
            "garch_enabled volatility is reserved for a follow-up slice; "
            "the setting is declared from Slice 27 but the implementation "
            "lands later."
        )

    # V1.1 Slice 27 rebuild: drift estimation can be confined to the
    # most recent ``drift_window_days`` bars. Volatility (sigma)
    # always uses the full series so the distribution width keeps the
    # benefit of the longer sample.
    #
    # V1.2 §A: when ``volatility_method="ewma"`` the constant
    # full-history sample SD is replaced by RiskMetrics EWMA. The
    # forecast bands then track regime changes ~10x faster, which
    # produces materially better calibrated p10/p90 coverage after
    # vol expansions (March 2020, Q4 2018, etc.). Default sample_sd
    # preserves V1 behaviour.
    if volatility_method == VOLATILITY_METHOD_EWMA:
        sigma_daily = _ewma_stdev(returns, ewma_lambda)
        sigma_clause = (
            f" Volatility: EWMA λ={ewma_lambda:.2f} (V1.2 §A)."
        )
    elif volatility_method == VOLATILITY_METHOD_SAMPLE_SD:
        sigma_daily = _sample_stdev(returns, _sample_mean(returns))
        sigma_clause = ""
    else:
        raise ValueError(
            f"Unknown volatility_method {volatility_method!r}; "
            f"expected one of {VOLATILITY_METHOD_SAMPLE_SD!r}, "
            f"{VOLATILITY_METHOD_EWMA!r}."
        )
    if sigma_daily <= 0.0:
        return _blocked_forecast(
            current_price=current_price,
            horizon_days=horizon_trading_days,
            bars=bars,
            reason="zero_volatility",
            explanation_nl=(
                "Historische volatiliteit is nul; baseline-voorspelling kan "
                "geen verdeling produceren."
            ),
        )

    drift_returns = returns
    drift_clause = ""
    if drift_window_days is not None and len(returns) > drift_window_days:
        drift_returns = returns[-drift_window_days:]
        drift_clause = (
            f" Drift-window: laatste {drift_window_days} bars (V1.1 §22.5)."
        )

    if regime_shift_enabled:
        mu_annual, regime_clause = _annualised_drift_with_regime_blend(
            drift_returns,
            short_window=DEFAULT_REGIME_SHIFT_SHORT_WINDOW,
            threshold_pct=regime_shift_threshold_pct,
            trading_days_per_year=trading_days_per_year,
        )
        drift_clause += regime_clause
    else:
        mu_annual = _sample_mean(drift_returns) * trading_days_per_year

    # V1.2 §B: Bayesian/James-Stein drift shrinkage toward zero.
    # ``μ_shrunk = (1 - α) · μ_raw``. The sample mean's standard error
    # σ/√n dominates the estimate at any practical lookback, so a
    # rational prior is "monthly drift is zero" and the operator
    # interpolates between raw estimate (α=0, V1 behaviour) and the
    # no-skill null (α=1). Applied AFTER regime-shift so a regime-blend
    # operator opting in still gets a calibrated point estimate.
    if drift_shrinkage_factor > 0.0:
        raw_mu_annual = mu_annual
        mu_annual = _shrink_drift(raw_mu_annual, drift_shrinkage_factor)
        drift_clause += (
            f" Shrinkage α={drift_shrinkage_factor:.2f} "
            f"({raw_mu_annual * 100:.2f}% → {mu_annual * 100:.2f}%, V1.2 §B)."
        )
    drift_clause += sigma_clause

    horizon_years = horizon_trading_days / float(trading_days_per_year)
    sigma_annual = sigma_daily * math.sqrt(trading_days_per_year)

    # V1.2 §C: empirical band scaling from the calibration diary.
    # band_scale_factor = 1.0 (default) preserves V1 behaviour. A value
    # > 1.0 widens the band (issued bands historically too narrow);
    # < 1.0 narrows it (historically too wide). Clamped to
    # [BAND_SCALE_MIN, BAND_SCALE_MAX] at the call site so a degenerate
    # calibration history can't blow up σ. The Itô correction inside
    # drift_log uses the UNSCALED sigma_annual because the correction
    # is a property of the physical process, not the operator's
    # uncertainty about it — scaling it would double-count the
    # calibration adjustment.
    if not BAND_SCALE_MIN <= band_scale_factor <= BAND_SCALE_MAX:
        raise ValueError(
            f"band_scale_factor {band_scale_factor} outside "
            f"[{BAND_SCALE_MIN}, {BAND_SCALE_MAX}]."
        )
    scaled_sigma_annual = sigma_annual * band_scale_factor

    s0 = float(current_price)
    drift_log = (mu_annual - 0.5 * sigma_annual**2) * horizon_years
    diffusion_log = scaled_sigma_annual * math.sqrt(horizon_years)

    p10 = s0 * math.exp(drift_log + diffusion_log * Z_10)
    p50 = s0 * math.exp(drift_log + diffusion_log * Z_50)
    p90 = s0 * math.exp(drift_log + diffusion_log * Z_90)
    expected_return_pct = (math.exp(drift_log) - 1.0) * 100.0

    # Probability mass under GBM: ln(S_T / S_0) ~ N(drift_log, diffusion_log^2).
    def _prob_below_ratio(ratio: float) -> float:
        z = (math.log(ratio) - drift_log) / diffusion_log
        return _normal_cdf(z)

    prob_loss = _prob_below_ratio(1.0)
    prob_gain = 1.0 - prob_loss
    prob_loss_gt_5pct = _prob_below_ratio(0.95)
    prob_loss_gt_10pct = _prob_below_ratio(0.90)
    prob_gain_gt_5pct = 1.0 - _prob_below_ratio(1.05)
    prob_gain_gt_10pct = 1.0 - _prob_below_ratio(1.10)

    # Downside risk score: percentage drawdown to the p10 level vs current.
    downside_risk = max(0.0, (s0 - p10) / s0) * 100.0
    confidence = _confidence_from_sample_size(len(returns))
    label, label_nl = _direction_label(
        expected_return_pct,
        vol_annual=sigma_annual,
        horizon_days=horizon_trading_days,
        sharpe_strong_threshold=sharpe_strong_threshold,
        sharpe_slight_threshold=sharpe_slight_threshold,
    )

    explanation_nl = (
        f"Baseline GBM op {len(returns)} dagrendementen: drift "
        f"{mu_annual * 100:.2f}%/jaar, volatiliteit "
        f"{sigma_annual * 100:.2f}%/jaar; horizon {horizon_trading_days} "
        f"handelsdagen.{drift_clause} Geen suggesties of orders gegenereerd."
    )

    return BaselineForecast(
        horizon_days=horizon_trading_days,
        data_points_used=len(returns),
        history_first_bar_date=bars[0].bar_date,
        history_last_bar_date=bars[-1].bar_date,
        current_price=current_price,
        expected_return_pct=_decimal(expected_return_pct, places=6),
        p10_price=_money(p10),
        p50_price=_money(p50),
        p90_price=_money(p90),
        prob_gain=_prob(prob_gain),
        prob_loss=_prob(prob_loss),
        prob_loss_gt_5pct=_prob(prob_loss_gt_5pct),
        prob_loss_gt_10pct=_prob(prob_loss_gt_10pct),
        prob_gain_gt_5pct=_prob(prob_gain_gt_5pct),
        prob_gain_gt_10pct=_prob(prob_gain_gt_10pct),
        expected_volatility_annual=_decimal(sigma_annual, places=6),
        downside_risk_score=_decimal(downside_risk, places=6),
        confidence_score=_decimal(confidence, places=6),
        direction_label=label,
        direction_label_nl=label_nl,
        explanation_nl=explanation_nl,
        status="ready",
        blocking_reason=None,
    )
