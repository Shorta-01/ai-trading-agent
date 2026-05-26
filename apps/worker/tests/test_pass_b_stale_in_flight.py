"""Task 135b — Pass B stale in-flight detection tests.

Covers the four scenarios the reconciler can encounter:

* Worker says ``submitted``, IBKR confirms ``Filled`` → status heals
  to ``filled`` with one ``status_corrected_to_filled`` audit row.
* Worker says ``working``, IBKR says ``Cancelled`` → status heals to
  ``cancelled``.
* Worker says in-flight, IBKR doesn't know the perm_id at all → one
  ``terminal_state_divergence_logged`` row, no status change.
* Worker + IBKR agree the order is still in-flight → no-op.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    IbkrSubmissionAuditEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
    SqlAlchemyReconciliationAuditRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.ibkr_reconciliation import (
    IbkrOrderStatusForReconciliation,
    run_pass_b_stale_in_flight,
)

_LATEST = "0053_reconciliation_audit_and_manual_review"
_NOW = datetime(2026, 5, 26, 11, 0, tzinfo=UTC)
_RUN_ID = "run-pass-b-001"


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


def _now_seq():  # type: ignore[no-untyped-def]
    counter = {"n": 0}

    def _next() -> datetime:
        counter["n"] += 1
        return _NOW + timedelta(seconds=counter["n"])

    return _next


def _seed_in_flight_draft(
    conn,  # type: ignore[no-untyped-def]
    *,
    draft_id: str,
    perm_id: int,
    target_status: str = "submitted",
    account_id: str = "DU1234567",
) -> None:
    repo = SqlAlchemyActionDraftRepository(conn, _report())
    repo.append(
        ActionDraftEntry(
            action_draft_id=draft_id,
            decision_package_id=None,
            forecast_run_id=None,
            created_at=_NOW - timedelta(hours=2),
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
            user_approved_at=_NOW - timedelta(minutes=30),
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
        transition_at=_NOW - timedelta(minutes=20),
    )
    walk = {
        "submitted": ["submitted"],
        "accepted": ["submitted", "accepted"],
        "working": ["submitted", "accepted", "working"],
        "partially_filled": [
            "submitted",
            "accepted",
            "working",
            "partially_filled",
        ],
        "pending_cancellation": [
            "submitted",
            "accepted",
            "working",
            "pending_cancellation",
        ],
    }[target_status]
    for index, status in enumerate(walk):
        repo.apply_lifecycle_transition(
            action_draft_id=draft_id,
            new_status=status,
            transitioned_at=_NOW - timedelta(minutes=15 - index),
        )

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


class _FakeStatusFetcher:
    def __init__(
        self, mapping: dict[int, IbkrOrderStatusForReconciliation]
    ) -> None:
        self._mapping = mapping
        self.calls: list[tuple[int, str]] = []

    def fetch_order_status(
        self, *, ibkr_perm_id: int, account_id: str
    ) -> IbkrOrderStatusForReconciliation:
        self.calls.append((ibkr_perm_id, account_id))
        if ibkr_perm_id not in self._mapping:
            return IbkrOrderStatusForReconciliation(
                ibkr_perm_id=ibkr_perm_id,
                found_in_ibkr=False,
                ibkr_raw_status=None,
                raw_payload={"reason": "unknown_perm_id"},
            )
        return self._mapping[ibkr_perm_id]


def _run_pass_b(
    conn,  # type: ignore[no-untyped-def]
    fetcher,  # type: ignore[no-untyped-def]
    *,
    account_id: str = "DU1234567",
):  # type: ignore[no-untyped-def]
    return run_pass_b_stale_in_flight(
        reconciliation_run_id=_RUN_ID,
        account_id=account_id,
        fetcher=fetcher,
        action_draft_repo=SqlAlchemyActionDraftRepository(conn, _report()),
        submission_audit_repo=SqlAlchemyIbkrSubmissionAuditRepository(
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


def test_submitted_with_ibkr_filled_heals_to_filled() -> None:
    with _conn() as conn:
        _seed_in_flight_draft(
            conn, draft_id="d-1", perm_id=100100, target_status="submitted"
        )
        fetcher = _FakeStatusFetcher(
            {
                100100: IbkrOrderStatusForReconciliation(
                    ibkr_perm_id=100100,
                    found_in_ibkr=True,
                    ibkr_raw_status="Filled",
                    raw_payload={"filled": "6"},
                )
            }
        )
        result = _run_pass_b(conn, fetcher)
        assert result.status_corrections_applied == 1
        assert result.healed_draft_ids == ("d-1",)
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        updated = repo.get_by_id("d-1")
        assert updated is not None
        assert updated.status == "filled"


def test_working_with_ibkr_cancelled_heals_to_cancelled() -> None:
    with _conn() as conn:
        _seed_in_flight_draft(
            conn, draft_id="d-2", perm_id=200200, target_status="working"
        )
        fetcher = _FakeStatusFetcher(
            {
                200200: IbkrOrderStatusForReconciliation(
                    ibkr_perm_id=200200,
                    found_in_ibkr=True,
                    ibkr_raw_status="Cancelled",
                    raw_payload={},
                )
            }
        )
        result = _run_pass_b(conn, fetcher)
        assert result.status_corrections_applied == 1
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        updated = repo.get_by_id("d-2")
        assert updated is not None
        assert updated.status == "cancelled"


def test_ibkr_unknown_perm_id_logs_terminal_divergence() -> None:
    with _conn() as conn:
        _seed_in_flight_draft(
            conn, draft_id="d-3", perm_id=300300, target_status="working"
        )
        fetcher = _FakeStatusFetcher({})  # IBKR doesn't know the perm_id
        result = _run_pass_b(conn, fetcher)
        assert result.terminal_divergence_logged == 1
        assert result.status_corrections_applied == 0
        assert result.divergent_draft_ids == ("d-3",)

        # Draft was not touched.
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        updated = repo.get_by_id("d-3")
        assert updated is not None
        assert updated.status == "working"

        # One audit row written.
        recon_repo = SqlAlchemyReconciliationAuditRepository(conn, _report())
        rows = recon_repo.list_for_run(_RUN_ID)
        assert len(rows) == 1
        assert rows[0].divergence_type == "terminal_state_divergence_logged"
        assert rows[0].before_status == "working"
        assert rows[0].after_status == "working"


def test_working_in_sync_with_ibkr_is_no_op() -> None:
    with _conn() as conn:
        _seed_in_flight_draft(
            conn, draft_id="d-4", perm_id=400400, target_status="working"
        )
        fetcher = _FakeStatusFetcher(
            {
                400400: IbkrOrderStatusForReconciliation(
                    ibkr_perm_id=400400,
                    found_in_ibkr=True,
                    ibkr_raw_status="PreSubmitted",
                    raw_payload={},
                )
            }
        )
        result = _run_pass_b(conn, fetcher)
        assert result.status_corrections_applied == 0
        assert result.terminal_divergence_logged == 0
        assert result.in_sync_count == 1


def test_draft_without_submission_audit_is_skipped() -> None:
    with _conn() as conn:
        repo = SqlAlchemyActionDraftRepository(conn, _report())
        # Seed but never write an ibkr_submission_audit row — Pass B
        # can't resolve a perm_id so it skips.
        repo.append(
            ActionDraftEntry(
                action_draft_id="d-noaudit",
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
                user_approved_at=_NOW - timedelta(minutes=20),
                dismissed_at=None,
                deleted_at=None,
                dismissed_reason=None,
                user_note=None,
                superseded_by_decision_package_id=None,
                audit_trail_hash="h",
                previous_draft_hash=None,
                safe_for_submission=False,
            )
        )
        repo.update_status(
            action_draft_id="d-noaudit",
            new_status="user_approved",
            transition_actor="user",
            transition_at=_NOW - timedelta(minutes=15),
        )
        repo.apply_lifecycle_transition(
            action_draft_id="d-noaudit",
            new_status="submitted",
            transitioned_at=_NOW - timedelta(minutes=10),
        )

        fetcher = _FakeStatusFetcher({})
        result = _run_pass_b(conn, fetcher)
        assert result.drafts_skipped_no_perm_id == 1
        assert result.status_corrections_applied == 0
        assert result.terminal_divergence_logged == 0
        assert fetcher.calls == []  # no IBKR lookup attempted


def test_no_in_flight_drafts_returns_zero() -> None:
    with _conn() as conn:
        fetcher = _FakeStatusFetcher({})
        result = _run_pass_b(conn, fetcher)
        assert result.drafts_evaluated == 0
        assert result.divergences_found == 0
