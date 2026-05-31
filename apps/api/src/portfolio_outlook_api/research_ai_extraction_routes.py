"""AI extraction endpoint for research source documents.

``POST /research/sources/{library_source_id}/ai-extract`` — reads the
plain-text extraction record produced by the existing
``/extract-text`` route, asks Claude (or the stub) to pull a list of
Dutch facts / quotes from it, and runs every fact through the
substring-based hallucination guard. Blocked / failed batches are
surfaced in the response (and *never* persisted) so the operator sees
the safety verdict instead of silent AI output.

This PR ships the safety pipeline + endpoint with a stub provider. A
follow-up wires the real Claude provider into the same factory arm
without touching the orchestrator or the guard. Until persistence is
added (separate, larger PR for the ``research_extracted_facts`` table)
the endpoint is read-only — operators trigger it on demand and the
result lives only in the HTTP response.
"""

from __future__ import annotations

import logging
from hashlib import sha256
from pathlib import Path

from ai_trading_agent_storage import (
    SqlAlchemyResearchSourceArchiveRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from portfolio_outlook_portfolio import (
    EXTRACTION_STATUS_GENERATED,
    validate_extracted_facts,
)
from pydantic import BaseModel

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.research_extraction_provider import (
    ResearchExtractionProviderInputs,
    ResearchExtractionProviderUnavailable,
    build_research_extraction_provider,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class AiExtractedFact(BaseModel):
    fact_text_nl: str
    is_grounded: bool


class ResearchAiExtractionResponse(BaseModel):
    status: str
    status_nl: str
    help_nl: str
    library_source_id: str
    source_text_hash: str | None
    model_provider_code: str | None
    model_name: str | None
    blocking_reason: str | None
    hallucinated_fact_indices: list[int]
    facts: list[AiExtractedFact]
    safe_for_orders: bool
    safe_for_suggestions: bool


_HELP_NL = (
    "AI haalt korte Nederlandse feiten / citaten uit de geëxtraheerde "
    "tekst van een onderzoeksbron. Elke feit wordt gecontroleerd op een "
    "verbatim-substring match (of een paraphrase waar alle getallen uit "
    "de bron komen) — gehallucineerde feiten blokkeren het hele batch. "
    "De resultaten zijn nooit veilig voor orders of suggesties; ze "
    "dienen alleen om de operator te helpen sneller relevante stukken "
    "in de bron te vinden."
)


def _empty(status: str, status_nl: str, library_source_id: str) -> ResearchAiExtractionResponse:
    return ResearchAiExtractionResponse(
        status=status,
        status_nl=status_nl,
        help_nl=_HELP_NL,
        library_source_id=library_source_id,
        source_text_hash=None,
        model_provider_code=None,
        model_name=None,
        blocking_reason=None,
        hallucinated_fact_indices=[],
        facts=[],
        safe_for_orders=False,
        safe_for_suggestions=False,
    )


def _read_extracted_text_file(storage_uri: str) -> str:
    """Read the worker-archived plain text from disk.

    The existing extraction route writes ``file://...`` URIs into the
    record. We resolve under the configured extracted-text root so a
    crafted URI can't escape via ``..`` — the same defence the
    extractor itself applies on the write path.
    """

    root = Path(settings.research_extraction.extracted_text_archive_dir).resolve()
    path = Path(storage_uri.removeprefix("file://")).resolve()
    if root not in path.parents and root != path.parent:
        raise HTTPException(
            status_code=400,
            detail="Geëxtraheerde tekst ligt buiten het toegestane archiefpad.",
        )
    if not path.exists() or not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Geëxtraheerd tekstbestand niet gevonden op schijf.",
        )
    return path.read_text(encoding="utf-8")


@router.post(
    "/research/sources/{library_source_id}/ai-extract",
    response_model=ResearchAiExtractionResponse,
)
def run_research_ai_extraction(
    library_source_id: str,
) -> ResearchAiExtractionResponse:
    if not settings.research_ai_extraction_enabled:
        return _empty(
            "disabled",
            "AI-extractie van onderzoeksbronnen is uitgeschakeld.",
            library_source_id,
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty(
            "not_configured",
            "Opslag is niet beschikbaar; AI-extractie kan geen brontekst lezen.",
            library_source_id,
        )

    try:
        storage_provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with storage_provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyResearchSourceArchiveRepository(
                checked.connection, checked.readiness
            )
            source = repo.get_research_source(library_source_id)
            if source is None:
                raise HTTPException(
                    status_code=404, detail="Onderzoeksbron niet gevonden."
                )
            extracted = repo.get_latest_extracted_text_for_source(library_source_id)
    except StorageConnectionError as exc:
        logger.warning("research ai-extract storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    if extracted is None or not extracted.extracted_text_storage_uri:
        return _empty(
            "no_extracted_text",
            "Er is nog geen plain-text extractie voor deze bron. Voer "
            "eerst /extract-text uit.",
            library_source_id,
        )

    source_text = _read_extracted_text_file(extracted.extracted_text_storage_uri)
    source_text_hash = sha256(source_text.encode("utf-8")).hexdigest()

    provider = build_research_extraction_provider(settings)
    if isinstance(provider, ResearchExtractionProviderUnavailable):
        response = _empty(
            "provider_unavailable", provider.detail_nl, library_source_id
        )
        return response.model_copy(
            update={
                "source_text_hash": source_text_hash,
                "blocking_reason": provider.reason,
            }
        )

    provider_inputs = ResearchExtractionProviderInputs(
        library_source_id=library_source_id,
        source_text_hash=source_text_hash,
        asset_symbol=source.asset_symbol,
        source_type=source.source_type,
        detected_language=extracted.detected_language,
        max_facts=settings.research_ai_extraction_max_facts,
        max_fact_chars=settings.research_ai_extraction_max_fact_chars,
        input_text=source_text,
    )
    try:
        provider_result = provider.extract(provider_inputs)
    except Exception as exc:  # noqa: BLE001 — boundary catch
        logger.warning("research extraction provider failed: %s", exc)
        response = _empty(
            "failed",
            "AI-extractie mislukte; geen feiten beschikbaar.",
            library_source_id,
        )
        return response.model_copy(
            update={
                "source_text_hash": source_text_hash,
                "blocking_reason": "provider_error",
            }
        )

    validation = validate_extracted_facts(
        extracted_facts=list(provider_result.extracted_facts),
        source_text=source_text,
        max_facts=settings.research_ai_extraction_max_facts,
        max_fact_chars=settings.research_ai_extraction_max_fact_chars,
    )

    hallucinated = set(validation.hallucinated_fact_indices)
    facts = [
        AiExtractedFact(
            fact_text_nl=fact,
            is_grounded=(idx not in hallucinated),
        )
        for idx, fact in enumerate(provider_result.extracted_facts)
    ]

    if validation.status == EXTRACTION_STATUS_GENERATED:
        status_nl = "AI-extractie geslaagd. Feiten zijn nog niet bruikbaar voor suggesties."
    else:
        status_nl = (
            "AI-extractie geblokkeerd door safety-controle "
            f"({validation.blocking_reason})."
        )

    return ResearchAiExtractionResponse(
        status=validation.status,
        status_nl=status_nl,
        help_nl=_HELP_NL,
        library_source_id=library_source_id,
        source_text_hash=source_text_hash,
        model_provider_code=provider_result.model_provider_code,
        model_name=provider_result.model_name,
        blocking_reason=validation.blocking_reason,
        hallucinated_fact_indices=list(validation.hallucinated_fact_indices),
        facts=facts,
        # Mirror the explanation pipeline's locked false flags. AI
        # extraction is research-aid only; the operator decides which
        # facts to copy into a Decision Package, and nothing here is
        # ever auto-promoted.
        safe_for_orders=False,
        safe_for_suggestions=False,
    )


__all__ = [
    "AiExtractedFact",
    "ResearchAiExtractionResponse",
    "router",
]
