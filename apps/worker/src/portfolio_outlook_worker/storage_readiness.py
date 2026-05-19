from __future__ import annotations

from collections.abc import Callable

from ai_trading_agent_storage import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
    build_database_not_connected_readiness_report,
    check_online_migration_readiness,
    migration_readiness_is_safe_to_write,
)
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from portfolio_outlook_worker.config import StorageSettings


class WorkerStorageReadiness(BaseModel):
    configured: bool
    connected: bool
    safe_to_write: bool
    status_nl: str
    message_nl: str
    migration_readiness_status: str
    writes_status_nl: str


EngineFactory = Callable[[str], Engine]
ReadinessChecker = Callable[[Connection], MigrationReadinessReport]


def build_worker_storage_readiness(
    storage_settings: StorageSettings,
    engine_factory: EngineFactory | None = None,
    readiness_checker: ReadinessChecker = check_online_migration_readiness,
) -> WorkerStorageReadiness:
    if not storage_settings.enabled:
        return WorkerStorageReadiness(
            configured=False,
            connected=False,
            safe_to_write=False,
            status_nl="Niet geconfigureerd",
            message_nl="Opslag staat uit. Database niet verbonden.",
            migration_readiness_status=MigrationReadinessStatus.NOT_CONNECTED.value,
            writes_status_nl="Writes geblokkeerd",
        )

    database_url = storage_settings.database_url
    if database_url is None or database_url.strip() == "":
        return WorkerStorageReadiness(
            configured=False,
            connected=False,
            safe_to_write=False,
            status_nl="Geblokkeerd",
            message_nl="Database-url ontbreekt. Niet verbonden.",
            migration_readiness_status=MigrationReadinessStatus.NOT_CONNECTED.value,
            writes_status_nl="Writes geblokkeerd",
        )

    if engine_factory is None:
        engine_factory = create_engine

    engine: Engine | None = None
    connection: Connection | None = None
    try:
        engine = engine_factory(database_url)
        connection = engine.connect()
        readiness = readiness_checker(connection)
    except (SQLAlchemyError, ValueError):
        readiness = build_database_not_connected_readiness_report()
        return WorkerStorageReadiness(
            configured=True,
            connected=False,
            safe_to_write=False,
            status_nl="Geblokkeerd",
            message_nl="Database niet bereikbaar",
            migration_readiness_status=readiness.status.value,
            writes_status_nl="Writes geblokkeerd",
        )
    finally:
        if connection is not None:
            connection.close()
        if engine is not None:
            engine.dispose()

    safe_to_write = migration_readiness_is_safe_to_write(readiness)
    return WorkerStorageReadiness(
        configured=True,
        connected=readiness.database_connected,
        safe_to_write=safe_to_write,
        status_nl="Verbonden" if readiness.database_connected else "Niet verbonden",
        message_nl=(
            "Migraties klaar"
            if readiness.status == MigrationReadinessStatus.MIGRATIONS_CURRENT
            else "Migraties niet klaar"
        ),
        migration_readiness_status=readiness.status.value,
        writes_status_nl="Writes toegestaan" if safe_to_write else "Writes geblokkeerd",
    )
