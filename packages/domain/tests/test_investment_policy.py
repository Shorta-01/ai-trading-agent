import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import InvestmentPolicyStatement
from portfolio_outlook_domain.primitives import Percentage


def test_investment_policy_safe_defaults() -> None:
    policy = InvestmentPolicyStatement(goal="groei", risk_profile="balanced")
    assert policy.allow_leverage is False
    assert policy.allow_short_selling is False
    assert policy.allow_options is False
    assert policy.allow_crypto is False


def test_investment_policy_rejects_invalid_allocation_order() -> None:
    with pytest.raises(ValidationError):
        InvestmentPolicyStatement(
            goal="groei",
            risk_profile="balanced",
            maximum_single_etf_allocation=Percentage(value="10"),
            maximum_single_stock_allocation=Percentage(value="12"),
        )
