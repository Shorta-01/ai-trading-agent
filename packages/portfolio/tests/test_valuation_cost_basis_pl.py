from decimal import Decimal

from portfolio_outlook_portfolio.valuation_cost_basis_pl import (
    PositionPlCalculationInput,
    PositionPlInput,
    PositionPlInputTrace,
    calculate_position_cost_basis_and_unrealized_pl,
)


def _trace() -> PositionPlInputTrace:
    return PositionPlInputTrace(
        latest_sync_run_id="run-1",
        position_trace_ids=["pos-1"],
        market_snapshot_ids=["mkt-1"],
        fx_snapshot_ids=["fx-1"],
    )


def test_cost_basis_and_pl_ready() -> None:
    result = calculate_position_cost_basis_and_unrealized_pl(
        PositionPlCalculationInput(
            position=PositionPlInput(
                position_id="p1",
                quantity=Decimal("10"),
                source_currency="EUR",
                native_market_value=Decimal("120.50"),
                average_cost_per_unit=Decimal("10.00"),
            ),
            base_currency="EUR",
            trace=_trace(),
        )
    )

    assert result.cost_basis_status == "cost_basis_ready"
    assert result.cost_basis == Decimal("100.00")
    assert result.unrealized_pl_status == "pl_ready"
    assert result.unrealized_pl == Decimal("20.50")
    assert result.unrealized_pl_percent == Decimal("0.205")


def test_missing_average_cost_blocks() -> None:
    result = calculate_position_cost_basis_and_unrealized_pl(
        PositionPlCalculationInput(
            position=PositionPlInput("p1", Decimal("10"), "EUR", Decimal("120"), None),
            base_currency="EUR",
            trace=_trace(),
        )
    )

    assert result.cost_basis_status == "cost_basis_missing"
    assert result.unrealized_pl_status == "pl_blocked_missing_cost_basis"
    assert result.cost_basis is None


def test_missing_market_value_blocks_only_pl() -> None:
    result = calculate_position_cost_basis_and_unrealized_pl(
        PositionPlCalculationInput(
            position=PositionPlInput("p1", Decimal("10"), "EUR", None, Decimal("5")),
            base_currency="EUR",
            trace=_trace(),
        )
    )

    assert result.cost_basis_status == "cost_basis_ready"
    assert result.cost_basis == Decimal("50")
    assert result.unrealized_pl_status == "pl_blocked_missing_market_data"
    assert result.unrealized_pl is None


def test_short_position_is_blocked() -> None:
    result = calculate_position_cost_basis_and_unrealized_pl(
        PositionPlCalculationInput(
            position=PositionPlInput("p1", Decimal("-1"), "EUR", Decimal("10"), Decimal("5")),
            base_currency="EUR",
            trace=_trace(),
        )
    )

    assert result.cost_basis_status == "cost_basis_blocked_short_position"
    assert result.unrealized_pl_available is False


def test_no_float_rounding_decimal_exactness() -> None:
    result = calculate_position_cost_basis_and_unrealized_pl(
        PositionPlCalculationInput(
            position=PositionPlInput(
                "p1",
                Decimal("3.333"),
                "USD",
                Decimal("9.999"),
                Decimal("1.111"),
            ),
            base_currency="USD",
            trace=_trace(),
        )
    )

    assert str(result.cost_basis) == "3.702963"
    assert str(result.unrealized_pl) == "6.296037"
    assert str(result.unrealized_pl_percent) == "1.700102700102700102700102700"


def test_no_zero_fallback_for_missing_quantity() -> None:
    result = calculate_position_cost_basis_and_unrealized_pl(
        PositionPlCalculationInput(
            position=PositionPlInput("p1", None, "EUR", Decimal("120"), Decimal("10")),
            base_currency="EUR",
            trace=_trace(),
        )
    )

    assert result.cost_basis_status == "cost_basis_missing"
    assert result.cost_basis is None
    assert "quantity" in result.missing_cost_basis_inputs
