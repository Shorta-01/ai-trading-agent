"""Task 134b — lifecycle handler fill-event tests.

Drives ``LifecycleHandler.handle_fill_event`` with a hand-built
``FillEvent`` against a real action_draft + lifecycle + executions
repo trio. Asserts:

* one ``ibkr_executions`` row written with the right Decimal
  price/quantity + the UNIQUE ``ibkr_exec_id`` enforced,
* one ``ibkr_submission_lifecycle`` row recorded with
  ``event_type="fill"``,
* the draft status transitions to ``filled`` when
  ``remaining_quantity_after == 0``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
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
from sqlalchemy.exc import IntegrityError

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


def test_full_fill_transitions_to_filled_and_writes_execution() -> None:
    conn, draft_repo, lifecycle_repo, executions_repo, handler = _setup()
    with conn:
        draft = draft_repo.get_by_id("draft-1")
        assert draft is not None
        event = FillEvent(
            perm_id=100100,
            event_at=_NOW,
            ibkr_exec_id="exec-A",
            fill_price_local=Decimal("638.72"),
            fill_quantity=Decimal("6"),
            fill_time=_NOW,
            exchange="AEB",
            raw_callback_json={"some": "callback"},
        )
        result = handler.handle_fill_event(
            draft=draft,
            event=event,
            remaining_quantity_after=Decimal("0"),
        )
        assert result.draft_status_after == "filled"
        assert result.execution_id_written == "exec-A"

        after = draft_repo.get_by_id("draft-1")
        assert after is not None
        assert after.status == "filled"
        assert after.terminal_state_at is not None

        execs = executions_repo.list_for_draft("draft-1")
        assert len(execs) == 1
        assert execs[0].fill_price_local == Decimal("638.72000000")
        assert execs[0].fill_quantity == Decimal("6")

        events = lifecycle_repo.list_for_draft("draft-1")
        assert len(events) == 1
        assert events[0].event_type == "fill"
        assert events[0].to_status == "filled"


def test_duplicate_exec_id_raises_integrity_error() -> None:
    conn, draft_repo, lifecycle_repo, executions_repo, handler = _setup()
    with conn:
        draft = draft_repo.get_by_id("draft-1")
        assert draft is not None
        event = FillEvent(
            perm_id=100100,
            event_at=_NOW,
            ibkr_exec_id="exec-DUP",
            fill_price_local=Decimal("638.72"),
            fill_quantity=Decimal("6"),
            fill_time=_NOW,
            exchange="AEB",
        )
        handler.handle_fill_event(
            draft=draft,
            event=event,
            remaining_quantity_after=Decimal("0"),
        )
        # The draft is now ``filled`` and the exec_id is unique — a
        # second fill with the same exec_id is the duplicate scenario
        # IBKR's UNIQUE constraint protects against. The handler does
        # not silence it.
        after = draft_repo.get_by_id("draft-1")
        assert after is not None
        with pytest.raises(IntegrityError):
            # We have to re-issue against the live (filled) draft —
            # the second fire is what catches the dup. In production
            # the lifecycle handler is also wrapped in a try/except
            # at the callback level; here we surface the raw exception.
            handler.handle_fill_event(
                draft=after,
                event=event,
                remaining_quantity_after=Decimal("0"),
            )
