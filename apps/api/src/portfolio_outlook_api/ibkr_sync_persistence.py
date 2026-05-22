from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    IbkrAccountCashSnapshotRecord,
    IbkrExecutionSnapshotRecord,
    IbkrOpenOrderSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
)

from portfolio_outlook_api.ibkr_sync import (
    IbkrCash,
    IbkrExecution,
    IbkrOpenOrder,
    IbkrPosition,
)

SnapshotIdFactory = Callable[[], str]


class IbkrSyncPersistenceRepository(Protocol):
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

    def save_ibkr_open_order_snapshots(
        self,
        sync_run_id: str,
        records: list[IbkrOpenOrderSnapshotRecord],
    ) -> None: ...

    def save_ibkr_execution_snapshots(
        self,
        sync_run_id: str,
        records: list[IbkrExecutionSnapshotRecord],
    ) -> None: ...


@dataclass(frozen=True)
class IbkrSyncPersistencePayload:
    sync_run: IbkrSyncRunRecord
    cash_snapshots: list[IbkrAccountCashSnapshotRecord]
    position_snapshots: list[IbkrPositionSnapshotRecord]
    open_order_snapshots: list[IbkrOpenOrderSnapshotRecord]
    execution_snapshots: list[IbkrExecutionSnapshotRecord]


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _default_snapshot_id_factory() -> str:
    return str(uuid4())


def map_sync_run_record(
    *,
    sync_run_id: str,
    started_at: datetime,
    completed_at: datetime | None,
    provider_code: str,
    provider_environment: str,
    account_mode: str,
    readonly: bool,
    status: str,
    account_summary_status: str,
    positions_status: str,
    open_orders_status: str,
    executions_status: str,
    positions_count: int,
    cash_values_count: int,
    open_orders_count: int,
    executions_count: int,
    status_nl: str | None,
    next_step_nl: str | None,
    help_nl: str | None,
    stored_at: datetime | None = None,
) -> IbkrSyncRunRecord:
    return IbkrSyncRunRecord(
        sync_run_id=sync_run_id,
        started_at=started_at,
        completed_at=completed_at,
        provider_code=provider_code,
        provider_environment=provider_environment,
        account_mode=account_mode,
        readonly=readonly,
        status=status,
        account_summary_status=account_summary_status,
        positions_status=positions_status,
        open_orders_status=open_orders_status,
        executions_status=executions_status,
        positions_count=positions_count,
        cash_values_count=cash_values_count,
        open_orders_count=open_orders_count,
        executions_count=executions_count,
        status_nl=status_nl,
        next_step_nl=next_step_nl,
        help_nl=help_nl,
        actions_allowed=False,
        order_submission_allowed=False,
        order_modification_allowed=False,
        order_cancellation_allowed=False,
        suggestions_allowed=False,
        stored_at=stored_at or _now_utc(),
    )


def map_cash_snapshot_record(
    *,
    sync_run_id: str,
    item: IbkrCash,
    received_at: datetime,
    stored_at: datetime,
    snapshot_id_factory: SnapshotIdFactory = _default_snapshot_id_factory,
) -> IbkrAccountCashSnapshotRecord:
    return IbkrAccountCashSnapshotRecord(
        snapshot_id=snapshot_id_factory(),
        sync_run_id=sync_run_id,
        account_ref=item.account_ref,
        base_currency=item.base_currency,
        cash=item.cash,
        available_funds=item.available_funds,
        buying_power=item.buying_power,
        received_at=received_at,
        stored_at=stored_at,
    )


def map_position_snapshot_record(
    *,
    sync_run_id: str,
    item: IbkrPosition,
    received_at: datetime,
    stored_at: datetime,
    snapshot_id_factory: SnapshotIdFactory = _default_snapshot_id_factory,
) -> IbkrPositionSnapshotRecord:
    conid = None if item.conid is None else str(item.conid)
    return IbkrPositionSnapshotRecord(
        snapshot_id=snapshot_id_factory(),
        sync_run_id=sync_run_id,
        account_ref=item.account_ref,
        conid=conid,
        symbol=item.symbol,
        security_type=item.security_type,
        currency=item.currency,
        exchange=item.exchange,
        primary_exchange=item.primary_exchange,
        quantity=item.quantity,
        average_cost=item.average_cost,
        received_at=received_at,
        stored_at=stored_at,
    )


def map_open_order_snapshot_record(
    *,
    sync_run_id: str,
    item: IbkrOpenOrder,
    received_at: datetime,
    stored_at: datetime,
    snapshot_id_factory: SnapshotIdFactory = _default_snapshot_id_factory,
) -> IbkrOpenOrderSnapshotRecord:
    return IbkrOpenOrderSnapshotRecord(
        snapshot_id=snapshot_id_factory(),
        sync_run_id=sync_run_id,
        account_ref=item.account_ref,
        ibkr_order_id=item.ibkr_order_id,
        ibkr_perm_id=item.ibkr_perm_id,
        parent_order_id=item.parent_order_id,
        client_id=item.client_id,
        symbol=item.symbol,
        security_type=item.security_type,
        currency=item.currency,
        exchange=item.exchange,
        primary_exchange=item.primary_exchange,
        action_side=item.action_side,
        order_type=item.order_type,
        quantity=item.quantity,
        limit_price=item.limit_price,
        stop_price=item.stop_price,
        tif=item.tif,
        status=item.status,
        filled_quantity=item.filled_quantity,
        remaining_quantity=item.remaining_quantity,
        average_fill_price=item.average_fill_price,
        last_status_at=item.last_status_at,
        raw_status_reference=item.raw_status_reference,
        received_at=received_at,
        stored_at=stored_at,
    )


def map_execution_snapshot_record(
    *,
    sync_run_id: str,
    item: IbkrExecution,
    received_at: datetime,
    stored_at: datetime,
    snapshot_id_factory: SnapshotIdFactory = _default_snapshot_id_factory,
) -> IbkrExecutionSnapshotRecord:
    return IbkrExecutionSnapshotRecord(
        snapshot_id=snapshot_id_factory(),
        sync_run_id=sync_run_id,
        account_ref=item.account_ref,
        execution_id=item.execution_id,
        ibkr_order_id=item.ibkr_order_id,
        ibkr_perm_id=item.ibkr_perm_id,
        symbol=item.symbol,
        security_type=item.security_type,
        currency=item.currency,
        exchange=item.exchange,
        primary_exchange=item.primary_exchange,
        side=item.side,
        quantity=item.quantity,
        price=item.price,
        execution_time=item.execution_time,
        commission=item.commission,
        commission_currency=item.commission_currency,
        realized_pnl=item.realized_pnl,
        raw_execution_reference=item.raw_execution_reference,
        received_at=received_at,
        stored_at=stored_at,
    )


def persist_ibkr_sync_payload(
    payload: IbkrSyncPersistencePayload,
    repository: IbkrSyncPersistenceRepository,
) -> None:
    sync_run_id = payload.sync_run.sync_run_id
    repository.save_ibkr_sync_run(payload.sync_run)
    repository.save_ibkr_account_cash_snapshots(sync_run_id, payload.cash_snapshots)
    repository.save_ibkr_position_snapshots(sync_run_id, payload.position_snapshots)
    repository.save_ibkr_open_order_snapshots(sync_run_id, payload.open_order_snapshots)
    repository.save_ibkr_execution_snapshots(sync_run_id, payload.execution_snapshots)
