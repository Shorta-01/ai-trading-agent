"""Read-only portfolio valuation preparation contracts and builder."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from ai_trading_agent_storage import (
    FxRateSnapshotRecord,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
    MarketDataLatestSnapshotRecord,
)
from portfolio_outlook_portfolio import (
    CashConversionInput,
    ConversionTotalsInput,
    FxPairConversionInput,
    PositionConversionInput,
    PositionPlCalculationInput,
    PositionPlInput,
    PositionPlInputTrace,
    ValuationInputTrace,
    calculate_conversion_totals,
    calculate_position_cost_basis_and_unrealized_pl,
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
    cost_basis_status: str = "cost_basis_missing"
    cost_basis_status_nl: str = "Kostbasis ontbreekt"
    cost_basis_help_nl: str = "Niet alle kostbasisvelden zijn aanwezig in opgeslagen input."
    cost_basis_available: bool = False
    cost_basis: str | None = None
    cost_basis_currency: str | None = None
    unrealized_pl_status: str = "pl_blocked_incomplete_inputs"
    unrealized_pl_status_nl: str = "Geblokkeerd"
    unrealized_pl_help_nl: str = "Niet alle vereiste inputvelden zijn ingevuld."
    unrealized_pl_available: bool = False
    unrealized_pl: str | None = None
    unrealized_pl_currency: str | None = None
    unrealized_pl_percent_available: bool = False
    unrealized_pl_percent: str | None = None
    converted_unrealized_pl_available: bool = False
    converted_unrealized_pl: str | None = None
    missing_cost_basis_inputs: list[str] = Field(default_factory=list)
    missing_pl_inputs: list[str] = Field(default_factory=list)
    cost_basis_input_trace: dict[str, object] | None = None
    unrealized_pl_input_trace: dict[str, object] | None = None
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
    fx_snapshot_contract_status: str = "fx_snapshot_contract_not_checked"
    fx_snapshot_contract_status_nl: str = "FX-opslagcontract niet gecontroleerd"
    fx_snapshot_contract_help_nl: str = "FX-opslagcontract is nog niet beoordeeld."
    fx_snapshot_contract_available: bool = False
    fx_snapshot_data_available: bool = False
    fx_snapshot_source: str | None = None
    fx_snapshot_count: int = 0
    fx_snapshot_pairs_available: list[str] = Field(default_factory=list)
    stale_fx_pairs: list[str] = Field(default_factory=list)
    invalid_fx_pairs: list[str] = Field(default_factory=list)
    total_market_value_available: bool = False
    total_cash_value_available: bool = False
    total_portfolio_value_available: bool = False
    total_value_status: str = "blocked"
    total_value_status_nl: str = "Geblokkeerd"
    total_value_help_nl: str = "Geen verzonnen waardes: totaal blijft geblokkeerd."
    missing_total_value_inputs: list[str] = Field(default_factory=list)
    conversion_total_status: str = "conversion_blocked_incomplete_inputs"
    conversion_total_status_nl: str = "Geblokkeerd"
    conversion_total_help_nl: str = "Niet alle vereiste inputvelden zijn ingevuld."
    total_market_value: str | None = None
    total_cash_value: str | None = None
    total_portfolio_value: str | None = None
    missing_market_data_conids: list[str] = Field(default_factory=list)
    converted_position_values_available: bool = False
    converted_cash_values_available: bool = False
    valuation_input_trace: dict[str, object] = Field(default_factory=dict)


@dataclass(frozen=True)
class PositionRowBuildInput:
    position: IbkrPositionSnapshotRecord
    market_snapshot: MarketDataLatestSnapshotRecord | None
    latest_sync_run_id: str | None


def _money(value: Decimal) -> str:
    return str(value)


def _derive_required_fx_pairs(
    *,
    portfolio_currencies: list[str],
    cash_currencies: list[str],
    base_currency: str | None,
) -> list[str]:
    if base_currency is None:
        return []
    base = base_currency.upper()
    candidates = sorted(set(portfolio_currencies) | set(cash_currencies))
    return [f"{currency}/{base}" for currency in candidates if currency != base]


def build_position_row(payload: PositionRowBuildInput) -> PositionValuationReadinessRow:
    quantity = payload.position.quantity
    average_cost = payload.position.average_cost
    trace = PositionPlInputTrace(
        latest_sync_run_id=payload.latest_sync_run_id,
        position_trace_ids=[payload.position.snapshot_id] if payload.position.snapshot_id else [],
        market_snapshot_ids=[],
        fx_snapshot_ids=[],
    )
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
    pl_payload = PositionPlCalculationInput(
        position=PositionPlInput(
            position_id=payload.position.conid or payload.position.snapshot_id or "unknown",
            quantity=quantity,
            source_currency=payload.position.currency,
            native_market_value=None,
            average_cost_per_unit=payload.position.average_cost,
            source_trace_id=payload.position.snapshot_id,
        ),
        base_currency=None,
        trace=trace,
    )
    pl_result = calculate_position_cost_basis_and_unrealized_pl(pl_payload)
    row.cost_basis_status = pl_result.cost_basis_status
    row.cost_basis_status_nl = pl_result.cost_basis_status_nl
    row.cost_basis_help_nl = pl_result.cost_basis_help_nl
    row.cost_basis_available = pl_result.cost_basis_available
    row.cost_basis = _money(pl_result.cost_basis) if pl_result.cost_basis is not None else None
    row.cost_basis_currency = pl_result.cost_basis_currency
    row.unrealized_pl_status = pl_result.unrealized_pl_status
    row.unrealized_pl_status_nl = pl_result.unrealized_pl_status_nl
    row.unrealized_pl_help_nl = pl_result.unrealized_pl_help_nl
    row.unrealized_pl_available = pl_result.unrealized_pl_available
    row.unrealized_pl = (
        _money(pl_result.unrealized_pl)
        if pl_result.unrealized_pl is not None
        else None
    )
    row.unrealized_pl_currency = pl_result.unrealized_pl_currency
    row.unrealized_pl_percent_available = pl_result.unrealized_pl_percent_available
    row.unrealized_pl_percent = (
        _money(pl_result.unrealized_pl_percent)
        if pl_result.unrealized_pl_percent is not None
        else None
    )
    row.converted_unrealized_pl_available = pl_result.converted_unrealized_pl_available
    row.converted_unrealized_pl = (
        _money(pl_result.converted_unrealized_pl)
        if pl_result.converted_unrealized_pl is not None
        else None
    )
    row.missing_cost_basis_inputs = pl_result.missing_cost_basis_inputs
    row.missing_pl_inputs = pl_result.missing_pl_inputs
    row.cost_basis_input_trace = (
        pl_result.cost_basis_input_trace.__dict__ if pl_result.cost_basis_input_trace else None
    )
    row.unrealized_pl_input_trace = (
        pl_result.unrealized_pl_input_trace.__dict__
        if pl_result.unrealized_pl_input_trace
        else None
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
    market_value = quantity * snapshot.last_price
    trace_with_market = PositionPlInputTrace(
        latest_sync_run_id=payload.latest_sync_run_id,
        position_trace_ids=[payload.position.snapshot_id] if payload.position.snapshot_id else [],
        market_snapshot_ids=[snapshot.snapshot_id],
        fx_snapshot_ids=[],
    )
    pl_payload = PositionPlCalculationInput(
        position=PositionPlInput(
            position_id=payload.position.conid or payload.position.snapshot_id or "unknown",
            quantity=quantity,
            source_currency=payload.position.currency,
            native_market_value=market_value if snapshot.freshness_status == "fresh" else None,
            average_cost_per_unit=payload.position.average_cost,
            source_trace_id=payload.position.snapshot_id,
        ),
        base_currency=None,
        trace=trace_with_market,
    )
    pl_result = calculate_position_cost_basis_and_unrealized_pl(pl_payload)
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
        unrealized_pnl=(
            _money(pl_result.unrealized_pl)
            if pl_result.unrealized_pl_available and pl_result.unrealized_pl is not None
            else None
        ),
        cost_basis_status=pl_result.cost_basis_status,
        cost_basis_status_nl=pl_result.cost_basis_status_nl,
        cost_basis_help_nl=pl_result.cost_basis_help_nl,
        cost_basis_available=pl_result.cost_basis_available,
        cost_basis=_money(pl_result.cost_basis) if pl_result.cost_basis is not None else None,
        cost_basis_currency=pl_result.cost_basis_currency,
        unrealized_pl_status=pl_result.unrealized_pl_status,
        unrealized_pl_status_nl=pl_result.unrealized_pl_status_nl,
        unrealized_pl_help_nl=pl_result.unrealized_pl_help_nl,
        unrealized_pl_available=pl_result.unrealized_pl_available,
        unrealized_pl=(
            _money(pl_result.unrealized_pl)
            if pl_result.unrealized_pl is not None
            else None
        ),
        unrealized_pl_currency=pl_result.unrealized_pl_currency,
        unrealized_pl_percent_available=pl_result.unrealized_pl_percent_available,
        unrealized_pl_percent=(
            _money(pl_result.unrealized_pl_percent)
        if pl_result.unrealized_pl_percent is not None
        else None
        ),
        converted_unrealized_pl_available=pl_result.converted_unrealized_pl_available,
        converted_unrealized_pl=(
            _money(pl_result.converted_unrealized_pl)
        if pl_result.converted_unrealized_pl is not None
        else None
        ),
        missing_cost_basis_inputs=pl_result.missing_cost_basis_inputs,
        missing_pl_inputs=pl_result.missing_pl_inputs,
        cost_basis_input_trace=(
            pl_result.cost_basis_input_trace.__dict__
            if pl_result.cost_basis_input_trace
            else None
        ),
        unrealized_pl_input_trace=(
            pl_result.unrealized_pl_input_trace.__dict__
        if pl_result.unrealized_pl_input_trace
        else None
        ),
        blocked=False,
        missing_inputs=[],
    )




def _conversion_trace_dict(trace: ValuationInputTrace) -> dict[str, object]:
    return {
        "latest_sync_run_id": trace.latest_sync_run_id,
        "position_trace_ids": trace.position_trace_ids,
        "cash_trace_ids": trace.cash_trace_ids,
        "market_snapshot_ids": trace.market_snapshot_ids,
        "cash_snapshot_ids": trace.cash_snapshot_ids,
        "fx_snapshot_ids": trace.fx_snapshot_ids,
    }


def _build_conversion_inputs(
    *,
    positions: list[IbkrPositionSnapshotRecord],
    rows: list[PositionValuationReadinessRow],
    market_by_conid: dict[str, MarketDataLatestSnapshotRecord],
    cash_snapshots: list[IbkrAccountCashSnapshotRecord],
    fx_snapshots: list[FxRateSnapshotRecord],
    latest_sync_run_id: str | None,
    base_currency: str | None,
) -> ConversionTotalsInput:
    position_inputs: list[PositionConversionInput] = []
    position_trace_ids: list[str] = []
    market_snapshot_ids: list[str] = []
    for position, row in zip(positions, rows, strict=True):
        trace_id = position.snapshot_id or position.conid
        if trace_id is not None:
            position_trace_ids.append(trace_id)
        snapshot = market_by_conid.get(position.conid or "")
        if snapshot is not None:
            market_snapshot_ids.append(snapshot.snapshot_id)
        native_market_value = Decimal(row.market_value) if row.market_value is not None else None
        position_inputs.append(
            PositionConversionInput(
                position_id=position.conid or position.snapshot_id,
                source_currency=position.currency,
                native_market_value=native_market_value,
                source_trace_id=trace_id,
            )
        )

    cash_inputs: list[CashConversionInput] = []
    cash_trace_ids: list[str] = []
    cash_snapshot_ids: list[str] = []
    for cash in cash_snapshots:
        trace_id = cash.snapshot_id
        cash_trace_ids.append(trace_id)
        cash_snapshot_ids.append(cash.snapshot_id)
        cash_inputs.append(
            CashConversionInput(
                cash_id=cash.snapshot_id,
                source_currency=cash.base_currency,
                native_cash_value=cash.cash,
                source_trace_id=trace_id,
            )
        )

    fx_inputs: list[FxPairConversionInput] = []
    fx_snapshot_ids: list[str] = []
    for fx in fx_snapshots:
        source_currency, target_currency = fx.pair.split("/", 1)
        fx_snapshot_ids.append(fx.snapshot_id)
        fx_inputs.append(
            FxPairConversionInput(
                pair=fx.pair,
                source_currency=source_currency,
                target_currency=target_currency,
                rate=fx.rate,
                freshness_status=fx.freshness_status,
                validation_status=fx.validation_status,
                fx_snapshot_id=fx.snapshot_id,
            )
        )

    trace = ValuationInputTrace(
        latest_sync_run_id=latest_sync_run_id,
        position_trace_ids=position_trace_ids,
        cash_trace_ids=cash_trace_ids,
        market_snapshot_ids=market_snapshot_ids,
        cash_snapshot_ids=cash_snapshot_ids,
        fx_snapshot_ids=fx_snapshot_ids,
    )
    return ConversionTotalsInput(
        positions=position_inputs,
        cash_values=cash_inputs,
        fx_pairs=fx_inputs,
        base_currency=base_currency,
        trace=trace,
    )

def build_portfolio_valuation_readiness(
    *,
    latest_run: IbkrSyncRunRecord | None,
    positions: list[IbkrPositionSnapshotRecord],
    market_by_conid: dict[str, MarketDataLatestSnapshotRecord],
    cash_snapshots: list[IbkrAccountCashSnapshotRecord],
    fx_snapshots: list[FxRateSnapshotRecord],
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
            fx_snapshot_contract_status="fx_snapshot_contract_available",
            fx_snapshot_contract_status_nl="FX-opslag beschikbaar",
            fx_snapshot_contract_help_nl="Opgeslagen FX-contract is beschikbaar.",
            fx_snapshot_contract_available=True,
            fx_snapshot_data_available=False,
            fx_snapshot_source=None,
            fx_snapshot_count=0,
            fx_snapshot_pairs_available=[],
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
            fx_snapshot_contract_status="fx_snapshot_contract_available",
            fx_snapshot_contract_status_nl="FX-opslag beschikbaar",
            fx_snapshot_contract_help_nl="Opgeslagen FX-contract is beschikbaar.",
            fx_snapshot_contract_available=True,
            fx_snapshot_data_available=False,
            fx_snapshot_source=None,
            fx_snapshot_count=0,
            fx_snapshot_pairs_available=[],
            missing_total_value_inputs=["cash_snapshot", "market_data", "fx_inputs"],
        )
    if not positions:
        cash_currencies = sorted({item.base_currency for item in cash_snapshots})
        valuation_currencies = list(cash_currencies)
        base_currency: str | None = None
        if len(cash_currencies) == 1:
            base_currency = cash_currencies[0]
        elif "USD" in cash_currencies:
            base_currency = "USD"

        fx_required = len(cash_currencies) > 1
        missing_fx_pairs = _derive_required_fx_pairs(
            portfolio_currencies=[],
            cash_currencies=cash_currencies,
            base_currency=base_currency,
        )
        fx_status = "fx_not_required"
        fx_status_nl = "FX niet nodig"
        fx_help = "Cash staat in één valuta; omzetting is niet nodig."
        if fx_required:
            if base_currency is None:
                fx_status = "fx_control_needed"
                fx_status_nl = "Controle nodig"
                fx_help = "Basismunt ontbreekt; vereiste wisselkoersen zijn onbekend."
                missing_fx_pairs = ["base_currency"]
            else:
                fx_status = "fx_snapshot_missing"
                fx_status_nl = "Wisselkoers ontbreekt"
                fx_help = "Niet alle vereiste opgeslagen wisselkoersen zijn aanwezig."

        missing_total_value_inputs = ["positions"]
        if fx_required:
            missing_total_value_inputs.append("fx_rates")
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
            cash_currencies=cash_currencies,
            has_base_currency_cash=any(item.cash is not None for item in cash_snapshots),
            missing_cash_inputs=[] if cash_snapshots else ["cash_snapshot"],
            fx_readiness_status=fx_status,
            fx_readiness_status_nl=fx_status_nl,
            fx_readiness_help_nl=fx_help,
            fx_required=fx_required,
            fx_snapshot_contract_status="fx_snapshot_contract_available",
            fx_snapshot_contract_status_nl="FX-opslag beschikbaar",
            fx_snapshot_contract_help_nl="Opgeslagen FX-contract is beschikbaar.",
            fx_snapshot_contract_available=True,
            fx_snapshot_data_available=False,
            fx_snapshot_source=None,
            fx_snapshot_count=0,
            fx_snapshot_pairs_available=[],
            valuation_currencies=valuation_currencies,
            base_currency=base_currency,
            missing_fx_pairs=[] if not fx_required else missing_fx_pairs,
            fx_rates_available=False,
            fx_conversion_allowed=not fx_required,
            converted_totals_available=False,
            total_value_status="blocked",
            total_value_status_nl="Geblokkeerd",
            total_value_help_nl="Geen posities om totaalwaarde te bepalen.",
            missing_total_value_inputs=missing_total_value_inputs,
        )
    rows = [
        build_position_row(
            PositionRowBuildInput(
                position=item,
                market_snapshot=market_by_conid.get(item.conid or ""),
                latest_sync_run_id=latest_run.sync_run_id,
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
    required_pairs = _derive_required_fx_pairs(
        portfolio_currencies=portfolio_currencies,
        cash_currencies=cash_currencies,
        base_currency=base_currency,
    )
    available_pairs = sorted({item.pair for item in fx_snapshots})
    stale_fx_pairs = sorted(
        {item.pair for item in fx_snapshots if item.freshness_status != "fresh"}
    )
    invalid_fx_pairs = sorted(
        {item.pair for item in fx_snapshots if item.validation_status != "valid"}
    )
    missing_fx_pairs = [pair for pair in required_pairs if pair not in available_pairs]
    fx_status = "fx_not_required"
    fx_status_nl = "FX niet nodig"
    fx_help = "Alle waardering is in één valuta."
    fx_rates_available = False
    fx_conversion_allowed = False
    fx_snapshot_data_available = False
    if fx_required:
        if base_currency is None:
            fx_status = "fx_control_needed"
            fx_status_nl = "Controle nodig"
            fx_help = "Basismunt ontbreekt; vereiste wisselkoersen zijn onbekend."
            missing_fx_pairs = ["base_currency"]
        elif missing_fx_pairs:
            fx_status = "fx_snapshot_missing"
            fx_status_nl = "Wisselkoers ontbreekt"
            fx_help = "Niet alle vereiste opgeslagen wisselkoersen zijn aanwezig."
        elif stale_fx_pairs:
            fx_status = "fx_snapshot_stale"
            fx_status_nl = "Wisselkoers verouderd"
            fx_help = "Opgeslagen wisselkoers is verouderd."
        elif invalid_fx_pairs:
            fx_status = "fx_snapshot_invalid"
            fx_status_nl = "Wisselkoers ongeldig"
            fx_help = "Opgeslagen wisselkoers is ongeldig."
        else:
            fx_status = "fx_snapshot_available"
            fx_status_nl = "Opgeslagen wisselkoers beschikbaar"
            fx_help = "Alle vereiste opgeslagen wisselkoersen zijn vers en geldig."
            fx_rates_available = True
            fx_conversion_allowed = True
            fx_snapshot_data_available = True
    conversion_input = _build_conversion_inputs(
        positions=positions,
        rows=rows,
        market_by_conid=market_by_conid,
        cash_snapshots=cash_snapshots,
        fx_snapshots=fx_snapshots,
        latest_sync_run_id=latest_run.sync_run_id,
        base_currency=base_currency,
    )
    conversion_result = calculate_conversion_totals(conversion_input)
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
        fx_snapshot_contract_status="fx_snapshot_contract_available",
        fx_snapshot_contract_status_nl="FX-opslag beschikbaar",
        fx_snapshot_contract_help_nl="Opgeslagen FX-contract is beschikbaar.",
        fx_snapshot_contract_available=True,
        fx_snapshot_data_available=fx_snapshot_data_available,
        fx_snapshot_source=None,
        fx_snapshot_count=len(fx_snapshots),
        fx_snapshot_pairs_available=available_pairs,
        stale_fx_pairs=stale_fx_pairs,
        invalid_fx_pairs=invalid_fx_pairs,
        portfolio_currencies=portfolio_currencies,
        valuation_currencies=valuation_currencies,
        base_currency=base_currency,
        missing_fx_pairs=[] if not fx_required else missing_fx_pairs,
        fx_rates_available=fx_rates_available,
        fx_conversion_allowed=fx_conversion_allowed if fx_required else True,
        converted_totals_available=conversion_result.total_portfolio_value_available,
        total_market_value_available=conversion_result.total_market_value_available,
        total_cash_value_available=conversion_result.total_cash_value_available,
        total_portfolio_value_available=conversion_result.total_portfolio_value_available,
        total_value_status=conversion_result.status,
        total_value_status_nl=conversion_result.status_nl,
        total_value_help_nl=conversion_result.help_nl,
        missing_total_value_inputs=conversion_result.missing_total_value_inputs,
        conversion_total_status=conversion_result.status,
        conversion_total_status_nl=conversion_result.status_nl,
        conversion_total_help_nl=conversion_result.help_nl,
        total_market_value=(
            _money(conversion_result.total_market_value)
            if conversion_result.total_market_value is not None
            else None
        ),
        total_cash_value=(
            _money(conversion_result.total_cash_value)
            if conversion_result.total_cash_value is not None
            else None
        ),
        total_portfolio_value=(
            _money(conversion_result.total_portfolio_value)
            if conversion_result.total_portfolio_value is not None
            else None
        ),
        missing_market_data_conids=conversion_result.missing_market_data_conids,
        converted_position_values_available=conversion_result.converted_position_values_available,
        converted_cash_values_available=conversion_result.converted_cash_values_available,
        valuation_input_trace=_conversion_trace_dict(conversion_result.valuation_input_trace),
    )
