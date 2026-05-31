"""Builder tests for the submission + cancel sweep wiring (execution layer 5)."""

from __future__ import annotations

from datetime import UTC, datetime

from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.ibkr_submission.ibkr_order_sweeps import (
    build_cancel_sweep,
    build_submission_sweep,
)
from portfolio_outlook_worker.single_flight_lock import InMemoryLock

# Thursday 12:00 UTC — inside the Brussels weekday market window.
_NOW = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)


def _report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id="0066_asset_suggestions_grid_columns",
        database_revision_id="0066_asset_suggestions_grid_columns",
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="test",
    )


class _FakeGateway:
    def is_connected(self) -> bool:
        return True

    def get_account_mode(self) -> str:
        return "paper"

    @property
    def account_id(self) -> str | None:
        return "DU1234567"


class _FakeAdapter:
    """Satisfies IbkrSubmitProtocol shape; never called with no drafts."""

    gateway_session_id = "s"
    account_mode = "paper"

    def fetch_managed_account_id(self) -> str:
        return "DU1234567"

    def fetch_tick_size(self, **kwargs: object) -> object:  # pragma: no cover
        raise AssertionError("not expected with no drafts")

    def place_order(self, contract: object, order: object) -> object:  # pragma: no cover
        raise AssertionError("not expected with no drafts")

    def cancel_order(self, perm_id: int) -> None:  # pragma: no cover
        raise AssertionError("not expected with no drafts")


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def test_build_submission_sweep_constructs_and_ticks() -> None:
    with _conn() as conn:
        sweep = build_submission_sweep(
            connection=conn,
            readiness=_report(),
            gateway=_FakeGateway(),
            order_adapter=_FakeAdapter(),
            ibkr_account_id="DU1234567",
            lock=InMemoryLock(),
            now_provider=lambda: _NOW,
        )
        result = sweep.tick()
    # No approved drafts seeded -> the wired sweep runs cleanly to no_drafts.
    assert result.mode == "no_drafts"


def test_build_cancel_sweep_constructs_and_ticks() -> None:
    with _conn() as conn:
        sweep = build_cancel_sweep(
            connection=conn,
            readiness=_report(),
            order_adapter=_FakeAdapter(),
            ibkr_account_id="DU1234567",
            lock=InMemoryLock(),
            now_provider=lambda: _NOW,
        )
        result = sweep.tick()
    assert result.mode == "no_drafts"
