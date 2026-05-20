from dataclasses import fields
from pathlib import Path

from ai_trading_agent_storage.migration_readiness import (
    MigrationInventory,
    MigrationReadinessReport,
    MigrationRevisionInfo,
    build_database_not_connected_readiness_report,
    build_expected_migration_inventory,
    check_offline_migration_inventory,
    expected_migration_revisions,
    migration_readiness_interfaces_are_defined,
    migration_readiness_is_safe_to_write,
)


def test_migration_readiness_imports_and_interfaces() -> None:
    assert migration_readiness_interfaces_are_defined() is True


def test_expected_revisions_match_known_migrations() -> None:
    revisions = expected_migration_revisions()
    inventory = build_expected_migration_inventory()

    assert len(revisions) == inventory.revision_count
    assert [item.revision_id for item in revisions[:14]] == [
        "0001",
        "0002",
        "0003",
        "0004",
        "0005",
        "0006",
        "0007",
        "0008",
        "0009",
        "0010",
        "0011",
        "0012",
        "0013",
        "0014",
    ]
    assert revisions[-1].revision_id == inventory.latest_expected_revision_id

    migration_files = {path.name for path in Path("alembic/versions").glob("*.py")}
    for item in revisions:
        assert item.filename in migration_files
        assert item.label_nl.strip()
        assert item.description_nl.strip()


def test_inventory_contract_is_deterministic_and_valid() -> None:
    inventory = build_expected_migration_inventory()

    assert isinstance(inventory, MigrationInventory)
    assert isinstance(inventory.expected_revisions, tuple)
    assert inventory.revision_count == len(inventory.expected_revisions)
    assert inventory.latest_expected_revision_id == inventory.expected_revisions[-1].revision_id
    assert inventory.inventory_valid is True


def test_not_connected_report_blocks_runtime_writes() -> None:
    report = build_database_not_connected_readiness_report()

    assert report.status.value == "not_connected"
    assert report.database_connected is False
    assert report.migrations_checked_against_database is False
    assert report.database_revision_id is None
    assert report.persistence_allowed is False
    assert report.blocks_runtime_writes is True
    assert report.explanation_nl.strip()
    assert migration_readiness_is_safe_to_write(report) is False


def test_offline_inventory_report_stays_offline_and_blocking() -> None:
    report = check_offline_migration_inventory()
    inventory = build_expected_migration_inventory()

    assert isinstance(report, MigrationReadinessReport)
    assert report.database_connected is False
    assert report.migrations_checked_against_database is False
    assert report.persistence_allowed is False
    assert report.blocks_runtime_writes is True
    assert report.latest_expected_revision_id == inventory.latest_expected_revision_id
    assert report.status.value == "offline_inventory_valid"
    assert "offline" in report.explanation_nl.lower()
    assert "geen bewijs" in report.explanation_nl.lower()


def test_no_secret_like_fields_in_readiness_contracts() -> None:
    forbidden = (
        "password",
        "api_key",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "credential",
    )
    for item in (MigrationRevisionInfo, MigrationInventory, MigrationReadinessReport):
        for field in fields(item):
            lower = field.name.lower()
            assert not any(word in lower for word in forbidden)


def test_migration_readiness_module_has_no_db_connection_markers() -> None:
    module_source = Path("src/ai_trading_agent_storage/migration_readiness.py").read_text()

    forbidden_markers = (
        "create_engine",
        "sessionmaker",
        "DATABASE_URL",
        "os.environ",
        "psycopg",
        "asyncpg",
    )
    for marker in forbidden_markers:
        assert marker not in module_source
