"""End-of-day digest endpoints — ``GET /digests/today``.

Surfaces the latest ``DailyDigestRecord`` produced by the worker's
``market_close`` fire. The dashboard renders this as the new
``/digest`` page: NAV change, top winners/losers, suggestion counts,
action-draft activity, plus the operator-facing alert list.

If multiple markets fired today (e.g. EU + US operator), this endpoint
returns the most recent digest per ``generated_at``. A future
``/digests/by-date/{date}`` endpoint can return the per-market split
when needed.
"""

from __future__ import annotations

import logging
from typing import Any

from ai_trading_agent_storage import (
    SqlAlchemyDailyDigestRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class DigestAlert(BaseModel):
    kind: str
    severity_nl: str
    title_nl: str
    body_nl: str
    reference_kind: str | None
    reference_id: str | None


class DigestTodayResponse(BaseModel):
    status: str
    status_nl: str
    help_nl: str
    generated_at: str | None
    briefing_date: str | None
    market_code: str | None
    nav_summary: dict[str, Any]
    positions_summary: dict[str, Any]
    suggestions_summary: dict[str, Any]
    action_drafts_summary: dict[str, Any]
    alerts: list[DigestAlert]
    safe_for_orders: bool


_HELP_NL = (
    "Einde-dag samenvatting van vandaag: NAV-verandering, top-bewegers, "
    "suggestie-tellingen en action-draft activiteit. Wordt automatisch "
    "berekend op elke ``market_close`` fire van een gevolgde markt — "
    "morgenochtend is er een verse digest beschikbaar."
)


def _empty(status: str, status_nl: str) -> DigestTodayResponse:
    return DigestTodayResponse(
        status=status,
        status_nl=status_nl,
        help_nl=_HELP_NL,
        generated_at=None,
        briefing_date=None,
        market_code=None,
        nav_summary={},
        positions_summary={},
        suggestions_summary={},
        action_drafts_summary={},
        alerts=[],
        safe_for_orders=False,
    )


@router.get("/digests/today", response_model=DigestTodayResponse)
def get_digest_today() -> DigestTodayResponse:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty("not_configured", "Opslag niet geconfigureerd")

    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            if latest_run is None:
                return _empty(
                    "no_ibkr_sync_run",
                    "Geen IBKR-sync gevonden",
                )
            # Position snapshots carry ``account_ref`` (e.g. DU1234567);
            # the digest is per-account, so we look up the latest
            # snapshot's account before fetching the digest.
            positions = list(
                ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id)
            )
            account_ref = next(
                (p.account_ref for p in positions if p.account_ref), None
            )
            if account_ref is None:
                return _empty(
                    "no_account",
                    "Geen IBKR-account herkend",
                )
            digest_repo = SqlAlchemyDailyDigestRepository(
                checked.connection, checked.readiness
            )
            digest_result = digest_repo.get_latest_daily_digest_for_account(
                account_ref
            )
            if not digest_result.found or digest_result.record is None:
                return _empty(
                    "no_digest",
                    "Nog geen einde-dag digest beschikbaar",
                )
            record = digest_result.record
    except StorageConnectionError as exc:
        logger.warning("digest-today storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    return DigestTodayResponse(
        status=record.status,
        status_nl=(
            "Einde-dag digest beschikbaar"
            if record.status == "ready"
            else "Digest gedeeltelijk — niet alle gegevens waren klaar"
        ),
        help_nl=_HELP_NL,
        generated_at=record.generated_at.isoformat(),
        briefing_date=record.briefing_date.isoformat(),
        market_code=record.market_code,
        nav_summary=dict(record.nav_summary_json),
        positions_summary=dict(record.positions_summary_json),
        suggestions_summary=dict(record.suggestions_summary_json),
        action_drafts_summary=dict(record.action_drafts_summary_json),
        alerts=[DigestAlert.model_validate(a) for a in record.alerts_json],
        safe_for_orders=False,
    )


__all__ = [
    "DigestAlert",
    "DigestTodayResponse",
    "router",
]
