"""Fractional Kelly + risk-parity sizing (Slice 19).

Locked in `version-1-product-experience-locks.md §21.5`: V1 sizes BUY
orders with **fractional Kelly** (default ½ Kelly) over the ensemble's
distribution, scaled by **risk-parity caps** so no single position can
dominate the portfolio.

## The Kelly formula

For an asymmetric bet (upside ≠ downside) the classical Kelly fraction
is::

    f* = (p × b − q × L) / (b × L)

where:

* ``p`` = prob_gain (∈ [0, 1])
* ``q`` = prob_loss = 1 − p
* ``b`` = expected upside (positive expected return per unit, decimal)
* ``L`` = expected downside (positive magnitude of the loss, decimal)

We clip the output to ``[0, 1]`` and multiply by ``kelly_fraction``
(half-Kelly by default). Any negative-EV bet collapses to 0 — Kelly's
estimation risk is real, and we prefer "do nothing" over "bet the farm
on a noisy edge".

## Risk-parity caps

After Kelly we apply two hard caps:

* ``per_asset_cap_pct`` — no single asset > X% of portfolio (default
  5%).
* ``per_sector_cap_pct`` — no sector > Y% of portfolio (default 30%),
  accounting for the asset's existing sector exposure plus the new
  Kelly recommendation.

The caps are deterministic clips — they never raise the Kelly
fraction, only ever reduce it. Cap-hit flags are surfaced so the
Decision Package can show the user *why* the size shrank.

This module is pure Python: floats internally, Decimal on the
boundary, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Final

DEFAULT_KELLY_FRACTION: Final[float] = 0.5
DEFAULT_PER_ASSET_CAP_PCT: Final[float] = 5.0
DEFAULT_PER_SECTOR_CAP_PCT: Final[float] = 30.0


@dataclass(frozen=True)
class KellyInputs:
    """Inputs to the Kelly recommender for one asset."""

    prob_gain: Decimal
    expected_return_pct: Decimal
    downside_loss_pct: Decimal
    kelly_fraction: float = DEFAULT_KELLY_FRACTION


@dataclass(frozen=True)
class KellyResult:
    """Result of fractional Kelly + risk-parity capping for one asset."""

    fraction: Decimal  # final fraction of portfolio to allocate, ∈ [0, 1]
    fraction_raw_kelly: Decimal  # raw fractional Kelly before caps
    per_asset_cap_hit: bool
    per_sector_cap_hit: bool
    explanation_nl: str


def _bounded(value: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _decimal_pct(value: float, places: int = 6) -> Decimal:
    quant = Decimal(10) ** -places
    return Decimal(str(value)).quantize(quant)


def compute_fractional_kelly_fraction(
    *,
    prob_gain: Decimal,
    expected_return_pct: Decimal,
    downside_loss_pct: Decimal,
    kelly_fraction: float = DEFAULT_KELLY_FRACTION,
) -> Decimal:
    """Return the half-Kelly fraction of portfolio to allocate to this
    asset.

    The result is clipped to ``[0, 1]``. Returns ``0`` when:

    * ``expected_return_pct ≤ 0`` (negative EV → don't bet)
    * ``downside_loss_pct ≤ 0`` (no downside means an infinite-edge
      bet which can't be sized via Kelly; we refuse to size)
    * ``prob_gain ≤ 0`` (no upside probability)
    * ``kelly_fraction ≤ 0`` (caller explicitly disabled Kelly)
    """

    if kelly_fraction <= 0:
        return Decimal("0.000000")
    if expected_return_pct <= 0:
        return Decimal("0.000000")
    if downside_loss_pct <= 0:
        return Decimal("0.000000")
    if prob_gain <= 0:
        return Decimal("0.000000")

    p = float(prob_gain)
    q = max(0.0, 1.0 - p)
    b = float(expected_return_pct) / 100.0
    L = float(downside_loss_pct) / 100.0
    numerator = p * b - q * L
    denominator = b * L
    if denominator <= 0 or numerator <= 0:
        return Decimal("0.000000")
    raw = numerator / denominator
    scaled = raw * kelly_fraction
    bounded = max(0.0, min(1.0, scaled))
    return _decimal_pct(bounded)


@dataclass(frozen=True)
class RiskParityInputs:
    """Inputs to the risk-parity cap step."""

    fraction: Decimal  # Kelly-recommended fraction (∈ [0, 1])
    current_sector_exposure_pct: Decimal | None
    per_asset_cap_pct: float = DEFAULT_PER_ASSET_CAP_PCT
    per_sector_cap_pct: float = DEFAULT_PER_SECTOR_CAP_PCT


def apply_risk_parity_caps(
    *,
    fraction: Decimal,
    current_sector_exposure_pct: Decimal | None = None,
    per_asset_cap_pct: float = DEFAULT_PER_ASSET_CAP_PCT,
    per_sector_cap_pct: float = DEFAULT_PER_SECTOR_CAP_PCT,
) -> KellyResult:
    """Apply per-asset and per-sector caps to a Kelly fraction.

    ``current_sector_exposure_pct`` is the existing portfolio weight in
    this asset's sector (e.g. ``25.0`` for 25 %). The cap is then
    ``per_sector_cap_pct − current_sector_exposure_pct`` (clipped to 0).
    When the sector exposure is unknown the per-sector cap is not
    applied (the per-asset cap still is).
    """

    per_asset_cap_fraction = Decimal(str(per_asset_cap_pct / 100.0))
    raw_fraction = fraction
    per_asset_cap_hit = raw_fraction > per_asset_cap_fraction
    capped = raw_fraction
    if per_asset_cap_hit:
        capped = per_asset_cap_fraction

    per_sector_cap_hit = False
    if current_sector_exposure_pct is not None:
        per_sector_remaining_pct = max(
            0.0,
            per_sector_cap_pct - float(current_sector_exposure_pct),
        )
        per_sector_remaining_fraction = Decimal(str(per_sector_remaining_pct / 100.0))
        if capped > per_sector_remaining_fraction:
            capped = per_sector_remaining_fraction
            per_sector_cap_hit = True

    capped = _bounded(capped, Decimal("0"), Decimal("1"))

    if capped == 0 and raw_fraction > 0:
        explanation = (
            "Kelly-aanbeveling werd door risk-parity caps tot 0 teruggebracht; "
            "geen extra blootstelling toegestaan."
        )
    elif per_asset_cap_hit and per_sector_cap_hit:
        explanation = (
            f"Kelly-fractie {raw_fraction} ingeperkt door zowel per-asset "
            f"cap ({per_asset_cap_pct}%) als per-sector cap ({per_sector_cap_pct}%) "
            f"→ {capped}."
        )
    elif per_asset_cap_hit:
        explanation = (
            f"Kelly-fractie {raw_fraction} ingeperkt door per-asset cap "
            f"({per_asset_cap_pct}%) → {capped}."
        )
    elif per_sector_cap_hit:
        explanation = (
            f"Kelly-fractie {raw_fraction} ingeperkt door per-sector cap "
            f"({per_sector_cap_pct}%) → {capped}."
        )
    elif raw_fraction == 0:
        explanation = (
            "Kelly-fractie = 0 (negatieve EV of geen distributie-input); "
            "geen koopaanbeveling."
        )
    else:
        explanation = (
            f"Kelly-fractie {raw_fraction} blijft binnen de caps "
            f"(per-asset {per_asset_cap_pct}%, per-sector {per_sector_cap_pct}%)."
        )

    return KellyResult(
        fraction=capped,
        fraction_raw_kelly=raw_fraction,
        per_asset_cap_hit=per_asset_cap_hit,
        per_sector_cap_hit=per_sector_cap_hit,
        explanation_nl=explanation,
    )


def size_buy_with_kelly(
    *,
    inputs: KellyInputs,
    usable_cash: Decimal,
    market_price: Decimal,
    current_sector_exposure_pct: Decimal | None = None,
    per_asset_cap_pct: float = DEFAULT_PER_ASSET_CAP_PCT,
    per_sector_cap_pct: float = DEFAULT_PER_SECTOR_CAP_PCT,
) -> tuple[Decimal, KellyResult]:
    """End-to-end helper: Kelly fraction → cap → whole-share quantity.

    Returns ``(quantity, kelly_result)``. ``quantity`` is the floor of
    ``capped_fraction × usable_cash ÷ market_price``. ``usable_cash`` and
    ``market_price`` must be positive — the caller is responsible for
    upstream validation (the BUY-path orchestrator handles
    missing-cash / missing-price as separate dry-run failures).
    """

    raw = compute_fractional_kelly_fraction(
        prob_gain=inputs.prob_gain,
        expected_return_pct=inputs.expected_return_pct,
        downside_loss_pct=inputs.downside_loss_pct,
        kelly_fraction=inputs.kelly_fraction,
    )
    result = apply_risk_parity_caps(
        fraction=raw,
        current_sector_exposure_pct=current_sector_exposure_pct,
        per_asset_cap_pct=per_asset_cap_pct,
        per_sector_cap_pct=per_sector_cap_pct,
    )
    if result.fraction <= 0 or usable_cash <= 0 or market_price <= 0:
        return Decimal("0"), result
    capital = result.fraction * usable_cash
    raw_qty = capital / market_price
    whole_shares = raw_qty.to_integral_value(rounding=ROUND_DOWN)
    if whole_shares < 0:
        whole_shares = Decimal("0")
    return whole_shares, result


__all__ = [
    "DEFAULT_KELLY_FRACTION",
    "DEFAULT_PER_ASSET_CAP_PCT",
    "DEFAULT_PER_SECTOR_CAP_PCT",
    "KellyInputs",
    "KellyResult",
    "RiskParityInputs",
    "compute_fractional_kelly_fraction",
    "apply_risk_parity_caps",
    "size_buy_with_kelly",
]
