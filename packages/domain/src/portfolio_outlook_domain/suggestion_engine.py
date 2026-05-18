from datetime import datetime

from pydantic import Field, model_validator

from .eligibility import SuggestionEligibilityCheck
from .enums import (
    AdviceAction,
    CandidateSource,
    CandidateStatus,
    RiskGateBlockReason,
    RiskGateStatus,
    SuggestionConfidenceLevel,
    SuggestionDraftDecision,
    SuggestionDraftStatus,
    SuggestionEligibilityStatus,
    SuggestionEngineRunStatus,
    SuggestionGateStatus,
    SuggestionGateType,
)
from .identifiers import (
    AuditEventId,
    CandidateId,
    CostTaxImpactId,
    InstrumentId,
    JobRunId,
    ResearchReportId,
    RiskGateResultId,
    SourceReferenceId,
    SuggestionDraftId,
    SuggestionEligibilityCheckId,
    SuggestionEngineRunId,
    SuggestionGateResultId,
)
from .primitives import DomainBaseModel


class SuggestionCandidate(DomainBaseModel):
    candidate_id: CandidateId
    instrument_id: InstrumentId
    source: CandidateSource
    status: CandidateStatus
    research_report_id: ResearchReportId | None = None
    source_reference_ids: list[SourceReferenceId] = Field(default_factory=list)
    audit_event_ids: list[AuditEventId] = Field(default_factory=list)
    explanation_nl: str
    created_at: datetime

    @model_validator(mode="after")
    def validate_model(self) -> "SuggestionCandidate":
        if not self.explanation_nl.strip() or not self.audit_event_ids:
            raise ValueError("explanation_nl en audit_event_ids zijn verplicht")
        if self.source is not CandidateSource.MANUAL_USER_INPUT and not self.source_reference_ids:
            raise ValueError("source_reference_ids zijn verplicht behalve bij manual_user_input")
        if self.status is CandidateStatus.ELIGIBLE_FOR_SUGGESTION and not self.source_reference_ids:
            raise ValueError("eligible_for_suggestion vereist source_reference_ids")
        return self


class SuggestionGateResult(DomainBaseModel):
    suggestion_gate_result_id: SuggestionGateResultId
    gate_type: SuggestionGateType
    status: SuggestionGateStatus
    block_reasons_nl: list[str] = Field(default_factory=list)
    warning_reasons_nl: list[str] = Field(default_factory=list)
    source_reference_ids: list[SourceReferenceId] = Field(default_factory=list)
    audit_event_ids: list[AuditEventId] = Field(default_factory=list)
    explanation_nl: str
    checked_at: datetime

    @model_validator(mode="after")
    def validate_model(self) -> "SuggestionGateResult":
        if not self.explanation_nl.strip():
            raise ValueError("explanation_nl is verplicht")
        if self.status is SuggestionGateStatus.PASSED:
            if self.block_reasons_nl or self.warning_reasons_nl:
                raise ValueError("passed mag geen redenen hebben")
            if not self.source_reference_ids or not self.audit_event_ids:
                raise ValueError("passed vereist source_reference_ids en audit_event_ids")
        if self.status is SuggestionGateStatus.WARNING:
            if self.block_reasons_nl or not self.warning_reasons_nl:
                raise ValueError("warning vereist alleen warning_reasons_nl")
        if (
            self.status in {SuggestionGateStatus.BLOCKED, SuggestionGateStatus.FAILED}
            and not self.block_reasons_nl
        ):
            raise ValueError("blocked/failed vereist block_reasons_nl")
        return self


class RiskGateResult(DomainBaseModel):
    risk_gate_result_id: RiskGateResultId
    status: RiskGateStatus
    block_reasons: list[RiskGateBlockReason] = Field(default_factory=list)
    warning_reasons_nl: list[str] = Field(default_factory=list)
    explanation_nl: str
    checked_at: datetime

    @model_validator(mode="after")
    def validate_model(self) -> "RiskGateResult":
        if not self.explanation_nl.strip():
            raise ValueError("explanation_nl is verplicht")
        if self.status is RiskGateStatus.PASSED:
            if self.block_reasons or self.warning_reasons_nl:
                raise ValueError("passed mag geen reasons bevatten")
        if self.status is RiskGateStatus.WARNING:
            if self.block_reasons or not self.warning_reasons_nl:
                raise ValueError("warning vereist warning_reasons_nl")
        if (
            self.status in {RiskGateStatus.BLOCKED, RiskGateStatus.FAILED}
            and not self.block_reasons
        ):
            raise ValueError("blocked/failed vereist block_reasons")
        return self


class CostTaxImpactPlaceholder(DomainBaseModel):
    cost_tax_impact_id: CostTaxImpactId
    status: SuggestionGateStatus
    estimated_costs_available: bool
    estimated_taxes_available: bool
    explanation_nl: str
    checked_at: datetime

    @model_validator(mode="after")
    def validate_model(self) -> "CostTaxImpactPlaceholder":
        if not self.explanation_nl.strip():
            raise ValueError("explanation_nl is verplicht")
        if self.status is SuggestionGateStatus.PASSED:
            if not self.estimated_costs_available or not self.estimated_taxes_available:
                raise ValueError("passed vereist kosten en taksen beschikbaar")
        return self


class SuggestionEngineRun(DomainBaseModel):
    suggestion_engine_run_id: SuggestionEngineRunId
    status: SuggestionEngineRunStatus
    candidate_ids: list[CandidateId] = Field(default_factory=list)
    scheduler_job_run_id: JobRunId | None = None
    started_at: datetime
    completed_at: datetime | None = None
    explanation_nl: str

    @model_validator(mode="after")
    def validate_model(self) -> "SuggestionEngineRun":
        if not self.explanation_nl.strip() or not self.candidate_ids:
            raise ValueError("explanation_nl en candidate_ids zijn verplicht")
        if (
            self.status
            in {
                SuggestionEngineRunStatus.COMPLETED,
                SuggestionEngineRunStatus.COMPLETED_WITH_WARNINGS,
                SuggestionEngineRunStatus.BLOCKED,
                SuggestionEngineRunStatus.FAILED,
            }
            and self.completed_at is None
        ):
            raise ValueError("completed_at is verplicht voor eindstatus")
        if self.completed_at and self.completed_at < self.started_at:
            raise ValueError("completed_at moet na started_at liggen")
        return self


class ActionSuggestionDraft(DomainBaseModel):
    suggestion_draft_id: SuggestionDraftId
    candidate_id: CandidateId
    instrument_id: InstrumentId
    action: AdviceAction
    status: SuggestionDraftStatus
    confidence: SuggestionConfidenceLevel
    gate_result_ids: list[SuggestionGateResultId] = Field(default_factory=list)
    risk_gate_result_id: RiskGateResultId
    cost_tax_impact_id: CostTaxImpactId | None = None
    suggestion_eligibility_check_id: SuggestionEligibilityCheckId
    source_reference_ids: list[SourceReferenceId] = Field(default_factory=list)
    audit_event_ids: list[AuditEventId] = Field(default_factory=list)
    title_nl: str
    summary_nl: str
    reason_nl: str
    risk_nl: str
    next_step_nl: str
    created_at: datetime

    @model_validator(mode="after")
    def validate_model(self) -> "ActionSuggestionDraft":
        if self.status is SuggestionDraftStatus.CONVERTED_TO_APPROVAL_REQUEST:
            raise ValueError("converted_to_approval_request is niet toegestaan bij creatie")
        if self.action is AdviceAction.BLOCKED:
            raise ValueError("action blocked is niet toegestaan")
        required_text = [
            self.title_nl,
            self.summary_nl,
            self.reason_nl,
            self.risk_nl,
            self.next_step_nl,
        ]
        if any(not field.strip() for field in required_text):
            raise ValueError("Nederlandse uitlegvelden zijn verplicht")
        if not self.source_reference_ids or not self.audit_event_ids or not self.gate_result_ids:
            raise ValueError("sources, audit events en gate_result_ids zijn verplicht")
        return self


def build_passed_gate_result(
    *,
    suggestion_gate_result_id: SuggestionGateResultId,
    gate_type: SuggestionGateType,
    source_reference_ids: list[SourceReferenceId],
    audit_event_ids: list[AuditEventId],
    checked_at: datetime,
    explanation_nl: str,
) -> SuggestionGateResult:
    return SuggestionGateResult(
        suggestion_gate_result_id=suggestion_gate_result_id,
        gate_type=gate_type,
        status=SuggestionGateStatus.PASSED,
        source_reference_ids=source_reference_ids,
        audit_event_ids=audit_event_ids,
        checked_at=checked_at,
        explanation_nl=explanation_nl,
    )


def build_blocked_gate_result(
    *,
    suggestion_gate_result_id: SuggestionGateResultId,
    gate_type: SuggestionGateType,
    block_reasons_nl: list[str],
    checked_at: datetime,
    explanation_nl: str,
) -> SuggestionGateResult:
    return SuggestionGateResult(
        suggestion_gate_result_id=suggestion_gate_result_id,
        gate_type=gate_type,
        status=SuggestionGateStatus.BLOCKED,
        block_reasons_nl=block_reasons_nl,
        checked_at=checked_at,
        explanation_nl=explanation_nl,
    )


def gate_result_blocks_suggestion(gate: SuggestionGateResult) -> bool:
    return gate.status in {SuggestionGateStatus.BLOCKED, SuggestionGateStatus.FAILED}


def risk_gate_blocks_suggestion(gate: RiskGateResult) -> bool:
    return gate.status in {RiskGateStatus.BLOCKED, RiskGateStatus.FAILED}


def decide_suggestion_draft_outcome(
    *,
    eligibility_check: SuggestionEligibilityCheck,
    gate_results: list[SuggestionGateResult],
    risk_gate_result: RiskGateResult,
    cost_tax_impact: CostTaxImpactPlaceholder | None = None,
) -> SuggestionDraftDecision:
    if eligibility_check.status is SuggestionEligibilityStatus.SKIPPED:
        return SuggestionDraftDecision.SKIP
    if eligibility_check.status is SuggestionEligibilityStatus.FAILED:
        return SuggestionDraftDecision.FAIL
    if eligibility_check.status is SuggestionEligibilityStatus.BLOCKED:
        return SuggestionDraftDecision.BLOCK
    if any(gate_result_blocks_suggestion(gate) for gate in gate_results):
        return SuggestionDraftDecision.BLOCK
    if risk_gate_blocks_suggestion(risk_gate_result):
        return SuggestionDraftDecision.BLOCK
    if cost_tax_impact and cost_tax_impact.status in {
        SuggestionGateStatus.BLOCKED,
        SuggestionGateStatus.FAILED,
    }:
        return SuggestionDraftDecision.BLOCK
    if (
        eligibility_check.status is SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS
        or any(gate.status is SuggestionGateStatus.WARNING for gate in gate_results)
        or risk_gate_result.status is RiskGateStatus.WARNING
    ):
        return SuggestionDraftDecision.CREATE_WITH_WARNING
    return SuggestionDraftDecision.CREATE_DRAFT


def build_action_suggestion_draft(
    *,
    suggestion_draft_id: SuggestionDraftId,
    candidate: SuggestionCandidate,
    action: AdviceAction,
    confidence: SuggestionConfidenceLevel,
    eligibility_check: SuggestionEligibilityCheck,
    gate_results: list[SuggestionGateResult],
    risk_gate_result: RiskGateResult,
    cost_tax_impact: CostTaxImpactPlaceholder | None,
    title_nl: str,
    summary_nl: str,
    reason_nl: str,
    risk_nl: str,
    next_step_nl: str,
    created_at: datetime,
) -> ActionSuggestionDraft:
    outcome = decide_suggestion_draft_outcome(
        eligibility_check=eligibility_check,
        gate_results=gate_results,
        risk_gate_result=risk_gate_result,
        cost_tax_impact=cost_tax_impact,
    )
    if outcome in {
        SuggestionDraftDecision.BLOCK,
        SuggestionDraftDecision.SKIP,
        SuggestionDraftDecision.FAIL,
    }:
        raise ValueError(f"cannot build draft with outcome {outcome.value}")

    gate_ids = [
        g.suggestion_gate_result_id
        for g in gate_results
        if g.status in {SuggestionGateStatus.PASSED, SuggestionGateStatus.WARNING}
    ]
    return ActionSuggestionDraft(
        suggestion_draft_id=suggestion_draft_id,
        candidate_id=candidate.candidate_id,
        instrument_id=candidate.instrument_id,
        action=action,
        status=SuggestionDraftStatus.READY_FOR_REVIEW,
        confidence=confidence,
        gate_result_ids=gate_ids,
        risk_gate_result_id=risk_gate_result.risk_gate_result_id,
        cost_tax_impact_id=cost_tax_impact.cost_tax_impact_id if cost_tax_impact else None,
        suggestion_eligibility_check_id=eligibility_check.suggestion_eligibility_check_id,
        source_reference_ids=candidate.source_reference_ids,
        audit_event_ids=candidate.audit_event_ids,
        title_nl=title_nl,
        summary_nl=summary_nl,
        reason_nl=reason_nl,
        risk_nl=risk_nl,
        next_step_nl=next_step_nl,
        created_at=created_at,
    )
