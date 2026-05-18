from datetime import UTC, datetime

import pytest

from portfolio_outlook_domain import (
    DataDomain,
    DataFreshnessCheck,
    DataGateDecision,
    DataQualityGateStatus,
    DataQualityIssue,
    DataQualityIssueType,
    DataQualityPolicy,
    FreshnessRequirement,
    RuntimeHealthSeverity,
    SuggestionEligibilityWarningReason,
    build_blocked_data_quality_gate,
    build_passed_data_quality_gate,
    gate_allows_suggestions,
    gate_blocks_suggestions,
)


def test_data_quality_models() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError):
        DataFreshnessCheck(
            data_freshness_check_id="f1",
            data_domain=DataDomain.MARKET_DATA,
            requirement=FreshnessRequirement.IMMEDIATE,
            observed_at=None,
            checked_at=now,
            status=DataQualityGateStatus.PASSED,
            issue_types=[],
            explanation_nl="ok",
        )
    issue = DataQualityIssue(
        issue_type=DataQualityIssueType.SOURCE_NOT_TRACEABLE,
        data_domain=DataDomain.MARKET_DATA,
        severity=RuntimeHealthSeverity.CRITICAL,
        message_nl="geen bron",
        blocks_suggestions=True,
    )
    gate = build_blocked_data_quality_gate(
        gate_name="g",
        required_domains=[DataDomain.MARKET_DATA],
        issues=[issue],
        checked_at=now,
        explanation_nl="blok",
    )
    assert gate_blocks_suggestions(gate)
    assert not gate_allows_suggestions(gate)
    passed = build_passed_data_quality_gate(
        gate_name="g2",
        required_domains=[DataDomain.MARKET_DATA],
        source_reference_ids=["src_1"],
        checked_at=now,
        explanation_nl="ok",
    )
    assert passed.status is DataQualityGateStatus.PASSED
    assert passed.decision is DataGateDecision.CONTINUE_ALLOWED
    assert gate_allows_suggestions(passed)
    assert passed.model_dump()["gate_name"] == "g2"


def test_policy_overlap_rejected() -> None:
    with pytest.raises(ValueError):
        DataQualityPolicy(
            suggestion_critical_domains=[DataDomain.MARKET_DATA],
            warning_only_domains=[DataDomain.MARKET_DATA],
            accepted_warning_reasons=[SuggestionEligibilityWarningReason.DELAYED_DATA],
            explanation_nl="x",
        )
