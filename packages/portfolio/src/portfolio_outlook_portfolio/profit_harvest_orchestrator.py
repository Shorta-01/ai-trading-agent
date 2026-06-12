"""Profit-harvest suggestion orchestrator (V1.2 §M).

Single entry-point that combines every doctrinal gate built in
Phases 2-7 into one verdict per candidate. The suggestion engine
calls this once per candidate after the forecast layer has produced
a per-name distribution.

Pipeline order is intentional. Cheapest checks first so we shed
losers before doing the lognormal CDF math:

1. **Macro regime** (per-cycle, not per-candidate). If the broad
   market is in a fear regime the gate refuses *every* new BUY for
   this cycle. Callers may evaluate it once and short-circuit the
   entire candidate loop.
2. **Risk universe** — pure-metadata + cheap volatility math. Filters
   out leveraged ETFs, small-caps, and high-vol names.
3. **Confidence gate** — lognormal P(target hit) ≥ user threshold.
   Uses the per-name forecast.
4. **Conviction sizing** — confidence pct → EUR position size in the
   user's [min, max] band.
5. **Sector concentration** — would the sized position push the
   sector over the cap? Run *after* sizing so the projected pct is
   accurate.
6. **Take-profit pair build** — entry LMT + GTC sell LMT at the
   gross level that nets ``target_net_pct`` after Belgian TOB.

The output dataclass carries every gate's diagnostics so the
operator UI can render a full Dutch-language explanation regardless
of where the candidate stopped in the pipeline.

This module is pure Python — no I/O, no datetime; it composes
existing helpers without introducing new math.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final

from portfolio_outlook_portfolio.baseline_forecast import HistoricalBar
from portfolio_outlook_portfolio.belgian_tax import TobSecurityClass
from portfolio_outlook_portfolio.confidence_gate import (
    ConfidenceGateResult,
    evaluate_confidence_gate,
)
from portfolio_outlook_portfolio.earnings_calendar_gate import (
    DEFAULT_EARNINGS_BLOCK_DAYS,
    EarningsGateInputs,
    EarningsGateResult,
    evaluate_earnings_calendar_gate,
)
from portfolio_outlook_portfolio.macro_regime_gate import (
    MacroRegimeInputs,
    MacroRegimeResult,
    evaluate_macro_regime,
)
from portfolio_outlook_portfolio.profit_harvest import (
    conviction_weighted_position_size_eur,
)
from portfolio_outlook_portfolio.risk_universe_gate import (
    RiskUniverseGateResult,
    RiskUniverseInputs,
    evaluate_risk_universe_gate,
)
from portfolio_outlook_portfolio.sector_concentration import (
    SectorAllocation,
    SectorConcentrationResult,
    evaluate_sector_concentration,
)
from portfolio_outlook_portfolio.take_profit_pair import (
    TakeProfitBuilderResult,
    build_take_profit_pair,
)

# Locked top-level verdict codes. The pipeline always populates one
# of these so the audit row has a single "where did this stop?"
# field.
DECISION_SUGGEST: Final[str] = "suggest"
DECISION_SKIP_MACRO: Final[str] = "skip_macro_regime"
DECISION_SKIP_RISK_UNIVERSE: Final[str] = "skip_risk_universe"
DECISION_SKIP_CONFIDENCE: Final[str] = "skip_confidence_gate"
DECISION_SKIP_SIZING: Final[str] = "skip_below_conviction_floor"
DECISION_SKIP_SECTOR: Final[str] = "skip_sector_concentration"
DECISION_SKIP_PAIR_BUILD: Final[str] = "skip_pair_build"
DECISION_SKIP_EARNINGS: Final[str] = "skip_earnings_window"


@dataclass(frozen=True)
class OrchestratorInputs:
    """Everything one candidate evaluation needs.

    Grouped so callers can mutate one logical block (e.g. update
    portfolio allocations between candidates) without rebuilding the
    whole struct.
    """

    # ---- candidate metadata -----------------------------------------
    ticker: str
    instrument_name: str
    sector: str | None
    market_cap_eur: Decimal | None
    security_class: TobSecurityClass
    candidate_bars: Sequence[HistoricalBar]

    # ---- forecast inputs (from baseline / ensemble) -----------------
    current_price: Decimal
    median_forecast_price: Decimal
    annual_volatility_pct: Decimal
    horizon_days: int
    confidence_pct: Decimal

    # ---- macro inputs (per-cycle, shared across candidates) ---------
    vix_level: Decimal | None
    index_bars: Sequence[HistoricalBar]

    # ---- portfolio state --------------------------------------------
    existing_sector_allocations: Sequence[SectorAllocation]

    # ---- earnings calendar (V1.2 §R) --------------------------------
    today: date
    next_earnings_date: date | None

    # ---- user settings ----------------------------------------------
    target_net_pct: Decimal
    confidence_threshold_pct: Decimal
    min_position_eur: Decimal
    max_position_eur: Decimal
    total_budget_eur: Decimal
    min_market_cap_eur: Decimal
    max_annual_volatility_pct: Decimal
    max_sector_pct: Decimal
    # V1.2 §Q fat-tail correction for the confidence gate.
    fat_tail_factor: Decimal = Decimal("1.15")
    # V1.2 §R earnings pre-print exclusion window (calendar days).
    earnings_block_days: int = DEFAULT_EARNINGS_BLOCK_DAYS


@dataclass(frozen=True)
class OrchestratorResult:
    """End-to-end verdict + every gate's diagnostics.

    On a successful SUGGEST the ``pair_build`` field carries the
    fully-specified take-profit order pair. On skip the relevant
    gate's diagnostics tell the UI exactly why.
    """

    decision: str
    blocking_reason: str | None
    macro: MacroRegimeResult | None
    risk_universe: RiskUniverseGateResult | None
    earnings: EarningsGateResult | None
    confidence: ConfidenceGateResult | None
    proposed_position_eur: Decimal | None
    sector_concentration: SectorConcentrationResult | None
    pair_build: TakeProfitBuilderResult | None


def evaluate_profit_harvest_candidate(
    inputs: OrchestratorInputs,
) -> OrchestratorResult:
    """Run the full profit-harvest pipeline over one candidate.

    Pipeline short-circuits at the first failing gate. The previous
    (successful) gates' results stay populated on the
    :class:`OrchestratorResult` so the UI can show them; everything
    after the failing gate is ``None``.
    """

    # 1. Macro regime.
    macro = evaluate_macro_regime(
        MacroRegimeInputs(
            vix_level=inputs.vix_level,
            index_bars=inputs.index_bars,
        )
    )
    if not macro.favorable:
        return OrchestratorResult(
            decision=DECISION_SKIP_MACRO,
            blocking_reason=macro.blocking_reason,
            macro=macro,
            risk_universe=None,
            earnings=None,
            confidence=None,
            proposed_position_eur=None,
            sector_concentration=None,
            pair_build=None,
        )

    # 2. Risk universe.
    risk = evaluate_risk_universe_gate(
        RiskUniverseInputs(
            ticker=inputs.ticker,
            instrument_name=inputs.instrument_name,
            market_cap_eur=inputs.market_cap_eur,
            bars=inputs.candidate_bars,
        ),
        min_market_cap_eur=inputs.min_market_cap_eur,
        max_annual_volatility_pct=inputs.max_annual_volatility_pct,
    )
    if not risk.allowed:
        return OrchestratorResult(
            decision=DECISION_SKIP_RISK_UNIVERSE,
            blocking_reason=risk.blocking_reason,
            macro=macro,
            risk_universe=risk,
            earnings=None,
            confidence=None,
            proposed_position_eur=None,
            sector_concentration=None,
            pair_build=None,
        )

    # 3. Earnings calendar — pure metadata check, cheap.
    earnings = evaluate_earnings_calendar_gate(
        EarningsGateInputs(
            symbol=inputs.ticker,
            today=inputs.today,
            next_earnings_date=inputs.next_earnings_date,
        ),
        days_to_earnings_block=inputs.earnings_block_days,
    )
    if not earnings.allowed:
        return OrchestratorResult(
            decision=DECISION_SKIP_EARNINGS,
            blocking_reason=earnings.blocking_reason,
            macro=macro,
            risk_universe=risk,
            earnings=earnings,
            confidence=None,
            proposed_position_eur=None,
            sector_concentration=None,
            pair_build=None,
        )

    # 4. Confidence gate.
    confidence = evaluate_confidence_gate(
        current_price=inputs.current_price,
        median_forecast_price=inputs.median_forecast_price,
        annual_volatility_pct=inputs.annual_volatility_pct,
        horizon_days=inputs.horizon_days,
        target_net_pct=inputs.target_net_pct,
        security_class=inputs.security_class,
        confidence_threshold_pct=inputs.confidence_threshold_pct,
        fat_tail_factor=inputs.fat_tail_factor,
    )
    if not confidence.allowed:
        return OrchestratorResult(
            decision=DECISION_SKIP_CONFIDENCE,
            blocking_reason=confidence.blocking_reason,
            macro=macro,
            risk_universe=risk,
            earnings=earnings,
            confidence=confidence,
            proposed_position_eur=None,
            sector_concentration=None,
            pair_build=None,
        )

    # 5. Conviction-weighted sizing.
    proposed_size = conviction_weighted_position_size_eur(
        confidence_pct=inputs.confidence_pct,
        confidence_floor_pct=inputs.confidence_threshold_pct,
        min_position_eur=inputs.min_position_eur,
        max_position_eur=inputs.max_position_eur,
    )
    if proposed_size <= 0:
        return OrchestratorResult(
            decision=DECISION_SKIP_SIZING,
            blocking_reason="confidence_below_floor",
            macro=macro,
            risk_universe=risk,
            earnings=earnings,
            confidence=confidence,
            proposed_position_eur=proposed_size,
            sector_concentration=None,
            pair_build=None,
        )

    # 6. Sector concentration — uses the sized position so the
    # projected pct is accurate.
    sector = evaluate_sector_concentration(
        candidate_sector=inputs.sector,
        candidate_intended_eur=proposed_size,
        existing_allocations=inputs.existing_sector_allocations,
        total_budget_eur=inputs.total_budget_eur,
        max_sector_pct=inputs.max_sector_pct,
    )
    if not sector.allowed:
        return OrchestratorResult(
            decision=DECISION_SKIP_SECTOR,
            blocking_reason=sector.blocking_reason,
            macro=macro,
            risk_universe=risk,
            earnings=earnings,
            confidence=confidence,
            proposed_position_eur=proposed_size,
            sector_concentration=sector,
            pair_build=None,
        )

    # 7. Take-profit pair.
    pair_build = build_take_profit_pair(
        ticker=inputs.ticker,
        entry_lmt_price=inputs.current_price,
        intended_position_eur=proposed_size,
        target_net_pct=inputs.target_net_pct,
        security_class=inputs.security_class,
    )
    if not pair_build.allowed:
        return OrchestratorResult(
            decision=DECISION_SKIP_PAIR_BUILD,
            blocking_reason=pair_build.blocking_reason,
            macro=macro,
            risk_universe=risk,
            earnings=earnings,
            confidence=confidence,
            proposed_position_eur=proposed_size,
            sector_concentration=sector,
            pair_build=pair_build,
        )

    return OrchestratorResult(
        decision=DECISION_SUGGEST,
        blocking_reason=None,
        macro=macro,
        risk_universe=risk,
        earnings=earnings,
        confidence=confidence,
        proposed_position_eur=proposed_size,
        sector_concentration=sector,
        pair_build=pair_build,
    )


__all__ = [
    "DECISION_SKIP_CONFIDENCE",
    "DECISION_SKIP_EARNINGS",
    "DECISION_SKIP_MACRO",
    "DECISION_SKIP_PAIR_BUILD",
    "DECISION_SKIP_RISK_UNIVERSE",
    "DECISION_SKIP_SECTOR",
    "DECISION_SKIP_SIZING",
    "DECISION_SUGGEST",
    "OrchestratorInputs",
    "OrchestratorResult",
    "evaluate_profit_harvest_candidate",
]
