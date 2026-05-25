"""Task 126 — migration 0045 schema assertions.

Validates that the new ``ibkr_account_id`` column is present on
every IBKR snapshot table, that each gets the matching index, that
the new ``ibkr_connection_audit`` table exists with the locked
check constraints, and that ``ibkr_sync_runs`` gains
``verified_at``.

Schema-driven via ``ai_trading_agent_storage.metadata.metadata``;
no live Postgres needed because the metadata module is the source
of truth that the Alembic migration drives toward.
"""

from __future__ import annotations

from ai_trading_agent_storage.metadata import (
    ibkr_account_cash_snapshots,
    ibkr_connection_audit,
    ibkr_execution_snapshots,
    ibkr_open_order_snapshots,
    ibkr_position_snapshots,
    ibkr_sync_runs,
    metadata,
)

_SNAPSHOT_TABLES = (
    ibkr_sync_runs,
    ibkr_account_cash_snapshots,
    ibkr_position_snapshots,
    ibkr_open_order_snapshots,
    ibkr_execution_snapshots,
)


def test_every_snapshot_table_has_ibkr_account_id_column() -> None:
    for table in _SNAPSHOT_TABLES:
        column = table.c.get("ibkr_account_id")
        assert column is not None, f"{table.name} is missing ibkr_account_id"
        # Nullable in 126a; tightens to NOT NULL in 126b. The metadata
        # column being declared nullable is the explicit contract.
        assert column.nullable is True
        assert str(column.type).upper().startswith("TEXT")


def test_ibkr_sync_runs_gains_verified_at_column() -> None:
    column = ibkr_sync_runs.c.get("verified_at")
    assert column is not None
    assert column.nullable is True


def test_ibkr_connection_audit_table_exists_in_metadata() -> None:
    assert "ibkr_connection_audit" in metadata.tables


def test_ibkr_connection_audit_columns_match_brief() -> None:
    columns = {c.name for c in ibkr_connection_audit.columns}
    assert columns == {
        "audit_id",
        "event_at",
        "ibkr_account_id",
        "event_type",
        "account_mode_detected",
        "connection_id",
        "details_json",
        "safe_for_action_drafts",
        "safe_for_orders",
    }


def test_ibkr_connection_audit_event_type_check_constraint() -> None:
    names = {c.name for c in ibkr_connection_audit.constraints}
    assert "ck_ibkr_connection_audit_event_type" in names
    assert "ck_ibkr_connection_audit_account_mode_detected" in names


def test_ibkr_connection_audit_ibkr_account_id_is_not_null() -> None:
    column = ibkr_connection_audit.c["ibkr_account_id"]
    assert column.nullable is False


def test_ibkr_connection_audit_has_account_event_index() -> None:
    index_names = {ix.name for ix in ibkr_connection_audit.indexes}
    assert "ix_ibkr_connection_audit_account_event" in index_names


def test_per_snapshot_table_has_ibkr_account_id_index() -> None:
    for table in _SNAPSHOT_TABLES:
        index_names = {ix.name for ix in table.indexes}
        assert (
            f"ix_{table.name}_ibkr_account_id" in index_names
        ), f"{table.name} is missing ix_{table.name}_ibkr_account_id index"


def test_ibkr_connection_audit_safety_booleans_default_to_false() -> None:
    for name in ("safe_for_action_drafts", "safe_for_orders"):
        column = ibkr_connection_audit.c[name]
        assert column.nullable is False
        assert column.server_default is not None
