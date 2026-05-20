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

class IbkrReadOnlyAdapter:
    def fetch_positions(self) -> list[IbkrPosition]:
        raise NotImplementedError
    def fetch_account_cash(self) -> list[IbkrCash]:
        raise NotImplementedError

class NotConfiguredIbkrAdapter(IbkrReadOnlyAdapter):
    def fetch_positions(self) -> list[IbkrPosition]:
        return []
    def fetch_account_cash(self) -> list[IbkrCash]:
        return []

class InMemoryIbkrSyncStore:
    def __init__(self) -> None:
        self.runs: list[dict[str, object]] = []
        self.positions: list[dict[str, object]] = []
        self.cash: list[dict[str, object]] = []

STORE = InMemoryIbkrSyncStore()


def is_configured(settings: Settings) -> bool:
    return bool(
        settings.ibkr_enabled
        and settings.ibkr_gateway_url
        and settings.ibkr_account_id_hint
    )


def run_sync(settings: Settings, adapter: IbkrReadOnlyAdapter | None = None) -> dict[str, object]:
    now = datetime.now(UTC)
    run_id = f"ibkr-sync-{uuid4()}"
    status = "success"
    error_message: str | None = None
    if not is_configured(settings):
        status = "failed"
        error_message = "IBKR koppeling niet ingesteld."
        positions: list[IbkrPosition] = []
        cash_items: list[IbkrCash] = []
    else:
        active_adapter = adapter or NotConfiguredIbkrAdapter()
        positions = active_adapter.fetch_positions()
        cash_items = active_adapter.fetch_account_cash()
        if not positions and not cash_items:
            status = "partial"

    STORE.runs.append({
        "sync_run_id": run_id,
        "source": "ibkr",
        "status": status,
        "started_at": now.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "error_message": error_message,
    })
    for p in positions:
        STORE.positions.append({
            "sync_run_id": run_id,
            "account_ref": p.account_ref,
            "symbol": p.symbol,
            "security_type": p.security_type,
            "currency": p.currency,
            "quantity": str(p.quantity),
            "average_cost": None if p.average_cost is None else str(p.average_cost),
            "exchange": p.exchange,
            "timestamp": now.isoformat(),
        })
    for c in cash_items:
        STORE.cash.append({
            "sync_run_id": run_id,
            "account_ref": c.account_ref,
            "base_currency": c.base_currency,
            "cash": str(c.cash),
            "available_funds": None if c.available_funds is None else str(c.available_funds),
            "buying_power": None if c.buying_power is None else str(c.buying_power),
            "timestamp": now.isoformat(),
        })
    return {
        "sync_run_id": run_id,
        "status": status,
        "positions_saved": len(positions),
        "cash_saved": len(cash_items),
    }


def read_status(settings: Settings) -> dict[str, object]:
    if not is_configured(settings):
        return {
            "configured": False,
            "status_nl": "Niet gekoppeld",
            "help_nl": "Koppel eerst IBKR instellingen.",
        }
    if not STORE.runs:
        return {
            "configured": True,
            "status_nl": "Nog niet gesynchroniseerd",
            "help_nl": "Start een eerste sync.",
        }
    latest = STORE.runs[-1]
    return {
        "configured": True,
        "status_nl": "Laatste sync beschikbaar",
        "last_run": latest,
        "positions_count": len(
            [p for p in STORE.positions if p["sync_run_id"] == latest["sync_run_id"]]
        ),
    }
