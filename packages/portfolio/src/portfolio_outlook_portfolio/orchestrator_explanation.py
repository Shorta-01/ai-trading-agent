"""Dutch-language explanation for orchestrator decisions (V1.2 §T).

The orchestrator returns a verdict + a stack of gate diagnostics.
For the operator UI to be useful the verdict has to become a
single, plain-language sentence the user can read while scanning a
list of candidates ("Verkopen op €104,73, koop 249 stuks Apple voor
€25 000 — kans 78 %, vertrouwen 85 %").

This module is the pure translator: ``OrchestratorResult ->
Dutch text``. Two outputs per result:

* **summary_nl** — one-liner suitable for a suggestion grid row.
* **detail_nl** — multi-line breakdown for the explanation panel.

No I/O, no datetime, no LLM. The strings are deterministic given
the same dataclass values; copy is locked so e-mail digests and
the operator UI never drift.

Style choices:

* Dutch first, no English filler ("forecast" → "voorspelling").
* Euro amounts use the Belgian convention (``€100.000`` with a
  thousands period, no decimal places by default).
* Percentages use the convention ``+4,73 %`` (comma decimal, space
  before the unit) — matches the rest of the operator UI.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from portfolio_outlook_portfolio.profit_harvest_orchestrator import (
    DECISION_SKIP_CONFIDENCE,
    DECISION_SKIP_EARNINGS,
    DECISION_SKIP_MACRO,
    DECISION_SKIP_PAIR_BUILD,
    DECISION_SKIP_RISK_UNIVERSE,
    DECISION_SKIP_SECTOR,
    DECISION_SKIP_SIZING,
    DECISION_SUGGEST,
    OrchestratorResult,
)


def _fmt_eur(value: Decimal) -> str:
    """Render an EUR amount as ``€100.000`` (thousands period)."""

    integer = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    # Belgian convention: thousands separated by dot, no decimal.
    s = f"{int(integer):,}".replace(",", ".")
    return f"€{s}"


def _fmt_pct(value: Decimal, *, sign: bool = False) -> str:
    """Render ``Decimal('4.73')`` as ``+4,73 %`` (Belgian convention)."""

    quantised = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    body = f"{quantised}".replace(".", ",")
    if sign and quantised > 0:
        body = f"+{body}"
    return f"{body} %"


def _fmt_price(value: Decimal) -> str:
    """Render a share price as ``€104,73``."""

    quantised = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return "€" + f"{quantised}".replace(".", ",")


# Locked one-line summaries per blocking reason. Keep these
# operator-friendly, not predictor jargon.
_MACRO_REASON_TEXT: dict[str, str] = {
    "macro_vix_too_high": "Marktklimaat: VIX te hoog — geen nieuwe BUYs.",
    "macro_index_in_bear_trend": (
        "Marktklimaat: index in bear-trend (50d < 200d) — geen nieuwe BUYs."
    ),
    "macro_insufficient_history": (
        "Marktklimaat: te weinig data om het regime te beoordelen."
    ),
}

_RISK_REASON_TEXT: dict[str, str] = {
    "leveraged_or_inverse_etf": (
        "Risico-filter: leveraged / inverse ETF — uitgesloten voor 3-6 maand horizon."
    ),
    "unknown_market_cap": "Risico-filter: marktkapitalisatie onbekend.",
    "below_min_market_cap": (
        "Risico-filter: onder minimum marktkapitalisatie."
    ),
    "insufficient_bars_for_volatility": (
        "Risico-filter: te weinig historische data voor volatiliteit."
    ),
    "above_max_volatility": (
        "Risico-filter: jaarvolatiliteit boven plafond."
    ),
}

_EARNINGS_REASON_TEXT: dict[str, str] = {
    "earnings_within_block_window": (
        "Earnings binnen blokkering-venster — geen BUY tot na publicatie."
    ),
}

_CONFIDENCE_REASON_TEXT: dict[str, str] = {
    "below_confidence_threshold": (
        "Kans op winstdoel onder drempel — niet voorgesteld."
    ),
    "invalid_forecast_inputs": "Voorspel-invoer ongeldig.",
    "zero_volatility": "Vlakke koershistorie — winstdoel onbereikbaar.",
}

_SECTOR_REASON_TEXT: dict[str, str] = {
    "sector_concentration_exceeded": (
        "Sector-concentratie zou de cap overschrijden."
    ),
    "invalid_total_budget": "Trading-budget ongeldig.",
    "invalid_max_sector_pct": "Sector-cap instelling ongeldig.",
    "invalid_candidate_eur": "Voorgestelde positiegrootte ongeldig.",
}

_PAIR_REASON_TEXT: dict[str, str] = {
    "intended_position_below_one_share": (
        "Positiegrootte minder dan één aandeel — te klein voor execution."
    ),
    "invalid_entry_price": "Aankoopprijs ongeldig.",
    "invalid_position_eur": "Positie-EUR ongeldig.",
    "invalid_target_net_pct": "Netto winstdoel ongeldig.",
}


def explain_decision(result: OrchestratorResult) -> str:
    """Return a one-line Dutch summary of the orchestrator verdict.

    For a SUGGEST result the line is action-oriented ("Koop X stuks
    op €Y, verkoop bij €Z — kans N %"). For a skip the line names
    the gate and the blocking reason in operator-friendly terms.
    """

    if result.decision == DECISION_SUGGEST:
        pair = result.pair_build.pair if result.pair_build else None
        conf = result.confidence
        if pair is None or conf is None:
            return "Voorgesteld."
        return (
            f"Koop {pair.qty} stuks {pair.ticker} op "
            f"{_fmt_price(pair.entry_lmt_price)} — verkoop bij "
            f"{_fmt_price(pair.take_profit_sell_price)} (+{pair.required_gross_pct}% "
            f"bruto, +{pair.target_net_pct}% netto) — kans "
            f"{_fmt_pct(conf.p_target_hit_pct)}."
        )

    reason = result.blocking_reason or ""
    if result.decision == DECISION_SKIP_MACRO:
        return _MACRO_REASON_TEXT.get(
            reason, "Marktklimaat blokkeert nieuwe BUYs."
        )
    if result.decision == DECISION_SKIP_RISK_UNIVERSE:
        return _RISK_REASON_TEXT.get(reason, "Risico-filter blokkeert.")
    if result.decision == DECISION_SKIP_EARNINGS:
        return _EARNINGS_REASON_TEXT.get(
            reason, "Earnings binnen blokkering-venster."
        )
    if result.decision == DECISION_SKIP_CONFIDENCE:
        return _CONFIDENCE_REASON_TEXT.get(
            reason, "Onvoldoende vertrouwen in winstdoel."
        )
    if result.decision == DECISION_SKIP_SIZING:
        return "Overtuiging onder drempel — positie te klein om voor te stellen."
    if result.decision == DECISION_SKIP_SECTOR:
        return _SECTOR_REASON_TEXT.get(reason, "Sector-concentratie probleem.")
    if result.decision == DECISION_SKIP_PAIR_BUILD:
        return _PAIR_REASON_TEXT.get(reason, "Order-pair kon niet gebouwd worden.")
    return f"Onbekende beslissing: {result.decision}"


def explain_decision_detail(result: OrchestratorResult) -> str:
    """Return a multi-line Dutch breakdown of every gate that ran.

    Useful for the suggestion detail page. Successful gates are
    rendered first (so the user can audit *why* a candidate passed
    or stopped where it did); the failing gate's reason appears
    last as the decisive line.
    """

    lines: list[str] = [f"Beslissing: {explain_decision(result)}"]

    if result.macro is not None:
        if result.macro.favorable:
            ma_short = result.macro.ma_short_day
            ma_long = result.macro.ma_long_day
            vix = result.macro.vix_level
            macro_bits: list[str] = []
            if vix is not None:
                macro_bits.append(f"VIX {vix}")
            if ma_short is not None and ma_long is not None:
                macro_bits.append(
                    f"50d {_fmt_price(ma_short)} > 200d {_fmt_price(ma_long)}"
                )
            macro_text = ", ".join(macro_bits) if macro_bits else "regime gunstig"
            lines.append(f"• Marktklimaat: gunstig ({macro_text}).")
        else:
            lines.append(f"• Marktklimaat: {explain_decision(result)}")

    if result.risk_universe is not None:
        rv = result.risk_universe
        if rv.allowed:
            bits: list[str] = []
            if rv.market_cap_eur is not None:
                bits.append(f"marktkap {_fmt_eur(rv.market_cap_eur)}")
            if rv.annualized_volatility_pct is not None:
                bits.append(f"jaarvol {rv.annualized_volatility_pct} %")
            lines.append(
                "• Risico-filter: oké ({}).".format(", ".join(bits) or "alle eisen")
            )

    if result.earnings is not None:
        if result.earnings.allowed:
            if result.earnings.days_to_earnings is not None:
                lines.append(
                    f"• Earnings: {result.earnings.days_to_earnings} dagen verwijderd."
                )
            else:
                lines.append("• Earnings: geen geplande publicatie bekend.")

    if result.confidence is not None and result.confidence.allowed:
        c = result.confidence
        lines.append(
            f"• Vertrouwen: {_fmt_pct(c.p_target_hit_pct)} kans op "
            f"{_fmt_price(c.target_price)} (+{c.required_gross_pct} % bruto)."
        )

    if result.news_sentiment is not None and result.news_sentiment.total_items > 0:
        lines.append(
            f"• Nieuwsstroom: {result.news_sentiment.bullish_count} "
            f"van {result.news_sentiment.total_items} berichten bullish "
            f"(boost {_fmt_pct(result.news_sentiment.buy_bias * Decimal('100'))})."
        )

    if result.sector_concentration is not None and result.sector_concentration.allowed:
        s = result.sector_concentration
        lines.append(
            f"• Sector ({s.candidate_sector}): {s.current_sector_pct} %"
            f" → {s.projected_sector_pct} % (cap {s.max_allowed_pct} %)."
        )

    if (
        result.proposed_position_eur is not None
        and result.proposed_position_eur > 0
    ):
        lines.append(
            f"• Voorgestelde positie: {_fmt_eur(result.proposed_position_eur)}."
        )

    if result.pair_build is not None and result.pair_build.pair is not None:
        pair = result.pair_build.pair
        lines.append(
            f"• Order: koop {pair.qty} stuks @ {_fmt_price(pair.entry_lmt_price)},"
            f" verkoop @ {_fmt_price(pair.take_profit_sell_price)}"
            f" (verwachte netto winst {_fmt_eur(pair.expected_net_profit_eur)})."
        )

    return "\n".join(lines)


__all__ = [
    "explain_decision",
    "explain_decision_detail",
]
