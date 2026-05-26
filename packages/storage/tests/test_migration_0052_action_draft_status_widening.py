"""Task 134a — verify the action_drafts.status CHECK constraint now
accepts the nine in-flight + terminal statuses Task 134 adds, while
preserving every Task 133 status as still valid.

The check runs against an in-memory SQLite db built from the
SQLAlchemy metadata (which mirrors the migration). The CHECK
constraint string is enforced by SQLite for direct INSERTs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from ai_trading_agent_storage.metadata import action_drafts, metadata

_BASE_TS = datetime(2026, 5, 26, 9, 0, tzinfo=UTC)


_TASK_133_STATUSES = (
    "proposed",
    "edited",
    "user_approved",
    "dismissed",
    "deleted",
    "superseded",
)
_TASK_134_STATUSES = (
    "submitted",
    "accepted",
    "working",
    "filled",
    "partially_filled",
    "cancelled",
    "rejected",
    "pending_cancellation",
    "awaiting_reply_timeout",
)


def _draft_payload(*, draft_id: str, status: str) -> dict[str, object]:
    return {
        "action_draft_id": draft_id,
        "decision_package_id": None,
        "forecast_run_id": None,
        "created_at": _BASE_TS,
        "created_by": "user",
        "ibkr_account_id": "DU1234567",
        "conid": "ASML.AS",
        "symbol": "ASML",
        "exchange": "AEB",
        "currency_local": "EUR",
        "side": "BUY",
        "quantity": Decimal("1"),
        "order_type": "LMT",
        "limit_price_local": Decimal("100"),
        "time_in_force": "DAY",
        "notional_local": Decimal("100"),
        "notional_eur": Decimal("100"),
        "fx_rate_at_creation": Decimal("1"),
        "usable_cash_eur_at_creation": Decimal("1000"),
        "held_quantity_at_creation": None,
        "status": status,
        "last_edited_at": None,
        "user_approved_at": None,
        "dismissed_at": None,
        "deleted_at": None,
        "dismissed_reason": None,
        "user_note": None,
        "superseded_by_decision_package_id": None,
        "audit_trail_hash": f"hash-{draft_id}",
        "previous_draft_hash": None,
        "safe_for_submission": False,
        "submission_block_reason": None,
        "submission_started_at": None,
        "terminal_state_at": None,
    }


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def test_every_task_133_status_still_accepted() -> None:
    with _conn() as conn:
        for index, status in enumerate(_TASK_133_STATUSES):
            payload = _draft_payload(
                draft_id=f"draft-{index}", status=status
            )
            conn.execute(action_drafts.insert().values(**payload))


def test_every_task_134_status_accepted() -> None:
    with _conn() as conn:
        for index, status in enumerate(_TASK_134_STATUSES):
            payload = _draft_payload(
                draft_id=f"draft-{index}", status=status
            )
            conn.execute(action_drafts.insert().values(**payload))


def test_unknown_status_rejected() -> None:
    with _conn() as conn:
        payload = _draft_payload(
            draft_id="draft-bogus", status="totally_not_a_status"
        )
        with pytest.raises(IntegrityError):
            conn.execute(action_drafts.insert().values(**payload))


def test_submission_block_reason_check_accepts_locked_values() -> None:
    with _conn() as conn:
        for index, reason in enumerate(
            (
                "cash_insufficient",
                "mode_mismatch",
                "connection_down",
                "account_id_mismatch",
                "duplicate_in_flight",
                "market_closed",
                "cooldown",
                "daily_limit",
                "soft_drawdown",
                "hard_drawdown",
                "fomo",
                "tick_size_invalid",
                "unknown",
            )
        ):
            payload = _draft_payload(
                draft_id=f"draft-{index}", status="user_approved"
            )
            payload["submission_block_reason"] = reason
            conn.execute(action_drafts.insert().values(**payload))


def test_submission_block_reason_unknown_value_rejected() -> None:
    with _conn() as conn:
        payload = _draft_payload(
            draft_id="draft-x", status="user_approved"
        )
        payload["submission_block_reason"] = "bogus"
        with pytest.raises(IntegrityError):
            conn.execute(action_drafts.insert().values(**payload))


def test_submission_block_reason_null_still_allowed() -> None:
    with _conn() as conn:
        payload = _draft_payload(
            draft_id="draft-null", status="user_approved"
        )
        payload["submission_block_reason"] = None
        conn.execute(action_drafts.insert().values(**payload))


def test_safe_for_submission_true_still_rejected() -> None:
    with _conn() as conn:
        payload = _draft_payload(
            draft_id="draft-unsafe", status="user_approved"
        )
        payload["safe_for_submission"] = True
        with pytest.raises(IntegrityError):
            conn.execute(action_drafts.insert().values(**payload))
