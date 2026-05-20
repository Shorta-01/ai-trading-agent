"""Public export smoke tests for ai_trading_agent_storage package root."""

import ai_trading_agent_storage as storage


def test_research_source_records_used_by_api_are_exported() -> None:
    """Ensure API-imported research source records stay available at package root."""

    assert hasattr(storage, "ResearchSourcePromptInjectionScanRecord")
    assert hasattr(storage, "ResearchSourceCredibilityAssessmentRecord")
    assert hasattr(storage, "ResearchSourceEvidenceItemRecord")
