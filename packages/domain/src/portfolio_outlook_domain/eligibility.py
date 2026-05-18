from datetime import datetime

from pydantic import Field, model_validator

from .data_quality import DataQualityGate
from .enums import (
    DataGateDecision,
    SuggestionEligibilityBlockReason,
    SuggestionEligibilityStatus,
    SuggestionEligibilityWarningReason,
)
from .identifiers import (
    AuditEventId,
    DataQualityGateId,
    InstrumentId,
    SourceReferenceId,
    SuggestionEligibilityCheckId,
    SuggestionEligibilityPolicyId,
)
from .primitives import DomainBaseModel


class SuggestionEligibilityPolicy(DomainBaseModel):
    suggestion_eligibility_policy_id: SuggestionEligibilityPolicyId
    policy_name: str
    require_data_quality_pass: bool = True
    require_source_traceability: bool = True
    require_service_health: bool = True
    require_capability_allowed: bool = True
    require_risk_pass: bool = True
    require_audit_link: bool = True
    explanation_nl: str

    @model_validator(mode="after")
    def validate_policy(self) -> "SuggestionEligibilityPolicy":
        if not self.policy_name.strip() or not self.explanation_nl.strip():
            raise ValueError("policy_name en explanation_nl zijn verplicht")
        return self


class SuggestionEligibilityCheck(DomainBaseModel):
    suggestion_eligibility_check_id: SuggestionEligibilityCheckId
    policy_id: SuggestionEligibilityPolicyId
    instrument_id: InstrumentId | None = None
    data_quality_gate_id: DataQualityGateId
    status: SuggestionEligibilityStatus
    block_reasons: list[SuggestionEligibilityBlockReason] = Field(default_factory=list)
    warning_reasons: list[SuggestionEligibilityWarningReason] = Field(default_factory=list)
    source_reference_ids: list[SourceReferenceId] = Field(default_factory=list)
    audit_event_ids: list[AuditEventId] = Field(default_factory=list)
    checked_at: datetime
    explanation_nl: str

    @model_validator(mode="after")
    def validate_check(self) -> "SuggestionEligibilityCheck":
        if not self.explanation_nl.strip():
            raise ValueError("explanation_nl is verplicht")
        if self.status is SuggestionEligibilityStatus.ELIGIBLE:
            if self.block_reasons or self.warning_reasons:
                raise ValueError("eligible status mag geen block of warning reasons hebben")
        if self.status is SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS:
            if self.block_reasons:
                raise ValueError("eligible_with_warnings mag geen block reasons hebben")
            if not self.warning_reasons:
                raise ValueError("eligible_with_warnings vereist warning reasons")
        if self.status is SuggestionEligibilityStatus.BLOCKED and not self.block_reasons:
            raise ValueError("blocked status vereist block reasons")
        if (
            self.status
            in {
                SuggestionEligibilityStatus.ELIGIBLE,
                SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS,
            }
            and not self.source_reference_ids
        ):
            raise ValueError("eligible statuses vereisen source_reference_ids")
        if (
            self.status
            in {
                SuggestionEligibilityStatus.ELIGIBLE,
                SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS,
            }
            and not self.audit_event_ids
        ):
            raise ValueError("eligible statuses vereisen audit_event_ids")
        return self


def build_default_suggestion_eligibility_policy() -> SuggestionEligibilityPolicy:
    return SuggestionEligibilityPolicy(
        suggestion_eligibility_policy_id="eligibility_policy_default",
        policy_name="Standaard suggestiebeleid",
        explanation_nl="Suggesties zijn alleen toegestaan met controleerbare data en auditlink.",
    )


def evaluate_suggestion_eligibility(
    *,
    policy: SuggestionEligibilityPolicy,
    data_quality_gate: DataQualityGate,
    source_reference_ids: list[SourceReferenceId],
    audit_event_ids: list[AuditEventId],
    checked_at: datetime,
    instrument_id: InstrumentId | None = None,
) -> SuggestionEligibilityCheck:
    block_reasons: list[SuggestionEligibilityBlockReason] = []
    warning_reasons: list[SuggestionEligibilityWarningReason] = []
    status = SuggestionEligibilityStatus.BLOCKED

    if policy.require_source_traceability and not source_reference_ids:
        block_reasons.append(SuggestionEligibilityBlockReason.SOURCE_NOT_TRACEABLE)
    if policy.require_audit_link and not audit_event_ids:
        block_reasons.append(SuggestionEligibilityBlockReason.AUDIT_LINK_MISSING)

    if block_reasons:
        status = SuggestionEligibilityStatus.BLOCKED
    elif data_quality_gate.decision is DataGateDecision.CONTINUE_ALLOWED:
        status = SuggestionEligibilityStatus.ELIGIBLE
    elif data_quality_gate.decision is DataGateDecision.CONTINUE_WITH_WARNING:
        status = SuggestionEligibilityStatus.ELIGIBLE_WITH_WARNINGS
        warning_reasons.append(SuggestionEligibilityWarningReason.UNKNOWN)
    elif data_quality_gate.decision is DataGateDecision.SKIP_JOB:
        status = SuggestionEligibilityStatus.SKIPPED
    elif data_quality_gate.decision is DataGateDecision.BLOCK_SUGGESTION:
        status = SuggestionEligibilityStatus.BLOCKED
        block_reasons.append(SuggestionEligibilityBlockReason.DATA_QUALITY_FAILED)
    elif data_quality_gate.decision is DataGateDecision.FAIL_JOB:
        status = SuggestionEligibilityStatus.FAILED
        block_reasons.append(SuggestionEligibilityBlockReason.DATA_QUALITY_FAILED)

    return SuggestionEligibilityCheck(
        suggestion_eligibility_check_id="eligibility_check_result",
        policy_id=policy.suggestion_eligibility_policy_id,
        instrument_id=instrument_id,
        data_quality_gate_id=data_quality_gate.data_quality_gate_id,
        status=status,
        block_reasons=block_reasons,
        warning_reasons=warning_reasons,
        source_reference_ids=source_reference_ids,
        audit_event_ids=audit_event_ids,
        checked_at=checked_at,
        explanation_nl="Resultaat van de suggestie-eligibility controle.",
    )
