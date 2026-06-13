"""Operator favorites + exclusions API (V1.2 §AU / CLAUDE.md §5).

The hybrid watchlist doctrine adds two operator-maintained lists on
top of the autonomous universe scan:

* **Favorieten** — symbols the operator wants to see on the dashboard
  with live orchestrator confidence even when they don't pass the
  gates.
* **Uitsluitingen** — symbols the orchestrator must never propose.

Endpoints (all account-scoped via ``account_id`` query arg, default
matches the orchestrator's ``ibkr_account_ref`` of ``"default"``):

* ``GET /watchlist-preferences/favorieten`` — list favorites, each
  enriched with the latest orchestrator scoring verdict so the
  dashboard widget can show live confidence next to every symbol.
* ``GET /watchlist-preferences/uitsluitingen`` — list excluded
  symbols. Read-only listing for the settings page.
* ``POST /watchlist-preferences`` — add or replace one favorite or
  exclusion. Idempotent on ``(account, symbol, kind)``.
* ``DELETE /watchlist-preferences`` — remove one favorite or
  exclusion. Idempotent (404-style behaviour is avoided so the UI
  never has to special-case "already gone").

Safety: storage writes are gated by ``ensure_persistence_allowed``
inside the repository, the same boundary every other write path
uses. No safe_for_* booleans are flipped — preferences are
configuration, not decision artefacts.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ai_trading_agent_storage import (
    OrchestratorScoringVerdictRecord,
    SaveWatchlistPreferenceRequest,
    SqlAlchemyOrchestratorScoringVerdictRepository,
    SqlAlchemyWatchlistPreferenceRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    StoragePersistenceBlockedError,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ----------------------------------------------------------------------
# Response models.
# ----------------------------------------------------------------------


class FavoriteRow(BaseModel):
    watchlist_preference_id: str
    symbol: str
    note: str | None
    created_at: str
    # Latest scoring info — None means no orchestrator verdict yet.
    latest_decision: str | None = None
    latest_blocking_reason: str | None = None
    latest_summary_nl: str | None = None
    latest_generated_at: str | None = None
    # Confidence is optionally embedded inside details_json by the
    # scoring leg; surface it explicitly so the UI doesn't have to
    # parse the blob.
    latest_confidence: float | None = None


class FavoritesResponse(BaseModel):
    title_nl: str
    help_nl: str
    account_id: str
    items: list[FavoriteRow]


class ExclusionRow(BaseModel):
    watchlist_preference_id: str
    symbol: str
    note: str | None
    created_at: str


class ExclusionsResponse(BaseModel):
    title_nl: str
    help_nl: str
    account_id: str
    items: list[ExclusionRow]


class SavePreferenceRequest(BaseModel):
    account_id: str = Field(default="default")
    symbol: str
    kind: str = Field(description="favorite | excluded")
    note: str | None = None


class PreferenceMutationResponse(BaseModel):
    accepted: bool
    record_id: str | None
    explanation_nl: str


# ----------------------------------------------------------------------
# Helpers.
# ----------------------------------------------------------------------


_FAVORITES_HELP_NL = (
    "Symbolen die je extra in de gaten wilt houden. De dashboard "
    "toont elke favoriet met de meest recente orchestrator-score, "
    "ook als de gates de positie nog niet vrijgegeven hebben — zo "
    "zie je waarom een naam (nog) geen voorstel is."
)

_EXCLUSIONS_HELP_NL = (
    "Symbolen die de software nooit mag voorstellen. Een harde veto "
    "die de orchestrator vóór het scoren toepast, zodat je niet "
    "telkens dezelfde overweging hoeft weg te klikken."
)


def _raise_storage_unavailable() -> None:
    raise HTTPException(status_code=503, detail="Opslag is niet beschikbaar.")


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    assert storage.database_url is not None
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


def _normalise_symbol(raw: str) -> str:
    symbol = raw.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="symbol mag niet leeg zijn.")
    return symbol


def _normalise_kind(raw: str) -> str:
    kind = raw.strip().lower()
    if kind not in {"favorite", "excluded"}:
        raise HTTPException(
            status_code=400,
            detail="kind moet 'favorite' of 'excluded' zijn.",
        )
    return kind


def _extract_confidence(verdict: OrchestratorScoringVerdictRecord) -> float | None:
    """The scoring leg stuffs the orchestrator's confidence into
    ``details_json`` under one of a handful of keys depending on
    which doctrine version wrote the row. Try them in order; return
    ``None`` if none are present (older verdicts predate the
    confidence field entirely)."""

    blob: dict[str, Any] = verdict.details_json or {}
    for key in ("confidence", "confidence_score", "score"):
        value = blob.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


# ----------------------------------------------------------------------
# Routes.
# ----------------------------------------------------------------------


@router.get(
    "/watchlist-preferences/favorieten",
    response_model=FavoritesResponse,
)
def list_favorieten(
    account_id: str = Query("default"),
) -> FavoritesResponse:
    """Return all favorites for one account with the latest
    orchestrator verdict per symbol.

    The orchestrator writes one verdict per (account, symbol,
    forecast_id) — we want the most recent per symbol so the UI
    surfaces "what is the doctrine saying about my favorite right
    now". We do that client-side by listing all verdicts for the
    account (capped at 500) and picking the newest per symbol.
    """

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=False) as checked:
            pref_repo = SqlAlchemyWatchlistPreferenceRepository(
                checked.connection, checked.readiness
            )
            verdict_repo = SqlAlchemyOrchestratorScoringVerdictRepository(
                checked.connection, checked.readiness
            )
            favorites = pref_repo.list_for_account(
                ibkr_account_ref=account_id, kind="favorite"
            )
            verdict_listing = verdict_repo.list_verdicts_for_account(
                ibkr_account_ref=account_id, limit=500
            )
    except StorageConnectionError as exc:
        logger.warning("favorieten storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    latest_per_symbol: dict[str, OrchestratorScoringVerdictRecord] = {}
    # verdict_repo returns newest-first; keep the first hit per symbol.
    for record in verdict_listing.records:
        latest_per_symbol.setdefault(record.symbol, record)

    items: list[FavoriteRow] = []
    for pref in favorites.records:
        verdict = latest_per_symbol.get(pref.symbol)
        items.append(
            FavoriteRow(
                watchlist_preference_id=pref.watchlist_preference_id,
                symbol=pref.symbol,
                note=pref.note,
                created_at=pref.created_at.isoformat(),
                latest_decision=verdict.decision if verdict else None,
                latest_blocking_reason=(
                    verdict.blocking_reason if verdict else None
                ),
                latest_summary_nl=verdict.summary_nl if verdict else None,
                latest_generated_at=(
                    verdict.generated_at.isoformat() if verdict else None
                ),
                latest_confidence=(
                    _extract_confidence(verdict) if verdict else None
                ),
            )
        )
    return FavoritesResponse(
        title_nl="Favorieten",
        help_nl=_FAVORITES_HELP_NL,
        account_id=account_id,
        items=items,
    )


@router.get(
    "/watchlist-preferences/uitsluitingen",
    response_model=ExclusionsResponse,
)
def list_uitsluitingen(
    account_id: str = Query("default"),
) -> ExclusionsResponse:
    """Return all exclusions for one account."""

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=False) as checked:
            pref_repo = SqlAlchemyWatchlistPreferenceRepository(
                checked.connection, checked.readiness
            )
            result = pref_repo.list_for_account(
                ibkr_account_ref=account_id, kind="excluded"
            )
    except StorageConnectionError as exc:
        logger.warning("uitsluitingen storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    items = [
        ExclusionRow(
            watchlist_preference_id=pref.watchlist_preference_id,
            symbol=pref.symbol,
            note=pref.note,
            created_at=pref.created_at.isoformat(),
        )
        for pref in result.records
    ]
    return ExclusionsResponse(
        title_nl="Uitsluitingen",
        help_nl=_EXCLUSIONS_HELP_NL,
        account_id=account_id,
        items=items,
    )


@router.post(
    "/watchlist-preferences",
    response_model=PreferenceMutationResponse,
    status_code=201,
)
def save_preference(
    payload: SavePreferenceRequest,
) -> PreferenceMutationResponse:
    """Add or replace one preference. Idempotent on ``(account,
    symbol, kind)`` — re-posting the same triple updates the ``note``
    and creation timestamp without raising."""

    symbol = _normalise_symbol(payload.symbol)
    kind = _normalise_kind(payload.kind)
    request = SaveWatchlistPreferenceRequest(
        watchlist_preference_id=str(uuid4()),
        ibkr_account_ref=payload.account_id,
        symbol=symbol,
        kind=kind,
        note=payload.note,
        created_at=datetime.now(UTC),
    )

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyWatchlistPreferenceRepository(
                checked.connection, checked.readiness
            )
            result = repo.upsert_preference(request)
            checked.connection.commit()
    except StoragePersistenceBlockedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageConnectionError as exc:
        logger.warning("watchlist-preference upsert storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return PreferenceMutationResponse(
        accepted=result.accepted,
        record_id=result.record_id,
        explanation_nl=result.explanation_nl,
    )


@router.delete(
    "/watchlist-preferences",
    response_model=PreferenceMutationResponse,
)
def delete_preference(
    account_id: str = Query("default"),
    symbol: str = Query(...),
    kind: str = Query(...),
) -> PreferenceMutationResponse:
    """Remove one preference. Idempotent — deleting a non-existent
    row returns success because the desired state (gone) holds."""

    symbol_normalised = _normalise_symbol(symbol)
    kind_normalised = _normalise_kind(kind)

    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyWatchlistPreferenceRepository(
                checked.connection, checked.readiness
            )
            result = repo.delete_preference(
                ibkr_account_ref=account_id,
                symbol=symbol_normalised,
                kind=kind_normalised,
            )
            checked.connection.commit()
    except StoragePersistenceBlockedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageConnectionError as exc:
        logger.warning("watchlist-preference delete storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    return PreferenceMutationResponse(
        accepted=result.accepted,
        record_id=result.record_id,
        explanation_nl=result.explanation_nl,
    )


__all__ = ["router"]
