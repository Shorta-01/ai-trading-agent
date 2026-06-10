"""Tests for V1.2 §E — bar-series integrity gate.

The integrity gate is the data-quality firewall before forecast math.
Hard blocks (duplicate dates, non-monotonic dates, suspicious jumps,
excessive calendar gaps) refuse the forecast; soft flags (moderate
jumps, gap counts) are informational and don't block.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio.bar_integrity import (
    MODERATE_JUMP_LOG_THRESHOLD,
    SUSPICIOUS_JUMP_LOG_THRESHOLD,
    BarIntegrityReport,
    validate_bar_integrity,
)
from portfolio_outlook_portfolio.baseline_forecast import HistoricalBar


def _bar(d: date, price: float) -> HistoricalBar:
    return HistoricalBar(bar_date=d, close_price=Decimal(str(price)))


def _clean_series(
    n: int = 100, start: float = 100.0, drift: float = 0.0005, seed: int = 1
) -> list[HistoricalBar]:
    """A clean trading-day series with small daily moves and one
    weekend gap baked in per week — i.e. realistic for liquid equity
    EOD bars from a sane provider. Mild stochastic noise so the
    volatility estimator gets a non-zero σ; the moves are far below
    the moderate-jump threshold so the integrity report stays clean."""

    import random as _random

    rng = _random.Random(seed)
    bars: list[HistoricalBar] = []
    d = date(2026, 1, 5)  # Monday
    price = start
    for _ in range(n):
        while d.weekday() >= 5:
            d += timedelta(days=1)
        bars.append(_bar(d, price))
        # ±2% daily noise — well below MODERATE_JUMP_LOG_THRESHOLD (15%).
        price *= math.exp(drift + rng.gauss(0.0, 0.02))
        d += timedelta(days=1)
    return bars


# ---- empty series ---------------------------------------------------------


def test_empty_series_is_reported_safe_with_zero_counters() -> None:
    """Empty series isn't an integrity problem — the forecast layer's
    ``insufficient_history`` check is the right place to refuse on
    length. We just report a clean zero."""

    out = validate_bar_integrity([])
    assert isinstance(out, BarIntegrityReport)
    assert out.is_safe is True
    assert out.hard_blocking_reason is None
    assert out.duplicate_date_count == 0
    assert out.suspicious_jump_count == 0
    assert out.moderate_jump_count == 0
    assert out.trading_day_gap_count == 0
    assert out.largest_gap_calendar_days == 0


# ---- clean series ---------------------------------------------------------


def test_clean_series_is_reported_safe_with_no_flags() -> None:
    out = validate_bar_integrity(_clean_series())
    assert out.is_safe is True
    assert out.hard_blocking_reason is None
    assert out.suspicious_jump_count == 0
    assert out.moderate_jump_count == 0
    # Weekends are 3 calendar days = exactly the soft threshold; not flagged.
    assert out.trading_day_gap_count == 0


# ---- duplicate dates: hard block ------------------------------------------


def test_duplicate_dates_hard_block() -> None:
    series = _clean_series(20)
    # Inject a duplicate.
    duplicated = list(series)
    duplicated.insert(5, _bar(series[5].bar_date, 99.0))
    out = validate_bar_integrity(duplicated)
    assert out.is_safe is False
    assert out.hard_blocking_reason == "duplicate_bar_dates"
    assert out.duplicate_date_count >= 1


def test_duplicate_dates_take_precedence_over_other_flags() -> None:
    """Structural problems are checked before content problems — a
    duplicate-date series is refused without trying to score the
    (potentially garbage) price jumps."""

    series = [
        _bar(date(2026, 1, 5), 100.0),
        _bar(date(2026, 1, 6), 101.0),
        _bar(date(2026, 1, 6), 50.0),  # duplicate AND a big jump
    ]
    out = validate_bar_integrity(series)
    assert out.hard_blocking_reason == "duplicate_bar_dates"
    # Jump count is intentionally NOT scored when the structural
    # check already failed — the duplicate makes the magnitude
    # meaningless.
    assert out.suspicious_jump_count == 0


# ---- non-monotonic dates: hard block --------------------------------------


def test_non_monotonic_dates_hard_block() -> None:
    series = _clean_series(10)
    # Swap two consecutive bars to make them out of order.
    reordered = list(series)
    reordered[3], reordered[4] = reordered[4], reordered[3]
    out = validate_bar_integrity(reordered)
    assert out.is_safe is False
    assert out.hard_blocking_reason == "non_monotonic_bar_dates"
    assert out.out_of_order_count >= 1


# ---- suspicious jump: hard block ------------------------------------------


def test_suspicious_jump_above_threshold_hard_blocks() -> None:
    """A single bar with |log-return| just above the suspicious
    threshold (default 0.40, ≈ 49% price move) is refused — this is the
    missed-split adjustment signature."""

    series = [
        _bar(date(2026, 1, 5), 100.0),
        _bar(date(2026, 1, 6), 100.5),
        _bar(date(2026, 1, 7), 50.0),  # log-return ≈ -0.70, way above 0.40
        _bar(date(2026, 1, 8), 50.5),
    ]
    out = validate_bar_integrity(series)
    assert out.is_safe is False
    assert out.hard_blocking_reason == "suspicious_single_bar_jump"
    assert out.suspicious_jump_count == 1


def test_jump_exactly_at_threshold_is_blocking() -> None:
    """Threshold is inclusive — a |log-return| exactly equal to the
    threshold is treated as suspicious. Operator-friendly because the
    threshold is the "if you see this it's almost always wrong" line."""

    p1 = 100.0
    p2 = p1 * math.exp(SUSPICIOUS_JUMP_LOG_THRESHOLD)
    series = [
        _bar(date(2026, 1, 5), p1),
        _bar(date(2026, 1, 6), p2),
    ]
    out = validate_bar_integrity(series)
    assert out.is_safe is False
    assert out.hard_blocking_reason == "suspicious_single_bar_jump"


def test_threshold_overrideable_for_high_vol_universes() -> None:
    """Crypto-style assets (out of V1 scope but plausible follow-up)
    legitimately move 50%+ in a day. The threshold is a kwarg so
    operators can opt in to a looser bar when they know the universe."""

    series = [
        _bar(date(2026, 1, 5), 100.0),
        _bar(date(2026, 1, 6), 50.0),
    ]
    out = validate_bar_integrity(series, suspicious_jump_threshold=1.0)
    # Loosened — the same series passes the hard check now.
    assert out.is_safe is True
    # But still counted as a moderate jump.
    assert out.moderate_jump_count == 1


# ---- moderate jump: soft flag, no block -----------------------------------


def test_moderate_jump_flagged_but_not_blocked() -> None:
    """A |log-return| in [0.15, 0.40) is flagged for the operator to
    notice (could be a real earnings move or a data artifact) but
    doesn't refuse the forecast."""

    p1 = 100.0
    p2 = p1 * math.exp(MODERATE_JUMP_LOG_THRESHOLD + 0.01)  # ~16% move
    series = [
        _bar(date(2026, 1, 5), p1),
        _bar(date(2026, 1, 6), p2),
        _bar(date(2026, 1, 7), p2 * 1.005),
    ]
    out = validate_bar_integrity(series)
    assert out.is_safe is True
    assert out.moderate_jump_count == 1
    assert out.suspicious_jump_count == 0


def test_jump_below_moderate_threshold_is_not_flagged_at_all() -> None:
    """A normal ±2% daily move shouldn't show up in either counter."""

    series = [
        _bar(date(2026, 1, 5), 100.0),
        _bar(date(2026, 1, 6), 102.0),
        _bar(date(2026, 1, 7), 100.5),
    ]
    out = validate_bar_integrity(series)
    assert out.moderate_jump_count == 0
    assert out.suspicious_jump_count == 0


# ---- calendar gaps --------------------------------------------------------


def test_weekend_gap_is_not_flagged() -> None:
    """3 calendar days = soft threshold; not flagged."""

    series = [
        _bar(date(2026, 1, 9), 100.0),  # Friday
        _bar(date(2026, 1, 12), 100.5),  # Monday
    ]
    out = validate_bar_integrity(series)
    assert out.trading_day_gap_count == 0
    assert out.largest_gap_calendar_days == 3


def test_holiday_gap_is_soft_flagged_but_not_blocked() -> None:
    """5 calendar days (e.g. Thanksgiving Thu/Fri shutdown) — above
    the soft threshold (4) but well below the hard threshold (14).
    Counts as one flagged gap; forecast still allowed."""

    series = [
        _bar(date(2026, 1, 5), 100.0),
        _bar(date(2026, 1, 12), 100.5),  # 7-day gap
    ]
    out = validate_bar_integrity(series)
    assert out.is_safe is True
    assert out.trading_day_gap_count == 1
    assert out.largest_gap_calendar_days == 7


def test_excessive_calendar_gap_hard_blocks() -> None:
    """A gap above the hard threshold (default 14) refuses the
    forecast — covers normal holidays but not multi-week outages."""

    series = [
        _bar(date(2026, 1, 5), 100.0),
        _bar(date(2026, 2, 5), 100.5),  # 31-day gap
    ]
    out = validate_bar_integrity(series)
    assert out.is_safe is False
    assert out.hard_blocking_reason == "excessive_calendar_gap"
    assert out.largest_gap_calendar_days == 31


def test_gap_threshold_overrideable() -> None:
    """Operator can tighten the hard threshold to e.g. 7 days for a
    universe where any holiday closure should refuse the forecast."""

    series = [
        _bar(date(2026, 1, 5), 100.0),
        _bar(date(2026, 1, 15), 100.5),  # 10-day gap
    ]
    # Default thresholds: 10 < 14, so safe.
    assert validate_bar_integrity(series).is_safe is True
    # Tightened: 10 > 7, so refused.
    tight = validate_bar_integrity(series, gap_hard_threshold_days=7)
    assert tight.is_safe is False
    assert tight.hard_blocking_reason == "excessive_calendar_gap"


# ---- robustness against degenerate inputs --------------------------------


def test_non_positive_prices_are_ignored_in_jump_check() -> None:
    """The jump check guards against zero / negative prices (which
    would make the log-return undefined). Such bars are simply not
    scored for jumps — but the structural checks still run."""

    series = [
        _bar(date(2026, 1, 5), 100.0),
        _bar(date(2026, 1, 6), 0.0),  # invalid price
        _bar(date(2026, 1, 7), 101.0),
    ]
    out = validate_bar_integrity(series)
    # No suspicious jump counted (the bar with zero price was skipped).
    assert out.suspicious_jump_count == 0
    # But structural checks (dates monotone, no duplicates) pass.
    assert out.is_safe is True


def test_single_bar_series_has_no_jumps_or_gaps() -> None:
    """A single bar can't have either; the report should be clean."""

    out = validate_bar_integrity([_bar(date(2026, 1, 5), 100.0)])
    assert out.is_safe is True
    assert out.largest_gap_calendar_days == 0


# ---- Integration: compute_baseline_forecast wiring ------------------------


def test_baseline_forecast_blocks_on_duplicate_dates() -> None:
    """A series with duplicated dates must return a blocked
    forecast — the integrity gate fires before any math runs."""

    from portfolio_outlook_portfolio.baseline_forecast import (
        compute_baseline_forecast,
    )

    bars = _clean_series(80)
    bars.insert(20, _bar(bars[20].bar_date, 99.0))  # duplicate

    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal("105.0")
    )
    assert result.status == "blocked"
    assert result.blocking_reason == "duplicate_bar_dates"
    assert "dubbele datum" in result.explanation_nl.lower()


def test_baseline_forecast_blocks_on_suspicious_jump() -> None:
    """Missed-split signature: a single bar with ≥ 40% log-return."""

    from portfolio_outlook_portfolio.baseline_forecast import (
        compute_baseline_forecast,
    )

    bars = _clean_series(80)
    # Halve the price at index 30 — log-return ≈ -0.69.
    bars[30] = _bar(bars[30].bar_date, float(bars[30].close_price) / 2.0)

    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal("105.0")
    )
    assert result.status == "blocked"
    assert result.blocking_reason == "suspicious_single_bar_jump"
    assert "corporate-action" in result.explanation_nl.lower()


def test_baseline_forecast_blocks_on_excessive_calendar_gap() -> None:
    from portfolio_outlook_portfolio.baseline_forecast import (
        compute_baseline_forecast,
    )

    bars = _clean_series(80)
    # Shift bars 40+ by 60 calendar days forward — opens a one-month-
    # plus gap between bar 39 and 40, keeping monotonic order intact.
    shift = timedelta(days=60)
    bars = bars[:40] + [
        _bar(b.bar_date + shift, float(b.close_price)) for b in bars[40:]
    ]

    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal("105.0")
    )
    assert result.status == "blocked"
    assert result.blocking_reason == "excessive_calendar_gap"


def test_baseline_forecast_passes_on_clean_series() -> None:
    """Regression: a clean series must STILL pass the integrity gate
    and produce a real (non-blocked) forecast — i.e. we haven't broken
    the V1 happy path."""

    from portfolio_outlook_portfolio.baseline_forecast import (
        compute_baseline_forecast,
    )

    bars = _clean_series(100)
    result = compute_baseline_forecast(
        bars=bars, current_price=Decimal("160.0")
    )
    assert result.status == "ready"
    assert result.blocking_reason is None
    assert result.p10_price < result.p50_price < result.p90_price
