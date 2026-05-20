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
    exchange: str | None = None


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
    symbol: str
    security_type: str
    currency: str
    quantity: Decimal
    status: str
    filled_quantity: Decimal
    remaining_quantity: Decimal
    order_type: str | None = None
    action_side: str | None = None
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    tif: str | None = None
    average_fill_price: Decimal | None = None
    ibkr_perm_id: int | None = None
    parent_order_id: int | None = None
    exchange: str | None = None
    primary_exchange: str | None = None
    good_after_time: str | None = None
    good_till_time: str | None = None
    raw_status_reference: str | None = None


@dataclass(frozen=True)
class IbkrExecution:
    account_ref: str
    execution_id: str
    symbol: str
    security_type: str
    currency: str
    side: str
    quantity: Decimal
    price: Decimal
    execution_time: str
    ibkr_order_id: int | None = None
    ibkr_perm_id: int | None = None
    exchange: str | None = None
    primary_exchange: str | None = None
    raw_execution_reference: str | None = None


class IbkrReadOnlyAdapter:
    def fetch_positions(self) -> list[IbkrPosition]:
        raise NotImplementedError

    def fetch_account_cash(self) -> list[IbkrCash]:
        raise NotImplementedError

    def fetch_open_orders(self) -> list[IbkrOpenOrder]:
        raise NotImplementedError

    def fetch_executions(self) -> list[IbkrExecution]:
        raise NotImplementedError


class NotConfiguredIbkrAdapter(IbkrReadOnlyAdapter):
    def fetch_positions(self) -> list[IbkrPosition]:
        return []

    def fetch_account_cash(self) -> list[IbkrCash]:
        return []

    def fetch_open_orders(self) -> list[IbkrOpenOrder]:
        return []

    def fetch_executions(self) -> list[IbkrExecution]:
        return []


class InMemoryIbkrSyncStore:
    def __init__(self) -> None:
        self.runs: list[dict[str, object]] = []
        self.positions: list[dict[str, object]] = []
        self.cash: list[dict[str, object]] = []
        self.open_orders: list[dict[str, object]] = []
        self.executions: list[dict[str, object]] = []


STORE = InMemoryIbkrSyncStore()


def is_configured(settings: Settings) -> bool:
    return bool(
        settings.ibkr_enabled
        and settings.ibkr_gateway_url
        and settings.ibkr_account_id_hint
    )


def run_sync(
    settings: Settings, adapter: IbkrReadOnlyAdapter | None = None
) -> dict[str, object]:
    now = datetime.now(UTC)
    run_id = f"ibkr-sync-{uuid4()}"
    status = "success"
    error_message: str | None = None
    positions: list[IbkrPosition] = []
    cash_items: list[IbkrCash] = []
    open_orders: list[IbkrOpenOrder] = []
    executions: list[IbkrExecution] = []

    if not is_configured(settings):
        status = "failed"
        error_message = "IBKR koppeling niet ingesteld."
    else:
        active_adapter = adapter or NotConfiguredIbkrAdapter()
        try:
            positions = active_adapter.fetch_positions()
            cash_items = active_adapter.fetch_account_cash()
            open_orders = active_adapter.fetch_open_orders()
            executions = active_adapter.fetch_executions()
            if not positions and not cash_items and not open_orders and not executions:
                status = "partial"
        except Exception:
            status = "failed"
            error_message = "IBKR sync kon niet volledig worden opgehaald."

    STORE.runs.append(
        {
            "sync_run_id": run_id,
            "source": "ibkr",
            "status": status,
            "started_at": now.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "error_message": error_message,
            "positions_count": len(positions),
            "cash_count": len(cash_items),
            "open_orders_count": len(open_orders),
            "executions_count": len(executions),
        }
    )
    for p in positions:
        STORE.positions.append(
            {
                "sync_run_id": run_id,
                "account_ref": p.account_ref,
                "symbol": p.symbol,
                "security_type": p.security_type,
                "currency": p.currency,
                "quantity": str(p.quantity),
                "average_cost": None if p.average_cost is None else str(p.average_cost),
                "exchange": p.exchange,
                "timestamp": now.isoformat(),
            }
        )
    for c in cash_items:
        STORE.cash.append(
            {
                "sync_run_id": run_id,
                "account_ref": c.account_ref,
                "base_currency": c.base_currency,
                "cash": str(c.cash),
                "available_funds": (
                    None if c.available_funds is None else str(c.available_funds)
                ),
                "buying_power": None if c.buying_power is None else str(c.buying_power),
                "timestamp": now.isoformat(),
            }
        )
    for o in open_orders:
        STORE.open_orders.append(
            {
                "sync_run_id": run_id,
                "account_ref": o.account_ref,
                "ibkr_order_id": o.ibkr_order_id,
                "ibkr_perm_id": o.ibkr_perm_id,
                "parent_order_id": o.parent_order_id,
                "symbol": o.symbol,
                "security_type": o.security_type,
                "exchange": o.exchange,
                "primary_exchange": o.primary_exchange,
                "currency": o.currency,
                "action_side": o.action_side,
                "order_type": o.order_type,
                "quantity": str(o.quantity),
                "limit_price": None if o.limit_price is None else str(o.limit_price),
                "stop_price": None if o.stop_price is None else str(o.stop_price),
                "tif": o.tif,
                "good_after_time": o.good_after_time,
                "good_till_time": o.good_till_time,
                "status": o.status,
                "filled_quantity": str(o.filled_quantity),
                "remaining_quantity": str(o.remaining_quantity),
                "average_fill_price": (
                    None if o.average_fill_price is None else str(o.average_fill_price)
                ),
                "last_status_at": now.isoformat(),
                "raw_status_reference": o.raw_status_reference,
                "created_at": now.isoformat(),
            }
        )
    for e in executions:
        STORE.executions.append(
            {
                "sync_run_id": run_id,
                "account_ref": e.account_ref,
                "execution_id": e.execution_id,
                "ibkr_order_id": e.ibkr_order_id,
                "ibkr_perm_id": e.ibkr_perm_id,
                "symbol": e.symbol,
                "security_type": e.security_type,
                "exchange": e.exchange,
                "primary_exchange": e.primary_exchange,
                "currency": e.currency,
                "side": e.side,
                "quantity": str(e.quantity),
                "price": str(e.price),
                "execution_time": e.execution_time,
                "raw_execution_reference": e.raw_execution_reference,
                "created_at": now.isoformat(),
            }
        )

    return {
        "sync_run_id": run_id,
        "status": status,
        "positions_saved": len(positions),
        "cash_saved": len(cash_items),
        "open_orders_saved": len(open_orders),
        "executions_saved": len(executions),
    }


def read_status(settings: Settings) -> dict[str, object]:
    if not is_configured(settings):
        return {
            "configured": False,
            "status_nl": "Niet gekoppeld",
            "help_nl": "Koppel eerst IBKR instellingen.",
            "positions_count": 0,
            "cash_available": False,
            "open_orders_count": 0,
            "executions_count": 0,
        }
    if not STORE.runs:
        return {
            "configured": True,
            "status_nl": "Nog niet gesynchroniseerd",
            "help_nl": "Start een eerste sync.",
            "positions_count": 0,
            "cash_available": False,
            "open_orders_count": 0,
            "executions_count": 0,
        }
    latest = STORE.runs[-1]
    positions_count = latest.get("positions_count", 0)
    cash_count = latest.get("cash_count", 0)
    open_orders_count = latest.get("open_orders_count", 0)
    executions_count = latest.get("executions_count", 0)
    return {
        "configured": True,
        "status_nl": "Laatste sync beschikbaar",
        "help_nl": "Gebruik snapshots als read-only brokerstatus.",
        "last_run": latest,
        "positions_count": positions_count,
        "cash_available": cash_count > 0,
        "open_orders_count": open_orders_count,
        "executions_count": executions_count,
        "last_sync_at": latest["finished_at"],
    }
