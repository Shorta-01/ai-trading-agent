import pytest
from portfolio_outlook_domain import CapabilityCategory

from portfolio_outlook_portfolio import (
    check_can_create_paper_order,
    check_can_create_paper_transaction,
    check_can_enter_paper_portfolio,
    check_can_generate_action_suggestion,
    check_can_research,
    check_can_watch,
    get_asset_capability,
    get_default_asset_capabilities,
    require_can_create_paper_order,
    require_can_create_paper_transaction,
)
from portfolio_outlook_portfolio.errors import InvalidAccountingInputError


def test_registry_and_unknown_are_safe() -> None:
    registry = get_default_asset_capabilities()
    assert CapabilityCategory.CASH in registry
    assert CapabilityCategory.FUTURES in registry
    assert CapabilityCategory.AUTOMATIC_REAL_MONEY_EXECUTION in registry
    assert all(cap.explanation_nl.strip() for cap in registry.values())
    assert get_asset_capability(CapabilityCategory.UNKNOWN).status.value == "blocked"


def test_allowed_categories() -> None:
    assert check_can_watch(CapabilityCategory.CASH).allowed
    assert check_can_enter_paper_portfolio(CapabilityCategory.TERM_DEPOSIT).allowed
    assert check_can_generate_action_suggestion(CapabilityCategory.UCITS_ETF).allowed
    assert check_can_create_paper_order(CapabilityCategory.STOCK).allowed
    assert check_can_research(CapabilityCategory.FX).allowed
    assert not check_can_create_paper_order(CapabilityCategory.BENCHMARK).allowed
    assert check_can_create_paper_order(CapabilityCategory.COMMODITY_ETF_ETC).allowed


def test_watch_only_and_blocked_categories() -> None:
    for category in [
        CapabilityCategory.FUTURES,
        CapabilityCategory.OPTIONS,
        CapabilityCategory.LEVERAGE,
        CapabilityCategory.SHORT_SELLING,
        CapabilityCategory.CRYPTO,
        CapabilityCategory.PENNY_STOCK,
        CapabilityCategory.COMPLEX_DERIVATIVE,
        CapabilityCategory.HIGH_FREQUENCY_TRADING,
    ]:
        assert check_can_watch(category).allowed
        assert check_can_research(category).allowed
        assert not check_can_generate_action_suggestion(category).allowed
        assert not check_can_create_paper_order(category).allowed
        assert not check_can_create_paper_transaction(category).allowed
        assert not check_can_enter_paper_portfolio(category).allowed

    real_money = CapabilityCategory.AUTOMATIC_REAL_MONEY_EXECUTION
    assert not check_can_watch(real_money).allowed
    assert not check_can_research(real_money).allowed
    assert not check_can_create_paper_order(real_money).allowed
    assert not check_can_create_paper_transaction(real_money).allowed
    assert not check_can_enter_paper_portfolio(real_money).allowed


def test_require_and_model_dump() -> None:
    require_can_create_paper_order(CapabilityCategory.UCITS_ETF)
    with pytest.raises(InvalidAccountingInputError):
        require_can_create_paper_order(CapabilityCategory.CRYPTO)
    with pytest.raises(InvalidAccountingInputError):
        require_can_create_paper_order(CapabilityCategory.AUTOMATIC_REAL_MONEY_EXECUTION)
    with pytest.raises(InvalidAccountingInputError):
        require_can_create_paper_transaction(CapabilityCategory.OPTIONS)
    with pytest.raises(InvalidAccountingInputError):
        require_can_create_paper_transaction(CapabilityCategory.AUTOMATIC_REAL_MONEY_EXECUTION)

    assert isinstance(
        check_can_create_paper_transaction(CapabilityCategory.CRYPTO).model_dump(), dict
    )
