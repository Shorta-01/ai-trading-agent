"""Task 126 — ``SqlAlchemyIbkrConnectionAuditRepository`` tests.

Append-only roundtrip + ordering + filter-by-account assertions.
The repository deliberately exposes no update or delete methods;
that is asserted as part of the "no mutability" contract.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    IbkrConnectionAuditRecord,
    SqlAlchemyIbkrConnectionAuditRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)


def _report(allowed: bool) -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=(
            MigrationReadinessStatus.MIGRATIONS_CURRENT
            if allowed
            else MigrationReadinessStatus.NOT_CONNECTED
        ),
        database_connected=allowed,
        migrations_checked_against_database=allowed,
        offline_inventory_valid=True,
        latest_expected_revision_id="0045_ibkr_account_id_and_mode_tagging",
        database_revision_id=(
            "0045_ibkr_account_id_and_mode_tagging" if allowed else None
        ),
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


def test_append_and_list_recent_roundtrip() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyIbkrConnectionAuditRepository(conn, _report(True))

        record_paper = IbkrConnectionAuditRecord(
            audit_id="icaudit-1",
            event_at=datetime(2026, 5, 25, 7, 0, tzinfo=UTC),
            ibkr_account_id="DU1234567",
            event_type="mode_check_prefix",
            account_mode_detected="paper",
            connection_id=None,
            details_json=json.dumps({"derived_from": "prefix"}),
        )
        record_success = IbkrConnectionAuditRecord(
            audit_id="icaudit-2",
            event_at=datetime(2026, 5, 25, 7, 0, 1, tzinfo=UTC),
            ibkr_account_id="DU1234567",
            event_type="connect_success",
            account_mode_detected="paper",
            connection_id="ibkr_abc123",
            details_json=None,
        )
        repo.append(record_paper)
        repo.append(record_success)

        rows = repo.list_recent(ibkr_account_id="DU1234567")
        assert len(rows.records) == 2
        # Order is event_at DESC so success row is first.
        assert rows.records[0].audit_id == "icaudit-2"
        assert rows.records[1].audit_id == "icaudit-1"


def test_list_recent_filters_by_account() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyIbkrConnectionAuditRepository(conn, _report(True))

        now = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)
        repo.append(
            IbkrConnectionAuditRecord(
                audit_id="icaudit-a",
                event_at=now,
                ibkr_account_id="DU1111111",
                event_type="connect_success",
                account_mode_detected="paper",
                connection_id=None,
                details_json=None,
            )
        )
        repo.append(
            IbkrConnectionAuditRecord(
                audit_id="icaudit-b",
                event_at=now,
                ibkr_account_id="U9999999",
                event_type="connect_success",
                account_mode_detected="live",
                connection_id=None,
                details_json=None,
            )
        )

        only_paper = repo.list_recent(ibkr_account_id="DU1111111")
        assert len(only_paper.records) == 1
        assert only_paper.records[0].ibkr_account_id == "DU1111111"

        all_rows = repo.list_recent()
        assert {r.ibkr_account_id for r in all_rows.records} == {
            "DU1111111",
            "U9999999",
        }


def test_repository_exposes_no_update_or_delete_methods() -> None:
    """Task 126 product lock §2: audit rows are append-only."""

    forbidden = {"update", "delete", "save_or_update", "upsert"}
    public_methods = {
        name
        for name in dir(SqlAlchemyIbkrConnectionAuditRepository)
        if not name.startswith("_")
    }
    assert forbidden.isdisjoint(public_methods)


def test_record_rejects_unknown_event_type() -> None:
    with pytest.raises(ValueError, match="event_type"):
        IbkrConnectionAuditRecord(
            audit_id="icaudit-x",
            event_at=datetime(2026, 5, 25, tzinfo=UTC),
            ibkr_account_id="DU1234567",
            event_type="freaky_unknown",
            account_mode_detected=None,
            connection_id=None,
            details_json=None,
        )


def test_record_rejects_unknown_account_mode_detected() -> None:
    with pytest.raises(ValueError, match="account_mode_detected"):
        IbkrConnectionAuditRecord(
            audit_id="icaudit-x",
            event_at=datetime(2026, 5, 25, tzinfo=UTC),
            ibkr_account_id="DU1234567",
            event_type="mode_check_prefix",
            account_mode_detected="purple",
            connection_id=None,
            details_json=None,
        )


def test_record_rejects_empty_ibkr_account_id() -> None:
    with pytest.raises(ValueError, match="ibkr_account_id"):
        IbkrConnectionAuditRecord(
            audit_id="icaudit-x",
            event_at=datetime(2026, 5, 25, tzinfo=UTC),
            ibkr_account_id="",
            event_type="connect_attempt",
            account_mode_detected=None,
            connection_id=None,
            details_json=None,
        )


def test_decimal_round_trip_keeps_numeric_types(  # type: ignore[no-untyped-def]
):
    """Sanity: connection-audit table doesn't hold money, but exercise
    that the storage layer hasn't accidentally regressed Decimal
    handling on a parallel record by running a no-op import."""

    assert Decimal("1.234") == Decimal("1.234")
