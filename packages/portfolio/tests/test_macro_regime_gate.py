"""Tests for the macro regime gate (V1.2 §I)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_BEAR_TREND,
    BLOCKING_REASON_VIX_TOO_HIGH,
    MACRO_REGIME_BLOCKING_REASON_INSUFFICIENT_HISTORY,
    HistoricalBar,
    MacroRegimeInputs,
    evaluate_macro_regime,
)


def _bars(closes: list[float]) -> list[HistoricalBar]:
    base = date(2025, 1, 1)
    return [
        HistoricalBar(
            bar_date=base + timedelta(days=i),
            close_price=Decimal(repr(round(c, 4))),
        )
        for i, c in enumerate(closes)
    ]


def _trending_up_bars(
    count: int, *, slope: float = 0.5, start: float = 100.0
) -> list[HistoricalBar]:
    """A straight upward trend — 50d MA will be above 200d MA."""

    return _bars([start + i * slope for i in range(count)])


def _trending_down_bars(
    count: int, *, slope: float = 0.5, start: float = 200.0
) -> list[HistoricalBar]:
    """A straight downward trend — 50d MA will be below 200d MA."""

    return _bars([start - i * slope for i in range(count)])


# ---- VIX gate --------------------------------------------------------


def test_high_vix_blocks_even_when_trend_is_up() -> None:
    result = evaluate_macro_regime(
        MacroRegimeInputs(
            vix_level=Decimal("35"),
            index_bars=_trending_up_bars(250),
        )
    )
    assert not result.favorable
    assert result.blocking_reason == BLOCKING_REASON_VIX_TOO_HIGH
    assert result.vix_level == Decimal("35")


def test_low_vix_with_up_trend_passes() -> None:
    result = evaluate_macro_regime(
        MacroRegimeInputs(
            vix_level=Decimal("15"),
            index_bars=_trending_up_bars(250),
        )
    )
    assert result.favorable
    assert result.blocking_reason is None
    assert result.vix_level == Decimal("15")


def test_vix_exactly_at_threshold_blocks() -> None:
    # Doctrine: >= threshold blocks, not > threshold.
    result = evaluate_macro_regime(
        MacroRegimeInputs(
            vix_level=Decimal("30"),
            index_bars=_trending_up_bars(250),
        )
    )
    assert not result.favorable
    assert result.blocking_reason == BLOCKING_REASON_VIX_TOO_HIGH


def test_unknown_vix_skips_vix_check() -> None:
    # No VIX reading → don't fire the VIX guard; trend takes over.
    result = evaluate_macro_regime(
        MacroRegimeInputs(
            vix_level=None,
            index_bars=_trending_up_bars(250),
        )
    )
    assert result.favorable


def test_unknown_vix_does_not_save_a_bear_trend() -> None:
    # Even without a VIX reading, an unmistakable bear trend blocks.
    result = evaluate_macro_regime(
        MacroRegimeInputs(
            vix_level=None,
            index_bars=_trending_down_bars(250),
        )
    )
    assert not result.favorable
    assert result.blocking_reason == BLOCKING_REASON_BEAR_TREND


# ---- MA crossover ----------------------------------------------------


def test_bear_trend_blocks() -> None:
    result = evaluate_macro_regime(
        MacroRegimeInputs(
            vix_level=Decimal("15"),
            index_bars=_trending_down_bars(250),
        )
    )
    assert not result.favorable
    assert result.blocking_reason == BLOCKING_REASON_BEAR_TREND
    assert result.ma_short_day is not None
    assert result.ma_long_day is not None
    assert result.ma_short_day < result.ma_long_day


def test_bull_trend_passes() -> None:
    result = evaluate_macro_regime(
        MacroRegimeInputs(
            vix_level=Decimal("15"),
            index_bars=_trending_up_bars(250),
        )
    )
    assert result.favorable
    assert result.ma_short_day is not None
    assert result.ma_long_day is not None
    assert result.ma_short_day > result.ma_long_day


def test_ma_equal_passes() -> None:
    # Flat series → MAs are equal. Doctrine: equal is "not bearish",
    # so allow.
    result = evaluate_macro_regime(
        MacroRegimeInputs(
            vix_level=Decimal("15"),
            index_bars=_bars([100.0] * 250),
        )
    )
    assert result.favorable


# ---- insufficient history --------------------------------------------


def test_too_few_bars_blocks_with_insufficient_history() -> None:
    result = evaluate_macro_regime(
        MacroRegimeInputs(
            vix_level=Decimal("15"),
            index_bars=_trending_up_bars(150),  # < 200
        )
    )
    assert not result.favorable
    assert (
        result.blocking_reason
        == MACRO_REGIME_BLOCKING_REASON_INSUFFICIENT_HISTORY
    )


def test_negative_close_blocks_with_insufficient_history() -> None:
    bars = _trending_up_bars(250)
    bad = list(bars)
    bad[-1] = HistoricalBar(bar_date=bars[-1].bar_date, close_price=Decimal("-5"))
    result = evaluate_macro_regime(
        MacroRegimeInputs(vix_level=Decimal("15"), index_bars=bad)
    )
    assert not result.favorable
    assert (
        result.blocking_reason
        == MACRO_REGIME_BLOCKING_REASON_INSUFFICIENT_HISTORY
    )


def test_custom_windows_work() -> None:
    # With 20/50 windows, the same length-150 input now has enough
    # history.
    result = evaluate_macro_regime(
        MacroRegimeInputs(
            vix_level=Decimal("15"),
            index_bars=_trending_up_bars(150),
        ),
        ma_short_window=20,
        ma_long_window=50,
    )
    assert result.favorable


# ---- check order -----------------------------------------------------


def test_vix_check_runs_before_trend_check() -> None:
    # Bear trend AND high VIX — should report VIX (the first check).
    result = evaluate_macro_regime(
        MacroRegimeInputs(
            vix_level=Decimal("40"),
            index_bars=_trending_down_bars(250),
        )
    )
    assert result.blocking_reason == BLOCKING_REASON_VIX_TOO_HIGH


def test_insufficient_history_runs_before_trend_check() -> None:
    # Insufficient bars → "macro_insufficient_history", not bear.
    result = evaluate_macro_regime(
        MacroRegimeInputs(vix_level=Decimal("15"), index_bars=_trending_down_bars(100))
    )
    assert (
        result.blocking_reason
        == MACRO_REGIME_BLOCKING_REASON_INSUFFICIENT_HISTORY
    )


# ---- input validation ------------------------------------------------


def test_float_threshold_rejected() -> None:
    with pytest.raises(TypeError):
        evaluate_macro_regime(
            MacroRegimeInputs(vix_level=Decimal("15"), index_bars=_trending_up_bars(250)),
            vix_threshold=30.0,  # type: ignore[arg-type]
        )


def test_invalid_windows_rejected() -> None:
    with pytest.raises(ValueError):
        evaluate_macro_regime(
            MacroRegimeInputs(vix_level=Decimal("15"), index_bars=_trending_up_bars(250)),
            ma_short_window=0,
        )
    with pytest.raises(ValueError):
        evaluate_macro_regime(
            MacroRegimeInputs(vix_level=Decimal("15"), index_bars=_trending_up_bars(250)),
            ma_short_window=200,
            ma_long_window=50,
        )
