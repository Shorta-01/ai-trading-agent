"""Take-profit signal monitor (V1.2 §AR).

Implementeert de SELL-suggestie kant van CLAUDE.md §2 + §6.3: de
software stuurt NOOIT een automatische take-profit LMT mee naar
IBKR. In plaats daarvan monitort de software intraday elke held
positie tegen de +4% target en genereert een SELL-suggestie
kaartje wanneer de positie het target raakt.

De operator beslist altijd zelf of hij wil verkopen. Het kaartje
toont:

* "VERKOOP — AAPL staat op +4,X%, neem je winst" (primair advies)
* Forecast-context voor komende 1-3 dagen: p50 en kans op verdere
  stijging — zodat de operator kan kiezen om langer te wachten als
  de forecaster nog upside ziet
* EUR-equivalent van het potentiële verkoop-resultaat
* Knoppen: "Verkopen nu" of "Houden, ik wacht op verder rijzen"

Deze module is **pure Python** — geen I/O, geen datetime.now();
de caller geeft de huidige prijs + forecast-info mee zodat tests
deterministisch blijven en zodat de monitor zowel offline
(replay) als online (live) kan draaien.

CLAUDE.md §2 fundamenteel principe: deze module produceert
alleen een advies-dataclass. Geen automatische orders, geen
auto-execute. De UI-laag (§AT kaartjes) consumeert dit signaal
en toont het op het dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

# Locked default — operator-doctrine in CLAUDE.md §6.1.
DEFAULT_TAKE_PROFIT_NET_PCT: Final[Decimal] = Decimal("4")

# Locked actie-codes. Synchroon gehouden met de Dutch labels die het
# dashboard rendert voor de SELL-suggestie kaartjes.
SIGNAL_HOLD: Final[str] = "hold"
SIGNAL_SUGGEST_SELL: Final[str] = "suggest_sell"


@dataclass(frozen=True)
class TakeProfitForecastContext:
    """Forecast-context voor het komende korte venster (3 dagen).

    Apart van de 3-6 maanden forecaster die voor BUY-suggesties
    wordt gebruikt: dit is de korte-termijn forecaster die de
    operator helpt beslissen om al-of-niet te wachten op verder
    rijzen.

    Wanneer de korte-termijn forecast niet beschikbaar is (b.v.
    de positie zit in een illiquide name), kunnen velden ``None``
    zijn. De UI toont dan een neutraal "geen korte-termijn
    voorspelling beschikbaar" bericht — geen verzonnen getallen.
    """

    horizon_days: int
    p50_next: Decimal | None
    p_above_current_pct: Decimal | None


@dataclass(frozen=True)
class TakeProfitSignalInputs:
    """Alles wat één evaluatie nodig heeft.

    De caller berekent het al-uitgevoerde positie-resultaat
    (entry × qty, current × qty) en levert de forecast-context
    voor de korte termijn. De module weet geen broker-syntax,
    geen IBKR-types — pure Decimal-math.
    """

    ticker: str
    entry_price: Decimal
    current_price: Decimal
    quantity: int
    target_net_pct: Decimal = DEFAULT_TAKE_PROFIT_NET_PCT
    # Eur-equivalent van het verkoop-resultaat na FX en TOB. Caller
    # berekent dit met de huidige wisselkoers en TOB-rates (zie
    # belgian_tax). None = niet berekenbaar (FX-koers stale).
    expected_net_proceeds_eur: Decimal | None = None
    # Korte-termijn forecast voor de "houden of nu verkopen" beslissing.
    short_term_forecast: TakeProfitForecastContext | None = None


@dataclass(frozen=True)
class TakeProfitSignalResult:
    """Uitkomst van één evaluatie.

    ``action`` is ofwel ``"hold"`` (target nog niet geraakt) ofwel
    ``"suggest_sell"`` (target geraakt — dashboard kaartje tonen).

    Diagnostiek-velden blijven altijd populated zodat de UI een
    consistente regel kan tonen — ook in de hold-fase ziet de
    operator "AAPL staat op +2,1%, target +4% (€102,1 → €104)".
    """

    action: str
    ticker: str
    current_pct_return: Decimal
    target_pct: Decimal
    distance_to_target_pct: Decimal  # positive = nog niet bereikt
    target_reached: bool
    expected_net_proceeds_eur: Decimal | None
    short_term_forecast: TakeProfitForecastContext | None
    headline_nl: str  # primaire regel die de UI groot toont
    detail_nl: str    # uitleg + forecast-context voor het kaartje


def _quantise_pct(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _format_pct(value: Decimal) -> str:
    """Belgisch formaat: komma als decimaal scheidingsteken."""

    quantised = _quantise_pct(value)
    text = format(quantised, "f")
    return text.replace(".", ",")


def evaluate_take_profit_signal(
    inputs: TakeProfitSignalInputs,
) -> TakeProfitSignalResult:
    """V1.2 §AR — bepaal of een held positie nu een SELL-suggestie
    moet tonen.

    Regel: als ``current_price ≥ entry_price × (1 + target/100)``,
    dan ``action = "suggest_sell"`` — anders ``hold``.

    De target is een GROSS-niveau (de operator-doctrine meet +4% in
    lokale munt vóór TOB; de TOB-aftrek zit al in de
    take_profit_sell_price uit ``profit_harvest`` als de caller die
    wil gebruiken). Voor de operator-UX rapporteren we de bruto-
    return.
    """

    if not isinstance(inputs.entry_price, Decimal):
        raise TypeError("entry_price must be a Decimal")
    if not isinstance(inputs.current_price, Decimal):
        raise TypeError("current_price must be a Decimal")
    if inputs.entry_price <= 0:
        raise ValueError("entry_price must be > 0")
    if inputs.current_price <= 0:
        raise ValueError("current_price must be > 0")
    if inputs.quantity <= 0:
        raise ValueError("quantity must be > 0")
    if inputs.target_net_pct <= 0:
        raise ValueError("target_net_pct must be > 0")

    current_pct = (
        (inputs.current_price - inputs.entry_price)
        / inputs.entry_price
        * Decimal("100")
    )
    target_pct = inputs.target_net_pct
    distance = target_pct - current_pct
    target_reached = current_pct >= target_pct

    pct_str = _format_pct(current_pct)
    target_str = _format_pct(target_pct)

    if target_reached:
        action = SIGNAL_SUGGEST_SELL
        headline = (
            f"VERKOOP — {inputs.ticker} staat op +{pct_str}%, neem je winst"
        )
        if inputs.short_term_forecast is not None:
            ctx = inputs.short_term_forecast
            forecast_pieces: list[str] = []
            if ctx.p50_next is not None:
                forecast_pieces.append(
                    f"forecast komende {ctx.horizon_days} dagen p50 "
                    f"€{ctx.p50_next}"
                )
            if ctx.p_above_current_pct is not None:
                forecast_pieces.append(
                    f"kans op verdere stijging {_format_pct(ctx.p_above_current_pct)}%"
                )
            if forecast_pieces:
                forecast_text = "; ".join(forecast_pieces)
                detail = (
                    f"+{pct_str}% target geraakt. Korte-termijn "
                    f"context: {forecast_text}. Operator kiest: nu "
                    "verkopen of nog wachten op verder rijzen."
                )
            else:
                detail = (
                    f"+{pct_str}% target geraakt. Geen korte-termijn "
                    "forecast beschikbaar. Operator beslist."
                )
        else:
            detail = (
                f"+{pct_str}% target geraakt. Geen korte-termijn "
                "forecast beschikbaar. Operator beslist."
            )
    else:
        action = SIGNAL_HOLD
        headline = (
            f"{inputs.ticker} staat op {pct_str}%, target +{target_str}%"
        )
        distance_str = _format_pct(distance)
        detail = (
            f"Nog {distance_str}% te gaan tot +{target_str}% take-profit "
            f"target. Geen actie — wachten op +4%."
        )

    return TakeProfitSignalResult(
        action=action,
        ticker=inputs.ticker,
        current_pct_return=_quantise_pct(current_pct),
        target_pct=_quantise_pct(target_pct),
        distance_to_target_pct=_quantise_pct(distance),
        target_reached=target_reached,
        expected_net_proceeds_eur=inputs.expected_net_proceeds_eur,
        short_term_forecast=inputs.short_term_forecast,
        headline_nl=headline,
        detail_nl=detail,
    )


__all__ = [
    "DEFAULT_TAKE_PROFIT_NET_PCT",
    "SIGNAL_HOLD",
    "SIGNAL_SUGGEST_SELL",
    "TakeProfitForecastContext",
    "TakeProfitSignalInputs",
    "TakeProfitSignalResult",
    "evaluate_take_profit_signal",
]
