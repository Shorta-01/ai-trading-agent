"""Sector concentration limit (V1.2 §L).

The profit-harvest doctrine bets on diversification as the *real*
capital protection — there is no stop-loss, so a single sector
imploding while the user holds 8 names in it would do real damage
to the trading bucket regardless of how good each individual name
looked at entry.

This gate enforces ``trading_max_sector_pct`` — the user's
configured maximum share of the trading bucket in any one sector.
The check runs **before** position sizing so a candidate that
would push a sector over the cap is refused with a specific
blocking reason rather than silently shrunk.

Two design decisions baked in:

* **Cap is measured against total budget, not currently-deployed.**
  Otherwise the first position in any sector would always take 100 %
  of that sector's allocation. Anchoring to the configured
  ``trading_total_budget_eur`` keeps the math honest as cash flows
  in and out.
* **"unknown" is its own sector.** Candidates whose sector metadata
  is missing share a bucket called ``"unknown"`` — that way they
  still count toward concentration risk and never get a free pass.

This module is pure Python — Decimal-only on the boundary. The
suggestion pipeline calls it once per candidate after the
risk-universe and confidence gates have already accepted the name.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

# Locked blocking reason codes — stable across versions.
BLOCKING_REASON_SECTOR_CONCENTRATION_EXCEEDED: Final[str] = (
    "sector_concentration_exceeded"
)
BLOCKING_REASON_INVALID_BUDGET: Final[str] = "invalid_total_budget"
BLOCKING_REASON_INVALID_MAX_PCT: Final[str] = "invalid_max_sector_pct"
BLOCKING_REASON_INVALID_CANDIDATE_EUR: Final[str] = "invalid_candidate_eur"

UNKNOWN_SECTOR: Final[str] = "unknown"
_PCT_QUANT: Final[Decimal] = Decimal("0.01")


@dataclass(frozen=True)
class SectorAllocation:
    """Existing capital in a named sector.

    ``sector`` is the lower-cased sector code; ``current_eur`` is the
    total EUR allocated (sum of position outlays) in that sector. The
    caller is responsible for grouping their position table into this
    shape — we don't aggregate here.
    """

    sector: str
    current_eur: Decimal


@dataclass(frozen=True)
class SectorConcentrationResult:
    """Verdict + diagnostics from one concentration-gate pass.

    The percentages are populated on both allowed and blocked
    results so the UI can render the explanation ("Tech zou stijgen
    van 22 % naar 28 % — limiet 25 %").
    """

    allowed: bool
    blocking_reason: str | None
    candidate_sector: str
    current_sector_pct: Decimal
    projected_sector_pct: Decimal
    max_allowed_pct: Decimal


def _normalise_sector(sector: str | None) -> str:
    """Empty / None / whitespace → ``UNKNOWN_SECTOR``. Lower-case."""

    if sector is None:
        return UNKNOWN_SECTOR
    cleaned = sector.strip().lower()
    return cleaned if cleaned else UNKNOWN_SECTOR


def evaluate_sector_concentration(
    *,
    candidate_sector: str | None,
    candidate_intended_eur: Decimal,
    existing_allocations: Sequence[SectorAllocation],
    total_budget_eur: Decimal,
    max_sector_pct: Decimal,
) -> SectorConcentrationResult:
    """Check whether adding a candidate violates the sector cap.

    Args:
        candidate_sector: Sector code of the candidate. None or
            empty → bucketed under ``"unknown"``.
        candidate_intended_eur: EUR the suggestion would allocate
            to the candidate.
        existing_allocations: Current sector allocations in the
            trading bucket. Multiple entries for the same sector
            are summed; sectors not listed count as zero.
        total_budget_eur: ``trading_total_budget_eur`` from settings
            — the denominator.
        max_sector_pct: ``trading_max_sector_pct`` from settings —
            the cap (0–100).

    Returns:
        ``SectorConcentrationResult`` with ``allowed=True`` only when
        the *projected* sector pct stays at or below the cap.
    """

    if not isinstance(candidate_intended_eur, Decimal):
        raise TypeError("candidate_intended_eur must be a Decimal")
    if not isinstance(total_budget_eur, Decimal):
        raise TypeError("total_budget_eur must be a Decimal")
    if not isinstance(max_sector_pct, Decimal):
        raise TypeError("max_sector_pct must be a Decimal")

    sector_key = _normalise_sector(candidate_sector)

    # Aggregate the existing allocations into a {sector: EUR} map.
    by_sector: dict[str, Decimal] = {}
    for alloc in existing_allocations:
        key = _normalise_sector(alloc.sector)
        by_sector[key] = by_sector.get(key, Decimal("0")) + alloc.current_eur
    current_in_sector = by_sector.get(sector_key, Decimal("0"))

    # Input validation surfaced as blocking reasons (not exceptions)
    # so the caller can render a UI message instead of crashing.
    if total_budget_eur <= 0:
        return SectorConcentrationResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_INVALID_BUDGET,
            candidate_sector=sector_key,
            current_sector_pct=Decimal("0.00"),
            projected_sector_pct=Decimal("0.00"),
            max_allowed_pct=max_sector_pct,
        )
    if max_sector_pct < 0 or max_sector_pct > Decimal("100"):
        return SectorConcentrationResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_INVALID_MAX_PCT,
            candidate_sector=sector_key,
            current_sector_pct=Decimal("0.00"),
            projected_sector_pct=Decimal("0.00"),
            max_allowed_pct=max_sector_pct,
        )
    if candidate_intended_eur < 0:
        return SectorConcentrationResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_INVALID_CANDIDATE_EUR,
            candidate_sector=sector_key,
            current_sector_pct=Decimal("0.00"),
            projected_sector_pct=Decimal("0.00"),
            max_allowed_pct=max_sector_pct,
        )

    current_pct = (current_in_sector / total_budget_eur * Decimal("100")).quantize(
        _PCT_QUANT, rounding=ROUND_HALF_UP
    )
    projected_pct = (
        (current_in_sector + candidate_intended_eur)
        / total_budget_eur
        * Decimal("100")
    ).quantize(_PCT_QUANT, rounding=ROUND_HALF_UP)

    if projected_pct > max_sector_pct:
        return SectorConcentrationResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_SECTOR_CONCENTRATION_EXCEEDED,
            candidate_sector=sector_key,
            current_sector_pct=current_pct,
            projected_sector_pct=projected_pct,
            max_allowed_pct=max_sector_pct,
        )

    return SectorConcentrationResult(
        allowed=True,
        blocking_reason=None,
        candidate_sector=sector_key,
        current_sector_pct=current_pct,
        projected_sector_pct=projected_pct,
        max_allowed_pct=max_sector_pct,
    )


__all__ = [
    "BLOCKING_REASON_INVALID_BUDGET",
    "BLOCKING_REASON_INVALID_CANDIDATE_EUR",
    "BLOCKING_REASON_INVALID_MAX_PCT",
    "BLOCKING_REASON_SECTOR_CONCENTRATION_EXCEEDED",
    "SectorAllocation",
    "SectorConcentrationResult",
    "UNKNOWN_SECTOR",
    "evaluate_sector_concentration",
]
