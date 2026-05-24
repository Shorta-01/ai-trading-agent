"""AI explanation provider boundary (Slice 10).

This module is the boundary between the deterministic Decision Package
evidence chain and an AI model that produces a natural-language Dutch
explanation. The provider is **disabled by default**; the factory
returns ``None`` unless the runtime explicitly opts in via the gates in
``Settings``.

A ``StubExplanationProvider`` is provided for testing and for the
default "AI on, no real client" path: it produces a fully deterministic
Dutch summary by paraphrasing the Decision Package's already-persisted
``rationale_nl`` + ``explanation_nl`` + research snippet. The stub does
not invent numbers; it only echoes what the package already contains
and appends the locked risk disclaimer. The output therefore always
passes :func:`validate_explanation_output`.

Real AI providers (Anthropic, OpenAI, ...) are out of scope for this
slice; the factory returns ``None`` with a ``real_client_not_implemented``
reason for any non-stub ``ai_explanation_provider_code``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from portfolio_outlook_portfolio import LOCKED_RISK_DISCLAIMER_NL

from portfolio_outlook_api.config import Settings

STUB_PROVIDER_CODE = "stub"
STUB_MODEL_NAME = "deterministic_paraphrase"
STUB_MODEL_VERSION = "v1"


@dataclass(frozen=True)
class ExplanationProviderInputs:
    """The canonical bundle the model receives.

    ``input_text`` is the canonical input the model is fed; the
    orchestrator hashes it for the audit ledger. Providers must not
    pull additional data from the network — everything the model sees
    is in this struct.
    """

    decision_package_id: str
    decision_package_content_hash: str
    symbol: str
    risk_profile: str
    rationale_nl: str
    package_explanation_nl: str
    research_snippet_nl: str | None
    input_text: str


@dataclass(frozen=True)
class ExplanationProviderResult:
    output_text: str
    model_provider_code: str
    model_name: str
    model_version: str


class ExplanationProviderProtocol(Protocol):
    def generate(
        self, inputs: ExplanationProviderInputs
    ) -> ExplanationProviderResult: ...


class StubExplanationProvider:
    """Deterministic paraphrase provider — no AI runtime.

    The stub keeps the V1 doctrine trivially satisfied: every numeric
    token in the output already appeared in the input, the locked risk
    disclaimer is always appended, and the output is fully reproducible
    for the same inputs.
    """

    def __init__(
        self,
        *,
        model_provider_code: str = STUB_PROVIDER_CODE,
        model_name: str = STUB_MODEL_NAME,
        model_version: str = STUB_MODEL_VERSION,
    ) -> None:
        self._model_provider_code = model_provider_code
        self._model_name = model_name
        self._model_version = model_version

    def generate(
        self, inputs: ExplanationProviderInputs
    ) -> ExplanationProviderResult:
        parts: list[str] = [
            f"Samenvatting voor {inputs.symbol} (risicoprofiel: "
            f"{inputs.risk_profile}).",
            inputs.package_explanation_nl,
            inputs.rationale_nl,
        ]
        if inputs.research_snippet_nl:
            parts.append(inputs.research_snippet_nl)
        parts.append(LOCKED_RISK_DISCLAIMER_NL)
        output_text = " ".join(part.strip() for part in parts if part.strip())
        return ExplanationProviderResult(
            output_text=output_text,
            model_provider_code=self._model_provider_code,
            model_name=self._model_name,
            model_version=self._model_version,
        )


@dataclass(frozen=True)
class ExplanationProviderUnavailable:
    reason: str
    detail_nl: str


def build_explanation_provider(
    runtime_settings: Settings,
) -> ExplanationProviderProtocol | ExplanationProviderUnavailable:
    """Construct a provider, or describe why none is available.

    The factory is the single gate that decides whether an AI runtime
    is wired up. Default state: returns
    :class:`ExplanationProviderUnavailable` with reason
    ``ai_explanation_disabled``. The orchestrator treats that as a
    no-op and writes nothing.
    """

    if not runtime_settings.ai_explanation_enabled:
        return ExplanationProviderUnavailable(
            reason="ai_explanation_disabled",
            detail_nl=(
                "AI uitleg-runtime is uitgeschakeld. Stel "
                "`AI_EXPLANATION_ENABLED=true` in om een uitleg te genereren."
            ),
        )
    provider_code = (runtime_settings.ai_explanation_provider_code or "").strip().lower()
    if provider_code == STUB_PROVIDER_CODE:
        return StubExplanationProvider()
    if not runtime_settings.ai_explanation_real_client_enabled:
        return ExplanationProviderUnavailable(
            reason="real_client_not_enabled",
            detail_nl=(
                "Echte AI-client is niet ingeschakeld. Gebruik "
                "`AI_EXPLANATION_PROVIDER_CODE=stub` voor een deterministische "
                "samenvatting, of zet `AI_EXPLANATION_REAL_CLIENT_ENABLED=true` "
                "voor een ingebouwde provider."
            ),
        )
    # Real provider implementations (Anthropic / OpenAI) are out of scope
    # for Slice 10. The boundary is wired so a future slice can plug them
    # in here without changing the orchestrator.
    return ExplanationProviderUnavailable(
        reason="real_client_not_implemented",
        detail_nl=(
            f"Provider `{provider_code}` is nog niet geïmplementeerd in V1. "
            "Beschikbaar: `stub`."
        ),
    )


__all__ = [
    "STUB_PROVIDER_CODE",
    "STUB_MODEL_NAME",
    "STUB_MODEL_VERSION",
    "ExplanationProviderInputs",
    "ExplanationProviderResult",
    "ExplanationProviderProtocol",
    "ExplanationProviderUnavailable",
    "StubExplanationProvider",
    "build_explanation_provider",
]
