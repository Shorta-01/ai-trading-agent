"""Task 134b — submission sweep market-hours gate.

Outside Brussels business hours (09:00-22:30 weekdays) the sweep
short-circuits with ``mode="skipped_market_closed"`` and writes no
audit rows. Tests use a fixed ``now_provider`` to drive the clock.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyBehaviouralGuardrailSettingsRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.ibkr_submission.order_builder import TickSize
from portfolio_outlook_worker.ibkr_submission.safety_recheck import (
    DrawdownContext,
    FomoContext,
    GatewaySnapshot,
)
from portfolio_outlook_worker.ibkr_submission.submission_sweep import (
    BrusselsBusinessHoursMarket,
    SubmissionSweep,
)
from portfolio_outlook_worker.ibkr_submission.submitter import (
    IbkrSubmitter,
    SubmittedTrade,
)
from portfolio_outlook_worker.single_flight_lock import InMemoryLock

_LATEST = "0052_ibkr_submission_lifecycle_audit_and_executions"


def _report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id=_LATEST,
        database_revision_id=_LATEST,
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="test",
    )


def _draft(now: datetime) -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id="draft-1",
        decision_package_id=None,
        forecast_run_id=None,
        created_at=now - timedelta(minutes=10),
        created_by="user",
        ibkr_account_id="DU1234567",
        conid="12345",
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        side="BUY",
        quantity=Decimal("6"),
        order_type="LMT",
        limit_price_local=Decimal("638.72"),
        time_in_force="DAY",
        notional_local=Decimal("3832.32"),
        notional_eur=Decimal("3832.32"),
        fx_rate_at_creation=Decimal("1"),
        usable_cash_eur_at_creation=Decimal("50000"),
        held_quantity_at_creation=None,
        status="user_approved",
        last_edited_at=None,
        user_approved_at=now - timedelta(minutes=5),
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=None,
        superseded_by_decision_package_id=None,
        audit_trail_hash="h-1",
        previous_draft_hash=None,
        safe_for_submission=False,
    )


class _FakeAdapter:
    gateway_session_id = "sess-1"
    account_mode: Literal["paper", "live"] = "paper"

    def fetch_managed_account_id(self) -> str:
        return "DU1234567"

    def fetch_tick_size(self, **kwargs: Any) -> TickSize:
        return TickSize(tick_size_local=Decimal("0.005"))

    def place_order(self, contract: Any, order: Any) -> SubmittedTrade:
        return SubmittedTrade(
            perm_id=100100,
            order_id=1,
            contract_dict={},
            order_dict={},
        )

    def cancel_order(self, perm_id: int) -> None:  # pragma: no cover
        raise NotImplementedError


class _Gateway:
    def snapshot(self) -> GatewaySnapshot:
        return GatewaySnapshot(
            connected=True, account_id="DU1234567", account_mode="paper"
        )


class _Cash:
    def get_latest_account_cash_snapshot(
        self, *, ibkr_account_id: str
    ) -> IbkrAccountCashSnapshotRecord:
        return IbkrAccountCashSnapshotRecord(
            snapshot_id="cash-1",
            sync_run_id="sync-1",
            account_ref=ibkr_account_id,
            base_currency="EUR",
            cash=Decimal("50000"),
            available_funds=Decimal("50000"),
            buying_power=Decimal("50000"),
            received_at=datetime(2026, 5, 26, 0, 0, tzinfo=UTC),
            stored_at=datetime(2026, 5, 26, 0, 0, tzinfo=UTC),
            ibkr_account_id=ibkr_account_id,
        )


class _Position:
    def get_latest_position_snapshot_for_conid(
        self, *, ibkr_account_id: str, conid: str
    ) -> IbkrPositionSnapshotRecord | None:
        return None


class _Drawdown:
    def for_account(self, *, ibkr_account_id: str) -> DrawdownContext:
        return DrawdownContext(
            soft_loss_pct=Decimal("0"), hard_loss_pct=Decimal("0")
        )


class _Fomo:
    def for_draft(self, *, draft: ActionDraftEntry) -> FomoContext:
        return FomoContext(current_price_local=None)


def _build_sweep(*, conn, now: datetime) -> SubmissionSweep:
    draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
    audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(conn, _report())
    guardrail_repo = SqlAlchemyBehaviouralGuardrailSettingsRepository(
        conn, _report()
    )
    draft_repo.append(_draft(now=now))
    submitter = IbkrSubmitter(
        submit_adapter=_FakeAdapter(),
        action_draft_repo=draft_repo,
        audit_repo=audit_repo,
        now_provider=lambda: now,
    )
    return SubmissionSweep(
        ibkr_account_id="DU1234567",
        lock=InMemoryLock(),
        action_draft_repo=draft_repo,
        audit_repo=audit_repo,
        guardrail_repo=guardrail_repo,
        submitter=submitter,
        gateway_snapshot_provider=_Gateway(),
        cash_snapshot_provider=_Cash(),
        position_snapshot_provider=_Position(),
        drawdown_provider=_Drawdown(),
        fomo_provider=_Fomo(),
        market_hours=BrusselsBusinessHoursMarket(),
        now_provider=lambda: now,
    )


def test_sweep_at_03_00_skips_market_closed() -> None:
    """03:00 UTC on a Tuesday — well before 09:00 → market closed."""
    now = datetime(2026, 5, 26, 3, 0, tzinfo=UTC)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        sweep = _build_sweep(conn=conn, now=now)
        result = sweep.tick()
        assert result.mode == "skipped_market_closed"
        assert result.evaluated_count == 0
        assert result.submitted == ()


def test_sweep_on_saturday_skips_market_closed() -> None:
    """Saturday at 11:00 → market closed regardless of hour."""
    now = datetime(2026, 5, 30, 11, 0, tzinfo=UTC)  # 2026-05-30 is Saturday
    assert now.weekday() == 5  # double-check the fixture
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        sweep = _build_sweep(conn=conn, now=now)
        result = sweep.tick()
        assert result.mode == "skipped_market_closed"


def test_sweep_at_11_00_weekday_runs() -> None:
    """11:00 UTC on a Tuesday → market open, sweep proceeds."""
    now = datetime(2026, 5, 26, 11, 0, tzinfo=UTC)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        sweep = _build_sweep(conn=conn, now=now)
        result = sweep.tick()
        assert result.mode == "completed"
        assert result.evaluated_count == 1
        assert len(result.submitted) == 1
