"""Task 135a — reconciliation_audit repository tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    ReconciliationAuditEntry,
    SqlAlchemyReconciliationAuditRepository,
)
from ai_trading_agent_storage.metadata import action_drafts, metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)

_LATEST = "0053_reconciliation_audit_and_manual_review"
_BASE_TS = datetime(2026, 5, 26, 9, 0, tzinfo=UTC)


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


def _seed_draft(conn, *, draft_id: str, account_id: str = "DU1234567") -> None:
    conn.execute(
        action_drafts.insert().values(
            action_draft_id=draft_id,
            decision_package_id=None,
            forecast_run_id=None,
            created_at=_BASE_TS,
            created_by="user",
            ibkr_account_id=account_id,
            conid="ASML.AS",
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
            usable_cash_eur_at_creation=Decimal("1000"),
            held_quantity_at_creation=None,
            status="submitted",
            last_edited_at=None,
            user_approved_at=None,
            dismissed_at=None,
            deleted_at=None,
            dismissed_reason=None,
            user_note=None,
            superseded_by_decision_package_id=None,
            audit_trail_hash=f"hash-{draft_id}",
            previous_draft_hash=None,
            safe_for_submission=False,
            submission_block_reason=None,
            submission_started_at=None,
            terminal_state_at=None,
        )
    )


def _entry(
    *,
    run_id: str = "run-1",
    draft_id: str | None = "draft-1",
    event_at: datetime | None = None,
    pass_name: str = "orphaned_execution",
    divergence_type: str = "missing_execution_applied",
    before_status: str | None = "submitted",
    after_status: str | None = "filled",
    evidence: dict[str, object] | None = None,
    notes: str | None = "Heal toegepast op basis van IBKR-fill.",
) -> ReconciliationAuditEntry:
    return ReconciliationAuditEntry(
        reconciliation_run_id=run_id,
        action_draft_id=draft_id,
        event_at=event_at or _BASE_TS,
        pass_name=pass_name,
        divergence_type=divergence_type,
        before_status=before_status,
        after_status=after_status,
        ibkr_evidence_json=evidence or {"perm_id": 100100, "exec_id": "e-1"},
        notes_dutch=notes,
    )


def test_append_returns_entry_with_autoincrement_id() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="draft-1")
        repo = SqlAlchemyReconciliationAuditRepository(conn, _report())
        stored = repo.append(_entry())
        assert stored.id is not None
        assert stored.reconciliation_run_id == "run-1"
        assert stored.divergence_type == "missing_execution_applied"
        assert stored.ibkr_evidence_json["perm_id"] == 100100


def test_append_allows_null_action_draft_id_for_unmatched_execution() -> None:
    with _conn() as conn:
        repo = SqlAlchemyReconciliationAuditRepository(conn, _report())
        stored = repo.append(
            _entry(
                draft_id=None,
                divergence_type="unmatched_execution",
                before_status=None,
                after_status=None,
            )
        )
        assert stored.id is not None
        assert stored.action_draft_id is None


def test_list_for_run_orders_chronologically() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="draft-1")
        repo = SqlAlchemyReconciliationAuditRepository(conn, _report())
        repo.append(
            _entry(
                event_at=_BASE_TS + timedelta(seconds=2),
                divergence_type="status_corrected_to_filled",
            )
        )
        repo.append(
            _entry(
                event_at=_BASE_TS + timedelta(seconds=1),
                divergence_type="missing_execution_applied",
            )
        )
        rows = repo.list_for_run("run-1")
        assert [r.divergence_type for r in rows] == [
            "missing_execution_applied",
            "status_corrected_to_filled",
        ]


def test_list_for_draft_filters_to_one_draft() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="draft-1")
        _seed_draft(conn, draft_id="draft-2")
        repo = SqlAlchemyReconciliationAuditRepository(conn, _report())
        repo.append(_entry(draft_id="draft-1"))
        repo.append(_entry(draft_id="draft-2"))
        rows = repo.list_for_draft("draft-1")
        assert len(rows) == 1
        assert rows[0].action_draft_id == "draft-1"


def test_list_for_account_includes_orphan_rows_and_account_drafts() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="d-acct", account_id="DU1234567")
        _seed_draft(conn, draft_id="d-other", account_id="DU9999999")
        repo = SqlAlchemyReconciliationAuditRepository(conn, _report())
        repo.append(_entry(draft_id="d-acct"))
        repo.append(_entry(draft_id="d-other"))
        repo.append(
            _entry(
                draft_id=None,
                divergence_type="unmatched_execution",
                before_status=None,
                after_status=None,
            )
        )
        rows = repo.list_for_account(account_id="DU1234567")
        draft_ids = {row.action_draft_id for row in rows}
        assert "d-acct" in draft_ids
        assert "d-other" not in draft_ids
        assert None in draft_ids


def test_count_drafts_healed_since_counts_distinct_drafts() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="d-h1")
        _seed_draft(conn, draft_id="d-h2")
        repo = SqlAlchemyReconciliationAuditRepository(conn, _report())
        repo.append(
            _entry(
                draft_id="d-h1",
                divergence_type="missing_execution_applied",
                event_at=_BASE_TS,
            )
        )
        repo.append(
            _entry(
                draft_id="d-h1",
                divergence_type="status_corrected_to_filled",
                event_at=_BASE_TS + timedelta(seconds=1),
            )
        )
        repo.append(
            _entry(
                draft_id="d-h2",
                divergence_type="timeout_recovered_to_terminal",
                event_at=_BASE_TS + timedelta(seconds=2),
            )
        )
        count = repo.count_drafts_healed_since(
            account_id="DU1234567", since=_BASE_TS - timedelta(hours=1)
        )
        assert count == 2


def test_count_drafts_healed_since_excludes_terminal_divergence_logs() -> None:
    """terminal_state_divergence_logged is not a heal — it is the row
    written when the system records that two terminal states disagreed
    but the system kept its own state (Task 135 lock §3 Pass B)."""

    with _conn() as conn:
        _seed_draft(conn, draft_id="d-1")
        repo = SqlAlchemyReconciliationAuditRepository(conn, _report())
        repo.append(
            _entry(
                draft_id="d-1",
                divergence_type="terminal_state_divergence_logged",
            )
        )
        count = repo.count_drafts_healed_since(
            account_id="DU1234567", since=_BASE_TS - timedelta(hours=1)
        )
        assert count == 0


def test_invalid_pass_name_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(pass_name="not_a_pass")


def test_invalid_divergence_type_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(divergence_type="something_else")


def test_empty_run_id_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(run_id="")
