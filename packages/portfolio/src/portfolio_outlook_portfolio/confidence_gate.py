"""Confidence gate for profit-harvest suggestions (V1.2 §H).

This is the bridge between the existing forecast layer and the
suggestion engine. Once a candidate has cleared the risk-universe
gate (`risk_universe_gate.py`) and produced a forecast, the
confidence gate asks the question that actually matters for the
retiree-income doctrine:

    *"What probability does the model assign to the gross take-
    profit target being hit inside the user's horizon?"*

If that probability is above the user's configured
``confidence_threshold_pct``, the candidate becomes a suggestion;
otherwise it's skipped.

The math fits a lognormal terminal-price distribution to the
forecast's median (``p50_price``) and annualised volatility, then
applies the standard normal CDF to compute ``P(S_T >= K)`` where
``S_T`` is the forecast price at horizon and ``K`` is the gross
take-profit price (``current_price`` × ``(1 + gross_target_pct/100)``).

A few practitioner notes baked into the contract:

* **Belgian TOB is folded in.** The gate computes the *gross* target
  from the user's *net* target via ``profit_harvest`` so the threshold
  comparison is apples-to-apples with the LMT price.
* **Terminal-price distribution, not running-maximum.** A real take-
  profit LMT triggers if the target is touched at *any* point during
  the horizon, which is mathematically a higher probability than the
  forecast's terminal-price ``P(S_T >= K)``. Using the terminal
  probability makes the gate conservative — under-suggest beats over-
  suggest for a retiree.
* **Empirical calibration upstream.** The forecast layer already runs
  a calibration feedback loop (V1.2 §C); the confidence gate inherits
  that honesty automatically by consuming its outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from math import erf, log, sqrt
from typing import Final

from portfolio_outlook_portfolio.belgian_tax import TobSecurityClass
from portfolio_outlook_portfolio.profit_harvest import (
    compute_take_profit_sell_price,
    gross_pct_for_net_target_pct,
)

# Locked blocking reason codes — surfaced in the suggestion audit
# trail and the operator UI. Stable across versions.
BLOCKING_REASON_BELOW_CONFIDENCE: Final[str] = "below_confidence_threshold"
BLOCKING_REASON_INVALID_FORECAST: Final[str] = "invalid_forecast_inputs"
BLOCKING_REASON_ZERO_VOLATILITY: Final[str] = "zero_volatility"

TRADING_DAYS_PER_YEAR: Final[int] = 252
_PCT_QUANT: Final[Decimal] = Decimal("0.01")


@dataclass(frozen=True)
class ConfidenceGateResult:
    """Verdict + diagnostics from one confidence-gate pass.

    ``p_target_hit_pct`` and ``target_price`` are populated on both
    allowed and rejected results so the UI can explain *why* a
    candidate was skipped ("only 58 % probability of hitting €104.73
    within 3-6 months — your threshold is 70 %").
    """

    allowed: bool
    blocking_reason: str | None
    p_target_hit_pct: Decimal
    required_gross_pct: Decimal
    target_price: Decimal


def _normal_cdf(x: float) -> float:
    """Standard normal CDF using ``math.erf``.

    No numpy required at this level; the underlying ``math.erf`` is
    accurate enough (~15 dp) for probability comparisons.
    """

    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def probability_of_target_hit(
    *,
    current_price: Decimal,
    median_forecast_price: Decimal,
    annual_volatility_pct: Decimal,
    horizon_days: int,
    target_price: Decimal,
) -> Decimal | None:
    """Compute the lognormal-implied ``P(S_T >= target_price)``.

    Derivation. Assume terminal log-return is Normal:

        ln(S_T / S_0) ~ N((μ - σ²/2) * T, σ² * T)

    The forecast median price is reached when the log-return equals
    its mean, so ``(μ - σ²/2) * T = ln(p50 / S_0)``. Plug that in:

        P(S_T >= K) = Φ(ln(p50 / K) / (σ * sqrt(T)))

    where Φ is the standard normal CDF.

    Returns ``None`` for any structural problem (non-positive prices,
    zero volatility, non-positive horizon). The caller maps that to
    a specific blocking reason.
    """

    if (
        current_price <= 0
        or median_forecast_price <= 0
        or target_price <= 0
        or annual_volatility_pct <= 0
        or horizon_days <= 0
    ):
        return None
    sigma_annual = float(annual_volatility_pct) / 100.0
    sigma_horizon = sigma_annual * sqrt(horizon_days / TRADING_DAYS_PER_YEAR)
    if sigma_horizon == 0.0:
        return None
    z = log(float(median_forecast_price) / float(target_price)) / sigma_horizon
    p = _normal_cdf(z)
    return (Decimal(repr(p)) * Decimal("100")).quantize(
        _PCT_QUANT, rounding=ROUND_HALF_UP
    )


def evaluate_confidence_gate(
    *,
    current_price: Decimal,
    median_forecast_price: Decimal,
    annual_volatility_pct: Decimal,
    horizon_days: int,
    target_net_pct: Decimal,
    security_class: TobSecurityClass,
    confidence_threshold_pct: Decimal,
) -> ConfidenceGateResult:
    """Decide whether a forecast meets the profit-harvest confidence bar.

    Pipeline:

    1. Convert the user's *net* target to a *gross* target via
       :func:`profit_harvest.gross_pct_for_net_target_pct`, accounting
       for Belgian TOB on both legs of the cycle.
    2. Compute the gross take-profit price via
       :func:`profit_harvest.compute_take_profit_sell_price`.
    3. Fit a lognormal terminal-price distribution to the forecast
       (``median_forecast_price`` + ``annual_volatility_pct``,
       projected over ``horizon_days``).
    4. Compute ``P(S_T >= target_price)`` and compare to the user's
       threshold.

    Args:
        current_price: Spot price of the candidate.
        median_forecast_price: Model's expected median price at the
            horizon (``BaselineForecast.p50_price``).
        annual_volatility_pct: Forecast's annualised vol estimate
            (``BaselineForecast.expected_volatility_annual``).
        horizon_days: Forecast horizon in trading days.
        target_net_pct: User's desired NET return per cycle.
        security_class: Belgian TOB class (drives the gross uplift).
        confidence_threshold_pct: User's minimum probability of hit.

    Returns:
        A :class:`ConfidenceGateResult` with ``allowed=True`` only
        when the computed P(hit) is at or above the threshold.
    """

    for name, value in (
        ("current_price", current_price),
        ("median_forecast_price", median_forecast_price),
        ("annual_volatility_pct", annual_volatility_pct),
        ("target_net_pct", target_net_pct),
        ("confidence_threshold_pct", confidence_threshold_pct),
    ):
        if not isinstance(value, Decimal):
            raise TypeError(f"{name} must be a Decimal")
    if not isinstance(horizon_days, int) or isinstance(horizon_days, bool):
        raise TypeError("horizon_days must be an int")

    # Always compute the gross uplift + target price so the result
    # is informative even on blocked candidates.
    gross_pct = gross_pct_for_net_target_pct(
        target_net_pct=target_net_pct, security_class=security_class
    )
    if current_price <= 0:
        return ConfidenceGateResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_INVALID_FORECAST,
            p_target_hit_pct=Decimal("0.00"),
            required_gross_pct=gross_pct,
            target_price=Decimal("0"),
        )
    target_price = compute_take_profit_sell_price(
        entry_price=current_price,
        target_net_pct=target_net_pct,
        security_class=security_class,
    )

    if (
        median_forecast_price <= 0
        or annual_volatility_pct < 0
        or horizon_days <= 0
    ):
        return ConfidenceGateResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_INVALID_FORECAST,
            p_target_hit_pct=Decimal("0.00"),
            required_gross_pct=gross_pct,
            target_price=target_price,
        )
    if annual_volatility_pct == 0:
        # Flat-history series — refuse without computing. A take-
        # profit on a literally flat asset never triggers.
        return ConfidenceGateResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_ZERO_VOLATILITY,
            p_target_hit_pct=Decimal("0.00"),
            required_gross_pct=gross_pct,
            target_price=target_price,
        )

    p_hit = probability_of_target_hit(
        current_price=current_price,
        median_forecast_price=median_forecast_price,
        annual_volatility_pct=annual_volatility_pct,
        horizon_days=horizon_days,
        target_price=target_price,
    )
    if p_hit is None:
        return ConfidenceGateResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_INVALID_FORECAST,
            p_target_hit_pct=Decimal("0.00"),
            required_gross_pct=gross_pct,
            target_price=target_price,
        )

    if p_hit < confidence_threshold_pct:
        return ConfidenceGateResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_BELOW_CONFIDENCE,
            p_target_hit_pct=p_hit,
            required_gross_pct=gross_pct,
            target_price=target_price,
        )

    return ConfidenceGateResult(
        allowed=True,
        blocking_reason=None,
        p_target_hit_pct=p_hit,
        required_gross_pct=gross_pct,
        target_price=target_price,
    )


__all__ = [
    "BLOCKING_REASON_BELOW_CONFIDENCE",
    "BLOCKING_REASON_INVALID_FORECAST",
    "BLOCKING_REASON_ZERO_VOLATILITY",
    "ConfidenceGateResult",
    "evaluate_confidence_gate",
    "probability_of_target_hit",
]
