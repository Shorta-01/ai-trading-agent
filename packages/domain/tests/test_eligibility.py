from datetime import UTC, datetime

from portfolio_outlook_domain import (
    DataDomain,
    DataGateDecision,
    DataQualityGate,
    DataQualityGateStatus,
    SuggestionEligibilityStatus,
    build_default_suggestion_eligibility_policy,
    evaluate_suggestion_eligibility,
)


def _gate(decision: DataGateDecision) -> DataQualityGate:
    status = DataQualityGateStatus.PASSED
    if decision is DataGateDecision.CONTINUE_WITH_WARNING:
        status = DataQualityGateStatus.WARNING
    if decision is DataGateDecision.BLOCK_SUGGESTION:
        status = DataQualityGateStatus.BLOCKED
    if decision is DataGateDecision.FAIL_JOB:
        status = DataQualityGateStatus.FAILED

    return DataQualityGate(
        data_quality_gate_id="dq_1",
        gate_name="gate",
        required_domains=[DataDomain.MARKET_DATA],
        status=status,
        decision=decision,
        checked_at=datetime.now(UTC),
        explanation_nl="uitleg",
        source_reference_ids=["src_1"] if decision is DataGateDecision.CONTINUE_ALLOWED else [],
    )


def test_evaluate() -> None:
    p = build_default_suggestion_eligibility_policy()
    assert p.require_audit_link and p.require_source_traceability
    ok = evaluate_suggestion_eligibility(
        policy=p,
        data_quality_gate=_gate(DataGateDecision.CONTINUE_ALLOWED),
        source_reference_ids=["src_1"],
        audit_event_ids=["aud_1"],
        checked_at=datetime.now(UTC),
    )
    assert ok.status is SuggestionEligibilityStatus.ELIGIBLE
    warn = evaluate_suggestion_eligibility(
        policy=p,
        data_quality_gate=_gate(DataGateDecision.CONTINUE_WITH_WARNING),
        source_reference_ids=["src_1"],
        audit_event_ids=["aud_1"],
        checked_at=datetime.now(UTC),
    )
    assert warn.status is SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS
    blocked = evaluate_suggestion_eligibility(
        policy=p,
        data_quality_gate=_gate(DataGateDecision.BLOCK_SUGGESTION),
        source_reference_ids=["src_1"],
        audit_event_ids=["aud_1"],
        checked_at=datetime.now(UTC),
    )
    assert blocked.status is SuggestionEligibilityStatus.BLOCKED
    failed = evaluate_suggestion_eligibility(
        policy=p,
        data_quality_gate=_gate(DataGateDecision.FAIL_JOB),
        source_reference_ids=["src_1"],
        audit_event_ids=["aud_1"],
        checked_at=datetime.now(UTC),
    )
    assert failed.status is SuggestionEligibilityStatus.FAILED
