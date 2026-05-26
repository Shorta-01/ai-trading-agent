"""Task 134b — lifecycle handler partial-fill tests.

A fill event with ``remaining_quantity_after > 0`` transitions the
draft to ``partially_filled`` (not ``filled``). A subsequent fill
that exhausts the remainder transitions to ``filled``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrExecutionsRepository,
    SqlAlchemyIbkrSubmissionLifecycleRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.ibkr_submission.lifecycle_handler import (
    FillEvent,
    LifecycleHandler,
)

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


def _draft(status: str = "working") -> ActionDraftEntry:
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
        status=status,
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


def _setup():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
    lifecycle_repo = SqlAlchemyIbkrSubmissionLifecycleRepository(
        conn, _report()
    )
    executions_repo = SqlAlchemyIbkrExecutionsRepository(conn, _report())
    draft_repo.append(_draft(status="working"))
    handler = LifecycleHandler(
        action_draft_repo=draft_repo,
        lifecycle_repo=lifecycle_repo,
        executions_repo=executions_repo,
    )
    return conn, draft_repo, lifecycle_repo, executions_repo, handler


def test_partial_fill_then_full_fill() -> None:
    conn, draft_repo, lifecycle_repo, executions_repo, handler = _setup()
    with conn:
        draft = draft_repo.get_by_id("draft-1")
        assert draft is not None

        # First fill: 3 of 6 shares.
        handler.handle_fill_event(
            draft=draft,
            event=FillEvent(
                perm_id=100100,
                event_at=_NOW,
                ibkr_exec_id="exec-1",
                fill_price_local=Decimal("638.72"),
                fill_quantity=Decimal("3"),
                fill_time=_NOW,
                exchange="AEB",
            ),
            remaining_quantity_after=Decimal("3"),
        )
        after_first = draft_repo.get_by_id("draft-1")
        assert after_first is not None
        assert after_first.status == "partially_filled"
        assert after_first.terminal_state_at is None

        # Second fill: remaining 3 → fills the order.
        handler.handle_fill_event(
            draft=after_first,
            event=FillEvent(
                perm_id=100100,
                event_at=_NOW + timedelta(seconds=2),
                ibkr_exec_id="exec-2",
                fill_price_local=Decimal("638.72"),
                fill_quantity=Decimal("3"),
                fill_time=_NOW + timedelta(seconds=2),
                exchange="AEB",
            ),
            remaining_quantity_after=Decimal("0"),
        )
        after_second = draft_repo.get_by_id("draft-1")
        assert after_second is not None
        assert after_second.status == "filled"
        assert after_second.terminal_state_at is not None

        # Two execution rows; total fill quantity = 6.
        execs = executions_repo.list_for_draft("draft-1")
        assert len(execs) == 2
        assert sum(e.fill_quantity for e in execs) == Decimal("6")

        # Two lifecycle rows of event_type="fill".
        events = lifecycle_repo.list_for_draft("draft-1")
        assert [e.event_type for e in events] == ["fill", "fill"]
        assert events[0].to_status == "partially_filled"
        assert events[1].to_status == "filled"
