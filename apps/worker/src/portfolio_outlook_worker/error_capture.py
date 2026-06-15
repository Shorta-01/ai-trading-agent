"""Worker-side central error capture.

Records worker failures (scheduler/sweep/reconciler job errors) into the shared
``system_events`` store so they show up in the dashboard error log alongside
API + frontend errors. Best-effort: recording never raises.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from ai_trading_agent_storage import (
    CreateSystemEventRequest,
    SqlAlchemySystemEventRepository,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_worker.config import StorageSettings

logger = logging.getLogger(__name__)


def record_worker_error(
    *,
    storage_settings: StorageSettings,
    source_component: str,
    event_code: str,
    message: str,
    technical_summary: str | None = None,
    stack_trace: str | None = None,
) -> None:
    """Persist a worker error as an open system_event. Never raises."""

    if not storage_settings.enabled or not storage_settings.database_url:
        return
    request = CreateSystemEventRequest(
        system_event_id=f"system-event-{uuid4()}",
        created_at=datetime.now(UTC),
        severity="error",
        category="runtime_error",
        source_service="worker",
        source_component=source_component[:200],
        event_code=event_code,
        title_nl="Fout in achtergrondtaak",
        message_nl=(message[:500] or "Onbekende fout"),
        help_nl="Kopieer de details en plak ze in Claude Code voor een fix.",
        technical_summary=(technical_summary[:2000] if technical_summary else None),
        redacted_details_json=None,
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
            build_database_connection_settings(storage_settings.database_url)
        )
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemySystemEventRepository(
                checked.connection, checked.readiness
            )
            repo.create_event(request)
            checked.connection.commit()
    except Exception:  # noqa: BLE001 — recording must never raise
        logger.exception("Kon worker-fout niet vastleggen in de foutlog.")


def record_worker_event(
    *,
    storage_settings: StorageSettings,
    source_component: str,
    event_code: str,
    severity: str,
    title_nl: str,
    message_nl: str,
    help_nl: str | None = None,
    category: str = "runtime_event",
    technical_summary: str | None = None,
) -> None:
    """Persist een non-error worker-event als open ``system_event``.

    Gebruikt voor zichtbare operator-meldingen die geen technische fout
    zijn (b.v. "order-sessie verbonden met LIVE account"). Severity is
    ``"warning"`` of ``"info"`` — voor harde fouten gebruik
    :func:`record_worker_error`. Recording mag NOOIT raise — wordt
    silently weggegooid als storage uit staat of niet bereikbaar is.
    """

    if not storage_settings.enabled or not storage_settings.database_url:
        return
    request = CreateSystemEventRequest(
        system_event_id=f"system-event-{uuid4()}",
        created_at=datetime.now(UTC),
        severity=severity,
        category=category,
        source_service="worker",
        source_component=source_component[:200],
        event_code=event_code,
        title_nl=title_nl[:200],
        message_nl=message_nl[:500],
        help_nl=(help_nl or "Operator-actie vereist.")[:500],
        technical_summary=(technical_summary[:2000] if technical_summary else None),
        redacted_details_json=None,
        stack_trace_redacted=None,
        related_entity_type=None,
        related_entity_id=None,
        blocks_suggestions=False,
        blocks_writes=False,
        blocks_ai_explanation=False,
        status="open",
        explanation_nl="Automatisch vastgelegd als operator-melding.",
    )
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage_settings.database_url)
        )
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemySystemEventRepository(
                checked.connection, checked.readiness
            )
            repo.create_event(request)
            checked.connection.commit()
    except Exception:  # noqa: BLE001 — recording must never raise
        logger.exception("Kon worker-event niet vastleggen.")


__all__ = ["record_worker_error", "record_worker_event"]
