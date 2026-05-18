"""Helpers that expose migration skeleton readiness without database access."""

from sqlalchemy import MetaData

from ai_trading_agent_storage.metadata import metadata


def get_target_metadata() -> MetaData:
    """Return the SQLAlchemy metadata target for Alembic."""

    return metadata


def is_migration_skeleton_ready() -> bool:
    """Return whether metadata import and helper wiring are available."""

    target_metadata = get_target_metadata()
    return isinstance(target_metadata, MetaData)
