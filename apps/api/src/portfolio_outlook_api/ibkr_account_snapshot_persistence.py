from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
)

from portfolio_outlook_api.ibkr_account_snapshot_preflight import (
    IbkrAccountSnapshotPreflightResult,
)
from portfolio_outlook_api.ibkr_ibapi_account_snapshot_client import (
    IbkrAccountCashPreflightItem,
    IbkrPositionPreflightItem,
)

SnapshotIdFactory = Callable[[], str]


class IbkrAccountSnapshotPersistenceRepository(Protocol):
    def save_ibkr_sync_run(self, record: IbkrSyncRunRecord) -> None: ...

    def save_ibkr_account_cash_snapshots(
        self,
        sync_run_id: str,
        records: list[IbkrAccountCashSnapshotRecord],
    ) -> None: ...

    def save_ibkr_position_snapshots(
        self,
        sync_run_id: str,
        records: list[IbkrPositionSnapshotRecord],
    ) -> None: ...


@dataclass(frozen=True)
class IbkrAccountSnapshotPersistencePayload:
    sync_run: IbkrSyncRunRecord
    cash_snapshots: list[IbkrAccountCashSnapshotRecord]
    position_snapshots: list[IbkrPositionSnapshotRecord]


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _default_snapshot_id_factory() -> str:
    return str(uuid4())


def _map_cash_value(value: Decimal | str) -> Decimal | None:
    return value if isinstance(value, Decimal) else None


def map_preflight_to_persistence_payload(
    preflight: IbkrAccountSnapshotPreflightResult,
    *,
    sync_run_id: str,
    persisted_at: datetime | None = None,
    snapshot_id_factory: SnapshotIdFactory = _default_snapshot_id_factory,
) -> IbkrAccountSnapshotPersistencePayload:
    stored_at = persisted_at or _now_utc()
    run = IbkrSyncRunRecord(
        sync_run_id=sync_run_id,
        started_at=stored_at,
        completed_at=stored_at,
        provider_code="ibkr",
        provider_environment=preflight.account_mode or "unknown",
        account_mode=preflight.account_mode or "unknown",
        readonly=True,
        status=preflight.status,
        account_summary_status=(
            "account_summary_received" if preflight.account_summary_requested else "not_requested"
        ),
        positions_status="positions_received" if preflight.positions_requested else "not_requested",
        open_orders_status="not_requested",
        executions_status="not_requested",
        positions_count=preflight.position_count,
        cash_values_count=preflight.cash_item_count,
        open_orders_count=0,
        executions_count=0,
        status_nl=preflight.status_nl,
        next_step_nl=preflight.next_step_nl,
        help_nl=preflight.help_nl,
        actions_allowed=False,
        order_submission_allowed=False,
        order_modification_allowed=False,
        order_cancellation_allowed=False,
        suggestions_allowed=False,
        stored_at=stored_at,
    )

    cash: list[IbkrAccountCashSnapshotRecord] = [
        map_cash_preflight_item(
            sync_run_id=sync_run_id,
            item=item,
            stored_at=stored_at,
            snapshot_id_factory=snapshot_id_factory,
        )
        for item in preflight.cash_items
    ]
    positions: list[IbkrPositionSnapshotRecord] = [
        map_position_preflight_item(
            sync_run_id=sync_run_id,
            item=item,
            stored_at=stored_at,
            snapshot_id_factory=snapshot_id_factory,
        )
        for item in preflight.positions
    ]
    return IbkrAccountSnapshotPersistencePayload(run, cash, positions)


def map_cash_preflight_item(
    *,
    sync_run_id: str,
    item: IbkrAccountCashPreflightItem,
    stored_at: datetime,
    snapshot_id_factory: SnapshotIdFactory = _default_snapshot_id_factory,
) -> IbkrAccountCashSnapshotRecord:
    return IbkrAccountCashSnapshotRecord(
        snapshot_id=snapshot_id_factory(),
        sync_run_id=sync_run_id,
        account_ref=None,
        base_currency=item.currency or "UNKNOWN",
        cash=_map_cash_value(item.value) if item.tag == "TotalCashValue" else None,
        available_funds=_map_cash_value(item.value) if item.tag == "AvailableFunds" else None,
        buying_power=_map_cash_value(item.value) if item.tag == "BuyingPower" else None,
        received_at=stored_at,
        stored_at=stored_at,
    )


def map_position_preflight_item(
    *,
    sync_run_id: str,
    item: IbkrPositionPreflightItem,
    stored_at: datetime,
    snapshot_id_factory: SnapshotIdFactory = _default_snapshot_id_factory,
) -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id=snapshot_id_factory(),
        sync_run_id=sync_run_id,
        account_ref=item.masked_account_id,
        conid=None if item.con_id is None else str(item.con_id),
        symbol=item.symbol or "UNKNOWN",
        security_type=item.sec_type or "UNKNOWN",
        currency=item.currency or "UNKNOWN",
        exchange=item.exchange,
        primary_exchange=item.primary_exchange,
        quantity=item.quantity,
        average_cost=item.average_cost,
        received_at=stored_at,
        stored_at=stored_at,
    )


def persist_account_snapshot_preflight_payload(
    repository: IbkrAccountSnapshotPersistenceRepository,
    payload: IbkrAccountSnapshotPersistencePayload,
) -> None:
    repository.save_ibkr_sync_run(payload.sync_run)
    repository.save_ibkr_account_cash_snapshots(
        payload.sync_run.sync_run_id,
        payload.cash_snapshots,
    )
    repository.save_ibkr_position_snapshots(
        payload.sync_run.sync_run_id,
        payload.position_snapshots,
    )
