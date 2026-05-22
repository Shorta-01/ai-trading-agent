"""Read-only portfolio valuation preparation contracts and builder."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from ai_trading_agent_storage import (
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
    MarketDataLatestSnapshotRecord,
)
from pydantic import BaseModel, Field


class PortfolioValuationStatus(StrEnum):
    STORAGE_UNAVAILABLE = "storage_unavailable"
    NO_LATEST_IBKR_SNAPSHOT = "no_latest_ibkr_snapshot"
    NO_POSITIONS = "no_positions"
    MISSING_MARKET_DATA = "missing_market_data"
    CALCULATION_AVAILABLE = "calculation_available"


class PositionValuationReadinessRow(BaseModel):
    conid: str | None = None
    symbol: str | None = None
    asset_class: str | None = None
    currency: str | None = None
    quantity: str
    average_cost: str | None = None
    market_data_status: str
    valuation_status: str
    reason_code: str
    status_nl: str
    help_nl: str
    last_market_snapshot_id: str | None = None
    market_price: str | None = None
    market_price_timestamp: str | None = None
    market_value: str | None = None
    unrealized_pnl: str | None = None
    blocked: bool
    missing_inputs: list[str] = Field(default_factory=list)


class PortfolioValuationReadinessResponse(BaseModel):
    status: str
    reason_code: str
    status_nl: str
    help_nl: str
    latest_sync_run_id: str | None = None
    latest_sync_completed_at: str | None = None
    storage_available: bool
    has_latest_ibkr_snapshot: bool
    has_positions: bool
    market_data_available: bool
    valuation_complete: bool
    blocked: bool
    suggestions_allowed: bool = False
    action_drafts_allowed: bool = False
    orders_allowed: bool = False
    rows: list[PositionValuationReadinessRow] = Field(default_factory=list)


@dataclass(frozen=True)
class PositionRowBuildInput:
    position: IbkrPositionSnapshotRecord
    market_snapshot: MarketDataLatestSnapshotRecord | None


def _money(value: Decimal) -> str:
    return str(value)


def build_position_row(payload: PositionRowBuildInput) -> PositionValuationReadinessRow:
    quantity = payload.position.quantity
    average_cost = payload.position.average_cost
    row = PositionValuationReadinessRow(
        conid=payload.position.conid,
        symbol=payload.position.symbol,
        asset_class=payload.position.security_type,
        currency=payload.position.currency,
        quantity=_money(quantity),
        average_cost=_money(average_cost) if average_cost is not None else None,
        market_data_status="missing_market_data",
        valuation_status="blocked",
        reason_code="missing_market_data",
        status_nl="Marktdataset ontbreekt",
        help_nl="Geen prijs beschikbaar in opgeslagen snapshots.",
        blocked=True,
        missing_inputs=["market_price"],
    )
    snapshot = payload.market_snapshot
    if snapshot is None or snapshot.last_price is None:
        return row
    if snapshot.freshness_status == "stale":
        row.reason_code = "stale_market_data"
        row.status_nl = "Controle nodig"
        row.help_nl = "Prijs is verouderd en kan niet veilig gebruikt worden."
        row.last_market_snapshot_id = snapshot.snapshot_id
        row.market_price = _money(snapshot.last_price)
        price_timestamp = snapshot.provider_as_of or snapshot.stored_at
        row.market_price_timestamp = price_timestamp.isoformat()
        return row
    market_value = quantity * snapshot.last_price
    unrealized_pnl = None
    if payload.position.average_cost is not None:
        unrealized_pnl = (snapshot.last_price - payload.position.average_cost) * quantity
    return PositionValuationReadinessRow(
        conid=payload.position.conid,
        symbol=payload.position.symbol,
        asset_class=payload.position.security_type,
        currency=payload.position.currency,
        quantity=_money(quantity),
        average_cost=_money(average_cost) if average_cost is not None else None,
        market_data_status="available",
        valuation_status="calculation_available",
        reason_code="valuation_available",
        status_nl="Waardering beschikbaar",
        help_nl="Waarde is berekend met opgeslagen marktsnapshot.",
        last_market_snapshot_id=snapshot.snapshot_id,
        market_price=_money(snapshot.last_price),
        market_price_timestamp=(snapshot.provider_as_of or snapshot.stored_at).isoformat(),
        market_value=_money(market_value),
        unrealized_pnl=_money(unrealized_pnl) if unrealized_pnl is not None else None,
        blocked=False,
        missing_inputs=[],
    )


def build_portfolio_valuation_readiness(
    *,
    latest_run: IbkrSyncRunRecord | None,
    positions: list[IbkrPositionSnapshotRecord],
    market_by_conid: dict[str, MarketDataLatestSnapshotRecord],
    storage_available: bool,
) -> PortfolioValuationReadinessResponse:
    if not storage_available:
        return PortfolioValuationReadinessResponse(
            status=PortfolioValuationStatus.STORAGE_UNAVAILABLE.value,
            reason_code="storage_unavailable",
            status_nl="Storage niet beschikbaar",
            help_nl="Waardering geblokkeerd: geen opslagverbinding.",
            storage_available=False,
            has_latest_ibkr_snapshot=False,
            has_positions=False,
            market_data_available=False,
            valuation_complete=False,
            blocked=True,
        )
    if latest_run is None:
        return PortfolioValuationReadinessResponse(
            status=PortfolioValuationStatus.NO_LATEST_IBKR_SNAPSHOT.value,
            reason_code="no_latest_ibkr_snapshot",
            status_nl="Geen laatste IBKR-snapshot",
            help_nl="Draai eerst een read-only IBKR sync.",
            storage_available=True,
            has_latest_ibkr_snapshot=False,
            has_positions=False,
            market_data_available=False,
            valuation_complete=False,
            blocked=True,
        )
    if not positions:
        return PortfolioValuationReadinessResponse(
            status=PortfolioValuationStatus.NO_POSITIONS.value,
            reason_code="no_positions",
            status_nl="Geen posities",
            help_nl="Er zijn nog geen posities om te waarderen.",
            latest_sync_run_id=latest_run.sync_run_id,
            latest_sync_completed_at=(
                latest_run.completed_at.isoformat() if latest_run.completed_at else None
            ),
            storage_available=True,
            has_latest_ibkr_snapshot=True,
            has_positions=False,
            market_data_available=False,
            valuation_complete=False,
            blocked=True,
        )
    rows = [
        build_position_row(
            PositionRowBuildInput(
                position=item,
                market_snapshot=market_by_conid.get(item.conid or ""),
            )
        )
        for item in positions
    ]
    blocked = any(row.blocked for row in rows)
    has_market = any(row.market_price is not None for row in rows)
    return PortfolioValuationReadinessResponse(
        status=(
            PortfolioValuationStatus.MISSING_MARKET_DATA.value
            if blocked
            else PortfolioValuationStatus.CALCULATION_AVAILABLE.value
        ),
        reason_code="missing_market_data" if blocked else "calculation_available",
        status_nl="Geblokkeerd" if blocked else "Waardering klaar",
        help_nl=(
            "Geen verzonnen waardes: ontbrekende marktdata blokkeert waardering."
            if blocked
            else "Read-only waardering berekend met opgeslagen data."
        ),
        latest_sync_run_id=latest_run.sync_run_id,
        latest_sync_completed_at=(
            latest_run.completed_at.isoformat() if latest_run.completed_at else None
        ),
        storage_available=True,
        has_latest_ibkr_snapshot=True,
        has_positions=True,
        market_data_available=has_market and not blocked,
        valuation_complete=not blocked,
        blocked=blocked,
        rows=rows,
    )
