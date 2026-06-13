"""Tests for the take-profit signal monitor (V1.2 §AR)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio_outlook_portfolio import (
    DEFAULT_TAKE_PROFIT_NET_PCT,
    SIGNAL_HOLD,
    SIGNAL_SUGGEST_SELL,
    TakeProfitForecastContext,
    TakeProfitSignalInputs,
    evaluate_take_profit_signal,
)


def _inputs(
    *,
    ticker: str = "AAPL",
    entry_price: Decimal = Decimal("100"),
    current_price: Decimal = Decimal("100"),
    quantity: int = 10,
    target_net_pct: Decimal = DEFAULT_TAKE_PROFIT_NET_PCT,
    expected_net_proceeds_eur: Decimal | None = None,
    short_term_forecast: TakeProfitForecastContext | None = None,
) -> TakeProfitSignalInputs:
    return TakeProfitSignalInputs(
        ticker=ticker,
        entry_price=entry_price,
        current_price=current_price,
        quantity=quantity,
        target_net_pct=target_net_pct,
        expected_net_proceeds_eur=expected_net_proceeds_eur,
        short_term_forecast=short_term_forecast,
    )


# ---- target not reached → hold ----------------------------------------


def test_below_entry_returns_hold() -> None:
    result = evaluate_take_profit_signal(
        _inputs(current_price=Decimal("98"))
    )
    assert result.action == SIGNAL_HOLD
    assert result.target_reached is False
    assert result.current_pct_return == Decimal("-2.00")
    assert result.distance_to_target_pct == Decimal("6.00")
    assert "Nog 6,00%" in result.detail_nl
    assert "geen actie" in result.detail_nl.lower()


def test_at_entry_returns_hold() -> None:
    result = evaluate_take_profit_signal(_inputs())
    assert result.action == SIGNAL_HOLD
    assert result.current_pct_return == Decimal("0.00")


def test_just_below_target_returns_hold() -> None:
    # +3.99% nog niet bereikt.
    result = evaluate_take_profit_signal(
        _inputs(current_price=Decimal("103.99"))
    )
    assert result.action == SIGNAL_HOLD
    assert result.target_reached is False


# ---- target reached → suggest_sell ------------------------------------


def test_exactly_at_target_suggests_sell() -> None:
    """Doctrine: ``current ≥ entry × (1 + target/100)`` is inclusief."""

    result = evaluate_take_profit_signal(
        _inputs(current_price=Decimal("104"))
    )
    assert result.action == SIGNAL_SUGGEST_SELL
    assert result.target_reached is True
    assert result.current_pct_return == Decimal("4.00")
    assert "VERKOOP" in result.headline_nl
    assert "AAPL" in result.headline_nl
    assert "+4,00%" in result.headline_nl


def test_above_target_suggests_sell() -> None:
    # +5% — duidelijk boven target.
    result = evaluate_take_profit_signal(
        _inputs(current_price=Decimal("105"))
    )
    assert result.action == SIGNAL_SUGGEST_SELL
    assert result.current_pct_return == Decimal("5.00")
    assert "+5,00%" in result.headline_nl


# ---- forecast context inclusion --------------------------------------


def test_suggest_sell_includes_short_term_forecast_when_provided() -> None:
    forecast = TakeProfitForecastContext(
        horizon_days=3,
        p50_next=Decimal("106"),
        p_above_current_pct=Decimal("72"),
    )
    result = evaluate_take_profit_signal(
        _inputs(
            current_price=Decimal("104"),
            short_term_forecast=forecast,
        )
    )
    assert "forecast komende 3 dagen" in result.detail_nl
    assert "p50 €106" in result.detail_nl
    assert "kans op verdere stijging 72,00%" in result.detail_nl
    assert "nu verkopen of nog wachten" in result.detail_nl


def test_suggest_sell_without_forecast_says_operator_decides() -> None:
    result = evaluate_take_profit_signal(
        _inputs(current_price=Decimal("104"))
    )
    assert "Geen korte-termijn forecast beschikbaar" in result.detail_nl
    assert "Operator beslist" in result.detail_nl


def test_suggest_sell_with_partial_forecast_only_includes_present_fields() -> None:
    """Als één veld van de forecast ontbreekt, geen fictie."""

    forecast = TakeProfitForecastContext(
        horizon_days=3,
        p50_next=Decimal("106"),
        p_above_current_pct=None,
    )
    result = evaluate_take_profit_signal(
        _inputs(
            current_price=Decimal("104"),
            short_term_forecast=forecast,
        )
    )
    assert "p50 €106" in result.detail_nl
    assert "kans op verdere stijging" not in result.detail_nl


def test_expected_net_proceeds_passes_through() -> None:
    result = evaluate_take_profit_signal(
        _inputs(
            current_price=Decimal("104"),
            expected_net_proceeds_eur=Decimal("1485"),
        )
    )
    assert result.expected_net_proceeds_eur == Decimal("1485")


# ---- custom target ----------------------------------------------------


def test_custom_target_pct_respected() -> None:
    # +6% target ipv +4%.
    result = evaluate_take_profit_signal(
        _inputs(
            current_price=Decimal("105"),
            target_net_pct=Decimal("6"),
        )
    )
    # +5% < +6% target → hold.
    assert result.action == SIGNAL_HOLD
    assert "target +6,00%" in result.headline_nl


# ---- input validation -------------------------------------------------


def test_invalid_entry_price_raises() -> None:
    with pytest.raises(ValueError, match="entry_price"):
        evaluate_take_profit_signal(
            _inputs(entry_price=Decimal("0"))
        )


def test_invalid_current_price_raises() -> None:
    with pytest.raises(ValueError, match="current_price"):
        evaluate_take_profit_signal(
            _inputs(current_price=Decimal("-10"))
        )


def test_invalid_quantity_raises() -> None:
    with pytest.raises(ValueError, match="quantity"):
        evaluate_take_profit_signal(_inputs(quantity=0))


def test_invalid_target_raises() -> None:
    with pytest.raises(ValueError, match="target_net_pct"):
        evaluate_take_profit_signal(
            _inputs(target_net_pct=Decimal("0"))
        )


def test_non_decimal_prices_raise() -> None:
    with pytest.raises(TypeError):
        evaluate_take_profit_signal(
            TakeProfitSignalInputs(
                ticker="AAPL",
                entry_price=100,  # type: ignore[arg-type]
                current_price=Decimal("104"),
                quantity=10,
            )
        )
