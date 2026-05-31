"""Tests for the AI research-extraction hallucination guard.

The guard is the doctrine lock for AI extraction: every fact in the
output must either be a verbatim (whitespace-normalised) substring of
the source document, or — for paraphrase-style prose — every numeric
token it carries must already appear in the source. A fact that does
neither is a hallucination and the entire batch is blocked.
"""

from __future__ import annotations

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_FACT_EMPTY,
    BLOCKING_REASON_FACT_TOO_LONG,
    BLOCKING_REASON_HALLUCINATED_FACTS,
    BLOCKING_REASON_TOO_MANY_FACTS,
    EXTRACTION_BLOCKING_REASON_EMPTY_OUTPUT,
    EXTRACTION_STATUS_BLOCKED,
    EXTRACTION_STATUS_GENERATED,
    validate_extracted_facts,
)

_SOURCE = (
    "Apple Inc. Q1 2025 Earnings Release.\n"
    "Revenue rose to 124.3 billion USD, beating consensus.\n"
    "iPhone sales were strong; Services revenue grew 18%.\n"
    "CEO Tim Cook commented on AI investments going forward.\n"
)


def test_verbatim_quote_passes() -> None:
    result = validate_extracted_facts(
        extracted_facts=[
            "Revenue rose to 124.3 billion USD, beating consensus.",
            "Services revenue grew 18%.",
        ],
        source_text=_SOURCE,
        max_facts=10,
        max_fact_chars=500,
    )
    assert result.status == EXTRACTION_STATUS_GENERATED
    assert result.blocking_reason is None
    assert result.hallucinated_fact_indices == ()


def test_whitespace_differences_in_verbatim_quote_still_pass() -> None:
    """A quote with collapsed whitespace / different line breaks is
    treated as the same substring as the original — operators see clean
    extracted text, the guard is resilient to formatting."""

    result = validate_extracted_facts(
        extracted_facts=[
            "Revenue rose  to  124.3 billion USD,\nbeating consensus.",
        ],
        source_text=_SOURCE,
        max_facts=5,
        max_fact_chars=500,
    )
    assert result.status == EXTRACTION_STATUS_GENERATED


def test_paraphrase_with_only_source_numbers_passes() -> None:
    """A short paraphrase that doesn't quote verbatim but only uses
    numbers from the source is allowed — the numeric guard catches the
    high-leverage hallucination path (invented EPS, made-up growth %)."""

    result = validate_extracted_facts(
        extracted_facts=[
            "Q1 omzet steeg met 18% volgens het bericht."
        ],
        source_text=_SOURCE,
        max_facts=5,
        max_fact_chars=500,
    )
    assert result.status == EXTRACTION_STATUS_GENERATED


def test_hallucinated_number_blocks_batch() -> None:
    result = validate_extracted_facts(
        extracted_facts=[
            "Revenue rose to 124.3 billion USD, beating consensus.",
            "EPS came in at 2.18 per share.",  # 2.18 not in source
        ],
        source_text=_SOURCE,
        max_facts=10,
        max_fact_chars=500,
    )
    assert result.status == EXTRACTION_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_HALLUCINATED_FACTS
    # The first fact is verbatim, the second invented a number.
    assert result.hallucinated_fact_indices == (1,)


def test_ungrounded_prose_blocks_batch() -> None:
    """A paraphrase with no numbers AND no verbatim substring match is
    refused — the AI must anchor every claim in the source."""

    result = validate_extracted_facts(
        extracted_facts=[
            "Apple zal volgens analisten een uitstekend jaar tegemoet gaan.",
        ],
        source_text=_SOURCE,
        max_facts=5,
        max_fact_chars=500,
    )
    assert result.status == EXTRACTION_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_HALLUCINATED_FACTS
    assert result.hallucinated_fact_indices == (0,)


def test_empty_list_is_blocked() -> None:
    result = validate_extracted_facts(
        extracted_facts=[],
        source_text=_SOURCE,
        max_facts=10,
        max_fact_chars=500,
    )
    assert result.status == EXTRACTION_STATUS_BLOCKED
    assert result.blocking_reason == EXTRACTION_BLOCKING_REASON_EMPTY_OUTPUT


def test_empty_string_fact_is_blocked() -> None:
    result = validate_extracted_facts(
        extracted_facts=["Revenue rose to 124.3 billion USD.", "   "],
        source_text=_SOURCE,
        max_facts=10,
        max_fact_chars=500,
    )
    assert result.status == EXTRACTION_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_FACT_EMPTY


def test_over_long_fact_is_blocked() -> None:
    long_fact = "a" * 600
    result = validate_extracted_facts(
        extracted_facts=[long_fact],
        source_text=_SOURCE,
        max_facts=10,
        max_fact_chars=500,
    )
    assert result.status == EXTRACTION_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_FACT_TOO_LONG


def test_too_many_facts_is_blocked() -> None:
    result = validate_extracted_facts(
        extracted_facts=[
            "Revenue rose to 124.3 billion USD." for _ in range(20)
        ],
        source_text=_SOURCE,
        max_facts=10,
        max_fact_chars=500,
    )
    assert result.status == EXTRACTION_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_TOO_MANY_FACTS


def test_case_insensitive_substring_match() -> None:
    """A quote whose casing differs from the source still matches —
    operators copy-pasting text in title-case shouldn't be blocked."""

    result = validate_extracted_facts(
        extracted_facts=["REVENUE ROSE TO 124.3 BILLION USD, BEATING CONSENSUS."],
        source_text=_SOURCE,
        max_facts=5,
        max_fact_chars=500,
    )
    assert result.status == EXTRACTION_STATUS_GENERATED
