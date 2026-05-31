"""Deterministic guards around the AI research-extraction layer.

Companion to :mod:`ai_explanation_guards`. The explanation guard is
built for *paraphrase* outputs (free-form Dutch text that summarises
already-persisted evidence); this module's guard is built for
*extraction* outputs (a list of facts / quotes pulled from a research
source document).

The locked V1 doctrine for AI extraction
(release-1-functional-workflow-blueprint.md §6 — same anchor as §8):

* AI **never** invents a fact. Each item in the output list must
  either be a verbatim substring of the source document (a literal
  quote) or a tight paraphrase whose every numeric token already
  appears in the source.
* Output is bound to a specific ``(library_source_id, source_text_hash)``
  pair — a new extraction is required when the source changes.
* Empty / oversized / over-numerous extractions are blocked.
* Hallucinated facts are blocked, not displayed, so a wrong AI
  reading can never silently feed into Decision Packages.

This module is pure Python — no I/O. The orchestrator wires it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EXTRACTION_STATUS_GENERATED = "generated"
EXTRACTION_STATUS_BLOCKED = "blocked"
EXTRACTION_STATUS_FAILED = "failed"

BLOCKING_REASON_HALLUCINATED_FACTS = "hallucinated_facts"
BLOCKING_REASON_EMPTY_OUTPUT = "empty_extraction_output"
BLOCKING_REASON_TOO_MANY_FACTS = "too_many_facts"
BLOCKING_REASON_FACT_TOO_LONG = "fact_too_long"
BLOCKING_REASON_FACT_EMPTY = "empty_fact"

# Mirror of the explanation-guard numeric pattern; kept duplicated so a
# future tweak to one validator can't silently shift the other.
_NUMERIC_TOKEN_PATTERN = re.compile(
    r"-?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|-?\d+(?:[.,]\d+)?"
)
# Whitespace + zero-width / NBSP characters that we normalise away
# before substring comparison so a verbatim quote with a slightly
# different whitespace layout still matches.
_WS_NORMALISER = re.compile(r"\s+")


@dataclass(frozen=True)
class ExtractionValidationResult:
    """Outcome of one batch validation.

    ``hallucinated_facts`` lists the *output indices* of items that
    failed the substring / numeric check (not the strings themselves —
    quoting the offending fact in a structured response would let the
    AI write its own "blocked" reason, which is exactly the abuse path
    we want to keep out).
    """

    status: str
    blocking_reason: str | None
    hallucinated_fact_indices: tuple[int, ...]


def _normalise_text(text: str) -> str:
    """Collapse all whitespace runs to a single space, casefold.

    Substring comparison is then resilient to: line wrapping, NBSPs,
    indentation differences, capital-letter differences. Numeric tokens
    are checked separately via the numeric normaliser so this can be
    aggressive without losing precision on financial figures.
    """

    return _WS_NORMALISER.sub(" ", text).strip().casefold()


def _extract_numeric_tokens(text: str) -> set[str]:
    return {match.group() for match in _NUMERIC_TOKEN_PATTERN.finditer(text)}


def _fact_is_grounded(*, fact: str, normalised_source: str, source_numbers: set[str]) -> bool:
    """A fact is grounded when (a) it appears as a normalised substring
    of the source, OR (b) every numeric token it carries is also in the
    source.

    The dual check lets the AI paraphrase prose ("the company beat
    consensus") without quoting verbatim, while still locking down
    every number (an invented EPS figure is always blocked, even
    inside an otherwise harmless sentence).
    """

    normalised_fact = _normalise_text(fact)
    if normalised_fact and normalised_fact in normalised_source:
        return True
    fact_numbers = _extract_numeric_tokens(fact)
    if not fact_numbers:
        # No numbers and not a verbatim match — treat as a hallucination
        # rather than allowing the AI to assert ungrounded claims.
        return False
    return fact_numbers.issubset(source_numbers)


def validate_extracted_facts(
    *,
    extracted_facts: list[str],
    source_text: str,
    max_facts: int,
    max_fact_chars: int,
) -> ExtractionValidationResult:
    """Apply the doctrine to one AI extraction batch.

    Returns the final ``status`` and the index list of failing items.
    Empty / oversize / over-numerous failures block before the
    substring check so the most informative reason wins. The function
    never raises — bad input produces a ``blocked`` result with the
    appropriate reason.
    """

    if not extracted_facts:
        return ExtractionValidationResult(
            status=EXTRACTION_STATUS_BLOCKED,
            blocking_reason=BLOCKING_REASON_EMPTY_OUTPUT,
            hallucinated_fact_indices=(),
        )
    if len(extracted_facts) > max_facts:
        return ExtractionValidationResult(
            status=EXTRACTION_STATUS_BLOCKED,
            blocking_reason=BLOCKING_REASON_TOO_MANY_FACTS,
            hallucinated_fact_indices=(),
        )
    for fact in extracted_facts:
        if not fact or not fact.strip():
            return ExtractionValidationResult(
                status=EXTRACTION_STATUS_BLOCKED,
                blocking_reason=BLOCKING_REASON_FACT_EMPTY,
                hallucinated_fact_indices=(),
            )
        if len(fact) > max_fact_chars:
            return ExtractionValidationResult(
                status=EXTRACTION_STATUS_BLOCKED,
                blocking_reason=BLOCKING_REASON_FACT_TOO_LONG,
                hallucinated_fact_indices=(),
            )

    normalised_source = _normalise_text(source_text)
    source_numbers = _extract_numeric_tokens(source_text)
    hallucinated: list[int] = [
        idx
        for idx, fact in enumerate(extracted_facts)
        if not _fact_is_grounded(
            fact=fact,
            normalised_source=normalised_source,
            source_numbers=source_numbers,
        )
    ]
    if hallucinated:
        return ExtractionValidationResult(
            status=EXTRACTION_STATUS_BLOCKED,
            blocking_reason=BLOCKING_REASON_HALLUCINATED_FACTS,
            hallucinated_fact_indices=tuple(hallucinated),
        )
    return ExtractionValidationResult(
        status=EXTRACTION_STATUS_GENERATED,
        blocking_reason=None,
        hallucinated_fact_indices=(),
    )


__all__ = [
    "BLOCKING_REASON_EMPTY_OUTPUT",
    "BLOCKING_REASON_FACT_EMPTY",
    "BLOCKING_REASON_FACT_TOO_LONG",
    "BLOCKING_REASON_HALLUCINATED_FACTS",
    "BLOCKING_REASON_TOO_MANY_FACTS",
    "EXTRACTION_STATUS_BLOCKED",
    "EXTRACTION_STATUS_FAILED",
    "EXTRACTION_STATUS_GENERATED",
    "ExtractionValidationResult",
    "validate_extracted_facts",
]
