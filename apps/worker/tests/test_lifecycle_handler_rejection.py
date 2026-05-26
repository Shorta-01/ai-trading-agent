"""Task 134b — lifecycle handler rejection-event tests.

A ``RejectionEvent`` from IBKR transitions the draft to ``rejected``
and captures the verbatim reject reason in the lifecycle row's
``raw_callback_json``. Out-of-order/late rejections (when the draft
has already moved to a non-in-flight state) are recorded but don't
mutate state.
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
    LifecycleHandler,
    RejectionEvent,
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


def _draft(status: str = "submitted") -> ActionDraftEntry:
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


def _setup(initial_status: str = "submitted"):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
    lifecycle_repo = SqlAlchemyIbkrSubmissionLifecycleRepository(
        conn, _report()
    )
    executions_repo = SqlAlchemyIbkrExecutionsRepository(conn, _report())
    draft_repo.append(_draft(status=initial_status))
    handler = LifecycleHandler(
        action_draft_repo=draft_repo,
        lifecycle_repo=lifecycle_repo,
        executions_repo=executions_repo,
    )
    return conn, draft_repo, lifecycle_repo, handler


def test_rejection_transitions_submitted_to_rejected_and_captures_reason() -> None:
    conn, draft_repo, lifecycle_repo, handler = _setup("submitted")
    with conn:
        draft = draft_repo.get_by_id("draft-1")
        assert draft is not None
        result = handler.handle_rejection_event(
            draft=draft,
            event=RejectionEvent(
                perm_id=100100,
                event_at=_NOW,
                reject_reason="Order quantity exceeds available cash.",
            ),
        )
        assert result.draft_status_after == "rejected"

        after = draft_repo.get_by_id("draft-1")
        assert after is not None
        assert after.status == "rejected"
        assert after.terminal_state_at is not None

        events = lifecycle_repo.list_for_draft("draft-1")
        assert len(events) == 1
        assert events[0].event_type == "status_change"
        assert events[0].to_status == "rejected"
        assert events[0].ibkr_raw_status == "Rejected"
        assert (
            events[0].raw_callback_json["reject_reason"]
            == "Order quantity exceeds available cash."
        )


def test_late_rejection_on_terminal_draft_logs_but_does_not_retransition() -> None:
    """If a Rejected callback arrives after the draft already moved to a
    different terminal status (e.g. cancelled), we record the event but
    don't try to apply an illegal state transition.
    """
    conn, draft_repo, lifecycle_repo, handler = _setup("submitted")
    with conn:
        # Force the draft to ``cancelled`` first via a legit transition.
        draft_repo.apply_lifecycle_transition(
            action_draft_id="draft-1",
            new_status="cancelled",
            transitioned_at=_NOW - timedelta(seconds=5),
        )
        cancelled = draft_repo.get_by_id("draft-1")
        assert cancelled is not None and cancelled.status == "cancelled"

        result = handler.handle_rejection_event(
            draft=cancelled,
            event=RejectionEvent(
                perm_id=100100,
                event_at=_NOW,
                reject_reason="late rejection arrived after cancel",
            ),
        )
        assert result.draft_status_after is None

        after = draft_repo.get_by_id("draft-1")
        assert after is not None
        # Status unchanged.
        assert after.status == "cancelled"

        events = lifecycle_repo.list_for_draft("draft-1")
        # One event with to_status=None marking the no-op record.
        assert len(events) == 1
        assert events[0].to_status is None
        assert events[0].ibkr_raw_status == "Rejected"
