"""Read-only portfolio valuation preparation contracts and builder."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from ai_trading_agent_storage import (
    IbkrAccountCashSnapshotRecord,
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
    cash_readiness_status: str = "cash_not_checked"
    cash_readiness_status_nl: str = "Cash niet gecontroleerd"
    cash_readiness_help_nl: str = "Cashsnapshot is nog niet beoordeeld."
    cash_snapshot_available: bool = False
    cash_snapshot_count: int = 0
    cash_currencies: list[str] = Field(default_factory=list)
    has_base_currency_cash: bool = False
    missing_cash_inputs: list[str] = Field(default_factory=list)
    cash_values: list[dict[str, str | None]] = Field(default_factory=list)
    fx_readiness_status: str = "fx_not_checked"
    fx_readiness_status_nl: str = "Valutacontrole niet uitgevoerd"
    fx_readiness_help_nl: str = "Valutacontrole is nog niet beoordeeld."
    fx_required: bool = False
    portfolio_currencies: list[str] = Field(default_factory=list)
    valuation_currencies: list[str] = Field(default_factory=list)
    base_currency: str | None = None
    missing_fx_pairs: list[str] = Field(default_factory=list)
    fx_rates_available: bool = False
    fx_conversion_allowed: bool = False
    converted_totals_available: bool = False
    total_market_value_available: bool = False
    total_cash_value_available: bool = False
    total_portfolio_value_available: bool = False
    total_value_status: str = "blocked"
    total_value_status_nl: str = "Geblokkeerd"
    total_value_help_nl: str = "Geen verzonnen waardes: totaal blijft geblokkeerd."
    missing_total_value_inputs: list[str] = Field(default_factory=list)


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
    cash_snapshots: list[IbkrAccountCashSnapshotRecord],
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
            cash_readiness_status="cash_storage_unavailable",
            cash_readiness_status_nl="Cashstorage niet beschikbaar",
            cash_readiness_help_nl="Cashsnapshot kan niet gelezen worden uit storage.",
            missing_cash_inputs=["cash_snapshot"],
            fx_readiness_status="fx_storage_unavailable",
            fx_readiness_status_nl="Valutastorage niet beschikbaar",
            fx_readiness_help_nl="Valutastatus kan niet bepaald worden zonder storage.",
            missing_total_value_inputs=["storage"],
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
            cash_readiness_status="no_cash_snapshot",
            cash_readiness_status_nl="Cashsnapshot ontbreekt",
            cash_readiness_help_nl="Draai eerst een read-only IBKR sync met cashdata.",
            missing_cash_inputs=["cash_snapshot"],
            fx_readiness_status="fx_control_needed",
            fx_readiness_status_nl="Controle nodig",
            fx_readiness_help_nl="Valutastatus vereist eerst posities en cashsnapshot.",
            missing_total_value_inputs=["cash_snapshot", "market_data", "fx_inputs"],
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
            cash_readiness_status=(
                "cash_available" if cash_snapshots else "no_cash_snapshot"
            ),
            cash_readiness_status_nl=(
                "Cash beschikbaar" if cash_snapshots else "Cashsnapshot ontbreekt"
            ),
            cash_readiness_help_nl=(
                "Cashsnapshot gevonden in opslag."
                if cash_snapshots
                else "Geen cashsnapshot in laatste sync."
            ),
            cash_snapshot_available=bool(cash_snapshots),
            cash_snapshot_count=len(cash_snapshots),
            cash_currencies=sorted({item.base_currency for item in cash_snapshots}),
            has_base_currency_cash=any(item.cash is not None for item in cash_snapshots),
            missing_cash_inputs=[] if cash_snapshots else ["cash_snapshot"],
            fx_readiness_status="fx_not_required",
            fx_readiness_status_nl="FX niet nodig",
            fx_readiness_help_nl="Geen posities aanwezig; omzetting is niet nodig.",
            fx_required=False,
            fx_conversion_allowed=True,
            total_value_status="blocked",
            total_value_status_nl="Geblokkeerd",
            total_value_help_nl="Geen posities om totaalwaarde te bepalen.",
            missing_total_value_inputs=["positions"],
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
    cash_currencies = sorted({item.base_currency for item in cash_snapshots})
    portfolio_currency_set = {
        (item.currency or "").strip()
        for item in positions
        if item.currency
    }
    portfolio_currencies = sorted(portfolio_currency_set)
    valuation_currencies = sorted(set(portfolio_currencies) | set(cash_currencies))
    base_currency = cash_currencies[0] if len(cash_currencies) == 1 else None
    cash_values: list[dict[str, str | None]] = []
    for item in cash_snapshots:
        cash_values.append(
            {
                "currency": item.base_currency,
                "cash": _money(item.cash) if item.cash is not None else None,
                "available_funds": (
                    _money(item.available_funds)
                    if item.available_funds is not None
                    else None
                ),
                "buying_power": (
                    _money(item.buying_power) if item.buying_power is not None else None
                ),
                "sync_run_id": item.sync_run_id,
                "snapshot_timestamp": item.received_at.isoformat(),
            }
        )
    fx_required = len(valuation_currencies) > 1
    fx_status = "fx_not_required" if not fx_required else "fx_not_supported_yet"
    fx_status_nl = "FX niet nodig" if not fx_required else "FX ontbreekt"
    fx_help = (
        "Alle waardering is in één valuta."
        if not fx_required
        else "Meerdere valuta zonder opgeslagen wisselkoers: controle nodig."
    )
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
        cash_readiness_status="cash_available" if cash_snapshots else "no_cash_snapshot",
        cash_readiness_status_nl=(
            "Cash beschikbaar" if cash_snapshots else "Cashsnapshot ontbreekt"
        ),
        cash_readiness_help_nl=(
            "Cashsnapshot is read-only beschikbaar uit opslag."
            if cash_snapshots
            else "Geen cashsnapshot in laatste sync; cashcontext ontbreekt."
        ),
        cash_snapshot_available=bool(cash_snapshots),
        cash_snapshot_count=len(cash_snapshots),
        cash_currencies=cash_currencies,
        has_base_currency_cash=any(item.cash is not None for item in cash_snapshots),
        missing_cash_inputs=[] if cash_snapshots else ["cash_snapshot"],
        cash_values=cash_values,
        fx_readiness_status=fx_status,
        fx_readiness_status_nl=fx_status_nl,
        fx_readiness_help_nl=fx_help,
        fx_required=fx_required,
        portfolio_currencies=portfolio_currencies,
        valuation_currencies=valuation_currencies,
        base_currency=base_currency,
        missing_fx_pairs=[] if not fx_required else ["all_required_pairs"],
        fx_rates_available=False,
        fx_conversion_allowed=not fx_required,
        converted_totals_available=False,
        total_market_value_available=not blocked,
        total_cash_value_available=False,
        total_portfolio_value_available=False,
        total_value_status="blocked",
        total_value_status_nl="Geblokkeerd",
        total_value_help_nl=(
            "Geen verzonnen waardes: totaal vereist cash+FX met gevalideerde inputs."
        ),
        missing_total_value_inputs=["fx_rates", "validated_cash_totals"],
    )
