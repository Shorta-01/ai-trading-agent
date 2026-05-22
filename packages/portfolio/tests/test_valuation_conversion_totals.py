from decimal import Decimal

from portfolio_outlook_portfolio.valuation_conversion_totals import (
    CashConversionInput,
    ConversionTotalsInput,
    FxPairConversionInput,
    PositionConversionInput,
    ValuationInputTrace,
    calculate_conversion_totals,
)


def _trace() -> ValuationInputTrace:
    return ValuationInputTrace(
        latest_sync_run_id="run-1",
        position_trace_ids=["pos-1"],
        cash_trace_ids=["cash-1"],
        market_snapshot_ids=["mkt-1"],
        cash_snapshot_ids=["cash-snap-1"],
        fx_snapshot_ids=["fx-1"],
    )


def test_single_currency_complete_inputs() -> None:
    result = calculate_conversion_totals(
        ConversionTotalsInput(
            positions=[PositionConversionInput("p1", "EUR", Decimal("100.10"))],
            cash_values=[CashConversionInput("c1", "EUR", Decimal("25.05"))],
            fx_pairs=[],
            base_currency=None,
            trace=_trace(),
        )
    )
    assert result.status == "conversion_not_required"
    assert result.base_currency == "EUR"
    assert result.total_market_value == Decimal("100.10")
    assert result.total_cash_value == Decimal("25.05")
    assert result.total_portfolio_value == Decimal("125.15")


def test_multi_currency_complete_inputs() -> None:
    result = calculate_conversion_totals(
        ConversionTotalsInput(
            positions=[PositionConversionInput("p1", "USD", Decimal("100.25"))],
            cash_values=[CashConversionInput("c1", "EUR", Decimal("50.10"))],
            fx_pairs=[
                FxPairConversionInput(
                    "USD/EUR", "USD", "EUR", Decimal("0.9"), "fresh", "valid", "fx-1"
                )
            ],
            base_currency="EUR",
            trace=_trace(),
        )
    )
    assert result.status == "conversion_ready"
    assert result.total_market_value == Decimal("90.225")
    assert result.total_cash_value == Decimal("50.10")
    assert result.total_portfolio_value == Decimal("140.325")
    assert result.valuation_input_trace.fx_snapshot_ids == ["fx-1"]


def test_missing_base_currency_blocks() -> None:
    result = calculate_conversion_totals(
        ConversionTotalsInput(
            positions=[PositionConversionInput("p1", "USD", Decimal("100"))],
            cash_values=[CashConversionInput("c1", "EUR", Decimal("50"))],
            fx_pairs=[],
            base_currency=None,
            trace=_trace(),
        )
    )
    assert result.status == "conversion_blocked_missing_base_currency"
    assert result.total_portfolio_value is None


def test_missing_fx_pair_blocks() -> None:
    result = calculate_conversion_totals(
        ConversionTotalsInput(
            positions=[PositionConversionInput("p1", "USD", Decimal("100"))],
            cash_values=[CashConversionInput("c1", "EUR", Decimal("50"))],
            fx_pairs=[],
            base_currency="EUR",
            trace=_trace(),
        )
    )
    assert result.status == "conversion_blocked_missing_fx"
    assert result.missing_fx_pairs == ["USD/EUR"]


def test_stale_fx_pair_blocks() -> None:
    result = calculate_conversion_totals(
        ConversionTotalsInput(
            positions=[PositionConversionInput("p1", "USD", Decimal("100"))],
            cash_values=[CashConversionInput("c1", "EUR", Decimal("50"))],
            fx_pairs=[
                FxPairConversionInput("USD/EUR", "USD", "EUR", Decimal("0.9"), "stale", "valid")
            ],
            base_currency="EUR",
            trace=_trace(),
        )
    )
    assert result.status == "conversion_control_needed_stale_fx"
    assert result.stale_fx_pairs == ["USD/EUR"]


def test_invalid_fx_pair_blocks() -> None:
    result = calculate_conversion_totals(
        ConversionTotalsInput(
            positions=[PositionConversionInput("p1", "USD", Decimal("100"))],
            cash_values=[CashConversionInput("c1", "EUR", Decimal("50"))],
            fx_pairs=[
                FxPairConversionInput("USD/EUR", "USD", "EUR", Decimal("0.9"), "fresh", "invalid")
            ],
            base_currency="EUR",
            trace=_trace(),
        )
    )
    assert result.status == "conversion_blocked_invalid_fx"
    assert result.invalid_fx_pairs == ["USD/EUR"]


def test_unknown_fx_status_is_conservative() -> None:
    result = calculate_conversion_totals(
        ConversionTotalsInput(
            positions=[PositionConversionInput("p1", "USD", Decimal("100"))],
            cash_values=[CashConversionInput("c1", "EUR", Decimal("50"))],
            fx_pairs=[
                FxPairConversionInput("USD/EUR", "USD", "EUR", Decimal("0.9"), "unknown", "valid")
            ],
            base_currency="EUR",
            trace=_trace(),
        )
    )
    assert result.status == "conversion_blocked_invalid_fx"


def test_missing_market_value_blocks() -> None:
    result = calculate_conversion_totals(
        ConversionTotalsInput(
            positions=[PositionConversionInput("p1", "EUR", None)],
            cash_values=[CashConversionInput("c1", "EUR", Decimal("50"))],
            fx_pairs=[],
            base_currency="EUR",
            trace=_trace(),
        )
    )
    assert result.status == "conversion_blocked_missing_market_data"
    assert result.missing_market_data_conids == ["p1"]


def test_missing_cash_blocks() -> None:
    result = calculate_conversion_totals(
        ConversionTotalsInput(
            positions=[PositionConversionInput("p1", "EUR", Decimal("100"))],
            cash_values=[CashConversionInput("c1", "EUR", None)],
            fx_pairs=[],
            base_currency="EUR",
            trace=_trace(),
        )
    )
    assert result.status == "conversion_blocked_missing_cash"
    assert result.missing_cash_inputs == ["c1"]


def test_no_inverse_pair_synthesis() -> None:
    result = calculate_conversion_totals(
        ConversionTotalsInput(
            positions=[PositionConversionInput("p1", "EUR", Decimal("100"))],
            cash_values=[CashConversionInput("c1", "USD", Decimal("50"))],
            fx_pairs=[
                FxPairConversionInput("USD/EUR", "USD", "EUR", Decimal("0.9"), "fresh", "valid")
            ],
            base_currency="USD",
            trace=_trace(),
        )
    )
    assert result.status == "conversion_blocked_missing_fx"
    assert result.missing_fx_pairs == ["EUR/USD"]


def test_decimal_exactness() -> None:
    result = calculate_conversion_totals(
        ConversionTotalsInput(
            positions=[PositionConversionInput("p1", "USD", Decimal("12.345"))],
            cash_values=[CashConversionInput("c1", "EUR", Decimal("0.655"))],
            fx_pairs=[
                FxPairConversionInput(
                    "USD/EUR",
                    "USD",
                    "EUR",
                    Decimal("0.123456789"),
                    "fresh",
                    "valid",
                )
            ],
            base_currency="EUR",
            trace=_trace(),
        )
    )
    assert str(result.total_market_value) == "1.524074060205"
    assert str(result.total_portfolio_value) == "2.179074060205"
