from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import (
    ApiBudgetPolicy,
    ApiConnectionCheck,
    ApiConnectionCheckStatus,
    BudgetPeriod,
    ExternalIntegrationKind,
    ExternalIntegrationStatus,
    IBKRApiGatewayKind,
    IBKRConnectionMode,
    IBKRConnectionSettings,
    OpenAIIntegrationSettings,
    OpenAIModelPricing,
    OpenAIModelPurpose,
    OpenAIUsageSource,
    PaperLiveMode,
    PortfolioSettings,
    SecretReference,
    SecretStatus,
    SecretStorageKind,
    build_default_settings_profile,
    calculate_budget_status,
    connection_check_blocks_jobs,
    estimate_openai_cost,
    ibkr_settings_ready_for_paper,
    openai_settings_ready,
    remaining_budget_eur,
)


def test_portfolio_settings_defaults() -> None:
    assert PortfolioSettings().paper_live_mode == PaperLiveMode.PAPER


def test_secret_reference_and_helpers() -> None:
    secret = SecretReference(
        secret_reference_id="sec1",
        secret_name="OpenAI",
        storage_kind=SecretStorageKind.ENVIRONMENT_VARIABLE,
        status=SecretStatus.AVAILABLE,
        environment_variable_name="OPENAI_API_KEY",
        configured=True,
        explanation_nl="ok",
    )
    assert secret.model_dump()["secret_reference_id"] == "sec1"
    with pytest.raises(ValidationError):
        SecretReference(
            secret_reference_id="sec2",
            secret_name="OpenAI",
            storage_kind=SecretStorageKind.NOT_CONFIGURED,
            status=SecretStatus.NOT_CONFIGURED,
            configured=True,
            explanation_nl="x",
        )


def test_ibkr_settings_validation_and_ready() -> None:
    s = IBKRConnectionSettings(
        external_integration_id="ibkr1",
        status=ExternalIntegrationStatus.NOT_CONFIGURED,
        connection_mode=IBKRConnectionMode.NOT_CONFIGURED,
        gateway_kind=IBKRApiGatewayKind.NOT_CONFIGURED,
        enabled=False,
        paper_account_required=True,
        allow_live_order_transmission=False,
        explanation_nl="Nog niet",
    )
    assert not ibkr_settings_ready_for_paper(s)


def test_openai_settings_ready() -> None:
    settings = OpenAIIntegrationSettings(
        external_integration_id="openai1",
        status=ExternalIntegrationStatus.CONFIGURED,
        enabled=True,
        api_key_secret_reference_id="sec1",
        default_research_model="gpt-x",
        explanation_nl="ok",
    )
    secret = SecretReference(
        secret_reference_id="sec1",
        secret_name="OpenAI",
        storage_kind=SecretStorageKind.ENVIRONMENT_VARIABLE,
        status=SecretStatus.AVAILABLE,
        environment_variable_name="OPENAI_API_KEY",
        configured=True,
        explanation_nl="ok",
    )
    assert openai_settings_ready(settings, [secret])


def test_cost_and_budget() -> None:
    pricing = OpenAIModelPricing(
        model_pricing_id="mp1",
        model_name="model",
        input_usd_per_1m_tokens=Decimal("2"),
        cached_input_usd_per_1m_tokens=Decimal("1"),
        output_usd_per_1m_tokens=Decimal("4"),
        purpose=OpenAIModelPurpose.DEEP_RESEARCH,
        effective_from=datetime.now(),
        source_reference_ids=["src1"],
        audit_event_ids=["aud1"],
        explanation_nl="ok",
    )
    estimate = estimate_openai_cost(
        pricing=pricing,
        input_tokens=1_000_000,
        cached_input_tokens=1_000_000,
        output_tokens=1_000_000,
        calculated_at=datetime.now(),
        eur_usd_exchange_rate=Decimal("1.1"),
    )
    assert estimate.estimated_cost_usd == Decimal("7")
    policy = ApiBudgetPolicy(
        api_budget_policy_id="b1",
        integration_kind=ExternalIntegrationKind.OPENAI,
        period=BudgetPeriod.MONTHLY,
        budget_amount_eur=Decimal("10"),
        warning_threshold_percent=Decimal("50"),
        critical_threshold_percent=Decimal("80"),
        block_when_exceeded=True,
        enabled=True,
        explanation_nl="ok",
    )
    assert calculate_budget_status(policy=policy, estimated_cost_eur=Decimal("9")) == "critical"
    assert remaining_budget_eur(policy=policy, estimated_cost_eur=Decimal("20")) == Decimal("0")


def test_user_strategy_settings_default_trading_cycle_parameters() -> None:
    from portfolio_outlook_domain.settings import UserStrategySettings

    settings = UserStrategySettings()
    # Locked retiree-income doctrine defaults.
    assert settings.trading_target_net_pct == Decimal("4")
    assert settings.trading_horizon_min_months == 3
    assert settings.trading_horizon_max_months == 6
    assert settings.trading_min_position_eur == Decimal("25000")
    assert settings.trading_max_position_eur == Decimal("100000")
    assert settings.trading_confidence_threshold_pct == Decimal("70")
    assert settings.trading_max_sector_pct == Decimal("25")
    assert settings.trading_min_market_cap_eur == Decimal("5000000000")
    assert settings.trading_max_annual_volatility_pct == Decimal("30")
    assert settings.trading_total_budget_eur == Decimal("1000000")


def test_user_strategy_settings_rejects_float_trading_inputs() -> None:
    from portfolio_outlook_domain.settings import UserStrategySettings

    with pytest.raises(ValidationError):
        UserStrategySettings(trading_target_net_pct=4.0)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        UserStrategySettings(trading_min_position_eur=25000.0)  # type: ignore[arg-type]


def test_user_strategy_settings_rejects_invalid_target_range() -> None:
    from portfolio_outlook_domain.settings import UserStrategySettings

    # 0% net target is below TOB round-trip cost — refuse.
    with pytest.raises(ValidationError):
        UserStrategySettings(trading_target_net_pct=Decimal("0"))
    # 60% is moonshot territory.
    with pytest.raises(ValidationError):
        UserStrategySettings(trading_target_net_pct=Decimal("60"))


def test_user_strategy_settings_rejects_invalid_horizon() -> None:
    from portfolio_outlook_domain.settings import UserStrategySettings

    with pytest.raises(ValidationError):
        UserStrategySettings(trading_horizon_min_months=0)
    with pytest.raises(ValidationError):
        UserStrategySettings(trading_horizon_max_months=25)


def test_user_strategy_settings_rejects_max_before_min_horizon() -> None:
    from portfolio_outlook_domain.settings import UserStrategySettings

    with pytest.raises(ValidationError):
        UserStrategySettings(
            trading_horizon_min_months=6, trading_horizon_max_months=3
        )


def test_user_strategy_settings_rejects_inverted_position_bounds() -> None:
    from portfolio_outlook_domain.settings import UserStrategySettings

    with pytest.raises(ValidationError):
        UserStrategySettings(
            trading_min_position_eur=Decimal("100000"),
            trading_max_position_eur=Decimal("50000"),
        )


def test_user_strategy_settings_rejects_position_above_budget() -> None:
    from portfolio_outlook_domain.settings import UserStrategySettings

    with pytest.raises(ValidationError):
        UserStrategySettings(
            trading_max_position_eur=Decimal("2000000"),
            trading_total_budget_eur=Decimal("1000000"),
        )


def test_user_strategy_settings_rejects_negative_eur_amounts() -> None:
    from portfolio_outlook_domain.settings import UserStrategySettings

    with pytest.raises(ValidationError):
        UserStrategySettings(trading_min_position_eur=Decimal("0"))
    with pytest.raises(ValidationError):
        UserStrategySettings(trading_total_budget_eur=Decimal("-1"))


def test_user_strategy_help_texts_cover_all_trading_fields() -> None:
    from portfolio_outlook_domain.settings import get_user_strategy_help_texts

    keys = {entry.key for entry in get_user_strategy_help_texts()}
    expected = {
        "trading_target_net_pct",
        "trading_horizon_min_months",
        "trading_horizon_max_months",
        "trading_min_position_eur",
        "trading_max_position_eur",
        "trading_confidence_threshold_pct",
        "trading_max_sector_pct",
        "trading_min_market_cap_eur",
        "trading_max_annual_volatility_pct",
        "trading_total_budget_eur",
    }
    assert expected.issubset(keys)


def test_usage_summary_and_connection_check_and_profile() -> None:
    from portfolio_outlook_domain.settings import ApiUsageSummary, SettingsProfile

    now = datetime.now()
    ApiUsageSummary(
        api_usage_summary_id="u1",
        integration_kind=ExternalIntegrationKind.OPENAI,
        usage_source=OpenAIUsageSource.LOCAL_ESTIMATE,
        period=BudgetPeriod.DAILY,
        period_start=now,
        period_end=now + timedelta(hours=1),
        input_tokens=1,
        cached_input_tokens=2,
        output_tokens=3,
        total_tokens=6,
        source_reference_ids=[],
        audit_event_ids=["aud1"],
        explanation_nl="ok",
    )
    check = ApiConnectionCheck(
        api_connection_check_id="c1",
        integration_kind=ExternalIntegrationKind.OPENAI,
        status=ApiConnectionCheckStatus.BLOCKED,
        checked_at=now,
        message_nl="blok",
        blocks_related_jobs=True,
    )
    assert connection_check_blocks_jobs(check)
    profile = build_default_settings_profile(created_at=now)
    assert profile.ibkr_settings.status == ExternalIntegrationStatus.NOT_CONFIGURED
    assert profile.openai_settings.status == ExternalIntegrationStatus.NOT_CONFIGURED
    assert "secret_value" not in str(profile.model_dump()).lower()
    assert isinstance(SettingsProfile(**profile.model_dump()), SettingsProfile)
