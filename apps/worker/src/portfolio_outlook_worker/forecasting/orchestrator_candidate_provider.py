"""Live candidate provider for the orchestrator scoring leg (V1.2 §Z).

Converts the pre-fetched live data (forecasts, fundamentals, held
positions, user settings) into a list of
:class:`CandidateScoringInput` ready for the runner from V1.2 §X.

Design:

* **Pure transformation, no I/O.** The caller pre-fetches data
  via the SQL repositories and hands it in as plain dataclasses.
  Keeps this module fully unit-testable with stub inputs.
* **Skip silently on missing per-symbol metadata.** A forecast
  without a fundamentals row (no market cap / sector) is skipped
  with a count, not surfaced as an error — the morning chain
  records the skip in the leg's detail string. Missing forecasts
  for a held name are *not* skipped; that just means we don't
  score that name this cycle.
* **Macro defaults are explicit knobs.** VIX and index bars are
  inputs to the provider. Until the live market-data feed is
  wired (out of scope for this slice) the caller passes safe
  defaults: VIX 15 and a synthetic uptrend. This keeps the
  per-name gates honest while documenting the gap.

The provider does NOT decide which forecasts to score — that's
the caller's responsibility (e.g. "the most recent forecast per
held symbol"). The provider just maps each supplied row to a
runnable input.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from portfolio_outlook_portfolio import (
    HistoricalBar,
    OrchestratorInputs,
    SectorAllocation,
    TobSecurityClass,
)

from portfolio_outlook_worker.forecasting.orchestrator_scoring_runner import (
    CandidateScoringInput,
)


@dataclass(frozen=True)
class ForecastRow:
    """Subset of an ``asset_forecasts`` row the provider consumes."""

    forecast_id: str
    symbol: str
    ibkr_conid: int | None
    current_price: Decimal
    p50_price: Decimal
    expected_volatility_annual: Decimal
    horizon_days: int
    confidence_score: Decimal  # 0–1 in storage


@dataclass(frozen=True)
class FundamentalsRow:
    """Subset of an ``asset_fundamentals_snapshots`` row."""

    symbol: str
    sector: str | None
    market_cap_eur: Decimal | None


@dataclass(frozen=True)
class HeldPositionRow:
    """Held-position row used for sector concentration aggregation."""

    symbol: str
    sector: str | None
    eur_value: Decimal


@dataclass(frozen=True)
class TradingSettingsSnapshot:
    """The 13 V1.2 user settings the orchestrator consumes."""

    target_net_pct: Decimal
    confidence_threshold_pct: Decimal
    min_position_eur: Decimal
    max_position_eur: Decimal
    total_budget_eur: Decimal
    min_market_cap_eur: Decimal
    max_annual_volatility_pct: Decimal
    max_sector_pct: Decimal
    fat_tail_factor: Decimal
    earnings_block_days: int
    news_buy_bias_max_boost_pct: Decimal


@dataclass(frozen=True)
class CandidateProviderInputs:
    """Everything one provider call needs, pre-fetched by the caller."""

    ibkr_account_ref: str
    today: date
    forecasts: Sequence[ForecastRow]
    fundamentals_by_symbol: dict[str, FundamentalsRow]
    candidate_bars_by_symbol: dict[str, tuple[HistoricalBar, ...]]
    held_positions: Sequence[HeldPositionRow]
    settings: TradingSettingsSnapshot
    # Macro placeholders until live VIX + index feeds are wired.
    vix_level: Decimal | None
    index_bars: tuple[HistoricalBar, ...]
    # V1.2 §AI — nearest future earnings date per symbol from the
    # earnings_events table. Missing symbols stay ``None`` (locked
    # gate semantics: missing data does not block; see
    # earnings_calendar_gate doctrine).
    next_earnings_by_symbol: dict[str, date | None] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateProviderResult:
    """List of scoreable candidates + a count of forecasts skipped.

    ``skipped_count`` is reported back so the morning-chain leg can
    write it in the audit row's ``detail_nl`` ("Scored 12 of 18
    forecasts; 6 lacked fundamentals snapshot").
    """

    candidates: tuple[CandidateScoringInput, ...]
    skipped_count: int
    skip_reasons: tuple[str, ...]


def _aggregate_sector_allocations(
    positions: Sequence[HeldPositionRow],
) -> tuple[SectorAllocation, ...]:
    """Group held positions by sector and sum EUR values.

    Empty / None sector buckets all roll into ``"unknown"`` to match
    the locked behaviour of the sector-concentration gate.
    """

    totals: dict[str, Decimal] = {}
    for position in positions:
        key = (
            (position.sector or "").strip().lower()
            if position.sector is not None
            else ""
        )
        if not key:
            key = "unknown"
        totals[key] = totals.get(key, Decimal("0")) + position.eur_value
    return tuple(
        SectorAllocation(sector=sector, current_eur=value)
        for sector, value in sorted(totals.items())
    )


def build_candidates(
    inputs: CandidateProviderInputs,
) -> CandidateProviderResult:
    """Convert pre-fetched live data into runner-ready candidates.

    For each forecast in ``inputs.forecasts``:

    1. Look up the symbol's fundamentals + bars. Skip with a logged
       reason if either is missing.
    2. Build the full :class:`OrchestratorInputs` using the
       per-symbol data + the shared portfolio / macro / settings
       state.
    3. Wrap into a :class:`CandidateScoringInput` for the runner.

    The provider always treats every name as a standard stock (TOB
    rate 0.35 %) — V1 universe is US equities. A future slice will
    map asset_type → ``TobSecurityClass`` once the worker has that
    metadata in hand.
    """

    sector_allocations = _aggregate_sector_allocations(inputs.held_positions)
    candidates: list[CandidateScoringInput] = []
    skip_reasons: list[str] = []

    for forecast in inputs.forecasts:
        symbol = forecast.symbol
        fundamentals = inputs.fundamentals_by_symbol.get(symbol)
        bars = inputs.candidate_bars_by_symbol.get(symbol)
        if fundamentals is None:
            skip_reasons.append(f"{symbol}: missing_fundamentals")
            continue
        if bars is None or len(bars) == 0:
            skip_reasons.append(f"{symbol}: missing_candidate_bars")
            continue

        # Storage stores confidence as 0–1; orchestrator wants 0–100.
        confidence_pct = (forecast.confidence_score * Decimal("100")).quantize(
            Decimal("0.01")
        )

        orchestrator_inputs = OrchestratorInputs(
            ticker=symbol,
            instrument_name=symbol,  # Provider doesn't have human name yet
            sector=fundamentals.sector,
            market_cap_eur=fundamentals.market_cap_eur,
            security_class=TobSecurityClass.STANDARD_STOCK,
            candidate_bars=bars,
            current_price=forecast.current_price,
            median_forecast_price=forecast.p50_price,
            annual_volatility_pct=forecast.expected_volatility_annual,
            horizon_days=forecast.horizon_days,
            confidence_pct=confidence_pct,
            vix_level=inputs.vix_level,
            index_bars=inputs.index_bars,
            existing_sector_allocations=sector_allocations,
            today=inputs.today,
            next_earnings_date=inputs.next_earnings_by_symbol.get(symbol),
            target_net_pct=inputs.settings.target_net_pct,
            confidence_threshold_pct=inputs.settings.confidence_threshold_pct,
            min_position_eur=inputs.settings.min_position_eur,
            max_position_eur=inputs.settings.max_position_eur,
            total_budget_eur=inputs.settings.total_budget_eur,
            min_market_cap_eur=inputs.settings.min_market_cap_eur,
            max_annual_volatility_pct=inputs.settings.max_annual_volatility_pct,
            max_sector_pct=inputs.settings.max_sector_pct,
            fat_tail_factor=inputs.settings.fat_tail_factor,
            earnings_block_days=inputs.settings.earnings_block_days,
            news_buy_bias_max_boost_pct=inputs.settings.news_buy_bias_max_boost_pct,
        )
        candidates.append(
            CandidateScoringInput(
                orchestrator_inputs=orchestrator_inputs,
                forecast_id=forecast.forecast_id,
                ibkr_conid=forecast.ibkr_conid,
            )
        )

    return CandidateProviderResult(
        candidates=tuple(candidates),
        skipped_count=len(skip_reasons),
        skip_reasons=tuple(skip_reasons),
    )


__all__ = [
    "CandidateProviderInputs",
    "CandidateProviderResult",
    "ForecastRow",
    "FundamentalsRow",
    "HeldPositionRow",
    "TradingSettingsSnapshot",
    "build_candidates",
]
