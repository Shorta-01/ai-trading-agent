"""Markt-regime macro-snapshot endpoint (V1.2 §AV / CLAUDE.md §7.2).

The profit-harvest doctrine treats the macro gate as *informational*
— the dashboard surfaces a strip at the top with the most recent
VIX + index-trend state but the operator decides whether to buy.

This endpoint reads the most-recent ``orchestrator_scoring_verdicts``
batch and extracts the macro diagnostics that the worker already
serialized inside ``details_json``. We do not re-compute anything —
the doctrine forbids the API surfacing numbers that didn't originate
in the orchestrator runner.

State buckets (CLAUDE.md §7.2):
* ``rustig`` — macro gate says ``favorable=True``.
* ``verhoogd`` — VIX above the threshold OR MA-crossover bearish.
* ``stress`` — both at once.
* ``onbekend`` — no orchestrator verdict yet (cold start).

Read-only; never raises except on storage-unavailable (503).
"""

from __future__ import annotations

import logging
from typing import Any, cast

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


class MacroSnapshotResponse(BaseModel):
    title_nl: str
    help_nl: str
    state: str  # rustig | verhoogd | stress | onbekend
    severity: str  # info | warning | critical
    headline_nl: str
    vix_level: float | None
    ma_short_day: float | None
    ma_long_day: float | None
    last_evaluated_at: str | None
    sample_size: int


_HELP_NL = (
    "Macro-regime info-strip. CLAUDE.md §7.2 maakt van de macro-"
    "gate een informatieve waarschuwing in plaats van een harde "
    "blokkade — beslissingen blijven bij de operator. De waarden "
    "komen uit de meest recente orchestrator-scoring batch."
)


def _account_ref() -> str:
    return "default"


def _empty_response() -> MacroSnapshotResponse:
    return MacroSnapshotResponse(
        title_nl="Markt-regime",
        help_nl=_HELP_NL,
        state="onbekend",
        severity="info",
        headline_nl=(
            "Macro-regime nog niet beoordeeld — wacht op de eerste "
            "orchestrator-scoring batch."
        ),
        vix_level=None,
        ma_short_day=None,
        ma_long_day=None,
        last_evaluated_at=None,
        sample_size=0,
    )


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _state_for(
    *,
    favorable: bool | None,
    vix_level: float | None,
    ma_short: float | None,
    ma_long: float | None,
) -> tuple[str, str, str]:
    """Bucket the macro state into one of four labels + severity +
    human-readable headline. ``None`` favorable means the worker
    didn't include the gate output (older verdict shape).
    """

    if favorable is True:
        ma_pair = ""
        if ma_short is not None and ma_long is not None:
            ma_pair = f" · S&P 50d {ma_short:.0f} ≥ 200d {ma_long:.0f}"
        vix_part = ""
        if vix_level is not None:
            vix_part = f" VIX {vix_level:.1f}."
        return (
            "rustig",
            "info",
            f"Markt-regime rustig.{vix_part}{ma_pair}".strip(),
        )
    if favorable is None:
        return (
            "onbekend",
            "info",
            "Macro-gate uit op de orchestrator — geen verdict.",
        )

    # favorable == False: figure out if it's one signal or both.
    vix_warns = vix_level is not None and vix_level >= 25
    ma_warns = (
        ma_short is not None
        and ma_long is not None
        and ma_short < ma_long
    )
    if vix_warns and ma_warns:
        return (
            "stress",
            "critical",
            (
                f"Macro-stress: VIX {vix_level:.1f} en S&P 50d "
                f"{ma_short:.0f} < 200d {ma_long:.0f}. Wees voorzichtig."
            ),
        )
    if vix_warns:
        return (
            "verhoogd",
            "warning",
            (
                f"Verhoogde volatiliteit: VIX {vix_level:.1f} boven "
                "drempel. Doctrine laat voorstellen door, maar "
                "wees voorzichtig."
            ),
        )
    if ma_warns:
        return (
            "verhoogd",
            "warning",
            (
                f"S&P-trend negatief (50d {ma_short:.0f} < 200d "
                f"{ma_long:.0f}). Doctrine laat voorstellen door."
            ),
        )
    # Gate said unfavorable but neither signal hit our display
    # threshold — surface a generic warning.
    return (
        "verhoogd",
        "warning",
        "Macro-gate ongunstig — controleer de orchestrator-details.",
    )


@router.get("/markets/macro-snapshot", response_model=MacroSnapshotResponse)
def get_macro_snapshot() -> MacroSnapshotResponse:
    """Return the most recent macro-regime snapshot.

    Reads the latest batch of ``orchestrator_scoring_verdicts`` and
    picks the macro diagnostics from any one row in it — every row
    in a batch shares the same macro inputs, so the first verdict
    in the burst is representative.
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty_response()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyOrchestratorScoringVerdictRepository(
                checked.connection, checked.readiness
            )
            result = repo.list_verdicts_for_account(
                ibkr_account_ref=_account_ref(), limit=500
            )
    except StorageConnectionError as exc:
        logger.warning("macro-snapshot storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    if not result.records:
        return _empty_response()

    latest_ts = result.records[0].generated_at
    threshold = latest_ts.timestamp() - 60.0
    in_latest = [
        record
        for record in result.records
        if record.generated_at.timestamp() >= threshold
    ]

    # Pick a representative row — every verdict in the batch sees the
    # same macro inputs.
    pick = in_latest[0]
    details_raw = pick.details_json or {}
    macro_raw = details_raw.get("macro") if isinstance(details_raw, dict) else None
    macro_blob: dict[str, Any] = (
        cast(dict[str, Any], macro_raw) if isinstance(macro_raw, dict) else {}
    )
    favorable_raw = macro_blob.get("favorable")
    favorable: bool | None = (
        favorable_raw if isinstance(favorable_raw, bool) else None
    )
    vix_level = _to_float(macro_blob.get("vix_level"))
    ma_short = _to_float(macro_blob.get("ma_short_day"))
    ma_long = _to_float(macro_blob.get("ma_long_day"))

    state, severity, headline_nl = _state_for(
        favorable=favorable,
        vix_level=vix_level,
        ma_short=ma_short,
        ma_long=ma_long,
    )
    return MacroSnapshotResponse(
        title_nl="Markt-regime",
        help_nl=_HELP_NL,
        state=state,
        severity=severity,
        headline_nl=headline_nl,
        vix_level=vix_level,
        ma_short_day=ma_short,
        ma_long_day=ma_long,
        last_evaluated_at=latest_ts.isoformat(),
        sample_size=len(in_latest),
    )


class MacroFeedRefreshResponse(BaseModel):
    """Antwoord op de macro-feed refresh trigger (V1.2 §BT / P1-10)."""

    accepted: bool
    vix_bars_persisted: int
    spx_bars_persisted: int
    provider_skipped: bool
    error_text: str | None
    status_nl: str


@router.post(
    "/markets/macro-snapshot/refresh",
    response_model=MacroFeedRefreshResponse,
)
def trigger_macro_feed_refresh() -> MacroFeedRefreshResponse:
    """V1.2 §BT / GAPS.md P1-10 — handmatige refresh van de macro
    feed (VIX + S&P 500).

    Bedoeld voor de worker-cron én voor operator-handmatige trigger
    via dashboard. Roept ``sync_macro_feed()`` aan dat ~380 dagen
    bars via EODHD ophaalt en upsert in ``macro_index_snapshots``.

    Geen EODHD-key → ``provider_skipped=True``, geen 5xx. Zo blijft
    de cron veilig om elke handelsdag te firen zonder dat het de
    audit-chain pollueert.
    """

    from portfolio_outlook_api.macro_feed_sync import sync_macro_feed

    result = sync_macro_feed()
    return MacroFeedRefreshResponse(
        accepted=not result.provider_skipped and result.error is None,
        vix_bars_persisted=result.vix_bars_persisted,
        spx_bars_persisted=result.spx_bars_persisted,
        provider_skipped=result.provider_skipped,
        error_text=result.error,
        status_nl=(
            f"Macro-feed refresh uitgevoerd: "
            f"VIX={result.vix_bars_persisted} bars, "
            f"SPX={result.spx_bars_persisted} bars."
            if result.error is None and not result.provider_skipped
            else (
                f"Macro-feed refresh overgeslagen: {result.error or 'provider niet beschikbaar'}."
            )
        ),
    )


__all__ = ["router"]
