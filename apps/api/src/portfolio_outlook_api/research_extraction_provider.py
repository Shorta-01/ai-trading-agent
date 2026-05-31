"""AI research-extraction provider boundary.

Companion to :mod:`ai_explanation_provider`. The explanation provider
paraphrases an already-persisted Decision Package; this one extracts
structured facts (a list of Dutch quotes / short paraphrases) from a
research source document.

Same factory pattern: ``build_research_extraction_provider`` returns a
``ResearchExtractionProviderProtocol`` OR a
``ResearchExtractionProviderUnavailable`` with a stable reason. The
default state is ``research_extraction_disabled`` — every call site
falls through gracefully when the provider isn't wired up.

PR 3 ships the stub provider only; a Claude-backed implementation is a
small follow-up that swaps the factory's ``provider_code`` branch
without touching the orchestrator or the guard.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from portfolio_outlook_api.config import Settings

STUB_PROVIDER_CODE = "stub"
STUB_MODEL_NAME = "deterministic_first_sentences"
STUB_MODEL_VERSION = "v1"


@dataclass(frozen=True)
class ResearchExtractionProviderInputs:
    """The canonical input bundle.

    ``input_text`` is the full source document text the provider sees.
    Providers must NOT pull any additional content from the network —
    every byte the model reads is in this struct, so the audit hash
    over ``input_text`` is the complete evidence record.
    """

    library_source_id: str
    source_text_hash: str
    asset_symbol: str | None
    source_type: str | None
    detected_language: str | None
    max_facts: int
    max_fact_chars: int
    input_text: str


@dataclass(frozen=True)
class ResearchExtractionProviderResult:
    """One batch of extracted facts plus model attribution."""

    extracted_facts: tuple[str, ...]
    model_provider_code: str
    model_name: str
    model_version: str


class ResearchExtractionProviderProtocol(Protocol):
    def extract(
        self, inputs: ResearchExtractionProviderInputs
    ) -> ResearchExtractionProviderResult: ...


@dataclass(frozen=True)
class ResearchExtractionProviderUnavailable:
    reason: str
    detail_nl: str


class StubResearchExtractionProvider:
    """Deterministic baseline — no AI runtime.

    Picks the first ``max_facts`` non-empty source lines as "facts"
    (capped at ``max_fact_chars`` each). Every output is by construction
    a verbatim substring of the source, so the hallucination guard
    always passes — useful for end-to-end pipeline tests + as a sane
    fallback when Claude is disabled.
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

    def extract(
        self, inputs: ResearchExtractionProviderInputs
    ) -> ResearchExtractionProviderResult:
        non_empty_lines = [
            line.strip()
            for line in inputs.input_text.splitlines()
            if line and line.strip()
        ]
        truncated = [
            line[: inputs.max_fact_chars]
            for line in non_empty_lines[: max(1, inputs.max_facts)]
        ]
        return ResearchExtractionProviderResult(
            extracted_facts=tuple(truncated),
            model_provider_code=self._model_provider_code,
            model_name=self._model_name,
            model_version=self._model_version,
        )


def build_research_extraction_provider(
    runtime_settings: Settings,
) -> ResearchExtractionProviderProtocol | ResearchExtractionProviderUnavailable:
    """Construct an extraction provider, or describe why none is available.

    Default state: returns ``ResearchExtractionProviderUnavailable``
    with reason ``research_extraction_disabled``. The orchestrator
    treats that as a no-op.

    PR 3 wires only the ``stub`` branch; a real Claude provider is a
    follow-up — it'll plug in here as a new ``provider_code`` arm and
    inherit the same hallucination guard via the orchestrator.
    """

    if not runtime_settings.research_ai_extraction_enabled:
        return ResearchExtractionProviderUnavailable(
            reason="research_extraction_disabled",
            detail_nl=(
                "AI-extractie van onderzoeksbronnen is uitgeschakeld. "
                "Zet `RESEARCH_AI_EXTRACTION_ENABLED=true` om de "
                "extractie te activeren."
            ),
        )
    provider_code = (
        runtime_settings.research_ai_extraction_provider_code or ""
    ).strip().lower()
    if provider_code == STUB_PROVIDER_CODE:
        return StubResearchExtractionProvider()
    # Real-provider arms (Anthropic, ...) land in a follow-up PR. Until
    # then any non-stub code falls back to "unavailable" so the operator
    # sees a clear reason instead of a silent stub swap.
    return ResearchExtractionProviderUnavailable(
        reason="real_client_not_implemented",
        detail_nl=(
            f"Provider `{provider_code}` is nog niet beschikbaar voor "
            "AI-extractie. Gebruik `stub` zolang de Claude-implementatie "
            "wordt uitgerold."
        ),
    )


__all__ = [
    "STUB_MODEL_NAME",
    "STUB_MODEL_VERSION",
    "STUB_PROVIDER_CODE",
    "ResearchExtractionProviderInputs",
    "ResearchExtractionProviderProtocol",
    "ResearchExtractionProviderResult",
    "ResearchExtractionProviderUnavailable",
    "StubResearchExtractionProvider",
    "build_research_extraction_provider",
]
