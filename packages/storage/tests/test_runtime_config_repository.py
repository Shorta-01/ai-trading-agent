"""Tests for the editable runtime-config repository (IBKR + Claude AI)."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine

from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from ai_trading_agent_storage.repository_contracts import RuntimeConfigRecord
from ai_trading_agent_storage.sql_repositories import (
    SqlAlchemyRuntimeConfigRepository,
)

_NOW = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)


def _report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id="0055_runtime_config",
        database_revision_id="0055_runtime_config",
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="test",
    )


def _record(
    *,
    ibkr_enabled: bool = True,
    account_id: str | None = "DU1",
    model: str | None = "claude-sonnet",
    budget: Decimal | None = Decimal("12.500000"),
    api_key: str | None = "secret-key-1",
    updated_at: datetime = _NOW,
) -> RuntimeConfigRecord:
    return RuntimeConfigRecord(
        config_id="default",
        ibkr_enabled=ibkr_enabled,
        ibkr_account_id=account_id,
        ibkr_host="127.0.0.1",
        ibkr_port=7497,
        ibkr_client_id=1,
        ai_explanation_enabled=True,
        claude_ai_explanation_model=model,
        claude_ai_budget_monthly_eur=budget,
        claude_ai_api_key=api_key,
        updated_at=updated_at,
    )


def test_get_returns_none_when_empty() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyRuntimeConfigRepository(conn, _report())
        assert repo.get() is None


def test_upsert_then_get_returns_the_row() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyRuntimeConfigRepository(conn, _report())
        repo.upsert(_record())
        conn.commit()

        stored = repo.get()

    assert stored is not None
    assert stored.config_id == "default"
    assert stored.ibkr_enabled is True
    assert stored.ibkr_account_id == "DU1"
    assert stored.ibkr_host == "127.0.0.1"
    assert stored.ibkr_port == 7497
    assert stored.ibkr_client_id == 1
    assert stored.ai_explanation_enabled is True
    assert stored.claude_ai_explanation_model == "claude-sonnet"
    assert stored.claude_ai_budget_monthly_eur == Decimal("12.500000")
    assert stored.claude_ai_api_key == "secret-key-1"


def test_second_upsert_updates_existing_row() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    later = datetime(2026, 6, 1, 9, 30, tzinfo=UTC)
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyRuntimeConfigRepository(conn, _report())
        repo.upsert(_record())
        conn.commit()

        repo.upsert(
            _record(
                ibkr_enabled=False,
                account_id="DU2",
                model="claude-opus",
                budget=Decimal("99.000000"),
                api_key="secret-key-2",
                updated_at=later,
            )
        )
        conn.commit()

        stored = repo.get()
        # Still a single row.
        count = conn.execute(
            metadata.tables["runtime_config"].select()
        ).fetchall()

    assert len(count) == 1
    assert stored is not None
    assert stored.ibkr_enabled is False
    assert stored.ibkr_account_id == "DU2"
    assert stored.claude_ai_explanation_model == "claude-opus"
    assert stored.claude_ai_budget_monthly_eur == Decimal("99.000000")
    assert stored.claude_ai_api_key == "secret-key-2"
    # SQLite drops tzinfo on round-trip; compare the naive wall-clock value.
    assert stored.updated_at.replace(tzinfo=None) == later.replace(tzinfo=None)
