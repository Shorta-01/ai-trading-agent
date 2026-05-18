from datetime import datetime

from pydantic import Field, model_validator

from .enums import (
    DataDomain,
    DataGateDecision,
    DataQualityGateStatus,
    DataQualityIssueType,
    FreshnessRequirement,
    RuntimeHealthSeverity,
    SuggestionEligibilityWarningReason,
)
from .identifiers import DataFreshnessCheckId, DataQualityGateId, SourceReferenceId
from .primitives import DomainBaseModel


class DataFreshnessCheck(DomainBaseModel):
    data_freshness_check_id: DataFreshnessCheckId
    data_domain: DataDomain
    requirement: FreshnessRequirement
    observed_at: datetime | None = None
    checked_at: datetime
    status: DataQualityGateStatus
    issue_types: list[DataQualityIssueType] = Field(default_factory=list)
    explanation_nl: str

    @model_validator(mode="after")
    def validate_check(self) -> "DataFreshnessCheck":
        if not self.explanation_nl.strip():
            raise ValueError("explanation_nl is verplicht")
        if self.status is DataQualityGateStatus.PASSED and self.issue_types:
            raise ValueError("passed status mag geen issue_types bevatten")
        if (
            self.status in {DataQualityGateStatus.BLOCKED, DataQualityGateStatus.FAILED}
            and not self.issue_types
        ):
            raise ValueError("blocked of failed status vereist issue_types")
        if (
            self.requirement is FreshnessRequirement.IMMEDIATE
            and self.observed_at is None
            and self.status is DataQualityGateStatus.PASSED
        ):
            raise ValueError("immediate freshness zonder observed_at kan niet passed zijn")
        return self


class DataQualityIssue(DomainBaseModel):
    issue_type: DataQualityIssueType
    data_domain: DataDomain
    severity: RuntimeHealthSeverity
    source_reference_id: SourceReferenceId | None = None
    message_nl: str
    blocks_suggestions: bool

    @model_validator(mode="after")
    def validate_issue(self) -> "DataQualityIssue":
        if not self.message_nl.strip():
            raise ValueError("message_nl is verplicht")
        if self.severity is RuntimeHealthSeverity.CRITICAL and not self.blocks_suggestions:
            raise ValueError("critical severity moet suggestions blokkeren")
        if (
            self.issue_type is DataQualityIssueType.SOURCE_NOT_TRACEABLE
            and not self.blocks_suggestions
        ):
            raise ValueError("source_not_traceable moet suggestions blokkeren")
        return self


class DataQualityGate(DomainBaseModel):
    data_quality_gate_id: DataQualityGateId
    gate_name: str
    required_domains: list[DataDomain]
    freshness_checks: list[DataFreshnessCheck] = Field(default_factory=list)
    issues: list[DataQualityIssue] = Field(default_factory=list)
    source_reference_ids: list[SourceReferenceId] = Field(default_factory=list)
    status: DataQualityGateStatus
    decision: DataGateDecision
    checked_at: datetime
    explanation_nl: str

    @model_validator(mode="after")
    def validate_gate(self) -> "DataQualityGate":
        if not self.gate_name.strip() or not self.explanation_nl.strip():
            raise ValueError("gate_name en explanation_nl zijn verplicht")
        if not self.required_domains:
            raise ValueError("required_domains mag niet leeg zijn")
        if self.status is DataQualityGateStatus.PASSED:
            if self.issues:
                raise ValueError("passed status mag geen issues bevatten")
            if self.decision is not DataGateDecision.CONTINUE_ALLOWED:
                raise ValueError("passed status vereist continue_allowed")
        blocking_issue = any(issue.blocks_suggestions for issue in self.issues)
        if blocking_issue:
            if self.status not in {DataQualityGateStatus.BLOCKED, DataQualityGateStatus.FAILED}:
                raise ValueError("blocking issue vereist blocked of failed status")
            if self.decision not in {DataGateDecision.BLOCK_SUGGESTION, DataGateDecision.FAIL_JOB}:
                raise ValueError("blocking issue vereist block_suggestion of fail_job")
        if (
            self.decision is DataGateDecision.BLOCK_SUGGESTION
            and self.status is not DataQualityGateStatus.BLOCKED
        ):
            raise ValueError("block_suggestion vereist blocked status")
        if not self.source_reference_ids and self.decision is DataGateDecision.CONTINUE_ALLOWED:
            raise ValueError("continue_allowed vereist source traceability")
        return self


class DataQualityPolicy(DomainBaseModel):
    suggestion_critical_domains: list[DataDomain]
    warning_only_domains: list[DataDomain] = Field(default_factory=list)
    accepted_warning_reasons: list[SuggestionEligibilityWarningReason] = Field(default_factory=list)
    explanation_nl: str

    @model_validator(mode="after")
    def validate_policy(self) -> "DataQualityPolicy":
        if not self.explanation_nl.strip():
            raise ValueError("explanation_nl is verplicht")
        if not self.suggestion_critical_domains:
            raise ValueError("suggestion_critical_domains mag niet leeg zijn")
        overlap = set(self.suggestion_critical_domains).intersection(self.warning_only_domains)
        if overlap:
            raise ValueError("een data_domain mag niet in beide lijsten staan")
        return self


def build_passed_data_quality_gate(
    *,
    gate_name: str,
    required_domains: list[DataDomain],
    source_reference_ids: list[SourceReferenceId],
    checked_at: datetime,
    explanation_nl: str,
) -> DataQualityGate:
    if not source_reference_ids:
        raise ValueError("source_reference_ids is verplicht")
    return DataQualityGate(
        data_quality_gate_id="data_quality_gate_passed",
        gate_name=gate_name,
        required_domains=required_domains,
        freshness_checks=[],
        issues=[],
        source_reference_ids=source_reference_ids,
        status=DataQualityGateStatus.PASSED,
        decision=DataGateDecision.CONTINUE_ALLOWED,
        checked_at=checked_at,
        explanation_nl=explanation_nl,
    )


def build_blocked_data_quality_gate(
    *,
    gate_name: str,
    required_domains: list[DataDomain],
    issues: list[DataQualityIssue],
    checked_at: datetime,
    explanation_nl: str,
) -> DataQualityGate:
    if not issues:
        raise ValueError("issues is verplicht")
    return DataQualityGate(
        data_quality_gate_id="data_quality_gate_blocked",
        gate_name=gate_name,
        required_domains=required_domains,
        freshness_checks=[],
        issues=issues,
        source_reference_ids=[],
        status=DataQualityGateStatus.BLOCKED,
        decision=DataGateDecision.BLOCK_SUGGESTION,
        checked_at=checked_at,
        explanation_nl=explanation_nl,
    )


def gate_blocks_suggestions(gate: DataQualityGate) -> bool:
    if gate.decision in {DataGateDecision.BLOCK_SUGGESTION, DataGateDecision.FAIL_JOB}:
        return True
    return any(issue.blocks_suggestions for issue in gate.issues)


def gate_allows_suggestions(gate: DataQualityGate) -> bool:
    return gate.decision in {
        DataGateDecision.CONTINUE_ALLOWED,
        DataGateDecision.CONTINUE_WITH_WARNING,
    }
