from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

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
from portfolio_outlook_api.ibkr_sync_persistence import (
    IbkrSyncPersistencePayload,
    map_cash_snapshot_record,
    map_execution_snapshot_record,
    map_open_order_snapshot_record,
    map_position_snapshot_record,
    map_sync_run_record,
    persist_ibkr_sync_payload,
)


class FakeSnapshotRepository:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.sync_run: IbkrSyncRunRecord | None = None
        self.cash: list[IbkrAccountCashSnapshotRecord] = []
        self.positions: list[IbkrPositionSnapshotRecord] = []
        self.open_orders: list[IbkrOpenOrderSnapshotRecord] = []
        self.executions: list[IbkrExecutionSnapshotRecord] = []

    def save_ibkr_sync_run(self, record: IbkrSyncRunRecord) -> None:
        self.calls.append("save_ibkr_sync_run")
        self.sync_run = record

    def save_ibkr_account_cash_snapshots(
        self,
        sync_run_id: str,
        records: list[IbkrAccountCashSnapshotRecord],
    ) -> None:
        self.calls.append("save_ibkr_account_cash_snapshots")
        assert all(item.sync_run_id == sync_run_id for item in records)
        self.cash = records

    def save_ibkr_position_snapshots(
        self,
        sync_run_id: str,
        records: list[IbkrPositionSnapshotRecord],
    ) -> None:
        self.calls.append("save_ibkr_position_snapshots")
        assert all(item.sync_run_id == sync_run_id for item in records)
        self.positions = records

    def save_ibkr_open_order_snapshots(
        self,
        sync_run_id: str,
        records: list[IbkrOpenOrderSnapshotRecord],
    ) -> None:
        self.calls.append("save_ibkr_open_order_snapshots")
        assert all(item.sync_run_id == sync_run_id for item in records)
        self.open_orders = records

    def save_ibkr_execution_snapshots(
        self,
        sync_run_id: str,
        records: list[IbkrExecutionSnapshotRecord],
    ) -> None:
        self.calls.append("save_ibkr_execution_snapshots")
        assert all(item.sync_run_id == sync_run_id for item in records)
        self.executions = records


def test_map_cash_snapshot_preserves_decimal_and_none() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    cash = IbkrCash(
        account_ref="paper-1",
        base_currency="USD",
        cash=Decimal("1000.25"),
        available_funds=None,
        buying_power=Decimal("2500.50"),
    )

    record = map_cash_snapshot_record(
        sync_run_id="run-1",
        item=cash,
        received_at=now,
        stored_at=now,
        snapshot_id_factory=lambda: "cash-1",
    )

    assert isinstance(record.cash, Decimal)
    assert record.cash == Decimal("1000.25")
    assert record.available_funds is None
    assert isinstance(record.buying_power, Decimal)


def test_map_position_snapshot_preserves_values_and_conid_conversion() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    position = IbkrPosition(
        account_ref="paper-1",
        symbol="MSFT",
        security_type="STK",
        currency="USD",
        quantity=Decimal("12"),
        average_cost=Decimal("200.01"),
        conid=12345,
        exchange="SMART",
        primary_exchange="NASDAQ",
    )

    mapped_with_conid = map_position_snapshot_record(
        sync_run_id="run-1",
        item=position,
        received_at=now,
        stored_at=now,
        snapshot_id_factory=lambda: "pos-1",
    )

    assert isinstance(mapped_with_conid.quantity, Decimal)
    assert mapped_with_conid.conid == "12345"
    assert mapped_with_conid.exchange == "SMART"
    assert mapped_with_conid.primary_exchange == "NASDAQ"

    mapped_without_conid = map_position_snapshot_record(
        sync_run_id="run-1",
        item=IbkrPosition(
            account_ref="paper-1",
            symbol="MSFT",
            security_type="STK",
            currency="USD",
            quantity=Decimal("12"),
            average_cost=None,
            conid=None,
            exchange=None,
            primary_exchange=None,
        ),
        received_at=now,
        stored_at=now,
        snapshot_id_factory=lambda: "pos-2",
    )
    assert mapped_without_conid.conid is None


def test_map_open_order_snapshot_preserves_fields_and_safety_stays_read_only() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    item = IbkrOpenOrder(
        account_ref="paper-1",
        ibkr_order_id=99,
        ibkr_perm_id=None,
        parent_order_id=None,
        client_id=None,
        symbol="AAPL",
        security_type="STK",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        action_side="BUY",
        order_type="LMT",
        quantity=Decimal("2"),
        limit_price=Decimal("100.55"),
        stop_price=None,
        tif="DAY",
        status="Submitted",
        filled_quantity=Decimal("0"),
        remaining_quantity=Decimal("2"),
        average_fill_price=None,
        last_status_at=now,
        raw_status_reference="raw",
    )

    record = map_open_order_snapshot_record(
        sync_run_id="run-1",
        item=item,
        received_at=now,
        stored_at=now,
        snapshot_id_factory=lambda: "ord-1",
    )

    assert record.limit_price == Decimal("100.55")
    assert record.stop_price is None
    assert record.status == "Submitted"

    run_record = map_sync_run_record(
        sync_run_id="run-1",
        started_at=now,
        completed_at=now,
        provider_code="ibkr",
        provider_environment="paper",
        account_mode="paper",
        readonly=True,
        status="paper_account_confirmed",
        account_summary_status="account_summary_received",
        positions_status="positions_received",
        open_orders_status="open_orders_received",
        executions_status="executions_received",
        positions_count=1,
        cash_values_count=1,
        open_orders_count=1,
        executions_count=1,
        status_nl="ok",
        next_step_nl="geen",
        help_nl="read-only",
        stored_at=now,
    )
    assert run_record.actions_allowed is False
    assert run_record.order_submission_allowed is False
    assert run_record.order_modification_allowed is False
    assert run_record.order_cancellation_allowed is False
    assert run_record.suggestions_allowed is False


def test_map_execution_snapshot_preserves_decimal_none_and_timestamp() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    execution = IbkrExecution(
        account_ref="paper-1",
        execution_id="exec-1",
        ibkr_order_id=41,
        ibkr_perm_id=88,
        symbol="MSFT",
        security_type="STK",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        side="BOT",
        quantity=Decimal("5"),
        price=Decimal("310.10"),
        execution_time=now,
        commission=None,
        commission_currency=None,
        realized_pnl=None,
        raw_execution_reference="raw-exec",
    )

    record = map_execution_snapshot_record(
        sync_run_id="run-1",
        item=execution,
        received_at=now,
        stored_at=now,
        snapshot_id_factory=lambda: "exec-row-1",
    )

    assert isinstance(record.quantity, Decimal)
    assert isinstance(record.price, Decimal)
    assert record.commission is None
    assert record.realized_pnl is None
    assert record.execution_time == now


def test_persist_payload_calls_repository_in_expected_order() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    run = map_sync_run_record(
        sync_run_id="run-order",
        started_at=now,
        completed_at=now,
        provider_code="ibkr",
        provider_environment="paper",
        account_mode="paper",
        readonly=True,
        status="partial_data",
        account_summary_status="account_summary_received",
        positions_status="positions_received",
        open_orders_status="no_open_orders",
        executions_status="no_executions",
        positions_count=1,
        cash_values_count=1,
        open_orders_count=1,
        executions_count=1,
        status_nl=None,
        next_step_nl=None,
        help_nl=None,
        stored_at=now,
    )
    cash = map_cash_snapshot_record(
        sync_run_id="run-order",
        item=IbkrCash(
            account_ref="paper-1",
            base_currency="USD",
            cash=Decimal("100.00"),
            available_funds=Decimal("90.00"),
            buying_power=Decimal("180.00"),
        ),
        received_at=now,
        stored_at=now,
        snapshot_id_factory=lambda: "cash-order",
    )
    position = map_position_snapshot_record(
        sync_run_id="run-order",
        item=IbkrPosition(
            account_ref="paper-1",
            symbol="MSFT",
            security_type="STK",
            currency="USD",
            quantity=Decimal("1"),
            average_cost=Decimal("250.00"),
            conid=123,
        ),
        received_at=now,
        stored_at=now,
        snapshot_id_factory=lambda: "pos-order",
    )
    order = map_open_order_snapshot_record(
        sync_run_id="run-order",
        item=IbkrOpenOrder(
            account_ref="paper-1",
            ibkr_order_id=1,
            ibkr_perm_id=None,
            parent_order_id=None,
            client_id=None,
            symbol="MSFT",
            security_type="STK",
            currency="USD",
            exchange=None,
            primary_exchange=None,
            action_side="BUY",
            order_type="LMT",
            quantity=Decimal("1"),
            limit_price=Decimal("200.00"),
            stop_price=None,
            tif="DAY",
            status="Submitted",
            filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("1"),
            average_fill_price=None,
            last_status_at=None,
            raw_status_reference=None,
        ),
        received_at=now,
        stored_at=now,
        snapshot_id_factory=lambda: "ord-order",
    )
    execution = map_execution_snapshot_record(
        sync_run_id="run-order",
        item=IbkrExecution(
            account_ref="paper-1",
            execution_id="exec-order",
            ibkr_order_id=1,
            ibkr_perm_id=None,
            symbol="MSFT",
            security_type="STK",
            currency="USD",
            exchange=None,
            primary_exchange=None,
            side="BOT",
            quantity=Decimal("1"),
            price=Decimal("200.00"),
            execution_time=now,
            commission=Decimal("0.10"),
            commission_currency="USD",
            realized_pnl=None,
            raw_execution_reference=None,
        ),
        received_at=now,
        stored_at=now,
        snapshot_id_factory=lambda: "exec-order",
    )

    repo = FakeSnapshotRepository()
    payload = IbkrSyncPersistencePayload(
        sync_run=run,
        cash_snapshots=[cash],
        position_snapshots=[position],
        open_order_snapshots=[order],
        execution_snapshots=[execution],
    )

    persist_ibkr_sync_payload(payload, repo)

    assert repo.calls == [
        "save_ibkr_sync_run",
        "save_ibkr_account_cash_snapshots",
        "save_ibkr_position_snapshots",
        "save_ibkr_open_order_snapshots",
        "save_ibkr_execution_snapshots",
    ]
    assert isinstance(repo.cash[0].cash, Decimal)
    assert isinstance(repo.positions[0].quantity, Decimal)
    assert isinstance(repo.open_orders[0].limit_price, Decimal)
    assert isinstance(repo.executions[0].price, Decimal)
