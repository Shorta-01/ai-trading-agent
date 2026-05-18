from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import (
    CostEstimate,
    CostType,
    ExecutionFill,
    Money,
    OrderStatus,
    OrderType,
    PaperLiveMode,
    PaperOrder,
    Quantity,
    TransactionSide,
)


def _order(**kwargs: object) -> PaperOrder:
    base = dict(
        order_id="ord_1",
        portfolio_id="pf_1",
        instrument_id="inst_1",
        side=TransactionSide.BUY,
        order_type=OrderType.MARKET,
        status=OrderStatus.PENDING,
        requested_amount=Money(amount=Decimal("100"), currency="EUR"),
        created_at=datetime(2026, 1, 1, 10, 0, 0),
        reason_nl="Instap in paper portefeuille",
    )
    base.update(kwargs)
    return PaperOrder(**base)


def test_market_order_with_requested_amount_accepted() -> None:
    assert _order().order_type == OrderType.MARKET


def test_limit_order_with_limit_price_accepted() -> None:
    order = _order(
        order_type=OrderType.LIMIT,
        requested_amount=None,
        requested_quantity=Quantity(value=Decimal("2")),
        limit_price=Money(amount=Decimal("42"), currency="EUR"),
    )
    assert order.limit_price is not None


def test_limit_order_without_limit_price_rejected() -> None:
    with pytest.raises(ValidationError):
        _order(order_type=OrderType.LIMIT)


def test_order_with_neither_amount_nor_quantity_rejected() -> None:
    with pytest.raises(ValidationError):
        _order(requested_amount=None, requested_quantity=None)


def test_non_paper_mode_rejected() -> None:
    with pytest.raises(ValidationError):
        _order(mode=PaperLiveMode.LIVE_READ_ONLY)


def test_empty_reason_rejected() -> None:
    with pytest.raises(ValidationError):
        _order(reason_nl="")


def test_valid_fill_accepted() -> None:
    fill = ExecutionFill(
        fill_id="fill_1",
        order_id="ord_1",
        filled_quantity=Quantity(value=Decimal("1")),
        fill_price=Money(amount=Decimal("50"), currency="EUR"),
        gross_amount=Money(amount=Decimal("50"), currency="EUR"),
        costs=[
            CostEstimate(
                cost_estimate_id="cost_1",
                cost_type=CostType.BROKER_FEE,
                amount=Money(amount=Decimal("0.50"), currency="EUR"),
            )
        ],
        filled_at=datetime(2026, 1, 1, 10, 5, 0),
        status_after_fill=OrderStatus.FILLED,
    )
    assert fill.status_after_fill == OrderStatus.FILLED


def test_fill_with_gross_currency_mismatch_rejected() -> None:
    with pytest.raises(ValidationError):
        ExecutionFill(
            fill_id="fill_1",
            order_id="ord_1",
            filled_quantity=Quantity(value=Decimal("1")),
            fill_price=Money(amount=Decimal("50"), currency="EUR"),
            gross_amount=Money(amount=Decimal("50"), currency="USD"),
            costs=[],
            filled_at=datetime(2026, 1, 1, 10, 5, 0),
            status_after_fill=OrderStatus.FILLED,
        )


def test_fill_with_invalid_status_after_fill_rejected() -> None:
    with pytest.raises(ValidationError):
        ExecutionFill(
            fill_id="fill_1",
            order_id="ord_1",
            filled_quantity=Quantity(value=Decimal("1")),
            fill_price=Money(amount=Decimal("50"), currency="EUR"),
            gross_amount=Money(amount=Decimal("50"), currency="EUR"),
            costs=[],
            filled_at=datetime(2026, 1, 1, 10, 5, 0),
            status_after_fill=OrderStatus.CANCELLED,
        )


def test_order_model_dump_contains_decimal() -> None:
    dumped = _order().model_dump()
    assert dumped["requested_amount"]["amount"] == Decimal("100")
