from collections.abc import Sequence
from decimal import Decimal

from portfolio_outlook_domain import (
    CostEstimate,
    CurrencyCode,
    Money,
    PaperTransaction,
    Quantity,
    TransactionSide,
)

from .errors import CurrencyMismatchError, InvalidAccountingInputError
from .money import add_money, ensure_same_currency, multiply_quantity_by_price


def calculate_gross_amount(quantity: Quantity, price: Money) -> Money:
    return multiply_quantity_by_price(quantity, price)


def calculate_total_costs(costs: Sequence[CostEstimate], currency: CurrencyCode) -> Money:
    if not costs:
        return Money(amount=Decimal("0"), currency=currency)

    amounts = [cost.amount for cost in costs]
    shared_currency = ensure_same_currency(*amounts)
    if shared_currency != currency:
        raise CurrencyMismatchError("Cost currency must match requested transaction currency.")

    return add_money(amounts)


def calculate_net_transaction_amount(
    side: TransactionSide,
    gross_amount: Money,
    costs: Sequence[CostEstimate],
) -> Money:
    total_costs = calculate_total_costs(costs, gross_amount.currency)
    if side is TransactionSide.BUY:
        return Money(
            amount=gross_amount.amount + total_costs.amount,
            currency=gross_amount.currency,
        )
    if side is TransactionSide.SELL:
        return Money(
            amount=gross_amount.amount - total_costs.amount,
            currency=gross_amount.currency,
        )
    raise InvalidAccountingInputError(f"Unsupported transaction side: {side}")


def calculate_cash_delta_for_transaction(side: TransactionSide, net_amount: Money) -> Money:
    if side is TransactionSide.BUY:
        return Money(amount=-net_amount.amount, currency=net_amount.currency)
    if side is TransactionSide.SELL:
        return Money(amount=net_amount.amount, currency=net_amount.currency)
    raise InvalidAccountingInputError(f"Unsupported transaction side: {side}")


def validate_transaction_amounts(transaction: PaperTransaction) -> None:
    ensure_same_currency(transaction.price, transaction.gross_amount, transaction.net_amount)

    calculated_gross = calculate_gross_amount(transaction.quantity, transaction.price)
    if calculated_gross != transaction.gross_amount:
        raise InvalidAccountingInputError(
            "transaction.gross_amount does not match quantity * price."
        )

    calculated_net = calculate_net_transaction_amount(
        side=transaction.side,
        gross_amount=transaction.gross_amount,
        costs=transaction.costs,
    )
    if calculated_net != transaction.net_amount:
        raise InvalidAccountingInputError(
            "transaction.net_amount does not match side, gross_amount and costs."
        )
