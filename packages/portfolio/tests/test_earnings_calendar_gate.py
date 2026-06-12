"""Tests for the earnings-calendar gate (V1.2 §R)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_EARNINGS_WINDOW,
    DEFAULT_EARNINGS_BLOCK_DAYS,
    EarningsGateInputs,
    evaluate_earnings_calendar_gate,
)

_TODAY = date(2025, 4, 15)


def _inputs(*, days_to_earnings: int | None = None) -> EarningsGateInputs:
    if days_to_earnings is None:
        return EarningsGateInputs(
            symbol="AAPL", today=_TODAY, next_earnings_date=None
        )
    return EarningsGateInputs(
        symbol="AAPL",
        today=_TODAY,
        next_earnings_date=_TODAY + timedelta(days=days_to_earnings),
    )


# ---- default doctrinal defaults --------------------------------------


def test_default_block_window_is_5() -> None:
    assert DEFAULT_EARNINGS_BLOCK_DAYS == 5


# ---- block window ----------------------------------------------------


def test_earnings_tomorrow_blocked() -> None:
    result = evaluate_earnings_calendar_gate(_inputs(days_to_earnings=1))
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_EARNINGS_WINDOW
    assert result.days_to_earnings == 1


def test_earnings_today_blocked() -> None:
    result = evaluate_earnings_calendar_gate(_inputs(days_to_earnings=0))
    assert not result.allowed
    assert result.days_to_earnings == 0


def test_earnings_in_5_days_blocked_at_default_window() -> None:
    # Doctrine: <= block window blocks (5 means 5 days still inside).
    result = evaluate_earnings_calendar_gate(_inputs(days_to_earnings=5))
    assert not result.allowed
    assert result.days_to_earnings == 5


def test_earnings_in_6_days_passes_at_default_window() -> None:
    # Doctrine: > block window allows.
    result = evaluate_earnings_calendar_gate(_inputs(days_to_earnings=6))
    assert result.allowed
    assert result.blocking_reason is None
    assert result.days_to_earnings == 6


def test_earnings_in_30_days_passes() -> None:
    result = evaluate_earnings_calendar_gate(_inputs(days_to_earnings=30))
    assert result.allowed
    assert result.days_to_earnings == 30


# ---- missing data ----------------------------------------------------


def test_no_earnings_date_passes() -> None:
    # Missing data is allowed — see module docstring.
    result = evaluate_earnings_calendar_gate(_inputs(days_to_earnings=None))
    assert result.allowed
    assert result.blocking_reason is None
    assert result.days_to_earnings is None


def test_earnings_in_the_past_passes() -> None:
    # Provider hasn't updated; treat as missing.
    result = evaluate_earnings_calendar_gate(_inputs(days_to_earnings=-10))
    assert result.allowed
    assert result.days_to_earnings == -10


# ---- custom window ---------------------------------------------------


def test_custom_block_window_3_days() -> None:
    # With a 3-day window, 4 days out should pass.
    result = evaluate_earnings_calendar_gate(
        _inputs(days_to_earnings=4), days_to_earnings_block=3
    )
    assert result.allowed
    result = evaluate_earnings_calendar_gate(
        _inputs(days_to_earnings=3), days_to_earnings_block=3
    )
    assert not result.allowed


def test_zero_window_disables_gate() -> None:
    # Even tomorrow's earnings allowed when window=0.
    result = evaluate_earnings_calendar_gate(
        _inputs(days_to_earnings=1), days_to_earnings_block=0
    )
    assert result.allowed


# ---- input validation ------------------------------------------------


def test_negative_window_rejected() -> None:
    with pytest.raises(ValueError):
        evaluate_earnings_calendar_gate(
            _inputs(days_to_earnings=5), days_to_earnings_block=-1
        )
