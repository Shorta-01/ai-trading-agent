"""Task 135b — IbkrReconciler orchestrator tests.

Covers the locked tick contract: single-flight lock, gateway-connected
short-circuit, fixed pass ordering (A → B → C), one
``reconciliation_run_audit`` row per tick, and exception-capture-not-
through behaviour.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    IbkrSubmissionAuditEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrExecutionsRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
    SqlAlchemyManualReviewQueueRepository,
    SqlAlchemyReconciliationAuditRepository,
    SqlAlchemyReconciliationRunAuditRepository,
    SqlAlchemyUnmatchedExecutionAuditRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.ibkr_reconciliation import (
    IbkrExecutionForReconciliation,
    IbkrOrderStatusForReconciliation,
    IbkrReconciler,
)
from portfolio_outlook_worker.single_flight_lock import InMemoryLock

_LATEST = "0053_reconciliation_audit_and_manual_review"
_NOW = datetime(2026, 5, 27, 12, 0, tzinfo=UTC)


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


class _Gateway:
    def __init__(self, connected: bool = True) -> None:
        self.connected = connected

    def is_connected(self) -> bool:
        return self.connected


class _NoFillsFetcher:
    def fetch_recent_executions(
        self, *, account_id: str
    ) -> tuple[IbkrExecutionForReconciliation, ...]:
        _ = account_id
        return ()


class _NoStatusFetcher:
    def fetch_order_status(
        self, *, ibkr_perm_id: int, account_id: str
    ) -> IbkrOrderStatusForReconciliation:
        _ = (ibkr_perm_id, account_id)
        return IbkrOrderStatusForReconciliation(
            ibkr_perm_id=ibkr_perm_id,
            found_in_ibkr=False,
            ibkr_raw_status=None,
            raw_payload={},
        )


def _build_reconciler(
    conn,  # type: ignore[no-untyped-def]
    *,
    execution_fetcher=None,  # type: ignore[no-untyped-def]
    order_status_fetcher=None,  # type: ignore[no-untyped-def]
    gateway: _Gateway | None = None,
    lock: InMemoryLock | None = None,
    now_value: datetime = _NOW,
) -> IbkrReconciler:
    return IbkrReconciler(
        ibkr_account_id="DU1234567",
        lock=lock or InMemoryLock(),
        gateway=gateway or _Gateway(connected=True),
        execution_fetcher=execution_fetcher or _NoFillsFetcher(),
        order_status_fetcher=order_status_fetcher or _NoStatusFetcher(),
        action_draft_repo=SqlAlchemyActionDraftRepository(conn, _report()),
        executions_repo=SqlAlchemyIbkrExecutionsRepository(conn, _report()),
        submission_audit_repo=SqlAlchemyIbkrSubmissionAuditRepository(
            conn, _report()
        ),
        unmatched_repo=SqlAlchemyUnmatchedExecutionAuditRepository(
            conn, _report()
        ),
        manual_review_repo=SqlAlchemyManualReviewQueueRepository(
            conn, _report()
        ),
        reconciliation_audit_repo=SqlAlchemyReconciliationAuditRepository(
            conn, _report()
        ),
        run_audit_repo=SqlAlchemyReconciliationRunAuditRepository(
            conn, _report()
        ),
        now_provider=lambda: now_value,
        run_id_factory=lambda: "fixed-run-id",
    )


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


def test_empty_database_runs_three_passes_with_zero_divergences() -> None:
    with _conn() as conn:
        reconciler = _build_reconciler(conn)
        result = reconciler.tick()
        assert result.mode_detected == "completed"
        assert result.divergences_found == 0
        assert result.pass_a_result is not None
        assert result.pass_b_result is not None
        assert result.pass_c_result is not None

        # Run audit row exists + is completed.
        run_repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        latest = run_repo.get_latest_for_account("DU1234567")
        assert latest is not None
        assert latest.reconciliation_run_id == "fixed-run-id"
        assert latest.completed_at is not None
        assert latest.mode_detected == "completed"


def test_skipped_locked_when_another_holder_owns_lock() -> None:
    with _conn() as conn:
        lock = InMemoryLock()
        assert lock.try_acquire() is True  # external holder
        reconciler = _build_reconciler(conn, lock=lock)
        result = reconciler.tick()
        assert result.mode_detected == "skipped_locked"
        assert result.divergences_found == 0
        # No run audit row should have been written for a locked tick.
        run_repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        assert run_repo.get_latest_for_account("DU1234567") is None


def test_skipped_disconnected_short_circuits_passes() -> None:
    with _conn() as conn:
        reconciler = _build_reconciler(
            conn, gateway=_Gateway(connected=False)
        )
        result = reconciler.tick()
        assert result.mode_detected == "skipped_disconnected"
        assert result.pass_a_result is None
        assert result.pass_b_result is None
        assert result.pass_c_result is None

        run_repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        latest = run_repo.get_latest_for_account("DU1234567")
        assert latest is not None
        assert latest.mode_detected == "skipped_disconnected"
        assert latest.completed_at is not None


def test_pass_a_exception_records_error_mode() -> None:
    class _BoomFetcher:
        def fetch_recent_executions(
            self, *, account_id: str
        ) -> tuple[IbkrExecutionForReconciliation, ...]:
            _ = account_id
            raise RuntimeError("simulated IBKR network failure")

    with _conn() as conn:
        reconciler = _build_reconciler(
            conn, execution_fetcher=_BoomFetcher()
        )
        result = reconciler.tick()
        assert result.mode_detected == "error"
        assert result.error_details_json is not None
        assert result.error_details_json["class"] == "RuntimeError"
        assert "simulated" in str(result.error_details_json["message"])
        assert result.pass_a_result is None

        run_repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        latest = run_repo.get_latest_for_account("DU1234567")
        assert latest is not None
        assert latest.mode_detected == "error"
        assert latest.error_details_json is not None


def test_full_tick_with_orphaned_execution_and_timeout_escalation() -> None:
    """Integration smoke test: seed one draft that's both touched by
    Pass A (missed fill) and one that should be escalated by Pass C
    (>24h timeout). Verify both heals fire in a single tick."""

    with _conn() as conn:
        # Seed an orphaned-fill draft (submitted, IBKR has the fill).
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        for index, (draft_id, status, age_hours) in enumerate(
            (("d-fill", "submitted", 0), ("d-old", "awaiting_reply_timeout", 30))
        ):
            ts = _NOW - timedelta(hours=2 + age_hours)
            repo.append(
                ActionDraftEntry(
                    action_draft_id=draft_id,
                    decision_package_id=None,
                    forecast_run_id=None,
                    created_at=ts - timedelta(minutes=20),
                    created_by="user",
                    ibkr_account_id="DU1234567",
                    conid=f"asset-{index}",
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
                    user_approved_at=ts - timedelta(minutes=10),
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
                transition_at=ts - timedelta(minutes=5),
            )
            repo.apply_lifecycle_transition(
                action_draft_id=draft_id,
                new_status="submitted",
                transitioned_at=ts - timedelta(minutes=1),
            )
            if status == "awaiting_reply_timeout":
                repo.apply_lifecycle_transition(
                    action_draft_id=draft_id,
                    new_status="awaiting_reply_timeout",
                    transitioned_at=ts,
                )

        audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(conn, _report())
        audit_repo.append(
            IbkrSubmissionAuditEntry(
                action_draft_id="d-fill",
                submitted_at=_NOW - timedelta(minutes=30),
                sent_to_account_id="DU1234567",
                sent_account_mode="paper",
                ibkr_perm_id=100100,
                ibkr_order_id=1,
                contract_json={"symbol": "ASML"},
                order_json={"action": "BUY"},
                gateway_session_id="sess-1",
                result="placed",
                error_class=None,
                error_message_dutch=None,
            )
        )

        class _OneFillFetcher:
            def fetch_recent_executions(
                self, *, account_id: str
            ) -> tuple[IbkrExecutionForReconciliation, ...]:
                _ = account_id
                return (
                    IbkrExecutionForReconciliation(
                        ibkr_exec_id="exec-001",
                        ibkr_perm_id=100100,
                        account_id="DU1234567",
                        conid="asset-0",
                        side="BUY",
                        fill_price_local=Decimal("638.72"),
                        fill_quantity=Decimal("6"),
                        fill_time=_NOW - timedelta(minutes=2),
                        raw={"perm_id": 100100},
                    ),
                )

        reconciler = _build_reconciler(
            conn,
            execution_fetcher=_OneFillFetcher(),
            now_value=_NOW,
        )
        result = reconciler.tick()
        assert result.mode_detected == "completed"
        assert result.pass_a_result is not None
        assert result.pass_a_result.missing_execution_applied == 1
        assert result.pass_c_result is not None
        assert result.pass_c_result.escalated_to_manual_review == 1
        assert result.divergences_found >= 2

        # Persisted run-audit row reflects per-pass counts.
        run_repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        latest = run_repo.get_latest_for_account("DU1234567")
        assert latest is not None
        assert latest.pass_a_orphaned_count == 1
        assert latest.pass_c_timeout_count == 1
        assert latest.divergences_found >= 2


_ = Literal  # silence unused-import warning
