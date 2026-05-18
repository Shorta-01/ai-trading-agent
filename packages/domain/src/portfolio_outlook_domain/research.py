from datetime import datetime

from pydantic import Field, field_validator, model_validator

from .enums import (
    AIResearchRole,
    DataQualityStatus,
    PromptInjectionRisk,
    ResearchReportStatus,
    ResearchUse,
)
from .identifiers import (
    InstrumentId,
    PortfolioId,
    ResearchReportId,
    ResearchRunId,
    SourceReferenceId,
)
from .primitives import DomainBaseModel, Percentage


class ResearchRun(DomainBaseModel):
    research_run_id: ResearchRunId
    portfolio_id: PortfolioId | None = None
    instrument_id: InstrumentId | None = None
    research_use: ResearchUse
    status: ResearchReportStatus
    started_at: datetime
    completed_at: datetime | None = None
    source_reference_ids: list[SourceReferenceId] = Field(default_factory=list)
    data_quality_status: DataQualityStatus
    prompt_template_version: str | None = None
    model_name: str | None = None

    @model_validator(mode="after")
    def validate_completed(self) -> "ResearchRun":
        if self.status == ResearchReportStatus.COMPLETED and self.completed_at is None:
            raise ValueError("completed research run requires completed_at")
        return self


class ResearchReport(DomainBaseModel):
    research_report_id: ResearchReportId
    research_run_id: ResearchRunId
    instrument_id: InstrumentId | None = None
    status: ResearchReportStatus
    ai_role: AIResearchRole
    summary_nl: str
    opportunity_summary_nl: str | None = None
    risk_summary_nl: str | None = None
    missing_data_warnings_nl: list[str] = Field(default_factory=list)
    source_reference_ids: list[SourceReferenceId] = Field(default_factory=list)
    input_hash: str | None = None
    output_hash: str | None = None
    created_at: datetime
    data_quality_status: DataQualityStatus
    prompt_injection_risk: PromptInjectionRisk

    @field_validator("summary_nl")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("summary_nl is required")
        return value

    @model_validator(mode="after")
    def validate_report(self) -> "ResearchReport":
        if (
            self.prompt_injection_risk == PromptInjectionRisk.BLOCKED
            and self.status != ResearchReportStatus.BLOCKED_BY_POLICY
        ):
            raise ValueError("blocked prompt injection requires blocked_by_policy status")
        if (
            self.data_quality_status == DataQualityStatus.FAILED
            and self.status == ResearchReportStatus.COMPLETED
        ):
            raise ValueError("failed data quality cannot be completed")
        return self


class ResearchFinding(DomainBaseModel):
    research_report_id: ResearchReportId
    label_nl: str
    detail_nl: str
    source_reference_ids: list[SourceReferenceId] = Field(default_factory=list)
    confidence: Percentage | None = None

    @field_validator("label_nl", "detail_nl")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required text field cannot be empty")
        return value
