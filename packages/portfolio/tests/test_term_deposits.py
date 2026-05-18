from datetime import date
from decimal import Decimal

import pytest
from portfolio_outlook_domain import (
    Money,
    Percentage,
    TermDepositInput,
    TermDepositInterestType,
    TermDepositStatus,
    TermDepositTerm,
)

from portfolio_outlook_portfolio import (
    build_term_deposit_projection,
    calculate_days_until_maturity,
    calculate_expected_maturity_value,
    calculate_gross_interest_for_term_deposit,
    calculate_maturity_date,
    calculate_net_interest_for_term_deposit,
    calculate_total_net_term_deposit_interest,
    calculate_total_term_deposit_value,
    derive_term_deposit_status,
    term_months,
)
from portfolio_outlook_portfolio.errors import CurrencyMismatchError


def build_term_deposit(**overrides: object) -> TermDepositInput:
    data = {
        "term_deposit_id": "td1",
        "portfolio_id": "pf1",
        "bank_name": "Bank",
        "name": "Naam",
        "principal": Money(amount="1200", currency="EUR"),
        "start_date": date(2026, 1, 15),
        "term": TermDepositTerm.ONE_MONTH,
        "interest_type": TermDepositInterestType.FIXED_RATE,
        "gross_interest_rate": Percentage(value="12"),
        "gross_interest_amount": None,
        "costs": Money(amount="2", currency="EUR"),
        "estimated_taxes": Money(amount="1", currency="EUR"),
        "status": TermDepositStatus.ACTIVE,
    }
    data.update(overrides)
    return TermDepositInput(**data)


def test_term_months_and_maturity() -> None:
    assert term_months(TermDepositTerm.ONE_MONTH) == 1
    assert term_months(TermDepositTerm.THREE_MONTHS) == 3
    assert term_months(TermDepositTerm.SIX_MONTHS) == 6
    assert term_months(TermDepositTerm.TWELVE_MONTHS) == 12
    assert calculate_maturity_date(date(2026, 1, 15), TermDepositTerm.ONE_MONTH) == date(
        2026, 2, 15
    )
    assert calculate_maturity_date(date(2026, 1, 31), TermDepositTerm.ONE_MONTH) == date(
        2026, 2, 28
    )
    assert calculate_maturity_date(date(2028, 1, 31), TermDepositTerm.ONE_MONTH) == date(
        2028, 2, 29
    )
    assert calculate_maturity_date(date(2026, 8, 31), TermDepositTerm.SIX_MONTHS) == date(
        2027, 2, 28
    )


def test_gross_interest() -> None:
    fixed_amount = build_term_deposit(
        interest_type=TermDepositInterestType.FIXED_AMOUNT,
        gross_interest_rate=None,
        gross_interest_amount=Money(amount="33", currency="EUR"),
    )
    assert calculate_gross_interest_for_term_deposit(fixed_amount).amount == Decimal("33")

    assert calculate_gross_interest_for_term_deposit(
        build_term_deposit(term=TermDepositTerm.ONE_MONTH)
    ).amount == Decimal("12")
    assert calculate_gross_interest_for_term_deposit(
        build_term_deposit(term=TermDepositTerm.THREE_MONTHS)
    ).amount == Decimal("36")
    assert calculate_gross_interest_for_term_deposit(
        build_term_deposit(term=TermDepositTerm.SIX_MONTHS)
    ).amount == Decimal("72")
    assert calculate_gross_interest_for_term_deposit(
        build_term_deposit(term=TermDepositTerm.TWELVE_MONTHS)
    ).amount == Decimal("144")


def test_net_interest_expected_value_days_status_and_projection_totals() -> None:
    net = calculate_net_interest_for_term_deposit(
        gross_interest=Money(amount="20", currency="EUR"),
        costs=Money(amount="3", currency="EUR"),
        estimated_taxes=Money(amount="4", currency="EUR"),
    )
    assert net.amount == Decimal("13")
    assert calculate_net_interest_for_term_deposit(
        gross_interest=Money(amount="1", currency="EUR"),
        costs=Money(amount="3", currency="EUR"),
        estimated_taxes=Money(amount="0", currency="EUR"),
    ).amount == Decimal("-2")
    with pytest.raises(CurrencyMismatchError):
        calculate_net_interest_for_term_deposit(
            gross_interest=Money(amount="1", currency="EUR"),
            costs=Money(amount="1", currency="USD"),
            estimated_taxes=Money(amount="0", currency="EUR"),
        )

    assert calculate_expected_maturity_value(
        principal=Money(amount="100", currency="EUR"),
        net_interest=Money(amount="-2", currency="EUR"),
    ).amount == Decimal("98")
    with pytest.raises(CurrencyMismatchError):
        calculate_expected_maturity_value(
            principal=Money(amount="100", currency="EUR"),
            net_interest=Money(amount="1", currency="USD"),
        )

    assert (
        calculate_days_until_maturity(as_of=date(2026, 1, 1), maturity_date=date(2026, 1, 10)) == 9
    )
    assert (
        calculate_days_until_maturity(as_of=date(2026, 1, 20), maturity_date=date(2026, 1, 10)) == 0
    )
    assert (
        derive_term_deposit_status(
            start_date=date(2026, 1, 5), maturity_date=date(2026, 2, 5), as_of=date(2026, 1, 1)
        )
        is TermDepositStatus.PLANNED
    )
    assert (
        derive_term_deposit_status(
            start_date=date(2026, 1, 5), maturity_date=date(2026, 2, 5), as_of=date(2026, 1, 6)
        )
        is TermDepositStatus.ACTIVE
    )
    assert (
        derive_term_deposit_status(
            start_date=date(2026, 1, 5), maturity_date=date(2026, 2, 5), as_of=date(2026, 2, 5)
        )
        is TermDepositStatus.MATURED
    )
    assert (
        derive_term_deposit_status(
            start_date=date(2026, 1, 5),
            maturity_date=date(2026, 2, 5),
            as_of=date(2026, 1, 6),
            cancelled=True,
        )
        is TermDepositStatus.CANCELLED
    )

    projection = build_term_deposit_projection(
        term_deposit=build_term_deposit(term=TermDepositTerm.THREE_MONTHS), as_of=date(2026, 2, 1)
    )
    assert projection.expected_maturity_value.amount == Decimal("1233")
    assert projection.net_interest.amount == Decimal("33")
    assert projection.days_until_maturity > 0
    assert projection.model_dump()["term"] == "three_months"

    cancelled_projection = build_term_deposit_projection(
        term_deposit=build_term_deposit(status=TermDepositStatus.CANCELLED),
        as_of=date(2026, 1, 20),
    )
    assert cancelled_projection.status is TermDepositStatus.CANCELLED

    assert calculate_total_term_deposit_value([], "EUR").amount == Decimal("0")
    assert calculate_total_net_term_deposit_interest([], "EUR").amount == Decimal("0")
    projection2 = build_term_deposit_projection(
        term_deposit=build_term_deposit(
            term_deposit_id="td2", gross_interest_rate=Percentage(value="0")
        ),
        as_of=date(2026, 1, 20),
    )
    assert (
        calculate_total_term_deposit_value([projection, projection2], "EUR").amount
        == projection.expected_maturity_value.amount + projection2.expected_maturity_value.amount
    )
    assert (
        calculate_total_net_term_deposit_interest([projection, projection2], "EUR").amount
        == projection.net_interest.amount + projection2.net_interest.amount
    )
    with pytest.raises(CurrencyMismatchError):
        calculate_total_term_deposit_value([projection], "USD")
    with pytest.raises(CurrencyMismatchError):
        calculate_total_net_term_deposit_interest([projection], "USD")
