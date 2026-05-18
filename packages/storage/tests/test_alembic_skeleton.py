from pathlib import Path

from ai_trading_agent_storage.alembic_helpers import (
    get_target_metadata,
    is_migration_skeleton_ready,
)
from ai_trading_agent_storage.metadata import metadata

ROOT = Path(__file__).resolve().parents[1]


def _token_position(content: str, token: str) -> int:
    position = content.find(token)
    assert position >= 0, f"Missing token: {token}"
    return position


def test_alembic_files_and_versions_folder_exist() -> None:
    assert (ROOT / "alembic.ini").exists()
    assert (ROOT / "alembic" / "env.py").exists()
    assert (ROOT / "alembic" / "versions").exists()


def test_target_metadata_is_package_metadata() -> None:
    assert get_target_metadata() is metadata


def test_skeleton_ready_without_database_connection() -> None:
    assert is_migration_skeleton_ready() is True


def test_single_revision_file_exists_with_expected_name() -> None:
    versions_dir = ROOT / "alembic" / "versions"
    revision_files = sorted(path.name for path in versions_dir.glob("*.py"))
    assert revision_files == ["0001_paper_setup_audit_foundation.py"]


def test_revision_file_contains_required_upgrade_downgrade_and_table_ops() -> None:
    revision_path = ROOT / "alembic" / "versions" / "0001_paper_setup_audit_foundation.py"
    content = revision_path.read_text(encoding="utf-8")

    assert "def upgrade()" in content
    assert "def downgrade()" in content

    first_create_position = _token_position(content, "op.create_table(")
    paper_setups_name_position = _token_position(content, '"paper_portfolio_setups"')
    paper_cash_name_position = _token_position(content, '"paper_cash_accounts"')
    audit_events_name_position = _token_position(content, '"audit_events"')
    assert first_create_position < paper_setups_name_position
    assert first_create_position < paper_cash_name_position
    assert first_create_position < audit_events_name_position

    audit_drop_position = _token_position(content, 'op.drop_table("audit_events")')
    cash_drop_position = _token_position(content, 'op.drop_table("paper_cash_accounts")')
    setup_drop_position = _token_position(content, 'op.drop_table("paper_portfolio_setups")')
    assert audit_drop_position < cash_drop_position < setup_drop_position


def test_revision_file_has_no_runtime_package_imports() -> None:
    revision_path = ROOT / "alembic" / "versions" / "0001_paper_setup_audit_foundation.py"
    content = revision_path.read_text(encoding="utf-8")
    forbidden = [
        "portfolio_outlook_domain",
        "portfolio_outlook_portfolio",
        "portfolio_outlook_api",
        "worker",
    ]
    for token in forbidden:
        assert token not in content
