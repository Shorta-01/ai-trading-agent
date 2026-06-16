"""Controlled storage connection provider with explicit readiness gating."""

from __future__ import annotations

import threading
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


# §CB.3 audit-correctie 2026-06-16 — engine-pool per URL.
#
# Vóór: `create_engine()` werd per request aangeroepen en daarna
# direct `dispose()`'d. Dat klinkt netjes maar betekent: per HTTP-call
# een fris pool-object, een nieuwe TCP-handshake, een nieuwe
# auth-uitwisseling met Postgres. Onder load (100+ daily refreshes
# op het dashboard) levert dat onnodige connection-churn op en kan
# Postgres' `max_connections` raken.
#
# Na: één engine per database-url, gecached in een module-level dict
# met thread-safe access. SQLAlchemy's `QueuePool` (default) doet
# zelf connection-pooling. We disposen niet meer per call; de engine
# blijft leven voor de levensduur van het proces. Bij SQLite (tests
# + lokale dev) heeft pool_size geen praktisch effect maar de cache
# voorkomt het `create_engine` overhead.
_DEFAULT_POOL_SIZE: int = 10
_DEFAULT_MAX_OVERFLOW: int = 20
_DEFAULT_POOL_RECYCLE_S: int = 3600  # Postgres idle-disconnect protection
_DEFAULT_POOL_PRE_PING: bool = True  # detect dead connections lazily

_engine_cache: dict[str, Engine] = {}
_engine_cache_lock = threading.Lock()


def _get_or_create_engine(database_url: str) -> Engine:
    with _engine_cache_lock:
        engine = _engine_cache.get(database_url)
        if engine is not None:
            return engine
        # SQLite ondersteunt geen QueuePool-tuning op dezelfde manier;
        # we passen alleen de pre-ping toe.
        if database_url.startswith("sqlite"):
            engine = create_engine(database_url, pool_pre_ping=_DEFAULT_POOL_PRE_PING)
        else:
            engine = create_engine(
                database_url,
                pool_size=_DEFAULT_POOL_SIZE,
                max_overflow=_DEFAULT_MAX_OVERFLOW,
                pool_recycle=_DEFAULT_POOL_RECYCLE_S,
                pool_pre_ping=_DEFAULT_POOL_PRE_PING,
            )
        _engine_cache[database_url] = engine
        return engine


def _dispose_cached_engines() -> None:
    """Test hook: dispose alle gecachte engines (voor pytest fixtures
    die wisselen tussen in-memory SQLite-instanties)."""

    with _engine_cache_lock:
        for engine in _engine_cache.values():
            engine.dispose()
        _engine_cache.clear()


@dataclass(frozen=True)
class StorageConnectionProvider:
    """Open connections against a cached, pooled engine per database url."""

    settings: DatabaseConnectionSettings

    @contextmanager
    def checked_connection(self, *, require_writable: bool) -> Iterator[CheckedStorageConnection]:
        database_url = self.settings.database_url
        if database_url is None or database_url.strip() == "":
            raise StorageConnectionError(
                "Database-url ontbreekt; expliciete runtimeverbinding kan niet worden geopend."
            )

        engine = _get_or_create_engine(database_url)
        connection: Connection | None = None
        try:
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
