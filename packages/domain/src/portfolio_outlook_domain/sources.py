from datetime import datetime

from pydantic import field_validator

from .enums import DataQualityStatus, PromptInjectionRisk, ResearchSourceType
from .identifiers import RawDataArchiveId, ResearchArchiveId, ResearchRunId, SourceReferenceId
from .primitives import DomainBaseModel


class SourceReference(DomainBaseModel):
    source_reference_id: SourceReferenceId
    source_type: ResearchSourceType
    title: str
    publisher: str | None = None
    url: str | None = None
    retrieved_at: datetime
    source_published_at: datetime | None = None
    content_hash: str | None = None
    raw_data_archive_id: RawDataArchiveId | None = None
    data_quality_status: DataQualityStatus
    prompt_injection_risk: PromptInjectionRisk

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title is required")
        return value

    @field_validator("url", "content_hash")
    @classmethod
    def validate_optional_nonempty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Optional string field cannot be empty")
        return value


class RawDataArchiveReference(DomainBaseModel):
    raw_data_archive_id: RawDataArchiveId
    source_type: ResearchSourceType
    storage_path: str
    content_hash: str
    received_at: datetime
    data_time: datetime | None = None
    schema_version: str
    data_quality_status: DataQualityStatus

    @field_validator("storage_path", "content_hash", "schema_version")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required string field cannot be empty")
        if "token=" in value.lower() or "apikey" in value.lower() or "secret" in value.lower():
            raise ValueError("storage/content fields must not contain secrets")
        return value


class ResearchArchiveReference(DomainBaseModel):
    research_archive_id: ResearchArchiveId
    research_run_id: ResearchRunId
    storage_path: str
    content_hash: str
    created_at: datetime
    schema_version: str

    @field_validator("storage_path", "content_hash", "schema_version")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required string field cannot be empty")
        return value
