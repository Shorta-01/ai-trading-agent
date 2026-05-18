from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal

from portfolio_outlook_domain import (
    CashLedgerEntry,
    CostEstimate,
    InstrumentId,
    LedgerEntryId,
    LedgerEntryType,
    Money,
    OrderId,
    PaperLiveMode,
    PaperTransaction,
    PortfolioId,
    Quantity,
    RunId,
    SuggestionId,
    TransactionId,
    TransactionSide,
    TransactionStatus,
)

from .accounting import (
    calculate_cash_delta_for_transaction,
    calculate_gross_amount,
    calculate_net_transaction_amount,
    validate_transaction_amounts,
)
from .errors import CurrencyMismatchError, InvalidAccountingInputError


def _require_non_empty_reason(reason_nl: str) -> str:
    if not reason_nl.strip():
        raise InvalidAccountingInputError("reason_nl is required")
    return reason_nl


def create_deposit_cash_entry(
    *,
    ledger_entry_id: LedgerEntryId,
    portfolio_id: PortfolioId,
    amount: Money,
    occurred_at: datetime,
    reason_nl: str,
    source_run_id: RunId | None = None,
) -> CashLedgerEntry:
    _require_non_empty_reason(reason_nl)
    if amount.amount <= Decimal("0"):
        raise InvalidAccountingInputError("Deposit amount must be positive.")

    return CashLedgerEntry(
        ledger_entry_id=ledger_entry_id,
        portfolio_id=portfolio_id,
        entry_type=LedgerEntryType.DEPOSIT,
        amount=amount,
        occurred_at=occurred_at,
        reason_nl=reason_nl,
        source_run_id=source_run_id,
    )


def create_withdrawal_cash_entry(
    *,
    ledger_entry_id: LedgerEntryId,
    portfolio_id: PortfolioId,
    amount: Money,
    occurred_at: datetime,
    reason_nl: str,
    source_run_id: RunId | None = None,
) -> CashLedgerEntry:
    _require_non_empty_reason(reason_nl)
    if amount.amount <= Decimal("0"):
        raise InvalidAccountingInputError("Withdrawal amount must be positive input.")

    return CashLedgerEntry(
        ledger_entry_id=ledger_entry_id,
        portfolio_id=portfolio_id,
        entry_type=LedgerEntryType.WITHDRAWAL,
        amount=Money(amount=-amount.amount, currency=amount.currency),
        occurred_at=occurred_at,
        reason_nl=reason_nl,
        source_run_id=source_run_id,
    )


def build_paper_transaction(
    *,
    transaction_id: TransactionId,
    portfolio_id: PortfolioId,
    instrument_id: InstrumentId,
    side: TransactionSide,
    quantity: Quantity,
    price: Money,
    costs: Sequence[CostEstimate],
    occurred_at: datetime,
    reason_nl: str,
    settlement_date: date | None = None,
    related_order_id: OrderId | None = None,
    related_suggestion_id: SuggestionId | None = None,
) -> PaperTransaction:
    _require_non_empty_reason(reason_nl)
    if quantity.value <= Decimal("0"):
        raise InvalidAccountingInputError("quantity must be greater than zero.")
    if price.amount < Decimal("0"):
        raise InvalidAccountingInputError("price amount must be zero or positive.")

    gross_amount = calculate_gross_amount(quantity=quantity, price=price)
    net_amount = calculate_net_transaction_amount(side=side, gross_amount=gross_amount, costs=costs)

    transaction = PaperTransaction(
        transaction_id=transaction_id,
        portfolio_id=portfolio_id,
        instrument_id=instrument_id,
        side=side,
        status=TransactionStatus.FILLED,
        quantity=quantity,
        price=price,
        gross_amount=gross_amount,
        net_amount=net_amount,
        costs=list(costs),
        occurred_at=occurred_at,
        settlement_date=settlement_date,
        reason_nl=reason_nl,
        related_order_id=related_order_id,
        related_suggestion_id=related_suggestion_id,
        mode=PaperLiveMode.PAPER,
    )
    validate_transaction_amounts(transaction)
    return transaction


def create_cash_entry_for_transaction(
    *,
    ledger_entry_id: LedgerEntryId,
    transaction: PaperTransaction,
    occurred_at: datetime | None = None,
    reason_nl: str | None = None,
    source_run_id: RunId | None = None,
) -> CashLedgerEntry:
    resolved_reason = transaction.reason_nl if reason_nl is None else reason_nl
    _require_non_empty_reason(resolved_reason)

    if transaction.side is TransactionSide.BUY:
        entry_type = LedgerEntryType.BUY
    elif transaction.side is TransactionSide.SELL:
        entry_type = LedgerEntryType.SELL
    else:
        raise InvalidAccountingInputError(f"Unsupported transaction side: {transaction.side}")

    return CashLedgerEntry(
        ledger_entry_id=ledger_entry_id,
        portfolio_id=transaction.portfolio_id,
        entry_type=entry_type,
        amount=calculate_cash_delta_for_transaction(transaction.side, transaction.net_amount),
        occurred_at=transaction.occurred_at if occurred_at is None else occurred_at,
        reason_nl=resolved_reason,
        related_instrument_id=transaction.instrument_id,
        related_transaction_id=transaction.transaction_id,
        related_order_id=transaction.related_order_id,
        related_suggestion_id=transaction.related_suggestion_id,
        source_run_id=source_run_id,
    )


def validate_cash_entry_sign(entry: CashLedgerEntry) -> None:
    amount = entry.amount.amount
    entry_type = entry.entry_type

    if entry_type is LedgerEntryType.DEPOSIT and amount <= Decimal("0"):
        raise InvalidAccountingInputError("Deposit cash entry amount must be positive.")
    if entry_type is LedgerEntryType.WITHDRAWAL and amount >= Decimal("0"):
        raise InvalidAccountingInputError("Withdrawal cash entry amount must be negative.")
    if entry_type is LedgerEntryType.BUY and amount >= Decimal("0"):
        raise InvalidAccountingInputError("Buy cash entry amount must be negative.")
    if entry_type is LedgerEntryType.SELL and amount <= Decimal("0"):
        raise InvalidAccountingInputError("Sell cash entry amount must be positive.")
    if (
        entry_type in {LedgerEntryType.FEE, LedgerEntryType.TAX_ESTIMATE}
        and amount >= Decimal("0")
    ):
        raise InvalidAccountingInputError(
            "Fee and tax_estimate cash entry amounts must be negative."
        )


def validate_transaction_cash_entry_pair(
    transaction: PaperTransaction,
    cash_entry: CashLedgerEntry,
) -> None:
    if cash_entry.related_transaction_id != transaction.transaction_id:
        raise InvalidAccountingInputError(
            "cash_entry.related_transaction_id must match transaction"
        )
    if cash_entry.related_instrument_id != transaction.instrument_id:
        raise InvalidAccountingInputError(
            "cash_entry.related_instrument_id must match transaction"
        )
    if cash_entry.amount.currency != transaction.net_amount.currency:
        raise CurrencyMismatchError("cash_entry amount currency must match transaction.net_amount")

    expected_amount = calculate_cash_delta_for_transaction(
        transaction.side, transaction.net_amount
    )
    if cash_entry.amount != expected_amount:
        raise InvalidAccountingInputError(
            "cash_entry.amount does not match transaction side/net_amount"
        )

    if transaction.side is TransactionSide.BUY and cash_entry.entry_type is not LedgerEntryType.BUY:
        raise InvalidAccountingInputError("Buy transactions require LedgerEntryType.BUY")
    if (
        transaction.side is TransactionSide.SELL
        and cash_entry.entry_type is not LedgerEntryType.SELL
    ):
        raise InvalidAccountingInputError("Sell transactions require LedgerEntryType.SELL")
