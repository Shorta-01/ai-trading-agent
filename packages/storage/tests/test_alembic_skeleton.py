from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from ai_trading_agent_storage.alembic_helpers import (
    get_target_metadata,
    is_migration_skeleton_ready,
)
from ai_trading_agent_storage.metadata import metadata

ROOT = Path(__file__).resolve().parents[1]


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


def test_alembic_files_and_versions_folder_exist() -> None:
    assert (ROOT / "alembic.ini").exists()
    assert (ROOT / "alembic" / "env.py").exists()
    assert (ROOT / "alembic" / "versions").exists()


def test_target_metadata_is_package_metadata() -> None:
    assert get_target_metadata() is metadata


def test_skeleton_ready_without_database_connection() -> None:
    assert is_migration_skeleton_ready() is True


def test_exactly_three_revision_files_exist_with_expected_names() -> None:
    versions_dir = ROOT / "alembic" / "versions"
    revision_files = sorted(
        path.name for path in versions_dir.glob("*.py") if path.name != ".gitkeep"
    )
    assert revision_files == [
        "0001_paper_setup_audit_foundation.py",
        "0002_broker_accounts_and_sync_runs.py",
        "0003_broker_position_and_cash_snapshots.py",
    ]


def test_0002_revision_content_and_safety_guards() -> None:
    revision_path = ROOT / "alembic" / "versions" / "0002_broker_accounts_and_sync_runs.py"
    content = revision_path.read_text(encoding="utf-8")
    normalized = _normalize(content)

    assert "def upgrade()" in content
    assert "def downgrade()" in content
    assert "broker account and sync run foundation" in content.lower()
    assert "ibkr mirror/reconciliation foundation slice 1" in content.lower()

    assert "broker_accounts" in content
    assert "broker_sync_runs" in content

    drop_sync_position = content.find('op.drop_table("broker_sync_runs")')
    drop_accounts_position = content.find('op.drop_table("broker_accounts")')
    assert drop_sync_position >= 0
    assert drop_accounts_position >= 0
    assert drop_sync_position < drop_accounts_position

    forbidden_tokens = [
        "password",
        "access_token",
        "refresh_token",
        "api_key",
        "secret_value",
        "ibapi",
        "ib_insync",
    ]
    for token in forbidden_tokens:
        assert token not in normalized

    forbidden_import_tokens = [
        "portfolio_outlook_domain",
        "portfolio_outlook_portfolio",
        "portfolio_outlook_api",
        "worker",
        "ibkr",
    ]
    for token in forbidden_import_tokens:
        assert f"import {token}" not in normalized
        assert f"from {token} import" not in normalized


def test_postgresql_create_table_compilation_includes_broker_tables() -> None:
    table_names = [
        "paper_portfolio_setups",
        "paper_cash_accounts",
        "audit_events",
        "broker_accounts",
        "broker_sync_runs",
        "broker_position_snapshots",
        "broker_cash_snapshots",
    ]
    for table_name in table_names:
        sql = str(CreateTable(metadata.tables[table_name]).compile(dialect=postgresql.dialect()))
        assert f"create table {table_name}" in sql.lower()


def test_0003_revision_content_and_safety_guards() -> None:
    revision_path = ROOT / "alembic" / "versions" / "0003_broker_position_and_cash_snapshots.py"
    content = revision_path.read_text(encoding="utf-8")
    normalized = _normalize(content)

    assert "def upgrade()" in content
    assert "def downgrade()" in content
    assert "broker position and cash snapshot foundation" in content.lower()
    assert "ibkr mirror/reconciliation foundation slice 2" in content.lower()
    assert "broker_position_snapshots" in content
    assert "broker_cash_snapshots" in content

    drop_cash_position = content.find('op.drop_table("broker_cash_snapshots")')
    drop_position_position = content.find('op.drop_table("broker_position_snapshots")')
    assert drop_cash_position >= 0
    assert drop_position_position >= 0
    assert drop_cash_position < drop_position_position

    forbidden_tokens = [
        "password",
        "access_token",
        "refresh_token",
        "api_key",
        "secret_value",
        "ibapi",
        "ib_insync",
    ]
    for token in forbidden_tokens:
        assert token not in normalized

    forbidden_import_tokens = ["domain", "portfolio", "api", "worker", "ibkr"]
    for token in forbidden_import_tokens:
        assert f"import {token}" not in normalized
        assert f"from {token} import" not in normalized
