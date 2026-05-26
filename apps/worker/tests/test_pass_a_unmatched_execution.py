"""Task 135a — Pass A unmatched-execution tests.

Covers the cases where IBKR reports a fill that doesn't match any
local draft (user placed an order directly in TWS, draft was deleted
locally, etc.). Pass A records these in ``unmatched_execution_audit``
and the divergence in ``reconciliation_audit`` — but never touches an
Action Draft.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrExecutionsRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
    SqlAlchemyReconciliationAuditRepository,
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
    run_pass_a_orphaned_executions,
)

_LATEST = "0053_reconciliation_audit_and_manual_review"
_NOW = datetime(2026, 5, 26, 10, 0, tzinfo=UTC)
_RUN_ID = "run-pass-a-unmatched"


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


def _now_seq() -> object:
    counter = {"n": 0}

    def _next() -> datetime:
        counter["n"] += 1
        return _NOW + timedelta(seconds=counter["n"])

    return _next


class _FakeFetcher:
    def __init__(
        self, executions: tuple[IbkrExecutionForReconciliation, ...]
    ) -> None:
        self._executions = executions

    def fetch_recent_executions(
        self, *, account_id: str
    ) -> tuple[IbkrExecutionForReconciliation, ...]:
        _ = account_id
        return self._executions


def _make_unmatched_fill(
    *,
    exec_id: str = "tws-exec-1",
    perm_id: int = 900900,
    conid: str = "67890",
) -> IbkrExecutionForReconciliation:
    return IbkrExecutionForReconciliation(
        ibkr_exec_id=exec_id,
        ibkr_perm_id=perm_id,
        account_id="DU1234567",
        conid=conid,
        side="BUY",
        fill_price_local=Decimal("100.50"),
        fill_quantity=Decimal("10"),
        fill_time=_NOW - timedelta(minutes=2),
        raw={"perm_id": perm_id, "source": "TWS"},
    )


def _run_pass_a(conn):  # type: ignore[no-untyped-def]
    fetcher = _FakeFetcher((_make_unmatched_fill(),))
    return run_pass_a_orphaned_executions(
        reconciliation_run_id=_RUN_ID,
        account_id="DU1234567",
        fetcher=fetcher,
        action_draft_repo=SqlAlchemyActionDraftRepository(conn, _report()),
        executions_repo=SqlAlchemyIbkrExecutionsRepository(conn, _report()),
        submission_audit_repo=SqlAlchemyIbkrSubmissionAuditRepository(
            conn, _report()
        ),
        unmatched_repo=SqlAlchemyUnmatchedExecutionAuditRepository(
            conn, _report()
        ),
        reconciliation_audit_repo=SqlAlchemyReconciliationAuditRepository(
            conn, _report()
        ),
        now_provider=_now_seq(),
    )


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


def test_unmatched_execution_appends_unmatched_row_and_audit() -> None:
    with _conn() as conn:
        result = _run_pass_a(conn)
        assert result.executions_observed == 1
        assert result.unmatched_execution_recorded == 1
        assert result.missing_execution_applied == 0
        assert result.unmatched_exec_ids == ("tws-exec-1",)

        unmatched_repo = SqlAlchemyUnmatchedExecutionAuditRepository(
            conn, _report()
        )
        unresolved = unmatched_repo.list_unresolved_for_account("DU1234567")
        assert len(unresolved) == 1
        assert unresolved[0].ibkr_exec_id == "tws-exec-1"
        assert unresolved[0].resolution_status == "unresolved"

        recon_repo = SqlAlchemyReconciliationAuditRepository(conn, _report())
        audit_rows = recon_repo.list_for_run(_RUN_ID)
        assert len(audit_rows) == 1
        assert audit_rows[0].divergence_type == "unmatched_execution"
        assert audit_rows[0].action_draft_id is None


def test_unmatched_execution_does_not_touch_action_draft_rows() -> None:
    with _conn() as conn:
        # No drafts seeded; Pass A must not insert any draft rows
        # while recording the unmatched execution.
        _run_pass_a(conn)
        draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
        assert (
            draft_repo.list_te_keuren_for_account("DU1234567") == ()
        )


def test_unmatched_execution_idempotent_on_replay() -> None:
    with _conn() as conn:
        _run_pass_a(conn)
        # Second run with the same fetcher payload should not double-
        # record (UNIQUE on ibkr_exec_id) and should report it as
        # already_recorded.
        result = _run_pass_a(conn)
        assert result.executions_already_recorded == 1
        assert result.unmatched_execution_recorded == 0

        unmatched_repo = SqlAlchemyUnmatchedExecutionAuditRepository(
            conn, _report()
        )
        assert len(unmatched_repo.list_unresolved_for_account("DU1234567")) == 1


def test_mixed_batch_with_matched_and_unmatched_fills() -> None:
    """One IBKR poll returns one matched + one unmatched execution —
    Pass A records both kinds in a single tick."""

    from ai_trading_agent_storage import (
        ActionDraftEntry,
        IbkrSubmissionAuditEntry,
    )

    with _conn() as conn:
        # Seed a draft + walk to ``submitted`` so the matched
        # execution can heal it.
        draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
        draft_repo.append(
            ActionDraftEntry(
                action_draft_id="d-match",
                decision_package_id=None,
                forecast_run_id=None,
                created_at=_NOW - timedelta(hours=1),
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
                status="proposed",
                last_edited_at=None,
                user_approved_at=_NOW - timedelta(minutes=30),
                dismissed_at=None,
                deleted_at=None,
                dismissed_reason=None,
                user_note=None,
                superseded_by_decision_package_id=None,
                audit_trail_hash="h-1",
                previous_draft_hash=None,
                safe_for_submission=False,
            )
        )
        draft_repo.update_status(
            action_draft_id="d-match",
            new_status="user_approved",
            transition_actor="user",
            transition_at=_NOW - timedelta(minutes=20),
        )
        draft_repo.apply_lifecycle_transition(
            action_draft_id="d-match",
            new_status="submitted",
            transitioned_at=_NOW - timedelta(minutes=15),
        )
        SqlAlchemyIbkrSubmissionAuditRepository(conn, _report()).append(
            IbkrSubmissionAuditEntry(
                action_draft_id="d-match",
                submitted_at=_NOW - timedelta(minutes=10),
                sent_to_account_id="DU1234567",
                sent_account_mode="paper",
                ibkr_perm_id=555555,
                ibkr_order_id=1,
                contract_json={"symbol": "ASML"},
                order_json={"action": "BUY"},
                gateway_session_id="sess-1",
                result="placed",
                error_class=None,
                error_message_dutch=None,
            )
        )

        fetcher = _FakeFetcher(
            (
                IbkrExecutionForReconciliation(
                    ibkr_exec_id="exec-match",
                    ibkr_perm_id=555555,
                    account_id="DU1234567",
                    conid="12345",
                    side="BUY",
                    fill_price_local=Decimal("638.72"),
                    fill_quantity=Decimal("6"),
                    fill_time=_NOW - timedelta(minutes=2),
                    raw={"perm_id": 555555},
                ),
                _make_unmatched_fill(exec_id="exec-tws", perm_id=999111),
            )
        )
        result = run_pass_a_orphaned_executions(
            reconciliation_run_id=_RUN_ID,
            account_id="DU1234567",
            fetcher=fetcher,
            action_draft_repo=SqlAlchemyActionDraftRepository(conn, _report()),
            executions_repo=SqlAlchemyIbkrExecutionsRepository(conn, _report()),
            submission_audit_repo=SqlAlchemyIbkrSubmissionAuditRepository(
                conn, _report()
            ),
            unmatched_repo=SqlAlchemyUnmatchedExecutionAuditRepository(
                conn, _report()
            ),
            reconciliation_audit_repo=SqlAlchemyReconciliationAuditRepository(
                conn, _report()
            ),
            now_provider=_now_seq(),
        )
        assert result.executions_observed == 2
        assert result.missing_execution_applied == 1
        assert result.unmatched_execution_recorded == 1
        assert result.divergences_found == 2
        assert result.healed_draft_ids == ("d-match",)
        assert result.unmatched_exec_ids == ("exec-tws",)
