"""Central error-log API.

Surfaces ``system_events`` of error severity as a manageable error log for the
dashboard: list (with FULL technical detail so it can be copied into Claude
Code for a fix), report a frontend error, resolve, and delete. Reuses the
system-event storage + recorder + resolve mutation; adds the error-focused
read shape and the delete action.
"""

from __future__ import annotations

import logging
import traceback
from datetime import UTC, datetime
from uuid import uuid4

from ai_trading_agent_storage import (
    CreateSystemEventRequest,
    SqlAlchemySystemEventRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Only these severities count as "errors" for the badge + panel; warning/info
# system events stay in the existing system-messages view.
_ERROR_SEVERITIES = frozenset({"error", "critical"})


class ErrorLogItem(BaseModel):
    system_event_id: str
    created_at: str
    severity: str
    category: str
    source_service: str
    source_component: str
    event_code: str
    title_nl: str
    message_nl: str
    technical_summary: str | None
    stack_trace_redacted: str | None
    redacted_details_json: dict[str, str] | None
    status: str


class ErrorLogResponse(BaseModel):
    open_count: int
    errors: list[ErrorLogItem]


class ReportFrontendErrorRequest(BaseModel):
    message: str
    component: str | None = None
    stack: str | None = None
    context: dict[str, str] | None = None


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise HTTPException(status_code=503, detail="Opslag is niet beschikbaar.")
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


@router.get("/errors", response_model=ErrorLogResponse)
def list_errors() -> ErrorLogResponse:
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemySystemEventRepository(
                checked.connection, checked.readiness
            )
            rows = repo.list_open_events().records
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    errors = [
        ErrorLogItem(
            system_event_id=r.system_event_id,
            created_at=r.created_at.isoformat(),
            severity=r.severity,
            category=r.category,
            source_service=r.source_service,
            source_component=r.source_component,
            event_code=r.event_code,
            title_nl=r.title_nl,
            message_nl=r.message_nl,
            technical_summary=r.technical_summary,
            stack_trace_redacted=r.stack_trace_redacted,
            redacted_details_json=r.redacted_details_json,
            status=r.status,
        )
        for r in rows
        if r.severity in _ERROR_SEVERITIES
    ]
    return ErrorLogResponse(open_count=len(errors), errors=errors)


@router.post("/errors/report", status_code=201)
def report_frontend_error(payload: ReportFrontendErrorRequest) -> dict[str, object]:
    system_event_id = f"system-event-{uuid4()}"
    request = CreateSystemEventRequest(
        system_event_id=system_event_id,
        created_at=datetime.now(UTC),
        severity="error",
        category="frontend_error",
        source_service="web",
        source_component=payload.component or "dashboard",
        event_code="frontend_error",
        title_nl="Fout in dashboard",
        message_nl=(payload.message[:500] or "Onbekende frontend-fout"),
        help_nl="Kopieer de details en plak ze in Claude Code voor een fix.",
        technical_summary=payload.message[:2000],
        redacted_details_json=payload.context,
        stack_trace_redacted=payload.stack,
        related_entity_type=None,
        related_entity_id=None,
        blocks_suggestions=False,
        blocks_writes=False,
        blocks_ai_explanation=False,
        status="open",
        explanation_nl="Frontend-fout gemeld via dashboard.",
    )
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemySystemEventRepository(
                checked.connection, checked.readiness
            )
            repo.create_event(request)
            checked.connection.commit()
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return {"system_event_id": system_event_id, "message_nl": "Fout gemeld."}


@router.post("/errors/{system_event_id}/resolve")
def resolve_error(system_event_id: str) -> dict[str, object]:
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemySystemEventRepository(
                checked.connection, checked.readiness
            )
            result = repo.mark_resolved(system_event_id)
            if result.accepted:
                checked.connection.commit()
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    if not result.accepted:
        raise HTTPException(status_code=404, detail=result.explanation_nl)
    return {
        "system_event_id": system_event_id,
        "message_nl": result.explanation_nl,
    }


@router.delete("/errors/{system_event_id}")
def delete_error(system_event_id: str) -> dict[str, object]:
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemySystemEventRepository(
                checked.connection, checked.readiness
            )
            result = repo.delete_event(system_event_id)
            if result.accepted:
                checked.connection.commit()
    except StorageConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    if not result.accepted:
        raise HTTPException(status_code=404, detail=result.explanation_nl)
    return {
        "system_event_id": system_event_id,
        "message_nl": result.explanation_nl,
    }


def record_error_event(
    *,
    source_service: str,
    source_component: str,
    event_code: str,
    message: str,
    technical_summary: str | None = None,
    stack_trace: str | None = None,
    context: dict[str, str] | None = None,
) -> None:
    """Best-effort: persist an error as an open system_event. Never raises.

    Used by the auto-capture exception handler so an unhandled error is logged
    centrally without masking the original failure."""

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return
    request = CreateSystemEventRequest(
        system_event_id=f"system-event-{uuid4()}",
        created_at=datetime.now(UTC),
        severity="error",
        category="runtime_error",
        source_service=source_service,
        source_component=source_component[:200],
        event_code=event_code,
        title_nl="Onverwachte serverfout",
        message_nl=(message[:500] or "Onbekende fout"),
        help_nl="Kopieer de details en plak ze in Claude Code voor een fix.",
        technical_summary=(technical_summary[:2000] if technical_summary else None),
        redacted_details_json=context,
        stack_trace_redacted=(stack_trace[-4000:] if stack_trace else None),
        related_entity_type=None,
        related_entity_id=None,
        blocks_suggestions=False,
        blocks_writes=False,
        blocks_ai_explanation=False,
        status="open",
        explanation_nl="Automatisch vastgelegd door de centrale foutlogging.",
    )
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemySystemEventRepository(
                checked.connection, checked.readiness
            )
            repo.create_event(request)
            checked.connection.commit()
    except Exception:  # noqa: BLE001 — recording must never raise
        logger.exception("Kon onverwachte fout niet vastleggen in de foutlog.")


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Auto-capture: record any unhandled API exception, then return 500.

    HTTPException + validation errors are handled by FastAPI's own handlers and
    never reach here — only genuine 500s do."""

    path = getattr(getattr(request, "url", None), "path", "unknown")
    record_error_event(
        source_service="api",
        source_component=str(path),
        event_code="unhandled_exception",
        message=f"{type(exc).__name__}: {exc}",
        technical_summary=f"{type(exc).__name__}: {exc}",
        stack_trace="".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ),
    )
    return JSONResponse(status_code=500, content={"detail": "Interne serverfout."})
