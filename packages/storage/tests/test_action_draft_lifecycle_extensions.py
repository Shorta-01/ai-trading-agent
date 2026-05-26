"""Task 134b — action_draft repository lifecycle extensions.

Verifies the three new methods added in 134b:

* ``apply_lifecycle_transition`` — drives user_approved → submitted →
  accepted → working → filled, setting ``submission_started_at`` +
  ``terminal_state_at`` along the way and NOT writing an
  ``action_draft_audit`` row (lifecycle has its own audit table).
* ``set_submission_block_reason`` — sets the badge reason without
  changing status; rejects non-user_approved drafts.
* ``list_in_flight_for_conid`` / ``list_user_approved_for_sweep`` —
  the FIFO + duplicate-detection helpers the sweep relies on.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    ActionDraftEntry,
    ActionDraftStateTransitionError,
    SqlAlchemyActionDraftAuditRepository,
    SqlAlchemyActionDraftRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)

_LATEST = "0052_ibkr_submission_lifecycle_audit_and_executions"
_BASE_TS = datetime(2026, 5, 26, 10, 0, tzinfo=UTC)


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


def _draft(
    *,
    draft_id: str = "draft-1",
    status: str = "user_approved",
    conid: str = "12345",
    account_id: str = "DU1234567",
    user_approved_at: datetime | None = None,
    audit_trail_hash: str | None = None,
) -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id=draft_id,
        decision_package_id=None,
        forecast_run_id=None,
        created_at=_BASE_TS - timedelta(minutes=10),
        created_by="user",
        ibkr_account_id=account_id,
        conid=conid,
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
        user_approved_at=user_approved_at or _BASE_TS - timedelta(minutes=5),
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=None,
        superseded_by_decision_package_id=None,
        audit_trail_hash=audit_trail_hash or f"h-{draft_id}",
        previous_draft_hash=None,
        safe_for_submission=False,
    )


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def test_apply_lifecycle_transition_drives_full_state_machine() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        audit_repo = SqlAlchemyActionDraftAuditRepository(conn, _report())
        repo.append(_draft())
        # Initial audit row (created) — record count before lifecycle.
        before = audit_repo.list_for_draft("draft-1")
        assert len(before) == 1

        # user_approved → submitted.
        submitted = repo.apply_lifecycle_transition(
            action_draft_id="draft-1",
            new_status="submitted",
            transitioned_at=_BASE_TS,
        )
        assert submitted.status == "submitted"
        assert submitted.submission_started_at is not None

        # submitted → accepted → working → filled.
        repo.apply_lifecycle_transition(
            action_draft_id="draft-1",
            new_status="accepted",
            transitioned_at=_BASE_TS + timedelta(seconds=1),
        )
        repo.apply_lifecycle_transition(
            action_draft_id="draft-1",
            new_status="working",
            transitioned_at=_BASE_TS + timedelta(seconds=2),
        )
        filled = repo.apply_lifecycle_transition(
            action_draft_id="draft-1",
            new_status="filled",
            transitioned_at=_BASE_TS + timedelta(seconds=5),
        )
        assert filled.status == "filled"
        assert filled.terminal_state_at is not None

        # action_draft_audit must NOT have grown — lifecycle has its
        # own audit table (ibkr_submission_lifecycle).
        after = audit_repo.list_for_draft("draft-1")
        assert len(after) == 1


def test_apply_lifecycle_transition_rejects_illegal_transition() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft())
        # user_approved → filled is not allowed (skips lifecycle).
        with pytest.raises(ActionDraftStateTransitionError):
            repo.apply_lifecycle_transition(
                action_draft_id="draft-1",
                new_status="filled",
                transitioned_at=_BASE_TS,
            )


def test_apply_lifecycle_transition_clears_block_reason_on_submitted() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft())
        repo.set_submission_block_reason(
            action_draft_id="draft-1",
            reason="cooldown",
            set_at=_BASE_TS - timedelta(seconds=30),
        )
        before = repo.get_by_id("draft-1")
        assert before is not None
        assert before.submission_block_reason == "cooldown"
        repo.apply_lifecycle_transition(
            action_draft_id="draft-1",
            new_status="submitted",
            transitioned_at=_BASE_TS,
        )
        after = repo.get_by_id("draft-1")
        assert after is not None
        assert after.submission_block_reason is None


def test_set_submission_block_reason_rejects_non_user_approved() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        repo.append(_draft(status="proposed"))
        with pytest.raises(ActionDraftStateTransitionError):
            repo.set_submission_block_reason(
                action_draft_id="draft-1",
                reason="cooldown",
                set_at=_BASE_TS,
            )


def test_list_user_approved_for_sweep_orders_by_user_approved_at() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        # Older approval first
        repo.append(
            _draft(
                draft_id="d-old",
                audit_trail_hash="h-old",
                user_approved_at=_BASE_TS - timedelta(hours=2),
            )
        )
        repo.append(
            _draft(
                draft_id="d-new",
                audit_trail_hash="h-new",
                user_approved_at=_BASE_TS - timedelta(minutes=5),
            )
        )
        rows = repo.list_user_approved_for_sweep(
            ibkr_account_id="DU1234567"
        )
        assert [d.action_draft_id for d in rows] == ["d-old", "d-new"]


def test_list_in_flight_for_conid_filters_by_lifecycle_states() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        # Various states; only the in-flight ones must be returned.
        repo.append(_draft(draft_id="d-user", status="user_approved", audit_trail_hash="h1"))
        repo.append(_draft(draft_id="d-sub", status="submitted", audit_trail_hash="h2"))
        repo.append(_draft(draft_id="d-acc", status="accepted", audit_trail_hash="h3"))
        repo.append(_draft(draft_id="d-work", status="working", audit_trail_hash="h4"))
        repo.append(_draft(draft_id="d-pf", status="partially_filled", audit_trail_hash="h5"))
        repo.append(_draft(draft_id="d-pc", status="pending_cancellation", audit_trail_hash="h6"))
        repo.append(_draft(draft_id="d-filled", status="filled", audit_trail_hash="h7"))
        repo.append(_draft(draft_id="d-cancel", status="cancelled", audit_trail_hash="h8"))

        rows = repo.list_in_flight_for_conid(
            ibkr_account_id="DU1234567", conid="12345"
        )
        ids = {d.action_draft_id for d in rows}
        assert ids == {"d-sub", "d-acc", "d-work", "d-pf", "d-pc"}
