"""Bar-series data quality gates (V1.2 §E).

Liquid equity EOD bars from a single provider — EODHD in production —
should be clean. But "should" is doing work there: missed corporate-
action adjustments, provider-side dedup mistakes, and weekend backfill
edge cases all silently poison forecasts when nothing checks for them.

This module is the single-pass integrity report that runs before any
forecast math touches the series. The contract is intentionally
conservative:

* **Hard blocks** — duplicate trading dates, non-monotonic dates, or
  a single-bar log-return whose absolute value exceeds the suspicious-
  jump threshold (default 40%, ≈ 49% price move). A liquid-equity
  one-day move of that size is essentially always a missed split
  adjustment or other data error. Refusing the forecast and surfacing
  the reason in ``hard_blocking_reason`` is safer than feeding the
  predictor garbage that the volatility estimator can't tell from
  signal.
* **Soft flags** — moderate one-bar jumps (≥ 15%) and multi-day
  trading-day gaps. These can be real (earnings, holidays) or
  artifacts; the report counts them so the forecast layer can
  downgrade confidence or surface a warning in the operator UI
  without refusing to forecast.

The module is pure Python — no I/O, no NumPy — so it can run inside
the leaf ``portfolio`` package without taking on extra deps.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from portfolio_outlook_portfolio.baseline_forecast import HistoricalBar

# Default thresholds. All are *log-return* magnitudes; the equivalent
# linear price-move percentage is given in the comment for reviewer
# intuition. Choices are practitioner-conservative:
#
# * 0.40 ≈ 49% one-day move — for any liquid-equity bar this is
#   essentially always a missed corporate-action adjustment.
# * 0.15 ≈ 16% one-day move — earnings and FOMC surprises CAN do
#   this, but it's worth flagging because the modal cause is still
#   a data artifact for diversified universes.
SUSPICIOUS_JUMP_LOG_THRESHOLD: Final[float] = 0.40
MODERATE_JUMP_LOG_THRESHOLD: Final[float] = 0.15

# Calendar-day gap thresholds between consecutive bars. A normal
# weekend is 3 calendar days (Fri → Mon); a single holiday on a
# Monday makes it 4. Anything above is a likely missing-bar
# situation. The largest gap is reported separately so callers can
# make a graded decision (12-day Christmas gap is normal; 30-day
# isn't).
GAP_DAYS_SOFT_THRESHOLD: Final[int] = 4
GAP_DAYS_HARD_THRESHOLD: Final[int] = 14


@dataclass(frozen=True)
class BarIntegrityReport:
    """Verdict + counters from a single pass over the bar series.

    ``is_safe`` is the gate: when ``False`` the forecast layer MUST
    return a blocked forecast with ``hard_blocking_reason`` rather than
    attempting math on the series. When ``True``, the soft counters
    may still be non-zero — they're informational, not blocking.
    """

    is_safe: bool
    hard_blocking_reason: str | None
    duplicate_date_count: int
    out_of_order_count: int
    suspicious_jump_count: int  # |log-return| ≥ SUSPICIOUS threshold
    moderate_jump_count: int  # |log-return| in [MODERATE, SUSPICIOUS)
    trading_day_gap_count: int  # consecutive-bar calendar gap > soft
    largest_gap_calendar_days: int  # 0 if series too short to measure


def validate_bar_integrity(
    bars: Sequence[HistoricalBar],
    *,
    suspicious_jump_threshold: float = SUSPICIOUS_JUMP_LOG_THRESHOLD,
    moderate_jump_threshold: float = MODERATE_JUMP_LOG_THRESHOLD,
    gap_soft_threshold_days: int = GAP_DAYS_SOFT_THRESHOLD,
    gap_hard_threshold_days: int = GAP_DAYS_HARD_THRESHOLD,
) -> BarIntegrityReport:
    """Single-pass integrity report over an EOD bar series.

    Detection order matters: structural problems (duplicate dates,
    non-monotonic dates) are checked before content problems (price
    jumps) because they can artificially inflate the jump count.

    Args:
        bars: Series to validate. Caller is responsible for the order
            they want the series to be in (ascending date). Empty
            series returns a "safe but empty" report — the forecast
            layer's own ``insufficient_history`` check is the right
            place to refuse on length.
        suspicious_jump_threshold: ``|log-return|`` above which a single
            bar-to-bar jump is treated as a hard block. Default 0.40.
        moderate_jump_threshold: ``|log-return|`` above which a jump is
            flagged but not blocked. Default 0.15.
        gap_soft_threshold_days: Calendar gap above which a missing
            trading day is counted (soft). Default 4.
        gap_hard_threshold_days: Calendar gap above which the entire
            series is refused (hard). Default 14 — covers normal
            holidays (Christmas/Easter) but not multi-week outages.
    """

    if not bars:
        return BarIntegrityReport(
            is_safe=True,
            hard_blocking_reason=None,
            duplicate_date_count=0,
            out_of_order_count=0,
            suspicious_jump_count=0,
            moderate_jump_count=0,
            trading_day_gap_count=0,
            largest_gap_calendar_days=0,
        )

    # ---- structural checks: ordering + duplicates --------------------
    from datetime import date as _date

    duplicate_date_count = 0
    out_of_order_count = 0
    seen_dates: set[_date] = set()
    previous_bar: HistoricalBar | None = None
    for bar in bars:
        if bar.bar_date in seen_dates:
            duplicate_date_count += 1
        seen_dates.add(bar.bar_date)
        if previous_bar is not None and bar.bar_date < previous_bar.bar_date:
            out_of_order_count += 1
        previous_bar = bar

    if duplicate_date_count > 0:
        return BarIntegrityReport(
            is_safe=False,
            hard_blocking_reason="duplicate_bar_dates",
            duplicate_date_count=duplicate_date_count,
            out_of_order_count=out_of_order_count,
            suspicious_jump_count=0,
            moderate_jump_count=0,
            trading_day_gap_count=0,
            largest_gap_calendar_days=0,
        )
    if out_of_order_count > 0:
        return BarIntegrityReport(
            is_safe=False,
            hard_blocking_reason="non_monotonic_bar_dates",
            duplicate_date_count=0,
            out_of_order_count=out_of_order_count,
            suspicious_jump_count=0,
            moderate_jump_count=0,
            trading_day_gap_count=0,
            largest_gap_calendar_days=0,
        )

    # ---- content checks: price jumps + calendar gaps -----------------
    suspicious_jump_count = 0
    moderate_jump_count = 0
    trading_day_gap_count = 0
    largest_gap_calendar_days = 0
    previous_bar = None
    for bar in bars:
        if previous_bar is not None:
            calendar_gap = (bar.bar_date - previous_bar.bar_date).days
            if calendar_gap > largest_gap_calendar_days:
                largest_gap_calendar_days = calendar_gap
            if calendar_gap > gap_soft_threshold_days:
                trading_day_gap_count += 1
            # Log-return guards against zero / negative prior price.
            prev_price = float(previous_bar.close_price)
            this_price = float(bar.close_price)
            if prev_price > 0.0 and this_price > 0.0:
                log_return = math.log(this_price / prev_price)
                magnitude = abs(log_return)
                if magnitude >= suspicious_jump_threshold:
                    suspicious_jump_count += 1
                elif magnitude >= moderate_jump_threshold:
                    moderate_jump_count += 1
        previous_bar = bar

    if suspicious_jump_count > 0:
        return BarIntegrityReport(
            is_safe=False,
            hard_blocking_reason="suspicious_single_bar_jump",
            duplicate_date_count=0,
            out_of_order_count=0,
            suspicious_jump_count=suspicious_jump_count,
            moderate_jump_count=moderate_jump_count,
            trading_day_gap_count=trading_day_gap_count,
            largest_gap_calendar_days=largest_gap_calendar_days,
        )
    if largest_gap_calendar_days > gap_hard_threshold_days:
        return BarIntegrityReport(
            is_safe=False,
            hard_blocking_reason="excessive_calendar_gap",
            duplicate_date_count=0,
            out_of_order_count=0,
            suspicious_jump_count=0,
            moderate_jump_count=moderate_jump_count,
            trading_day_gap_count=trading_day_gap_count,
            largest_gap_calendar_days=largest_gap_calendar_days,
        )

    return BarIntegrityReport(
        is_safe=True,
        hard_blocking_reason=None,
        duplicate_date_count=0,
        out_of_order_count=0,
        suspicious_jump_count=0,
        moderate_jump_count=moderate_jump_count,
        trading_day_gap_count=trading_day_gap_count,
        largest_gap_calendar_days=largest_gap_calendar_days,
    )


__all__ = [
    "BarIntegrityReport",
    "GAP_DAYS_HARD_THRESHOLD",
    "GAP_DAYS_SOFT_THRESHOLD",
    "MODERATE_JUMP_LOG_THRESHOLD",
    "SUSPICIOUS_JUMP_LOG_THRESHOLD",
    "validate_bar_integrity",
]
