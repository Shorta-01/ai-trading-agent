from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from portfolio_outlook_domain import (
    CashLedgerEntry,
    CostEstimate,
    CostType,
    CurrencyCode,
    LedgerEntryType,
    Money,
    Percentage,
    PortfolioId,
)

from .errors import InvalidAccountingInputError
from .money import ensure_same_currency


@dataclass(frozen=True)
class PortfolioCashFlowSummary:
    starting_capital: Money
    deposits: Money
    withdrawals: Money
    net_external_cash_flow: Money


@dataclass(frozen=True)
class PortfolioCostAndTaxSummary:
    fees: Money
    estimated_taxes: Money
    total_costs_and_estimated_taxes: Money


@dataclass(frozen=True)
class PortfolioPerformanceSummary:
    portfolio_id: PortfolioId
    starting_capital: Money
    deposits: Money
    withdrawals: Money
    current_cash: Money
    current_positions_value: Money
    current_total_value: Money
    gross_result_since_start: Money
    fees: Money
    estimated_taxes: Money
    net_result_since_start: Money
    return_since_start: Percentage | None


def calculate_cash_flow_summary(
    *,
    starting_capital: Money,
    cash_entries: Sequence[CashLedgerEntry],
) -> PortfolioCashFlowSummary:
    if starting_capital.amount <= Decimal("0"):
        raise InvalidAccountingInputError("starting_capital must be greater than zero.")

    deposits_total = Decimal("0")
    withdrawals_total = Decimal("0")

    for entry in cash_entries:
        if entry.entry_type not in {LedgerEntryType.DEPOSIT, LedgerEntryType.WITHDRAWAL}:
            continue
        ensure_same_currency(starting_capital, entry.amount)
        if entry.entry_type is LedgerEntryType.DEPOSIT:
            deposits_total += entry.amount.amount
        else:
            withdrawals_total += abs(entry.amount.amount)

    deposits = Money(amount=deposits_total, currency=starting_capital.currency)
    withdrawals = Money(amount=withdrawals_total, currency=starting_capital.currency)
    return PortfolioCashFlowSummary(
        starting_capital=starting_capital,
        deposits=deposits,
        withdrawals=withdrawals,
        net_external_cash_flow=Money(
            amount=deposits.amount - withdrawals.amount,
            currency=starting_capital.currency,
        ),
    )


def calculate_cost_and_tax_summary(
    *,
    currency: CurrencyCode,
    costs: Sequence[CostEstimate] = (),
    cash_entries: Sequence[CashLedgerEntry] = (),
) -> PortfolioCostAndTaxSummary:
    fees_total = Decimal("0")
    taxes_total = Decimal("0")

    tax_cost_types = {CostType.TOB_ESTIMATE, CostType.WITHHOLDING_TAX_ESTIMATE}

    for cost in costs:
        ensure_same_currency(Money(amount=Decimal("0"), currency=currency), cost.amount)
        if cost.cost_type in tax_cost_types:
            taxes_total += cost.amount.amount
        else:
            fees_total += cost.amount.amount

    for entry in cash_entries:
        if entry.entry_type not in {LedgerEntryType.FEE, LedgerEntryType.TAX_ESTIMATE}:
            continue
        ensure_same_currency(Money(amount=Decimal("0"), currency=currency), entry.amount)
        if entry.entry_type is LedgerEntryType.FEE:
            fees_total += abs(entry.amount.amount)
        else:
            taxes_total += abs(entry.amount.amount)

    fees = Money(amount=fees_total, currency=currency)
    estimated_taxes = Money(amount=taxes_total, currency=currency)
    return PortfolioCostAndTaxSummary(
        fees=fees,
        estimated_taxes=estimated_taxes,
        total_costs_and_estimated_taxes=Money(
            amount=fees.amount + estimated_taxes.amount,
            currency=currency,
        ),
    )


def calculate_current_total_value(*, current_cash: Money, current_positions_value: Money) -> Money:
    ensure_same_currency(current_cash, current_positions_value)
    return Money(
        amount=current_cash.amount + current_positions_value.amount,
        currency=current_cash.currency,
    )


def calculate_result_since_start(
    *,
    current_total_value: Money,
    starting_capital: Money,
    deposits: Money,
    withdrawals: Money,
) -> Money:
    ensure_same_currency(current_total_value, starting_capital, deposits, withdrawals)
    return Money(
        amount=current_total_value.amount
        - starting_capital.amount
        - deposits.amount
        + withdrawals.amount,
        currency=current_total_value.currency,
    )


def calculate_net_result_since_start(
    *,
    gross_result_since_start: Money,
    fees: Money,
    estimated_taxes: Money,
) -> Money:
    ensure_same_currency(gross_result_since_start, fees, estimated_taxes)
    if fees.amount < Decimal("0") or estimated_taxes.amount < Decimal("0"):
        raise InvalidAccountingInputError("fees and estimated_taxes must be zero or positive.")
    return Money(
        amount=gross_result_since_start.amount - fees.amount - estimated_taxes.amount,
        currency=gross_result_since_start.currency,
    )


def calculate_return_since_start(
    *,
    net_result_since_start: Money,
    starting_capital: Money,
    deposits: Money,
    withdrawals: Money,
) -> Percentage | None:
    ensure_same_currency(net_result_since_start, starting_capital, deposits, withdrawals)
    adjusted_base = starting_capital.amount + deposits.amount - withdrawals.amount
    if adjusted_base <= Decimal("0"):
        return None
    return Percentage(value=(net_result_since_start.amount / adjusted_base) * Decimal("100"))


def build_portfolio_performance_summary(
    *,
    portfolio_id: PortfolioId,
    starting_capital: Money,
    current_cash: Money,
    current_positions_value: Money,
    cash_entries: Sequence[CashLedgerEntry],
    costs: Sequence[CostEstimate] = (),
) -> PortfolioPerformanceSummary:
    ensure_same_currency(starting_capital, current_cash, current_positions_value)
    cash_flow = calculate_cash_flow_summary(
        starting_capital=starting_capital,
        cash_entries=cash_entries,
    )
    cost_tax = calculate_cost_and_tax_summary(
        currency=starting_capital.currency,
        costs=costs,
        cash_entries=cash_entries,
    )
    current_total_value = calculate_current_total_value(
        current_cash=current_cash,
        current_positions_value=current_positions_value,
    )
    gross_result = calculate_result_since_start(
        current_total_value=current_total_value,
        starting_capital=starting_capital,
        deposits=cash_flow.deposits,
        withdrawals=cash_flow.withdrawals,
    )
    net_result = calculate_net_result_since_start(
        gross_result_since_start=gross_result,
        fees=cost_tax.fees,
        estimated_taxes=cost_tax.estimated_taxes,
    )
    total_return = calculate_return_since_start(
        net_result_since_start=net_result,
        starting_capital=starting_capital,
        deposits=cash_flow.deposits,
        withdrawals=cash_flow.withdrawals,
    )
    return PortfolioPerformanceSummary(
        portfolio_id=portfolio_id,
        starting_capital=starting_capital,
        deposits=cash_flow.deposits,
        withdrawals=cash_flow.withdrawals,
        current_cash=current_cash,
        current_positions_value=current_positions_value,
        current_total_value=current_total_value,
        gross_result_since_start=gross_result,
        fees=cost_tax.fees,
        estimated_taxes=cost_tax.estimated_taxes,
        net_result_since_start=net_result,
        return_since_start=total_return,
    )
