"""Public export smoke tests for ai_trading_agent_storage package root."""

import ai_trading_agent_storage as storage


def test_research_source_records_used_by_api_are_exported() -> None:
    """Ensure API-imported research source records stay available at package root."""

    assert hasattr(storage, "ResearchSourcePromptInjectionScanRecord")
    assert hasattr(storage, "ResearchSourceCredibilityAssessmentRecord")
    assert hasattr(storage, "ResearchSourceEvidenceItemRecord")
    assert hasattr(storage, "ResearchGateOutcomeRecord")
    assert hasattr(storage, "ResearchSourceConflictFindingRecord")
    assert hasattr(storage, "SourceToAssetLinkRecord")
    assert hasattr(storage, "AssetListingRecord")

    assert hasattr(storage, "RequestLogRecord")
    assert hasattr(storage, "ProviderSourceRecord")
    assert hasattr(storage, "FreshnessAuditRecord")
    assert hasattr(storage, "RequestAuditRepository")
    assert hasattr(storage, "SqlAlchemyRequestAuditRepository")
    assert hasattr(storage, "request_logs")
    assert hasattr(storage, "provider_sources")
    assert hasattr(storage, "freshness_audit_records")
