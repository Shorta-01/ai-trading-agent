from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

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
    disabled_at: datetime | None
    disabled_reason: str | None
    safe_for_analysis: bool = False
    safe_for_suggestions: bool = False
    safe_for_action_drafts: bool = False
    status_nl: str
    help_nl: str
    audit_help_nl: str


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


class RequestLogListResponse(BaseModel):
    items: list[RequestLogResponse]
    status_nl: str
    help_nl: str


class ProviderSourceListResponse(BaseModel):
    items: list[ProviderSourceResponse]
    status_nl: str
    help_nl: str


class FreshnessAuditListResponse(BaseModel):
    items: list[FreshnessAuditResponse]
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


def _request_log_response(record: RequestLogRecord) -> RequestLogResponse:
    return RequestLogResponse(
        **record.__dict__,
        status_nl="Read-only requestlogrecord.",
        help_nl=BOUNDARY_HELP_NL,
        audit_help_nl=BOUNDARY_HELP_NL,
    )


def _provider_source_response(record: ProviderSourceRecord) -> ProviderSourceResponse:
    return ProviderSourceResponse(
        **record.__dict__,
        status_nl="Read-only provider/source metadata.",
        help_nl=BOUNDARY_HELP_NL,
        audit_help_nl=BOUNDARY_HELP_NL,
    )


def _freshness_response(record: FreshnessAuditRecord) -> FreshnessAuditResponse:
    return FreshnessAuditResponse(
        **record.__dict__,
        status_nl="Read-only freshness-auditstatus.",
        help_nl=BOUNDARY_HELP_NL,
        audit_help_nl=BOUNDARY_HELP_NL,
    )


@router.get("/request-logs", response_model=RequestLogListResponse)
def list_request_logs() -> RequestLogListResponse:
    records = _with_repository(lambda repo: repo.list_request_logs().records)
    return RequestLogListResponse(
        items=[_request_log_response(r) for r in records],
        status_nl="Requestlogs read-only opgehaald."
        if records
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
    return ProviderSourceListResponse(
        items=[_provider_source_response(r) for r in records],
        status_nl="Provider/sources read-only opgehaald."
        if records
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
    return FreshnessAuditListResponse(
        items=[_freshness_response(r) for r in records],
        status_nl="Freshness-audits read-only opgehaald."
        if records
        else "Nog geen freshness-audits beschikbaar.",
        help_nl="Read-only lijstweergave. " + BOUNDARY_HELP_NL,
    )


@router.get("/freshness-audits/{freshness_audit_id}", response_model=FreshnessAuditResponse)
def get_freshness_audit(freshness_audit_id: str) -> FreshnessAuditResponse:
    result = _with_repository(lambda repo: repo.get_freshness_audit(freshness_audit_id))
    if not result.found or result.record is None:
        raise HTTPException(status_code=404, detail="Freshness-audit niet gevonden.")
    return _freshness_response(result.record)
