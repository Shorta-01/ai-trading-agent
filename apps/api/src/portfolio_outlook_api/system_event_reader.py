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
    # V1.2 §BZ vervolg — surface resolved_at / archived_at zodat het
    # audit-trail (en het belastingrapport) een chronologische
    # geschiedenis kan tonen: WANNEER heeft de operator een event
    # weggeklikt of gearchiveerd? Compliance-relevant. Beide None
    # zolang het event nog in ``status="open"`` zit.
    resolved_at: str | None = None
    archived_at: str | None = None


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
        resolved_at=(
            record.resolved_at.isoformat()
            if record.resolved_at is not None
            else None
        ),
        archived_at=(
            record.archived_at.isoformat()
            if record.archived_at is not None
            else None
        ),
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


# V1.2 §BZ vervolg: audit-trail constants for the IBKR config view.
# Houdt alle SystemEvent-codes / categorieën die de operator over de
# tijd ziet rondom IBKR mode-switches, mismatch detections en
# account-id wijzigingen samen, zodat een nieuwe code (b.v. uit een
# follow-up PR) automatisch in het audit-rapport landt.
_IBKR_CONFIG_AUDIT_CATEGORIES: tuple[str, ...] = (
    "ibkr_config_mismatch",
    "ibkr_config_change",
)
_IBKR_CONFIG_AUDIT_EVENT_CODES: tuple[str, ...] = (
    "order_session_live_account",
    "account_id_mismatch",
    "ibkr_account_id_changed",
)


def list_ibkr_config_audit(
    storage_settings: StorageSettings,
    connection_provider_factory: ConnectionProviderFactory | None = None,
    repository_factory: RepositoryFactory | None = None,
    *,
    limit: int = 500,
) -> ActiveSystemEventsResponse:
    """V1.2 §BZ vervolg — compliance audit-trail van alle IBKR-config events.

    Returnt ook RESOLVED + ARCHIVED events (in tegenstelling tot
    :func:`list_active_system_events` die alleen open events laat zien).
    Dit geeft de operator en accountant een chronologisch overzicht
    van mode-switches, mismatches en account-id wijzigingen — bewijs
    voor het "goed huisvader" §12 belastingrapport.
    """

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
            message_nl="Audit-trail niet beschikbaar: opslag staat uit.",
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
            message_nl="Audit-trail niet beschikbaar: database-url ontbreekt.",
            events=[],
        )

    provider = connection_provider_factory(
        build_database_connection_settings(database_url)
    )

    try:
        with provider.checked_connection(require_writable=False) as checked:
            repository = repository_factory(
                checked.connection, checked.readiness
            )
            result = repository.list_events_by_categories(
                _IBKR_CONFIG_AUDIT_CATEGORIES,
                include_event_codes=_IBKR_CONFIG_AUDIT_EVENT_CODES,
                limit=limit,
            )
            mapped = [_map_event_summary(record) for record in result.records]
            return ActiveSystemEventsResponse(
                available=True,
                storage_configured=True,
                events_loaded=True,
                active_count=len(mapped),
                status_nl="Beschikbaar",
                message_nl=(
                    f"{len(mapped)} IBKR-config events in het audit-trail."
                ),
                events=mapped,
            )
    except StorageConnectionError:
        return ActiveSystemEventsResponse(
            available=False,
            storage_configured=True,
            events_loaded=False,
            active_count=0,
            status_nl="Niet beschikbaar",
            message_nl="Audit-trail niet beschikbaar door veilige foutafhandeling.",
            events=[],
        )
