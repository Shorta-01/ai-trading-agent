from decimal import Decimal

import pytest
from portfolio_outlook_domain import Money, Quantity
from pydantic import ValidationError

from portfolio_outlook_portfolio import (
    CurrencyMismatchError,
    InvalidAccountingInputError,
    add_money,
    multiply_quantity_by_price,
    subtract_money,
)


def test_add_money_same_currency() -> None:
    result = add_money([
        Money(amount=Decimal("10.10"), currency="EUR"),
        Money(amount=Decimal("2.90"), currency="EUR"),
    ])
    assert result == Money(amount=Decimal("13.00"), currency="EUR")


def test_add_money_currency_mismatch_raises() -> None:
    with pytest.raises(CurrencyMismatchError):
        add_money([
            Money(amount=Decimal("10"), currency="EUR"),
            Money(amount=Decimal("2"), currency="USD"),
        ])


def test_add_money_empty_input_raises() -> None:
    with pytest.raises(InvalidAccountingInputError):
        add_money([])


def test_subtract_money_works() -> None:
    result = subtract_money(
        Money(amount=Decimal("10"), currency="EUR"),
        Money(amount=Decimal("2.50"), currency="EUR"),
    )
    assert result == Money(amount=Decimal("7.50"), currency="EUR")


def test_multiply_quantity_by_price_works() -> None:
    result = multiply_quantity_by_price(
        quantity=Quantity(value=Decimal("3")),
        price=Money(amount=Decimal("15.25"), currency="EUR"),
    )
    assert result == Money(amount=Decimal("45.75"), currency="EUR")


def test_multiply_zero_quantity_raises() -> None:
    with pytest.raises(InvalidAccountingInputError):
        multiply_quantity_by_price(
            quantity=Quantity(value=Decimal("0")),
            price=Money(amount=Decimal("15.25"), currency="EUR"),
        )


def test_multiply_negative_price_raises() -> None:
    with pytest.raises(InvalidAccountingInputError):
        multiply_quantity_by_price(
            quantity=Quantity(value=Decimal("1")),
            price=Money(amount=Decimal("-1"), currency="EUR"),
        )


def test_domain_primitives_reject_float_input() -> None:
    with pytest.raises(ValidationError):
        Money(amount=1.25, currency="EUR")
    with pytest.raises(ValidationError):
        Quantity(value=1.5)
