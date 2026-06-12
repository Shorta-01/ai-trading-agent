"""Take-profit order pair builder (V1.2 §J).

The profit-harvest cycle pairs every BUY with an automatic SELL LMT
priced at the gross level that nets the configured target_net_pct
after Belgian TOB on both legs. Without the pair, the cycle has no
exit mechanism — the user would have to watch the position and place
the sell order manually, which defeats the whole purpose.

This module is the *pure* builder: it converts an intent ("spend
€X on ticker Y at price Z, target +4 % net per cycle") into a fully-
specified order pair that downstream code (the order builder in
the worker, the IBKR submission client in the API) can wire up
without any further math.

The math layered on top of ``profit_harvest``:

* **Buy-side qty** = floor(intended_position_eur / (entry_lmt_price ×
  (1 + buy_tob_rate))). Floor so the actual cash outlay never
  exceeds the intended position size — under-fill is safe, over-fill
  is doctrine-breaking (we'd exceed ``trading_max_position_eur``).
* **Take-profit sell price** comes from
  ``profit_harvest.compute_take_profit_sell_price`` so the gross
  uplift accounting for Belgian TOB stays in one place.
* **Tier-aware refusal**: if even one whole share doesn't fit at the
  configured position cap, the builder refuses with a specific
  blocking reason rather than silently returning qty = 0.

This module is pure Python — Decimal-only on the boundary; no I/O,
no datetime, no IBKR types. The actual order-submission layer maps
the dataclass onto IBKR's Contract + Order.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Final

from portfolio_outlook_portfolio.belgian_tax import TobSecurityClass, tob_rate_info
from portfolio_outlook_portfolio.profit_harvest import (
    compute_take_profit_sell_price,
    gross_pct_for_net_target_pct,
)

# Locked blocking reason codes — go on the audit trail of an unfilled
# pair so the UI can explain why nothing was proposed.
BLOCKING_REASON_POSITION_TOO_SMALL: Final[str] = (
    "intended_position_below_one_share"
)
BLOCKING_REASON_INVALID_PRICE: Final[str] = "invalid_entry_price"
BLOCKING_REASON_INVALID_POSITION_EUR: Final[str] = "invalid_position_eur"
BLOCKING_REASON_INVALID_NET_TARGET: Final[str] = "invalid_target_net_pct"

# Locked TIFs. The entry LMT is a DAY order — it should fill today
# or be reconsidered tomorrow. The take-profit is GTC because the
# user has no stop-loss and the +4 % might land any time inside the
# 3-6 month horizon.
ENTRY_TIF: Final[str] = "DAY"
TAKE_PROFIT_TIF: Final[str] = "GTC"


@dataclass(frozen=True)
class TakeProfitOrderPair:
    """Specification for an entry-LMT + take-profit-SELL-LMT pair.

    Both legs are LMT orders. The entry is priced at the spot
    ``entry_lmt_price`` the caller supplied (usually the live bid /
    last); the take-profit is priced at the *gross* level needed to
    net ``target_net_pct`` after Belgian TOB on both transactions.

    The dataclass is intentionally provider-agnostic — no IBKR
    contract types here. The submission layer takes the strings,
    decimals, and ints and renders them into broker-specific
    payloads.
    """

    ticker: str
    qty: int
    entry_lmt_price: Decimal
    take_profit_sell_price: Decimal
    intended_position_eur: Decimal
    actual_outlay_eur: Decimal
    expected_net_profit_eur: Decimal
    target_net_pct: Decimal
    required_gross_pct: Decimal
    security_class: TobSecurityClass
    entry_tif: str = ENTRY_TIF
    take_profit_tif: str = TAKE_PROFIT_TIF


@dataclass(frozen=True)
class TakeProfitBuilderResult:
    """Verdict + (when allowed) the order pair."""

    allowed: bool
    blocking_reason: str | None
    pair: TakeProfitOrderPair | None


def _quantise_eur(value: Decimal) -> Decimal:
    """Round to whole euros (HALF_UP) for outlay/profit summaries."""

    return value.quantize(Decimal("1"), rounding=ROUND_DOWN)


def build_take_profit_pair(
    *,
    ticker: str,
    entry_lmt_price: Decimal,
    intended_position_eur: Decimal,
    target_net_pct: Decimal,
    security_class: TobSecurityClass,
) -> TakeProfitBuilderResult:
    """Build a take-profit order pair from intent.

    Pipeline:

    1. Validate inputs (Decimal types, positive prices and amounts,
       target in the doctrine-allowed range).
    2. Compute the maximum whole-share qty whose total outlay
       (price × qty × (1 + buy_tob_rate)) does not exceed
       ``intended_position_eur``. Floor — never over-spend.
    3. Compute the take-profit LMT price via the existing
       profit_harvest helper.
    4. Project the expected NET profit: the *difference* between
       net sell proceeds and entry outlay, both inclusive of TOB.

    Args:
        ticker: Symbol — written through to the order pair verbatim.
        entry_lmt_price: Cash share price the entry LMT will be
            placed at. Must be > 0.
        intended_position_eur: Maximum euro outlay the caller is
            willing to spend on this position (after TOB).
        target_net_pct: Desired net return per cycle, e.g. 4.
        security_class: Belgian TOB class — drives both the buy-side
            outlay calculation and the take-profit price.

    Returns:
        A :class:`TakeProfitBuilderResult` with ``allowed=True`` and
        a populated ``pair`` when everything fits, or ``allowed=False``
        with a locked blocking reason when it doesn't.
    """

    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("ticker must be a non-empty string")
    if not isinstance(entry_lmt_price, Decimal):
        raise TypeError("entry_lmt_price must be a Decimal")
    if not isinstance(intended_position_eur, Decimal):
        raise TypeError("intended_position_eur must be a Decimal")
    if not isinstance(target_net_pct, Decimal):
        raise TypeError("target_net_pct must be a Decimal")

    if entry_lmt_price <= 0:
        return TakeProfitBuilderResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_INVALID_PRICE,
            pair=None,
        )
    if intended_position_eur <= 0:
        return TakeProfitBuilderResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_INVALID_POSITION_EUR,
            pair=None,
        )
    if target_net_pct <= 0:
        # Below the TOB round-trip cost makes no sense. Defer to the
        # settings-level guard for the upper bound; here we just
        # refuse anything non-positive.
        return TakeProfitBuilderResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_INVALID_NET_TARGET,
            pair=None,
        )

    tob_rate = tob_rate_info(security_class).rate
    # Cost per share inclusive of buy-side TOB.
    cost_per_share = entry_lmt_price * (Decimal("1") + tob_rate)
    max_qty_decimal = intended_position_eur / cost_per_share
    qty = int(max_qty_decimal.to_integral_value(rounding=ROUND_DOWN))
    if qty < 1:
        return TakeProfitBuilderResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_POSITION_TOO_SMALL,
            pair=None,
        )

    take_profit_price = compute_take_profit_sell_price(
        entry_price=entry_lmt_price,
        target_net_pct=target_net_pct,
        security_class=security_class,
    )
    required_gross_pct = gross_pct_for_net_target_pct(
        target_net_pct=target_net_pct,
        security_class=security_class,
    )

    qty_decimal = Decimal(qty)
    actual_outlay_eur = entry_lmt_price * qty_decimal * (Decimal("1") + tob_rate)
    net_sell_proceeds = (
        take_profit_price * qty_decimal * (Decimal("1") - tob_rate)
    )
    expected_net_profit_eur = net_sell_proceeds - actual_outlay_eur

    pair = TakeProfitOrderPair(
        ticker=ticker.strip().upper(),
        qty=qty,
        entry_lmt_price=entry_lmt_price,
        take_profit_sell_price=take_profit_price,
        intended_position_eur=intended_position_eur,
        actual_outlay_eur=_quantise_eur(actual_outlay_eur),
        expected_net_profit_eur=_quantise_eur(expected_net_profit_eur),
        target_net_pct=target_net_pct,
        required_gross_pct=required_gross_pct,
        security_class=security_class,
    )
    return TakeProfitBuilderResult(
        allowed=True,
        blocking_reason=None,
        pair=pair,
    )


__all__ = [
    "BLOCKING_REASON_INVALID_NET_TARGET",
    "BLOCKING_REASON_INVALID_POSITION_EUR",
    "BLOCKING_REASON_INVALID_PRICE",
    "BLOCKING_REASON_POSITION_TOO_SMALL",
    "ENTRY_TIF",
    "TAKE_PROFIT_TIF",
    "TakeProfitBuilderResult",
    "TakeProfitOrderPair",
    "build_take_profit_pair",
]
