"""Task 127: read-only API surface for the worker-owned scheduler.

Two routes back the dashboard ``SchedulerStatusBadge``:

* ``GET /scheduler/v127/status`` — collapses the most recent
  ``scheduled_run_audit`` row + the worker's ``scheduler_state``
  rows into one status payload.
* ``GET /scheduler/v127/runs?limit=20`` — paged audit rows.

The ``v127`` URL prefix is needed because the V1 scheduler (Slice 13)
already owns the ``/scheduler/...`` namespace via its own routes
(scheduler runs / scheduler jobs). Task 127's worker-owned APScheduler
is a separate runtime — these routes expose its state without
disturbing the V1 surface.

Both routes fail closed with HTTP 503 + locked Dutch body
``{"detail": "Opslag is niet beschikbaar."}`` when storage is
unreachable. Pydantic v2 typed end-to-end.
"""

from __future__ import annotations

from typing import Literal

from ai_trading_agent_storage import (
    ScheduledRunAuditEntry,
    SqlAlchemyScheduledRunAuditRepository,
    SqlAlchemySchedulerStateRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from portfolio_outlook_api.config import settings

router = APIRouter()


STORAGE_UNAVAILABLE_DETAIL = "Opslag is niet beschikbaar."


# ---- Pydantic v2 response models ---------------------------------


class SchedulerV127StatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    last_run_at: str | None = None
    last_run_type: str | None = None
    last_mode_detected: str | None = None
    last_outcome: str | None = None
    next_runs: list[str] = Field(default_factory=list)
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class ScheduledRunAuditRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    run_at: str
    run_type: str
    ibkr_account_id: str | None
    mode_detected: str
    duration_ms: int | None
    outcome: str
    error_details_json: str | None
    next_scheduled_at: str | None


class SchedulerV127RunsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ScheduledRunAuditRow]
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


# ---- helpers -----------------------------------------------------


def _raise_storage_unavailable() -> None:
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


def _serialize_run(row: ScheduledRunAuditEntry) -> dict[str, object]:
    return {
        "run_id": row.run_id,
        "run_at": row.run_at.isoformat(),
        "run_type": row.run_type,
        "ibkr_account_id": row.ibkr_account_id,
        "mode_detected": row.mode_detected,
        "duration_ms": row.duration_ms,
        "outcome": row.outcome,
        "error_details_json": row.error_details_json,
        "next_scheduled_at": (
            row.next_scheduled_at.isoformat() if row.next_scheduled_at else None
        ),
    }


# ---- routes ------------------------------------------------------


@router.get("/scheduler/v127/status", response_model=SchedulerV127StatusResponse)
def read_scheduler_v127_status() -> dict[str, object]:
    """Return the synthesised worker-scheduler status.

    Storage off → ``enabled=false``. Otherwise ``enabled`` is true
    iff at least one ``scheduler_state`` row exists.
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return {
            "enabled": False,
            "last_run_at": None,
            "last_run_type": None,
            "last_mode_detected": None,
            "last_outcome": None,
            "next_runs": [],
            "safe_for_action_drafts": False,
            "safe_for_orders": False,
        }

    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            audit_repo = SqlAlchemyScheduledRunAuditRepository(
                checked.connection, checked.readiness
            )
            state_repo = SqlAlchemySchedulerStateRepository(
                checked.connection, checked.readiness
            )
            recent = audit_repo.list_recent(limit=1)
            states = state_repo.list_all()
    except StorageConnectionError:
        _raise_storage_unavailable()

    last_row = recent.records[0] if recent.records else None
    enabled = bool(states.records)
    next_runs: list[str] = []
    for state in states.records:
        if state.next_pre_briefing_at is not None:
            next_runs.append(state.next_pre_briefing_at.isoformat())
        if state.next_hourly_at is not None:
            next_runs.append(state.next_hourly_at.isoformat())
    next_runs = sorted(set(next_runs))

    return {
        "enabled": enabled,
        "last_run_at": last_row.run_at.isoformat() if last_row else None,
        "last_run_type": last_row.run_type if last_row else None,
        "last_mode_detected": last_row.mode_detected if last_row else None,
        "last_outcome": last_row.outcome if last_row else None,
        "next_runs": next_runs,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


@router.get("/scheduler/v127/runs", response_model=SchedulerV127RunsResponse)
def read_scheduler_v127_runs(
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, object]:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            audit_repo = SqlAlchemyScheduledRunAuditRepository(
                checked.connection, checked.readiness
            )
            result = audit_repo.list_recent(limit=limit)
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "items": [_serialize_run(row) for row in result.records],
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }
