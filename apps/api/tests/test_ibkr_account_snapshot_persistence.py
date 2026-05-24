from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
)

from portfolio_outlook_api.ibkr_account_snapshot_persistence import (
    map_preflight_to_persistence_payload,
    persist_account_snapshot_preflight_payload,
)
from portfolio_outlook_api.ibkr_account_snapshot_preflight import (
    IbkrAccountSnapshotPreflightResult,
)
from portfolio_outlook_api.ibkr_ibapi_account_snapshot_client import (
    IbkrAccountCashPreflightItem,
    IbkrPositionPreflightItem,
)


class FakeRepo:
    def __init__(self) -> None:
        self.sync_run: IbkrSyncRunRecord | None = None
        self.cash: list[IbkrAccountCashSnapshotRecord] = []
        self.positions: list[IbkrPositionSnapshotRecord] = []

    def save_ibkr_sync_run(self, record: IbkrSyncRunRecord) -> None:
        self.sync_run = record

    def save_ibkr_account_cash_snapshots(
        self,
        sync_run_id: str,
        records: list[IbkrAccountCashSnapshotRecord],
    ) -> None:
        assert all(r.sync_run_id == sync_run_id for r in records)
        self.cash = records

    def save_ibkr_position_snapshots(
        self,
        sync_run_id: str,
        records: list[IbkrPositionSnapshotRecord],
    ) -> None:
        assert all(r.sync_run_id == sync_run_id for r in records)
        self.positions = records


def _preflight() -> IbkrAccountSnapshotPreflightResult:
    return IbkrAccountSnapshotPreflightResult(
        status="snapshot_preflight_completed",
        status_nl="Afgerond",
        allowed=True,
        blocked=False,
        blocked_reasons=(),
        help_nl="Read-only",
        next_step_nl="Persist",
        account_mode="paper",
        account_mode_status="ok",
        expected_account_mode="paper",
        connect_attempted=True,
        account_summary_requested=True,
        account_summary_cancel_attempted=True,
        positions_requested=True,
        positions_cancel_attempted=True,
        disconnect_attempted=True,
        disconnect_error_ignored=False,
        cash_items=(
            IbkrAccountCashPreflightItem(
                tag="TotalCashValue",
                currency="USD",
                value=Decimal("1200.50"),
                source="ibkr",
                parse_status="parsed",
            ),
        ),
        positions=(
            IbkrPositionPreflightItem(
                account_mode="paper",
                masked_account_id="DU****123",
                symbol="MSFT",
                sec_type="STK",
                currency="USD",
                exchange="SMART",
                primary_exchange="NASDAQ",
                con_id=123,
                quantity=Decimal("5"),
                average_cost=Decimal("100.25"),
                source="ibkr",
            ),
        ),
        cash_item_count=1,
        position_count=1,
        snapshot_complete=True,
        snapshot_partial=False,
    )


def test_map_preflight_to_storage_payload() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    payload = map_preflight_to_persistence_payload(
        _preflight(),
        sync_run_id="run-1",
        persisted_at=now,
        snapshot_id_factory=lambda: "snap-1",
    )

    assert payload.sync_run.sync_run_id == "run-1"
    assert payload.sync_run.readonly is True
    assert payload.sync_run.actions_allowed is False
    assert payload.cash_snapshots[0].cash == Decimal("1200.50")
    assert payload.position_snapshots[0].symbol == "MSFT"
    assert payload.position_snapshots[0].conid == "123"


def test_persist_payload_writes_run_cash_and_positions() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    payload = map_preflight_to_persistence_payload(
        _preflight(),
        sync_run_id="run-2",
        persisted_at=now,
        snapshot_id_factory=lambda: "snap-2",
    )
    repo = FakeRepo()

    persist_account_snapshot_preflight_payload(repo, payload)

    assert repo.sync_run is not None
    assert repo.sync_run.sync_run_id == "run-2"
    assert len(repo.cash) == 1
    assert len(repo.positions) == 1
