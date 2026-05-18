from datetime import UTC, datetime

import pytest

from portfolio_outlook_domain import (
    DataAccessMethod,
    DataCostTier,
    DataDomain,
    DataFailurePolicy,
    DataFreshnessClass,
    DataProviderKind,
    DataSourceDefinition,
    DataSourcePolicy,
    DataSourceRegistry,
    DataSourceRequirement,
    DataUsageStatus,
    DataUsePermission,
    SourceReliabilityTier,
    build_default_data_source_registry,
    can_use_source_for,
    find_sources_for_domain,
    requires_block_when_missing,
)


def test_default_registry_contains_expected_sources() -> None:
    registry = build_default_data_source_registry(created_at=datetime.now(UTC))
    assert len(registry.sources) >= 18

    public_news = [s for s in registry.sources if s.provider_kind == DataProviderKind.PUBLIC_NEWS]
    assert len(public_news) == 1
    assert not can_use_source_for(public_news[0], DataUsePermission.SUGGESTION_ELIGIBILITY)


def test_blocked_policy_rejects_allowed_uses() -> None:
    with pytest.raises(ValueError):
        DataSourcePolicy(
            data_source_policy_id="policy1",
            usage_status=DataUsageStatus.BLOCKED,
            reliability_tier=SourceReliabilityTier.UNKNOWN,
            allowed_uses=[DataUsePermission.RESEARCH_CONTEXT],
            legal_review_status_nl="Niet ok",
            notes_nl="Geblokkeerd",
        )


def test_review_required_requires_manual_or_license_review() -> None:
    with pytest.raises(ValueError):
        DataSourcePolicy(
            data_source_policy_id="policy2",
            usage_status=DataUsageStatus.REVIEW_REQUIRED,
            reliability_tier=SourceReliabilityTier.UNKNOWN,
            legal_review_status_nl="Review nodig",
            notes_nl="Wacht op review",
        )


def test_registry_rejects_duplicate_ids() -> None:
    policy = DataSourcePolicy(
        data_source_policy_id="policy3",
        usage_status=DataUsageStatus.ALLOWED,
        reliability_tier=SourceReliabilityTier.HIGH,
        allowed_uses=[DataUsePermission.RESEARCH_CONTEXT],
        legal_review_status_nl="Goedgekeurd",
        notes_nl="Ok",
    )
    source = DataSourceDefinition(
        data_source_id="src1",
        name="Source",
        provider_kind=DataProviderKind.INTERNAL_SYSTEM,
        data_domains=[DataDomain.RESEARCH_CONTEXT],
        access_method=DataAccessMethod.INTERNAL_SYSTEM,
        cost_tier=DataCostTier.INTERNAL,
        policy=policy,
        notes_nl="Interne bron",
    )
    requirement = DataSourceRequirement(
        data_source_requirement_id="req1",
        name="Req",
        data_domain=DataDomain.RESEARCH_CONTEXT,
        use_permission=DataUsePermission.RESEARCH_CONTEXT,
        freshness_class=DataFreshnessClass.WEEKLY,
        failure_policy=DataFailurePolicy.WARN_AND_LOG,
        notes_nl="Notitie",
    )

    with pytest.raises(ValueError):
        DataSourceRegistry(
            data_source_registry_id="registry1",
            created_at=datetime.now(UTC),
            sources=[source, source],
            requirements=[requirement],
        )


def test_requirement_validation_and_helpers() -> None:
    req = DataSourceRequirement(
        data_source_requirement_id="req_ok",
        name="Waardering",
        data_domain=DataDomain.MARKET_DATA,
        use_permission=DataUsePermission.PORTFOLIO_VALUATION,
        freshness_class=DataFreshnessClass.DAILY,
        failure_policy=DataFailurePolicy.BLOCK_OPERATION,
        notes_nl="Moet compleet zijn",
    )
    assert requires_block_when_missing(req)

    with pytest.raises(ValueError):
        DataSourceRequirement(
            data_source_requirement_id="req_bad",
            name="Suggestie",
            data_domain=DataDomain.RESEARCH_OUTPUT,
            use_permission=DataUsePermission.SUGGESTION_ELIGIBILITY,
            freshness_class=DataFreshnessClass.DAILY,
            failure_policy=DataFailurePolicy.IGNORE_IF_OPTIONAL,
            notes_nl="Mag niet",
        )


def test_source_url_cannot_contain_obvious_secret() -> None:
    policy = DataSourcePolicy(
        data_source_policy_id="policy_ok",
        usage_status=DataUsageStatus.ALLOWED_WITH_LIMITS,
        reliability_tier=SourceReliabilityTier.MEDIUM,
        allowed_uses=[DataUsePermission.RESEARCH_CONTEXT],
        legal_review_status_nl="Review ok",
        notes_nl="Beperkt",
    )

    with pytest.raises(ValueError):
        DataSourceDefinition(
            data_source_id="src_secret",
            name="Secret URL source",
            provider_kind=DataProviderKind.PUBLIC_WEBSITE,
            data_domains=[DataDomain.RESEARCH_CONTEXT],
            access_method=DataAccessMethod.PUBLIC_WEBSITE,
            cost_tier=DataCostTier.FREE,
            policy=policy,
            source_url="https://example.com?apiKey=secret",
            notes_nl="Niet ok",
        )


def test_find_sources_for_domain_returns_matches() -> None:
    registry = build_default_data_source_registry(created_at=datetime.now(UTC))
    result = find_sources_for_domain(registry, DataDomain.MARKET_DATA)
    assert result
