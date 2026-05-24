"""Research evidence summarizer for the Decision Package.

Slice 9 wires the Research Desk into the Decision Package evidence chain.
The doctrine (release-1-functional-workflow-blueprint.md §6 +
version-1-product-experience-locks.md §11) treats source content as
**evidence**, never as **instruction**: research can flag a block, but
research alone can never *lift* a block. The underlying storage
invariants (``ResearchSourceEvidenceItemRecord.blocks_suggestions=True``,
``ResearchSourceCredibilityAssessmentRecord.blocks_suggestions=True``)
enforce this at the dataclass level.

This module is **pure Python** — no I/O, no datetime.now() except as a
parameter — so the summary is deterministic and trivially testable. AI
never appears here; the rules are an explicit decision tree over a fixed
set of signals.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

CREDIBILITY_NO_RESEARCH = "no_research"
CREDIBILITY_HIGH = "high"
CREDIBILITY_MIXED = "mixed"
CREDIBILITY_LOW = "low"

FRESHNESS_NO_RESEARCH = "no_research"
FRESHNESS_FRESH = "fresh"
FRESHNESS_MIXED = "mixed"
FRESHNESS_STALE = "stale"

BLOCKING_REASON_PROMPT_INJECTION_HIGH_RISK = "prompt_injection_high_risk"
BLOCKING_REASON_CREDIBILITY_REJECTED = "credibility_rejected"

# Days thresholds for freshness classification. Locked here so callers
# can rely on the deterministic boundary; downstream tests reference
# these constants rather than the integer literals.
FRESHNESS_FRESH_MAX_DAYS = 30
FRESHNESS_MIXED_MAX_DAYS = 90


@dataclass(frozen=True)
class ResearchEvidenceInputs:
    """Per-source inputs to the summarizer.

    Each entry represents one research source confirmed-linked to the
    asset. ``credibility_level`` and ``prompt_injection_risk_level``
    follow the storage contract values (e.g. ``high`` / ``medium`` /
    ``low`` / ``unknown``); ``last_signal_at`` is the most recent
    timestamp on the source's evidence chain (assessment / scan /
    extraction).
    """

    library_source_id: str
    credibility_level: str | None
    prompt_injection_risk_level: str | None
    last_signal_at: datetime | None


@dataclass(frozen=True)
class ResearchEvidenceSummary:
    research_evidence_count: int
    research_credibility_summary: str | None
    research_freshness_status: str | None
    research_blocking_reason: str | None
    research_snippet_nl: str


def _normalize(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def _aggregate_credibility(levels: list[str]) -> str | None:
    """Aggregate per-source credibility levels into one bucket.

    ``high`` only when every linked source assesses to high; ``low``
    when every source is low; otherwise ``mixed``. Sources with unknown
    or absent assessments are ignored — if no source has an assessment
    the aggregate is ``mixed`` (we have research but no credibility
    signal yet).
    """

    known = [level for level in levels if level in {"high", "medium", "low"}]
    if not known:
        return CREDIBILITY_MIXED
    if all(level == "high" for level in known):
        return CREDIBILITY_HIGH
    if all(level == "low" for level in known):
        return CREDIBILITY_LOW
    return CREDIBILITY_MIXED


def _aggregate_freshness(timestamps: list[datetime], *, now: datetime) -> str | None:
    if not timestamps:
        return FRESHNESS_MIXED
    age_days = [(now - ts).days for ts in timestamps if ts is not None]
    if not age_days:
        return FRESHNESS_MIXED
    if all(days <= FRESHNESS_FRESH_MAX_DAYS for days in age_days):
        return FRESHNESS_FRESH
    if all(days > FRESHNESS_MIXED_MAX_DAYS for days in age_days):
        return FRESHNESS_STALE
    return FRESHNESS_MIXED


def _build_snippet_nl(
    *,
    count: int,
    credibility: str | None,
    freshness: str | None,
    blocking_reason: str | None,
) -> str:
    if count == 0:
        return "Geen onderzoek gekoppeld aan dit asset."
    if blocking_reason == BLOCKING_REASON_PROMPT_INJECTION_HIGH_RISK:
        return (
            f"{count} onderzoeksbron(nen) gekoppeld, maar minstens één "
            "bron heeft een hoog prompt-injection risico. Onderzoek is "
            "geblokkeerd voor gebruik in suggesties; review eerst de bron."
        )
    if blocking_reason == BLOCKING_REASON_CREDIBILITY_REJECTED:
        return (
            f"{count} onderzoeksbron(nen) gekoppeld, maar minstens één "
            "bron is afgewezen door de credibility-assessment. Onderzoek "
            "is geblokkeerd; review de credibility-uitkomst."
        )
    credibility_label = {
        CREDIBILITY_HIGH: "hoge credibility",
        CREDIBILITY_MIXED: "gemengde credibility",
        CREDIBILITY_LOW: "lage credibility",
    }.get(credibility or "", "credibility onbekend")
    freshness_label = {
        FRESHNESS_FRESH: "vers",
        FRESHNESS_MIXED: "gemengde versheid",
        FRESHNESS_STALE: "verouderd",
    }.get(freshness or "", "versheid onbekend")
    return (
        f"{count} onderzoeksbron(nen) gekoppeld; {credibility_label}, "
        f"{freshness_label}. Onderzoek is read-only context; het kan een "
        "block opwerpen maar nooit een block opheffen."
    )


def summarize_research_for_asset(
    sources: Iterable[ResearchEvidenceInputs],
    *,
    now: datetime,
) -> ResearchEvidenceSummary:
    """Aggregate per-source research signals into one Decision-Package summary.

    The function never raises and never reaches across an I/O boundary;
    every result follows directly from the inputs.
    """

    source_list = list(sources)
    count = len(source_list)
    if count == 0:
        return ResearchEvidenceSummary(
            research_evidence_count=0,
            research_credibility_summary=CREDIBILITY_NO_RESEARCH,
            research_freshness_status=FRESHNESS_NO_RESEARCH,
            research_blocking_reason=None,
            research_snippet_nl=_build_snippet_nl(
                count=0,
                credibility=None,
                freshness=None,
                blocking_reason=None,
            ),
        )

    blocking_reason: str | None = None
    for source in source_list:
        if _normalize(source.prompt_injection_risk_level) == "high":
            blocking_reason = BLOCKING_REASON_PROMPT_INJECTION_HIGH_RISK
            break
    if blocking_reason is None:
        for source in source_list:
            if _normalize(source.credibility_level) == "rejected":
                blocking_reason = BLOCKING_REASON_CREDIBILITY_REJECTED
                break

    credibility = _aggregate_credibility(
        [_normalize(s.credibility_level) for s in source_list]
    )
    freshness = _aggregate_freshness(
        [s.last_signal_at for s in source_list if s.last_signal_at is not None],
        now=now,
    )

    snippet = _build_snippet_nl(
        count=count,
        credibility=credibility,
        freshness=freshness,
        blocking_reason=blocking_reason,
    )

    return ResearchEvidenceSummary(
        research_evidence_count=count,
        research_credibility_summary=credibility,
        research_freshness_status=freshness,
        research_blocking_reason=blocking_reason,
        research_snippet_nl=snippet,
    )


__all__ = [
    "CREDIBILITY_NO_RESEARCH",
    "CREDIBILITY_HIGH",
    "CREDIBILITY_MIXED",
    "CREDIBILITY_LOW",
    "FRESHNESS_NO_RESEARCH",
    "FRESHNESS_FRESH",
    "FRESHNESS_MIXED",
    "FRESHNESS_STALE",
    "FRESHNESS_FRESH_MAX_DAYS",
    "FRESHNESS_MIXED_MAX_DAYS",
    "BLOCKING_REASON_PROMPT_INJECTION_HIGH_RISK",
    "BLOCKING_REASON_CREDIBILITY_REJECTED",
    "ResearchEvidenceInputs",
    "ResearchEvidenceSummary",
    "summarize_research_for_asset",
]
