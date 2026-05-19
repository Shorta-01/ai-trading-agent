from pathlib import Path

import pytest
from sqlalchemy import text

from ai_trading_agent_storage.connection_provider import (
    StorageConnectionError,
    StorageConnectionNotReadyError,
    StorageConnectionProvider,
)
from ai_trading_agent_storage.migration_readiness import MigrationReadinessStatus
from ai_trading_agent_storage.settings import build_database_connection_settings


def test_provider_raises_if_database_url_missing() -> None:
    provider = StorageConnectionProvider(settings=build_database_connection_settings(None))

    with pytest.raises(StorageConnectionError):
        with provider.checked_connection(require_writable=False):
            pass


def test_provider_allows_read_only_connection_when_revision_behind(tmp_path: Path) -> None:
    db_path = tmp_path / "storage-readonly.sqlite"
    url = f"sqlite+pysqlite:///{db_path}"
    provider = StorageConnectionProvider(settings=build_database_connection_settings(url))

    with provider.checked_connection(require_writable=False) as checked:
        checked.connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        checked.connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('0005')")
        )
        report = checked.readiness

    assert report.status == MigrationReadinessStatus.FAILED
    assert report.persistence_allowed is False


def test_provider_blocks_writable_when_not_ready(tmp_path: Path) -> None:
    db_path = tmp_path / "storage-blocked.sqlite"
    url = f"sqlite+pysqlite:///{db_path}"

    with StorageConnectionProvider(
        settings=build_database_connection_settings(url)
    ).checked_connection(require_writable=False) as checked:
        checked.connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        checked.connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('0005')")
        )
        checked.connection.commit()

    provider = StorageConnectionProvider(settings=build_database_connection_settings(url))

    with pytest.raises(StorageConnectionNotReadyError):
        with provider.checked_connection(require_writable=True):
            pass


def test_provider_allows_writable_when_ready(tmp_path: Path) -> None:
    db_path = tmp_path / "storage-ready.sqlite"
    url = f"sqlite+pysqlite:///{db_path}"

    with StorageConnectionProvider(
        settings=build_database_connection_settings(url)
    ).checked_connection(require_writable=False) as checked:
        checked.connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        checked.connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('0006')")
        )
        checked.connection.commit()

    provider = StorageConnectionProvider(settings=build_database_connection_settings(url))

    with provider.checked_connection(require_writable=True) as checked:
        assert checked.readiness.status == MigrationReadinessStatus.MIGRATIONS_CURRENT
        assert checked.readiness.persistence_allowed is True


def test_provider_module_has_no_global_engine_markers() -> None:
    source = Path("src/ai_trading_agent_storage/connection_provider.py").read_text()
    forbidden = (
        "sessionmaker",
        "DATABASE_URL",
        "os.environ",
    )

    for marker in forbidden:
        assert marker not in source
