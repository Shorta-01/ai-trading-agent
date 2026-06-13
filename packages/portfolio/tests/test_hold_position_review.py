"""Tests for the hold-position review (V1.2 §AQ)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio_outlook_portfolio import (
    DEFAULT_HORIZON_REVIEW_START_DAYS,
    DEFAULT_LOSS_FLOOR_PCT,
    DEFAULT_TARGET_NET_PCT,
    HOLD_ACTION_HOLD,
    HOLD_ACTION_SUGGEST_SELL,
    HoldPositionReviewInputs,
    evaluate_hold_position_review,
)


def _inputs(
    *,
    ticker: str = "AAPL",
    entry_price: Decimal = Decimal("100"),
    current_price: Decimal = Decimal("100"),
    days_held: int = 30,
    forecast_p50: Decimal = Decimal("108"),
    target_net_pct: Decimal = DEFAULT_TARGET_NET_PCT,
    horizon_review_start_days: int = DEFAULT_HORIZON_REVIEW_START_DAYS,
    loss_floor_pct: Decimal = DEFAULT_LOSS_FLOOR_PCT,
) -> HoldPositionReviewInputs:
    return HoldPositionReviewInputs(
        ticker=ticker,
        entry_price=entry_price,
        current_price=current_price,
        days_held=days_held,
        forecast_p50=forecast_p50,
        target_net_pct=target_net_pct,
        horizon_review_start_days=horizon_review_start_days,
        loss_floor_pct=loss_floor_pct,
    )


# ---- hold-window invariants (0-6 months) -------------------------------


def test_within_hold_window_action_is_hold_regardless_of_price() -> None:
    """Doctrine: tijdens 0-6m blijven we houden ongeacht prijsverloop."""

    for current in (Decimal("80"), Decimal("100"), Decimal("130")):
        result = evaluate_hold_position_review(
            _inputs(current_price=current, days_held=90)
        )
        assert result.action == HOLD_ACTION_HOLD
        assert "Binnen 6-maanden" in result.blocking_reason_nl


def test_within_hold_window_diagnostics_still_populated() -> None:
    """Hold-fase moet dashboard nog steeds van diagnostiek voorzien."""

    result = evaluate_hold_position_review(
        _inputs(current_price=Decimal("92"), days_held=30)
    )
    assert result.current_pct_return == Decimal("-8")
    # -8 ≤ -5 floor → in loss
    assert result.position_in_loss is True
    # Forecast p50 (108) ≥ target (100 × 1.04 = 104) → still above
    assert result.forecaster_above_target is True


def test_at_horizon_boundary_minus_one_still_holds() -> None:
    # Exactly one day shy of the review-start: still in hold window.
    result = evaluate_hold_position_review(
        _inputs(days_held=DEFAULT_HORIZON_REVIEW_START_DAYS - 1)
    )
    assert result.action == HOLD_ACTION_HOLD


# ---- after 6 months: combo-trigger ------------------------------------


def test_after_horizon_both_conditions_true_suggests_sell() -> None:
    """Forecast onder target én positie in verlies → SELL-suggestie."""

    result = evaluate_hold_position_review(
        _inputs(
            entry_price=Decimal("100"),
            current_price=Decimal("93"),  # -7% in loss
            days_held=200,
            forecast_p50=Decimal("96"),  # below target of 104
        )
    )
    assert result.action == HOLD_ACTION_SUGGEST_SELL
    assert result.forecaster_above_target is False
    assert result.position_in_loss is True
    assert "Outlook verslechterd" in result.blocking_reason_nl
    assert "Overweeg te verkopen" in result.blocking_reason_nl


def test_after_horizon_only_forecast_negative_still_holds() -> None:
    """Forecast verzwakt maar positie nog niet in verlies → hold."""

    result = evaluate_hold_position_review(
        _inputs(
            entry_price=Decimal("100"),
            current_price=Decimal("98"),  # -2% — niet onder -5 floor
            days_held=200,
            forecast_p50=Decimal("96"),  # below target
        )
    )
    assert result.action == HOLD_ACTION_HOLD
    assert result.forecaster_above_target is False
    assert result.position_in_loss is False
    assert "Forecast verzwakt" in result.blocking_reason_nl
    assert "niet voldoende" in result.blocking_reason_nl


def test_after_horizon_only_loss_still_holds() -> None:
    """Positie in verlies maar forecast nog upside → hold."""

    result = evaluate_hold_position_review(
        _inputs(
            entry_price=Decimal("100"),
            current_price=Decimal("92"),  # -8% in loss
            days_held=200,
            forecast_p50=Decimal("108"),  # above target of 104
        )
    )
    assert result.action == HOLD_ACTION_HOLD
    assert result.forecaster_above_target is True
    assert result.position_in_loss is True
    assert "Wachten op herstel" in result.blocking_reason_nl


def test_after_horizon_both_conditions_false_still_holds() -> None:
    """Outlook nog positief én positie boven instap → hold."""

    result = evaluate_hold_position_review(
        _inputs(
            entry_price=Decimal("100"),
            current_price=Decimal("102"),  # +2%
            days_held=200,
            forecast_p50=Decimal("108"),  # above target
        )
    )
    assert result.action == HOLD_ACTION_HOLD
    assert result.forecaster_above_target is True
    assert result.position_in_loss is False
    assert "Outlook nog positief" in result.blocking_reason_nl


# ---- boundary conditions ----------------------------------------------


def test_loss_at_exactly_5pct_triggers_loss_condition() -> None:
    """De doctrine zegt ≥ -5% (inclusief). Bij precies -5 moet
    ``position_in_loss = True``."""

    result = evaluate_hold_position_review(
        _inputs(
            entry_price=Decimal("100"),
            current_price=Decimal("95"),  # exact -5
            days_held=200,
            forecast_p50=Decimal("90"),  # forecast also below target
        )
    )
    assert result.position_in_loss is True
    assert result.action == HOLD_ACTION_SUGGEST_SELL


def test_forecast_at_exactly_target_does_not_trigger_negative() -> None:
    """``forecast_p50 ≥ target_price`` blijft positief; precies gelijk
    aan target is een upside van precies +4%, dus positief."""

    target_price = Decimal("104")  # 100 × 1.04
    result = evaluate_hold_position_review(
        _inputs(
            entry_price=Decimal("100"),
            current_price=Decimal("92"),
            days_held=200,
            forecast_p50=target_price,
        )
    )
    assert result.forecaster_above_target is True
    assert result.action == HOLD_ACTION_HOLD


def test_custom_loss_floor_respected() -> None:
    """Operator kan een striktere loss-floor instellen (b.v. -10%) en
    de doctrine moet die honoreren."""

    result = evaluate_hold_position_review(
        _inputs(
            entry_price=Decimal("100"),
            current_price=Decimal("93"),  # -7%
            days_held=200,
            forecast_p50=Decimal("90"),
            loss_floor_pct=Decimal("-10"),  # strikter
        )
    )
    # -7% ligt nog boven de strengere -10% floor → niet in loss
    assert result.position_in_loss is False
    assert result.action == HOLD_ACTION_HOLD


def test_custom_horizon_window_respected() -> None:
    """Operator kan een kortere of langere review-start instellen."""

    # 3-maanden review-start: positie 100 dagen oud is buiten venster.
    result = evaluate_hold_position_review(
        _inputs(
            entry_price=Decimal("100"),
            current_price=Decimal("93"),
            days_held=100,
            forecast_p50=Decimal("96"),
            horizon_review_start_days=90,
        )
    )
    assert result.action == HOLD_ACTION_SUGGEST_SELL


# ---- input validation -------------------------------------------------


def test_negative_entry_price_raises() -> None:
    with pytest.raises(ValueError, match="entry_price"):
        evaluate_hold_position_review(
            _inputs(entry_price=Decimal("-100"))
        )


def test_zero_current_price_raises() -> None:
    with pytest.raises(ValueError, match="current_price"):
        evaluate_hold_position_review(
            _inputs(current_price=Decimal("0"))
        )


def test_negative_days_held_raises() -> None:
    with pytest.raises(ValueError, match="days_held"):
        evaluate_hold_position_review(_inputs(days_held=-1))


def test_negative_target_net_pct_raises() -> None:
    with pytest.raises(ValueError, match="target_net_pct"):
        evaluate_hold_position_review(
            _inputs(target_net_pct=Decimal("-1"))
        )
