from collections.abc import Sequence
from decimal import Decimal

from portfolio_outlook_domain import CurrencyCode, Money, Quantity

from .errors import CurrencyMismatchError, InvalidAccountingInputError


def ensure_same_currency(*amounts: Money) -> CurrencyCode:
    if not amounts:
        raise InvalidAccountingInputError("At least one Money value is required.")

    currency = amounts[0].currency
    for amount in amounts[1:]:
        if amount.currency != currency:
            raise CurrencyMismatchError("All Money values must share the same currency.")
    return currency


def add_money(amounts: Sequence[Money]) -> Money:
    if not amounts:
        raise InvalidAccountingInputError("add_money requires at least one Money value.")

    currency = ensure_same_currency(*amounts)
    total = sum((amount.amount for amount in amounts), start=Decimal("0"))
    return Money(amount=total, currency=currency)


def subtract_money(left: Money, right: Money) -> Money:
    ensure_same_currency(left, right)
    return Money(amount=left.amount - right.amount, currency=left.currency)


def multiply_quantity_by_price(quantity: Quantity, price: Money) -> Money:
    if quantity.value <= Decimal("0"):
        raise InvalidAccountingInputError("quantity must be greater than zero.")
    if price.amount < Decimal("0"):
        raise InvalidAccountingInputError("price amount must be zero or positive.")

    return Money(amount=quantity.value * price.amount, currency=price.currency)
