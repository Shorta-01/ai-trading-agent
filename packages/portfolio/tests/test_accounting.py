from datetime import date, datetime
from decimal import Decimal

import pytest
from portfolio_outlook_domain import (
    CostEstimate,
    CostType,
    Money,
    PaperTransaction,
    Quantity,
    TransactionSide,
)

from portfolio_outlook_portfolio import (
    CurrencyMismatchError,
    InvalidAccountingInputError,
    calculate_cash_delta_for_transaction,
    calculate_net_transaction_amount,
    validate_transaction_amounts,
)


def _cost(amount: str, currency: str = "EUR") -> CostEstimate:
    return CostEstimate(
        cost_estimate_id=f"cost_{amount.replace('.','_')}_{currency}",
        cost_type=CostType.BROKER_FEE,
        amount=Money(amount=Decimal(amount), currency=currency),
    )


def _tx(side: TransactionSide, gross: str, net: str, costs: list[CostEstimate]) -> PaperTransaction:
    return PaperTransaction(
        transaction_id="tx_1",
        portfolio_id="pf_1",
        instrument_id="inst_1",
        side=side,
        status="filled",
        quantity=Quantity(value=Decimal("2")),
        price=Money(amount=Decimal("10"), currency="EUR"),
        gross_amount=Money(amount=Decimal(gross), currency="EUR"),
        net_amount=Money(amount=Decimal(net), currency="EUR"),
        costs=costs,
        occurred_at=datetime(2026, 1, 1, 10, 0, 0),
        settlement_date=date(2026, 1, 3),
        reason_nl="Papertest",
    )


def test_validate_buy_gross_net_passes() -> None:
    tx = _tx(TransactionSide.BUY, gross="20", net="20.50", costs=[_cost("0.50")])
    validate_transaction_amounts(tx)


def test_validate_sell_gross_net_passes() -> None:
    tx = _tx(TransactionSide.SELL, gross="20", net="19.50", costs=[_cost("0.50")])
    validate_transaction_amounts(tx)


def test_validate_wrong_gross_raises() -> None:
    tx = _tx(TransactionSide.BUY, gross="21", net="21.50", costs=[_cost("0.50")])
    with pytest.raises(InvalidAccountingInputError):
        validate_transaction_amounts(tx)


def test_validate_wrong_net_raises() -> None:
    tx = _tx(TransactionSide.BUY, gross="20", net="20.40", costs=[_cost("0.50")])
    with pytest.raises(InvalidAccountingInputError):
        validate_transaction_amounts(tx)


def test_validate_currency_mismatch_raises() -> None:
    tx = _tx(TransactionSide.BUY, gross="20", net="20", costs=[_cost("0.50", currency="USD")])
    with pytest.raises(CurrencyMismatchError):
        validate_transaction_amounts(tx)


def test_buy_cash_delta_is_negative() -> None:
    net = calculate_net_transaction_amount(
        TransactionSide.BUY,
        Money(amount=Decimal("20"), currency="EUR"),
        [_cost("1")],
    )
    delta = calculate_cash_delta_for_transaction(TransactionSide.BUY, net)
    assert delta == Money(amount=Decimal("-21"), currency="EUR")


def test_sell_cash_delta_is_positive() -> None:
    net = calculate_net_transaction_amount(
        TransactionSide.SELL,
        Money(amount=Decimal("20"), currency="EUR"),
        [_cost("1")],
    )
    delta = calculate_cash_delta_for_transaction(TransactionSide.SELL, net)
    assert delta == Money(amount=Decimal("19"), currency="EUR")


def test_empty_costs_allowed() -> None:
    tx = _tx(TransactionSide.BUY, gross="20", net="20", costs=[])
    validate_transaction_amounts(tx)
