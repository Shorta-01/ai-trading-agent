"""Task 135b: IBKR reconciliation read + manual-review write API.

Six routes that surface the worker-side reconciler state to the
frontend admin page:

* ``GET /reconciliation/status?account_id=`` — overall status: latest
  run summary + drafts healed in last 24h + pending manual-review count.
* ``GET /reconciliation/runs?account_id=&limit=`` — recent reconciler
  tick history (newest-first).
* ``GET /reconciliation/audit?account_id=&limit=`` — recent
  reconciliation_audit rows (newest-first).
* ``GET /reconciliation/manual-review?account_id=`` — pending queue
  rows for human review.
* ``POST /reconciliation/manual-review/{id}/acknowledge`` — mark a
  pending queue row as ``acknowledged`` (idempotent on replay).
* ``GET /reconciliation/unmatched-executions?account_id=`` — unresolved
  TWS-side fills that have no matching draft.

All routes:

* Pydantic v2 typed responses.
* Decimal-as-string on the wire.
* HTTP 503 + locked Dutch body on storage unavailable.
* mypy --strict clean.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from ai_trading_agent_storage import (
    ManualReviewQueueEntry,
    ReconciliationAuditEntry,
    ReconciliationRunAuditEntry,
    SqlAlchemyManualReviewQueueRepository,
    SqlAlchemyReconciliationAuditRepository,
    SqlAlchemyReconciliationRunAuditRepository,
    SqlAlchemyUnmatchedExecutionAuditRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    UnmatchedExecutionAuditEntry,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from portfolio_outlook_api.config import settings

router = APIRouter()

STORAGE_UNAVAILABLE_DETAIL = "Opslag is niet beschikbaar."
NO_ACCOUNT_DETAIL = "Geen IBKR-rekening geconfigureerd."
QUEUE_ROW_NOT_FOUND_DETAIL = "Beoordelingsrij niet gevonden."


# ----------------------------------------------------------------------
# Response models.
# ----------------------------------------------------------------------


class ReconciliationRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None
    reconciliation_run_id: str
    started_at: str
    completed_at: str | None
    account_id: str
    pass_a_orphaned_count: int
    pass_b_stale_count: int
    pass_c_timeout_count: int
    divergences_found: int
    mode_detected: Literal[
        "completed",
        "skipped_locked",
        "skipped_disconnected",
        "error",
    ]
    error_details_json: dict[str, object] | None


class ReconciliationRunListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str
    runs: list[ReconciliationRunResponse]


class ReconciliationStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str
    latest_run: ReconciliationRunResponse | None
    drafts_healed_last_24h: int
    pending_manual_review_count: int
    unresolved_unmatched_count: int


class ReconciliationAuditResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None
    reconciliation_run_id: str
    action_draft_id: str | None
    event_at: str
    pass_name: Literal[
        "orphaned_execution",
        "stale_in_flight",
        "timeout_recovery",
    ]
    divergence_type: str
    before_status: str | None
    after_status: str | None
    ibkr_evidence_json: dict[str, object]
    notes_dutch: str | None


class ReconciliationAuditListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str
    rows: list[ReconciliationAuditResponse]


class ManualReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None
    flagged_at: str
    action_draft_id: str
    reason: Literal[
        "timeout_24h_no_data",
        "terminal_state_divergence",
        "unmatched_execution_no_draft",
    ]
    details_dutch: str
    resolution_status: Literal["pending", "resolved", "acknowledged"]
    resolved_at: str | None
    resolution_note: str | None


class ManualReviewListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str
    rows: list[ManualReviewResponse]


class UnmatchedExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None
    event_at: str
    ibkr_perm_id: int
    ibkr_exec_id: str
    account_id: str
    conid: str
    side: Literal["BUY", "SELL"]
    fill_price_local: str
    fill_quantity: str
    fill_time: str
    raw_execution_json: dict[str, object]
    resolution_status: Literal["unresolved", "manually_matched", "ignored"]


class UnmatchedExecutionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_account_id: str
    rows: list[UnmatchedExecutionResponse]


# ----------------------------------------------------------------------
# Serialization helpers.
# ----------------------------------------------------------------------


def _serialize_run(
    entry: ReconciliationRunAuditEntry,
) -> dict[str, object]:
    return {
        "id": entry.id,
        "reconciliation_run_id": entry.reconciliation_run_id,
        "started_at": entry.started_at.isoformat(),
        "completed_at": (
            entry.completed_at.isoformat()
            if entry.completed_at is not None
            else None
        ),
        "account_id": entry.account_id,
        "pass_a_orphaned_count": entry.pass_a_orphaned_count,
        "pass_b_stale_count": entry.pass_b_stale_count,
        "pass_c_timeout_count": entry.pass_c_timeout_count,
        "divergences_found": entry.divergences_found,
        "mode_detected": entry.mode_detected,
        "error_details_json": (
            dict(entry.error_details_json)
            if entry.error_details_json is not None
            else None
        ),
    }


def _serialize_audit(
    entry: ReconciliationAuditEntry,
) -> dict[str, object]:
    return {
        "id": entry.id,
        "reconciliation_run_id": entry.reconciliation_run_id,
        "action_draft_id": entry.action_draft_id,
        "event_at": entry.event_at.isoformat(),
        "pass_name": entry.pass_name,
        "divergence_type": entry.divergence_type,
        "before_status": entry.before_status,
        "after_status": entry.after_status,
        "ibkr_evidence_json": dict(entry.ibkr_evidence_json),
        "notes_dutch": entry.notes_dutch,
    }


def _serialize_manual_review(
    entry: ManualReviewQueueEntry,
) -> dict[str, object]:
    return {
        "id": entry.id,
        "flagged_at": entry.flagged_at.isoformat(),
        "action_draft_id": entry.action_draft_id,
        "reason": entry.reason,
        "details_dutch": entry.details_dutch,
        "resolution_status": entry.resolution_status,
        "resolved_at": (
            entry.resolved_at.isoformat()
            if entry.resolved_at is not None
            else None
        ),
        "resolution_note": entry.resolution_note,
    }


def _serialize_unmatched(
    entry: UnmatchedExecutionAuditEntry,
) -> dict[str, object]:
    return {
        "id": entry.id,
        "event_at": entry.event_at.isoformat(),
        "ibkr_perm_id": entry.ibkr_perm_id,
        "ibkr_exec_id": entry.ibkr_exec_id,
        "account_id": entry.account_id,
        "conid": entry.conid,
        "side": entry.side,
        "fill_price_local": str(entry.fill_price_local),
        "fill_quantity": str(entry.fill_quantity),
        "fill_time": entry.fill_time.isoformat(),
        "raw_execution_json": dict(entry.raw_execution_json),
        "resolution_status": entry.resolution_status,
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
        raise HTTPException(status_code=404, detail=NO_ACCOUNT_DETAIL)
    return effective


# ----------------------------------------------------------------------
# Routes.
# ----------------------------------------------------------------------


@router.get(
    "/reconciliation/status",
    response_model=ReconciliationStatusResponse,
)
def get_reconciliation_status(
    account_id: str | None = None,
) -> dict[str, object]:
    """Overall reconciler health for the dashboard widget."""

    effective_account = _resolve_account_id(account_id)
    provider = _storage_provider()
    payload: dict[str, object] = {
        "ibkr_account_id": effective_account,
        "latest_run": None,
        "drafts_healed_last_24h": 0,
        "pending_manual_review_count": 0,
        "unresolved_unmatched_count": 0,
    }
    try:
        with provider.checked_connection(require_writable=False) as checked:
            run_repo = SqlAlchemyReconciliationRunAuditRepository(
                checked.connection, checked.readiness
            )
            audit_repo = SqlAlchemyReconciliationAuditRepository(
                checked.connection, checked.readiness
            )
            queue_repo = SqlAlchemyManualReviewQueueRepository(
                checked.connection, checked.readiness
            )
            unmatched_repo = SqlAlchemyUnmatchedExecutionAuditRepository(
                checked.connection, checked.readiness
            )
            latest = run_repo.get_latest_for_account(effective_account)
            cutoff = datetime.now(UTC) - timedelta(hours=24)
            healed = audit_repo.count_drafts_healed_since(
                account_id=effective_account, since=cutoff
            )
            pending = queue_repo.count_pending_for_account(effective_account)
            unresolved = len(
                unmatched_repo.list_unresolved_for_account(effective_account)
            )
            payload = {
                "ibkr_account_id": effective_account,
                "latest_run": (
                    None if latest is None else _serialize_run(latest)
                ),
                "drafts_healed_last_24h": healed,
                "pending_manual_review_count": pending,
                "unresolved_unmatched_count": unresolved,
            }
    except StorageConnectionError:
        _raise_storage_unavailable()
    return payload


@router.get(
    "/reconciliation/runs",
    response_model=ReconciliationRunListResponse,
)
def list_reconciliation_runs(
    account_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    """Recent reconciler tick history (newest-first)."""

    effective_account = _resolve_account_id(account_id)
    provider = _storage_provider()
    runs_payload: list[dict[str, object]] = []
    try:
        with provider.checked_connection(require_writable=False) as checked:
            run_repo = SqlAlchemyReconciliationRunAuditRepository(
                checked.connection, checked.readiness
            )
            rows = run_repo.list_for_account(
                account_id=effective_account, limit=limit
            )
            runs_payload = [_serialize_run(r) for r in rows]
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "ibkr_account_id": effective_account,
        "runs": runs_payload,
    }


@router.get(
    "/reconciliation/audit",
    response_model=ReconciliationAuditListResponse,
)
def list_reconciliation_audit(
    account_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    """Recent reconciliation_audit rows (newest-first)."""

    effective_account = _resolve_account_id(account_id)
    provider = _storage_provider()
    rows_payload: list[dict[str, object]] = []
    try:
        with provider.checked_connection(require_writable=False) as checked:
            audit_repo = SqlAlchemyReconciliationAuditRepository(
                checked.connection, checked.readiness
            )
            rows = audit_repo.list_for_account(
                account_id=effective_account, limit=limit
            )
            rows_payload = [_serialize_audit(r) for r in rows]
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "ibkr_account_id": effective_account,
        "rows": rows_payload,
    }


@router.get(
    "/reconciliation/manual-review",
    response_model=ManualReviewListResponse,
)
def list_pending_manual_review(
    account_id: str | None = None,
) -> dict[str, object]:
    """Pending manual-review queue rows for human triage."""

    effective_account = _resolve_account_id(account_id)
    provider = _storage_provider()
    rows_payload: list[dict[str, object]] = []
    try:
        with provider.checked_connection(require_writable=False) as checked:
            queue_repo = SqlAlchemyManualReviewQueueRepository(
                checked.connection, checked.readiness
            )
            rows = queue_repo.list_pending_for_account(effective_account)
            rows_payload = [_serialize_manual_review(r) for r in rows]
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "ibkr_account_id": effective_account,
        "rows": rows_payload,
    }


@router.post(
    "/reconciliation/manual-review/{queue_id}/acknowledge",
    response_model=ManualReviewResponse,
)
def acknowledge_manual_review(
    queue_id: int,
    note: str | None = None,
) -> dict[str, object]:
    """Flip a pending manual-review row to ``acknowledged``.

    Idempotent: re-acknowledging an already-acknowledged row returns
    the existing row unchanged. The underlying Action Draft is **not**
    touched — the user reviewed the row and is closing the queue
    item; the draft's terminal status remains whatever the reconciler
    set it to.
    """

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            queue_repo = SqlAlchemyManualReviewQueueRepository(
                checked.connection, checked.readiness
            )
            existing = queue_repo.get_by_id(queue_id)
            if existing is None:
                raise HTTPException(
                    status_code=404, detail=QUEUE_ROW_NOT_FOUND_DETAIL
                )
            updated = queue_repo.acknowledge(
                queue_id=queue_id,
                resolved_at=datetime.now(UTC),
                note=note,
            )
            checked.connection.commit()
    except StorageConnectionError:
        _raise_storage_unavailable()
    return _serialize_manual_review(updated)


@router.get(
    "/reconciliation/unmatched-executions",
    response_model=UnmatchedExecutionListResponse,
)
def list_unmatched_executions(
    account_id: str | None = None,
) -> dict[str, object]:
    """Unresolved TWS-side fills with no matching local draft."""

    effective_account = _resolve_account_id(account_id)
    provider = _storage_provider()
    rows_payload: list[dict[str, object]] = []
    try:
        with provider.checked_connection(require_writable=False) as checked:
            unmatched_repo = SqlAlchemyUnmatchedExecutionAuditRepository(
                checked.connection, checked.readiness
            )
            rows = unmatched_repo.list_unresolved_for_account(
                effective_account
            )
            rows_payload = [_serialize_unmatched(r) for r in rows]
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "ibkr_account_id": effective_account,
        "rows": rows_payload,
    }


_ = Decimal  # silence unused-import warning on Decimal-only types in models
