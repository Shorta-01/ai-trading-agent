from datetime import UTC, datetime, timedelta

import pytest

from portfolio_outlook_domain import (
    ActionSuggestionDraft,
    AdviceAction,
    CandidateSource,
    CandidateStatus,
    CostTaxImpactPlaceholder,
    RiskGateBlockReason,
    RiskGateResult,
    RiskGateStatus,
    SuggestionCandidate,
    SuggestionConfidenceLevel,
    SuggestionDraftDecision,
    SuggestionDraftStatus,
    SuggestionEligibilityCheck,
    SuggestionEligibilityStatus,
    SuggestionEngineRun,
    SuggestionEngineRunStatus,
    SuggestionGateResult,
    SuggestionGateStatus,
    SuggestionGateType,
    build_action_suggestion_draft,
    build_blocked_gate_result,
    build_passed_gate_result,
    decide_suggestion_draft_outcome,
    gate_result_blocks_suggestion,
    risk_gate_blocks_suggestion,
)


def test_identifier_types_accept_and_reject() -> None:
    SuggestionCandidate(
        candidate_id="cand_1",
        instrument_id="inst_1",
        source=CandidateSource.WATCHLIST,
        status=CandidateStatus.NEW,
        source_reference_ids=["src_1"],
        audit_event_ids=["aud_1"],
        explanation_nl="ok",
        created_at=datetime.now(UTC),
    )
    with pytest.raises(ValueError):
        SuggestionCandidate(
            candidate_id="",
            instrument_id="inst_1",
            source=CandidateSource.WATCHLIST,
            status=CandidateStatus.NEW,
            source_reference_ids=["src_1"],
            audit_event_ids=["aud_1"],
            explanation_nl="ok",
            created_at=datetime.now(UTC),
        )


def _elig(status: SuggestionEligibilityStatus) -> SuggestionEligibilityCheck:
    return SuggestionEligibilityCheck(
        suggestion_eligibility_check_id="elig_1",
        policy_id="policy_1",
        data_quality_gate_id="dq_1",
        status=status,
        source_reference_ids=["src_1"]
        if status
        in {
            SuggestionEligibilityStatus.ELIGIBLE,
            SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS,
        }
        else [],
        audit_event_ids=["aud_1"]
        if status
        in {
            SuggestionEligibilityStatus.ELIGIBLE,
            SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS,
        }
        else [],
        warning_reasons=["unknown"]
        if status is SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS
        else [],
        block_reasons=["data_quality_failed"]
        if status in {SuggestionEligibilityStatus.BLOCKED, SuggestionEligibilityStatus.FAILED}
        else [],
        checked_at=datetime.now(UTC),
        explanation_nl="eligibility",
    )


def test_core_models_and_helpers() -> None:
    now = datetime.now(UTC)
    candidate = SuggestionCandidate(
        candidate_id="cand_1",
        instrument_id="inst_1",
        source=CandidateSource.WATCHLIST,
        status=CandidateStatus.ELIGIBLE_FOR_SUGGESTION,
        source_reference_ids=["src_1"],
        audit_event_ids=["aud_1"],
        explanation_nl="uitleg",
        created_at=now,
    )
    passed_gate = build_passed_gate_result(
        suggestion_gate_result_id="gate_1",
        gate_type=SuggestionGateType.CAPABILITY,
        source_reference_ids=["src_1"],
        audit_event_ids=["aud_1"],
        checked_at=now,
        explanation_nl="ok",
    )
    blocked_gate = build_blocked_gate_result(
        suggestion_gate_result_id="gate_2",
        gate_type=SuggestionGateType.AUDIT,
        block_reasons_nl=["geen audit"],
        checked_at=now,
        explanation_nl="block",
    )
    assert gate_result_blocks_suggestion(blocked_gate)
    assert not gate_result_blocks_suggestion(passed_gate)

    risk_pass = RiskGateResult(
        risk_gate_result_id="risk_1",
        status=RiskGateStatus.PASSED,
        explanation_nl="ok",
        checked_at=now,
    )
    risk_warn = RiskGateResult(
        risk_gate_result_id="risk_2",
        status=RiskGateStatus.WARNING,
        warning_reasons_nl=["controleer"],
        explanation_nl="warn",
        checked_at=now,
    )
    assert not risk_gate_blocks_suggestion(risk_warn)
    assert risk_gate_blocks_suggestion(
        RiskGateResult(
            risk_gate_result_id="risk_3",
            status=RiskGateStatus.BLOCKED,
            block_reasons=[RiskGateBlockReason.POLICY_BLOCKED],
            explanation_nl="block",
            checked_at=now,
        )
    )

    cost = CostTaxImpactPlaceholder(
        cost_tax_impact_id="cost_1",
        status=SuggestionGateStatus.PASSED,
        estimated_costs_available=True,
        estimated_taxes_available=True,
        explanation_nl="ok",
        checked_at=now,
    )

    run = SuggestionEngineRun(
        suggestion_engine_run_id="run_1",
        status=SuggestionEngineRunStatus.COMPLETED,
        candidate_ids=["cand_1"],
        started_at=now,
        completed_at=now + timedelta(minutes=1),
        explanation_nl="klaar",
    )
    assert run.model_dump()["status"] == SuggestionEngineRunStatus.COMPLETED

    outcome = decide_suggestion_draft_outcome(
        eligibility_check=_elig(SuggestionEligibilityStatus.ELIGIBLE),
        gate_results=[passed_gate],
        risk_gate_result=risk_pass,
        cost_tax_impact=cost,
    )
    assert outcome is SuggestionDraftDecision.CREATE_DRAFT
    assert (
        decide_suggestion_draft_outcome(
            eligibility_check=_elig(SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS),
            gate_results=[passed_gate],
            risk_gate_result=risk_pass,
        )
        is SuggestionDraftDecision.CREATE_WITH_WARNING
    )
    assert (
        decide_suggestion_draft_outcome(
            eligibility_check=_elig(SuggestionEligibilityStatus.ELIGIBLE),
            gate_results=[
                SuggestionGateResult(
                    suggestion_gate_result_id="gate_w",
                    gate_type=SuggestionGateType.POLICY,
                    status=SuggestionGateStatus.WARNING,
                    warning_reasons_nl=["let op"],
                    explanation_nl="warn",
                    checked_at=now,
                )
            ],
            risk_gate_result=risk_pass,
        )
        is SuggestionDraftDecision.CREATE_WITH_WARNING
    )
    assert (
        decide_suggestion_draft_outcome(
            eligibility_check=_elig(SuggestionEligibilityStatus.ELIGIBLE),
            gate_results=[passed_gate],
            risk_gate_result=risk_warn,
        )
        is SuggestionDraftDecision.CREATE_WITH_WARNING
    )
    assert (
        decide_suggestion_draft_outcome(
            eligibility_check=_elig(SuggestionEligibilityStatus.BLOCKED),
            gate_results=[passed_gate],
            risk_gate_result=risk_pass,
        )
        is SuggestionDraftDecision.BLOCK
    )
    assert (
        decide_suggestion_draft_outcome(
            eligibility_check=_elig(SuggestionEligibilityStatus.SKIPPED),
            gate_results=[passed_gate],
            risk_gate_result=risk_pass,
        )
        is SuggestionDraftDecision.SKIP
    )
    assert (
        decide_suggestion_draft_outcome(
            eligibility_check=_elig(SuggestionEligibilityStatus.FAILED),
            gate_results=[passed_gate],
            risk_gate_result=risk_pass,
        )
        is SuggestionDraftDecision.FAIL
    )

    draft = build_action_suggestion_draft(
        suggestion_draft_id="draft_1",
        candidate=candidate,
        action=AdviceAction.HOLD,
        confidence=SuggestionConfidenceLevel.NOT_AVAILABLE,
        eligibility_check=_elig(SuggestionEligibilityStatus.ELIGIBLE),
        gate_results=[passed_gate],
        risk_gate_result=risk_pass,
        cost_tax_impact=cost,
        title_nl="Actiesuggestie",
        summary_nl="Samenvatting",
        reason_nl="Waarom",
        risk_nl="Risico",
        next_step_nl="Volgende stap",
        created_at=now,
    )
    assert isinstance(draft, ActionSuggestionDraft)
    assert draft.status is SuggestionDraftStatus.READY_FOR_REVIEW
    assert draft.model_dump()["title_nl"] == "Actiesuggestie"

    with pytest.raises(ValueError):
        build_action_suggestion_draft(
            suggestion_draft_id="draft_2",
            candidate=candidate,
            action=AdviceAction.HOLD,
            confidence=SuggestionConfidenceLevel.LOW,
            eligibility_check=_elig(SuggestionEligibilityStatus.BLOCKED),
            gate_results=[passed_gate],
            risk_gate_result=risk_pass,
            cost_tax_impact=None,
            title_nl="Actiesuggestie",
            summary_nl="Samenvatting",
            reason_nl="Waarom",
            risk_nl="Risico",
            next_step_nl="Volgende stap",
            created_at=now,
        )

    with pytest.raises(ValueError):
        ActionSuggestionDraft(
            suggestion_draft_id="draft_x",
            candidate_id="cand_1",
            instrument_id="inst_1",
            action=AdviceAction.HOLD,
            status=SuggestionDraftStatus.CONVERTED_TO_APPROVAL_REQUEST,
            confidence=SuggestionConfidenceLevel.LOW,
            gate_result_ids=["gate_1"],
            risk_gate_result_id="risk_1",
            suggestion_eligibility_check_id="elig_1",
            source_reference_ids=["src_1"],
            audit_event_ids=["aud_1"],
            title_nl="a",
            summary_nl="b",
            reason_nl="c",
            risk_nl="d",
            next_step_nl="e",
            created_at=now,
        )
