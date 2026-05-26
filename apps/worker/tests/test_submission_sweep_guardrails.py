"""Task 134b — sweep-level guardrail integration tests.

The per-gate logic + Dutch wording is exhaustively covered by
``test_safety_recheck_gates`` (Task 134a). These tests assert that
the **sweep** correctly threads the guardrail context through to
``evaluate_submission_gates`` and writes the right
``submission_block_reason`` on the draft — one test per guardrail
(cooldown / daily_limit / soft_drawdown / hard_drawdown / FOMO).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSubmissionAuditEntry,
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


def _draft(side: str = "BUY") -> ActionDraftEntry:
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
        side=side,
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

    def fetch_tick_size(self, **kwargs: Any) -> TickSize:
        return TickSize(tick_size_local=Decimal("0.005"))

    def place_order(self, contract: Any, order: Any) -> SubmittedTrade:
        return SubmittedTrade(
            perm_id=200200,
            order_id=2,
            contract_dict={},
            order_dict={},
        )

    def cancel_order(self, perm_id: int) -> None:  # pragma: no cover
        raise NotImplementedError


class _StaticGateway:
    def snapshot(self) -> GatewaySnapshot:
        return GatewaySnapshot(
            connected=True, account_id="DU1234567", account_mode="paper"
        )


class _Cash:
    def __init__(self, *, position_quantity: Decimal | None = None) -> None:
        self._pos_qty = position_quantity

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
    def __init__(self, qty: Decimal | None = None) -> None:
        self._qty = qty

    def get_latest_position_snapshot_for_conid(
        self, *, ibkr_account_id: str, conid: str
    ) -> IbkrPositionSnapshotRecord | None:
        if self._qty is None:
            return None
        return IbkrPositionSnapshotRecord(
            snapshot_id="pos-1",
            sync_run_id="sync-1",
            account_ref=ibkr_account_id,
            conid=conid,
            symbol="ASML",
            security_type="STK",
            currency="EUR",
            exchange="AEB",
            primary_exchange="AEB",
            quantity=self._qty,
            average_cost=Decimal("500"),
            received_at=_NOW,
            stored_at=_NOW,
            ibkr_account_id=ibkr_account_id,
        )


class _DrawdownProvider:
    def __init__(
        self,
        *,
        soft: Decimal | None = Decimal("0"),
        hard: Decimal | None = Decimal("0"),
    ) -> None:
        self._soft = soft
        self._hard = hard

    def for_account(self, *, ibkr_account_id: str) -> DrawdownContext:
        return DrawdownContext(
            soft_loss_pct=self._soft, hard_loss_pct=self._hard
        )


class _FomoProvider:
    def __init__(self, current_price: Decimal | None = None) -> None:
        self._current = current_price

    def for_draft(self, *, draft: ActionDraftEntry) -> FomoContext:
        return FomoContext(current_price_local=self._current)


def _build_sweep(
    *,
    conn,
    side: str = "BUY",
    drawdown: _DrawdownProvider | None = None,
    fomo: _FomoProvider | None = None,
    position: _PositionProvider | None = None,
    seed_audit_rows: tuple[IbkrSubmissionAuditEntry, ...] = (),
) -> tuple[SubmissionSweep, SqlAlchemyActionDraftRepository]:
    draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
    audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(conn, _report())
    guardrail_repo = SqlAlchemyBehaviouralGuardrailSettingsRepository(
        conn, _report()
    )
    draft_repo.append(_draft(side=side))
    for row in seed_audit_rows:
        audit_repo.append(row)
    submitter = IbkrSubmitter(
        submit_adapter=_FakeAdapter(),
        action_draft_repo=draft_repo,
        audit_repo=audit_repo,
        now_provider=lambda: _NOW,
    )
    sweep = SubmissionSweep(
        ibkr_account_id="DU1234567",
        lock=InMemoryLock(),
        action_draft_repo=draft_repo,
        audit_repo=audit_repo,
        guardrail_repo=guardrail_repo,
        submitter=submitter,
        gateway_snapshot_provider=_StaticGateway(),
        cash_snapshot_provider=_Cash(),
        position_snapshot_provider=position or _PositionProvider(),
        drawdown_provider=drawdown or _DrawdownProvider(),
        fomo_provider=fomo or _FomoProvider(),
        market_hours=_AlwaysOpenMarket(),
        now_provider=lambda: _NOW,
    )
    return sweep, draft_repo


def _audit_placed_at(
    at: datetime, *, perm_id: int
) -> IbkrSubmissionAuditEntry:
    return IbkrSubmissionAuditEntry(
        action_draft_id=f"prev-{perm_id}",
        submitted_at=at,
        sent_to_account_id="DU1234567",
        sent_account_mode="paper",
        ibkr_perm_id=perm_id,
        ibkr_order_id=perm_id,
        contract_json={"symbol": "ASML"},
        order_json={"action": "BUY"},
        gateway_session_id="sess-prev",
        result="placed",
        error_class=None,
        error_message_dutch=None,
    )


# ---- cooldown ----------------------------------------------------------


def test_cooldown_blocks_when_previous_submission_within_window() -> None:
    """A placed submission 30 seconds ago → cooldown (default 60s) blocks
    the next sweep tick.
    """
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        # Seed a fake recent submission audit row to trip the cooldown.
        # We can't FK it to a draft (audit table refs action_drafts),
        # so just insert a stub draft + audit chain pair. The sweep
        # gates only inspect the audit row's account_id + result +
        # submitted_at.
        # Use the dedicated draft repo to append the prev draft first.
        prev_audit = _audit_placed_at(
            _NOW - timedelta(seconds=30), perm_id=1
        )
        # Build a prerequisite draft that satisfies the FK constraint.
        draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
        prev_draft = ActionDraftEntry(
            action_draft_id="prev-1",
            decision_package_id=None,
            forecast_run_id=None,
            created_at=_NOW - timedelta(minutes=2),
            created_by="user",
            ibkr_account_id="DU1234567",
            conid="12345",
            symbol="ASML",
            exchange="AEB",
            currency_local="EUR",
            side="BUY",
            quantity=Decimal("1"),
            order_type="LMT",
            limit_price_local=Decimal("100"),
            time_in_force="DAY",
            notional_local=Decimal("100"),
            notional_eur=Decimal("100"),
            fx_rate_at_creation=Decimal("1"),
            usable_cash_eur_at_creation=Decimal("50000"),
            held_quantity_at_creation=None,
            status="user_approved",
            last_edited_at=None,
            user_approved_at=_NOW - timedelta(minutes=2),
            dismissed_at=None,
            deleted_at=None,
            dismissed_reason=None,
            user_note=None,
            superseded_by_decision_package_id=None,
            audit_trail_hash="prev-h",
            previous_draft_hash=None,
            safe_for_submission=False,
        )
        draft_repo.append(prev_draft)

        # Now seed the audit row and build the sweep around the
        # second user_approved draft.
        audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(
            conn, _report()
        )
        audit_repo.append(prev_audit)
        draft_repo.append(_draft())
        guardrail_repo = SqlAlchemyBehaviouralGuardrailSettingsRepository(
            conn, _report()
        )
        submitter = IbkrSubmitter(
            submit_adapter=_FakeAdapter(),
            action_draft_repo=draft_repo,
            audit_repo=audit_repo,
            now_provider=lambda: _NOW,
        )
        sweep = SubmissionSweep(
            ibkr_account_id="DU1234567",
            lock=InMemoryLock(),
            action_draft_repo=draft_repo,
            audit_repo=audit_repo,
            guardrail_repo=guardrail_repo,
            submitter=submitter,
            gateway_snapshot_provider=_StaticGateway(),
            cash_snapshot_provider=_Cash(),
            position_snapshot_provider=_PositionProvider(),
            drawdown_provider=_DrawdownProvider(),
            fomo_provider=_FomoProvider(),
            market_hours=_AlwaysOpenMarket(),
            now_provider=lambda: _NOW,
        )
        result = sweep.tick()
        # FIFO: the older draft (prev-1) is processed first and gets
        # blocked by cooldown. The newer draft-1 isn't touched (the
        # sweep stops after the first eligible draft).
        assert result.mode == "completed"
        assert result.submitted == ()
        assert any(
            b.block_reason == "cooldown" for b in result.blocked
        )


# ---- daily_limit -------------------------------------------------------


def test_daily_limit_blocks_after_five_submissions_in_24h() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        # Seed 5 prior placed audit rows + their stub drafts.
        draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
        audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(
            conn, _report()
        )
        for index in range(5):
            stub_draft = ActionDraftEntry(
                action_draft_id=f"prev-{index}",
                decision_package_id=None,
                forecast_run_id=None,
                created_at=_NOW - timedelta(hours=12 - index),
                created_by="user",
                ibkr_account_id="DU1234567",
                conid="12345",
                symbol="ASML",
                exchange="AEB",
                currency_local="EUR",
                side="BUY",
                quantity=Decimal("1"),
                order_type="LMT",
                limit_price_local=Decimal("100"),
                time_in_force="DAY",
                notional_local=Decimal("100"),
                notional_eur=Decimal("100"),
                fx_rate_at_creation=Decimal("1"),
                usable_cash_eur_at_creation=Decimal("50000"),
                held_quantity_at_creation=None,
                status="user_approved",
                last_edited_at=None,
                user_approved_at=_NOW - timedelta(hours=12 - index),
                dismissed_at=None,
                deleted_at=None,
                dismissed_reason=None,
                user_note=None,
                superseded_by_decision_package_id=None,
                audit_trail_hash=f"prev-h-{index}",
                previous_draft_hash=None,
                safe_for_submission=False,
            )
            draft_repo.append(stub_draft)
            audit_repo.append(
                IbkrSubmissionAuditEntry(
                    action_draft_id=f"prev-{index}",
                    submitted_at=_NOW - timedelta(hours=10 - index),
                    sent_to_account_id="DU1234567",
                    sent_account_mode="paper",
                    ibkr_perm_id=100 + index,
                    ibkr_order_id=100 + index,
                    contract_json={"symbol": "ASML"},
                    order_json={"action": "BUY"},
                    gateway_session_id="sess-prev",
                    result="placed",
                    error_class=None,
                    error_message_dutch=None,
                )
            )
        # Now the 6th draft.
        draft_repo.append(_draft())
        guardrail_repo = SqlAlchemyBehaviouralGuardrailSettingsRepository(
            conn, _report()
        )
        submitter = IbkrSubmitter(
            submit_adapter=_FakeAdapter(),
            action_draft_repo=draft_repo,
            audit_repo=audit_repo,
            now_provider=lambda: _NOW,
        )
        sweep = SubmissionSweep(
            ibkr_account_id="DU1234567",
            lock=InMemoryLock(),
            action_draft_repo=draft_repo,
            audit_repo=audit_repo,
            guardrail_repo=guardrail_repo,
            submitter=submitter,
            gateway_snapshot_provider=_StaticGateway(),
            cash_snapshot_provider=_Cash(),
            position_snapshot_provider=_PositionProvider(),
            drawdown_provider=_DrawdownProvider(),
            fomo_provider=_FomoProvider(),
            market_hours=_AlwaysOpenMarket(),
            now_provider=lambda: _NOW,
        )
        result = sweep.tick()
        assert result.mode == "completed"
        # All six (5 prev + 1 new) are user_approved; the sweep stops
        # after the first blocked submission.
        assert result.submitted == ()
        assert any(
            b.block_reason == "daily_limit" for b in result.blocked
        )


# ---- soft drawdown ------------------------------------------------------


def test_soft_drawdown_blocks_buy() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        sweep, draft_repo = _build_sweep(
            conn=conn,
            side="BUY",
            drawdown=_DrawdownProvider(
                soft=Decimal("-6"), hard=Decimal("-2")
            ),
        )
        result = sweep.tick()
        assert any(
            b.block_reason == "soft_drawdown" for b in result.blocked
        )
        # And the draft now carries the badge reason.
        after = draft_repo.get_by_id("draft-1")
        assert after is not None
        assert after.submission_block_reason == "soft_drawdown"


def test_soft_drawdown_allows_sell() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        # SELL needs a held position to satisfy cash/position gate.
        sweep, _ = _build_sweep(
            conn=conn,
            side="SELL",
            drawdown=_DrawdownProvider(
                soft=Decimal("-6"), hard=Decimal("-2")
            ),
            position=_PositionProvider(Decimal("100")),
        )
        result = sweep.tick()
        assert any(
            s.action_draft_id == "draft-1" for s in result.submitted
        )


# ---- hard drawdown ------------------------------------------------------


def test_hard_drawdown_blocks_all_sides() -> None:
    for side in ("BUY", "SELL"):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        with engine.connect() as conn:
            metadata.create_all(conn)
            sweep, _ = _build_sweep(
                conn=conn,
                side=side,
                drawdown=_DrawdownProvider(
                    soft=Decimal("-2"), hard=Decimal("-11")
                ),
                position=_PositionProvider(Decimal("100"))
                if side == "SELL"
                else None,
            )
            result = sweep.tick()
            assert any(
                b.block_reason == "hard_drawdown" for b in result.blocked
            ), f"side={side}"


# ---- FOMO -------------------------------------------------------------


def test_fomo_blocks_when_market_price_drifted_past_threshold() -> None:
    """Approved at 638.72; current market 660 → ~3.3% above the 1.5%
    locked default threshold."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        sweep, draft_repo = _build_sweep(
            conn=conn,
            side="BUY",
            fomo=_FomoProvider(Decimal("660")),
        )
        result = sweep.tick()
        assert any(b.block_reason == "fomo" for b in result.blocked)
        after = draft_repo.get_by_id("draft-1")
        assert after is not None
        assert after.submission_block_reason == "fomo"
