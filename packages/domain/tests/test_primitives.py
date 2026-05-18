from decimal import Decimal

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import Money, Percentage, Quantity


def test_money_accepts_decimal_and_string() -> None:
    m1 = Money(amount=Decimal("10.50"), currency="EUR")
    m2 = Money(amount="15.75", currency="USD")
    assert m1.amount == Decimal("10.50")
    assert m2.amount == Decimal("15.75")


def test_money_rejects_float() -> None:
    with pytest.raises(ValidationError):
        Money(amount=10.5, currency="EUR")


def test_currency_code_rejects_lowercase_and_invalid() -> None:
    with pytest.raises(ValidationError):
        Money(amount="1", currency="eur")
    with pytest.raises(ValidationError):
        Money(amount="1", currency="EU")


def test_money_display() -> None:
    assert Money(amount="1000", currency="EUR").display == "1000.00 EUR"


def test_percentage_and_quantity_validation() -> None:
    assert Percentage(value="20").value == Decimal("20")
    with pytest.raises(ValidationError):
        Percentage(value="NaN")
    assert Quantity(value="0").value == Decimal("0")
    with pytest.raises(ValidationError):
        Quantity(value="-1")
