"""Task 134b — submission sweep single-flight semantics.

Two concurrent sweep invocations against the same lock — only the
first runs; the second returns ``SubmissionSweepResult(mode="skipped_locked")``.
The first-holder commits and then releases so a subsequent tick
proceeds normally.
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
    MarketHoursProviderProtocol,
)
from portfolio_outlook_worker.ibkr_submission.submission_sweep import (
    SubmissionSweep,
)
from portfolio_outlook_worker.ibkr_submission.submitter import (
    IbkrSubmitter,
    SubmittedTrade,
)
from portfolio_outlook_worker.single_flight_lock import InMemoryLock

_LATEST = "0052_ibkr_submission_lifecycle_audit_and_executions"
_NOW = datetime(2026, 5, 26, 10, 0, tzinfo=UTC)


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


def _draft() -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id="draft-1",
        decision_package_id=None,
        forecast_run_id=None,
        created_at=_NOW - timedelta(minutes=10),
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
        user_approved_at=_NOW - timedelta(minutes=5),
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=None,
        superseded_by_decision_package_id=None,
        audit_trail_hash="h-1",
        previous_draft_hash=None,
        safe_for_submission=False,
    )


class _AlwaysOpenMarket(MarketHoursProviderProtocol):
    def is_open(self, *, exchange: str, now: datetime) -> bool:
        return True


class _FakeAdapter:
    gateway_session_id = "sess-1"
    account_mode: Literal["paper", "live"] = "paper"

    def fetch_managed_account_id(self) -> str:
        return "DU1234567"

    def fetch_tick_size(
        self, *, symbol: str, exchange: str, currency: str, conid: int | None
    ) -> TickSize:
        return TickSize(tick_size_local=Decimal("0.005"))

    def place_order(self, contract: Any, order: Any) -> SubmittedTrade:
        return SubmittedTrade(
            perm_id=100100,
            order_id=1,
            contract_dict={"symbol": "ASML"},
            order_dict={"action": "BUY"},
        )

    def cancel_order(self, perm_id: int) -> None:  # pragma: no cover
        raise NotImplementedError


class _StaticGateway:
    def snapshot(self) -> GatewaySnapshot:
        return GatewaySnapshot(
            connected=True, account_id="DU1234567", account_mode="paper"
        )


class _CashProvider:
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
            received_at=_NOW,
            stored_at=_NOW,
            ibkr_account_id=ibkr_account_id,
        )


class _PositionProvider:
    def get_latest_position_snapshot_for_conid(
        self, *, ibkr_account_id: str, conid: str
    ) -> IbkrPositionSnapshotRecord | None:
        return None


class _NoDrawdown:
    def for_account(self, *, ibkr_account_id: str) -> DrawdownContext:
        # None values → conservative block; for the happy-path sweep
        # use safe non-loss values.
        return DrawdownContext(
            soft_loss_pct=Decimal("0"), hard_loss_pct=Decimal("0")
        )


class _NoFomo:
    def for_draft(self, *, draft: ActionDraftEntry) -> FomoContext:
        return FomoContext(current_price_local=None)


def _build_sweep(*, conn, lock: InMemoryLock) -> SubmissionSweep:
    draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
    audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(conn, _report())
    guardrail_repo = SqlAlchemyBehaviouralGuardrailSettingsRepository(
        conn, _report()
    )
    draft_repo.append(_draft())
    submitter = IbkrSubmitter(
        submit_adapter=_FakeAdapter(),
        action_draft_repo=draft_repo,
        audit_repo=audit_repo,
        now_provider=lambda: _NOW,
    )
    return SubmissionSweep(
        ibkr_account_id="DU1234567",
        lock=lock,
        action_draft_repo=draft_repo,
        audit_repo=audit_repo,
        guardrail_repo=guardrail_repo,
        submitter=submitter,
        gateway_snapshot_provider=_StaticGateway(),
        cash_snapshot_provider=_CashProvider(),
        position_snapshot_provider=_PositionProvider(),
        drawdown_provider=_NoDrawdown(),
        fomo_provider=_NoFomo(),
        market_hours=_AlwaysOpenMarket(),
        now_provider=lambda: _NOW,
    )


def test_second_concurrent_tick_skips_with_locked_mode() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        lock = InMemoryLock()

        # Grab the lock externally so the sweep can't.
        assert lock.try_acquire() is True
        sweep = _build_sweep(conn=conn, lock=lock)
        result = sweep.tick()
        assert result.mode == "skipped_locked"
        assert result.evaluated_count == 0
        assert result.submitted == ()

        # Release and try again — now the sweep gets the lock and
        # processes the one user_approved draft.
        lock.release()
        result2 = sweep.tick()
        assert result2.mode == "completed"
        assert result2.evaluated_count == 1
        assert len(result2.submitted) == 1
        assert result2.submitted[0].action_draft_id == "draft-1"


def test_lock_released_after_successful_tick() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        lock = InMemoryLock()
        sweep = _build_sweep(conn=conn, lock=lock)
        sweep.tick()
        # A subsequent acquire must succeed.
        assert lock.try_acquire() is True
        lock.release()
