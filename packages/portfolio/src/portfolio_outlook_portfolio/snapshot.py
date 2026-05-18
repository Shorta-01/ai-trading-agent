from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from portfolio_outlook_domain import (
    CashLedgerEntry,
    InstrumentId,
    Money,
    PaperTransaction,
    PortfolioId,
    Quantity,
    TransactionSide,
    TransactionStatus,
)

from .errors import CurrencyMismatchError, InvalidAccountingInputError
from .money import add_money


@dataclass(frozen=True)
class InstrumentPositionQuantity:
    instrument_id: InstrumentId
    quantity: Quantity


@dataclass(frozen=True)
class InstrumentTransactionTotals:
    instrument_id: InstrumentId
    bought_quantity: Quantity
    sold_quantity: Quantity
    buy_gross_amount: Money | None
    sell_gross_amount: Money | None


@dataclass(frozen=True)
class PaperPortfolioSnapshot:
    portfolio_id: PortfolioId
    cash_balances: dict[str, Money]
    positions: dict[str, InstrumentPositionQuantity]
    transaction_totals: dict[str, InstrumentTransactionTotals]


@dataclass
class _TotalsBucket:
    bought: Decimal
    sold: Decimal
    buy_amounts: list[Money]
    sell_amounts: list[Money]
    buy_currency: str | None
    sell_currency: str | None


def calculate_cash_balances(entries: Sequence[CashLedgerEntry]) -> dict[str, Money]:
    grouped: dict[str, list[Money]] = {}
    for entry in entries:
        grouped.setdefault(entry.amount.currency, []).append(entry.amount)

    return {currency: add_money(amounts) for currency, amounts in grouped.items()}


def calculate_position_quantities(
    transactions: Sequence[PaperTransaction],
) -> dict[str, InstrumentPositionQuantity]:
    quantities: dict[str, Decimal] = {}

    for tx in transactions:
        if tx.status is not TransactionStatus.FILLED:
            continue

        instrument_id = tx.instrument_id
        current = quantities.get(instrument_id, Decimal("0"))

        if tx.side is TransactionSide.BUY:
            next_value = current + tx.quantity.value
        elif tx.side is TransactionSide.SELL:
            next_value = current - tx.quantity.value
            if next_value < Decimal("0"):
                raise InvalidAccountingInputError(
                    f"Sell quantity exceeds current position for instrument {instrument_id}."
                )
        else:
            raise InvalidAccountingInputError(f"Unsupported transaction side: {tx.side}")

        quantities[instrument_id] = next_value

    return {
        instrument_id: InstrumentPositionQuantity(
            instrument_id=instrument_id,
            quantity=Quantity(value=quantity),
        )
        for instrument_id, quantity in quantities.items()
        if quantity > Decimal("0")
    }


def calculate_transaction_totals(
    transactions: Sequence[PaperTransaction],
) -> dict[str, InstrumentTransactionTotals]:
    state: dict[str, _TotalsBucket] = {}

    for tx in transactions:
        if tx.status is not TransactionStatus.FILLED:
            continue

        instrument_id = tx.instrument_id
        if instrument_id not in state:
            state[instrument_id] = _TotalsBucket(
                bought=Decimal("0"),
                sold=Decimal("0"),
                buy_amounts=[],
                sell_amounts=[],
                buy_currency=None,
                sell_currency=None,
            )

        bucket = state[instrument_id]
        if tx.side is TransactionSide.BUY:
            bucket.bought += tx.quantity.value
            if bucket.buy_currency is None:
                bucket.buy_currency = tx.gross_amount.currency
            elif bucket.buy_currency != tx.gross_amount.currency:
                raise CurrencyMismatchError(
                    f"Buy gross amounts for instrument {instrument_id} must use one currency."
                )
            bucket.buy_amounts.append(tx.gross_amount)
        elif tx.side is TransactionSide.SELL:
            bucket.sold += tx.quantity.value
            if bucket.sell_currency is None:
                bucket.sell_currency = tx.gross_amount.currency
            elif bucket.sell_currency != tx.gross_amount.currency:
                raise CurrencyMismatchError(
                    f"Sell gross amounts for instrument {instrument_id} must use one currency."
                )
            bucket.sell_amounts.append(tx.gross_amount)
        else:
            raise InvalidAccountingInputError(f"Unsupported transaction side: {tx.side}")

    totals: dict[str, InstrumentTransactionTotals] = {}
    for instrument_id, bucket in state.items():
        totals[instrument_id] = InstrumentTransactionTotals(
            instrument_id=instrument_id,
            bought_quantity=Quantity(value=bucket.bought),
            sold_quantity=Quantity(value=bucket.sold),
            buy_gross_amount=add_money(bucket.buy_amounts) if bucket.buy_amounts else None,
            sell_gross_amount=add_money(bucket.sell_amounts) if bucket.sell_amounts else None,
        )

    return totals


def validate_no_oversells(transactions: Sequence[PaperTransaction]) -> None:
    filled = [tx for tx in transactions if tx.status is TransactionStatus.FILLED]
    ordered = sorted(enumerate(filled), key=lambda item: (item[1].occurred_at, item[0]))

    running: dict[str, Decimal] = {}
    for _, tx in ordered:
        instrument_id = tx.instrument_id
        current = running.get(instrument_id, Decimal("0"))

        if tx.side is TransactionSide.BUY:
            running[instrument_id] = current + tx.quantity.value
        elif tx.side is TransactionSide.SELL:
            next_value = current - tx.quantity.value
            if next_value < Decimal("0"):
                message = (
                    "Oversell detected for instrument "
                    f"{instrument_id} at {tx.occurred_at.isoformat()}."
                )
                raise InvalidAccountingInputError(message)
            running[instrument_id] = next_value
        else:
            raise InvalidAccountingInputError(f"Unsupported transaction side: {tx.side}")


def build_paper_portfolio_snapshot(
    *,
    portfolio_id: PortfolioId,
    cash_entries: Sequence[CashLedgerEntry],
    transactions: Sequence[PaperTransaction],
) -> PaperPortfolioSnapshot:
    for entry in cash_entries:
        if entry.portfolio_id != portfolio_id:
            raise InvalidAccountingInputError(
                "All cash entries must match the requested portfolio_id."
            )

    for tx in transactions:
        if tx.portfolio_id != portfolio_id:
            raise InvalidAccountingInputError(
                "All transactions must match the requested portfolio_id."
            )

    validate_no_oversells(transactions)

    return PaperPortfolioSnapshot(
        portfolio_id=portfolio_id,
        cash_balances=calculate_cash_balances(cash_entries),
        positions=calculate_position_quantities(transactions),
        transaction_totals=calculate_transaction_totals(transactions),
    )
