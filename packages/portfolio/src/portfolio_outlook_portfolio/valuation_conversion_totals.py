from dataclasses import dataclass
from decimal import Decimal

ConversionStatus = str


@dataclass(frozen=True)
class PositionConversionInput:
    position_id: str
    source_currency: str | None
    native_market_value: Decimal | None
    source_trace_id: str | None = None


@dataclass(frozen=True)
class CashConversionInput:
    cash_id: str
    source_currency: str | None
    native_cash_value: Decimal | None
    source_trace_id: str | None = None


@dataclass(frozen=True)
class FxPairConversionInput:
    pair: str
    source_currency: str
    target_currency: str
    rate: Decimal
    freshness_status: str
    validation_status: str
    fx_snapshot_id: str | None = None


@dataclass(frozen=True)
class ValuationInputTrace:
    latest_sync_run_id: str | None
    position_trace_ids: list[str]
    cash_trace_ids: list[str]
    market_snapshot_ids: list[str]
    cash_snapshot_ids: list[str]
    fx_snapshot_ids: list[str]


@dataclass(frozen=True)
class ConversionTotalsInput:
    positions: list[PositionConversionInput]
    cash_values: list[CashConversionInput]
    fx_pairs: list[FxPairConversionInput]
    base_currency: str | None
    trace: ValuationInputTrace


@dataclass(frozen=True)
class ConversionTotalsResult:
    status: ConversionStatus
    status_nl: str
    help_nl: str
    base_currency: str | None
    total_market_value_available: bool
    total_market_value: Decimal | None
    total_cash_value_available: bool
    total_cash_value: Decimal | None
    total_portfolio_value_available: bool
    total_portfolio_value: Decimal | None
    missing_total_value_inputs: list[str]
    missing_market_data_conids: list[str]
    missing_cash_inputs: list[str]
    missing_fx_pairs: list[str]
    stale_fx_pairs: list[str]
    invalid_fx_pairs: list[str]
    converted_position_values_available: bool
    converted_cash_values_available: bool
    valuation_input_trace: ValuationInputTrace


_STATUS_TEXT: dict[str, tuple[str, str]] = {
    "conversion_not_required": (
        "Omrekening niet nodig",
        "Alle waardes delen dezelfde valuta en kunnen direct opgeteld worden.",
    ),
    "conversion_ready": (
        "Totaalwaarde klaar",
        "Alle benodigde waardes en wisselkoersen zijn bruikbaar.",
    ),
    "conversion_blocked_missing_base_currency": (
        "Basismunt ontbreekt",
        "Omrekening vereist een bekende basismunt.",
    ),
    "conversion_blocked_missing_market_data": (
        "Marktdata ontbreekt",
        "Niet alle positie-waardes zijn aanwezig.",
    ),
    "conversion_blocked_missing_cash": (
        "Cashsnapshot ontbreekt",
        "Niet alle cash-waardes zijn aanwezig.",
    ),
    "conversion_blocked_missing_fx": (
        "Wisselkoers ontbreekt",
        "Minstens één vereiste wisselkoers ontbreekt.",
    ),
    "conversion_control_needed_stale_fx": (
        "Wisselkoers verouderd",
        "Minstens één vereiste wisselkoers is verouderd.",
    ),
    "conversion_blocked_invalid_fx": (
        "Wisselkoers ongeldig",
        "Minstens één vereiste wisselkoers is ongeldig of onbekend.",
    ),
    "conversion_blocked_incomplete_inputs": (
        "Geblokkeerd",
        "Niet alle vereiste inputvelden zijn ingevuld.",
    ),
}


def _status_text(status: str) -> tuple[str, str]:
    return _STATUS_TEXT[status]


def calculate_conversion_totals(payload: ConversionTotalsInput) -> ConversionTotalsResult:
    fx_by_pair = {item.pair: item for item in payload.fx_pairs}
    position_currencies = {
        p.source_currency for p in payload.positions if p.source_currency is not None
    }
    cash_currencies = {
        c.source_currency for c in payload.cash_values if c.source_currency is not None
    }
    all_currencies = position_currencies | cash_currencies
    requires_conversion = len(all_currencies) > 1

    missing_market_data_conids = [
        p.position_id for p in payload.positions if p.native_market_value is None
    ]
    missing_cash_inputs = [c.cash_id for c in payload.cash_values if c.native_cash_value is None]

    if any(p.source_currency is None for p in payload.positions) or any(
        c.source_currency is None for c in payload.cash_values
    ):
        return _blocked(
            payload,
            "conversion_blocked_incomplete_inputs",
            missing_market_data_conids,
            missing_cash_inputs,
        )

    if missing_market_data_conids:
        return _blocked(
            payload,
            "conversion_blocked_missing_market_data",
            missing_market_data_conids,
            missing_cash_inputs,
        )

    if missing_cash_inputs:
        return _blocked(
            payload,
            "conversion_blocked_missing_cash",
            missing_market_data_conids,
            missing_cash_inputs,
        )

    if requires_conversion and payload.base_currency is None:
        return _blocked(
            payload,
            "conversion_blocked_missing_base_currency",
            missing_market_data_conids,
            missing_cash_inputs,
        )

    base_currency = payload.base_currency
    if not requires_conversion and base_currency is None and len(all_currencies) == 1:
        base_currency = next(iter(all_currencies))

    required_pairs = _required_pairs(payload.positions, payload.cash_values, base_currency)
    missing_fx_pairs: list[str] = []
    stale_fx_pairs: list[str] = []
    invalid_fx_pairs: list[str] = []

    for pair in required_pairs:
        fx = fx_by_pair.get(pair)
        if fx is None:
            missing_fx_pairs.append(pair)
            continue
        if fx.validation_status != "valid":
            invalid_fx_pairs.append(pair)
            continue
        if fx.freshness_status != "fresh":
            if fx.freshness_status == "stale":
                stale_fx_pairs.append(pair)
            else:
                invalid_fx_pairs.append(pair)

    if invalid_fx_pairs:
        return _blocked(
            payload,
            "conversion_blocked_invalid_fx",
            missing_market_data_conids,
            missing_cash_inputs,
            missing_fx_pairs,
            stale_fx_pairs,
            invalid_fx_pairs,
            base_currency,
        )

    if stale_fx_pairs:
        return _blocked(
            payload,
            "conversion_control_needed_stale_fx",
            missing_market_data_conids,
            missing_cash_inputs,
            missing_fx_pairs,
            stale_fx_pairs,
            invalid_fx_pairs,
            base_currency,
        )

    if missing_fx_pairs:
        return _blocked(
            payload,
            "conversion_blocked_missing_fx",
            missing_market_data_conids,
            missing_cash_inputs,
            missing_fx_pairs,
            stale_fx_pairs,
            invalid_fx_pairs,
            base_currency,
        )

    total_market = _sum_positions(payload.positions, base_currency, fx_by_pair)
    total_cash = _sum_cash(payload.cash_values, base_currency, fx_by_pair)
    total_portfolio = total_market + total_cash

    status = "conversion_ready" if required_pairs else "conversion_not_required"
    status_nl, help_nl = _status_text(status)
    return ConversionTotalsResult(
        status=status,
        status_nl=status_nl,
        help_nl=help_nl,
        base_currency=base_currency,
        total_market_value_available=True,
        total_market_value=total_market,
        total_cash_value_available=True,
        total_cash_value=total_cash,
        total_portfolio_value_available=True,
        total_portfolio_value=total_portfolio,
        missing_total_value_inputs=[],
        missing_market_data_conids=[],
        missing_cash_inputs=[],
        missing_fx_pairs=[],
        stale_fx_pairs=[],
        invalid_fx_pairs=[],
        converted_position_values_available=True,
        converted_cash_values_available=True,
        valuation_input_trace=payload.trace,
    )


def _required_pairs(
    positions: list[PositionConversionInput],
    cash_values: list[CashConversionInput],
    base_currency: str | None,
) -> list[str]:
    if base_currency is None:
        return []
    currencies = {item.source_currency for item in positions + cash_values}
    return sorted(
        f"{currency}/{base_currency}" for currency in currencies if currency != base_currency
    )


def _sum_positions(
    positions: list[PositionConversionInput],
    base_currency: str | None,
    fx_by_pair: dict[str, FxPairConversionInput],
) -> Decimal:
    total = Decimal("0")
    for position in positions:
        assert position.native_market_value is not None
        assert position.source_currency is not None
        if position.source_currency == base_currency:
            total += position.native_market_value
            continue
        pair = f"{position.source_currency}/{base_currency}"
        total += position.native_market_value * fx_by_pair[pair].rate
    return total


def _sum_cash(
    cash_values: list[CashConversionInput],
    base_currency: str | None,
    fx_by_pair: dict[str, FxPairConversionInput],
) -> Decimal:
    total = Decimal("0")
    for cash in cash_values:
        assert cash.native_cash_value is not None
        assert cash.source_currency is not None
        if cash.source_currency == base_currency:
            total += cash.native_cash_value
            continue
        pair = f"{cash.source_currency}/{base_currency}"
        total += cash.native_cash_value * fx_by_pair[pair].rate
    return total


def _blocked(
    payload: ConversionTotalsInput,
    status: str,
    missing_market_data_conids: list[str],
    missing_cash_inputs: list[str],
    missing_fx_pairs: list[str] | None = None,
    stale_fx_pairs: list[str] | None = None,
    invalid_fx_pairs: list[str] | None = None,
    base_currency: str | None = None,
) -> ConversionTotalsResult:
    status_nl, help_nl = _status_text(status)
    missing_total_value_inputs: list[str] = []
    if missing_market_data_conids:
        missing_total_value_inputs.append("market_data")
    if missing_cash_inputs:
        missing_total_value_inputs.append("cash_snapshot")
    if missing_fx_pairs:
        missing_total_value_inputs.append("fx_rates")
    if stale_fx_pairs:
        missing_total_value_inputs.append("stale_fx")
    if invalid_fx_pairs:
        missing_total_value_inputs.append("invalid_fx")
    if status == "conversion_blocked_missing_base_currency":
        missing_total_value_inputs.append("base_currency")

    return ConversionTotalsResult(
        status=status,
        status_nl=status_nl,
        help_nl=help_nl,
        base_currency=base_currency if base_currency is not None else payload.base_currency,
        total_market_value_available=False,
        total_market_value=None,
        total_cash_value_available=False,
        total_cash_value=None,
        total_portfolio_value_available=False,
        total_portfolio_value=None,
        missing_total_value_inputs=missing_total_value_inputs,
        missing_market_data_conids=missing_market_data_conids,
        missing_cash_inputs=missing_cash_inputs,
        missing_fx_pairs=missing_fx_pairs or [],
        stale_fx_pairs=stale_fx_pairs or [],
        invalid_fx_pairs=invalid_fx_pairs or [],
        converted_position_values_available=False,
        converted_cash_values_available=False,
        valuation_input_trace=payload.trace,
    )
