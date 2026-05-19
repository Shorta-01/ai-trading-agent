from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ai_trading_agent_storage import (
    DatabaseConnectionSettings,
    MigrationReadinessReport,
    SqlAlchemySystemEventRepository,
    StorageConnectionError,
    StorageConnectionNotReadyError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from pydantic import BaseModel, ConfigDict
from sqlalchemy.engine import Connection

from portfolio_outlook_api.config import StorageSettings


class SystemEventMutationInput(BaseModel):
    model_config = ConfigDict(frozen=True)
    reason_nl: str | None = None


@dataclass(frozen=True)
class SystemEventMutationResult:
    response: dict[str, object]
    blocked: bool
    not_found: bool = False


ConnectionProviderFactory = Callable[[DatabaseConnectionSettings], StorageConnectionProvider]
RepositoryFactory = Callable[
    [Connection, MigrationReadinessReport],
    SqlAlchemySystemEventRepository,
]


def mark_system_event_resolved(
    system_event_id: str,
    storage_settings: StorageSettings,
    payload: SystemEventMutationInput,
    connection_provider_factory: ConnectionProviderFactory | None = None,
    repository_factory: RepositoryFactory | None = None,
) -> SystemEventMutationResult:
    return _mutate_system_event_status(
        system_event_id=system_event_id,
        storage_settings=storage_settings,
        payload=payload,
        mutation='resolve',
        connection_provider_factory=connection_provider_factory,
        repository_factory=repository_factory,
    )


def mark_system_event_archived(
    system_event_id: str,
    storage_settings: StorageSettings,
    payload: SystemEventMutationInput,
    connection_provider_factory: ConnectionProviderFactory | None = None,
    repository_factory: RepositoryFactory | None = None,
) -> SystemEventMutationResult:
    return _mutate_system_event_status(
        system_event_id=system_event_id,
        storage_settings=storage_settings,
        payload=payload,
        mutation='archive',
        connection_provider_factory=connection_provider_factory,
        repository_factory=repository_factory,
    )


def _mutate_system_event_status(
    *,
    system_event_id: str,
    storage_settings: StorageSettings,
    payload: SystemEventMutationInput,
    mutation: str,
    connection_provider_factory: ConnectionProviderFactory | None,
    repository_factory: RepositoryFactory | None,
) -> SystemEventMutationResult:
    if connection_provider_factory is None:
        connection_provider_factory = StorageConnectionProvider
    if repository_factory is None:
        repository_factory = SqlAlchemySystemEventRepository

    if not storage_settings.enabled:
        return SystemEventMutationResult(
            response={'status_nl': 'Geblokkeerd', 'updated': False, 'message_nl': 'Opslag staat uit. Wijzigingen zijn geblokkeerd.'},
            blocked=True,
        )

    database_url = storage_settings.database_url
    if database_url is None or database_url.strip() == '':
        return SystemEventMutationResult(
            response={'status_nl': 'Geblokkeerd', 'updated': False, 'message_nl': 'Database-url ontbreekt. Wijzigingen zijn geblokkeerd.'},
            blocked=True,
        )

    provider = connection_provider_factory(build_database_connection_settings(database_url))

    try:
        with provider.checked_connection(require_writable=True) as checked:
            repository = repository_factory(checked.connection, checked.readiness)
            if mutation == 'resolve':
                result = repository.mark_resolved(system_event_id, reason_nl=payload.reason_nl)
                ok_message = 'Systeemmelding gemarkeerd als opgelost.'
            else:
                result = repository.mark_archived(system_event_id, reason_nl=payload.reason_nl)
                ok_message = 'Systeemmelding gearchiveerd.'

            if not result.accepted:
                return SystemEventMutationResult(
                    response={'status_nl': 'Niet gevonden', 'updated': False, 'message_nl': 'Systeemmelding niet gevonden.'},
                    blocked=False,
                    not_found=True,
                )

            return SystemEventMutationResult(
                response={'status_nl': 'Gelukt', 'updated': True, 'message_nl': ok_message},
                blocked=False,
            )
    except StorageConnectionNotReadyError:
        return SystemEventMutationResult(
            response={'status_nl': 'Geblokkeerd', 'updated': False, 'message_nl': 'Writes zijn geblokkeerd door migratie-readiness.'},
            blocked=True,
        )
    except StorageConnectionError:
        return SystemEventMutationResult(
            response={'status_nl': 'Geblokkeerd', 'updated': False, 'message_nl': 'Databaseverbinding mislukt. Wijziging is geblokkeerd.'},
            blocked=True,
        )
