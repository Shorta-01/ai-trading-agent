"""Pauze-modus endpoints (V1.2 §AY / CLAUDE.md §11).

CLAUDE.md §11 wil één knop op het dashboard:

* ``GET /pauze`` — huidige toestand (paused yes/no + sinds).
* ``POST /pauze`` — pauzeer de software. Idempotent: een tweede call
  doet niets meer.
* ``POST /pauze/hervat`` — hervat de software. Idempotent.

De morning-chain leest deze vlag bij elke run en slaat de BUY-leg
over wanneer ``software_paused = True``. SELL-monitoring blijft
draaien — operator wil geen +4 % hit missen tijdens een pauze.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from ai_trading_agent_storage import (
    RuntimeConfigRecord,
    SqlAlchemyRuntimeConfigRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    StoragePersistenceBlockedError,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class PauzeStatusResponse(BaseModel):
    title_nl: str
    help_nl: str
    paused: bool
    paused_at: str | None
    summary_nl: str


_HELP_NL = (
    "Pauze-modus. Bij pauzeren stopt de morning-chain de BUY-leg, "
    "maar SELL-monitoring blijft draaien zodat je geen +4 % "
    "winstmoment mist. Bestaande posities en orders blijven "
    "onaangeroerd; de operator moet pas een individuele actie "
    "nemen om iets te sluiten."
)


def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        )
    assert storage.database_url is not None
    return StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )


def _default_record(now: datetime) -> RuntimeConfigRecord:
    """Build a no-op default row when none exists yet.

    The pauze endpoint may run before any settings have been written
    by the operator. We synthesize the minimal record so the upsert
    path doesn't crash on missing IBKR / AI defaults — every existing
    column gets a safe null/false default that matches the schema.
    """

    return RuntimeConfigRecord(
        config_id="default",
        ibkr_enabled=False,
        ibkr_account_id=None,
        ibkr_host=None,
        ibkr_port=None,
        ibkr_client_id=None,
        ai_explanation_enabled=False,
        claude_ai_explanation_model=None,
        claude_ai_budget_monthly_eur=None,
        claude_ai_api_key=None,
        updated_at=now,
    )


def _summary(paused: bool, paused_at: datetime | None) -> str:
    if not paused:
        return "Software draait. Klik 'Pauzeer' om tijdelijk te stoppen."
    if paused_at is not None:
        return (
            f"Software gepauzeerd sinds "
            f"{paused_at.strftime('%d/%m/%Y %H:%M')} UTC. "
            "Klik 'Hervat' om opnieuw te starten."
        )
    return "Software gepauzeerd. Klik 'Hervat' om opnieuw te starten."


def _to_response(record: RuntimeConfigRecord) -> PauzeStatusResponse:
    return PauzeStatusResponse(
        title_nl="Pauze-modus",
        help_nl=_HELP_NL,
        paused=record.software_paused,
        paused_at=(
            record.software_paused_at.isoformat()
            if record.software_paused_at is not None
            else None
        ),
        summary_nl=_summary(record.software_paused, record.software_paused_at),
    )


def _read_record() -> RuntimeConfigRecord:
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            record = repo.get()
    except StorageConnectionError as exc:
        logger.warning("pauze read storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc
    if record is None:
        return _default_record(datetime.now(UTC))
    return record


def _write_record(*, paused: bool) -> RuntimeConfigRecord:
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            now = datetime.now(UTC)
            existing = repo.get()
            base = existing if existing is not None else _default_record(now)
            updated = RuntimeConfigRecord(
                **{
                    **base.__dict__,
                    "software_paused": paused,
                    "software_paused_at": now if paused else None,
                    "updated_at": now,
                }
            )
            repo.upsert(updated)
            checked.connection.commit()
            return updated
    except StoragePersistenceBlockedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageConnectionError as exc:
        logger.warning("pauze write storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc


@router.get("/pauze", response_model=PauzeStatusResponse)
def get_pauze_status() -> PauzeStatusResponse:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        # If storage is off we cannot persist a paused-state, but we
        # also can't be paused — return "draaiend" as a safe default.
        return _to_response(_default_record(datetime.now(UTC)))
    return _to_response(_read_record())


@router.post("/pauze", response_model=PauzeStatusResponse)
def pauze() -> PauzeStatusResponse:
    return _to_response(_write_record(paused=True))


@router.post("/pauze/hervat", response_model=PauzeStatusResponse)
def hervat() -> PauzeStatusResponse:
    return _to_response(_write_record(paused=False))


# ----------------------------------------------------------------------
# Internal helper for the morning-chain.
# ----------------------------------------------------------------------


def is_software_paused() -> bool:
    """Read-only check the morning-chain calls before BUY legs fire.

    Returns ``False`` whenever storage is unavailable so a transient
    connection issue never silently freezes the operator's flow.
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return False
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            record = repo.get()
    except StorageConnectionError:
        return False
    if record is None:
        return False
    return record.software_paused


__all__ = ["router", "is_software_paused"]
