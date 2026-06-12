"""News-sentiment booster for BUY conviction (V1.2 §S).

Companion to ``news_severity.py``. The severity module treats news
as an *exit* signal (CRITICAL / ALERT → sell); this module treats
news as an *entry-conviction* signal (positive flow → small boost
to the size we propose).

Two practitioner facts justify the separation:

* **Bad news kills positions; good news rarely makes them.** A single
  CRITICAL print can wipe out months of drift. A single bullish
  print rarely sustains 3-6 month outperformance on its own. So the
  *response* to each direction is asymmetric: bad news is a hard
  exit, good news is a small bias.
* **The conviction multiplier never replaces the math.** We *do not*
  let positive headlines override a failing confidence gate. The
  boost only nudges the conviction-weighted position size — a
  borderline candidate that the math says is fine becomes a
  larger position when the news flow agrees.

Locked bullish keyword catalogue (English + Dutch where common):

* Contract / customer wins, partnership announcements
* Analyst upgrades, target price increases
* Dividend raises, buyback announcements
* Insider buying disclosures
* FDA / EMA / regulatory approvals (drug, device, M&A)
* Beat earnings (the rare *unambiguous* positive earnings phrase)

Bearish-equivalent keywords are intentionally NOT mirrored here —
those live in ``news_severity.py`` where they trigger exits. This
module is bullish-only by construction.

The aggregate score is a normalised count: number of bullish items
÷ total items, clipped to [0, 1]. The integration layer maps that
score onto a configurable conviction multiplier (default cap of
+5 percentage points on ``confidence_pct``).

This module is pure Python — no I/O, no LLM. V2 may add a Claude
classifier for ambiguous headlines; V1 sticks to deterministic
pattern matching for auditability.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from portfolio_outlook_portfolio.news_severity import NewsItem

# Bullish keyword catalogue. Word-boundary regex on single-word
# keywords; looser punctuation-or-space boundaries on multi-word
# phrases (matches `news_severity.py` convention).
_BULLISH_KEYWORDS: Final[tuple[str, ...]] = (
    # Earnings / guidance positives
    "beats earnings",
    "beats estimates",
    "earnings beat",
    "raised guidance",
    "raises guidance",
    "guidance raised",
    "raises forecast",
    "raises outlook",
    "upbeat outlook",
    # Analyst positives
    "analyst upgrade",
    "upgraded to buy",
    "upgrade to buy",
    "rating upgrade",
    "price target raised",
    "target price raised",
    "raised price target",
    "raised target price",
    # Capital return
    "dividend hike",
    "dividend increase",
    "dividend raised",
    "dividend verhoogd",
    "buyback announced",
    "share buyback",
    "share repurchase",
    "stock buyback",
    # Insider buying
    "insider buying",
    "insider buy",
    "insider purchase",
    "ceo buys",
    "cfo buys",
    "director buys",
    # Regulatory / approvals
    "fda approval",
    "fda approves",
    "ema approval",
    "ema approves",
    "regulatory approval",
    "drug approval",
    "device approval",
    # Wins / partnerships
    "contract win",
    "major contract",
    "partnership announced",
    "strategic partnership",
    "acquisition target",
    "takeover bid",
    "buyout offer",
)

_MULTI_WORD_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = tuple(
    (
        kw,
        re.compile(
            r"(?:^|[\s.,;:!?()])" + re.escape(kw) + r"(?=$|[\s.,;:!?()])",
            re.IGNORECASE,
        ),
    )
    for kw in _BULLISH_KEYWORDS
    if " " in kw
)
_SINGLE_WORD_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = tuple(
    (kw, re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE))
    for kw in _BULLISH_KEYWORDS
    if " " not in kw
)


def _is_bullish(item: NewsItem) -> str | None:
    """Return the first matched bullish keyword, or ``None``."""

    haystack = f"{item.title}\n{item.body}"
    for keyword, pattern in _MULTI_WORD_PATTERNS:
        if pattern.search(haystack):
            return keyword
    for keyword, pattern in _SINGLE_WORD_PATTERNS:
        if pattern.search(haystack):
            return keyword
    return None


@dataclass(frozen=True)
class NewsSentimentScore:
    """Result of aggregating bullish news for one symbol.

    ``buy_bias`` ranges from ``0.0`` (no bullish content at all) to
    ``1.0`` (every item in the batch matched a bullish keyword). The
    integration layer maps this to a conviction multiplier capped at
    a small percentage-point boost (default 5 pp on confidence_pct).
    """

    total_items: int
    bullish_count: int
    matched_keywords: tuple[str, ...]
    buy_bias: Decimal


def compute_news_buy_bias(items: Sequence[NewsItem]) -> NewsSentimentScore:
    """Aggregate bullish-news classifications into a single score.

    Empty batches return ``buy_bias = 0``. Otherwise the bias is the
    bullish-fraction of the batch (the simplest, most defensible
    aggregator — every bullish item contributes equally).
    """

    matched: list[str] = []
    bullish_count = 0
    for item in items:
        kw = _is_bullish(item)
        if kw is not None:
            bullish_count += 1
            matched.append(kw)
    total = len(items)
    if total == 0:
        bias = Decimal("0.00")
    else:
        bias = (Decimal(bullish_count) / Decimal(total)).quantize(
            Decimal("0.01")
        )
    return NewsSentimentScore(
        total_items=total,
        bullish_count=bullish_count,
        matched_keywords=tuple(matched),
        buy_bias=bias,
    )


def apply_buy_bias_to_confidence(
    *,
    base_confidence_pct: Decimal,
    buy_bias: Decimal,
    max_boost_pct: Decimal,
) -> Decimal:
    """Lift ``base_confidence_pct`` by ``buy_bias × max_boost_pct``.

    The result is clipped at 100 % so a very bullish news flow can
    push the conviction to its mathematical ceiling but never
    overshoot. Bias of 0 returns the base unchanged.

    Args:
        base_confidence_pct: Predictor confidence (0–100).
        buy_bias: Aggregate news bias from
            :func:`compute_news_buy_bias` (0–1).
        max_boost_pct: User-configured ceiling on the boost. Default
            in the orchestrator is 5 (a +5 pp boost at full bullish
            bias).
    """

    if not isinstance(base_confidence_pct, Decimal):
        raise TypeError("base_confidence_pct must be a Decimal")
    if not isinstance(buy_bias, Decimal):
        raise TypeError("buy_bias must be a Decimal")
    if not isinstance(max_boost_pct, Decimal):
        raise TypeError("max_boost_pct must be a Decimal")
    if buy_bias < 0 or buy_bias > 1:
        raise ValueError("buy_bias must be 0–1")
    if max_boost_pct < 0:
        raise ValueError("max_boost_pct must be >= 0")
    boost = buy_bias * max_boost_pct
    boosted = base_confidence_pct + boost
    if boosted > Decimal("100"):
        return Decimal("100")
    return boosted.quantize(Decimal("0.01"))


__all__ = [
    "NewsSentimentScore",
    "apply_buy_bias_to_confidence",
    "compute_news_buy_bias",
]
