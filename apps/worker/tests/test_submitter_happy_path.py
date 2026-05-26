"""Task 134b — submitter happy path tests.

Drives ``IbkrSubmitter.submit(draft)`` with a fake ``IbkrSubmitProtocol``
adapter against a real (in-memory SQLite) action_draft + submission
audit repository pair. Asserts:

* one ``ibkr_submission_audit`` row with ``result="placed"`` is
  written carrying the live account ID + perm_id + contract/order
  JSON,
* the draft transitions ``user_approved`` → ``submitted`` with
  ``submission_started_at`` set,
* the returned ``SubmissionResult`` carries the perm_id + audit_id.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from ai_trading_agent_storage import (
    ActionDraftEntry,
    SqlAlchemyActionDraftRepository,
    SqlAlchemyIbkrSubmissionAuditRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine

from portfolio_outlook_worker.ibkr_submission.order_builder import TickSize
from portfolio_outlook_worker.ibkr_submission.submitter import (
    IbkrSubmitter,
    SubmittedTrade,
)

_LATEST = "0052_ibkr_submission_lifecycle_audit_and_executions"
_NOW = datetime(2026, 5, 26, 10, 0, tzinfo=UTC)


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


def _draft(
    *,
    draft_id: str = "draft-1",
    account_id: str = "DU1234567",
    quantity: Decimal = Decimal("6"),
    limit_price: Decimal = Decimal("638.72"),
) -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id=draft_id,
        decision_package_id=None,
        forecast_run_id=None,
        created_at=_NOW - timedelta(minutes=10),
        created_by="user",
        ibkr_account_id=account_id,
        conid="12345",  # IBKR contract IDs are numeric strings
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        side="BUY",
        quantity=quantity,
        order_type="LMT",
        limit_price_local=limit_price,
        time_in_force="DAY",
        notional_local=quantity * limit_price,
        notional_eur=quantity * limit_price,
        fx_rate_at_creation=Decimal("1"),
        usable_cash_eur_at_creation=Decimal("50000"),
        held_quantity_at_creation=None,
        status="user_approved",
        last_edited_at=None,
        user_approved_at=_NOW - timedelta(minutes=5),
        dismissed_at=None,
        deleted_at=None,
        dismissed_reason=None,
        user_note=None,
        superseded_by_decision_package_id=None,
        audit_trail_hash="h-1",
        previous_draft_hash=None,
        safe_for_submission=False,
    )


class _FakeAdapter:
    """Minimal ``IbkrSubmitProtocol`` impl that records calls."""

    def __init__(
        self,
        *,
        live_account_id: str = "DU1234567",
        account_mode: Literal["paper", "live"] = "paper",
        tick: TickSize | None = None,
        perm_id: int = 100100,
        order_id: int = 7,
    ) -> None:
        self.gateway_session_id = "sess-1"
        self.account_mode = account_mode
        self._live_account_id = live_account_id
        self._tick = tick or TickSize(tick_size_local=Decimal("0.005"))
        self._perm_id = perm_id
        self._order_id = order_id
        self.place_order_calls: list[tuple[Any, Any]] = []
        self.tick_calls: list[dict[str, Any]] = []

    def fetch_managed_account_id(self) -> str:
        return self._live_account_id

    def fetch_tick_size(
        self,
        *,
        symbol: str,
        exchange: str,
        currency: str,
        conid: int | None,
    ) -> TickSize:
        self.tick_calls.append(
            {
                "symbol": symbol,
                "exchange": exchange,
                "currency": currency,
                "conid": conid,
            }
        )
        return self._tick

    def place_order(self, contract: Any, order: Any) -> SubmittedTrade:
        self.place_order_calls.append((contract, order))
        return SubmittedTrade(
            perm_id=self._perm_id,
            order_id=self._order_id,
            contract_dict={
                "symbol": contract.symbol,
                "exchange": contract.exchange,
                "currency": contract.currency,
            },
            order_dict={
                "action": order.action,
                "totalQuantity": order.totalQuantity,
                "orderType": order.orderType,
                "lmtPrice": order.lmtPrice,
                "tif": order.tif,
            },
        )

    def cancel_order(self, perm_id: int) -> None:  # pragma: no cover
        raise NotImplementedError


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def _seed(conn) -> tuple[SqlAlchemyActionDraftRepository, SqlAlchemyIbkrSubmissionAuditRepository]:  # type: ignore[no-untyped-def]
    draft_repo = SqlAlchemyActionDraftRepository(conn, _report())
    audit_repo = SqlAlchemyIbkrSubmissionAuditRepository(conn, _report())
    # _draft() already returns status="user_approved" — append directly.
    draft_repo.append(_draft())
    return draft_repo, audit_repo


def test_happy_path_writes_audit_and_transitions_to_submitted() -> None:
    with _conn() as conn:
        draft_repo, audit_repo = _seed(conn)
        adapter = _FakeAdapter()
        submitter = IbkrSubmitter(
            submit_adapter=adapter,
            action_draft_repo=draft_repo,
            audit_repo=audit_repo,
            now_provider=lambda: _NOW,
        )
        draft = draft_repo.get_by_id("draft-1")
        assert draft is not None and draft.status == "user_approved"
        result = submitter.submit(draft)

        assert result.ok is True
        assert result.perm_id == 100100
        assert result.audit_id is not None
        assert result.block_reason is None

        # Draft moved to submitted with timestamp set.
        after = draft_repo.get_by_id("draft-1")
        assert after is not None
        assert after.status == "submitted"
        # SQLite drops the timezone on round-trip; compare naive values.
        assert after.submission_started_at is not None
        assert after.submission_started_at.replace(tzinfo=UTC) == _NOW
        assert after.submission_block_reason is None

        # Audit row written.
        rows = audit_repo.list_for_account(
            ibkr_account_id="DU1234567"
        )
        assert len(rows) == 1
        assert rows[0].result == "placed"
        assert rows[0].ibkr_perm_id == 100100
        assert rows[0].ibkr_order_id == 7
        assert rows[0].sent_to_account_id == "DU1234567"
        assert rows[0].sent_account_mode == "paper"
        assert rows[0].contract_json["symbol"] == "ASML"
        assert rows[0].order_json["lmtPrice"] == 638.72


def test_account_id_mismatch_at_tier_two_blocks() -> None:
    """Draft says DU1234567 but the live adapter reports U7654321 — the
    Tier 2 per-submit check refuses the order, writes a rejected_at_send
    audit row, and leaves the draft at user_approved with the Dutch
    block reason."""
    with _conn() as conn:
        draft_repo, audit_repo = _seed(conn)
        adapter = _FakeAdapter(live_account_id="U7654321", account_mode="live")
        submitter = IbkrSubmitter(
            submit_adapter=adapter,
            action_draft_repo=draft_repo,
            audit_repo=audit_repo,
            now_provider=lambda: _NOW,
        )
        draft = draft_repo.get_by_id("draft-1")
        assert draft is not None
        result = submitter.submit(draft)

        assert result.ok is False
        assert result.block_reason == "account_id_mismatch"
        assert result.perm_id is None
        assert (
            result.error_message_dutch is not None
            and "account" in result.error_message_dutch.lower()
        )

        after = draft_repo.get_by_id("draft-1")
        assert after is not None
        assert after.status == "user_approved"  # stays here
        assert after.submission_block_reason == "account_id_mismatch"

        # The audit row is filed against the DRAFT's account_id (what
        # the user expected); the live account ID that didn't match is
        # carried in error_class + error_message_dutch.
        rows = audit_repo.list_for_account(
            ibkr_account_id="DU1234567"
        )
        assert len(rows) == 1
        assert rows[0].result == "rejected_at_send"
        assert rows[0].error_class == "AccountIdMismatchError"
        # No placeOrder call was attempted.
        assert adapter.place_order_calls == []


def test_submit_round_trips_decimal_quantities_and_prices() -> None:
    with _conn() as conn:
        draft_repo, audit_repo = _seed(conn)
        adapter = _FakeAdapter()
        submitter = IbkrSubmitter(
            submit_adapter=adapter,
            action_draft_repo=draft_repo,
            audit_repo=audit_repo,
            now_provider=lambda: _NOW,
        )
        draft = draft_repo.get_by_id("draft-1")
        assert draft is not None
        submitter.submit(draft)

        # The adapter received an order with float fields, but the
        # draft itself stayed Decimal — verified by re-reading the row.
        after = draft_repo.get_by_id("draft-1")
        assert after is not None
        assert after.quantity == Decimal("6")
        assert after.limit_price_local == Decimal("638.72")


def test_submit_rejects_non_user_approved_draft() -> None:
    import pytest

    with _conn() as conn:
        draft_repo, audit_repo = _seed(conn)
        # Transition past user_approved by submitting once.
        adapter = _FakeAdapter()
        submitter = IbkrSubmitter(
            submit_adapter=adapter,
            action_draft_repo=draft_repo,
            audit_repo=audit_repo,
            now_provider=lambda: _NOW,
        )
        draft = draft_repo.get_by_id("draft-1")
        assert draft is not None
        submitter.submit(draft)
        # Now in 'submitted' — second submit attempt must reject.
        again = draft_repo.get_by_id("draft-1")
        assert again is not None and again.status == "submitted"
        with pytest.raises(ValueError):
            submitter.submit(again)
