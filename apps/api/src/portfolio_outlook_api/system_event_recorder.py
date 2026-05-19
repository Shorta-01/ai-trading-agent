from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from ai_trading_agent_storage import (
    CreateSystemEventRequest,
    DatabaseConnectionSettings,
    MigrationReadinessReport,
    SqlAlchemySystemEventRepository,
    StorageConnectionError,
    StorageConnectionNotReadyError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from sqlalchemy.engine import Connection

from portfolio_outlook_api.config import StorageSettings


@dataclass(frozen=True)
class ApiSystemEventInput:
    severity: str
    category: str
    source_component: str
    event_code: str
    title_nl: str
    message_nl: str
    help_nl: str
    technical_summary: str | None = None
    redacted_details_json: dict[str, str] | None = None
    stack_trace_redacted: str | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    blocks_suggestions: bool = False
    blocks_writes: bool = False
    blocks_ai_explanation: bool = False


@dataclass(frozen=True)
class ApiSystemEventRecordingResult:
    attempted: bool
    recorded: bool
    blocked: bool
    system_event_id: str | None
    status_nl: str
    message_nl: str


ConnectionProviderFactory = Callable[[DatabaseConnectionSettings], StorageConnectionProvider]
RepositoryFactory = Callable[
    [Connection, MigrationReadinessReport],
    SqlAlchemySystemEventRepository,
]
DateTimeProvider = Callable[[], datetime]
IdProvider = Callable[[], str]


def record_api_system_event(
    payload: ApiSystemEventInput,
    storage_settings: StorageSettings,
    connection_provider_factory: ConnectionProviderFactory | None = None,
    repository_factory: RepositoryFactory | None = None,
    now_provider: DateTimeProvider = lambda: datetime.now(UTC),
    id_provider: IdProvider = lambda: f"system-event-{uuid4()}",
) -> ApiSystemEventRecordingResult:
    """Record a system event only through checked storage pathways.

    Caller-provided details must already be redacted.
    """
    if connection_provider_factory is None:
        connection_provider_factory = StorageConnectionProvider
    if repository_factory is None:
        repository_factory = SqlAlchemySystemEventRepository

    if not storage_settings.enabled:
        return ApiSystemEventRecordingResult(
            attempted=False,
            recorded=False,
            blocked=True,
            system_event_id=None,
            status_nl="geblokkeerd",
            message_nl="Systeemmelding niet opgeslagen: opslag staat uit.",
        )

    database_url = storage_settings.database_url
    if database_url is None or database_url.strip() == "":
        return ApiSystemEventRecordingResult(
            attempted=False,
            recorded=False,
            blocked=True,
            system_event_id=None,
            status_nl="geblokkeerd",
            message_nl="Systeemmelding niet opgeslagen: database-url ontbreekt.",
        )

    provider = connection_provider_factory(build_database_connection_settings(database_url))
    system_event_id = id_provider()

    try:
        with provider.checked_connection(require_writable=True) as checked:
            repository = repository_factory(checked.connection, checked.readiness)
            repository.create_event(
                CreateSystemEventRequest(
                    system_event_id=system_event_id,
                    created_at=now_provider(),
                    severity=payload.severity,
                    category=payload.category,
                    source_service="api",
                    source_component=payload.source_component,
                    event_code=payload.event_code,
                    title_nl=payload.title_nl,
                    message_nl=payload.message_nl,
                    help_nl=payload.help_nl,
                    technical_summary=payload.technical_summary,
                    redacted_details_json=payload.redacted_details_json,
                    stack_trace_redacted=payload.stack_trace_redacted,
                    related_entity_type=payload.related_entity_type,
                    related_entity_id=payload.related_entity_id,
                    blocks_suggestions=payload.blocks_suggestions,
                    blocks_writes=payload.blocks_writes,
                    blocks_ai_explanation=payload.blocks_ai_explanation,
                    status="open",
                    explanation_nl="Systeemmelding vastgelegd via API-helper.",
                )
            )
        return ApiSystemEventRecordingResult(
            attempted=True,
            recorded=True,
            blocked=False,
            system_event_id=system_event_id,
            status_nl="opgeslagen",
            message_nl="Systeemmelding opgeslagen.",
        )
    except StorageConnectionNotReadyError:
        return ApiSystemEventRecordingResult(
            attempted=True,
            recorded=False,
            blocked=True,
            system_event_id=None,
            status_nl="geblokkeerd",
            message_nl="Systeemmelding niet opgeslagen: writes geblokkeerd.",
        )
    except StorageConnectionError:
        return ApiSystemEventRecordingResult(
            attempted=True,
            recorded=False,
            blocked=True,
            system_event_id=None,
            status_nl="mislukt",
            message_nl="Systeemmelding niet opgeslagen door een veilige foutafhandeling.",
        )
