"""Task 135a — Pass A happy-path tests.

Covers the most common reconciliation scenarios:

* IBKR has a fill we missed, draft is ``submitted`` → executions row
  is inserted and the draft transitions to ``filled``.
* IBKR has a partial fill, draft is ``submitted`` → draft transitions
  to ``partially_filled``.
* IBKR re-delivers an execution that's already locally recorded → no-op.
* Draft is ``awaiting_reply_timeout`` and IBKR has a fill → draft
  recovers to ``filled`` (Task 135 widening of the state machine).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    IbkrExecutionEntry,
    IbkrSubmissionAuditEntry,
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
_RUN_ID = "run-pass-a-001"


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
    """Deterministic ``now_provider`` that increments by 1 second on
    each call so reconciliation_audit rows order strictly."""

    counter = {"n": 0}

    def _next() -> datetime:
        counter["n"] += 1
        return _NOW + timedelta(seconds=counter["n"])

    return _next


def _draft(
    *,
    draft_id: str = "draft-1",
    status: str = "submitted",
    quantity: Decimal = Decimal("6"),
) -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id=draft_id,
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
        quantity=quantity,
        order_type="LMT",
        limit_price_local=Decimal("638.72"),
        time_in_force="DAY",
        notional_local=Decimal("3832.32"),
        notional_eur=Decimal("3832.32"),
        fx_rate_at_creation=Decimal("1"),
        usable_cash_eur_at_creation=Decimal("50000"),
        held_quantity_at_creation=None,
        status="proposed",  # will be progressed via apply_lifecycle_transition
        last_edited_at=None,
        user_approved_at=_NOW - timedelta(minutes=30),
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=None,
        superseded_by_decision_package_id=None,
        audit_trail_hash=f"hash-{draft_id}",
        previous_draft_hash=None,
        safe_for_submission=False,
    ), status


def _seed_draft_at_status(
    conn, *, draft_id: str, target_status: str, quantity: Decimal = Decimal("6")
) -> None:
    """Insert a draft and walk it to ``target_status`` via the locked
    state machine so it lands in a state Pass A would actually meet
    in production."""

    repo = SqlAlchemyActionDraftRepository(conn, _report())
    draft, _ = _draft(
        draft_id=draft_id, status=target_status, quantity=quantity
    )
    repo.append(draft)
    walks: dict[str, list[str]] = {
        "submitted": ["user_approved", "submitted"],
        "accepted": ["user_approved", "submitted", "accepted"],
        "working": ["user_approved", "submitted", "accepted", "working"],
        "awaiting_reply_timeout": [
            "user_approved",
            "submitted",
            "awaiting_reply_timeout",
        ],
    }
    if target_status not in walks:
        raise ValueError(f"_seed_draft_at_status: no walk for {target_status}")
    for index, status in enumerate(walks[target_status]):
        if status == "user_approved":
            repo.update_status(
                action_draft_id=draft_id,
                new_status=status,
                transition_actor="user",
                transition_at=_NOW - timedelta(minutes=20 - index),
            )
        else:
            repo.apply_lifecycle_transition(
                action_draft_id=draft_id,
                new_status=status,
                transitioned_at=_NOW - timedelta(minutes=20 - index),
            )


def _seed_submission_audit(
    conn, *, draft_id: str, perm_id: int, account_id: str = "DU1234567"
) -> None:
    """Insert one ``placed`` ibkr_submission_audit row so Pass A's
    perm_id → draft lookup succeeds."""

    audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(conn, _report())
    audit_repo.append(
        IbkrSubmissionAuditEntry(
            action_draft_id=draft_id,
            submitted_at=_NOW - timedelta(minutes=10),
            sent_to_account_id=account_id,
            sent_account_mode="paper",
            ibkr_perm_id=perm_id,
            ibkr_order_id=1,
            contract_json={"symbol": "ASML"},
            order_json={"action": "BUY"},
            gateway_session_id="sess-1",
            result="placed",
            error_class=None,
            error_message_dutch=None,
        )
    )


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


def _make_fill(
    *,
    exec_id: str = "exec-001",
    perm_id: int = 100100,
    side: str = "BUY",
    quantity: Decimal = Decimal("6"),
    price: Decimal = Decimal("638.72"),
) -> IbkrExecutionForReconciliation:
    return IbkrExecutionForReconciliation(
        ibkr_exec_id=exec_id,
        ibkr_perm_id=perm_id,
        account_id="DU1234567",
        conid="12345",
        side=side,
        fill_price_local=price,
        fill_quantity=quantity,
        fill_time=_NOW - timedelta(minutes=2),
        raw={"perm_id": perm_id, "side": side},
    )


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


def test_orphaned_full_fill_heals_submitted_draft_to_filled() -> None:
    with _conn() as conn:
        _seed_draft_at_status(conn, draft_id="d-1", target_status="submitted")
        _seed_submission_audit(conn, draft_id="d-1", perm_id=100100)

        fetcher = _FakeFetcher(
            (_make_fill(exec_id="exec-001", perm_id=100100),)
        )
        result = run_pass_a_orphaned_executions(
            reconciliation_run_id=_RUN_ID,
            account_id="DU1234567",
            fetcher=fetcher,
            action_draft_repo=SqlAlchemyActionDraftRepository(
                conn, _report()
            ),
            executions_repo=SqlAlchemyIbkrExecutionsRepository(
                conn, _report()
            ),
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

        assert result.executions_observed == 1
        assert result.missing_execution_applied == 1
        assert result.unmatched_execution_recorded == 0
        assert result.divergences_found == 1
        assert result.healed_draft_ids == ("d-1",)

        # Draft is now filled.
        draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
        updated = draft_repo.get_by_id("d-1")
        assert updated is not None
        assert updated.status == "filled"

        # The execution is in the local ledger.
        exec_repo = SqlAlchemyIbkrExecutionsRepository(conn, _report())
        assert exec_repo.get_by_exec_id("exec-001") is not None

        # The reconciliation audit has two rows (missing + corrected).
        recon_repo = SqlAlchemyReconciliationAuditRepository(conn, _report())
        audit_rows = recon_repo.list_for_run(_RUN_ID)
        divergence_types = [row.divergence_type for row in audit_rows]
        assert "missing_execution_applied" in divergence_types
        assert "status_corrected_to_filled" in divergence_types


def test_orphaned_partial_fill_heals_submitted_draft_to_partially_filled() -> None:
    with _conn() as conn:
        _seed_draft_at_status(
            conn, draft_id="d-2", target_status="submitted",
            quantity=Decimal("10"),
        )
        _seed_submission_audit(conn, draft_id="d-2", perm_id=200200)

        fetcher = _FakeFetcher(
            (
                _make_fill(
                    exec_id="exec-partial",
                    perm_id=200200,
                    quantity=Decimal("4"),
                ),
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
        assert result.missing_execution_applied == 1
        draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
        updated = draft_repo.get_by_id("d-2")
        assert updated is not None
        assert updated.status == "partially_filled"


def test_already_recorded_execution_is_skipped() -> None:
    with _conn() as conn:
        _seed_draft_at_status(conn, draft_id="d-3", target_status="working")
        _seed_submission_audit(conn, draft_id="d-3", perm_id=300300)

        # Pre-record an execution for this exec_id so Pass A treats it
        # as already-recorded.
        exec_repo = SqlAlchemyIbkrExecutionsRepository(conn, _report())
        exec_repo.append(
            IbkrExecutionEntry(
                ibkr_exec_id="exec-already",
                ibkr_perm_id=300300,
                action_draft_id="d-3",
                account_id="DU1234567",
                conid="12345",
                side="BUY",
                fill_price_local=Decimal("638.72"),
                fill_quantity=Decimal("3"),
                fill_time=_NOW - timedelta(minutes=5),
                commission=Decimal("0"),
                commission_currency="EUR",
                exchange="AEB",
            )
        )

        fetcher = _FakeFetcher(
            (
                _make_fill(
                    exec_id="exec-already",
                    perm_id=300300,
                    quantity=Decimal("3"),
                ),
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
        assert result.executions_observed == 1
        assert result.executions_already_recorded == 1
        assert result.missing_execution_applied == 0
        assert result.divergences_found == 0

        # Draft was not touched.
        draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
        updated = draft_repo.get_by_id("d-3")
        assert updated is not None
        assert updated.status == "working"


def test_awaiting_reply_timeout_draft_heals_to_filled_via_pass_a() -> None:
    with _conn() as conn:
        _seed_draft_at_status(
            conn,
            draft_id="d-4",
            target_status="awaiting_reply_timeout",
        )
        _seed_submission_audit(conn, draft_id="d-4", perm_id=400400)

        fetcher = _FakeFetcher(
            (_make_fill(exec_id="exec-late", perm_id=400400),)
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
        assert result.missing_execution_applied == 1
        draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
        updated = draft_repo.get_by_id("d-4")
        assert updated is not None
        assert updated.status == "filled"


def test_no_executions_returns_zero_divergences() -> None:
    with _conn() as conn:
        fetcher = _FakeFetcher(())
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
        assert result.executions_observed == 0
        assert result.divergences_found == 0
        assert result.healed_draft_ids == ()
        assert result.unmatched_exec_ids == ()
