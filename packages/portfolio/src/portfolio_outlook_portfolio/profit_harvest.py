"""Profit-harvest cycle math (V1.2 §F).

The retiree-income doctrine is "buy → wait until a configured *net*
profit target is hit → sell → recycle the cash into the next high-
confidence name". The strategy lives or dies on three things being
exactly right:

* The **gross** sell price must compensate for Belgian TOB on both
  legs (buy and sell). A 4% net target on a standard stock requires
  a ~4.73% gross price rise — set the take-profit LMT at the gross
  level, not the net level, otherwise every cycle silently leaks
  ~0.70% to taxes.
* The **position size** must scale with model confidence. Low
  conviction → small position; high conviction → large position. We
  use a straight linear map between configured min and max EUR, with
  the confidence threshold as the floor.
* The **sector concentration** cap must be enforced *before* sizing,
  not after, so the recommended size is always something the user
  can actually accept without violating diversification.

All math is Decimal-only and deterministic. No randomness, no I/O.
This module is the single place the rest of the codebase asks
"given X% net target and Y class, what gross % do I need?" — pricing
logic must not be re-derived in routes, workers, or UIs.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from portfolio_outlook_portfolio.belgian_tax import (
    TobSecurityClass,
    tob_rate_info,
)

# Quantisation grids for output. LMT prices commonly trade in 4
# decimal places on US/EU venues; positions in whole-euro amounts.
_PRICE_QUANT: Final[Decimal] = Decimal("0.0001")
_EUR_QUANT: Final[Decimal] = Decimal("1")
_PCT_QUANT: Final[Decimal] = Decimal("0.01")


def gross_pct_for_net_target_pct(
    *,
    target_net_pct: Decimal,
    security_class: TobSecurityClass,
) -> Decimal:
    """Return the gross price-rise % required to net ``target_net_pct``.

    Derivation. Let ``r`` = TOB rate for ``security_class``, ``p_buy``
    the entry share price, ``p_sell`` the exit share price, and ``Q``
    the share count.

    * Cash outlay at entry = ``p_buy × Q × (1 + r)``.
    * Net cash received at exit = ``p_sell × Q × (1 - r)``.
    * Net return on outlay = ``(p_sell × (1 - r) − p_buy × (1 + r)) /
      (p_buy × (1 + r))``.

    Setting net return to the target and solving for ``p_sell / p_buy``:

        p_sell / p_buy = (1 + target) × (1 + r) / (1 - r)

    The gross-rise % is ``(p_sell / p_buy − 1) × 100``.

    The TOB *cap* is ignored deliberately. The per-transaction caps
    (€1 600 standard, €4 000 accumulating) only bind above ~€457k
    (standard) and ~€303k (accumulating) gross transaction value —
    both well above the locked single-position ceiling, so the linear
    rate is the correct one for every realistic ``target_net_pct``.

    Args:
        target_net_pct: Desired net return as a percentage (e.g.
            ``Decimal("4")`` for 4%). Must be ≥ 0.
        security_class: TOB security class — drives the rate.

    Returns:
        Gross price-rise percentage, rounded HALF_UP to 2 dp.
    """

    if not isinstance(target_net_pct, Decimal):
        raise TypeError("target_net_pct must be a Decimal")
    if target_net_pct < 0:
        raise ValueError("target_net_pct must be ≥ 0")
    rate = tob_rate_info(security_class).rate
    target_frac = target_net_pct / Decimal("100")
    multiplier = (Decimal("1") + target_frac) * (Decimal("1") + rate) / (
        Decimal("1") - rate
    )
    gross_pct = (multiplier - Decimal("1")) * Decimal("100")
    return gross_pct.quantize(_PCT_QUANT, rounding=ROUND_HALF_UP)


def compute_take_profit_sell_price(
    *,
    entry_price: Decimal,
    target_net_pct: Decimal,
    security_class: TobSecurityClass,
) -> Decimal:
    """Compute the take-profit LMT price for a given entry + net target.

    Wraps :func:`gross_pct_for_net_target_pct` and applies it to the
    entry price. Result is rounded HALF_UP to 4 decimal places to fit
    standard LMT tick sizes.

    Args:
        entry_price: Cash share price at entry (NOT including TOB).
        target_net_pct: Desired net return as %.
        security_class: TOB security class.
    """

    if not isinstance(entry_price, Decimal):
        raise TypeError("entry_price must be a Decimal")
    if entry_price <= 0:
        raise ValueError("entry_price must be > 0")
    gross_pct = gross_pct_for_net_target_pct(
        target_net_pct=target_net_pct,
        security_class=security_class,
    )
    multiplier = Decimal("1") + gross_pct / Decimal("100")
    return (entry_price * multiplier).quantize(_PRICE_QUANT, rounding=ROUND_HALF_UP)


def conviction_weighted_position_size_eur(
    *,
    confidence_pct: Decimal,
    confidence_floor_pct: Decimal,
    min_position_eur: Decimal,
    max_position_eur: Decimal,
) -> Decimal:
    """V1.2 §AO — stepped confidence-tier position sizing.

    Maps a confidence reading to an EUR position size using the
    operator-doctrine tiers locked in `CLAUDE.md §3`:

    * ≥90% confidence (zeer zeker) → ``max_position_eur`` (100% of
      cap, typically 50% of trading portfolio = €25k on €50k)
    * 80-90% (zeker) → 60% of cap (typically 30% of portfolio = €15k
      on €50k)
    * 70-80% (redelijk) → 30% of cap (typically 15% of portfolio =
      €7.5k on €50k)
    * <``confidence_floor_pct`` → ``Decimal("0")`` (skip, do not
      propose the trade at all)

    The tiers are RELATIVE to ``max_position_eur`` so the caller can
    set a portfolio-size-aware cap (typically ``portfolio_eur ×
    0.50``) without the function needing to know the portfolio size
    directly.

    The result is floored at ``min_position_eur`` for non-zero
    tiers: TOB (0.70% round-trip) makes positions below ~€5k
    inefficient. If the computed tier-size falls below the floor,
    the floor is returned — unless the floor itself exceeds
    ``max_position_eur``, in which case the trade is skipped to
    prevent breaching the cap.

    The doctrine intentionally moved from a linear ramp to discrete
    tiers so the operator sees clearly "this is a 30% portfolio
    position because the model is in the 80-90% confidence band"
    rather than a continuous slider. This makes confidence-cohorts
    easier to compare across trades.

    Args:
        confidence_pct: Model's P(target hit within horizon), as a
            percentage (0–100).
        confidence_floor_pct: Minimum confidence to propose the trade
            (also a percentage, 0–100). Comes from user settings.
            Doctrine default: 70.
        min_position_eur: EUR floor for an accepted trade. Doctrine
            default: 5000.
        max_position_eur: EUR ceiling at the highest tier. Caller
            sets this to ``portfolio_eur × max_position_pct``
            (doctrine: 50%).

    Returns:
        Recommended position size in whole EUR (rounded HALF_UP).
        Zero if ``confidence_pct < confidence_floor_pct`` or if the
        minimum exceeds the maximum (a misconfigured cap).
    """

    for name, value in (
        ("confidence_pct", confidence_pct),
        ("confidence_floor_pct", confidence_floor_pct),
        ("min_position_eur", min_position_eur),
        ("max_position_eur", max_position_eur),
    ):
        if not isinstance(value, Decimal):
            raise TypeError(f"{name} must be a Decimal")
    if min_position_eur <= 0 or max_position_eur <= 0:
        raise ValueError("Position bounds must be > 0")
    if max_position_eur < min_position_eur:
        raise ValueError("max_position_eur must be ≥ min_position_eur")
    if confidence_floor_pct < 0 or confidence_floor_pct > Decimal("100"):
        raise ValueError("confidence_floor_pct must be 0–100")
    if confidence_pct < 0 or confidence_pct > Decimal("100"):
        raise ValueError("confidence_pct must be 0–100")

    if confidence_pct < confidence_floor_pct:
        return Decimal("0")

    # Stepped tiers — RELATIVE to max_position_eur so the function
    # is portfolio-size agnostic. The multipliers (1.0 / 0.6 / 0.3)
    # map to 50% / 30% / 15% of trading-portfolio when the caller
    # passes max = portfolio × 0.50.
    if confidence_pct >= Decimal("90"):
        tier_multiplier = Decimal("1.0")
    elif confidence_pct >= Decimal("80"):
        tier_multiplier = Decimal("0.6")
    else:
        # 70-80% band (or whatever the operator's floor is, down to
        # 70% — the doctrine floor).
        tier_multiplier = Decimal("0.3")

    size = max_position_eur * tier_multiplier
    # TOB-efficiency floor: never propose a position below the
    # minimum unless the minimum itself exceeds the cap (which
    # means the caller's cap is too tight — skip rather than
    # violate the cap).
    if size < min_position_eur:
        size = min_position_eur

    return size.quantize(_EUR_QUANT, rounding=ROUND_HALF_UP)


__all__ = [
    "compute_take_profit_sell_price",
    "conviction_weighted_position_size_eur",
    "gross_pct_for_net_target_pct",
]
