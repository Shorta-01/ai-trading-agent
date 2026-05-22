from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


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
