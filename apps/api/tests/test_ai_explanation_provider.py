"""Tests for the AI explanation provider factory + stub (Slice 10)."""

from __future__ import annotations

from portfolio_outlook_portfolio import LOCKED_RISK_DISCLAIMER_NL

from portfolio_outlook_api.ai_explanation_provider import (
    STUB_PROVIDER_CODE,
    ExplanationProviderInputs,
    ExplanationProviderUnavailable,
    StubExplanationProvider,
    build_explanation_provider,
)
from portfolio_outlook_api.config import Settings


def _settings(**overrides: object) -> Settings:
    base = Settings()
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_factory_returns_unavailable_when_disabled_by_default() -> None:
    result = build_explanation_provider(_settings())
    assert isinstance(result, ExplanationProviderUnavailable)
    assert result.reason == "ai_explanation_disabled"


def test_factory_returns_stub_when_enabled_with_stub_provider_code() -> None:
    result = build_explanation_provider(
        _settings(
            ai_explanation_enabled=True,
            ai_explanation_provider_code=STUB_PROVIDER_CODE,
        )
    )
    assert isinstance(result, StubExplanationProvider)


def test_factory_returns_unavailable_for_unimplemented_provider() -> None:
    result = build_explanation_provider(
        _settings(
            ai_explanation_enabled=True,
            ai_explanation_provider_code="anthropic",
            ai_explanation_real_client_enabled=True,
        )
    )
    assert isinstance(result, ExplanationProviderUnavailable)
    assert result.reason == "real_client_not_implemented"


def test_factory_returns_unavailable_when_real_client_not_enabled() -> None:
    result = build_explanation_provider(
        _settings(
            ai_explanation_enabled=True,
            ai_explanation_provider_code="anthropic",
            ai_explanation_real_client_enabled=False,
        )
    )
    assert isinstance(result, ExplanationProviderUnavailable)
    assert result.reason == "real_client_not_enabled"


def test_stub_provider_paraphrases_input_with_disclaimer() -> None:
    provider = StubExplanationProvider()
    inputs = ExplanationProviderInputs(
        decision_package_id="dp-1",
        decision_package_content_hash="hash-1",
        symbol="AAPL",
        risk_profile="Gebalanceerd",
        rationale_nl="Houden vanwege lichte stijging.",
        package_explanation_nl="Volledig evidence chain aanwezig.",
        research_snippet_nl="2 onderzoeksbron(nen); hoge credibility, vers.",
        input_text="canonical json input",
    )
    result = provider.generate(inputs)
    assert result.model_provider_code == STUB_PROVIDER_CODE
    assert "AAPL" in result.output_text
    assert "Gebalanceerd" in result.output_text
    assert inputs.rationale_nl in result.output_text
    assert inputs.research_snippet_nl in result.output_text
    assert LOCKED_RISK_DISCLAIMER_NL in result.output_text


def test_stub_provider_handles_missing_research_snippet() -> None:
    provider = StubExplanationProvider()
    inputs = ExplanationProviderInputs(
        decision_package_id="dp-1",
        decision_package_content_hash="hash-1",
        symbol="AAPL",
        risk_profile="Gebalanceerd",
        rationale_nl="Houden.",
        package_explanation_nl="ok",
        research_snippet_nl=None,
        input_text="canonical json input",
    )
    result = provider.generate(inputs)
    assert result.output_text
    assert LOCKED_RISK_DISCLAIMER_NL in result.output_text
