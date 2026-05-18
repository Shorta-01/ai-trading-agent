import calendar
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from portfolio_outlook_domain import (
    CurrencyCode,
    Money,
    TermDepositInput,
    TermDepositInterestType,
    TermDepositProjection,
    TermDepositStatus,
    TermDepositTerm,
)

from .errors import InvalidAccountingInputError
from .money import ensure_same_currency


def term_months(term: TermDepositTerm) -> int:
    mapping = {
        TermDepositTerm.ONE_MONTH: 1,
        TermDepositTerm.THREE_MONTHS: 3,
        TermDepositTerm.SIX_MONTHS: 6,
        TermDepositTerm.TWELVE_MONTHS: 12,
    }
    return mapping[term]


def calculate_maturity_date(start_date: date, term: TermDepositTerm) -> date:
    months_to_add = term_months(term)
    month_index = (start_date.month - 1) + months_to_add
    year = start_date.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(start_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def calculate_gross_interest_for_term_deposit(term_deposit: TermDepositInput) -> Money:
    if term_deposit.interest_type is TermDepositInterestType.FIXED_AMOUNT:
        if term_deposit.gross_interest_amount is None:
            raise InvalidAccountingInputError("gross_interest_amount is required for fixed_amount.")
        return term_deposit.gross_interest_amount

    if term_deposit.gross_interest_rate is None:
        raise InvalidAccountingInputError("gross_interest_rate is required for fixed_rate.")
    if term_deposit.gross_interest_rate.value < Decimal("0"):
        raise InvalidAccountingInputError("gross_interest_rate must be zero or positive.")

    months = Decimal(str(term_months(term_deposit.term)))
    gross_amount = (
        term_deposit.principal.amount
        * term_deposit.gross_interest_rate.value
        / Decimal("100")
        * months
        / Decimal("12")
    )
    return Money(amount=gross_amount, currency=term_deposit.principal.currency)


def calculate_net_interest_for_term_deposit(
    *, gross_interest: Money, costs: Money, estimated_taxes: Money
) -> Money:
    ensure_same_currency(gross_interest, costs, estimated_taxes)
    if costs.amount < Decimal("0") or estimated_taxes.amount < Decimal("0"):
        raise InvalidAccountingInputError("costs and estimated_taxes must be zero or positive.")
    return Money(
        amount=gross_interest.amount - costs.amount - estimated_taxes.amount,
        currency=gross_interest.currency,
    )


def calculate_expected_maturity_value(*, principal: Money, net_interest: Money) -> Money:
    ensure_same_currency(principal, net_interest)
    return Money(amount=principal.amount + net_interest.amount, currency=principal.currency)


def calculate_days_until_maturity(*, as_of: date, maturity_date: date) -> int:
    return max((maturity_date - as_of).days, 0)


def derive_term_deposit_status(
    *, start_date: date, maturity_date: date, as_of: date, cancelled: bool = False
) -> TermDepositStatus:
    if cancelled:
        return TermDepositStatus.CANCELLED
    if as_of < start_date:
        return TermDepositStatus.PLANNED
    if as_of < maturity_date:
        return TermDepositStatus.ACTIVE
    return TermDepositStatus.MATURED


def build_term_deposit_projection(
    *, term_deposit: TermDepositInput, as_of: date, cancelled: bool = False
) -> TermDepositProjection:
    maturity_date = calculate_maturity_date(term_deposit.start_date, term_deposit.term)
    gross_interest = calculate_gross_interest_for_term_deposit(term_deposit)
    net_interest = calculate_net_interest_for_term_deposit(
        gross_interest=gross_interest,
        costs=term_deposit.costs,
        estimated_taxes=term_deposit.estimated_taxes,
    )
    expected_maturity_value = calculate_expected_maturity_value(
        principal=term_deposit.principal,
        net_interest=net_interest,
    )
    status = (
        TermDepositStatus.CANCELLED
        if term_deposit.status is TermDepositStatus.CANCELLED
        else derive_term_deposit_status(
            start_date=term_deposit.start_date,
            maturity_date=maturity_date,
            as_of=as_of,
            cancelled=cancelled,
        )
    )

    return TermDepositProjection(
        term_deposit_id=term_deposit.term_deposit_id,
        portfolio_id=term_deposit.portfolio_id,
        bank_name=term_deposit.bank_name,
        name=term_deposit.name,
        principal=term_deposit.principal,
        start_date=term_deposit.start_date,
        maturity_date=maturity_date,
        term=term_deposit.term,
        gross_interest=gross_interest,
        costs=term_deposit.costs,
        estimated_taxes=term_deposit.estimated_taxes,
        net_interest=net_interest,
        expected_maturity_value=expected_maturity_value,
        days_until_maturity=calculate_days_until_maturity(as_of=as_of, maturity_date=maturity_date),
        status=status,
    )


def calculate_total_term_deposit_value(
    projections: Sequence[TermDepositProjection], currency: CurrencyCode
) -> Money:
    total = Decimal("0")
    for projection in projections:
        ensure_same_currency(
            Money(amount=Decimal("0"), currency=currency), projection.expected_maturity_value
        )
        total += projection.expected_maturity_value.amount
    return Money(amount=total, currency=currency)


def calculate_total_net_term_deposit_interest(
    projections: Sequence[TermDepositProjection], currency: CurrencyCode
) -> Money:
    total = Decimal("0")
    for projection in projections:
        ensure_same_currency(Money(amount=Decimal("0"), currency=currency), projection.net_interest)
        total += projection.net_interest.amount
    return Money(amount=total, currency=currency)
