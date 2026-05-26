"""Task 134c: IBKR submission read API.

Five read-only routes that surface the Stage 3 IBKR submission state
to the frontend:

* ``GET /ibkr-submission/audit?account_id=&limit=`` — submission audit
  rows for the account (newest-first), powering the diagnostics view.
* ``GET /ibkr-submission/lifecycle/{action_draft_id}`` — full callback
  audit chain for one draft, powering the SubmissionLifecycleDrawer.
* ``GET /ibkr-submission/active?account_id=`` — drafts in any in-flight
  status (submitted / accepted / working / partially_filled /
  pending_cancellation), powering the "Actief bij IBKR" tab.
* ``GET /ibkr-submission/historiek?account_id=&limit=`` — drafts in
  any terminal status, powering the "Historiek" tab.
* ``GET /ibkr-executions?account_id=&conid=`` — per-asset execution
  history (Decimal-as-string), powering the execution row view.

All routes:

* Pydantic v2 typed responses.
* Decimal-as-string on the wire.
* HTTP 503 + locked Dutch body on storage unavailable.
* Decimal-as-string serialisation; no float.
* mypy --strict clean.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    IbkrExecutionEntry,
    IbkrSubmissionAuditEntry,
    IbkrSubmissionLifecycleEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrExecutionsRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
    SqlAlchemyIbkrSubmissionLifecycleRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from portfolio_outlook_api.action_draft import (
    ActionDraftResponse,
    _serialize_draft,
)
from portfolio_outlook_api.config import settings

router = APIRouter()

STORAGE_UNAVAILABLE_DETAIL = "Opslag is niet beschikbaar."


# ----------------------------------------------------------------------
# Response models.
# ----------------------------------------------------------------------


class IbkrSubmissionAuditResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None
    action_draft_id: str
    submitted_at: str
    sent_to_account_id: str
    sent_account_mode: Literal["paper", "live"]
    ibkr_perm_id: int | None
    ibkr_order_id: int | None
    contract_json: dict[str, object]
    order_json: dict[str, object]
    gateway_session_id: str
    result: Literal["placed", "rejected_at_send", "connection_lost"]
    error_class: str | None
    error_message_dutch: str | None


class IbkrSubmissionAuditListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str
    rows: list[IbkrSubmissionAuditResponse]


class IbkrSubmissionLifecycleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None
    action_draft_id: str
    event_at: str
    ibkr_perm_id: int
    event_type: Literal[
        "status_change",
        "fill",
        "commission_report",
        "cancellation_request",
    ]
    from_status: str | None
    to_status: str | None
    ibkr_raw_status: str | None
    fill_price_local: str | None
    fill_quantity: str | None
    commission: str | None
    commission_currency: str | None
    raw_callback_json: dict[str, object]


class IbkrSubmissionLifecycleListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_draft_id: str
    events: list[IbkrSubmissionLifecycleResponse]


class ActiveDraftListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str
    drafts: list[ActionDraftResponse]


class HistoriekDraftListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str
    drafts: list[ActionDraftResponse]


class IbkrExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None
    ibkr_exec_id: str
    ibkr_perm_id: int
    action_draft_id: str
    account_id: str
    conid: str
    side: Literal["BUY", "SELL"]
    fill_price_local: str
    fill_quantity: str
    fill_time: str
    commission: str
    commission_currency: str
    exchange: str


class IbkrExecutionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    conid: str
    executions: list[IbkrExecutionResponse]


# ----------------------------------------------------------------------
# Serialization helpers.
# ----------------------------------------------------------------------


def _serialize_audit(
    entry: IbkrSubmissionAuditEntry,
) -> dict[str, object]:
    return {
        "id": entry.id,
        "action_draft_id": entry.action_draft_id,
        "submitted_at": entry.submitted_at.isoformat(),
        "sent_to_account_id": entry.sent_to_account_id,
        "sent_account_mode": entry.sent_account_mode,
        "ibkr_perm_id": entry.ibkr_perm_id,
        "ibkr_order_id": entry.ibkr_order_id,
        "contract_json": dict(entry.contract_json),
        "order_json": dict(entry.order_json),
        "gateway_session_id": entry.gateway_session_id,
        "result": entry.result,
        "error_class": entry.error_class,
        "error_message_dutch": entry.error_message_dutch,
    }


def _serialize_lifecycle(
    entry: IbkrSubmissionLifecycleEntry,
) -> dict[str, object]:
    def _dec(value: Decimal | None) -> str | None:
        return None if value is None else str(value)

    return {
        "id": entry.id,
        "action_draft_id": entry.action_draft_id,
        "event_at": entry.event_at.isoformat(),
        "ibkr_perm_id": entry.ibkr_perm_id,
        "event_type": entry.event_type,
        "from_status": entry.from_status,
        "to_status": entry.to_status,
        "ibkr_raw_status": entry.ibkr_raw_status,
        "fill_price_local": _dec(entry.fill_price_local),
        "fill_quantity": _dec(entry.fill_quantity),
        "commission": _dec(entry.commission),
        "commission_currency": entry.commission_currency,
        "raw_callback_json": dict(entry.raw_callback_json),
    }


def _serialize_execution(entry: IbkrExecutionEntry) -> dict[str, object]:
    return {
        "id": entry.id,
        "ibkr_exec_id": entry.ibkr_exec_id,
        "ibkr_perm_id": entry.ibkr_perm_id,
        "action_draft_id": entry.action_draft_id,
        "account_id": entry.account_id,
        "conid": entry.conid,
        "side": entry.side,
        "fill_price_local": str(entry.fill_price_local),
        "fill_quantity": str(entry.fill_quantity),
        "fill_time": entry.fill_time.isoformat(),
        "commission": str(entry.commission),
        "commission_currency": entry.commission_currency,
        "exchange": entry.exchange,
    }


def _raise_storage_unavailable() -> None:
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    assert storage.database_url is not None
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


def _configured_account_id() -> str | None:
    hint = getattr(settings, "ibkr_account_id_hint", None)
    if hint is None:
        return None
    text = str(hint).strip()
    return text or None


def _resolve_account_id(account_id: str | None) -> str:
    effective = account_id or _configured_account_id()
    if effective is None:
        raise HTTPException(
            status_code=404,
            detail="Geen IBKR-rekening geconfigureerd.",
        )
    return effective


# ----------------------------------------------------------------------
# Routes.
# ----------------------------------------------------------------------


@router.get(
    "/ibkr-submission/audit",
    response_model=IbkrSubmissionAuditListResponse,
)
def list_submission_audit(
    account_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    """Newest-first audit rows for the account."""

    effective_account = _resolve_account_id(account_id)
    provider = _storage_provider()
    payload: list[dict[str, object]] = []
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyIbkrSubmissionAuditRepository(
                checked.connection, checked.readiness
            )
            rows = repo.list_for_account(
                ibkr_account_id=effective_account, limit=limit
            )
            payload = [_serialize_audit(r) for r in rows]
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "ibkr_account_id": effective_account,
        "rows": payload,
    }


@router.get(
    "/ibkr-submission/lifecycle/{action_draft_id}",
    response_model=IbkrSubmissionLifecycleListResponse,
)
def list_submission_lifecycle(
    action_draft_id: str,
) -> dict[str, object]:
    """Full lifecycle event log for one draft (chronological)."""

    provider = _storage_provider()
    payload: list[dict[str, object]] = []
    try:
        with provider.checked_connection(require_writable=False) as checked:
            lifecycle_repo = SqlAlchemyIbkrSubmissionLifecycleRepository(
                checked.connection, checked.readiness
            )
            events = lifecycle_repo.list_for_draft(action_draft_id)
            payload = [_serialize_lifecycle(e) for e in events]
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "action_draft_id": action_draft_id,
        "events": payload,
    }


@router.get(
    "/ibkr-submission/active",
    response_model=ActiveDraftListResponse,
)
def list_active_submissions(
    account_id: str | None = None,
) -> dict[str, object]:
    """Drafts in any in-flight status (Te keuren tab's sibling)."""

    effective_account = _resolve_account_id(account_id)
    provider = _storage_provider()
    drafts_payload: list[dict[str, object]] = []
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyActionDraftRepository(
                checked.connection, checked.readiness
            )
            drafts = repo.list_active_for_account(
                ibkr_account_id=effective_account
            )
            drafts_payload = [_serialize_draft(d) for d in drafts]
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "ibkr_account_id": effective_account,
        "drafts": drafts_payload,
    }


@router.get(
    "/ibkr-submission/historiek",
    response_model=HistoriekDraftListResponse,
)
def list_terminal_submissions(
    account_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    """Drafts in any terminal status (Historiek tab)."""

    effective_account = _resolve_account_id(account_id)
    provider = _storage_provider()
    drafts_payload: list[dict[str, object]] = []
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyActionDraftRepository(
                checked.connection, checked.readiness
            )
            drafts = repo.list_terminal_for_account(
                ibkr_account_id=effective_account, limit=limit
            )
            drafts_payload = [_serialize_draft(d) for d in drafts]
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "ibkr_account_id": effective_account,
        "drafts": drafts_payload,
    }


@router.get(
    "/ibkr-executions",
    response_model=IbkrExecutionListResponse,
)
def list_executions(
    account_id: str | None = None,
    conid: str = Query(..., min_length=1),
) -> dict[str, object]:
    """Per-asset execution history."""

    effective_account = _resolve_account_id(account_id)
    provider = _storage_provider()
    executions_payload: list[dict[str, object]] = []
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyIbkrExecutionsRepository(
                checked.connection, checked.readiness
            )
            rows = repo.list_for_account_conid(
                account_id=effective_account, conid=conid
            )
            executions_payload = [_serialize_execution(r) for r in rows]
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "account_id": effective_account,
        "conid": conid,
        "executions": executions_payload,
    }


__all__ = [
    "ActiveDraftListResponse",
    "HistoriekDraftListResponse",
    "IbkrExecutionListResponse",
    "IbkrExecutionResponse",
    "IbkrSubmissionAuditListResponse",
    "IbkrSubmissionAuditResponse",
    "IbkrSubmissionLifecycleListResponse",
    "IbkrSubmissionLifecycleResponse",
    "router",
]


# Silence unused imports kept for downstream callers.
_ = (datetime, ActionDraftEntry)
