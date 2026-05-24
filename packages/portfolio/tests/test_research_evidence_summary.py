"""Tests for the deterministic research evidence summarizer (Slice 9)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_CREDIBILITY_REJECTED,
    BLOCKING_REASON_PROMPT_INJECTION_HIGH_RISK,
    CREDIBILITY_HIGH,
    CREDIBILITY_LOW,
    CREDIBILITY_MIXED,
    CREDIBILITY_NO_RESEARCH,
    FRESHNESS_FRESH,
    FRESHNESS_MIXED,
    FRESHNESS_NO_RESEARCH,
    FRESHNESS_STALE,
    ResearchEvidenceInputs,
    summarize_research_for_asset,
)

_NOW = datetime(2025, 5, 24, 12, 0, tzinfo=UTC)


def _input(
    *,
    library_source_id: str = "src-1",
    credibility_level: str | None = "high",
    prompt_injection_risk_level: str | None = "low",
    days_ago: int = 7,
) -> ResearchEvidenceInputs:
    return ResearchEvidenceInputs(
        library_source_id=library_source_id,
        credibility_level=credibility_level,
        prompt_injection_risk_level=prompt_injection_risk_level,
        last_signal_at=_NOW - timedelta(days=days_ago),
    )


def test_no_sources_returns_no_research() -> None:
    result = summarize_research_for_asset([], now=_NOW)
    assert result.research_evidence_count == 0
    assert result.research_credibility_summary == CREDIBILITY_NO_RESEARCH
    assert result.research_freshness_status == FRESHNESS_NO_RESEARCH
    assert result.research_blocking_reason is None
    assert "Geen onderzoek" in result.research_snippet_nl


def test_single_high_credibility_fresh_source() -> None:
    result = summarize_research_for_asset(
        [_input(credibility_level="high", days_ago=5)],
        now=_NOW,
    )
    assert result.research_evidence_count == 1
    assert result.research_credibility_summary == CREDIBILITY_HIGH
    assert result.research_freshness_status == FRESHNESS_FRESH
    assert result.research_blocking_reason is None
    assert "hoge credibility" in result.research_snippet_nl
    assert "vers" in result.research_snippet_nl


def test_all_low_credibility_sources_aggregate_to_low() -> None:
    result = summarize_research_for_asset(
        [
            _input(library_source_id="a", credibility_level="low"),
            _input(library_source_id="b", credibility_level="low"),
        ],
        now=_NOW,
    )
    assert result.research_credibility_summary == CREDIBILITY_LOW


def test_mixed_credibility_levels_aggregate_to_mixed() -> None:
    result = summarize_research_for_asset(
        [
            _input(library_source_id="a", credibility_level="high"),
            _input(library_source_id="b", credibility_level="low"),
        ],
        now=_NOW,
    )
    assert result.research_credibility_summary == CREDIBILITY_MIXED


def test_unknown_credibility_levels_aggregate_to_mixed() -> None:
    result = summarize_research_for_asset(
        [_input(credibility_level=None)],
        now=_NOW,
    )
    assert result.research_credibility_summary == CREDIBILITY_MIXED


def test_high_prompt_injection_blocks_research() -> None:
    result = summarize_research_for_asset(
        [
            _input(credibility_level="high", prompt_injection_risk_level="high"),
        ],
        now=_NOW,
    )
    assert result.research_blocking_reason == (
        BLOCKING_REASON_PROMPT_INJECTION_HIGH_RISK
    )
    assert "prompt-injection" in result.research_snippet_nl
    # credibility/freshness still computed but block dominates the snippet
    assert result.research_credibility_summary == CREDIBILITY_HIGH


def test_rejected_credibility_blocks_research() -> None:
    result = summarize_research_for_asset(
        [_input(credibility_level="rejected")],
        now=_NOW,
    )
    assert result.research_blocking_reason == BLOCKING_REASON_CREDIBILITY_REJECTED
    assert "credibility" in result.research_snippet_nl


def test_prompt_injection_blocks_before_credibility_rejected() -> None:
    result = summarize_research_for_asset(
        [
            _input(
                library_source_id="a",
                credibility_level="rejected",
                prompt_injection_risk_level="high",
            ),
        ],
        now=_NOW,
    )
    assert result.research_blocking_reason == (
        BLOCKING_REASON_PROMPT_INJECTION_HIGH_RISK
    )


def test_all_stale_sources_yield_stale_freshness() -> None:
    result = summarize_research_for_asset(
        [_input(days_ago=120)],
        now=_NOW,
    )
    assert result.research_freshness_status == FRESHNESS_STALE


def test_mixed_age_sources_yield_mixed_freshness() -> None:
    result = summarize_research_for_asset(
        [
            _input(library_source_id="a", days_ago=5),
            _input(library_source_id="b", days_ago=200),
        ],
        now=_NOW,
    )
    assert result.research_freshness_status == FRESHNESS_MIXED


def test_sources_without_timestamps_yield_mixed_freshness() -> None:
    inputs = ResearchEvidenceInputs(
        library_source_id="a",
        credibility_level="high",
        prompt_injection_risk_level="low",
        last_signal_at=None,
    )
    result = summarize_research_for_asset([inputs], now=_NOW)
    assert result.research_freshness_status == FRESHNESS_MIXED


def test_count_reflects_total_input_sources() -> None:
    result = summarize_research_for_asset(
        [_input(library_source_id=f"src-{i}") for i in range(5)],
        now=_NOW,
    )
    assert result.research_evidence_count == 5


def test_snippet_nl_is_always_present_and_in_dutch() -> None:
    result = summarize_research_for_asset([_input()], now=_NOW)
    assert result.research_snippet_nl
    assert "onderzoek" in result.research_snippet_nl.lower()
