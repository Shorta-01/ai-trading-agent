from decimal import Decimal

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import CostEstimate, CostType, Money, TotalCostEstimate


def test_cost_estimate_accepts_positive_money() -> None:
    model = CostEstimate(
        cost_estimate_id="cost_1",
        cost_type=CostType.BROKER_FEE,
        amount=Money(amount=Decimal("1.25"), currency="EUR"),
    )
    assert model.amount.amount == Decimal("1.25")


def test_cost_estimate_rejects_negative_amount() -> None:
    with pytest.raises(ValidationError):
        CostEstimate(
            cost_estimate_id="cost_1",
            cost_type=CostType.BROKER_FEE,
            amount=Money(amount=Decimal("-0.01"), currency="EUR"),
        )


def test_total_by_currency_sums_costs_with_same_currency() -> None:
    total = TotalCostEstimate(
        costs=[
            CostEstimate(
                cost_estimate_id="c1",
                cost_type=CostType.BROKER_FEE,
                amount=Money(amount="1.10", currency="EUR"),
            ),
            CostEstimate(
                cost_estimate_id="c2",
                cost_type=CostType.FX_COST,
                amount=Money(amount="2.40", currency="EUR"),
            ),
        ]
    )
    assert total.total_by_currency() == {"EUR": Decimal("3.50")}


def test_total_by_currency_separates_currencies() -> None:
    total = TotalCostEstimate(
        costs=[
            CostEstimate(
                cost_estimate_id="c1",
                cost_type=CostType.BROKER_FEE,
                amount=Money(amount="1.10", currency="EUR"),
            ),
            CostEstimate(
                cost_estimate_id="c2",
                cost_type=CostType.FX_COST,
                amount=Money(amount="2.40", currency="USD"),
            ),
        ]
    )
    assert total.total_by_currency() == {"EUR": Decimal("1.10"), "USD": Decimal("2.40")}


def test_no_floats_accepted_through_money() -> None:
    with pytest.raises(ValidationError):
        Money(amount=1.5, currency="EUR")
