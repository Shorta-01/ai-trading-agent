from dataclasses import dataclass
from decimal import Decimal

PlStatus = str


@dataclass(frozen=True)
class PositionPlInput:
    position_id: str
    quantity: Decimal | None
    source_currency: str | None
    native_market_value: Decimal | None
    average_cost_per_unit: Decimal | None
    source_trace_id: str | None = None


@dataclass(frozen=True)
class PositionPlInputTrace:
    latest_sync_run_id: str | None
    position_trace_ids: list[str]
    market_snapshot_ids: list[str]
    fx_snapshot_ids: list[str]


@dataclass(frozen=True)
class PositionPlCalculationInput:
    position: PositionPlInput
    base_currency: str | None
    converted_market_value: Decimal | None = None
    converted_cost_basis: Decimal | None = None
    trace: PositionPlInputTrace | None = None


@dataclass(frozen=True)
class PositionPlCalculationResult:
    cost_basis_status: str
    cost_basis_status_nl: str
    cost_basis_help_nl: str
    cost_basis_available: bool
    cost_basis: Decimal | None
    cost_basis_currency: str | None
    unrealized_pl_status: str
    unrealized_pl_status_nl: str
    unrealized_pl_help_nl: str
    unrealized_pl_available: bool
    unrealized_pl: Decimal | None
    unrealized_pl_currency: str | None
    unrealized_pl_percent_available: bool
    unrealized_pl_percent: Decimal | None
    converted_unrealized_pl_available: bool
    converted_unrealized_pl: Decimal | None
    missing_cost_basis_inputs: list[str]
    missing_pl_inputs: list[str]
    cost_basis_input_trace: PositionPlInputTrace | None
    unrealized_pl_input_trace: PositionPlInputTrace | None


_STATUS_TEXT: dict[str, tuple[str, str]] = {
    "cost_basis_ready": ("Kostbasis klaar", "Kostbasis is veilig berekend uit opgeslagen input."),
    "cost_basis_missing": (
        "Kostbasis ontbreekt",
        "Niet alle kostbasisvelden zijn aanwezig in opgeslagen input.",
    ),
    "cost_basis_blocked_invalid_quantity": (
        "Aantal ongeldig",
        "Aantal moet groter dan nul zijn om kostbasis te bepalen.",
    ),
    "cost_basis_blocked_short_position": (
        "Shortpositie niet ondersteund",
        "Shortposities vallen buiten deze versie.",
    ),
    "pl_ready": (
        "Ongerealiseerde winst/verlies klaar",
        "Winst/verlies is veilig berekend uit market value en kostbasis.",
    ),
    "pl_blocked_missing_cost_basis": (
        "Kostbasis ontbreekt",
        "Winst/verlies vereist een veilige kostbasis.",
    ),
    "pl_blocked_missing_market_data": (
        "Marktdata ontbreekt",
        "Winst/verlies vereist een veilige market value.",
    ),
    "pl_blocked_incomplete_inputs": (
        "Geblokkeerd",
        "Niet alle vereiste inputvelden zijn ingevuld.",
    ),
}


def _status_text(status: str) -> tuple[str, str]:
    return _STATUS_TEXT[status]


def calculate_position_cost_basis_and_unrealized_pl(
    payload: PositionPlCalculationInput,
) -> PositionPlCalculationResult:
    position = payload.position
    missing_cost_basis_inputs: list[str] = []
    missing_pl_inputs: list[str] = []

    if position.source_currency is None:
        missing_cost_basis_inputs.append("source_currency")
        missing_pl_inputs.append("source_currency")
        return _blocked(
            payload,
            "cost_basis_missing",
            "pl_blocked_incomplete_inputs",
            missing_cost_basis_inputs,
            missing_pl_inputs,
        )

    if position.quantity is None:
        missing_cost_basis_inputs.append("quantity")
        missing_pl_inputs.append("quantity")
        return _blocked(
            payload,
            "cost_basis_missing",
            "pl_blocked_incomplete_inputs",
            missing_cost_basis_inputs,
            missing_pl_inputs,
        )

    if position.quantity < Decimal("0"):
        return _blocked(
            payload,
            "cost_basis_blocked_short_position",
            "pl_blocked_incomplete_inputs",
            missing_cost_basis_inputs,
            ["short_position"],
        )

    if position.quantity == Decimal("0"):
        return _blocked(
            payload,
            "cost_basis_blocked_invalid_quantity",
            "pl_blocked_incomplete_inputs",
            ["quantity"],
            ["quantity"],
        )

    if position.average_cost_per_unit is None:
        missing_cost_basis_inputs.append("average_cost_per_unit")
        return _blocked(
            payload,
            "cost_basis_missing",
            "pl_blocked_missing_cost_basis",
            missing_cost_basis_inputs,
            ["cost_basis"],
        )

    cost_basis = position.quantity * position.average_cost_per_unit

    if position.native_market_value is None:
        missing_pl_inputs.append("native_market_value")
        return _cost_basis_ready_pl_blocked(
            payload,
            cost_basis,
            missing_cost_basis_inputs,
            missing_pl_inputs,
        )

    unrealized_pl = position.native_market_value - cost_basis

    unrealized_pl_percent: Decimal | None = None
    unrealized_pl_percent_available = False
    if cost_basis > Decimal("0"):
        unrealized_pl_percent = unrealized_pl / cost_basis
        unrealized_pl_percent_available = True

    converted_unrealized_pl_available = False
    converted_unrealized_pl: Decimal | None = None
    if payload.converted_market_value is not None and payload.converted_cost_basis is not None:
        converted_unrealized_pl = payload.converted_market_value - payload.converted_cost_basis
        converted_unrealized_pl_available = True

    cost_basis_status_nl, cost_basis_help_nl = _status_text("cost_basis_ready")
    pl_status_nl, pl_help_nl = _status_text("pl_ready")

    return PositionPlCalculationResult(
        cost_basis_status="cost_basis_ready",
        cost_basis_status_nl=cost_basis_status_nl,
        cost_basis_help_nl=cost_basis_help_nl,
        cost_basis_available=True,
        cost_basis=cost_basis,
        cost_basis_currency=position.source_currency,
        unrealized_pl_status="pl_ready",
        unrealized_pl_status_nl=pl_status_nl,
        unrealized_pl_help_nl=pl_help_nl,
        unrealized_pl_available=True,
        unrealized_pl=unrealized_pl,
        unrealized_pl_currency=position.source_currency,
        unrealized_pl_percent_available=unrealized_pl_percent_available,
        unrealized_pl_percent=unrealized_pl_percent,
        converted_unrealized_pl_available=converted_unrealized_pl_available,
        converted_unrealized_pl=converted_unrealized_pl,
        missing_cost_basis_inputs=missing_cost_basis_inputs,
        missing_pl_inputs=missing_pl_inputs,
        cost_basis_input_trace=payload.trace,
        unrealized_pl_input_trace=payload.trace,
    )


def _cost_basis_ready_pl_blocked(
    payload: PositionPlCalculationInput,
    cost_basis: Decimal,
    missing_cost_basis_inputs: list[str],
    missing_pl_inputs: list[str],
) -> PositionPlCalculationResult:
    cost_basis_status_nl, cost_basis_help_nl = _status_text("cost_basis_ready")
    pl_status_nl, pl_help_nl = _status_text("pl_blocked_missing_market_data")
    return PositionPlCalculationResult(
        cost_basis_status="cost_basis_ready",
        cost_basis_status_nl=cost_basis_status_nl,
        cost_basis_help_nl=cost_basis_help_nl,
        cost_basis_available=True,
        cost_basis=cost_basis,
        cost_basis_currency=payload.position.source_currency,
        unrealized_pl_status="pl_blocked_missing_market_data",
        unrealized_pl_status_nl=pl_status_nl,
        unrealized_pl_help_nl=pl_help_nl,
        unrealized_pl_available=False,
        unrealized_pl=None,
        unrealized_pl_currency=None,
        unrealized_pl_percent_available=False,
        unrealized_pl_percent=None,
        converted_unrealized_pl_available=False,
        converted_unrealized_pl=None,
        missing_cost_basis_inputs=missing_cost_basis_inputs,
        missing_pl_inputs=missing_pl_inputs,
        cost_basis_input_trace=payload.trace,
        unrealized_pl_input_trace=payload.trace,
    )


def _blocked(
    payload: PositionPlCalculationInput,
    cost_basis_status: str,
    pl_status: str,
    missing_cost_basis_inputs: list[str],
    missing_pl_inputs: list[str],
) -> PositionPlCalculationResult:
    cost_basis_status_nl, cost_basis_help_nl = _status_text(cost_basis_status)
    pl_status_nl, pl_help_nl = _status_text(pl_status)
    return PositionPlCalculationResult(
        cost_basis_status=cost_basis_status,
        cost_basis_status_nl=cost_basis_status_nl,
        cost_basis_help_nl=cost_basis_help_nl,
        cost_basis_available=False,
        cost_basis=None,
        cost_basis_currency=None,
        unrealized_pl_status=pl_status,
        unrealized_pl_status_nl=pl_status_nl,
        unrealized_pl_help_nl=pl_help_nl,
        unrealized_pl_available=False,
        unrealized_pl=None,
        unrealized_pl_currency=None,
        unrealized_pl_percent_available=False,
        unrealized_pl_percent=None,
        converted_unrealized_pl_available=False,
        converted_unrealized_pl=None,
        missing_cost_basis_inputs=missing_cost_basis_inputs,
        missing_pl_inputs=missing_pl_inputs,
        cost_basis_input_trace=payload.trace,
        unrealized_pl_input_trace=payload.trace,
    )
