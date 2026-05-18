from datetime import date

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import (
    Money,
    Percentage,
    TermDepositInput,
    TermDepositInterestType,
    TermDepositProjection,
    TermDepositStatus,
    TermDepositTerm,
)


def base_input() -> dict[str, object]:
    return {
        "term_deposit_id": "td_1",
        "portfolio_id": "pf_1",
        "bank_name": "Bank A",
        "name": "Naam",
        "principal": Money(amount="1000", currency="EUR"),
        "start_date": date(2026, 1, 1),
        "term": TermDepositTerm.SIX_MONTHS,
        "interest_type": TermDepositInterestType.FIXED_RATE,
        "gross_interest_rate": Percentage(value="3"),
        "gross_interest_amount": None,
        "costs": Money(amount="5", currency="EUR"),
        "estimated_taxes": Money(amount="2", currency="EUR"),
        "status": TermDepositStatus.ACTIVE,
    }


def test_input_validation_and_projection() -> None:
    assert TermDepositInput(**base_input())
    assert TermDepositInput(
        **(
            base_input()
            | {
                "interest_type": TermDepositInterestType.FIXED_AMOUNT,
                "gross_interest_rate": None,
                "gross_interest_amount": Money(amount="20", currency="EUR"),
            }
        )
    )

    invalid_cases = [
        {"bank_name": " "},
        {"name": ""},
        {"principal": Money(amount="0", currency="EUR")},
        {"costs": Money(amount="-1", currency="EUR")},
        {"estimated_taxes": Money(amount="-1", currency="EUR")},
        {"costs": Money(amount="1", currency="USD")},
        {"estimated_taxes": Money(amount="1", currency="USD")},
        {"gross_interest_rate": None},
        {"gross_interest_amount": Money(amount="1", currency="EUR")},
        {
            "interest_type": TermDepositInterestType.FIXED_AMOUNT,
            "gross_interest_rate": Percentage(value="2"),
            "gross_interest_amount": Money(amount="1", currency="EUR"),
        },
        {
            "interest_type": TermDepositInterestType.FIXED_AMOUNT,
            "gross_interest_rate": None,
            "gross_interest_amount": None,
        },
        {
            "interest_type": TermDepositInterestType.FIXED_AMOUNT,
            "gross_interest_rate": None,
            "gross_interest_amount": Money(amount="1", currency="USD"),
        },
    ]
    for case in invalid_cases:
        with pytest.raises(ValidationError):
            TermDepositInput(**(base_input() | case))

    projection = TermDepositProjection(
        term_deposit_id="td_1",
        portfolio_id="pf_1",
        bank_name="Bank A",
        name="A",
        principal=Money(amount="1000", currency="EUR"),
        start_date=date(2026, 1, 1),
        maturity_date=date(2026, 7, 1),
        term=TermDepositTerm.SIX_MONTHS,
        gross_interest=Money(amount="10", currency="EUR"),
        costs=Money(amount="20", currency="EUR"),
        estimated_taxes=Money(amount="2", currency="EUR"),
        net_interest=Money(amount="-12", currency="EUR"),
        expected_maturity_value=Money(amount="988", currency="EUR"),
        days_until_maturity=0,
        status=TermDepositStatus.MATURED,
    )
    assert projection.net_interest.amount == -12
    assert projection.model_dump()["term_deposit_id"] == "td_1"

    with pytest.raises(ValidationError):
        TermDepositProjection(**(projection.model_dump() | {"maturity_date": date(2026, 1, 1)}))
    with pytest.raises(ValidationError):
        TermDepositProjection(**(projection.model_dump() | {"days_until_maturity": -1}))
