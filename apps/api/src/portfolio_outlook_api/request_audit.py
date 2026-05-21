from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import TypedDict

from ai_trading_agent_storage import (
    FreshnessAuditRecord,
    ProviderSourceRecord,
    RequestLogRecord,
    SqlAlchemyRequestAuditRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

router = APIRouter(prefix="/audit", tags=["audit"])

BOUNDARY_HELP_NL = (
    "Read-only status: geen market-data runtime, geen runtime-fetch, geen analysevrijgave, "
    "geen suggesties, geen Decision Packages, geen actiedrafts en geen orders."
)


class RequestLogResponse(BaseModel):
    request_log_id: str
    correlation_id: str
    request_family: str
    request_purpose: str
    created_at: datetime
    completed_at: datetime | None
    provider_code: str
    provider_account_mode: str
    provider_environment: str
    source_type: str
    data_domain: str
    request_kind: str
    request_target: str
    request_status: str
    initiated_by: str
    pacing_weight: int | None
    provider_request_budget_remaining: int | None
    retry_count: int | None
    received_record_count: int | None
    stored_record_count: int | None
    rejected_record_count: int | None
    safe_for_analysis: bool = False
    safe_for_suggestions: bool = False
    safe_for_action_drafts: bool = False
    status_nl: str
    help_nl: str
    audit_help_nl: str
    chain_completeness_status: str
    chain_completeness_nl: str
    missing_chain_links: list[str]


class ProviderSourceResponse(BaseModel):
    provider_source_id: str
    provider_code: str
    provider_kind: str
    data_domain: str
    source_type: str
    provider_environment: str
    provider_account_mode: str
    source_effective_from: datetime | None
    source_effective_to: datetime | None
    created_at: datetime
    updated_at: datetime
    disabled_at: datetime | None = None
    disabled_reason: str | None = None
    safe_for_analysis: bool = False
    safe_for_suggestions: bool = False
    safe_for_action_drafts: bool = False
    status_nl: str
    help_nl: str
    audit_help_nl: str
    metadata_quality_status: str
    metadata_quality_nl: str
    missing_metadata_fields: list[str]


class FreshnessAuditResponse(BaseModel):
    freshness_audit_id: str
    request_log_id: str | None
    provider_source_id: str | None
    data_domain: str
    audit_scope: str
    freshness_status: str
    reason_code: str | None
    evaluated_at: datetime
    expected_max_age_seconds: int | None
    observed_age_seconds: int | None
    source_timestamp: datetime | None
    expires_at: datetime | None
    safe_for_analysis: bool = False
    safe_for_suggestions: bool = False
    safe_for_action_drafts: bool = False
    status_nl: str
    help_nl: str
    audit_help_nl: str
    chain_completeness_status: str
    chain_completeness_nl: str
    missing_chain_links: list[str]


class RequestLogListResponse(BaseModel):
    items: list[RequestLogResponse]
    total_count: int
    safe_for_analysis_count: int
    safe_for_suggestions_count: int
    safe_for_action_drafts_count: int
    blocked_for_analysis_count: int
    blocked_for_suggestions_count: int
    blocked_for_action_drafts_count: int
    request_status_counts: dict[str, int]
    provider_code_counts: dict[str, int]
    data_domain_counts: dict[str, int]
    chain_complete_count: int
    chain_partial_count: int
    chain_missing_links_count: int
    chain_metadata_only_count: int
    audit_help_nl: str
    status_nl: str
    help_nl: str


class ProviderSourceListResponse(BaseModel):
    items: list[ProviderSourceResponse]
    total_count: int
    provider_kind_counts: dict[str, int]
    provider_code_counts: dict[str, int]
    data_domain_counts: dict[str, int]
    disabled_count: int
    active_metadata_count: int
    metadata_complete_count: int
    metadata_partial_count: int
    metadata_unknown_count: int
    audit_help_nl: str
    status_nl: str
    help_nl: str


class FreshnessAuditListResponse(BaseModel):
    items: list[FreshnessAuditResponse]
    total_count: int
    safe_for_analysis_count: int
    safe_for_suggestions_count: int
    safe_for_action_drafts_count: int
    blocked_for_analysis_count: int
    blocked_for_suggestions_count: int
    blocked_for_action_drafts_count: int
    freshness_status_counts: dict[str, int]
    reason_code_counts: dict[str, int]
    provider_code_counts: dict[str, int]
    data_domain_counts: dict[str, int]
    chain_complete_count: int
    chain_partial_count: int
    chain_missing_links_count: int
    chain_metadata_only_count: int
    audit_help_nl: str
    status_nl: str
    help_nl: str


def _with_repository[T](operation: Callable[[SqlAlchemyRequestAuditRepository], T]) -> T:
    storage_settings = settings.storage
    if not storage_settings.enabled or not storage_settings.database_url:
        raise HTTPException(
            status_code=503, detail="Opslag niet beschikbaar voor read-only auditstatus."
        )

    provider = StorageConnectionProvider(
        build_database_connection_settings(storage_settings.database_url)
    )
    try:
        with provider.checked_connection(require_writable=False) as checked:
            return operation(
                SqlAlchemyRequestAuditRepository(checked.connection, checked.readiness)
            )
    except StorageConnectionError as exc:
        raise HTTPException(status_code=503, detail="Opslagverbinding niet beschikbaar.") from exc




def count_by_field[T](records: Sequence[T], get_value: Callable[[T], str | None]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = get_value(record)
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def count_safety_flags[T](records: Sequence[T], get_flag: Callable[[T], bool]) -> tuple[int, int]:
    safe_count = sum(1 for record in records if bool(get_flag(record)))
    return safe_count, len(records) - safe_count


class RequestLogSummary(TypedDict):
    total_count: int
    safe_for_analysis_count: int
    safe_for_suggestions_count: int
    safe_for_action_drafts_count: int
    blocked_for_analysis_count: int
    blocked_for_suggestions_count: int
    blocked_for_action_drafts_count: int
    request_status_counts: dict[str, int]
    provider_code_counts: dict[str, int]
    data_domain_counts: dict[str, int]
    audit_help_nl: str


def build_request_log_summary(records: Sequence[RequestLogRecord]) -> RequestLogSummary:
    safe_analysis, blocked_analysis = count_safety_flags(
        records,
        lambda r: r.safe_for_analysis,
    )
    safe_suggestions, blocked_suggestions = count_safety_flags(
        records,
        lambda r: r.safe_for_suggestions,
    )
    safe_actions, blocked_actions = count_safety_flags(
        records,
        lambda r: r.safe_for_action_drafts,
    )
    return {
        "total_count": len(records),
        "safe_for_analysis_count": safe_analysis,
        "safe_for_suggestions_count": safe_suggestions,
        "safe_for_action_drafts_count": safe_actions,
        "blocked_for_analysis_count": blocked_analysis,
        "blocked_for_suggestions_count": blocked_suggestions,
        "blocked_for_action_drafts_count": blocked_actions,
        "request_status_counts": count_by_field(records, lambda r: r.request_status),
        "provider_code_counts": count_by_field(records, lambda r: r.provider_code),
        "data_domain_counts": count_by_field(records, lambda r: r.data_domain),
        "audit_help_nl": BOUNDARY_HELP_NL,
    }


class ProviderSourceSummary(TypedDict):
    total_count: int
    provider_kind_counts: dict[str, int]
    provider_code_counts: dict[str, int]
    data_domain_counts: dict[str, int]
    disabled_count: int
    active_metadata_count: int
    audit_help_nl: str


def build_provider_source_summary(
    records: Sequence[ProviderSourceRecord],
) -> ProviderSourceSummary:
    disabled_count = 0
    return {
        "total_count": len(records),
        "provider_kind_counts": count_by_field(records, lambda r: r.provider_kind),
        "provider_code_counts": count_by_field(records, lambda r: r.provider_code),
        "data_domain_counts": count_by_field(records, lambda r: r.data_domain),
        "disabled_count": disabled_count,
        "active_metadata_count": len(records) - disabled_count,
        "audit_help_nl": BOUNDARY_HELP_NL,
    }


class FreshnessAuditSummary(TypedDict):
    total_count: int
    safe_for_analysis_count: int
    safe_for_suggestions_count: int
    safe_for_action_drafts_count: int
    blocked_for_analysis_count: int
    blocked_for_suggestions_count: int
    blocked_for_action_drafts_count: int
    freshness_status_counts: dict[str, int]
    reason_code_counts: dict[str, int]
    provider_code_counts: dict[str, int]
    data_domain_counts: dict[str, int]
    audit_help_nl: str


def build_freshness_audit_summary(
    records: Sequence[FreshnessAuditRecord],
) -> FreshnessAuditSummary:
    safe_analysis, blocked_analysis = count_safety_flags(
        records,
        lambda r: r.safe_for_analysis,
    )
    safe_suggestions, blocked_suggestions = count_safety_flags(
        records,
        lambda r: r.safe_for_suggestions,
    )
    safe_actions, blocked_actions = count_safety_flags(
        records,
        lambda r: r.safe_for_action_drafts,
    )
    return {
        "total_count": len(records),
        "safe_for_analysis_count": safe_analysis,
        "safe_for_suggestions_count": safe_suggestions,
        "safe_for_action_drafts_count": safe_actions,
        "blocked_for_analysis_count": blocked_analysis,
        "blocked_for_suggestions_count": blocked_suggestions,
        "blocked_for_action_drafts_count": blocked_actions,
        "freshness_status_counts": count_by_field(records, lambda r: r.freshness_status),
        "reason_code_counts": count_by_field(records, _freshness_reason_code),
        "provider_code_counts": {},
        "data_domain_counts": count_by_field(records, lambda r: r.data_domain),
        "audit_help_nl": BOUNDARY_HELP_NL,
    }


def _chain_label(status: str) -> str:
    return {
        "complete": "Auditketen volledig",
        "partial": "Auditketen gedeeltelijk",
        "missing_links": "Ontbrekende auditkoppelingen",
        "metadata_only": "Alleen metadata/status",
    }.get(status, "Alleen metadata/status")


def _request_chain_fields(record: RequestLogRecord) -> tuple[str, str, list[str]]:
    missing = ["freshness_audit"]
    status = "missing_links"
    return status, _chain_label(status), missing


def _freshness_chain_fields(record: FreshnessAuditRecord) -> tuple[str, str, list[str]]:
    missing: list[str] = []
    if not getattr(record, "request_log_id", None):
        missing.append("request_log")
    if not getattr(record, "provider_source_id", None):
        missing.append("provider_source")
    status = "complete" if not missing else "partial" if len(missing) == 1 else "missing_links"
    return status, _chain_label(status), missing


def _metadata_quality_fields(record: ProviderSourceRecord) -> tuple[str, str, list[str]]:
    required = [
        ("provider_code", record.provider_code),
        ("provider_kind", record.provider_kind),
        ("data_domain", record.data_domain),
        ("source_type", record.source_type),
        ("provider_environment", record.provider_environment),
        ("provider_account_mode", record.provider_account_mode),
    ]
    missing = [k for k,v in required if not v]
    if missing:
        return "unknown", "Alleen metadata/status", missing
    return "complete", "Auditketen volledig", []


def _count_statuses(items: list[str], key: str) -> int:
    return sum(1 for i in items if i == key)

def _request_log_response(record: RequestLogRecord) -> RequestLogResponse:
    chain_status, chain_nl, missing = _request_chain_fields(record)
    return RequestLogResponse(
        **record.__dict__,
        status_nl="Read-only requestlogrecord.",
        help_nl=BOUNDARY_HELP_NL,
        audit_help_nl=BOUNDARY_HELP_NL,
        chain_completeness_status=chain_status,
        chain_completeness_nl=chain_nl,
        missing_chain_links=missing,
    )


def _provider_source_response(record: ProviderSourceRecord) -> ProviderSourceResponse:
    quality_status, quality_nl, missing = _metadata_quality_fields(record)
    return ProviderSourceResponse(
        **record.__dict__,
        status_nl="Read-only provider/source metadata.",
        help_nl=BOUNDARY_HELP_NL,
        audit_help_nl=BOUNDARY_HELP_NL,
        metadata_quality_status=quality_status,
        metadata_quality_nl=quality_nl,
        missing_metadata_fields=missing,
    )


def _freshness_reason_code(record: FreshnessAuditRecord) -> str | None:
    if record.freshness_status.lower() == "blocked":
        return "stale"
    if record.freshness_status.lower() == "ok":
        return "fresh"
    return record.freshness_policy_code


def _freshness_response(record: FreshnessAuditRecord) -> FreshnessAuditResponse:
    reason_code = _freshness_reason_code(record)
    chain_status, chain_nl, missing = _freshness_chain_fields(record)
    return FreshnessAuditResponse(
        freshness_audit_id=record.freshness_audit_id,
        request_log_id=getattr(record, "request_log_id", None),
        provider_source_id=getattr(record, "provider_source_id", None),
        data_domain=record.data_domain,
        audit_scope=record.data_domain,
        freshness_status=record.freshness_status,
        reason_code=reason_code,
        evaluated_at=record.evaluated_at,
        expected_max_age_seconds=record.freshness_window_seconds,
        observed_age_seconds=record.age_seconds,
        source_timestamp=record.snapshot_as_of,
        expires_at=record.expires_at,
        safe_for_analysis=record.safe_for_analysis,
        safe_for_suggestions=record.safe_for_suggestions,
        safe_for_action_drafts=record.safe_for_action_drafts,
        status_nl="Read-only freshness-auditstatus.",
        help_nl=BOUNDARY_HELP_NL,
        audit_help_nl=BOUNDARY_HELP_NL,
        chain_completeness_status=chain_status,
        chain_completeness_nl=chain_nl,
        missing_chain_links=missing,
    )


@router.get("/request-logs", response_model=RequestLogListResponse)
def list_request_logs() -> RequestLogListResponse:
    records = _with_repository(lambda repo: repo.list_request_logs().records)
    record_list = list(records)
    items = [_request_log_response(r) for r in record_list]
    chain_statuses = [item.chain_completeness_status for item in items]
    return RequestLogListResponse(
        items=items,
        **build_request_log_summary(record_list),
        chain_complete_count=_count_statuses(chain_statuses, "complete"),
        chain_partial_count=_count_statuses(chain_statuses, "partial"),
        chain_missing_links_count=_count_statuses(chain_statuses, "missing_links"),
        chain_metadata_only_count=_count_statuses(chain_statuses, "metadata_only"),
        status_nl="Requestlogs read-only opgehaald."
        if record_list
        else "Nog geen requestlogs beschikbaar.",
        help_nl="Read-only lijstweergave. " + BOUNDARY_HELP_NL,
    )


@router.get("/request-logs/{request_log_id}", response_model=RequestLogResponse)
def get_request_log(request_log_id: str) -> RequestLogResponse:
    result = _with_repository(lambda repo: repo.get_request_log(request_log_id))
    if not result.found or result.record is None:
        raise HTTPException(status_code=404, detail="Requestlog niet gevonden.")
    return _request_log_response(result.record)


@router.get("/provider-sources", response_model=ProviderSourceListResponse)
def list_provider_sources() -> ProviderSourceListResponse:
    records = _with_repository(lambda repo: repo.list_provider_sources().records)
    record_list = list(records)
    items = [_provider_source_response(r) for r in record_list]
    metadata_statuses = [item.metadata_quality_status for item in items]
    return ProviderSourceListResponse(
        items=items,
        **build_provider_source_summary(record_list),
        metadata_complete_count=_count_statuses(metadata_statuses, "complete"),
        metadata_partial_count=_count_statuses(metadata_statuses, "partial"),
        metadata_unknown_count=_count_statuses(metadata_statuses, "unknown"),
        status_nl="Provider/sources read-only opgehaald."
        if record_list
        else "Nog geen provider/source records beschikbaar.",
        help_nl="Read-only lijstweergave. " + BOUNDARY_HELP_NL,
    )


@router.get("/provider-sources/{provider_source_id}", response_model=ProviderSourceResponse)
def get_provider_source(provider_source_id: str) -> ProviderSourceResponse:
    result = _with_repository(lambda repo: repo.get_provider_source(provider_source_id))
    if not result.found or result.record is None:
        raise HTTPException(status_code=404, detail="Provider/source niet gevonden.")
    return _provider_source_response(result.record)


@router.get("/freshness-audits", response_model=FreshnessAuditListResponse)
def list_freshness_audits() -> FreshnessAuditListResponse:
    records = _with_repository(lambda repo: repo.list_freshness_audits().records)
    record_list = list(records)
    items = [_freshness_response(r) for r in record_list]
    chain_statuses = [item.chain_completeness_status for item in items]
    return FreshnessAuditListResponse(
        items=items,
        **build_freshness_audit_summary(record_list),
        chain_complete_count=_count_statuses(chain_statuses, "complete"),
        chain_partial_count=_count_statuses(chain_statuses, "partial"),
        chain_missing_links_count=_count_statuses(chain_statuses, "missing_links"),
        chain_metadata_only_count=_count_statuses(chain_statuses, "metadata_only"),
        status_nl="Freshness-audits read-only opgehaald."
        if record_list
        else "Nog geen freshness-audits beschikbaar.",
        help_nl="Read-only lijstweergave. " + BOUNDARY_HELP_NL,
    )


@router.get("/freshness-audits/{freshness_audit_id}", response_model=FreshnessAuditResponse)
def get_freshness_audit(freshness_audit_id: str) -> FreshnessAuditResponse:
    result = _with_repository(lambda repo: repo.get_freshness_audit(freshness_audit_id))
    if not result.found or result.record is None:
        raise HTTPException(status_code=404, detail="Freshness-audit niet gevonden.")
    return _freshness_response(result.record)
