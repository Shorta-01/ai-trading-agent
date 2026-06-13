"""Hold-position review (V1.2 §AQ) — soft horizon + 6m combo-trigger.

Implements the operator-doctrine for managing an *already-held*
position, locked in `CLAUDE.md §6.2`:

* **Maand 0-6**: positie wordt vastgehouden ongeacht prijsverloop.
  Geen stop-loss. Geen geforceerde verkoop. De software monitort
  intraday tegen de +4% take-profit en toont een SELL-suggestie
  zodra die wordt geraakt (zie §AR).
* **Vanaf maand 6**: maandelijkse re-evaluatie met **combo-trigger**.
  *Beide* condities moeten waar zijn voor een SELL-suggestie:

  1. **Forecast-conditie**: de geüpdatete forecaster (baseline GBM +
     ensemble) zegt dat de mediaan-prijs (p50) over de volgende 3-6
     maanden geen ``target_net_pct`` upside meer geeft — concreet:
     ``forecast_p50 < entry_price * (1 + target_net_pct/100)``.
  2. **Verlies-conditie**: de positie staat ≥ ``loss_floor_pct`` onder
     instapprijs — default -5%.

* Als slechts één van de twee waar is: blijven houden. Een asset kan
  even -8% staan door market noise en dan terugveren; we willen niet
  voortijdig verkopen.
* Als beide waar zijn: SELL-suggestie kaartje op het dashboard met de
  Nederlandstalige reden — operator beslist of hij de verkoop
  doorvoert (CLAUDE.md §2 fundamenteel principe: software adviseert,
  operator beslist).

Dit module is **pure Python** — geen I/O, geen datetime.now(); de
caller geeft ``days_held`` mee zodat tests deterministisch blijven.

Het module is bewust gescheiden van de profit-harvest-orchestrator
omdat de orchestrator nieuwe BUY-kandidaten evalueert; deze module
evalueert bestaande HOLD-posities. Twee verschillende
verantwoordelijkheden.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

# Locked doctrine defaults — overrides komen later via runtime
# settings indien de operator dit wil bijstellen. Voor nu zijn het
# constants zodat de gedrags-onderbouwing in code expliciet is.
DEFAULT_HORIZON_REVIEW_START_DAYS: Final[int] = 180  # 6 months
DEFAULT_LOSS_FLOOR_PCT: Final[Decimal] = Decimal("-5")
DEFAULT_TARGET_NET_PCT: Final[Decimal] = Decimal("4")

# Locked action-codes — surface op het audit-rij + UI. Synchroon
# gehouden met de Dutch labels in ``hold_position_review_nl.py``
# (todo, follow-up §AR voor de UI-laag).
HOLD_ACTION_HOLD: Final[str] = "hold"
HOLD_ACTION_SUGGEST_SELL: Final[str] = "suggest_sell"


@dataclass(frozen=True)
class HoldPositionReviewInputs:
    """Alles wat één evaluatie nodig heeft.

    De caller is verantwoordelijk om deze inputs samen te stellen uit
    de laatste forecast-rij voor het symbool, de IBKR-positie-row, en
    de doctrine-defaults.

    ``days_held`` wordt door de caller berekend (bijvoorbeeld
    ``(today - entry_date).days``) — de module zelf raakt geen
    datetime aan om tests deterministisch te houden.
    """

    ticker: str
    entry_price: Decimal
    current_price: Decimal
    days_held: int
    # Geüpdatete forecast voor 3-6m horizon.
    forecast_p50: Decimal
    target_net_pct: Decimal = DEFAULT_TARGET_NET_PCT
    horizon_review_start_days: int = DEFAULT_HORIZON_REVIEW_START_DAYS
    loss_floor_pct: Decimal = DEFAULT_LOSS_FLOOR_PCT


@dataclass(frozen=True)
class HoldPositionReviewResult:
    """Uitkomst van één review.

    ``action`` is ofwel ``"hold"`` ofwel ``"suggest_sell"`` — beide
    gedragen zich passief; de orchestrator van de software stuurt
    geen order zonder operator-klik (CLAUDE.md §2).

    De diagnostiek-velden (``forecaster_above_target``,
    ``position_in_loss``, ``current_pct_return``) blijven altijd
    populated zodat het dashboard de evaluatie volledig kan tonen,
    ook wanneer de actie ``hold`` is.
    """

    action: str
    days_held: int
    current_pct_return: Decimal
    forecaster_above_target: bool
    position_in_loss: bool
    blocking_reason_nl: str


def evaluate_hold_position_review(
    inputs: HoldPositionReviewInputs,
) -> HoldPositionReviewResult:
    """V1.2 §AQ — combo-trigger review van een bestaande positie.

    Doctrine-flow:

    1. **Validation** — entry/current prijs moeten positief zijn,
       ``days_held`` moet ≥ 0 zijn.
    2. **Tijdens hold-venster (0 t/m ``horizon_review_start_days``)**:
       ``action = "hold"``. Geen evaluatie van forecast of verlies —
       de doctrine zegt expliciet ongeacht prijsverloop houden.
    3. **Na hold-venster**: evalueer beide condities.

       * ``forecaster_above_target`` = ``forecast_p50 ≥ entry × (1 + target/100)``
       * ``position_in_loss`` = ``current_pct_return ≤ loss_floor_pct``

       Beide condities ``True`` → behoud upside-overtuiging → ``hold``.
       Eén waar, één niet → behoud (één signaal alleen is niet
       voldoende; markt-ruis kan een tijdelijke dip veroorzaken).
       Beide ``False`` (geen upside meer EN positie in verlies) →
       ``suggest_sell``.

    Het is bewust een asymmetrische combo-trigger: we kantelen
    *uit* een positie alleen als beide doctrine-signalen waar zijn.
    """

    if inputs.entry_price <= 0:
        raise ValueError("entry_price must be > 0")
    if inputs.current_price <= 0:
        raise ValueError("current_price must be > 0")
    if inputs.days_held < 0:
        raise ValueError("days_held must be ≥ 0")
    if inputs.target_net_pct < 0:
        raise ValueError("target_net_pct must be ≥ 0")

    current_pct_return = (
        (inputs.current_price - inputs.entry_price)
        / inputs.entry_price
        * Decimal("100")
    )

    # Diagnostics worden altijd berekend zodat het dashboard ze kan
    # tonen, ook in de hold-fase.
    target_price = inputs.entry_price * (
        Decimal("1") + inputs.target_net_pct / Decimal("100")
    )
    forecaster_above_target = inputs.forecast_p50 >= target_price
    position_in_loss = current_pct_return <= inputs.loss_floor_pct

    # Doctrine-conditie 1: binnen 0-6m hold-venster → altijd hold.
    if inputs.days_held < inputs.horizon_review_start_days:
        return HoldPositionReviewResult(
            action=HOLD_ACTION_HOLD,
            days_held=inputs.days_held,
            current_pct_return=current_pct_return,
            forecaster_above_target=forecaster_above_target,
            position_in_loss=position_in_loss,
            blocking_reason_nl=(
                f"Binnen 6-maanden hold-venster ({inputs.days_held} dagen "
                f"gehouden, drempel {inputs.horizon_review_start_days}). "
                "Wachten op +4% take-profit; geen geforceerde verkoop."
            ),
        )

    # Doctrine-conditie 2: na 6 maanden, combo-trigger.
    # Beide condities moeten waar zijn voor SELL-suggestie. Asymmetrisch
    # bewust — één signaal alleen kan markt-ruis zijn.
    if not forecaster_above_target and position_in_loss:
        return HoldPositionReviewResult(
            action=HOLD_ACTION_SUGGEST_SELL,
            days_held=inputs.days_held,
            current_pct_return=current_pct_return,
            forecaster_above_target=False,
            position_in_loss=True,
            blocking_reason_nl=(
                f"Outlook verslechterd na 6+ maanden: forecast p50 zegt geen "
                f"+{inputs.target_net_pct}% upside meer EN positie staat op "
                f"{current_pct_return.quantize(Decimal('0.01'))}% "
                f"(onder {inputs.loss_floor_pct}%). Overweeg te verkopen."
            ),
        )

    # Eén-van-twee of geen van beide → hold.
    if not forecaster_above_target:
        # Forecast verzwakt maar positie nog niet in verlies — wachten.
        reason = (
            "Forecast verzwakt, maar positie staat nog niet "
            f"{inputs.loss_floor_pct}% onder instap "
            f"({current_pct_return.quantize(Decimal('0.01'))}%). "
            "Geduldig wachten; één signaal is niet voldoende."
        )
    elif position_in_loss:
        # Positie in verlies maar forecast zegt nog upside — wachten.
        reason = (
            f"Positie staat op {current_pct_return.quantize(Decimal('0.01'))}% "
            f"(onder {inputs.loss_floor_pct}%), maar forecast p50 zegt nog "
            f"+{inputs.target_net_pct}% upside boven instap. Wachten op "
            "herstel."
        )
    else:
        # Beide signalen positief — gewoon doorlopen.
        reason = (
            f"Outlook nog positief en positie staat "
            f"{current_pct_return.quantize(Decimal('0.01'))}% boven instap. "
            "Blijven houden."
        )

    return HoldPositionReviewResult(
        action=HOLD_ACTION_HOLD,
        days_held=inputs.days_held,
        current_pct_return=current_pct_return,
        forecaster_above_target=forecaster_above_target,
        position_in_loss=position_in_loss,
        blocking_reason_nl=reason,
    )


__all__ = [
    "DEFAULT_HORIZON_REVIEW_START_DAYS",
    "DEFAULT_LOSS_FLOOR_PCT",
    "DEFAULT_TARGET_NET_PCT",
    "HOLD_ACTION_HOLD",
    "HOLD_ACTION_SUGGEST_SELL",
    "HoldPositionReviewInputs",
    "HoldPositionReviewResult",
    "evaluate_hold_position_review",
]
