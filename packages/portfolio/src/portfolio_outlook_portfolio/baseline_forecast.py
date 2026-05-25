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

# Standard-normal quantiles used for p10/p50/p90 — stable constants so the
# math doesn't need an inverse-erf implementation.
Z_10: Final[float] = -1.2815515655446004
Z_50: Final[float] = 0.0
Z_90: Final[float] = 1.2815515655446004


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


def _direction_label(expected_return_pct: float) -> tuple[str, str]:
    """Translate the expected log-return drift over the horizon to a Dutch
    direction label.

    Thresholds are deliberately conservative — the doctrine forbids
    overconfident headlines. Anything between ``-2%`` and ``+2%`` is neutral.
    """

    if expected_return_pct >= 10.0:
        return "strong_up", "Sterke stijging verwacht"
    if expected_return_pct >= 2.0:
        return "slight_up", "Lichte stijging verwacht"
    if expected_return_pct > -2.0:
        return "neutral", "Geen duidelijke richting"
    if expected_return_pct > -10.0:
        return "slight_down", "Lichte daling verwacht"
    return "strong_down", "Duidelijke daling verwacht"


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
    sigma_daily = _sample_stdev(returns, _sample_mean(returns))
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

    horizon_years = horizon_trading_days / float(trading_days_per_year)
    sigma_annual = sigma_daily * math.sqrt(trading_days_per_year)

    s0 = float(current_price)
    drift_log = (mu_annual - 0.5 * sigma_annual**2) * horizon_years
    diffusion_log = sigma_annual * math.sqrt(horizon_years)

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
    label, label_nl = _direction_label(expected_return_pct)

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
