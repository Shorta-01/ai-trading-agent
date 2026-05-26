"""Task 135b — Pass C 24h timeout escalation tests.

Pass C only touches drafts in ``awaiting_reply_timeout``. The cut-off
is a hard 24 hours measured against ``terminal_state_at`` (the moment
the draft entered timeout). Within the cut-off → no-op; beyond it →
escalation to ``requires_manual_review`` + manual_review_queue row +
reconciliation_audit row.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyManualReviewQueueRepository,
    SqlAlchemyReconciliationAuditRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.ibkr_reconciliation import (
    TIMEOUT_CUTOFF,
    run_pass_c_timeout_recovery,
)

_LATEST = "0053_reconciliation_audit_and_manual_review"
_NOW = datetime(2026, 5, 27, 12, 0, tzinfo=UTC)
_RUN_ID = "run-pass-c-001"


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


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def _seed_timeout_draft(
    conn,  # type: ignore[no-untyped-def]
    *,
    draft_id: str,
    timeout_age: timedelta,
    account_id: str = "DU1234567",
) -> None:
    """Insert a draft and walk it to ``awaiting_reply_timeout`` so its
    ``terminal_state_at`` equals ``now - timeout_age``."""

    repo = SqlAlchemyActionDraftRepository(conn, _report())
    timeout_at = _NOW - timeout_age
    repo.append(
        ActionDraftEntry(
            action_draft_id=draft_id,
            decision_package_id=None,
            forecast_run_id=None,
            created_at=timeout_at - timedelta(minutes=10),
            created_by="user",
            ibkr_account_id=account_id,
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
            status="proposed",
            last_edited_at=None,
            user_approved_at=timeout_at - timedelta(minutes=5),
            dismissed_at=None,
            deleted_at=None,
            dismissed_reason=None,
            user_note=None,
            superseded_by_decision_package_id=None,
            audit_trail_hash=f"hash-{draft_id}",
            previous_draft_hash=None,
            safe_for_submission=False,
        )
    )
    repo.update_status(
        action_draft_id=draft_id,
        new_status="user_approved",
        transition_actor="user",
        transition_at=timeout_at - timedelta(minutes=2),
    )
    repo.apply_lifecycle_transition(
        action_draft_id=draft_id,
        new_status="submitted",
        transitioned_at=timeout_at - timedelta(minutes=1),
    )
    repo.apply_lifecycle_transition(
        action_draft_id=draft_id,
        new_status="awaiting_reply_timeout",
        transitioned_at=timeout_at,
    )


def _run_pass_c(
    conn,  # type: ignore[no-untyped-def]
    *,
    account_id: str = "DU1234567",
):  # type: ignore[no-untyped-def]
    return run_pass_c_timeout_recovery(
        reconciliation_run_id=_RUN_ID,
        account_id=account_id,
        action_draft_repo=SqlAlchemyActionDraftRepository(conn, _report()),
        manual_review_repo=SqlAlchemyManualReviewQueueRepository(
            conn, _report()
        ),
        reconciliation_audit_repo=SqlAlchemyReconciliationAuditRepository(
            conn, _report()
        ),
        now_provider=lambda: _NOW,
    )


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


def test_timeout_older_than_24h_escalates_to_manual_review() -> None:
    with _conn() as conn:
        _seed_timeout_draft(
            conn, draft_id="d-old", timeout_age=timedelta(hours=25)
        )
        result = _run_pass_c(conn)
        assert result.timeouts_evaluated == 1
        assert result.escalated_to_manual_review == 1
        assert result.skipped_within_cutoff == 0
        assert result.escalated_draft_ids == ("d-old",)

        draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
        updated = draft_repo.get_by_id("d-old")
        assert updated is not None
        assert updated.status == "requires_manual_review"

        queue_repo = SqlAlchemyManualReviewQueueRepository(conn, _report())
        pending = queue_repo.list_pending_for_account("DU1234567")
        assert len(pending) == 1
        assert pending[0].action_draft_id == "d-old"
        assert pending[0].reason == "timeout_24h_no_data"

        recon_repo = SqlAlchemyReconciliationAuditRepository(conn, _report())
        rows = recon_repo.list_for_run(_RUN_ID)
        assert len(rows) == 1
        assert rows[0].divergence_type == "timeout_flagged_manual_review"
        assert rows[0].before_status == "awaiting_reply_timeout"
        assert rows[0].after_status == "requires_manual_review"


def test_timeout_under_24h_is_skipped() -> None:
    with _conn() as conn:
        _seed_timeout_draft(
            conn,
            draft_id="d-young",
            timeout_age=timedelta(hours=23, minutes=59),
        )
        result = _run_pass_c(conn)
        assert result.escalated_to_manual_review == 0
        assert result.skipped_within_cutoff == 1

        draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
        updated = draft_repo.get_by_id("d-young")
        assert updated is not None
        assert updated.status == "awaiting_reply_timeout"


def test_timeout_exactly_24h_escalates() -> None:
    """The cut-off is locked at >= 24h (Task 135 product lock §4)."""

    with _conn() as conn:
        _seed_timeout_draft(
            conn, draft_id="d-exact", timeout_age=TIMEOUT_CUTOFF
        )
        result = _run_pass_c(conn)
        assert result.escalated_to_manual_review == 1


def test_no_timeout_drafts_returns_zero() -> None:
    with _conn() as conn:
        result = _run_pass_c(conn)
        assert result.timeouts_evaluated == 0
        assert result.escalated_to_manual_review == 0


def test_mixed_old_and_young_processes_only_the_old_one() -> None:
    with _conn() as conn:
        _seed_timeout_draft(
            conn, draft_id="d-old", timeout_age=timedelta(hours=30)
        )
        _seed_timeout_draft(
            conn, draft_id="d-young", timeout_age=timedelta(hours=5)
        )
        result = _run_pass_c(conn)
        assert result.timeouts_evaluated == 2
        assert result.escalated_to_manual_review == 1
        assert result.skipped_within_cutoff == 1
        assert result.escalated_draft_ids == ("d-old",)
