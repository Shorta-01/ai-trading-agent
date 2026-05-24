"""Deterministic Dutch label translator (V1).

Maps a probabilistic ``BaselineForecast`` plus a risk profile and the
held/not-held context to one of the **locked** Dutch action labels:

    Kopen, Langzaam bijkopen, Houden, Bekijken, Verminderen, Verkopen,
    Vermijden, Cash houden, Geen actie, Geblokkeerd

Hard contract — repeated from ``docs/product/locked-decisions.md``:

* AI never decides the label. Pure Python rules over evidence-gated inputs.
* No suggestion ever auto-promotes to an action draft or order.
* The output of this translator is *evidence-grade information for the user*,
  not an instruction to the system.

Rules below are deliberately conservative: when the inputs do not clearly
support a confident action the translator returns ``Houden`` (for held
positions) or ``Bekijken`` / ``Geen actie`` (for watchlist candidates).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from portfolio_outlook_portfolio.baseline_forecast import BaselineForecast

# ---- Locked label constants ------------------------------------------------


LABEL_KOPEN: Final = "Kopen"
LABEL_LANGZAAM_BIJKOPEN: Final = "Langzaam bijkopen"
LABEL_HOUDEN: Final = "Houden"
LABEL_BEKIJKEN: Final = "Bekijken"
LABEL_VERMINDEREN: Final = "Verminderen"
LABEL_VERKOPEN: Final = "Verkopen"
LABEL_VERMIJDEN: Final = "Vermijden"
LABEL_CASH_HOUDEN: Final = "Cash houden"
LABEL_GEEN_ACTIE: Final = "Geen actie"
LABEL_GEBLOKKEERD: Final = "Geblokkeerd"


LOCKED_ACTION_LABELS: Final[tuple[str, ...]] = (
    LABEL_KOPEN,
    LABEL_LANGZAAM_BIJKOPEN,
    LABEL_HOUDEN,
    LABEL_BEKIJKEN,
    LABEL_VERMINDEREN,
    LABEL_VERKOPEN,
    LABEL_VERMIJDEN,
    LABEL_CASH_HOUDEN,
    LABEL_GEEN_ACTIE,
    LABEL_GEBLOKKEERD,
)


# ---- Locked risk profile constants -----------------------------------------


RISK_PROFILE_VOORZICHTIG: Final = "Voorzichtig"
RISK_PROFILE_GEBALANCEERD: Final = "Gebalanceerd"
RISK_PROFILE_GROEI: Final = "Groei"

LOCKED_RISK_PROFILES: Final[tuple[str, ...]] = (
    RISK_PROFILE_VOORZICHTIG,
    RISK_PROFILE_GEBALANCEERD,
    RISK_PROFILE_GROEI,
)


# ---- Confidence thresholds (Hoog/Middel/Laag) ------------------------------


CONFIDENCE_HIGH_THRESHOLD: Final[Decimal] = Decimal("0.70")
CONFIDENCE_MEDIUM_THRESHOLD: Final[Decimal] = Decimal("0.50")

CONFIDENCE_LABEL_HIGH: Final = "Hoog"
CONFIDENCE_LABEL_MEDIUM: Final = "Middel"
CONFIDENCE_LABEL_LOW: Final = "Laag"


MODEL_CODE: Final = "baseline_label_translator"
MODEL_VERSION: Final = "v1.0.0"


# ---- Inputs / outputs ------------------------------------------------------


@dataclass(frozen=True)
class SuggestionInputs:
    forecast: BaselineForecast
    risk_profile: str
    has_position: bool
    gate_failures: tuple[str, ...] = ()
    """Optional list of gate IDs that failed (e.g. ``("stale_market_data",)``).
    A non-empty value forces the translator to return ``Bekijken`` or
    ``Geblokkeerd`` so the user is told to control the inputs rather than
    given a confident action."""


@dataclass(frozen=True)
class SuggestionDecision:
    action_label: str
    action_label_nl: str
    confidence_label: str
    confidence_label_nl: str
    confidence_score: Decimal
    rationale_nl: str
    drivers: tuple[str, ...]
    blockers: tuple[str, ...]
    status: str  # "ready" | "blocked" | "control_needed"
    blocking_reason: str | None
    risk_profile: str
    has_position: bool
    model_code: str = MODEL_CODE
    model_version: str = MODEL_VERSION


# ---- Internal helpers ------------------------------------------------------


def _normalize_risk_profile(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return RISK_PROFILE_GEBALANCEERD
    for canonical in LOCKED_RISK_PROFILES:
        if canonical.lower() == text.lower():
            return canonical
    return RISK_PROFILE_GEBALANCEERD


def _confidence_label(score: Decimal) -> tuple[str, str]:
    if score >= CONFIDENCE_HIGH_THRESHOLD:
        return CONFIDENCE_LABEL_HIGH, "Hoog"
    if score >= CONFIDENCE_MEDIUM_THRESHOLD:
        return CONFIDENCE_LABEL_MEDIUM, "Middel"
    return CONFIDENCE_LABEL_LOW, "Laag"


def _build_drivers(forecast: BaselineForecast) -> tuple[str, ...]:
    return (
        f"direction_label={forecast.direction_label}",
        f"prob_gain={forecast.prob_gain}",
        f"prob_loss={forecast.prob_loss}",
        f"expected_return_pct={forecast.expected_return_pct}",
        f"expected_volatility_annual={forecast.expected_volatility_annual}",
        f"downside_risk_score={forecast.downside_risk_score}",
        f"confidence_score={forecast.confidence_score}",
        f"horizon_days={forecast.horizon_days}",
    )


def _format_blockers(values: Iterable[str]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _rationale(label_nl: str, forecast: BaselineForecast, profile: str) -> str:
    return (
        f"{label_nl}: baseline-richting {forecast.direction_label} met "
        f"betrouwbaarheid {forecast.confidence_score} en kans op stijging "
        f"{forecast.prob_gain}; risicoprofiel {profile}, horizon "
        f"{forecast.horizon_days} dagen. Geen action drafts of orders."
    )


# ---- Public translator -----------------------------------------------------


def translate_forecast_to_label(inputs: SuggestionInputs) -> SuggestionDecision:
    """Apply the locked-label rules and return a typed ``SuggestionDecision``.

    The decision tree is intentionally simple and fully documented in the
    inline comments below — every branch maps to one of the 10 locked labels.
    """

    forecast = inputs.forecast
    profile = _normalize_risk_profile(inputs.risk_profile)
    confidence_label, confidence_label_nl = _confidence_label(forecast.confidence_score)
    drivers = _build_drivers(forecast)

    # 1. Gate failures escalate above any direction analysis.
    if inputs.gate_failures:
        blockers = _format_blockers(inputs.gate_failures)
        label = LABEL_BEKIJKEN
        return SuggestionDecision(
            action_label=label,
            action_label_nl=label,
            confidence_label=confidence_label,
            confidence_label_nl=confidence_label_nl,
            confidence_score=forecast.confidence_score,
            rationale_nl=(
                "Eerst controle nodig: niet alle gates zijn geslaagd."
                " Geen advies tot blockers zijn opgelost."
            ),
            drivers=drivers,
            blockers=blockers,
            status="control_needed",
            blocking_reason="gate_failures",
            risk_profile=profile,
            has_position=inputs.has_position,
        )

    # 2. A blocked forecast cannot drive a label by itself.
    if forecast.status != "ready" or forecast.blocking_reason is not None:
        reason = forecast.blocking_reason or "forecast_not_ready"
        label = LABEL_GEBLOKKEERD
        return SuggestionDecision(
            action_label=label,
            action_label_nl=label,
            confidence_label=confidence_label,
            confidence_label_nl=confidence_label_nl,
            confidence_score=forecast.confidence_score,
            rationale_nl=(
                "Baseline-voorspelling is niet beschikbaar; "
                "geen suggestie tot data en model klaar zijn."
            ),
            drivers=drivers,
            blockers=(reason,),
            status="blocked",
            blocking_reason=reason,
            risk_profile=profile,
            has_position=inputs.has_position,
        )

    # 3. Apply held-position vs cold-start rules.
    label = _label_for_held(forecast, profile, confidence_label) if inputs.has_position else (
        _label_for_cold_start(forecast, profile, confidence_label)
    )

    return SuggestionDecision(
        action_label=label,
        action_label_nl=label,
        confidence_label=confidence_label,
        confidence_label_nl=confidence_label_nl,
        confidence_score=forecast.confidence_score,
        rationale_nl=_rationale(label, forecast, profile),
        drivers=drivers,
        blockers=(),
        status="ready",
        blocking_reason=None,
        risk_profile=profile,
        has_position=inputs.has_position,
    )


def _label_for_held(
    forecast: BaselineForecast,
    risk_profile: str,
    confidence_label: str,
) -> str:
    """Decision tree for an already-held position.

    The doctrine prefers ``Houden`` whenever evidence is ambiguous; only strong
    downward signals at high confidence drive a sell, and only strong upward
    signals at high confidence with a growth profile drive a top-up.
    """

    direction = forecast.direction_label
    if direction == "strong_down":
        if confidence_label == CONFIDENCE_LABEL_HIGH:
            return LABEL_VERKOPEN
        if confidence_label == CONFIDENCE_LABEL_MEDIUM:
            return LABEL_VERMINDEREN
        return LABEL_BEKIJKEN
    if direction == "slight_down":
        if confidence_label == CONFIDENCE_LABEL_HIGH:
            return LABEL_VERMINDEREN
        return LABEL_HOUDEN
    if direction in {"neutral", "slight_up"}:
        return LABEL_HOUDEN
    if direction == "strong_up":
        if (
            risk_profile == RISK_PROFILE_GROEI
            and confidence_label == CONFIDENCE_LABEL_HIGH
        ):
            return LABEL_LANGZAAM_BIJKOPEN
        return LABEL_HOUDEN
    return LABEL_HOUDEN


def _label_for_cold_start(
    forecast: BaselineForecast,
    risk_profile: str,
    confidence_label: str,
) -> str:
    """Decision tree for a non-held asset (watchlist / `Nieuwe kansen`).

    A new buy is the most consequential output of the translator, so the rule
    is conservative: ``Kopen`` only on ``strong_up`` with ``Hoog`` confidence
    on a ``Groei`` profile. Every other ``up`` direction routes to
    ``Bekijken`` so the user reviews the evidence first; every ``down``
    direction routes to ``Vermijden``.
    """

    direction = forecast.direction_label
    if direction == "strong_up":
        if (
            risk_profile == RISK_PROFILE_GROEI
            and confidence_label == CONFIDENCE_LABEL_HIGH
        ):
            return LABEL_KOPEN
        if confidence_label == CONFIDENCE_LABEL_HIGH:
            return LABEL_BEKIJKEN
        return LABEL_BEKIJKEN
    if direction == "slight_up":
        if confidence_label in {CONFIDENCE_LABEL_HIGH, CONFIDENCE_LABEL_MEDIUM}:
            return LABEL_BEKIJKEN
        return LABEL_GEEN_ACTIE
    if direction == "neutral":
        return LABEL_GEEN_ACTIE
    if direction == "slight_down":
        return LABEL_VERMIJDEN
    if direction == "strong_down":
        return LABEL_VERMIJDEN
    return LABEL_GEEN_ACTIE
