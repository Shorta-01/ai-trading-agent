"""Risk universe gate (V1.2 §G).

The retiree-income doctrine has one non-negotiable rule: *only surface
suggestions where the catastrophic-loss probability is low*. Two
practical filters do most of the work:

* Market-cap floor — a €5 B+ liquid name almost never goes to zero
  overnight. Penny stocks and micro-caps do. The user can adjust the
  threshold in Settings; the default 5 B catches everything below
  mid-cap.
* Annualised volatility ceiling — a 30 %-vol stock is "exciting"; a
  60 %-vol stock is a casino chip. The ceiling protects the no-stop-
  loss doctrine from runaway draws while the user waits for the +4 %
  target to hit.

A third hard rule is leveraged / inverse ETF exclusion. Those
products use daily-reset compounding that systematically decays —
holding one for 3-6 months is a near-guaranteed loss even when the
underlying drifts sideways. The detector is pragmatic: a curated set
of the most-traded US 2x/3x/inverse tickers plus a name-pattern
regex that catches ``"2x"``, ``"3x"``, ``"ultra"``, ``"leveraged"``
and ``"inverse"`` markers in any provider's product name.

This module is *pure*: no I/O, no network, no datetime.now(). It
takes precomputed inputs and returns a verdict. The suggestion
pipeline calls it once per candidate before any forecast math runs.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from portfolio_outlook_portfolio.baseline_forecast import HistoricalBar

# Locked blocking reason codes — these go on the audit trail and the
# operator UI, so they have to stay stable across versions.
BLOCKING_REASON_UNKNOWN_MARKET_CAP: Final[str] = "unknown_market_cap"
BLOCKING_REASON_BELOW_MIN_MARKET_CAP: Final[str] = "below_min_market_cap"
BLOCKING_REASON_ABOVE_MAX_VOLATILITY: Final[str] = "above_max_volatility"
BLOCKING_REASON_INSUFFICIENT_BARS: Final[str] = "insufficient_bars_for_volatility"
BLOCKING_REASON_LEVERAGED_OR_INVERSE: Final[str] = "leveraged_or_inverse_etf"

# Minimum bar count for a meaningful annualised stdev. 60 trading
# days ≈ 3 months — short enough that brand-new listings can be
# evaluated, long enough that the stdev is not pure noise.
DEFAULT_MIN_BARS_FOR_VOLATILITY: Final[int] = 60
TRADING_DAYS_PER_YEAR: Final[int] = 252

# Curated set of the most-traded US leveraged / inverse ETF tickers.
# Not exhaustive — the regex on the product name catches everything
# else (Direxion, ProShares, GraniteShares, et al.).
KNOWN_LEVERAGED_OR_INVERSE_TICKERS: Final[frozenset[str]] = frozenset(
    {
        # Direxion Daily 3x bull
        "TQQQ", "SOXL", "SPXL", "TNA", "FAS", "LABU", "NUGT",
        "JNUG", "GUSH", "ERX", "CURE", "DRN", "DPST", "TECL",
        # Direxion Daily 3x bear
        "SQQQ", "SOXS", "SPXS", "TZA", "FAZ", "LABD", "DUST",
        "JDST", "DRIP", "ERY", "DRV", "TECS",
        # ProShares UltraPro / UltraShort
        "UPRO", "SPXU", "QLD", "QID", "SSO", "SDS",
        "TBT", "TMF", "TMV", "USD", "SH", "PSQ", "DOG",
        # Single-name 2x (newer)
        "TSLL", "TSLS", "NVDL", "NVDS", "AMZD", "AMZU",
    }
)

# Name patterns that mark leverage / inverse. The regex requires
# explicit word boundaries to avoid false positives like
# "Ultratech Inc" or "Inverse Solutions".
_LEVERAGE_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?ix)"
    r"\b(?:"
    r"\d+x|"  # 2x, 3x, -2x, etc.
    r"daily\s+\d+x|"  # "Daily 3x"
    r"ultra(?:pro|short)?|"  # Ultra, UltraPro, UltraShort (ProShares)
    r"leveraged|"
    r"inverse|"
    r"bear\s+\d+x|"  # "Bear 3x"
    r"bull\s+\d+x"  # "Bull 3x"
    r")\b"
)


@dataclass(frozen=True)
class RiskUniverseInputs:
    """Per-candidate inputs to the risk gate.

    ``market_cap_eur`` may be ``None`` when the provider didn't return
    it — the gate then has to decide whether unknown == block. By
    doctrine it does: better to skip a name than to suggest a
    micro-cap on missing metadata.
    """

    ticker: str
    instrument_name: str
    market_cap_eur: Decimal | None
    bars: Sequence[HistoricalBar]


@dataclass(frozen=True)
class RiskUniverseGateResult:
    """Verdict + diagnostics from one gate pass.

    The annualised volatility is reported even on accepted candidates
    so the operator UI can show it alongside the forecast — high-vol
    accepted names get a softer signal than low-vol accepted names.
    """

    allowed: bool
    blocking_reason: str | None
    annualized_volatility_pct: Decimal | None
    market_cap_eur: Decimal | None


def is_leveraged_or_inverse(ticker: str, instrument_name: str) -> bool:
    """Return True if the candidate is a leveraged or inverse ETF.

    Combines a curated-ticker check with a regex on the product
    name. Either match is enough — the regex is intentionally a bit
    aggressive, but a false positive on this gate is cheap (we skip
    a name); a false negative is expensive (we hold a daily-reset
    product for 3-6 months and lose to compounding decay).
    """

    if ticker.upper() in KNOWN_LEVERAGED_OR_INVERSE_TICKERS:
        return True
    return _LEVERAGE_NAME_PATTERN.search(instrument_name) is not None


def annualized_volatility_pct(bars: Sequence[HistoricalBar]) -> Decimal | None:
    """Compute annualised volatility as a percentage from a bar series.

    Returns ``None`` if the series is too short (< 2 bars) or any
    bar has a non-positive close — both situations are surfaced as
    structural problems by the caller, not as accepted volatility.

    The math is plain Python (``math.log`` + ``math.sqrt``) so the
    function stays usable in environments without numpy. Sample
    stdev (Bessel-corrected) is annualised by ``sqrt(252)``.
    """

    n = len(bars)
    if n < 2:
        return None
    closes = [float(bar.close_price) for bar in bars]
    if any(close <= 0.0 for close in closes):
        return None
    log_returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, n)]
    m = len(log_returns)
    if m < 2:
        return None
    mean = sum(log_returns) / m
    variance = sum((r - mean) ** 2 for r in log_returns) / (m - 1)
    sigma_daily = math.sqrt(variance)
    sigma_annual = sigma_daily * math.sqrt(TRADING_DAYS_PER_YEAR)
    return (Decimal(repr(sigma_annual)) * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def evaluate_risk_universe_gate(
    inputs: RiskUniverseInputs,
    *,
    min_market_cap_eur: Decimal,
    max_annual_volatility_pct: Decimal,
    min_bars_for_volatility: int = DEFAULT_MIN_BARS_FOR_VOLATILITY,
) -> RiskUniverseGateResult:
    """Run the full risk-universe gate over one candidate.

    Order of checks matters:

    1. Leveraged / inverse — pure-metadata test, decide first.
    2. Market cap — if unknown, block (doctrine: missing > risky).
    3. Volatility — only meaningful with enough bars; insufficient
       history is its own blocking reason so the UI can distinguish
       "new listing, come back later" from "too wild, never".

    The reported ``annualized_volatility_pct`` is populated whenever
    we successfully computed it, even if a later check blocks the
    candidate — useful for explanation panels.
    """

    if not isinstance(min_market_cap_eur, Decimal):
        raise TypeError("min_market_cap_eur must be a Decimal")
    if not isinstance(max_annual_volatility_pct, Decimal):
        raise TypeError("max_annual_volatility_pct must be a Decimal")

    # 1. Leveraged / inverse — pure string check on metadata.
    if is_leveraged_or_inverse(inputs.ticker, inputs.instrument_name):
        return RiskUniverseGateResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_LEVERAGED_OR_INVERSE,
            annualized_volatility_pct=None,
            market_cap_eur=inputs.market_cap_eur,
        )

    # 2. Market cap — doctrine: unknown counts as block.
    if inputs.market_cap_eur is None:
        return RiskUniverseGateResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_UNKNOWN_MARKET_CAP,
            annualized_volatility_pct=None,
            market_cap_eur=None,
        )
    if inputs.market_cap_eur < min_market_cap_eur:
        return RiskUniverseGateResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_BELOW_MIN_MARKET_CAP,
            annualized_volatility_pct=None,
            market_cap_eur=inputs.market_cap_eur,
        )

    # 3. Volatility — needs enough bars.
    if len(inputs.bars) < min_bars_for_volatility:
        return RiskUniverseGateResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_INSUFFICIENT_BARS,
            annualized_volatility_pct=None,
            market_cap_eur=inputs.market_cap_eur,
        )
    vol_pct = annualized_volatility_pct(inputs.bars)
    if vol_pct is None:
        # Structural problem in the bar series (non-positive close,
        # etc). Treat as insufficient — caller's bar_integrity check
        # is the right place to surface the structural reason.
        return RiskUniverseGateResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_INSUFFICIENT_BARS,
            annualized_volatility_pct=None,
            market_cap_eur=inputs.market_cap_eur,
        )
    if vol_pct > max_annual_volatility_pct:
        return RiskUniverseGateResult(
            allowed=False,
            blocking_reason=BLOCKING_REASON_ABOVE_MAX_VOLATILITY,
            annualized_volatility_pct=vol_pct,
            market_cap_eur=inputs.market_cap_eur,
        )

    return RiskUniverseGateResult(
        allowed=True,
        blocking_reason=None,
        annualized_volatility_pct=vol_pct,
        market_cap_eur=inputs.market_cap_eur,
    )


__all__ = [
    "BLOCKING_REASON_ABOVE_MAX_VOLATILITY",
    "BLOCKING_REASON_BELOW_MIN_MARKET_CAP",
    "BLOCKING_REASON_INSUFFICIENT_BARS",
    "BLOCKING_REASON_LEVERAGED_OR_INVERSE",
    "BLOCKING_REASON_UNKNOWN_MARKET_CAP",
    "DEFAULT_MIN_BARS_FOR_VOLATILITY",
    "KNOWN_LEVERAGED_OR_INVERSE_TICKERS",
    "RiskUniverseGateResult",
    "RiskUniverseInputs",
    "TRADING_DAYS_PER_YEAR",
    "annualized_volatility_pct",
    "evaluate_risk_universe_gate",
    "is_leveraged_or_inverse",
]
