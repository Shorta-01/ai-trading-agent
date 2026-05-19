"""Controlled storage connection provider with explicit readiness gating."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    check_online_migration_readiness,
    migration_readiness_is_safe_to_write,
)
from ai_trading_agent_storage.settings import DatabaseConnectionSettings


class StorageConnectionError(RuntimeError):
    """Base error for controlled storage connection provisioning."""


class StorageConnectionNotReadyError(StorageConnectionError):
    """Raised when a writable connection is requested before migrations are ready."""


@dataclass(frozen=True)
class CheckedStorageConnection:
    connection: Connection
    readiness: MigrationReadinessReport


@dataclass(frozen=True)
class StorageConnectionProvider:
    """Create engines/connections on-demand and close them reliably."""

    settings: DatabaseConnectionSettings

    @contextmanager
    def checked_connection(self, *, require_writable: bool) -> Iterator[CheckedStorageConnection]:
        database_url = self.settings.database_url
        if database_url is None or database_url.strip() == "":
            raise StorageConnectionError(
                "Database-url ontbreekt; expliciete runtimeverbinding kan niet worden geopend."
            )

        engine: Engine | None = None
        connection: Connection | None = None
        try:
            engine = create_engine(database_url)
            connection = engine.connect()
            readiness = check_online_migration_readiness(connection)

            if require_writable and not migration_readiness_is_safe_to_write(readiness):
                raise StorageConnectionNotReadyError(
                    "Migratie-readiness blokkeert writes; connection wordt "
                    "niet als writable vrijgegeven."
                )

            yield CheckedStorageConnection(connection=connection, readiness=readiness)
        except SQLAlchemyError as exc:
            raise StorageConnectionError(
                "Storage-verbinding mislukt tijdens gecontroleerde connectie-opbouw."
            ) from exc
        finally:
            if connection is not None:
                connection.close()
            if engine is not None:
                engine.dispose()
