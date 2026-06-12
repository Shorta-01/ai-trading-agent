"""Macro regime gate (V1.2 §I).

Capital-protection guard layered on top of the per-name confidence
gate. When the broad market is in a fear regime the per-name math
still says "+4 % is reachable", but the empirical hit rate during
crashes is much lower than the lognormal model implies. Crash
correlation collapses individual-name forecasts onto a single
downward trajectory.

Two practitioner-standard signals are enough to refuse new BUYs:

* **VIX above a fear threshold** — historically a VIX print north of
  30 marks a stress regime where individual-name volatility forecasts
  underestimate true downside.
* **Index 50/200-day MA crossover** — when the 50-day MA falls below
  the 200-day MA the broad index has established a bearish trend. We
  do not try to time the bottom; we simply refuse new entries until
  the trend turns.

If *either* signal fires, the gate refuses new BUY suggestions.
Existing held positions are untouched — the no-stop-loss doctrine
says they wait for either the +4 % take-profit or a hard news flag.

This module is pure Python — math.fsum + plain comparisons; no
numpy at this leaf. The suggestion pipeline calls it once per
suggestion cycle, not per candidate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from math import fsum
from typing import Final

from portfolio_outlook_portfolio.baseline_forecast import HistoricalBar

# Locked blocking reason codes. Stable across versions because they
# end up on the audit trail and in the operator-UI explanation.
BLOCKING_REASON_VIX_TOO_HIGH: Final[str] = "macro_vix_too_high"
BLOCKING_REASON_BEAR_TREND: Final[str] = "macro_index_in_bear_trend"
BLOCKING_REASON_INSUFFICIENT_HISTORY: Final[str] = "macro_insufficient_history"

# Default thresholds. The VIX number is the standard practitioner
# "stress" line; the MA windows are the textbook 50/200-day pair.
DEFAULT_VIX_THRESHOLD: Final[Decimal] = Decimal("30")
DEFAULT_MA_SHORT_DAYS: Final[int] = 50
DEFAULT_MA_LONG_DAYS: Final[int] = 200

_PRICE_QUANT: Final[Decimal] = Decimal("0.0001")


@dataclass(frozen=True)
class MacroRegimeInputs:
    """Inputs to the macro regime gate.

    ``vix_level`` may be ``None`` when the provider didn't return it.
    The gate then keeps the VIX guard from firing — the MA-crossover
    signal alone is enough to refuse on its own. Compared to risk
    universe (where unknown == block), here unknown == ignore that
    single check, because a missing VIX print is much more common
    than a missing market-cap reading.

    ``index_bars`` is the broad-market index history (S&P 500 or
    similar) ordered ascending by date. The list must contain at
    least ``ma_long_window`` bars for the MA crossover to be
    evaluable — otherwise the gate surfaces
    ``macro_insufficient_history``.
    """

    vix_level: Decimal | None
    index_bars: Sequence[HistoricalBar]


@dataclass(frozen=True)
class MacroRegimeResult:
    """Verdict + diagnostics from one regime-gate pass.

    ``ma_50_day`` / ``ma_200_day`` are populated whenever computed,
    even on blocked results — the UI uses them to display the
    crossover state ("S&P 50d 4 921 < 200d 5 142 — bear trend").
    """

    favorable: bool
    blocking_reason: str | None
    vix_level: Decimal | None
    ma_short_day: Decimal | None
    ma_long_day: Decimal | None


def _sma(closes: Sequence[float], window: int) -> Decimal | None:
    """Simple moving average over the last ``window`` closes."""

    if window <= 0 or len(closes) < window:
        return None
    tail = list(closes[-window:])
    avg = fsum(tail) / window
    return Decimal(repr(avg)).quantize(_PRICE_QUANT, rounding=ROUND_HALF_UP)


def evaluate_macro_regime(
    inputs: MacroRegimeInputs,
    *,
    vix_threshold: Decimal = DEFAULT_VIX_THRESHOLD,
    ma_short_window: int = DEFAULT_MA_SHORT_DAYS,
    ma_long_window: int = DEFAULT_MA_LONG_DAYS,
) -> MacroRegimeResult:
    """Check whether the broad market regime is favorable for new BUYs.

    Order of checks:

    1. **VIX** — if a level was supplied and it's >= threshold, refuse.
       A missing VIX value just skips this check.
    2. **Insufficient history** — without ``ma_long_window`` bars we
       cannot evaluate the trend; refuse with that reason.
    3. **MA crossover** — if 50-day MA falls below the 200-day MA,
       refuse with bear-trend reason.

    Args:
        inputs: VIX level + index bar history.
        vix_threshold: VIX reading at or above which the regime is
            considered unfavorable. Default 30.
        ma_short_window: Short MA window in bars. Default 50.
        ma_long_window: Long MA window in bars. Default 200.
    """

    if not isinstance(vix_threshold, Decimal):
        raise TypeError("vix_threshold must be a Decimal")
    if ma_short_window <= 0 or ma_long_window <= 0:
        raise ValueError("MA windows must be > 0")
    if ma_short_window >= ma_long_window:
        raise ValueError("ma_short_window must be < ma_long_window")

    # 1. VIX check — only fires when a level was actually supplied.
    if inputs.vix_level is not None and inputs.vix_level >= vix_threshold:
        return MacroRegimeResult(
            favorable=False,
            blocking_reason=BLOCKING_REASON_VIX_TOO_HIGH,
            vix_level=inputs.vix_level,
            ma_short_day=None,
            ma_long_day=None,
        )

    # 2. Need enough bars for both MAs.
    closes = [float(bar.close_price) for bar in inputs.index_bars]
    if any(c <= 0 for c in closes):
        return MacroRegimeResult(
            favorable=False,
            blocking_reason=BLOCKING_REASON_INSUFFICIENT_HISTORY,
            vix_level=inputs.vix_level,
            ma_short_day=None,
            ma_long_day=None,
        )
    if len(closes) < ma_long_window:
        return MacroRegimeResult(
            favorable=False,
            blocking_reason=BLOCKING_REASON_INSUFFICIENT_HISTORY,
            vix_level=inputs.vix_level,
            ma_short_day=None,
            ma_long_day=None,
        )

    # 3. MA crossover.
    ma_short = _sma(closes, ma_short_window)
    ma_long = _sma(closes, ma_long_window)
    if ma_short is None or ma_long is None:
        # Should be unreachable given the length checks above, but a
        # belt-and-braces against caller-supplied windows.
        return MacroRegimeResult(
            favorable=False,
            blocking_reason=BLOCKING_REASON_INSUFFICIENT_HISTORY,
            vix_level=inputs.vix_level,
            ma_short_day=ma_short,
            ma_long_day=ma_long,
        )
    if ma_short < ma_long:
        return MacroRegimeResult(
            favorable=False,
            blocking_reason=BLOCKING_REASON_BEAR_TREND,
            vix_level=inputs.vix_level,
            ma_short_day=ma_short,
            ma_long_day=ma_long,
        )

    return MacroRegimeResult(
        favorable=True,
        blocking_reason=None,
        vix_level=inputs.vix_level,
        ma_short_day=ma_short,
        ma_long_day=ma_long,
    )


__all__ = [
    "BLOCKING_REASON_BEAR_TREND",
    "BLOCKING_REASON_INSUFFICIENT_HISTORY",
    "BLOCKING_REASON_VIX_TOO_HIGH",
    "DEFAULT_MA_LONG_DAYS",
    "DEFAULT_MA_SHORT_DAYS",
    "DEFAULT_VIX_THRESHOLD",
    "MacroRegimeInputs",
    "MacroRegimeResult",
    "evaluate_macro_regime",
]
