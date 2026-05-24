"""Deterministic mean-reversion predictor (Slice 15).

Three classical mean-reversion signals combined deterministically:

* **RSI (Relative Strength Index, 14-day)** — Wilder smoothing. Above
  70 suggests overbought (price likely to drop back toward its mean);
  below 30 suggests oversold (likely to bounce). The signal *strength*
  scales linearly with distance from the neutral level (50).
* **Bollinger z-score (20-day)** — ``(price - SMA_20) / SD_20``. A
  z-score of +2 is at the upper Bollinger band (overbought); -2 is at
  the lower band (oversold). Strength scales with ``|z|``, capped at
  3 (the "outside the bands" cap).
* **Hurst exponent (rescaled-range, multi-window over 100 days)** —
  ``H < 0.5`` means the series is mean-reverting; ``H > 0.5`` means it
  is trending. Hurst acts as a **confidence multiplier** on the
  RSI + Bollinger blend: high confidence when the series is genuinely
  mean-reverting, zero confidence in a strong trend.

The composite **pull factor** = (RSI_strength + Bollinger_strength) / 2
× Hurst_confidence. The projected price is
``current + pull × (SMA_20 - current)`` — the price reverts *toward*
the 20-day SMA, with magnitude proportional to the pull.

Pure Python: no SciPy. Decimal on the boundary; floats internally
(same pattern as GBM + Momentum).
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

MODEL_CODE: Final[str] = "mean_reversion_v1"
MODEL_VERSION: Final[str] = "v1.0.0"

# Window sizes (in trading days).
RSI_PERIOD: Final[int] = 14
BOLLINGER_PERIOD: Final[int] = 20
HURST_WINDOW: Final[int] = 100
HURST_CHUNK_SIZES: Final[tuple[int, ...]] = (10, 20, 50, 100)

# Minimum bars: Hurst needs 100, plus a few for the RSI/Bollinger to
# settle; 130 is the smallest sane floor.
MEAN_REVERSION_MIN_BARS: Final[int] = 130

# Strength caps.
BOLLINGER_Z_CAP: Final[float] = 3.0
RSI_NEUTRAL: Final[float] = 50.0
RSI_SCALE: Final[float] = 50.0  # max distance from neutral

# Direction thresholds (mirroring GBM + Momentum).
THRESHOLD_STRONG_PCT: Final[float] = 10.0
THRESHOLD_SLIGHT_PCT: Final[float] = 2.0


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


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stdev(values: Sequence[float], mean_value: float) -> float:
    if len(values) < 2:
        return 0.0
    variance = sum((v - mean_value) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _log_returns(prices: Sequence[float]) -> list[float]:
    returns: list[float] = []
    for i in range(1, len(prices)):
        prev = prices[i - 1]
        curr = prices[i]
        if prev <= 0 or curr <= 0:
            continue
        returns.append(math.log(curr / prev))
    return returns


# ---- RSI (Wilder smoothing) ------------------------------------------


def _compute_rsi(prices: Sequence[float], period: int = RSI_PERIOD) -> float | None:
    if len(prices) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(0.0, change))
        losses.append(max(0.0, -change))
    # Initial averages over the first `period` deltas.
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    # Wilder smoothing for the rest.
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# ---- Bollinger ---------------------------------------------------------


def _compute_bollinger(
    prices: Sequence[float], period: int = BOLLINGER_PERIOD
) -> tuple[float, float, float] | None:
    """Return ``(sma, sd, z)`` over the last ``period`` prices."""

    if len(prices) < period:
        return None
    window = prices[-period:]
    sma = _mean(window)
    sd = _stdev(window, sma)
    if sd == 0:
        return None
    z = (prices[-1] - sma) / sd
    return sma, sd, z


# ---- Hurst exponent (rescaled range, multi-window) -------------------


def _compute_hurst(prices: Sequence[float]) -> float | None:
    """Estimate the Hurst exponent on the trailing ``HURST_WINDOW`` log
    returns using a multi-window rescaled-range fit.

    Returns ``None`` if any chunk has zero standard deviation.
    """

    if len(prices) < HURST_WINDOW + 1:
        return None
    window = prices[-(HURST_WINDOW + 1) :]
    returns = _log_returns(window)
    n_returns = len(returns)
    if n_returns < HURST_WINDOW:
        return None

    log_n: list[float] = []
    log_rs: list[float] = []
    for chunk_size in HURST_CHUNK_SIZES:
        if chunk_size > n_returns:
            continue
        chunks = [
            returns[i : i + chunk_size]
            for i in range(0, n_returns - chunk_size + 1, chunk_size)
        ]
        rs_values: list[float] = []
        for chunk in chunks:
            mean_r = _mean(chunk)
            adjusted = [r - mean_r for r in chunk]
            cumsum: list[float] = []
            running = 0.0
            for value in adjusted:
                running += value
                cumsum.append(running)
            r_range = max(cumsum) - min(cumsum)
            sd = _stdev(chunk, mean_r)
            if sd == 0 or r_range == 0:
                continue
            rs_values.append(r_range / sd)
        if rs_values:
            log_n.append(math.log(chunk_size))
            log_rs.append(math.log(_mean(rs_values)))
    if len(log_n) < 2:
        return None
    # Least-squares slope of log(R/S) vs log(n)
    mean_x = _mean(log_n)
    mean_y = _mean(log_rs)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(log_n, log_rs, strict=True))
    den = sum((x - mean_x) ** 2 for x in log_n)
    if den == 0:
        return None
    return num / den


# ---- Predictor implementation ----------------------------------------


def _direction_label(expected_return_pct: float) -> str:
    if expected_return_pct >= THRESHOLD_STRONG_PCT:
        return DIRECTION_STRONG_UP
    if expected_return_pct >= THRESHOLD_SLIGHT_PCT:
        return DIRECTION_SLIGHT_UP
    if expected_return_pct > -THRESHOLD_SLIGHT_PCT:
        return DIRECTION_FLAT
    if expected_return_pct > -THRESHOLD_STRONG_PCT:
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


def _confidence_from_sample(n: int, hurst_confidence: float) -> float:
    """Baseline confidence at 0.4 with HURST_WINDOW bars; asymptotes to
    0.8 at one trading year. Multiplied by the Hurst confidence so a
    trending series caps confidence at near-zero (consistent with the
    pull factor)."""

    if n <= MEAN_REVERSION_MIN_BARS:
        base = 0.4
    elif n >= DEFAULT_TRADING_DAYS_PER_YEAR:
        base = 0.8
    else:
        span = DEFAULT_TRADING_DAYS_PER_YEAR - MEAN_REVERSION_MIN_BARS
        progress = (n - MEAN_REVERSION_MIN_BARS) / span
        base = 0.4 + (0.8 - 0.4) * progress
    return base * max(0.0, min(1.0, hurst_confidence))


class MeanReversionPredictor:
    """RSI + Bollinger + Hurst mean-reversion predictor."""

    def __init__(
        self,
        *,
        minimum_bars_required: int = MEAN_REVERSION_MIN_BARS,
        trading_days_per_year: int = DEFAULT_TRADING_DAYS_PER_YEAR,
    ) -> None:
        self._minimum_bars_required = minimum_bars_required
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
                    f"Mean-reversion vereist minstens "
                    f"{self._minimum_bars_required} bars; "
                    f"{len(inputs.historical_bars)} ontvangen."
                ),
            )

        prices = _bar_closes(inputs.historical_bars)
        rsi = _compute_rsi(prices)
        bollinger = _compute_bollinger(prices)
        hurst = _compute_hurst(prices)
        if bollinger is None:
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_FLAT_HISTORY,
                explanation_nl=(
                    "Bollinger volatiliteit is 0 over de laatste 20 dagen; "
                    "geen mean-reversion-distributie mogelijk."
                ),
            )

        sma, _bollinger_sd, z = bollinger

        # Strength components (0..1).
        rsi_strength = (
            min(1.0, abs(rsi - RSI_NEUTRAL) / RSI_SCALE) if rsi is not None else 0.0
        )
        bollinger_strength = min(1.0, abs(z) / BOLLINGER_Z_CAP)
        base_strength = (rsi_strength + bollinger_strength) / 2

        # Hurst confidence: 1 at H=0, 0 at H=0.5 and above. Default to
        # 0.3 (mild mean-reversion assumption) when Hurst can't be
        # estimated — we still want some signal rather than dropping it.
        hurst_confidence = (
            max(0.0, 1.0 - 2.0 * hurst) if hurst is not None else 0.3
        )
        pull = base_strength * hurst_confidence

        # Pull the projected price toward the 20-day SMA.
        current = float(inputs.current_price)
        target_price = current + pull * (sma - current)
        expected_return_pct = (target_price - current) / current * 100.0

        # Distribution width: trailing 6-month-equivalent volatility on
        # log-returns. We re-use the recent SD scaled to the horizon.
        recent_returns = _log_returns(prices[-min(126, len(prices)) :])
        mean_r = _mean(recent_returns)
        sd_recent = _stdev(recent_returns, mean_r)
        if sd_recent <= 0:
            return _blocked(
                horizon_trading_days=horizon,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_FLAT_HISTORY,
                explanation_nl=(
                    "Recente prijsreeks heeft geen volatiliteit; mean-reversion "
                    "kan geen distributie afleiden."
                ),
            )
        horizon_sd_log = sd_recent * math.sqrt(horizon)
        target_log_return = math.log(target_price / current) if target_price > 0 else 0.0
        p10_log = target_log_return + horizon_sd_log * (-1.2815515655446004)
        p50_log = target_log_return
        p90_log = target_log_return + horizon_sd_log * 1.2815515655446004
        p10 = current * math.exp(p10_log)
        p50 = current * math.exp(p50_log)
        p90 = current * math.exp(p90_log)

        z_for_zero = -target_log_return / horizon_sd_log if horizon_sd_log > 0 else 0.0
        prob_gain = 1.0 - _normal_cdf(z_for_zero)
        prob_loss = 1.0 - prob_gain
        confidence = _confidence_from_sample(
            len(inputs.historical_bars), hurst_confidence
        )

        rsi_text = f"{rsi:.1f}" if rsi is not None else "n/b"
        hurst_text = f"{hurst:.3f}" if hurst is not None else "n/b"
        explanation = (
            f"Mean-reversion: RSI={rsi_text}, Bollinger z={z:.2f}, "
            f"Hurst={hurst_text}, pull={pull:.2f} → verwachte rendement over "
            f"{horizon} dagen = {expected_return_pct:.2f}% "
            f"(target SMA={sma:.2f})."
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
            direction=_direction_label(expected_return_pct),
            confidence_score=_decimal(confidence, 6),
            status=STATUS_READY,
            blocking_reason=None,
            explanation_nl=explanation,
        )


__all__ = [
    "MODEL_CODE",
    "MODEL_VERSION",
    "MEAN_REVERSION_MIN_BARS",
    "RSI_PERIOD",
    "BOLLINGER_PERIOD",
    "HURST_WINDOW",
    "MeanReversionPredictor",
]
