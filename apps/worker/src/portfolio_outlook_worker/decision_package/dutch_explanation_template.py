"""Task 132: deterministic Dutch explanation template.

Pure Python templating. No AI. No conditional prose beyond the locked
branches below. Same forecast + same gate outcomes always produces the
exact same paragraph — that's the doctrine: "AI never originates a
field of the Decision Package".

The paragraph structure is locked:

    {opening sentence with asset name + label + horizon}
    {forecast quantile sentence with p10/p50/p90 prices in EUR}
    {probability sentence with prob_positive + prob_loss_gt_5pct}
    {risk sentence with annualized volatility}
    {confidence sentence}
    {validity sentence}
    {one "Let op: <reason>" sentence per failed gate}

UI surfaces the paragraph verbatim — no client-side rendering of
forecast numbers, no client-side translation.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

from ai_trading_agent_storage import GateOutcome

# Locked label-to-prose mapping. Kept in sync with the six locked
# Dutch labels from Task 130 product lock §4 minus 'Geblokkeerd' which
# never reaches this template (composition skips that path).
_LABEL_PROSE = {
    "Kopen": "een koopkans",
    "Verminderen": "een aanleiding om de positie te verminderen",
    "Verkopen": "een aanleiding om de positie te verkopen",
    "Houden": "geen actie nodig",
    "Bekijken": "een signaal om te bekijken",
}

# Locked Dutch month names — avoid locale-dependent strftime which on
# CI containers can produce English names.
_DUTCH_MONTHS = {
    1: "januari",
    2: "februari",
    3: "maart",
    4: "april",
    5: "mei",
    6: "juni",
    7: "juli",
    8: "augustus",
    9: "september",
    10: "oktober",
    11: "november",
    12: "december",
}


def _fmt_date_nl(dt: datetime) -> str:
    return f"{dt.day} {_DUTCH_MONTHS[dt.month]} {dt.year}"


def _fmt_pct(value: Decimal, decimals: int = 0) -> str:
    """Format a 0..1 probability as a Dutch percentage string."""

    pct = value * Decimal("100")
    fmt = f"{{:.{decimals}f}}".format(float(pct))
    return f"{fmt.replace('.', ',')}%"


def _fmt_eur(value: Decimal) -> str:
    """Format a Decimal as Dutch EUR (€640,12 with comma decimal)."""

    rounded = value.quantize(Decimal("0.01"))
    text = f"{rounded:f}".replace(".", ",")
    return f"€{text}"


def render_explanation(
    *,
    symbol: str,
    label: str,
    horizon_trading_days: int,
    p10_price_eur: Decimal,
    p50_price_eur: Decimal,
    p90_price_eur: Decimal,
    prob_positive: Decimal,
    prob_loss_gt_5pct: Decimal,
    expected_volatility_annualized: Decimal,
    confidence_level: str,
    valid_until: datetime,
    gate_outcomes: Iterable[GateOutcome],
) -> str:
    """Render the deterministic Dutch explanation paragraph.

    Raises ``ValueError`` if ``label`` is not in the locked
    Decision-Package label set (Geblokkeerd belongs to the forecast
    row, not the package).
    """

    if label not in _LABEL_PROSE:
        raise ValueError(
            f"label {label!r} not in {sorted(_LABEL_PROSE)} "
            "(Geblokkeerd forecasts get no Decision Package)"
        )

    opening = (
        f"Voor {symbol} duidt de voorspelling op {_LABEL_PROSE[label]} "
        f"(label: {label}) over de komende {horizon_trading_days} "
        "handelsdagen."
    )
    quantile_sentence = (
        f"Verwachte bandbreedte in EUR: {_fmt_eur(p10_price_eur)} "
        f"(p10) — {_fmt_eur(p50_price_eur)} (mediaan) — "
        f"{_fmt_eur(p90_price_eur)} (p90)."
    )
    probability_sentence = (
        f"Kans op stijging: {_fmt_pct(prob_positive)}; "
        f"kans op verlies van meer dan 5%: {_fmt_pct(prob_loss_gt_5pct)}."
    )
    risk_sentence = (
        f"Verwachte jaarlijkse volatiliteit: "
        f"{_fmt_pct(expected_volatility_annualized * Decimal('1'), decimals=1)}."
    )
    confidence_sentence = f"Betrouwbaarheid: {confidence_level}."
    validity_sentence = (
        f"Deze Decision Package is geldig tot {_fmt_date_nl(valid_until)}."
    )

    paragraph_parts = [
        opening,
        quantile_sentence,
        probability_sentence,
        risk_sentence,
        confidence_sentence,
        validity_sentence,
    ]
    # One "Let op:" sentence per failed gate. Order matches the input
    # ``gate_outcomes`` order — composer is responsible for evaluating
    # gates in the locked sequence.
    for gate in gate_outcomes:
        if not gate.passed:
            paragraph_parts.append(f"Let op: {gate.reason_nl}")
    return " ".join(paragraph_parts)


__all__ = ["render_explanation"]
