from datetime import datetime
from decimal import Decimal

import pytest
from portfolio_outlook_domain import (
    CashLedgerEntry,
    CostEstimate,
    CostType,
    LedgerEntryType,
    Money,
    Quantity,
    TransactionSide,
)

from portfolio_outlook_portfolio import (
    CurrencyMismatchError,
    InvalidAccountingInputError,
    build_paper_transaction,
    create_cash_entry_for_transaction,
    create_deposit_cash_entry,
    create_withdrawal_cash_entry,
    validate_cash_entry_sign,
    validate_transaction_cash_entry_pair,
)


def _cost(cost_id: str, amount: str, currency: str = "EUR") -> CostEstimate:
    return CostEstimate(
        cost_estimate_id=cost_id,
        cost_type=CostType.BROKER_FEE,
        amount=Money(amount=Decimal(amount), currency=currency),
    )


def _buy_transaction() -> object:
    return build_paper_transaction(
        transaction_id="tx_buy_1",
        portfolio_id="pf_1",
        instrument_id="inst_1",
        side=TransactionSide.BUY,
        quantity=Quantity(value=Decimal("2")),
        price=Money(amount=Decimal("10"), currency="EUR"),
        costs=[_cost("c1", "1.50")],
        occurred_at=datetime(2026, 1, 1, 10, 0, 0),
        reason_nl="Paperaankoop",
        related_order_id="ord_1",
        related_suggestion_id="sug_1",
    )


def _sell_transaction() -> object:
    return build_paper_transaction(
        transaction_id="tx_sell_1",
        portfolio_id="pf_1",
        instrument_id="inst_1",
        side=TransactionSide.SELL,
        quantity=Quantity(value=Decimal("2")),
        price=Money(amount=Decimal("10"), currency="EUR"),
        costs=[_cost("c2", "0.50")],
        occurred_at=datetime(2026, 1, 1, 11, 0, 0),
        reason_nl="Paperverkoop",
    )


def test_create_deposit_cash_entry_positive() -> None:
    entry = create_deposit_cash_entry(
        ledger_entry_id="le_1",
        portfolio_id="pf_1",
        amount=Money(amount=Decimal("100"), currency="EUR"),
        occurred_at=datetime(2026, 1, 1, 9, 0, 0),
        reason_nl="Startkapitaal",
    )
    assert entry.entry_type is LedgerEntryType.DEPOSIT
    assert entry.amount == Money(amount=Decimal("100"), currency="EUR")


@pytest.mark.parametrize("amount", ["0", "-1"])
def test_create_deposit_rejects_non_positive(amount: str) -> None:
    with pytest.raises(InvalidAccountingInputError):
        create_deposit_cash_entry(
            ledger_entry_id="le_2",
            portfolio_id="pf_1",
            amount=Money(amount=Decimal(amount), currency="EUR"),
            occurred_at=datetime(2026, 1, 1, 9, 0, 0),
            reason_nl="Storting",
        )


def test_create_deposit_rejects_empty_reason() -> None:
    with pytest.raises(InvalidAccountingInputError):
        create_deposit_cash_entry(
            ledger_entry_id="le_3",
            portfolio_id="pf_1",
            amount=Money(amount=Decimal("10"), currency="EUR"),
            occurred_at=datetime(2026, 1, 1, 9, 0, 0),
            reason_nl="   ",
        )


def test_create_withdrawal_negative_output_from_positive_input() -> None:
    entry = create_withdrawal_cash_entry(
        ledger_entry_id="le_4",
        portfolio_id="pf_1",
        amount=Money(amount=Decimal("25"), currency="EUR"),
        occurred_at=datetime(2026, 1, 1, 9, 30, 0),
        reason_nl="Opname",
    )
    assert entry.entry_type is LedgerEntryType.WITHDRAWAL
    assert entry.amount == Money(amount=Decimal("-25"), currency="EUR")


@pytest.mark.parametrize("amount", ["0", "-5"])
def test_create_withdrawal_rejects_non_positive_input(amount: str) -> None:
    with pytest.raises(InvalidAccountingInputError):
        create_withdrawal_cash_entry(
            ledger_entry_id="le_5",
            portfolio_id="pf_1",
            amount=Money(amount=Decimal(amount), currency="EUR"),
            occurred_at=datetime(2026, 1, 1, 9, 0, 0),
            reason_nl="Opname",
        )


def test_create_withdrawal_rejects_empty_reason() -> None:
    with pytest.raises(InvalidAccountingInputError):
        create_withdrawal_cash_entry(
            ledger_entry_id="le_6",
            portfolio_id="pf_1",
            amount=Money(amount=Decimal("10"), currency="EUR"),
            occurred_at=datetime(2026, 1, 1, 9, 0, 0),
            reason_nl="",
        )


def test_build_paper_transaction_buy_and_sell() -> None:
    buy = _buy_transaction()
    sell = _sell_transaction()
    assert buy.gross_amount == Money(amount=Decimal("20"), currency="EUR")
    assert buy.net_amount == Money(amount=Decimal("21.50"), currency="EUR")
    assert buy.mode.value == "paper"
    assert buy.status.value == "filled"
    assert sell.gross_amount == Money(amount=Decimal("20"), currency="EUR")
    assert sell.net_amount == Money(amount=Decimal("19.50"), currency="EUR")


def test_build_paper_transaction_rejects_bad_inputs() -> None:
    with pytest.raises(InvalidAccountingInputError):
        build_paper_transaction(
            transaction_id="tx_bad_1",
            portfolio_id="pf_1",
            instrument_id="inst_1",
            side=TransactionSide.BUY,
            quantity=Quantity(value=Decimal("0")),
            price=Money(amount=Decimal("10"), currency="EUR"),
            costs=[],
            occurred_at=datetime(2026, 1, 1, 10, 0, 0),
            reason_nl="test",
        )
    with pytest.raises(CurrencyMismatchError):
        build_paper_transaction(
            transaction_id="tx_bad_2",
            portfolio_id="pf_1",
            instrument_id="inst_1",
            side=TransactionSide.BUY,
            quantity=Quantity(value=Decimal("1")),
            price=Money(amount=Decimal("10"), currency="EUR"),
            costs=[_cost("x", "1", "USD")],
            occurred_at=datetime(2026, 1, 1, 10, 0, 0),
            reason_nl="test",
        )
    with pytest.raises(InvalidAccountingInputError):
        build_paper_transaction(
            transaction_id="tx_bad_3",
            portfolio_id="pf_1",
            instrument_id="inst_1",
            side=TransactionSide.BUY,
            quantity=Quantity(value=Decimal("1")),
            price=Money(amount=Decimal("10"), currency="EUR"),
            costs=[],
            occurred_at=datetime(2026, 1, 1, 10, 0, 0),
            reason_nl="   ",
        )


def test_create_cash_entry_for_transaction_links_and_signs() -> None:
    buy = _buy_transaction()
    buy_entry = create_cash_entry_for_transaction(ledger_entry_id="le_b", transaction=buy)
    assert buy_entry.amount == Money(amount=Decimal("-21.50"), currency="EUR")
    assert buy_entry.related_transaction_id == buy.transaction_id
    assert buy_entry.related_instrument_id == buy.instrument_id
    assert buy_entry.related_order_id == "ord_1"
    assert buy_entry.reason_nl == buy.reason_nl

    sell = _sell_transaction()
    sell_entry = create_cash_entry_for_transaction(
        ledger_entry_id="le_s", transaction=sell, reason_nl="Aangepaste reden"
    )
    assert sell_entry.amount == Money(amount=Decimal("19.50"), currency="EUR")
    assert sell_entry.reason_nl == "Aangepaste reden"


def test_validate_cash_entry_sign_rules() -> None:
    def entry(entry_type: LedgerEntryType, amount: str) -> CashLedgerEntry:
        return CashLedgerEntry(
            ledger_entry_id=f"le_{entry_type.value}_{amount.replace('-', 'n')}",
            portfolio_id="pf_1",
            entry_type=entry_type,
            amount=Money(amount=Decimal(amount), currency="EUR"),
            occurred_at=datetime(2026, 1, 1, 12, 0, 0),
            reason_nl="test",
        )

    validate_cash_entry_sign(entry(LedgerEntryType.DEPOSIT, "1"))
    with pytest.raises(InvalidAccountingInputError):
        validate_cash_entry_sign(entry(LedgerEntryType.DEPOSIT, "-1"))

    validate_cash_entry_sign(entry(LedgerEntryType.WITHDRAWAL, "-1"))
    with pytest.raises(InvalidAccountingInputError):
        validate_cash_entry_sign(entry(LedgerEntryType.WITHDRAWAL, "1"))

    validate_cash_entry_sign(entry(LedgerEntryType.BUY, "-1"))
    with pytest.raises(InvalidAccountingInputError):
        validate_cash_entry_sign(entry(LedgerEntryType.BUY, "1"))

    validate_cash_entry_sign(entry(LedgerEntryType.SELL, "1"))
    with pytest.raises(InvalidAccountingInputError):
        validate_cash_entry_sign(entry(LedgerEntryType.SELL, "-1"))

    validate_cash_entry_sign(entry(LedgerEntryType.FEE, "-1"))
    with pytest.raises(InvalidAccountingInputError):
        validate_cash_entry_sign(entry(LedgerEntryType.FEE, "1"))

    validate_cash_entry_sign(entry(LedgerEntryType.CASH_ADJUSTMENT, "1"))
    validate_cash_entry_sign(entry(LedgerEntryType.CASH_ADJUSTMENT, "-1"))


def test_validate_transaction_cash_entry_pair_rules() -> None:
    buy = _buy_transaction()
    buy_entry = create_cash_entry_for_transaction(ledger_entry_id="le_ok_buy", transaction=buy)
    validate_transaction_cash_entry_pair(buy, buy_entry)

    sell = _sell_transaction()
    sell_entry = create_cash_entry_for_transaction(ledger_entry_id="le_ok_sell", transaction=sell)
    validate_transaction_cash_entry_pair(sell, sell_entry)

    with pytest.raises(InvalidAccountingInputError):
        validate_transaction_cash_entry_pair(
            buy,
            buy_entry.model_copy(update={"related_transaction_id": "tx_wrong"}),
        )
    with pytest.raises(InvalidAccountingInputError):
        validate_transaction_cash_entry_pair(
            buy,
            buy_entry.model_copy(update={"related_instrument_id": "inst_wrong"}),
        )
    with pytest.raises(InvalidAccountingInputError):
        validate_transaction_cash_entry_pair(
            buy,
            buy_entry.model_copy(update={"amount": Money(amount=Decimal("-20"), currency="EUR")}),
        )
    with pytest.raises(InvalidAccountingInputError):
        validate_transaction_cash_entry_pair(
            buy,
            buy_entry.model_copy(update={"entry_type": LedgerEntryType.SELL}),
        )
    with pytest.raises(CurrencyMismatchError):
        validate_transaction_cash_entry_pair(
            buy,
            buy_entry.model_copy(
                update={"amount": Money(amount=Decimal("-21.50"), currency="USD")}
            ),
        )


def test_model_dump_for_generated_records() -> None:
    tx = _buy_transaction()
    entry = create_cash_entry_for_transaction(ledger_entry_id="le_dump", transaction=tx)
    assert isinstance(tx.model_dump(), dict)
    assert isinstance(entry.model_dump(), dict)
