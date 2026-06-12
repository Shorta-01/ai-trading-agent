"""Tests for the take-profit pair → submission inputs adapter (V1.2 §U)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from portfolio_outlook_portfolio import (
    TobSecurityClass,
    build_take_profit_pair,
)

from portfolio_outlook_api.take_profit_submission_adapter import (
    DEFAULT_BUY_ACTION_SIDE,
    DEFAULT_CURRENCY,
    DEFAULT_PRIMARY_EXCHANGE,
    DEFAULT_SECURITY_TYPE,
    pair_to_submission_inputs,
)


def _build_pair() -> object:
    result = build_take_profit_pair(
        ticker="AAPL",
        entry_lmt_price=Decimal("100"),
        intended_position_eur=Decimal("25000"),
        target_net_pct=Decimal("4"),
        security_class=TobSecurityClass.STANDARD_STOCK,
    )
    assert result.pair is not None
    return result.pair


# ---- happy path ------------------------------------------------------


def test_adapter_emits_bracket_with_no_stop_loss() -> None:
    pair = _build_pair()
    converted = pair_to_submission_inputs(pair)  # type: ignore[arg-type]
    inputs = converted.inputs
    assert inputs.symbol == "AAPL"
    assert inputs.action_side == DEFAULT_BUY_ACTION_SIDE
    assert inputs.security_type == DEFAULT_SECURITY_TYPE
    assert inputs.currency == DEFAULT_CURRENCY
    assert inputs.primary_exchange == DEFAULT_PRIMARY_EXCHANGE
    assert inputs.order_type == "BRACKET"
    assert inputs.limit_price == Decimal("100")
    assert inputs.bracket_take_profit_limit_price == Decimal("104.7300")
    # Locked doctrine signal: no stop-loss.
    assert inputs.bracket_stop_loss_price is None
    assert inputs.quantity == Decimal("249")


def test_adapter_accepts_custom_routing() -> None:
    pair = _build_pair()
    converted = pair_to_submission_inputs(
        pair,  # type: ignore[arg-type]
        primary_exchange="ARCA",
        currency="USD",
        security_type="STK",
    )
    assert converted.inputs.primary_exchange == "ARCA"


# ---- invariant guards ------------------------------------------------


def test_adapter_rejects_zero_qty() -> None:
    pair = _build_pair()
    bad = type(pair)(  # type: ignore[arg-type, operator]
        **{**pair.__dict__, "qty": 0}  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError):
        pair_to_submission_inputs(bad)


def test_adapter_rejects_take_profit_at_or_below_entry() -> None:
    pair = _build_pair()
    bad = type(pair)(  # type: ignore[arg-type, operator]
        **{
            **pair.__dict__,
            "take_profit_sell_price": Decimal("99"),
        }
    )
    with pytest.raises(ValueError):
        pair_to_submission_inputs(bad)


def test_adapter_rejects_empty_routing_fields() -> None:
    pair = _build_pair()
    with pytest.raises(ValueError):
        pair_to_submission_inputs(
            pair, primary_exchange=""  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError):
        pair_to_submission_inputs(
            pair, currency="   "  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError):
        pair_to_submission_inputs(
            pair, security_type=""  # type: ignore[arg-type]
        )
