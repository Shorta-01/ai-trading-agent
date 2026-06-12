"""Earnings-calendar gate (V1.2 §R).

Quarterly earnings releases are binary events — a stock can gap
±20 % on the print depending on whether revenue / EPS / forward
guidance beat or missed. For the profit-harvest cycle that's the
opposite of what we want: we're betting on a +4 % drift inside
3-6 months, not on directional luck around a single overnight
event.

This gate refuses new BUY suggestions inside a configurable window
before earnings. The doctrine choice is locked at 5 trading days
because:

* Implied vol typically starts ramping ~5-7 days pre-print as
  hedgers and event-driven traders bid up options. The risk
  premium baked in by the market is the same signal we want to
  avoid eating ourselves.
* Analysts publish their last-minute revisions in this window;
  buying *during* the revision is effectively front-running our
  own analyst-revision predictor.
* Holding through earnings is fine when the position is *already
  open*. The gate is opening-only — held positions wait for either
  the take-profit LMT or a hard news exit, just as the doctrine
  says.

Two locked semantics:

* **Missing data is allowed.** When the provider has no upcoming-
  earnings date for a candidate (newly-listed names, ETFs,
  international issuers without coverage) we let the candidate
  through. Compare to the risk-universe gate where missing
  market-cap blocks — there the unknown is the *capital* risk;
  here it's just timing.
* **Earnings already past blocks nothing.** A date in the past
  means the next print is somewhere in the future the provider
  hasn't updated yet; treat as missing.

This module is pure Python — no I/O, no datetime.now(); the caller
hands in ``today`` so testing stays deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Final

# Locked blocking reason — surfaces on the suggestion audit row and
# in the operator UI ("Suggested: blocked — earnings binnen 3
# handelsdagen").
BLOCKING_REASON_EARNINGS_WINDOW: Final[str] = "earnings_within_block_window"

# Doctrine default. The user may override via
# `trading_earnings_block_days` in settings. Five trading days is
# the textbook pre-print exclusion window for quantitative funds
# that avoid event risk.
DEFAULT_EARNINGS_BLOCK_DAYS: Final[int] = 5


@dataclass(frozen=True)
class EarningsGateInputs:
    """Per-candidate inputs to the earnings calendar gate.

    ``next_earnings_date`` is the provider's best estimate of the
    next scheduled release. ``None`` means the provider has no
    upcoming date — gate allows by default (see module docstring).
    ``today`` is supplied by the caller so tests can run
    deterministically without monkey-patching datetime.
    """

    symbol: str
    today: date
    next_earnings_date: date | None


@dataclass(frozen=True)
class EarningsGateResult:
    """Verdict + diagnostics from one gate pass.

    ``days_to_earnings`` is reported on every result so the operator
    UI can display the time-to-print badge ("Earnings over 8 dagen"
    even on an allowed candidate; this lets the user mentally
    discount fresh BUYs that are a little risky despite passing).
    """

    allowed: bool
    blocking_reason: str | None
    days_to_earnings: int | None


def evaluate_earnings_calendar_gate(
    inputs: EarningsGateInputs,
    *,
    days_to_earnings_block: int = DEFAULT_EARNINGS_BLOCK_DAYS,
) -> EarningsGateResult:
    """Refuse new BUY suggestions in the pre-earnings window.

    Args:
        inputs: Symbol, today's date, and the next scheduled earnings
            date (or ``None`` when unknown).
        days_to_earnings_block: Block window in *calendar* days. Even
            though the doctrinal name is "trading days", the
            provider gives us calendar dates — using calendar days
            keeps the math direct and avoids a market-calendar
            dependency at the leaf.

    Returns:
        :class:`EarningsGateResult` with ``allowed=False`` when the
        earnings are within the block window, ``allowed=True``
        otherwise (including the missing-data case).
    """

    if days_to_earnings_block < 0:
        raise ValueError("days_to_earnings_block must be >= 0")

    if inputs.next_earnings_date is None:
        return EarningsGateResult(
            allowed=True,
            blocking_reason=None,
            days_to_earnings=None,
        )

    delta = (inputs.next_earnings_date - inputs.today).days
    if delta < 0:
        # Earnings already passed — provider hasn't published the
        # next scheduled date yet. Treat as missing.
        return EarningsGateResult(
            allowed=True,
            blocking_reason=None,
            days_to_earnings=delta,
        )
    if delta <= days_to_earnings_block:
        return EarningsGateResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_EARNINGS_WINDOW,
            days_to_earnings=delta,
        )
    return EarningsGateResult(
        allowed=True,
        blocking_reason=None,
        days_to_earnings=delta,
    )


__all__ = [
    "BLOCKING_REASON_EARNINGS_WINDOW",
    "DEFAULT_EARNINGS_BLOCK_DAYS",
    "EarningsGateInputs",
    "EarningsGateResult",
    "evaluate_earnings_calendar_gate",
]
