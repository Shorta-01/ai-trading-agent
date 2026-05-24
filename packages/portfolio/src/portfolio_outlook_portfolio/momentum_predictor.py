"""Deterministic momentum predictor (Slice 14).

Two locked momentum components:

* **12-1 momentum** — the cumulative return over the trailing 12
  months excluding the most-recent month. Classic academic factor
  (Jegadeesh & Titman 1993; Asness, Moskowitz, Pedersen 2013). Skipping
  the last month removes short-term mean-reversion noise.
* **Time-series momentum (TSM)** — the sign and magnitude of the last
  six-month return divided by the trailing six-month volatility.
  Positive TSM means the asset has been trending up relative to its
  own volatility; negative means trending down. (Moskowitz, Ooi,
  Pedersen 2012.)

The composite **momentum score** is the average of the two normalised
components, clipped to [-1, +1]. We then project a horizon return by
multiplying the score by an annual drift baseline (capped at ±25 %),
construct a Gaussian distribution around the projected price using
trailing volatility, and return a :class:`PredictionDistribution`.

This is pure Python: no SciPy, no datetime.now(). Decimal-only on the
boundary; floats internally for the math (same approach as the GBM
baseline).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from decimal import Decimal
from typing import Final

from .baseline_forecast import (
    DEFAULT_HORIZON_TRADING_DAYS,
    DEFAULT_TRADING_DAYS_PER_YEAR,
    HistoricalBar,
)
from .predictor_protocol import (
    BLOCKING_REASON_FLAT_HISTORY,
    BLOCKING_REASON_INSUFFICIENT_HISTORY,
    BLOCKING_REASON_INVALID_CURRENT_PRICE,
    BLOCKING_REASON_INVALID_HORIZON,
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_DOWN,
    DIRECTION_STRONG_UP,
    STATUS_BLOCKED,
    STATUS_READY,
    PredictionDistribution,
    PredictorInputs,
)

MODEL_CODE: Final[str] = "momentum_v1"
MODEL_VERSION: Final[str] = "v1.0.0"

# Minimum bars required: 12-1 momentum needs ~13 trading months ≈ 273
# trading days. For practical retail use we accept 250 (~12 months).
MOMENTUM_MIN_BARS: Final[int] = 250

# Lookback windows (in trading days; ~21 trading days per month).
TRADING_DAYS_PER_MONTH: Final[int] = 21
LOOKBACK_12M: Final[int] = 12 * TRADING_DAYS_PER_MONTH
LOOKBACK_1M: Final[int] = TRADING_DAYS_PER_MONTH
LOOKBACK_6M: Final[int] = 6 * TRADING_DAYS_PER_MONTH

# Score → annual-drift mapping. A maxed-out (+1) momentum score predicts
# +25 % annualised drift; -1 predicts -25 %. Conservative on purpose so
# the ensemble combiner doesn't get dominated by a single dramatic
# momentum reading.
MAX_ANNUAL_DRIFT_PCT: Final[float] = 25.0


def _decimal(value: float, places: int = 6) -> Decimal:
    quant = Decimal(10) ** -places
    return Decimal(str(value)).quantize(quant)


def _money(value: float) -> Decimal:
    return _decimal(value, 6)


def _prob(value: float) -> Decimal:
    bounded = max(0.0, min(1.0, value))
    return _decimal(bounded, 6)


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _bar_closes(bars: Sequence[HistoricalBar]) -> list[float]:
    return [float(bar.close_price) for bar in bars]


def _log_returns(prices: Sequence[float]) -> list[float]:
    returns: list[float] = []
    for i in range(1, len(prices)):
        prev = prices[i - 1]
        curr = prices[i]
        if prev <= 0 or curr <= 0:
            continue
        returns.append(math.log(curr / prev))
    return returns


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stdev(values: Sequence[float], mean_value: float) -> float:
    if len(values) < 2:
        return 0.0
    variance = sum((v - mean_value) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _direction_label(expected_return_pct: float) -> str:
    if expected_return_pct >= 10.0:
        return DIRECTION_STRONG_UP
    if expected_return_pct >= 2.0:
        return DIRECTION_SLIGHT_UP
    if expected_return_pct > -2.0:
        return DIRECTION_FLAT
    if expected_return_pct > -10.0:
        return DIRECTION_SLIGHT_DOWN
    return DIRECTION_STRONG_DOWN


def _blocked(
    *,
    horizon_trading_days: int,
    current_price: Decimal,
    reason: str,
    explanation_nl: str,
) -> PredictionDistribution:
    safe_horizon = (
        horizon_trading_days
        if horizon_trading_days > 0
        else DEFAULT_HORIZON_TRADING_DAYS
    )
    safe_price = current_price if current_price > 0 else Decimal("0.000001")
    return PredictionDistribution(
        model_code=MODEL_CODE,
        model_version=MODEL_VERSION,
        horizon_trading_days=safe_horizon,
        current_price=safe_price,
        p10_price=safe_price,
        p50_price=safe_price,
        p90_price=safe_price,
        prob_gain=Decimal("0.500000"),
        prob_loss=Decimal("0.500000"),
        expected_return_pct=Decimal("0.000000"),
        direction=DIRECTION_FLAT,
        confidence_score=Decimal("0.000000"),
        status=STATUS_BLOCKED,
        blocking_reason=reason,
        explanation_nl=explanation_nl,
    )


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


def _compute_time_series_momentum(prices: Sequence[float]) -> float | None:
    """Return the 6-month log-return divided by the 6-month volatility.

    This is a unitless signal: positive means the asset is trending up
    relative to its own noise floor; negative means down. Magnitudes
    above ~1 are strong signals.
    """

    if len(prices) <= LOOKBACK_6M:
        return None
    window = prices[-LOOKBACK_6M:]
    returns = _log_returns(window)
    if len(returns) < 2:
        return None
    mean_r = _mean(returns)
    sd_r = _stdev(returns, mean_r)
    if sd_r <= 0:
        return None
    six_month_log_return = math.log(window[-1] / window[0]) if window[0] > 0 else 0.0
    annualisation = math.sqrt(LOOKBACK_6M)
    return six_month_log_return / (sd_r * annualisation)


def _composite_score(twelve_one: float | None, tsm: float | None) -> float:
    """Average the two components, normalising 12-1 by the 25 % cap.

    The 12-1 component is converted from a log-return into a [-1, +1]
    range by dividing by ``log(1 + 0.25)`` (≈ 0.223). TSM is already
    roughly in that range; we clip both to [-1, +1] before averaging.
    Returns ``0.0`` when both inputs are ``None``.
    """

    twelve_one_norm = (
        max(-1.0, min(1.0, twelve_one / math.log(1.25))) if twelve_one is not None else None
    )
    tsm_norm = max(-1.0, min(1.0, tsm)) if tsm is not None else None
    candidates = [v for v in (twelve_one_norm, tsm_norm) if v is not None]
    if not candidates:
        return 0.0
    return sum(candidates) / len(candidates)


def _confidence_from_sample(n: int) -> float:
    """Same bounded heuristic as GBM: 0.4 at the minimum sample,
    asymptotes to 0.85 (slightly lower than GBM since momentum is more
    fragile to regime changes)."""

    if n <= MOMENTUM_MIN_BARS:
        return 0.4
    if n >= DEFAULT_TRADING_DAYS_PER_YEAR * 2:
        return 0.85
    span = DEFAULT_TRADING_DAYS_PER_YEAR * 2 - MOMENTUM_MIN_BARS
    progress = (n - MOMENTUM_MIN_BARS) / span
    return 0.4 + (0.85 - 0.4) * progress


class MomentumPredictor:
    """Deterministic 12-1 + time-series momentum predictor."""

    def __init__(
        self,
        *,
        minimum_bars_required: int = MOMENTUM_MIN_BARS,
        max_annual_drift_pct: float = MAX_ANNUAL_DRIFT_PCT,
        trading_days_per_year: int = DEFAULT_TRADING_DAYS_PER_YEAR,
    ) -> None:
        self._minimum_bars_required = minimum_bars_required
        self._max_annual_drift_pct = max_annual_drift_pct
        self._trading_days_per_year = trading_days_per_year

    @property
    def model_code(self) -> str:
        return MODEL_CODE

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    def predict(self, inputs: PredictorInputs) -> PredictionDistribution:
        horizon = inputs.horizon_trading_days
        if horizon <= 0:
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_INVALID_HORIZON,
                explanation_nl="Horizon moet positief zijn.",
            )
        if inputs.current_price <= 0:
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_INVALID_CURRENT_PRICE,
                explanation_nl="Huidige prijs is niet beschikbaar of <= 0.",
            )
        if len(inputs.historical_bars) < self._minimum_bars_required:
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_INSUFFICIENT_HISTORY,
                explanation_nl=(
                    f"Momentum vereist minstens {self._minimum_bars_required} bars; "
                    f"{len(inputs.historical_bars)} ontvangen."
                ),
            )

        prices = _bar_closes(inputs.historical_bars)
        twelve_one = _compute_12_1_momentum(prices)
        tsm = _compute_time_series_momentum(prices)
        score = _composite_score(twelve_one, tsm)

        # Annualised drift implied by the composite score.
        annual_drift_pct = self._max_annual_drift_pct * score
        annual_drift_log = (
            math.log(1.0 + annual_drift_pct / 100.0)
            if annual_drift_pct > -100.0
            else -1.0
        )
        horizon_drift_log = annual_drift_log * (horizon / self._trading_days_per_year)

        # Use trailing 6-month log-return volatility as our distribution width.
        recent_returns = _log_returns(prices[-LOOKBACK_6M:])
        mean_recent = _mean(recent_returns)
        sd_recent = _stdev(recent_returns, mean_recent)
        if sd_recent <= 0:
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_FLAT_HISTORY,
                explanation_nl=(
                    "Recente prijsreeks heeft geen volatiliteit; momentum kan "
                    "geen distributie afleiden."
                ),
            )
        horizon_sd_log = sd_recent * math.sqrt(horizon)

        current = float(inputs.current_price)
        p10_log = horizon_drift_log + horizon_sd_log * (-1.2815515655446004)
        p50_log = horizon_drift_log
        p90_log = horizon_drift_log + horizon_sd_log * 1.2815515655446004
        p10 = current * math.exp(p10_log)
        p50 = current * math.exp(p50_log)
        p90 = current * math.exp(p90_log)

        # P(end > start) under the lognormal-with-drift assumption.
        z_for_zero = -horizon_drift_log / horizon_sd_log if horizon_sd_log > 0 else 0.0
        prob_gain = 1.0 - _normal_cdf(z_for_zero)
        prob_loss = 1.0 - prob_gain
        expected_return_pct = (math.exp(p50_log) - 1.0) * 100.0
        direction = _direction_label(expected_return_pct)
        confidence = _confidence_from_sample(len(inputs.historical_bars))

        explanation = (
            f"Momentum: composite score {score:.2f} "
            f"(12-1 = {twelve_one:.4f}, TSM = {tsm:.2f}); "
            f"verwachte rendement over {horizon} dagen = {expected_return_pct:.2f}%."
            if twelve_one is not None and tsm is not None
            else f"Momentum: composite score {score:.2f}; "
            f"verwachte rendement over {horizon} dagen = {expected_return_pct:.2f}%."
        )

        return PredictionDistribution(
            model_code=MODEL_CODE,
            model_version=MODEL_VERSION,
            horizon_trading_days=horizon,
            current_price=inputs.current_price,
            p10_price=_money(p10),
            p50_price=_money(p50),
            p90_price=_money(p90),
            prob_gain=_prob(prob_gain),
            prob_loss=_prob(prob_loss),
            expected_return_pct=_decimal(expected_return_pct, 6),
            direction=direction,
            confidence_score=_decimal(confidence, 6),
            status=STATUS_READY,
            blocking_reason=None,
            explanation_nl=explanation,
        )


__all__ = [
    "MODEL_CODE",
    "MODEL_VERSION",
    "MOMENTUM_MIN_BARS",
    "MAX_ANNUAL_DRIFT_PCT",
    "MomentumPredictor",
]
