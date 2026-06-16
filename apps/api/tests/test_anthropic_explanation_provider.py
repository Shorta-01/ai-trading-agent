"""Tests for the V1.1 Slice 29 real Anthropic Claude explanation provider."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest
from ai_trading_agent_storage import ClaudeAiBudgetUsageRecord

from portfolio_outlook_api.ai_explanation_provider import (
    ExplanationProviderInputs,
)
from portfolio_outlook_api.anthropic_explanation_provider import (
    PROVIDER_CODE,
    SYSTEM_PROMPT_NL,
    AnthropicExplanationProvider,
    AnthropicTransientError,
    ClaudeAiBudgetExceededError,
    ExplanationPromptError,
    load_explanation_system_prompt,
)

# ---- Fake Anthropic client ---------------------------------------------


@dataclass
class _FakeContentBlock:
    text: str


@dataclass
class _FakeUsage:
    input_tokens: int = 500
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    output_tokens: int = 80


@dataclass
class _FakeMessage:
    content: list[_FakeContentBlock]
    usage: _FakeUsage
    model: str = "claude-haiku-4-5-20251001"


class _FakeMessagesAPI:
    def __init__(self, *, text: str, usage: _FakeUsage | None = None) -> None:
        self._text = text
        self._usage = usage or _FakeUsage()
        self.last_payload: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> _FakeMessage:
        self.last_payload = kwargs
        return _FakeMessage(
            content=[_FakeContentBlock(text=self._text)],
            usage=self._usage,
        )


class _FakeAnthropicClient:
    def __init__(self, *, text: str = "Samenvatting in het Nederlands.") -> None:
        self.messages = _FakeMessagesAPI(text=text)


class _FakeBudgetRepo:
    def __init__(self, *, monthly_total: Decimal = Decimal("0")) -> None:
        self._monthly_total = monthly_total
        self.saved: list[ClaudeAiBudgetUsageRecord] = []

    def monthly_total_eur(self, budget_month: str) -> Decimal:
        return self._monthly_total

    def save_usage(self, record):  # type: ignore[no-untyped-def]
        self.saved.append(record)


def _inputs(**overrides: Any) -> ExplanationProviderInputs:
    base = dict(
        decision_package_id="dp-1",
        decision_package_content_hash="hash-abc",
        symbol="AAPL",
        risk_profile="balanced",
        rationale_nl="Decision Package rationale.",
        package_explanation_nl="Decision Package uitleg.",
        research_snippet_nl="Research evidence snippet.",
        input_text="…",
    )
    base.update(overrides)
    return ExplanationProviderInputs(**base)


# ---- happy path --------------------------------------------------------


def test_generate_returns_text_and_persists_audit_row() -> None:
    repo = _FakeBudgetRepo()
    fake_client = _FakeAnthropicClient(text="Korte samenvatting.")
    provider = AnthropicExplanationProvider(
        budget_repo=repo,
        monthly_cap_eur=Decimal("50"),
        client_factory=lambda: fake_client,
    )
    result = provider.generate(_inputs())
    assert result.output_text == "Korte samenvatting."
    assert result.model_provider_code == PROVIDER_CODE
    assert result.model_name.startswith("claude-haiku")
    # One audit row was persisted.
    assert len(repo.saved) == 1
    row = repo.saved[0]
    assert row.call_kind == "explanation"
    assert row.safe_for_action_drafts is False
    assert row.safe_for_orders is False


def test_generate_sends_cached_system_prompt() -> None:
    repo = _FakeBudgetRepo()
    fake_client = _FakeAnthropicClient(text="x")
    provider = AnthropicExplanationProvider(
        budget_repo=repo,
        monthly_cap_eur=Decimal("50"),
        client_factory=lambda: fake_client,
    )
    provider.generate(_inputs())
    payload = fake_client.messages.last_payload
    assert payload is not None
    # System blocks include the locked Dutch prompt + the legal
    # disclaimer; both carry the ephemeral cache_control marker.
    system_blocks = payload["system"]
    assert len(system_blocks) == 2
    assert any(block["text"] == SYSTEM_PROMPT_NL for block in system_blocks)
    assert all(
        block.get("cache_control", {}).get("type") == "ephemeral"
        for block in system_blocks
    )


def test_generate_user_payload_includes_decision_package_hash() -> None:
    repo = _FakeBudgetRepo()
    fake_client = _FakeAnthropicClient(text="x")
    provider = AnthropicExplanationProvider(
        budget_repo=repo,
        monthly_cap_eur=Decimal("50"),
        client_factory=lambda: fake_client,
    )
    provider.generate(_inputs(decision_package_content_hash="hash-zzz"))
    payload = fake_client.messages.last_payload
    user_text = payload["messages"][0]["content"]
    assert "hash-zzz" in user_text
    assert "AAPL" in user_text


# ---- budget cap --------------------------------------------------------


# Mimic Anthropic SDK exception classes by name; the source matches
# on ``type(exc).__name__`` so the classes need the SDK names exactly.
class RateLimitError(Exception):  # noqa: N818 — matches SDK name
    """Mimics anthropic.RateLimitError without depending on the SDK."""


class OverloadedError(Exception):  # noqa: N818 — matches SDK name
    """Mimics anthropic.OverloadedError."""


class APITimeoutError(Exception):  # noqa: N818 — matches SDK name
    """Mimics anthropic.APITimeoutError."""


class _RaisingMessagesAPI:
    def __init__(self, *, exc: Exception) -> None:
        self._exc = exc

    def create(self, **kwargs: Any) -> Any:  # noqa: ARG002 — unused
        raise self._exc


class _RaisingAnthropicClient:
    def __init__(self, *, exc: Exception) -> None:
        self.messages = _RaisingMessagesAPI(exc=exc)


@pytest.mark.parametrize(
    "exc",
    [
        RateLimitError("Rate limit exceeded"),
        OverloadedError("Overloaded"),
        APITimeoutError("Timeout"),
    ],
)
def test_generate_translates_transient_sdk_errors(exc: Exception) -> None:
    """Audit-correctie §CB.1 — Anthropic SDK 429/529/timeout krijgen
    een onze eigen ``AnthropicTransientError`` zodat de caller naar de
    stub-fallback kan grijpen i.p.v. de exception door te laten lekken.
    """

    repo = _FakeBudgetRepo()
    fake_client = _RaisingAnthropicClient(exc=exc)
    provider = AnthropicExplanationProvider(
        budget_repo=repo,
        monthly_cap_eur=Decimal("50"),
        client_factory=lambda: fake_client,
    )
    with pytest.raises(AnthropicTransientError):
        provider.generate(_inputs())


def test_generate_passes_through_non_transient_errors() -> None:
    """ValueError / AttributeError etc. mogen NIET als transient
    worden behandeld — die wijzen op een echte bug en moeten naar
    boven propageren."""

    repo = _FakeBudgetRepo()
    fake_client = _RaisingAnthropicClient(exc=ValueError("malformed payload"))
    provider = AnthropicExplanationProvider(
        budget_repo=repo,
        monthly_cap_eur=Decimal("50"),
        client_factory=lambda: fake_client,
    )
    with pytest.raises(ValueError):
        provider.generate(_inputs())


def test_generate_raises_when_budget_exceeded() -> None:
    repo = _FakeBudgetRepo(monthly_total=Decimal("60"))  # > €50 cap
    fake_client = _FakeAnthropicClient(text="x")
    provider = AnthropicExplanationProvider(
        budget_repo=repo,
        monthly_cap_eur=Decimal("50"),
        client_factory=lambda: fake_client,
    )
    with pytest.raises(ClaudeAiBudgetExceededError):
        provider.generate(_inputs())
    # No audit row should have been written.
    assert repo.saved == []


def test_generate_persists_breakdown_with_cached_units() -> None:
    """A response with cache_read_input_tokens > 0 should record
    those units as cached_input_units (cheaper rate)."""

    repo = _FakeBudgetRepo()
    usage = _FakeUsage(
        input_tokens=100,
        cache_creation_input_tokens=50,
        cache_read_input_tokens=400,
        output_tokens=80,
    )
    fake_client = _FakeAnthropicClient(text="x")
    fake_client.messages._usage = usage
    provider = AnthropicExplanationProvider(
        budget_repo=repo,
        monthly_cap_eur=Decimal("50"),
        client_factory=lambda: fake_client,
    )
    provider.generate(_inputs())
    row = repo.saved[0]
    # Cache reads → cached_input_units; raw + cache creations → input_units.
    assert row.cached_input_units == 400
    assert row.input_units == 150
    assert row.output_units == 80
    assert row.cost_eur > Decimal("0")


# ---- factory gates -----------------------------------------------------


def test_factory_returns_stub_when_provider_code_is_stub() -> None:
    from portfolio_outlook_api.ai_explanation_provider import (
        StubExplanationProvider,
        build_explanation_provider,
    )
    from portfolio_outlook_api.config import Settings

    s = Settings()
    s.ai_explanation_enabled = True
    s.ai_explanation_provider_code = "stub"
    provider = build_explanation_provider(s)
    assert isinstance(provider, StubExplanationProvider)


def test_factory_unavailable_when_anthropic_key_missing() -> None:
    from portfolio_outlook_api.ai_explanation_provider import (
        ExplanationProviderUnavailable,
        build_explanation_provider,
    )
    from portfolio_outlook_api.config import Settings

    s = Settings()
    s.ai_explanation_enabled = True
    s.ai_explanation_real_client_enabled = True
    s.ai_explanation_provider_code = "anthropic_claude"
    s.claude_ai_api_key = None
    provider = build_explanation_provider(s, budget_repo=_FakeBudgetRepo())
    assert isinstance(provider, ExplanationProviderUnavailable)
    assert provider.reason == "claude_ai_api_key_missing"


def test_factory_unavailable_when_budget_repo_missing() -> None:
    from portfolio_outlook_api.ai_explanation_provider import (
        ExplanationProviderUnavailable,
        build_explanation_provider,
    )
    from portfolio_outlook_api.config import Settings

    s = Settings()
    s.ai_explanation_enabled = True
    s.ai_explanation_real_client_enabled = True
    s.ai_explanation_provider_code = "anthropic_claude"
    s.claude_ai_api_key = "sk-test"
    provider = build_explanation_provider(s, budget_repo=None)
    assert isinstance(provider, ExplanationProviderUnavailable)
    assert provider.reason == "claude_ai_budget_repo_missing"


def test_factory_returns_real_provider_when_all_gates_open() -> None:
    from portfolio_outlook_api.ai_explanation_provider import (
        build_explanation_provider,
    )
    from portfolio_outlook_api.config import Settings

    s = Settings()
    s.ai_explanation_enabled = True
    s.ai_explanation_real_client_enabled = True
    s.ai_explanation_provider_code = "anthropic_claude"
    s.claude_ai_api_key = "sk-test"
    provider = build_explanation_provider(s, budget_repo=_FakeBudgetRepo())
    assert isinstance(provider, AnthropicExplanationProvider)


# ---- prompt-as-data loader (T-047 §2) ----------------------------------


def test_loader_returns_locked_default_when_no_path() -> None:
    assert load_explanation_system_prompt(None) == SYSTEM_PROMPT_NL


def test_loader_reads_external_prompt_file(tmp_path) -> None:
    body = "Aangepaste Nederlandse system prompt voor de uitleg-assistent."
    f = tmp_path / "prompt.txt"
    f.write_text(body + "\n", encoding="utf-8")
    assert load_explanation_system_prompt(str(f)) == body


def test_loader_raises_on_missing_file(tmp_path) -> None:
    missing = tmp_path / "nope.txt"
    with pytest.raises(ExplanationPromptError):
        load_explanation_system_prompt(str(missing))


def test_loader_raises_on_empty_file(tmp_path) -> None:
    f = tmp_path / "empty.txt"
    f.write_text("   \n", encoding="utf-8")
    with pytest.raises(ExplanationPromptError):
        load_explanation_system_prompt(str(f))


def test_provider_sends_configured_system_prompt() -> None:
    custom = "Volledig aangepaste system prompt geladen uit een bestand (>40)."
    repo = _FakeBudgetRepo()
    fake_client = _FakeAnthropicClient(text="x")
    provider = AnthropicExplanationProvider(
        budget_repo=repo,
        monthly_cap_eur=Decimal("50"),
        client_factory=lambda: fake_client,
        system_prompt=custom,
    )
    provider.generate(_inputs())
    payload = fake_client.messages.last_payload
    assert payload is not None
    system_blocks = payload["system"]
    assert any(block["text"] == custom for block in system_blocks)
    assert all(block["text"] != SYSTEM_PROMPT_NL for block in system_blocks)
