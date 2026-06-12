"""News-severity classifier + held-position exit evaluator (V1.2 §K).

The retiree-income doctrine has *no* stop-loss on held positions —
the user waits for the +4 % target. That makes the news safety net
critical: when a real company-specific event happens (profit
warning, fraud, bankruptcy filing) the user needs the system to
*proactively* surface a "Verkopen — bedrijfsnieuws" suggestion
before the position bleeds out.

The piece you don't want is the system reacting to every news
headline. Routine analyst notes, dividend declarations, and
sector commentary fire dozens of items per name per week — if any
of them triggered a SELL the user would whipsaw out of perfectly
good positions.

This module is the pragmatic V1 classifier: pattern-match against
a curated keyword catalogue in English + Dutch and emit one of
four severity tiers:

    INFO     analyst notes, dividend, general commentary
    WARN     regulatory inquiry, executive departure, downgrade
    ALERT    profit warning, guidance cut, lawsuit, recall, exec exit
    CRITICAL fraud, SEC investigation, bankruptcy, going concern

Only ``ALERT`` and ``CRITICAL`` trigger an exit suggestion. The
``WARN`` items show up in the operator UI as informational badges,
not as actions.

V2 will plug in an AI classifier (Claude) for the ambiguous tail —
"FDA inspection" can be a routine site visit (INFO) or a Form 483
warning (ALERT) and a pattern match alone can't tell them apart.
For now we accept that V1 will mis-classify some borderline cases;
the locked invariant is that ``CRITICAL`` keywords are *always*
treated as critical and never silently downgraded.

This module is pure Python — no I/O, no network, no LLM.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class NewsSeverity(StrEnum):
    """Locked severity tiers in ascending order of urgency."""

    INFO = "info"
    WARN = "warn"
    ALERT = "alert"
    CRITICAL = "critical"


# Severity rank — used internally to "take the highest tier wins"
# when multiple keywords match the same item.
_SEVERITY_RANK: Final[dict[NewsSeverity, int]] = {
    NewsSeverity.INFO: 0,
    NewsSeverity.WARN: 1,
    NewsSeverity.ALERT: 2,
    NewsSeverity.CRITICAL: 3,
}


@dataclass(frozen=True)
class NewsItem:
    """Inputs to the classifier — title + body, both lower-cased
    internally before matching."""

    title: str
    body: str = ""


@dataclass(frozen=True)
class NewsClassificationResult:
    """Verdict for one news item.

    ``matched_keyword`` is the *first* keyword from the highest-
    ranking matched tier; useful for the audit trail and the UI
    explanation ("Geclassificeerd als ALERT: matched 'profit
    warning')").
    """

    severity: NewsSeverity
    matched_keyword: str | None


@dataclass(frozen=True)
class NewsExitEvaluation:
    """Verdict over a batch of news items for one held position."""

    should_exit: bool
    exit_severity: NewsSeverity | None
    triggering_keyword: str | None
    classification_counts: dict[NewsSeverity, int]


# CRITICAL — keywords that ALWAYS produce an exit suggestion. These
# are events from which a 3-6 month hold is essentially never going
# to recover.
_CRITICAL_KEYWORDS: Final[tuple[str, ...]] = (
    "fraud",
    "fraude",
    "accounting scandal",
    "boekhoudfraude",
    "sec investigation",
    "sec enforcement action",
    "doj investigation",
    "going concern",
    "bankruptcy",
    "faillissement",
    "chapter 11",
    "chapter 7",
    "insolvent",
    "insolventie",
    "delisting",
    "delisted",
    "auditor resigns",
    "auditor weigert",
    "auditor refused",
    "trading halted indefinitely",
    "ponzi",
    "embezzlement",
    "verduistering",
)

# ALERT — significant company-specific bad news. Exit-triggering but
# not as terminal as CRITICAL.
_ALERT_KEYWORDS: Final[tuple[str, ...]] = (
    "profit warning",
    "profit-warning",
    "winstwaarschuwing",
    "guidance cut",
    "guidance lowered",
    "lowers guidance",
    "lowered guidance",
    "cuts forecast",
    "cuts outlook",
    "ceo resigns",
    "ceo steps down",
    "ceo to resign",
    "ceo departure",
    "ceo vertrekt",
    "ceo opgestapt",
    "cfo resigns",
    "cfo steps down",
    "cfo departure",
    "cfo vertrekt",
    "major lawsuit",
    "class action",
    "class-action",
    "product recall",
    "recall announced",
    "terugroep",
    "terugroepactie",
    "fda rejects",
    "fda rejection",
    "fda warning letter",
    "form 483",
    "ema rejects",
    "earnings miss",
    "missed earnings",
    "missed estimates by",
)

# WARN — informational but not actionable. Displayed to the operator
# as a badge so they can monitor; do not trigger an exit.
_WARN_KEYWORDS: Final[tuple[str, ...]] = (
    "regulatory inquiry",
    "antitrust",
    "investigation opened",
    "rating downgrade",
    "credit downgrade",
    "downgrade",
    "analyst downgrade",
    "executive departure",
    "missed estimates",
    "below estimates",
    "below expectations",
    "concerns over",
    "warns about",
)

_PATTERNS_BY_SEVERITY: Final[tuple[tuple[NewsSeverity, tuple[str, ...]], ...]] = (
    (NewsSeverity.CRITICAL, _CRITICAL_KEYWORDS),
    (NewsSeverity.ALERT, _ALERT_KEYWORDS),
    (NewsSeverity.WARN, _WARN_KEYWORDS),
)


def _compile_word_boundary(keyword: str) -> re.Pattern[str]:
    """Compile a case-insensitive word-boundary regex for ``keyword``.

    ``\\b`` won't fire next to punctuation like ``-``, so for
    multi-word keywords we use literal substring matching guarded by
    spaces / start / end. Single-word keywords use ``\\b`` so
    "fraudster" doesn't fire ``fraud``.
    """

    if " " in keyword or "-" in keyword:
        # Multi-word — use a looser pattern with leading/trailing
        # boundaries (start, end, whitespace, punctuation).
        return re.compile(
            r"(?:^|[\s.,;:!?()])" + re.escape(keyword) + r"(?=$|[\s.,;:!?()])",
            re.IGNORECASE,
        )
    return re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)


_COMPILED_PATTERNS: Final[
    tuple[tuple[NewsSeverity, tuple[tuple[str, re.Pattern[str]], ...]], ...]
] = tuple(
    (
        severity,
        tuple((kw, _compile_word_boundary(kw)) for kw in keywords),
    )
    for severity, keywords in _PATTERNS_BY_SEVERITY
)


def classify_news_severity(item: NewsItem) -> NewsClassificationResult:
    """Classify a single news item.

    Returns the *highest* matched severity. Ties on rank are broken
    by the order keywords appear in the catalogue. No match →
    :data:`NewsSeverity.INFO` with ``matched_keyword=None``.
    """

    haystack = f"{item.title}\n{item.body}"
    for severity, patterns in _COMPILED_PATTERNS:
        for keyword, pattern in patterns:
            if pattern.search(haystack):
                return NewsClassificationResult(
                    severity=severity, matched_keyword=keyword
                )
    return NewsClassificationResult(
        severity=NewsSeverity.INFO, matched_keyword=None
    )


def evaluate_news_exit(items: Sequence[NewsItem]) -> NewsExitEvaluation:
    """Decide whether a held position should be exited on news flags.

    Doctrine: only ``ALERT`` and ``CRITICAL`` trigger an exit. The
    triggering item is the *first* news item (in the order supplied)
    whose classification reaches that bar — caller is responsible
    for ordering items chronologically newest-first if "latest
    trigger wins" semantics are desired.

    ``classification_counts`` is populated regardless so the UI can
    render a summary row ("3 INFO, 1 WARN, 1 ALERT — verkopen
    voorgesteld").
    """

    counts: dict[NewsSeverity, int] = {
        NewsSeverity.INFO: 0,
        NewsSeverity.WARN: 0,
        NewsSeverity.ALERT: 0,
        NewsSeverity.CRITICAL: 0,
    }
    trigger_severity: NewsSeverity | None = None
    trigger_keyword: str | None = None
    for item in items:
        result = classify_news_severity(item)
        counts[result.severity] += 1
        if trigger_severity is None and _SEVERITY_RANK[result.severity] >= _SEVERITY_RANK[
            NewsSeverity.ALERT
        ]:
            trigger_severity = result.severity
            trigger_keyword = result.matched_keyword

    return NewsExitEvaluation(
        should_exit=trigger_severity is not None,
        exit_severity=trigger_severity,
        triggering_keyword=trigger_keyword,
        classification_counts=counts,
    )


__all__ = [
    "NewsClassificationResult",
    "NewsExitEvaluation",
    "NewsItem",
    "NewsSeverity",
    "classify_news_severity",
    "evaluate_news_exit",
]
