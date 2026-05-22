from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from portfolio_outlook_api.config import Settings


@dataclass(frozen=True)
class IbkrPosition:
    account_ref: str
    symbol: str
    security_type: str
    currency: str
    quantity: Decimal
    average_cost: Decimal | None
    conid: int | None = None
    exchange: str | None = None
    primary_exchange: str | None = None


@dataclass(frozen=True)
class IbkrCash:
    account_ref: str
    base_currency: str
    cash: Decimal
    available_funds: Decimal | None
    buying_power: Decimal | None


@dataclass(frozen=True)
class IbkrOpenOrder:
    account_ref: str
    ibkr_order_id: int
    ibkr_perm_id: int | None
    parent_order_id: int | None
    client_id: int | None
    symbol: str
    security_type: str
    currency: str
    exchange: str | None
    primary_exchange: str | None
    action_side: str
    order_type: str
    quantity: Decimal
    limit_price: Decimal | None
    stop_price: Decimal | None
    tif: str | None
    status: str
    filled_quantity: Decimal
    remaining_quantity: Decimal
    average_fill_price: Decimal | None
    last_status_at: datetime | None
    raw_status_reference: str | None


@dataclass(frozen=True)
class IbkrExecution:
    account_ref: str
    execution_id: str
    ibkr_order_id: int
    ibkr_perm_id: int | None
    symbol: str
    security_type: str
    currency: str
    exchange: str | None
    primary_exchange: str | None
    side: str
    quantity: Decimal
    price: Decimal
    execution_time: datetime
    commission: Decimal | None
    commission_currency: str | None
    realized_pnl: Decimal | None
    raw_execution_reference: str | None


class IbkrReadOnlyAdapter:
    def sync_account_summary(self) -> list[IbkrCash]:
        raise NotImplementedError

    def sync_positions(self) -> list[IbkrPosition]:
        raise NotImplementedError

    def sync_open_orders(self) -> list[IbkrOpenOrder]:
        raise NotImplementedError

    def sync_executions(self) -> list[IbkrExecution]:
        raise NotImplementedError


class NotConfiguredIbkrAdapter(IbkrReadOnlyAdapter):
    def sync_account_summary(self) -> list[IbkrCash]:
        return []

    def sync_positions(self) -> list[IbkrPosition]:
        return []

    def sync_open_orders(self) -> list[IbkrOpenOrder]:
        return []

    def sync_executions(self) -> list[IbkrExecution]:
        return []


class InMemoryIbkrSyncStore:
    def __init__(self) -> None:
        self.runs: list[dict[str, object]] = []
        self.positions: list[dict[str, object]] = []
        self.cash: list[dict[str, object]] = []
        self.open_orders: list[dict[str, object]] = []
        self.executions: list[dict[str, object]] = []


STORE = InMemoryIbkrSyncStore()


def _configured(settings: Settings) -> bool:
    return bool(
        settings.ibkr_sync_enabled
        and settings.ibkr_sync_host
        and settings.ibkr_sync_port is not None
        and settings.ibkr_sync_client_id is not None
    )


def run_sync(settings: Settings, adapter: IbkrReadOnlyAdapter | None = None) -> dict[str, object]:
    now = datetime.now(UTC)
    run_id = f"ibkr-sync-{uuid4()}"
    result_status = "disabled"
    account_summary_status = "disabled"
    positions_status = "disabled"
    open_orders_status = "disabled"
    executions_status = "disabled"
    positions: list[IbkrPosition] = []
    cash_items: list[IbkrCash] = []
    open_orders: list[IbkrOpenOrder] = []
    executions: list[IbkrExecution] = []

    if not settings.ibkr_sync_enabled:
        result_status = "disabled"
    elif settings.ibkr_sync_account_mode.lower() != "paper":
        result_status = "wrong_account_mode"
    elif not settings.ibkr_sync_readonly:
        result_status = "provider_error"
    elif not _configured(settings):
        result_status = "not_configured"
    else:
        active_adapter = adapter or NotConfiguredIbkrAdapter()
        try:
            cash_items = active_adapter.sync_account_summary()
            positions = active_adapter.sync_positions()
            open_orders = active_adapter.sync_open_orders()
            executions = active_adapter.sync_executions()
            account_summary_status = "account_summary_received" if cash_items else "partial_data"
            positions_status = "positions_received" if positions else "partial_data"
            open_orders_status = "open_orders_received" if open_orders else "no_open_orders"
            executions_status = "executions_received" if executions else "no_executions"
            result_status = "partial_data"
            if cash_items and positions:
                result_status = "paper_account_confirmed"
        except TimeoutError:
            result_status = "timeout"
            account_summary_status = "timeout"
            positions_status = "timeout"
            open_orders_status = "timeout"
            executions_status = "timeout"
        except Exception:
            result_status = "provider_error"
            account_summary_status = "provider_error"
            positions_status = "provider_error"
            open_orders_status = "provider_error"
            executions_status = "provider_error"

    STORE.runs.append(
        {
            "sync_run_id": run_id,
            "started_at": now.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "provider_code": settings.ibkr_sync_provider_code,
            "provider_environment": settings.ibkr_sync_account_mode,
            "account_mode": settings.ibkr_sync_account_mode,
            "readonly": settings.ibkr_sync_readonly,
            "status": result_status,
            "account_summary_status": account_summary_status,
            "positions_status": positions_status,
            "open_orders_status": open_orders_status,
            "executions_status": executions_status,
            "positions_count": len(positions),
            "cash_values_count": len(cash_items),
            "open_orders_count": len(open_orders),
            "executions_count": len(executions),
        }
    )
    for p in positions:
        STORE.positions.append(
            {
                "sync_run_id": run_id,
                "symbol": p.symbol,
                "quantity": str(p.quantity),
            }
        )
    for c in cash_items:
        STORE.cash.append(
            {
                "sync_run_id": run_id,
                "cash": str(c.cash),
                "account_ref": c.account_ref,
            }
        )
    for order in open_orders:
        STORE.open_orders.append(
            {
                "sync_run_id": run_id,
                "ibkr_order_id": order.ibkr_order_id,
                "symbol": order.symbol,
                "quantity": str(order.quantity),
                "status": order.status,
            }
        )
    for execution in executions:
        STORE.executions.append(
            {
                "sync_run_id": run_id,
                "execution_id": execution.execution_id,
                "symbol": execution.symbol,
                "quantity": str(execution.quantity),
                "price": str(execution.price),
            }
        )

    return read_status(settings) | {"sync_run_id": run_id}


def _int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def read_status(settings: Settings) -> dict[str, object]:
    latest = STORE.runs[-1] if STORE.runs else None
    status = "disabled" if not settings.ibkr_sync_enabled else "configured_not_connected"
    status_nl = "IBKR-sync niet geconfigureerd"
    next_step_nl = "Activeer handmatig met paper-only instellingen."
    if status != "disabled":
        status_nl = "Read-only synchronisatie"
        next_step_nl = "Start handmatige sync."
    if latest is not None:
        status = str(latest["status"])
        if status == "wrong_account_mode":
            status_nl = "Alleen papiermodus toegestaan"
            next_step_nl = "Controleer accountmodus paper."
        else:
            status_nl = "Read-only synchronisatie"
            next_step_nl = "Geen orders mogelijk"

    return {
        "status": status,
        "provider_code": settings.ibkr_sync_provider_code,
        "provider_environment": settings.ibkr_sync_account_mode,
        "account_mode": settings.ibkr_sync_account_mode,
        "readonly": settings.ibkr_sync_readonly,
        "account_summary_status": latest["account_summary_status"] if latest else "disabled",
        "positions_status": latest["positions_status"] if latest else "disabled",
        "open_orders_status": latest["open_orders_status"] if latest else "disabled",
        "executions_status": latest["executions_status"] if latest else "disabled",
        "positions_count": _int_value(latest["positions_count"]) if latest else 0,
        "cash_values_count": _int_value(latest["cash_values_count"]) if latest else 0,
        "open_orders_count": _int_value(latest["open_orders_count"]) if latest else 0,
        "executions_count": _int_value(latest["executions_count"]) if latest else 0,
        "started_at": latest["started_at"] if latest else None,
        "completed_at": latest["completed_at"] if latest else None,
        "status_nl": status_nl,
        "next_step_nl": next_step_nl,
        "help_nl": "Geen brokerdata opgeslagen zonder echte IBKR-respons",
        "sync_allowed": True,
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
    }
