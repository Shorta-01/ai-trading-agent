"""Tests for the deterministic Dutch label translator.

Every branch of the decision tree maps to a locked label; the tests pin those
branches exactly so a future change to the rules has to update the tests too.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from portfolio_outlook_portfolio.baseline_forecast import BaselineForecast
from portfolio_outlook_portfolio.baseline_label_translator import (
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
    LABEL_BEKIJKEN,
    LABEL_GEBLOKKEERD,
    LABEL_GEEN_ACTIE,
    LABEL_HOUDEN,
    LABEL_KOPEN,
    LABEL_LANGZAAM_BIJKOPEN,
    LABEL_VERKOPEN,
    LABEL_VERMIJDEN,
    LABEL_VERMINDEREN,
    LOCKED_ACTION_LABELS,
    RISK_PROFILE_GEBALANCEERD,
    RISK_PROFILE_GROEI,
    RISK_PROFILE_VOORZICHTIG,
    SuggestionInputs,
    translate_forecast_to_label,
)


def _forecast(
    *,
    direction: str = "neutral",
    confidence: str = "0.80",
    status: str = "ready",
    blocking_reason: str | None = None,
) -> BaselineForecast:
    return BaselineForecast(
        horizon_days=21,
        data_points_used=200,
        history_first_bar_date=date(2024, 8, 1),
        history_last_bar_date=date(2025, 5, 23),
        current_price=Decimal("100"),
        expected_return_pct=Decimal("0"),
        p10_price=Decimal("95"),
        p50_price=Decimal("100"),
        p90_price=Decimal("105"),
        prob_gain=Decimal("0.5"),
        prob_loss=Decimal("0.5"),
        prob_loss_gt_5pct=Decimal("0.1"),
        prob_loss_gt_10pct=Decimal("0.01"),
        prob_gain_gt_5pct=Decimal("0.1"),
        prob_gain_gt_10pct=Decimal("0.01"),
        expected_volatility_annual=Decimal("0.18"),
        downside_risk_score=Decimal("5.0"),
        confidence_score=Decimal(confidence),
        direction_label=direction,
        direction_label_nl="test",
        explanation_nl="test",
        status=status,
        blocking_reason=blocking_reason,
    )


# ---- confidence labelling --------------------------------------------------


def test_confidence_label_is_hoog_at_or_above_threshold() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(confidence=str(CONFIDENCE_HIGH_THRESHOLD), direction="neutral"),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=True,
        )
    )
    assert decision.confidence_label == "Hoog"


def test_confidence_label_is_middel_between_thresholds() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(
                confidence=str(CONFIDENCE_MEDIUM_THRESHOLD), direction="neutral"
            ),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=True,
        )
    )
    assert decision.confidence_label == "Middel"


def test_confidence_label_is_laag_below_medium_threshold() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(confidence="0.10", direction="neutral"),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=True,
        )
    )
    assert decision.confidence_label == "Laag"


# ---- gate failures and blocked forecasts ----------------------------------


def test_gate_failure_returns_bekijken_with_control_needed_status() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_up", confidence="0.95"),
            risk_profile=RISK_PROFILE_GROEI,
            has_position=False,
            gate_failures=("stale_market_data",),
        )
    )
    assert decision.action_label == LABEL_BEKIJKEN
    assert decision.status == "control_needed"
    assert "stale_market_data" in decision.blockers
    assert decision.blocking_reason == "gate_failures"


def test_blocked_forecast_returns_geblokkeerd() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(
                status="blocked",
                blocking_reason="insufficient_history",
                direction="blocked",
            ),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=True,
        )
    )
    assert decision.action_label == LABEL_GEBLOKKEERD
    assert decision.status == "blocked"
    assert decision.blocking_reason == "insufficient_history"


# ---- held-position rules ---------------------------------------------------


def test_held_strong_down_with_high_confidence_is_verkopen() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_down", confidence="0.85"),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=True,
        )
    )
    assert decision.action_label == LABEL_VERKOPEN


def test_held_strong_down_with_medium_confidence_is_verminderen() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_down", confidence="0.55"),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=True,
        )
    )
    assert decision.action_label == LABEL_VERMINDEREN


def test_held_strong_down_with_low_confidence_is_bekijken() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_down", confidence="0.35"),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=True,
        )
    )
    assert decision.action_label == LABEL_BEKIJKEN


def test_held_slight_down_with_high_confidence_is_verminderen() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="slight_down", confidence="0.85"),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=True,
        )
    )
    assert decision.action_label == LABEL_VERMINDEREN


def test_held_slight_down_with_lower_confidence_is_houden() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="slight_down", confidence="0.55"),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=True,
        )
    )
    assert decision.action_label == LABEL_HOUDEN


@pytest.mark.parametrize("direction", ["neutral", "slight_up"])
def test_held_neutral_or_slight_up_is_houden_regardless_of_profile(direction: str) -> None:
    for profile in (
        RISK_PROFILE_VOORZICHTIG,
        RISK_PROFILE_GEBALANCEERD,
        RISK_PROFILE_GROEI,
    ):
        decision = translate_forecast_to_label(
            SuggestionInputs(
                forecast=_forecast(direction=direction, confidence="0.85"),
                risk_profile=profile,
                has_position=True,
            )
        )
        assert decision.action_label == LABEL_HOUDEN


def test_held_strong_up_high_confidence_on_groei_is_langzaam_bijkopen() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_up", confidence="0.85"),
            risk_profile=RISK_PROFILE_GROEI,
            has_position=True,
        )
    )
    assert decision.action_label == LABEL_LANGZAAM_BIJKOPEN


def test_held_strong_up_on_voorzichtig_stays_houden() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_up", confidence="0.85"),
            risk_profile=RISK_PROFILE_VOORZICHTIG,
            has_position=True,
        )
    )
    assert decision.action_label == LABEL_HOUDEN


def test_held_strong_up_with_low_confidence_stays_houden_on_groei() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_up", confidence="0.40"),
            risk_profile=RISK_PROFILE_GROEI,
            has_position=True,
        )
    )
    assert decision.action_label == LABEL_HOUDEN


# ---- cold-start (non-held) rules -------------------------------------------


def test_cold_start_strong_up_high_confidence_on_groei_is_kopen() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_up", confidence="0.85"),
            risk_profile=RISK_PROFILE_GROEI,
            has_position=False,
        )
    )
    assert decision.action_label == LABEL_KOPEN


def test_cold_start_strong_up_on_gebalanceerd_is_bekijken() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_up", confidence="0.85"),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=False,
        )
    )
    assert decision.action_label == LABEL_BEKIJKEN


def test_cold_start_strong_up_on_voorzichtig_is_bekijken() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_up", confidence="0.85"),
            risk_profile=RISK_PROFILE_VOORZICHTIG,
            has_position=False,
        )
    )
    assert decision.action_label == LABEL_BEKIJKEN


def test_cold_start_strong_up_with_medium_confidence_is_bekijken() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_up", confidence="0.55"),
            risk_profile=RISK_PROFILE_GROEI,
            has_position=False,
        )
    )
    assert decision.action_label == LABEL_BEKIJKEN


def test_cold_start_slight_up_with_medium_or_high_confidence_is_bekijken() -> None:
    for confidence in ("0.55", "0.85"):
        decision = translate_forecast_to_label(
            SuggestionInputs(
                forecast=_forecast(direction="slight_up", confidence=confidence),
                risk_profile=RISK_PROFILE_GEBALANCEERD,
                has_position=False,
            )
        )
        assert decision.action_label == LABEL_BEKIJKEN


def test_cold_start_slight_up_with_low_confidence_is_geen_actie() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="slight_up", confidence="0.40"),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=False,
        )
    )
    assert decision.action_label == LABEL_GEEN_ACTIE


def test_cold_start_neutral_is_geen_actie() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="neutral", confidence="0.80"),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=False,
        )
    )
    assert decision.action_label == LABEL_GEEN_ACTIE


@pytest.mark.parametrize("direction", ["slight_down", "strong_down"])
def test_cold_start_downward_directions_are_vermijden(direction: str) -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction=direction, confidence="0.85"),
            risk_profile=RISK_PROFILE_GEBALANCEERD,
            has_position=False,
        )
    )
    assert decision.action_label == LABEL_VERMIJDEN


# ---- general invariants ----------------------------------------------------


def test_every_returned_label_is_in_the_locked_set() -> None:
    profiles = (RISK_PROFILE_VOORZICHTIG, RISK_PROFILE_GEBALANCEERD, RISK_PROFILE_GROEI)
    for direction in ("strong_down", "slight_down", "neutral", "slight_up", "strong_up"):
        for confidence in ("0.20", "0.55", "0.85"):
            for profile in profiles:
                for has_position in (False, True):
                    decision = translate_forecast_to_label(
                        SuggestionInputs(
                            forecast=_forecast(
                                direction=direction, confidence=confidence
                            ),
                            risk_profile=profile,
                            has_position=has_position,
                        )
                    )
                    assert decision.action_label in LOCKED_ACTION_LABELS


def test_unknown_risk_profile_falls_back_to_gebalanceerd_safely() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_up", confidence="0.85"),
            risk_profile="totally-unknown",
            has_position=False,
        )
    )
    # Falls back to Gebalanceerd → strong_up + high confidence → Bekijken.
    assert decision.action_label == LABEL_BEKIJKEN
    assert decision.risk_profile == RISK_PROFILE_GEBALANCEERD


def test_drivers_and_rationale_are_populated() -> None:
    decision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=_forecast(direction="strong_up", confidence="0.85"),
            risk_profile=RISK_PROFILE_GROEI,
            has_position=False,
        )
    )
    assert any("direction_label=strong_up" in d for d in decision.drivers)
    assert decision.rationale_nl  # non-empty


# ---- #3 portfolio-context gate post-processor ---------------------------


def _kopen_decision() -> "SuggestionDecision":
    """Build a happy-path Kopen decision from a strong-up cold-start
    forecast we can then post-process through the gate."""

    from portfolio_outlook_portfolio.baseline_forecast import BaselineForecast
    from portfolio_outlook_portfolio.baseline_label_translator import (
        SuggestionDecision,
        SuggestionInputs,
        translate_forecast_to_label,
    )

    forecast = BaselineForecast(
        horizon_days=30,
        data_points_used=120,
        history_first_bar_date=None,
        history_last_bar_date=None,
        current_price=Decimal("100"),
        # 5% expected on 5% vol → strong Sharpe → strong_up.
        expected_return_pct=Decimal("5.0"),
        p10_price=Decimal("90"),
        p50_price=Decimal("105"),
        p90_price=Decimal("120"),
        prob_gain=Decimal("0.8"),
        prob_loss=Decimal("0.2"),
        prob_loss_gt_5pct=Decimal("0.1"),
        prob_loss_gt_10pct=Decimal("0.02"),
        prob_gain_gt_5pct=Decimal("0.5"),
        prob_gain_gt_10pct=Decimal("0.2"),
        expected_volatility_annual=Decimal("0.05"),
        downside_risk_score=Decimal("5"),
        confidence_score=Decimal("0.85"),
        direction_label="strong_up",
        direction_label_nl="Sterke stijging verwacht",
        explanation_nl="test",
        status="ready",
        blocking_reason=None,
    )
    decision: SuggestionDecision = translate_forecast_to_label(
        SuggestionInputs(
            forecast=forecast, risk_profile="Groei", has_position=False
        )
    )
    # Sanity: this fixture really produces Kopen.
    assert decision.action_label == "Kopen"
    return decision


def test_portfolio_gate_passes_through_when_no_context_supplied() -> None:
    """A PortfolioContext with all None fields is a no-op."""

    from portfolio_outlook_portfolio.baseline_label_translator import (
        PortfolioContext,
        apply_portfolio_context_gates,
    )

    decision = _kopen_decision()
    out = apply_portfolio_context_gates(decision, PortfolioContext())
    assert out is decision  # untouched


def test_portfolio_gate_downgrades_to_bekijken_when_already_at_max_position() -> None:
    """The user's per-position cap is the hardest gate: at-or-past it,
    don't suggest more, regardless of how strong the forecast is."""

    from portfolio_outlook_portfolio.baseline_label_translator import (
        PortfolioContext,
        apply_portfolio_context_gates,
    )

    out = apply_portfolio_context_gates(
        _kopen_decision(),
        PortfolioContext(
            current_position_pct=Decimal("10"),
            max_position_pct=Decimal("10"),
        ),
    )
    assert out.action_label == "Bekijken"
    assert out.status == "control_needed"
    assert "over_max_position_pct" in out.blockers


def test_portfolio_gate_downgrades_when_sector_concentration_is_at_cap() -> None:
    """A 6th tech name doesn't diversify; downgrade to Bekijken."""

    from portfolio_outlook_portfolio.baseline_label_translator import (
        PortfolioContext,
        apply_portfolio_context_gates,
    )

    out = apply_portfolio_context_gates(
        _kopen_decision(),
        PortfolioContext(sector_pct=Decimal("30")),  # default cap is 30%
    )
    assert out.action_label == "Bekijken"
    assert "over_max_sector_pct" in out.blockers


def test_portfolio_gate_downgrades_when_cost_dominates_expected_gain() -> None:
    """Default ratio: cost must be < 1/3 of expected return. With a 5%
    expected return, a 2% round-trip cost trips the gate (cost > 33%)."""

    from portfolio_outlook_portfolio.baseline_label_translator import (
        PortfolioContext,
        apply_portfolio_context_gates,
    )

    out = apply_portfolio_context_gates(
        _kopen_decision(),
        PortfolioContext(estimated_round_trip_cost_pct=Decimal("2.0")),
    )
    assert out.action_label == "Bekijken"
    assert "cost_exceeds_gain" in out.blockers


def test_portfolio_gate_leaves_non_buy_labels_alone() -> None:
    """The gate only affects buy proposals — selling a sector that's
    already over-weighted, for example, should still be Verkopen."""

    from portfolio_outlook_portfolio.baseline_label_translator import (
        PortfolioContext,
        SuggestionDecision,
        apply_portfolio_context_gates,
    )

    sell_decision = SuggestionDecision(
        action_label="Verkopen",
        action_label_nl="Verkopen",
        confidence_label="Hoog",
        confidence_label_nl="Hoog",
        confidence_score=Decimal("0.85"),
        rationale_nl="test",
        drivers=("expected_return_pct=-10",),
        blockers=(),
        status="ready",
        blocking_reason=None,
        risk_profile="Gebalanceerd",
        has_position=True,
    )
    out = apply_portfolio_context_gates(
        sell_decision,
        PortfolioContext(sector_pct=Decimal("50")),
    )
    assert out is sell_decision  # untouched
