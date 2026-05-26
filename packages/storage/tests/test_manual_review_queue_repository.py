"""Task 135a — manual_review_queue repository tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    ManualReviewQueueEntry,
    SqlAlchemyManualReviewQueueRepository,
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
            status="requires_manual_review",
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
    draft_id: str = "draft-1",
    flagged_at: datetime | None = None,
    reason: str = "timeout_24h_no_data",
    details: str = "24 uur geen update van IBKR ontvangen.",
    resolution_status: str = "pending",
    resolved_at: datetime | None = None,
    resolution_note: str | None = None,
) -> ManualReviewQueueEntry:
    return ManualReviewQueueEntry(
        flagged_at=flagged_at or _BASE_TS,
        action_draft_id=draft_id,
        reason=reason,
        details_dutch=details,
        resolution_status=resolution_status,
        resolved_at=resolved_at,
        resolution_note=resolution_note,
    )


def test_append_returns_entry_with_autoincrement_id() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="draft-1")
        repo = SqlAlchemyManualReviewQueueRepository(conn, _report())
        stored = repo.append(_entry())
        assert stored.id is not None
        assert stored.reason == "timeout_24h_no_data"
        assert stored.resolution_status == "pending"


def test_get_by_id_returns_row_or_none() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="draft-1")
        repo = SqlAlchemyManualReviewQueueRepository(conn, _report())
        stored = repo.append(_entry())
        assert stored.id is not None
        assert repo.get_by_id(stored.id) is not None
        assert repo.get_by_id(999_999) is None


def test_acknowledge_flips_pending_to_acknowledged() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="draft-1")
        repo = SqlAlchemyManualReviewQueueRepository(conn, _report())
        stored = repo.append(_entry())
        assert stored.id is not None
        ack_at = _BASE_TS + timedelta(hours=1)
        updated = repo.acknowledge(
            queue_id=stored.id,
            resolved_at=ack_at,
            note="Door gebruiker bevestigd.",
        )
        assert updated.resolution_status == "acknowledged"
        # SQLite strips tzinfo on the round-trip; compare naive components.
        assert updated.resolved_at is not None
        assert updated.resolved_at.replace(tzinfo=None) == ack_at.replace(
            tzinfo=None
        )
        assert updated.resolution_note == "Door gebruiker bevestigd."


def test_acknowledge_is_idempotent_for_already_acknowledged_row() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="draft-1")
        repo = SqlAlchemyManualReviewQueueRepository(conn, _report())
        stored = repo.append(_entry())
        assert stored.id is not None
        first_ack_at = _BASE_TS + timedelta(hours=1)
        repo.acknowledge(queue_id=stored.id, resolved_at=first_ack_at)
        # Second call should not overwrite the timestamp.
        second = repo.acknowledge(
            queue_id=stored.id,
            resolved_at=_BASE_TS + timedelta(hours=10),
            note="andere notitie",
        )
        assert second.resolution_status == "acknowledged"
        # SQLite strips tzinfo on the round-trip; compare naive components.
        assert second.resolved_at is not None
        assert second.resolved_at.replace(tzinfo=None) == first_ack_at.replace(
            tzinfo=None
        )


def test_acknowledge_unknown_id_raises_lookup_error() -> None:
    with _conn() as conn:
        repo = SqlAlchemyManualReviewQueueRepository(conn, _report())
        with pytest.raises(LookupError):
            repo.acknowledge(queue_id=42, resolved_at=_BASE_TS)


def test_list_pending_for_account_excludes_acknowledged_rows() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="draft-a")
        _seed_draft(conn, draft_id="draft-b")
        repo = SqlAlchemyManualReviewQueueRepository(conn, _report())
        a = repo.append(_entry(draft_id="draft-a"))
        repo.append(_entry(draft_id="draft-b"))
        assert a.id is not None
        repo.acknowledge(queue_id=a.id, resolved_at=_BASE_TS)
        rows = repo.list_pending_for_account("DU1234567")
        assert [r.action_draft_id for r in rows] == ["draft-b"]


def test_list_pending_for_account_filters_by_account() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="draft-a", account_id="DU1111111")
        _seed_draft(conn, draft_id="draft-b", account_id="DU2222222")
        repo = SqlAlchemyManualReviewQueueRepository(conn, _report())
        repo.append(_entry(draft_id="draft-a"))
        repo.append(_entry(draft_id="draft-b"))
        rows_a = repo.list_pending_for_account("DU1111111")
        rows_b = repo.list_pending_for_account("DU2222222")
        assert [r.action_draft_id for r in rows_a] == ["draft-a"]
        assert [r.action_draft_id for r in rows_b] == ["draft-b"]


def test_list_pending_orders_newest_first() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="d-old")
        _seed_draft(conn, draft_id="d-new")
        repo = SqlAlchemyManualReviewQueueRepository(conn, _report())
        repo.append(_entry(draft_id="d-old", flagged_at=_BASE_TS))
        repo.append(
            _entry(
                draft_id="d-new",
                flagged_at=_BASE_TS + timedelta(hours=2),
            )
        )
        rows = repo.list_pending_for_account("DU1234567")
        assert [r.action_draft_id for r in rows] == ["d-new", "d-old"]


def test_count_pending_for_account_matches_list_length() -> None:
    with _conn() as conn:
        _seed_draft(conn, draft_id="draft-1")
        repo = SqlAlchemyManualReviewQueueRepository(conn, _report())
        assert repo.count_pending_for_account("DU1234567") == 0
        repo.append(_entry())
        assert repo.count_pending_for_account("DU1234567") == 1


def test_invalid_reason_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(reason="not_a_reason")


def test_invalid_resolution_status_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(resolution_status="closed")


def test_empty_details_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(details="")
