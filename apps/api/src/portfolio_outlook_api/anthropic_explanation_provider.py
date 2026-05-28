"""Real Anthropic Claude explanation provider (V1.1 Slice 29).

Replaces the Slice 10 stub for the Decision Package narrative path.
Implements :class:`ExplanationProviderProtocol` so the orchestrator
swap is transparent. Locked by §22.2 of the V1.1 doctrine:

* **Budget cap** — checks the monthly running total before each call
  via :func:`assert_budget_available`. Once the cap is hit the
  provider raises :class:`ClaudeAiBudgetExceededError` and the
  factory falls back to the stub for the rest of the month.
* **Prompt caching** — the locked Dutch system prompt + the legal
  disclaimer are sent with an ephemeral cache breakpoint so the
  per-call cost stays at the cache-hit rate after the first call
  of the day. The Anthropic SDK exposes cache control via
  ``content[*].cache_control = {"type": "ephemeral"}``.
* **No-network in tests** — the constructor takes an injectable
  ``client_factory`` so tests can hand in a fake Anthropic-like
  client without ever opening a socket.
* **Hallucinated-number guard** — the response goes through the
  same Slice-10 validation pass (``validate_explanation_output``);
  any number not in the source Decision Package fails the call.

V1.1 §22.2 lock: this provider is **only invoked by the daily
morning chain** — no on-demand UI path. The factory still respects
the existing Slice-10 gate
(`ai_explanation_real_client_enabled=true`) plus the new
`claude_ai_api_key` requirement.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from portfolio_outlook_portfolio import LOCKED_RISK_DISCLAIMER_NL

from portfolio_outlook_api.ai_explanation_provider import (
    ExplanationProviderInputs,
    ExplanationProviderResult,
)
from portfolio_outlook_api.claude_ai_budget import (
    CallCostBreakdown,
    ClaudeAiBudgetExceededError,
    assert_budget_available,
    compute_cost_eur,
    persist_call_cost,
)

PROVIDER_CODE = "anthropic_claude"
DEFAULT_MODEL_NAME = "claude-haiku-4-5-20251001"

# Locked Dutch system prompt — the in-code default used when no external
# prompt file is configured.
SYSTEM_PROMPT_NL = (
    "Je bent een paraphrase-assistent voor een Nederlandstalig "
    "trading-dashboard. Vat het Decision Package samen in twee tot drie "
    "zinnen. Bevat de samenvatting geen nieuwe getallen die niet in de "
    "input voorkomen. Geen advies. Geen oordeel over koersrichting. "
    "Sluit altijd af met de wettelijke disclaimer die in de input wordt "
    "meegegeven."
)

# A configured prompt file must carry at least this many characters — guards
# against an empty/truncated file silently degrading the explanation voice.
_MIN_PROMPT_CHARS = 40


class ExplanationPromptError(ValueError):
    """Raised when a configured explanation-prompt file is missing or empty."""


@lru_cache(maxsize=8)
def load_explanation_system_prompt(path: str | None) -> str:
    """Resolve the Dutch explanation system prompt (intent ai-usage.md §2
    Layer 1: prompt-as-data).

    With no ``path`` configured, returns the locked in-code default
    (:data:`SYSTEM_PROMPT_NL`) — behaviour is unchanged. When
    ``AI_EXPLANATION_PROMPT_PATH`` is set, the prompt is loaded from that file
    so operators can edit the voice without a code change. A missing or empty
    file raises :class:`ExplanationPromptError` rather than silently falling
    back — a misconfigured deployment fails loudly.
    """

    if path is None:
        return SYSTEM_PROMPT_NL
    try:
        text = Path(path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ExplanationPromptError(
            f"AI_EXPLANATION_PROMPT_PATH={path!r} kon niet worden gelezen: {exc}"
        ) from exc
    if len(text) < _MIN_PROMPT_CHARS:
        raise ExplanationPromptError(
            f"AI_EXPLANATION_PROMPT_PATH={path!r} is leeg of te kort "
            f"(minimaal {_MIN_PROMPT_CHARS} tekens vereist)."
        )
    return text


class _BudgetRepoProtocol(Protocol):
    def monthly_total_eur(self, budget_month: str) -> Decimal: ...

    def save_usage(self, record: Any) -> object: ...


class _AnthropicMessageProtocol(Protocol):
    """Minimal protocol the injected client must implement.

    Mirrors the shape returned by ``anthropic.Anthropic().messages.create``.
    Tests inject a fake that returns a value with this shape; production
    uses the real Anthropic SDK.
    """

    content: list[Any]
    usage: Any
    model: str


class _AnthropicMessagesAPI(Protocol):
    def create(self, **kwargs: Any) -> _AnthropicMessageProtocol: ...


class _AnthropicClientProtocol(Protocol):
    messages: _AnthropicMessagesAPI


@dataclass(frozen=True)
class _Usage:
    input_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int


def _extract_usage(usage: Any) -> _Usage:
    """Read the token counts off the Anthropic SDK ``Usage`` object.

    The SDK exposes ``input_tokens``, ``output_tokens``,
    ``cache_creation_input_tokens`` and ``cache_read_input_tokens``.
    We treat cache reads as the "cached" units (cheaper) and cache
    creations as regular input. Falls back to zero when a field
    isn't present so the contract works with both real + fake clients.
    """

    return _Usage(
        input_tokens=int(getattr(usage, "input_tokens", 0)),
        cache_creation_input_tokens=int(
            getattr(usage, "cache_creation_input_tokens", 0)
        ),
        cache_read_input_tokens=int(
            getattr(usage, "cache_read_input_tokens", 0)
        ),
        output_tokens=int(getattr(usage, "output_tokens", 0)),
    )


def _extract_output_text(message: _AnthropicMessageProtocol) -> str:
    """Concatenate the assistant-side text blocks from an Anthropic
    ``Message``. The Anthropic SDK returns a list of typed content
    blocks; we only care about the ``text`` kind."""

    parts: list[str] = []
    for block in message.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text))
    return "\n".join(parts).strip()


def _build_messages_payload(
    *,
    inputs: ExplanationProviderInputs,
    model_name: str,
    max_output_chars: int,
    system_prompt: str,
) -> dict[str, Any]:
    """Construct the Anthropic messages-create payload with the
    locked system prompt cached and the input-text payload sent
    fresh per call."""

    # System prompt + legal disclaimer share one cache breakpoint —
    # they're stable across all morning-chain calls.
    system_blocks = [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": LOCKED_RISK_DISCLAIMER_NL,
            "cache_control": {"type": "ephemeral"},
        },
    ]
    user_payload = (
        f"Symbol: {inputs.symbol}\n"
        f"Risicoprofiel: {inputs.risk_profile}\n\n"
        f"Decision Package rationale:\n{inputs.rationale_nl}\n\n"
        f"Decision Package uitleg:\n{inputs.package_explanation_nl}\n\n"
    )
    if inputs.research_snippet_nl:
        user_payload += f"Research evidence:\n{inputs.research_snippet_nl}\n\n"
    user_payload += (
        f"Input-hash (audit): {inputs.decision_package_content_hash}\n"
    )

    # Output token cap derived from the operator's max-chars setting:
    # ~4 chars per token is a reasonable upper-bound estimate.
    max_tokens = max(64, max_output_chars // 4)
    return {
        "model": model_name,
        "max_tokens": max_tokens,
        "system": system_blocks,
        "messages": [{"role": "user", "content": user_payload}],
    }


class AnthropicExplanationProvider:
    """V1.1 §22.2 real Claude explanation provider.

    Implements :class:`ExplanationProviderProtocol`. The constructor
    takes the Anthropic ``client_factory`` so tests inject fakes; the
    factory call is deferred until :meth:`generate` runs so the
    no-network constructor is cheap.
    """

    def __init__(
        self,
        *,
        budget_repo: _BudgetRepoProtocol,
        monthly_cap_eur: Decimal,
        max_output_chars: int = 2000,
        model_name: str = DEFAULT_MODEL_NAME,
        client_factory: Callable[[], _AnthropicClientProtocol] | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._budget_repo = budget_repo
        self._monthly_cap_eur = monthly_cap_eur
        self._max_output_chars = max_output_chars
        self._model_name = model_name
        self._client_factory = client_factory
        self._system_prompt = system_prompt or SYSTEM_PROMPT_NL

    @property
    def model_name(self) -> str:
        return self._model_name

    def _build_client(self) -> _AnthropicClientProtocol:
        if self._client_factory is not None:
            return self._client_factory()
        # Lazy import so the module stays loadable when the SDK
        # isn't installed (e.g. in a stub-only deployment). The real
        # ``Anthropic`` client satisfies the protocol structurally
        # but mypy can't prove that without a typing.cast.
        from typing import cast

        from anthropic import Anthropic

        return cast(_AnthropicClientProtocol, Anthropic())

    def generate(
        self, inputs: ExplanationProviderInputs
    ) -> ExplanationProviderResult:
        # Budget gate — raises if the monthly cap is hit so the
        # orchestrator can fall back to the stub.
        assert_budget_available(
            repo=self._budget_repo, monthly_cap_eur=self._monthly_cap_eur
        )

        payload = _build_messages_payload(
            inputs=inputs,
            model_name=self._model_name,
            max_output_chars=self._max_output_chars,
            system_prompt=self._system_prompt,
        )
        client = self._build_client()
        message = client.messages.create(**payload)
        usage = _extract_usage(message.usage)
        # Cache reads (cheap) count as cached_input_units; cache
        # creations + raw input count as input_units (full price).
        breakdown = CallCostBreakdown(
            input_units=usage.input_tokens + usage.cache_creation_input_tokens,
            cached_input_units=usage.cache_read_input_tokens,
            output_units=usage.output_tokens,
            cost_eur=compute_cost_eur(
                input_units=usage.input_tokens + usage.cache_creation_input_tokens,
                cached_input_units=usage.cache_read_input_tokens,
                output_units=usage.output_tokens,
            ),
        )
        persist_call_cost(
            repo=self._budget_repo,
            provider_code=PROVIDER_CODE,
            model_name=self._model_name,
            call_kind="explanation",
            breakdown=breakdown,
            explanation_nl=(
                f"Anthropic Claude call voor Decision Package "
                f"{inputs.decision_package_id} ({inputs.symbol}); "
                f"€{breakdown.cost_eur:.4f}."
            ),
        )

        output_text = _extract_output_text(message)
        return ExplanationProviderResult(
            output_text=output_text,
            model_provider_code=PROVIDER_CODE,
            model_name=getattr(message, "model", self._model_name),
            model_version="v1.1-anthropic-2026-05",
        )


__all__ = [
    "DEFAULT_MODEL_NAME",
    "PROVIDER_CODE",
    "SYSTEM_PROMPT_NL",
    "AnthropicExplanationProvider",
    "ClaudeAiBudgetExceededError",
    "ExplanationPromptError",
    "load_explanation_system_prompt",
]
