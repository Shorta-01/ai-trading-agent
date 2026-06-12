"""Orchestrator scoring verdicts endpoints (V1.2 §AD).

Surfaces the rows the morning-chain leg writes to
``orchestrator_scoring_verdicts``. Two routes:

* ``GET /orchestrator-verdicts/today`` — summary counts per
  decision code. Powers the dashboard's "doctrine output today"
  metric card.
* ``GET /orchestrator-verdicts`` — paginated list of recent
  verdicts. Powers the operator UI's verdicts page.

Both endpoints are read-only and never raise except on the
opslag-niet-beschikbaar boundary (503).
"""

from __future__ import annotations

import logging
from typing import Any

from ai_trading_agent_storage import (
    SqlAlchemyOrchestratorScoringVerdictRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class VerdictRow(BaseModel):
    verdict_id: str
    symbol: str
    ibkr_conid: int | None
    forecast_id: str | None
    generated_at: str
    decision: str
    blocking_reason: str | None
    summary_nl: str
    details_json: dict[str, Any]


class VerdictsListResponse(BaseModel):
    title_nl: str
    help_nl: str
    items: list[VerdictRow]


class VerdictsSummaryResponse(BaseModel):
    title_nl: str
    help_nl: str
    total: int
    by_decision: dict[str, int]
    latest_generated_at: str | None


_LIST_HELP_NL = (
    "Verdicts van de profit-harvest orchestrator: per kandidaat "
    "één regel met de beslissing (suggest of skip_*), de blokkering-"
    "reden en een Nederlandse uitleg. Wordt geschreven door de "
    "morning-chain wanneer ``orchestrator_scoring_enabled`` aan staat."
)

_SUMMARY_HELP_NL = (
    "Telling van vandaag's verdicts per beslissing. Geeft je in één "
    "oogopslag hoe de doctrine de universe filtert."
)


def _account_ref_or_default() -> str:
    """Resolve the IBKR account ref the leg writes verdicts for.

    Mirrors `orchestrator_scoring_leg.build_real_orchestrator_scoring_leg`
    which uses ``ibkr_account_ref="default"`` by default. Future slice
    pulls this from runtime config; for now we accept the default
    string so the endpoints work without extra config wiring.
    """

    return "default"


def _empty_list() -> VerdictsListResponse:
    return VerdictsListResponse(
        title_nl="Orchestrator verdicts",
        help_nl=_LIST_HELP_NL,
        items=[],
    )


def _empty_summary() -> VerdictsSummaryResponse:
    return VerdictsSummaryResponse(
        title_nl="Doctrine output vandaag",
        help_nl=_SUMMARY_HELP_NL,
        total=0,
        by_decision={},
        latest_generated_at=None,
    )


@router.get("/orchestrator-verdicts/today", response_model=VerdictsSummaryResponse)
def get_orchestrator_verdicts_summary() -> VerdictsSummaryResponse:
    """Aggregate counts of the most recent verdicts per decision code.

    "Most recent" = the verdicts written at the latest
    ``generated_at`` timestamp. The morning-chain leg writes one
    burst per fire, so this surfaces "what did today's run produce".
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty_summary()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyOrchestratorScoringVerdictRepository(
                checked.connection, checked.readiness
            )
            result = repo.list_verdicts_for_account(
                ibkr_account_ref=_account_ref_or_default(), limit=500
            )
    except StorageConnectionError as exc:
        logger.warning("verdicts-summary storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    if not result.records:
        return _empty_summary()

    # Filter to the latest batch: same ``generated_at`` (within a
    # minute, in case of clock-skew on bulk writes).
    latest_ts = result.records[0].generated_at
    threshold = latest_ts.timestamp() - 60.0
    in_latest = [
        record
        for record in result.records
        if record.generated_at.timestamp() >= threshold
    ]
    by_decision: dict[str, int] = {}
    for record in in_latest:
        by_decision[record.decision] = by_decision.get(record.decision, 0) + 1
    return VerdictsSummaryResponse(
        title_nl="Doctrine output vandaag",
        help_nl=_SUMMARY_HELP_NL,
        total=len(in_latest),
        by_decision=by_decision,
        latest_generated_at=latest_ts.isoformat(),
    )


@router.get("/orchestrator-verdicts", response_model=VerdictsListResponse)
def list_orchestrator_verdicts(limit: int = 100) -> VerdictsListResponse:
    """Return the most-recent verdicts, newest first.

    Default ``limit`` is 100; the repo caps at storage-level.
    """

    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit moet > 0 zijn")
    if limit > 500:
        limit = 500

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty_list()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyOrchestratorScoringVerdictRepository(
                checked.connection, checked.readiness
            )
            result = repo.list_verdicts_for_account(
                ibkr_account_ref=_account_ref_or_default(), limit=limit
            )
    except StorageConnectionError as exc:
        logger.warning("verdicts-list storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    items = [
        VerdictRow(
            verdict_id=record.verdict_id,
            symbol=record.symbol,
            ibkr_conid=record.ibkr_conid,
            forecast_id=record.forecast_id,
            generated_at=record.generated_at.isoformat(),
            decision=record.decision,
            blocking_reason=record.blocking_reason,
            summary_nl=record.summary_nl,
            details_json=record.details_json,
        )
        for record in result.records
    ]
    return VerdictsListResponse(
        title_nl="Orchestrator verdicts",
        help_nl=_LIST_HELP_NL,
        items=items,
    )


__all__ = ["router"]
