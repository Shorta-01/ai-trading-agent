from __future__ import annotations

from collections.abc import Callable

from ai_trading_agent_storage import (
    DatabaseConnectionSettings,
    MigrationReadinessReport,
    SqlAlchemySystemEventRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    SystemEventRecord,
    build_database_connection_settings,
)
from pydantic import BaseModel, ConfigDict
from sqlalchemy.engine import Connection

from portfolio_outlook_api.config import StorageSettings


class ActiveSystemEventSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    system_event_id: str
    created_at: str
    severity: str
    category: str
    source_service: str
    source_component: str
    event_code: str
    title_nl: str
    message_nl: str
    help_nl: str
    blocks_suggestions: bool
    blocks_writes: bool
    blocks_ai_explanation: bool
    status: str


class ActiveSystemEventsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    available: bool
    storage_configured: bool
    events_loaded: bool
    active_count: int
    status_nl: str
    message_nl: str
    events: list[ActiveSystemEventSummary]


ConnectionProviderFactory = Callable[[DatabaseConnectionSettings], StorageConnectionProvider]
RepositoryFactory = Callable[
    [Connection, MigrationReadinessReport],
    SqlAlchemySystemEventRepository,
]


def _map_event_summary(record: SystemEventRecord) -> ActiveSystemEventSummary:
    return ActiveSystemEventSummary(
        system_event_id=record.system_event_id,
        created_at=record.created_at.isoformat(),
        severity=record.severity,
        category=record.category,
        source_service=record.source_service,
        source_component=record.source_component,
        event_code=record.event_code,
        title_nl=record.title_nl,
        message_nl=record.message_nl,
        help_nl=record.help_nl,
        blocks_suggestions=record.blocks_suggestions,
        blocks_writes=record.blocks_writes,
        blocks_ai_explanation=record.blocks_ai_explanation,
        status=record.status,
    )


def list_active_system_events(
    storage_settings: StorageSettings,
    connection_provider_factory: ConnectionProviderFactory | None = None,
    repository_factory: RepositoryFactory | None = None,
) -> ActiveSystemEventsResponse:
    if connection_provider_factory is None:
        connection_provider_factory = StorageConnectionProvider
    if repository_factory is None:
        repository_factory = SqlAlchemySystemEventRepository

    if not storage_settings.enabled:
        return ActiveSystemEventsResponse(
            available=False,
            storage_configured=False,
            events_loaded=False,
            active_count=0,
            status_nl="Niet beschikbaar",
            message_nl="Systeemmeldingen niet beschikbaar: opslag staat uit.",
            events=[],
        )

    database_url = storage_settings.database_url
    if database_url is None or database_url.strip() == "":
        return ActiveSystemEventsResponse(
            available=False,
            storage_configured=False,
            events_loaded=False,
            active_count=0,
            status_nl="Niet beschikbaar",
            message_nl="Systeemmeldingen niet beschikbaar: database-url ontbreekt.",
            events=[],
        )

    provider = connection_provider_factory(build_database_connection_settings(database_url))

    try:
        with provider.checked_connection(require_writable=False) as checked:
            repository = repository_factory(checked.connection, checked.readiness)
            open_events = repository.list_open_events().records
            mapped_events = [_map_event_summary(record) for record in open_events]

            if len(mapped_events) == 0:
                return ActiveSystemEventsResponse(
                    available=True,
                    storage_configured=True,
                    events_loaded=True,
                    active_count=0,
                    status_nl="Beschikbaar",
                    message_nl="Geen actieve systeemmeldingen.",
                    events=[],
                )

            return ActiveSystemEventsResponse(
                available=True,
                storage_configured=True,
                events_loaded=True,
                active_count=len(mapped_events),
                status_nl="Beschikbaar",
                message_nl="Systeemmeldingen beschikbaar.",
                events=mapped_events,
            )
    except StorageConnectionError:
        return ActiveSystemEventsResponse(
            available=False,
            storage_configured=True,
            events_loaded=False,
            active_count=0,
            status_nl="Niet beschikbaar",
            message_nl="Systeemmeldingen niet beschikbaar door veilige foutafhandeling.",
            events=[],
        )
