from dataclasses import asdict
from datetime import datetime
from decimal import Decimal

import pytest
from portfolio_outlook_domain import (
    CashLedgerEntry,
    CostEstimate,
    CostType,
    LedgerEntryType,
    Money,
)

from portfolio_outlook_portfolio import (
    CurrencyMismatchError,
    InvalidAccountingInputError,
    build_portfolio_performance_summary,
    calculate_cash_flow_summary,
    calculate_cost_and_tax_summary,
    calculate_current_total_value,
    calculate_net_result_since_start,
    calculate_result_since_start,
    calculate_return_since_start,
)


def _cash_entry(
    entry_id: str,
    entry_type: LedgerEntryType,
    amount: str,
    currency: str = "EUR",
) -> CashLedgerEntry:
    return CashLedgerEntry(
        ledger_entry_id=entry_id,
        portfolio_id="pf_1",
        entry_type=entry_type,
        amount=Money(amount=Decimal(amount), currency=currency),
        occurred_at=datetime(2026, 1, 1, 9, 0, 0),
        reason_nl="Test",
    )


def _cost(cost_id: str, cost_type: CostType, amount: str, currency: str = "EUR") -> CostEstimate:
    return CostEstimate(
        cost_estimate_id=cost_id,
        cost_type=cost_type,
        amount=Money(amount=Decimal(amount), currency=currency),
    )


def test_calculate_cash_flow_summary_cases() -> None:
    start = Money(amount=Decimal("10000"), currency="EUR")
    summary = calculate_cash_flow_summary(starting_capital=start, cash_entries=[])
    assert summary.deposits == Money(amount=Decimal("0"), currency="EUR")
    assert summary.withdrawals == Money(amount=Decimal("0"), currency="EUR")

    summary2 = calculate_cash_flow_summary(
        starting_capital=start,
        cash_entries=[
            _cash_entry("e1", LedgerEntryType.DEPOSIT, "500"),
            _cash_entry("e2", LedgerEntryType.DEPOSIT, "1500"),
            _cash_entry("e3", LedgerEntryType.WITHDRAWAL, "-200"),
            _cash_entry("e4", LedgerEntryType.BUY, "-100"),
        ],
    )
    assert summary2.deposits.amount == Decimal("2000")
    assert summary2.withdrawals.amount == Decimal("200")
    assert summary2.net_external_cash_flow.amount == Decimal("1800")

    with pytest.raises(CurrencyMismatchError):
        calculate_cash_flow_summary(
            starting_capital=start,
            cash_entries=[_cash_entry("e5", LedgerEntryType.DEPOSIT, "100", currency="USD")],
        )

    with pytest.raises(InvalidAccountingInputError):
        calculate_cash_flow_summary(
            starting_capital=Money(amount=Decimal("0"), currency="EUR"),
            cash_entries=[],
        )


def test_calculate_cost_and_tax_summary_cases() -> None:
    empty = calculate_cost_and_tax_summary(currency="EUR")
    assert empty.fees.amount == Decimal("0")
    assert empty.estimated_taxes.amount == Decimal("0")

    summary = calculate_cost_and_tax_summary(
        currency="EUR",
        costs=[
            _cost("c1", CostType.BROKER_FEE, "10"),
            _cost("c2", CostType.TOB_ESTIMATE, "5"),
            _cost("c3", CostType.WITHHOLDING_TAX_ESTIMATE, "3"),
        ],
        cash_entries=[
            _cash_entry("e1", LedgerEntryType.FEE, "-2"),
            _cash_entry("e2", LedgerEntryType.TAX_ESTIMATE, "-1"),
        ],
    )
    assert summary.fees.amount == Decimal("12")
    assert summary.estimated_taxes.amount == Decimal("9")
    assert summary.total_costs_and_estimated_taxes.amount == Decimal("21")

    with pytest.raises(CurrencyMismatchError):
        calculate_cost_and_tax_summary(
            currency="EUR",
            costs=[_cost("c4", CostType.BROKER_FEE, "1", currency="USD")],
        )

    with pytest.raises(ValueError):
        _cost("bad", CostType.BROKER_FEE, "-1")


def test_calculate_current_total_value_and_result_cases() -> None:
    total = calculate_current_total_value(
        current_cash=Money(amount=Decimal("1000"), currency="EUR"),
        current_positions_value=Money(amount=Decimal("2500"), currency="EUR"),
    )
    assert total == Money(amount=Decimal("3500"), currency="EUR")

    with pytest.raises(CurrencyMismatchError):
        calculate_current_total_value(
            current_cash=Money(amount=Decimal("1000"), currency="EUR"),
            current_positions_value=Money(amount=Decimal("2500"), currency="USD"),
        )

    assert calculate_result_since_start(
        current_total_value=Money(amount=Decimal("11000"), currency="EUR"),
        starting_capital=Money(amount=Decimal("10000"), currency="EUR"),
        deposits=Money(amount=Decimal("0"), currency="EUR"),
        withdrawals=Money(amount=Decimal("0"), currency="EUR"),
    ).amount == Decimal("1000")

    assert calculate_result_since_start(
        current_total_value=Money(amount=Decimal("12500"), currency="EUR"),
        starting_capital=Money(amount=Decimal("10000"), currency="EUR"),
        deposits=Money(amount=Decimal("2000"), currency="EUR"),
        withdrawals=Money(amount=Decimal("0"), currency="EUR"),
    ).amount == Decimal("500")

    assert calculate_result_since_start(
        current_total_value=Money(amount=Decimal("9500"), currency="EUR"),
        starting_capital=Money(amount=Decimal("10000"), currency="EUR"),
        deposits=Money(amount=Decimal("0"), currency="EUR"),
        withdrawals=Money(amount=Decimal("1000"), currency="EUR"),
    ).amount == Decimal("500")

    assert calculate_result_since_start(
        current_total_value=Money(amount=Decimal("9000"), currency="EUR"),
        starting_capital=Money(amount=Decimal("10000"), currency="EUR"),
        deposits=Money(amount=Decimal("0"), currency="EUR"),
        withdrawals=Money(amount=Decimal("0"), currency="EUR"),
    ).amount == Decimal("-1000")


def test_calculate_net_result_and_return_cases() -> None:
    net = calculate_net_result_since_start(
        gross_result_since_start=Money(amount=Decimal("1000"), currency="EUR"),
        fees=Money(amount=Decimal("50"), currency="EUR"),
        estimated_taxes=Money(amount=Decimal("10"), currency="EUR"),
    )
    assert net.amount == Decimal("940")

    with pytest.raises(InvalidAccountingInputError):
        calculate_net_result_since_start(
            gross_result_since_start=Money(amount=Decimal("1000"), currency="EUR"),
            fees=Money(amount=Decimal("-1"), currency="EUR"),
            estimated_taxes=Money(amount=Decimal("0"), currency="EUR"),
        )

    ret = calculate_return_since_start(
        net_result_since_start=Money(amount=Decimal("1000"), currency="EUR"),
        starting_capital=Money(amount=Decimal("10000"), currency="EUR"),
        deposits=Money(amount=Decimal("0"), currency="EUR"),
        withdrawals=Money(amount=Decimal("0"), currency="EUR"),
    )
    assert ret is not None
    assert ret.value == Decimal("10")

    ret_deposit = calculate_return_since_start(
        net_result_since_start=Money(amount=Decimal("1000"), currency="EUR"),
        starting_capital=Money(amount=Decimal("10000"), currency="EUR"),
        deposits=Money(amount=Decimal("5000"), currency="EUR"),
        withdrawals=Money(amount=Decimal("0"), currency="EUR"),
    )
    assert ret_deposit is not None
    assert ret_deposit.value == Decimal("6.666666666666666666666666667")

    ret_withdrawal = calculate_return_since_start(
        net_result_since_start=Money(amount=Decimal("1000"), currency="EUR"),
        starting_capital=Money(amount=Decimal("10000"), currency="EUR"),
        deposits=Money(amount=Decimal("0"), currency="EUR"),
        withdrawals=Money(amount=Decimal("2000"), currency="EUR"),
    )
    assert ret_withdrawal is not None
    assert ret_withdrawal.value == Decimal("12.500")

    assert (
        calculate_return_since_start(
            net_result_since_start=Money(amount=Decimal("100"), currency="EUR"),
            starting_capital=Money(amount=Decimal("1000"), currency="EUR"),
            deposits=Money(amount=Decimal("0"), currency="EUR"),
            withdrawals=Money(amount=Decimal("1000"), currency="EUR"),
        )
        is None
    )

    negative_ret = calculate_return_since_start(
        net_result_since_start=Money(amount=Decimal("-500"), currency="EUR"),
        starting_capital=Money(amount=Decimal("10000"), currency="EUR"),
        deposits=Money(amount=Decimal("0"), currency="EUR"),
        withdrawals=Money(amount=Decimal("0"), currency="EUR"),
    )
    assert negative_ret is not None
    assert negative_ret.value == Decimal("-5")


def test_build_portfolio_performance_summary_cases() -> None:
    summary = build_portfolio_performance_summary(
        portfolio_id="pf_1",
        starting_capital=Money(amount=Decimal("10000"), currency="EUR"),
        current_cash=Money(amount=Decimal("2000"), currency="EUR"),
        current_positions_value=Money(amount=Decimal("10500"), currency="EUR"),
        cash_entries=[
            _cash_entry("e1", LedgerEntryType.DEPOSIT, "2000"),
            _cash_entry("e2", LedgerEntryType.WITHDRAWAL, "-500"),
            _cash_entry("e3", LedgerEntryType.FEE, "-25"),
            _cash_entry("e4", LedgerEntryType.TAX_ESTIMATE, "-10"),
        ],
        costs=[
            _cost("c1", CostType.BROKER_FEE, "5"),
            _cost("c2", CostType.TOB_ESTIMATE, "2"),
        ],
    )
    assert summary.current_total_value.amount == Decimal("12500")
    assert summary.gross_result_since_start.amount == Decimal("1000")
    assert summary.net_result_since_start.amount == Decimal("958")
    assert summary.return_since_start is not None
    assert summary.fees.amount == Decimal("30")
    assert summary.estimated_taxes.amount == Decimal("12")
    assert summary.deposits.amount == Decimal("2000")
    assert summary.withdrawals.amount == Decimal("500")
    assert summary.portfolio_id == "pf_1"
    assert isinstance(asdict(summary), dict)
