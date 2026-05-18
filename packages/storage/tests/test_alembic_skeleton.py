from pathlib import Path

from ai_trading_agent_storage.alembic_helpers import (
    get_target_metadata,
    is_migration_skeleton_ready,
)
from ai_trading_agent_storage.metadata import metadata

ROOT = Path(__file__).resolve().parents[1]


def test_alembic_files_and_versions_placeholder_exist() -> None:
    assert (ROOT / "alembic.ini").exists()
    assert (ROOT / "alembic" / "env.py").exists()
    versions = ROOT / "alembic" / "versions"
    assert versions.exists()
    assert (versions / ".gitkeep").exists()


def test_target_metadata_is_package_metadata_and_empty() -> None:
    assert get_target_metadata() is metadata
    assert len(metadata.tables) == 0


def test_skeleton_ready_without_database_connection() -> None:
    assert is_migration_skeleton_ready() is True


def test_no_revision_files_yet() -> None:
    versions_dir = ROOT / "alembic" / "versions"
    entries = sorted(path.name for path in versions_dir.iterdir())
    assert entries == [".gitkeep"]
