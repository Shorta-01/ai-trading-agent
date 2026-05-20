from pathlib import Path

from sqlalchemy import create_engine, text

from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessStatus,
    build_database_not_connected_readiness_report,
    build_expected_migration_inventory,
    check_offline_migration_inventory,
    check_online_migration_readiness,
    migration_readiness_is_safe_to_write,
    online_migration_readiness_interfaces_are_defined,
)


def _new_connection():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    return engine.connect()


def test_online_imports_and_interface_flag() -> None:
    assert online_migration_readiness_interfaces_are_defined() is True


def test_online_current_revision_allows_persistence() -> None:
    latest_revision_id = build_expected_migration_inventory().latest_expected_revision_id
    with _new_connection() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:latest_revision_id)"),
            {"latest_revision_id": latest_revision_id},
        )
        report = check_online_migration_readiness(conn)

    assert report.status == MigrationReadinessStatus.MIGRATIONS_CURRENT
    assert report.database_connected is True
    assert report.migrations_checked_against_database is True
    assert report.database_revision_id == latest_revision_id
    assert report.latest_expected_revision_id == latest_revision_id
    assert report.persistence_allowed is True
    assert report.blocks_runtime_writes is False
    assert report.explanation_nl.strip()
    assert migration_readiness_is_safe_to_write(report) is True


def test_online_known_behind_revision_blocks_writes() -> None:
    with _new_connection() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0005')"))
        report = check_online_migration_readiness(conn)

    assert report.status == MigrationReadinessStatus.MIGRATIONS_BEHIND
    assert report.database_revision_id == "0005"
    assert report.persistence_allowed is False
    assert report.blocks_runtime_writes is True


def test_online_unknown_revision_blocks_writes() -> None:
    with _new_connection() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('9999')"))
        report = check_online_migration_readiness(conn)

    assert report.status == MigrationReadinessStatus.MIGRATIONS_UNKNOWN
    assert report.persistence_allowed is False
    assert report.blocks_runtime_writes is True


def test_online_missing_alembic_version_table_blocks_writes() -> None:
    with _new_connection() as conn:
        report = check_online_migration_readiness(conn)

    assert report.status == MigrationReadinessStatus.FAILED
    assert report.database_revision_id is None
    assert report.persistence_allowed is False
    assert report.blocks_runtime_writes is True
    assert report.explanation_nl.strip()


def test_online_empty_alembic_version_table_blocks_writes() -> None:
    with _new_connection() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        report = check_online_migration_readiness(conn)

    assert report.status == MigrationReadinessStatus.MIGRATIONS_UNKNOWN
    assert report.database_revision_id is None
    assert report.persistence_allowed is False
    assert report.blocks_runtime_writes is True


def test_online_multiple_rows_are_not_treated_as_success() -> None:
    latest_revision_id = build_expected_migration_inventory().latest_expected_revision_id
    with _new_connection() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0005')"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:latest_revision_id)"),
            {"latest_revision_id": latest_revision_id},
        )
        report = check_online_migration_readiness(conn)

    assert report.status == MigrationReadinessStatus.FAILED
    assert report.persistence_allowed is False
    assert report.blocks_runtime_writes is True


def test_module_has_no_env_or_engine_autowiring_markers() -> None:
    source = Path("src/ai_trading_agent_storage/migration_readiness.py").read_text()
    forbidden = (
        "DATABASE_URL",
        "os.environ",
        "create_engine",
        "sessionmaker",
        "psycopg",
        "asyncpg",
    )
    for marker in forbidden:
        assert marker not in source


def test_offline_behavior_remains_blocking() -> None:
    offline = check_offline_migration_inventory()
    not_connected = build_database_not_connected_readiness_report()

    assert offline.persistence_allowed is False
    assert offline.blocks_runtime_writes is True
    assert not_connected.persistence_allowed is False
    assert not_connected.blocks_runtime_writes is True
    assert migration_readiness_is_safe_to_write(offline) is False
    assert migration_readiness_is_safe_to_write(not_connected) is False
