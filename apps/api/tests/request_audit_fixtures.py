from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ai_trading_agent_storage import (
    FreshnessAuditRecord,
    ProviderSourceRecord,
    RequestLogRecord,
)


class _Read:
    def __init__(self, record: object | None) -> None:
        self.found = record is not None
        self.record = record


class _List:
    def __init__(self, records: list[object]) -> None:
        self.records = tuple(records)


def _base_timestamp(value: datetime | None) -> datetime:
    return value if value is not None else datetime(2026, 1, 1, tzinfo=UTC)


def make_request_log_record(
    *,
    request_log_id: str = "req-1",
    provider_code: str = "ibkr",
    request_status: str = "blocked",
    data_domain: str = "market_data",
    created_at: datetime | None = None,
    **overrides: Any,
) -> RequestLogRecord:
    values = {
        "request_log_id": request_log_id,
        "correlation_id": "corr-1",
        "request_family": "audit",
        "request_purpose": "status",
        "created_at": _base_timestamp(created_at),
        "completed_at": None,
        "provider_code": provider_code,
        "provider_account_mode": "paper",
        "provider_environment": "sandbox",
        "source_type": "broker",
        "data_domain": data_domain,
        "request_kind": "list",
        "request_target": "/audit",
        "request_status": request_status,
        "initiated_by": "api",
        "pacing_weight": 0,
        "provider_request_budget_remaining": 0,
        "retry_count": 0,
        "received_record_count": 0,
        "stored_record_count": 0,
        "rejected_record_count": 0,
        "safe_for_analysis": False,
        "safe_for_suggestions": False,
        "safe_for_action_drafts": False,
        "explanation_nl": "Read-only test record.",
    }
    values.update(overrides)
    return RequestLogRecord(**values)


def make_provider_source_record(
    *,
    provider_source_id: str = "src-1",
    created_at: datetime | None = None,
    **overrides: Any,
) -> ProviderSourceRecord:
    ts = _base_timestamp(created_at)
    values = {
        "provider_source_id": provider_source_id,
        "provider_code": "ibkr",
        "provider_kind": "broker",
        "data_domain": "market_data",
        "source_type": "feed",
        "provider_environment": "sandbox",
        "provider_account_mode": "paper",
        "source_effective_from": None,
        "source_effective_to": None,
        "created_at": ts,
        "updated_at": ts,
        "explanation_nl": "Read-only bronmetadata.",
    }
    values.update(overrides)
    return ProviderSourceRecord(**values)


def make_freshness_audit_record(
    *,
    freshness_audit_id: str = "fr-1",
    freshness_status: str = "blocked",
    evaluated_at: datetime | None = None,
    **overrides: Any,
) -> FreshnessAuditRecord:
    ts = _base_timestamp(evaluated_at)
    values = {
        "freshness_audit_id": freshness_audit_id,
        "evaluated_at": ts,
        "data_domain": "market_data",
        "freshness_policy_code": "snapshot",
        "freshness_status": freshness_status,
        "snapshot_as_of": ts,
        "stale_after": ts,
        "expires_at": None,
        "age_seconds": 1,
        "freshness_window_seconds": 300,
        "safe_for_analysis": False,
        "safe_for_suggestions": False,
        "safe_for_action_drafts": False,
        "explanation_nl": "Read-only freshnessstatus.",
    }
    values.update(overrides)
    return FreshnessAuditRecord(**values)


def make_request_audit_records_bundle() -> tuple[
    list[RequestLogRecord],
    list[ProviderSourceRecord],
    list[FreshnessAuditRecord],
]:
    return (
        [make_request_log_record(request_log_id="req-1", request_status="blocked")],
        [make_provider_source_record(provider_source_id="src-1")],
        [
            make_freshness_audit_record(
                freshness_audit_id="fr-1",
                freshness_status="blocked",
            )
        ],
    )


def make_request_audit_repo(
    *,
    request_logs: list[RequestLogRecord] | None = None,
    provider_sources: list[ProviderSourceRecord] | None = None,
    freshness_audits: list[FreshnessAuditRecord] | None = None,
):
    req = request_logs or []
    src = provider_sources or []
    fr = freshness_audits or []

    class Repo:
        def list_request_logs(self):
            return _List(req)

        def list_provider_sources(self):
            return _List(src)

        def list_freshness_audits(self):
            return _List(fr)

        def get_request_log(self, request_log_id: str):
            record = next(
                (
                    record
                    for record in req
                    if record.request_log_id == request_log_id
                ),
                None,
            )
            return _Read(record)

        def get_provider_source(self, provider_source_id: str):
            record = next(
                (
                    record
                    for record in src
                    if record.provider_source_id == provider_source_id
                ),
                None,
            )
            return _Read(record)

        def get_freshness_audit(self, freshness_audit_id: str):
            record = next(
                (
                    record
                    for record in fr
                    if record.freshness_audit_id == freshness_audit_id
                ),
                None,
            )
            return _Read(record)

    return Repo()
