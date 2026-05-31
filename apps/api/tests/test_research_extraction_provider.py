"""Tests for the AI research-extraction provider factory.

Mirrors the explanation-provider factory tests: assert that each gate
returns a stable ``ResearchExtractionProviderUnavailable.reason``
string, and that the stub provider produces a deterministic batch of
facts that all pass the substring-based hallucination guard by
construction (the stub picks verbatim source lines).
"""

from __future__ import annotations

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.research_extraction_provider import (
    ResearchExtractionProviderInputs,
    ResearchExtractionProviderUnavailable,
    StubResearchExtractionProvider,
    build_research_extraction_provider,
)


def _reset() -> None:
    settings.research_ai_extraction_enabled = False
    settings.research_ai_extraction_provider_code = "stub"
    settings.research_ai_extraction_max_facts = 12
    settings.research_ai_extraction_max_fact_chars = 500


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def test_factory_returns_unavailable_by_default() -> None:
    result = build_research_extraction_provider(settings)
    assert isinstance(result, ResearchExtractionProviderUnavailable)
    assert result.reason == "research_extraction_disabled"


def test_factory_returns_stub_when_flag_on_and_code_stub() -> None:
    settings.research_ai_extraction_enabled = True
    settings.research_ai_extraction_provider_code = "stub"
    result = build_research_extraction_provider(settings)
    assert isinstance(result, StubResearchExtractionProvider)


def test_factory_returns_not_implemented_for_unknown_provider_code() -> None:
    settings.research_ai_extraction_enabled = True
    settings.research_ai_extraction_provider_code = "openai_gpt4"
    result = build_research_extraction_provider(settings)
    assert isinstance(result, ResearchExtractionProviderUnavailable)
    assert result.reason == "real_client_not_implemented"


def test_stub_picks_first_non_empty_lines_as_facts() -> None:
    """Stub guarantees every output is a verbatim substring of the
    source, so the hallucination guard always passes on stub output."""

    source = (
        "Apple Inc. Q1 2025 Earnings.\n"
        "\n"
        "Revenue rose to 124.3 billion USD.\n"
        "iPhone sales were strong.\n"
        "   \n"
        "Services revenue grew 18%.\n"
    )
    inputs = ResearchExtractionProviderInputs(
        library_source_id="src-1",
        source_text_hash="hash-1",
        asset_symbol="AAPL",
        source_type="filing",
        detected_language="en",
        max_facts=3,
        max_fact_chars=500,
        input_text=source,
    )
    result = StubResearchExtractionProvider().extract(inputs)
    assert result.extracted_facts == (
        "Apple Inc. Q1 2025 Earnings.",
        "Revenue rose to 124.3 billion USD.",
        "iPhone sales were strong.",
    )
    assert result.model_provider_code == "stub"


def test_stub_truncates_overlong_lines_to_max_fact_chars() -> None:
    long_line = "A" * 1000
    inputs = ResearchExtractionProviderInputs(
        library_source_id="src-1",
        source_text_hash="hash-1",
        asset_symbol=None,
        source_type=None,
        detected_language=None,
        max_facts=1,
        max_fact_chars=50,
        input_text=long_line,
    )
    result = StubResearchExtractionProvider().extract(inputs)
    assert len(result.extracted_facts) == 1
    assert len(result.extracted_facts[0]) == 50
