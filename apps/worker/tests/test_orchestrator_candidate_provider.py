"""Tests for the live candidate provider (V1.2 §Z)."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio import HistoricalBar

from portfolio_outlook_worker.forecasting.orchestrator_candidate_provider import (
    CandidateProviderInputs,
    ForecastRow,
    FundamentalsRow,
    HeldPositionRow,
    TradingSettingsSnapshot,
    build_candidates,
)

_TODAY = date(2026, 6, 12)


def _bars(count: int = 250) -> tuple[HistoricalBar, ...]:
    base = date(2025, 1, 1)
    price = 100.0
    out = []
    for i in range(count):
        noise = math.sin(i * 17) * 0.015
        price *= math.exp(noise)
        out.append(
            HistoricalBar(
                bar_date=base + timedelta(days=i),
                close_price=Decimal(repr(round(price, 4))),
            )
        )
    return tuple(out)


def _trending_up_bars(count: int = 250) -> tuple[HistoricalBar, ...]:
    base = date(2025, 1, 1)
    return tuple(
        HistoricalBar(
            bar_date=base + timedelta(days=i),
            close_price=Decimal(repr(round(100.0 + i * 0.5, 4))),
        )
        for i in range(count)
    )


def _settings() -> TradingSettingsSnapshot:
    return TradingSettingsSnapshot(
        target_net_pct=Decimal("4"),
        confidence_threshold_pct=Decimal("70"),
        min_position_eur=Decimal("25000"),
        max_position_eur=Decimal("100000"),
        total_budget_eur=Decimal("1000000"),
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
        max_sector_pct=Decimal("25"),
        fat_tail_factor=Decimal("1.15"),
        earnings_block_days=5,
        news_buy_bias_max_boost_pct=Decimal("5"),
    )


def _forecast(
    *,
    forecast_id: str = "fc-1",
    symbol: str = "AAPL",
    p50: Decimal = Decimal("115"),
) -> ForecastRow:
    return ForecastRow(
        forecast_id=forecast_id,
        symbol=symbol,
        ibkr_conid=265598,
        current_price=Decimal("100"),
        p50_price=p50,
        expected_volatility_annual=Decimal("20"),
        horizon_days=126,
        confidence_score=Decimal("0.85"),
    )


def _fundamentals(
    *,
    symbol: str = "AAPL",
    sector: str | None = "technology",
    market_cap_eur: Decimal | None = Decimal("3000000000000"),
) -> FundamentalsRow:
    return FundamentalsRow(
        symbol=symbol,
        sector=sector,
        market_cap_eur=market_cap_eur,
    )


def _inputs(
    *,
    forecasts: tuple[ForecastRow, ...] = (),
    fundamentals: dict[str, FundamentalsRow] | None = None,
    bars: dict[str, tuple[HistoricalBar, ...]] | None = None,
    held_positions: tuple[HeldPositionRow, ...] = (),
    vix_level: Decimal | None = Decimal("15"),
    next_earnings_by_symbol: dict[str, date | None] | None = None,
    excluded_symbols: frozenset[str] = frozenset(),
) -> CandidateProviderInputs:
    return CandidateProviderInputs(
        ibkr_account_ref="DU1234567",
        today=_TODAY,
        forecasts=forecasts,
        fundamentals_by_symbol=fundamentals or {},
        candidate_bars_by_symbol=bars or {},
        held_positions=held_positions,
        settings=_settings(),
        vix_level=vix_level,
        index_bars=_trending_up_bars(),
        next_earnings_by_symbol=next_earnings_by_symbol or {},
        excluded_symbols=excluded_symbols,
    )


# ---- happy path ------------------------------------------------------


def test_single_forecast_maps_to_one_candidate() -> None:
    fc = _forecast()
    result = build_candidates(
        _inputs(
            forecasts=(fc,),
            fundamentals={"AAPL": _fundamentals()},
            bars={"AAPL": _bars()},
        )
    )
    assert result.skipped_count == 0
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.forecast_id == "fc-1"
    assert candidate.ibkr_conid == 265598
    inputs = candidate.orchestrator_inputs
    assert inputs.ticker == "AAPL"
    assert inputs.market_cap_eur == Decimal("3000000000000")
    assert inputs.sector == "technology"
    assert inputs.current_price == Decimal("100")
    assert inputs.median_forecast_price == Decimal("115")
    # Confidence storage 0.85 → orchestrator 85.00.
    assert inputs.confidence_pct == Decimal("85.00")
    assert inputs.today == _TODAY
    # Settings flow through.
    assert inputs.target_net_pct == Decimal("4")
    assert inputs.fat_tail_factor == Decimal("1.15")
    assert inputs.earnings_block_days == 5


def test_multiple_forecasts_yield_multiple_candidates() -> None:
    result = build_candidates(
        _inputs(
            forecasts=(
                _forecast(forecast_id="fc-1", symbol="AAPL"),
                _forecast(forecast_id="fc-2", symbol="MSFT"),
            ),
            fundamentals={
                "AAPL": _fundamentals(symbol="AAPL"),
                "MSFT": _fundamentals(symbol="MSFT"),
            },
            bars={"AAPL": _bars(), "MSFT": _bars()},
        )
    )
    assert result.skipped_count == 0
    assert len(result.candidates) == 2
    assert {c.orchestrator_inputs.ticker for c in result.candidates} == {
        "AAPL",
        "MSFT",
    }


def test_sector_allocations_aggregated_from_held_positions() -> None:
    held = (
        HeldPositionRow(symbol="A", sector="technology", eur_value=Decimal("80000")),
        HeldPositionRow(symbol="B", sector="Technology", eur_value=Decimal("20000")),  # case
        HeldPositionRow(symbol="C", sector="healthcare", eur_value=Decimal("50000")),
        HeldPositionRow(symbol="D", sector=None, eur_value=Decimal("10000")),
    )
    fc = _forecast()
    result = build_candidates(
        _inputs(
            forecasts=(fc,),
            fundamentals={"AAPL": _fundamentals()},
            bars={"AAPL": _bars()},
            held_positions=held,
        )
    )
    allocs = {
        a.sector: a.current_eur
        for a in result.candidates[0].orchestrator_inputs.existing_sector_allocations
    }
    assert allocs["technology"] == Decimal("100000")
    assert allocs["healthcare"] == Decimal("50000")
    assert allocs["unknown"] == Decimal("10000")


# ---- skips -----------------------------------------------------------


def test_missing_fundamentals_skips_with_reason() -> None:
    fc = _forecast(symbol="UNKNOWN")
    result = build_candidates(
        _inputs(
            forecasts=(fc,),
            fundamentals={},
            bars={"UNKNOWN": _bars()},
        )
    )
    assert result.candidates == ()
    assert result.skipped_count == 1
    assert "UNKNOWN" in result.skip_reasons[0]
    assert "missing_fundamentals" in result.skip_reasons[0]


def test_missing_bars_skips_with_reason() -> None:
    fc = _forecast()
    result = build_candidates(
        _inputs(
            forecasts=(fc,),
            fundamentals={"AAPL": _fundamentals()},
            bars={},
        )
    )
    assert result.candidates == ()
    assert result.skipped_count == 1
    assert "missing_candidate_bars" in result.skip_reasons[0]


def test_partial_skip_keeps_good_candidates() -> None:
    result = build_candidates(
        _inputs(
            forecasts=(
                _forecast(forecast_id="fc-1", symbol="AAPL"),
                _forecast(forecast_id="fc-2", symbol="MISSING"),
                _forecast(forecast_id="fc-3", symbol="MSFT"),
            ),
            fundamentals={
                "AAPL": _fundamentals(symbol="AAPL"),
                "MSFT": _fundamentals(symbol="MSFT"),
            },
            bars={"AAPL": _bars(), "MSFT": _bars()},
        )
    )
    assert len(result.candidates) == 2
    assert result.skipped_count == 1


# ---- empty inputs ----------------------------------------------------


def test_empty_forecasts_returns_empty_result() -> None:
    result = build_candidates(_inputs(forecasts=()))
    assert result.candidates == ()
    assert result.skipped_count == 0
    assert result.skip_reasons == ()


def test_no_held_positions_gives_empty_sector_allocations() -> None:
    fc = _forecast()
    result = build_candidates(
        _inputs(
            forecasts=(fc,),
            fundamentals={"AAPL": _fundamentals()},
            bars={"AAPL": _bars()},
            held_positions=(),
        )
    )
    assert result.candidates[0].orchestrator_inputs.existing_sector_allocations == ()


# ---- macro passthrough -----------------------------------------------


def test_vix_and_index_bars_flow_through_to_orchestrator() -> None:
    fc = _forecast()
    result = build_candidates(
        _inputs(
            forecasts=(fc,),
            fundamentals={"AAPL": _fundamentals()},
            bars={"AAPL": _bars()},
            vix_level=Decimal("25"),
        )
    )
    inputs = result.candidates[0].orchestrator_inputs
    assert inputs.vix_level == Decimal("25")
    assert len(inputs.index_bars) == 250


def test_vix_none_passes_through() -> None:
    fc = _forecast()
    result = build_candidates(
        _inputs(
            forecasts=(fc,),
            fundamentals={"AAPL": _fundamentals()},
            bars={"AAPL": _bars()},
            vix_level=None,
        )
    )
    assert result.candidates[0].orchestrator_inputs.vix_level is None


def test_next_earnings_date_threads_from_input_dict() -> None:
    """V1.2 §AI — replaces the hardcoded ``next_earnings_date=None``.

    The orchestrator's earnings-window gate refuses new BUYs inside
    the locked window before earnings; the provider has to thread
    the actual upcoming date in. Symbols missing from the dict stay
    ``None`` (locked gate semantics: missing data does not block).
    """

    aapl = _forecast()
    msft = _forecast(symbol="MSFT", forecast_id="fc-MSFT")
    earnings_date = date(2026, 7, 15)
    result = build_candidates(
        _inputs(
            forecasts=(aapl, msft),
            fundamentals={
                "AAPL": _fundamentals(),
                "MSFT": _fundamentals(),
            },
            bars={"AAPL": _bars(), "MSFT": _bars()},
            next_earnings_by_symbol={"AAPL": earnings_date},
        )
    )
    candidates_by_symbol = {
        c.orchestrator_inputs.ticker: c for c in result.candidates
    }
    assert (
        candidates_by_symbol["AAPL"].orchestrator_inputs.next_earnings_date
        == earnings_date
    )
    assert (
        candidates_by_symbol["MSFT"].orchestrator_inputs.next_earnings_date
        is None
    )


def test_next_earnings_by_symbol_defaults_to_empty_dict() -> None:
    """Backwards-compatible default — existing callers don't have to
    pass the new arg until the morning chain wires it up."""

    fc = _forecast()
    result = build_candidates(
        _inputs(
            forecasts=(fc,),
            fundamentals={"AAPL": _fundamentals()},
            bars={"AAPL": _bars()},
        )
    )
    assert result.candidates[0].orchestrator_inputs.next_earnings_date is None


# ---- V1.2 §AU exclusions --------------------------------------------


def test_excluded_symbol_is_skipped_before_any_lookups() -> None:
    """Operator exclusion takes precedence over even fundamentals or
    bars — the forecast never reaches the gates."""

    result = build_candidates(
        _inputs(
            forecasts=(_forecast(symbol="TSLA"),),
            fundamentals={"TSLA": _fundamentals(symbol="TSLA")},
            bars={"TSLA": _bars()},
            excluded_symbols=frozenset({"TSLA"}),
        )
    )
    assert result.candidates == ()
    assert result.skipped_count == 1
    assert any("excluded_by_operator" in r for r in result.skip_reasons)


def test_exclusion_skips_only_listed_symbol() -> None:
    """Other forecasts proceed normally — exclusion is per-symbol."""

    result = build_candidates(
        _inputs(
            forecasts=(
                _forecast(forecast_id="fc-1", symbol="AAPL"),
                _forecast(forecast_id="fc-2", symbol="TSLA"),
            ),
            fundamentals={
                "AAPL": _fundamentals(symbol="AAPL"),
                "TSLA": _fundamentals(symbol="TSLA"),
            },
            bars={"AAPL": _bars(), "TSLA": _bars()},
            excluded_symbols=frozenset({"TSLA"}),
        )
    )
    assert {c.orchestrator_inputs.ticker for c in result.candidates} == {"AAPL"}
    assert result.skipped_count == 1


def test_empty_exclusion_set_does_not_affect_candidates() -> None:
    """Backwards-compat: the default ``frozenset()`` matches today's
    behaviour exactly."""

    result = build_candidates(
        _inputs(
            forecasts=(_forecast(),),
            fundamentals={"AAPL": _fundamentals()},
            bars={"AAPL": _bars()},
        )
    )
    assert len(result.candidates) == 1
    assert result.skipped_count == 0
