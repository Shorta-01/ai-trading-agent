"""Worker → API HTTP triggers for jobs that used to live in the API process.

Moving the cron registration into the worker (the single source of cron
truth) means the API can be a stateless HTTP server again — multi-replica
deploys no longer race on the lock-less ``scheduler_runs`` table because
only the worker fires.

Each helper is a thin ``httpx.post`` wrapper that swallows network and
non-2xx failures: a scheduled HTTP tick must never crash the scheduler
loop. Persistent failures land in the standard scheduler audit chain
(the API's ``scheduler_runs`` row will still show the actual outcome
when the request *does* land).
"""

from __future__ import annotations

import logging
from typing import Any, cast

logger = logging.getLogger(__name__)


def trigger_morning_chain(
    *, base_url: str | None, timeout_seconds: float
) -> dict[str, Any] | None:
    """POST ``/scheduler/runs/morning-chain`` on the API.

    Returns the JSON body on success, ``None`` on transport failure or
    non-2xx response. Tests inject a stub ``base_url`` and assert on the
    captured call.
    """

    return _post(base_url, "/scheduler/runs/morning-chain", timeout_seconds)


def trigger_ibkr_sync(
    *, base_url: str | None, timeout_seconds: float
) -> dict[str, Any] | None:
    """POST ``/ibkr/sync/run`` on the API."""

    return _post(base_url, "/ibkr/sync/run", timeout_seconds)


def trigger_morning_explanation_batch(
    *, base_url: str | None, timeout_seconds: float
) -> dict[str, Any] | None:
    """POST ``/explanations/morning-batch`` on the API.

    Fired after the daily morning chain so Claude's Dutch paraphrase
    is ready for every held-position Decision Package before the
    operator opens the dashboard. Honours the API-side opt-in flag
    (``ai_explanation_morning_batch_enabled``) — when off, the API
    returns ``status="disabled"`` and the call is a deterministic
    no-op.
    """

    return _post(base_url, "/explanations/morning-batch", timeout_seconds)


def trigger_sell_signal_sweep(
    *, base_url: str | None, timeout_seconds: float
) -> dict[str, Any] | None:
    """POST ``/sell-signals/sweep`` on the API (V1.2 §BI).

    CLAUDE.md §6.3 + §11 — de SELL-monitoring sweep moet
    automatisch draaien zodat de operator zijn +4 % intraday hits
    niet mist. De sweep zelf is bewust pauze-agnostisch (CLAUDE.md
    §11), maar wordt nooit door het pre-briefing pad getriggerd —
    deze trigger is dat ontbrekende stuk wireup.

    Returns ``None`` op transport-fout of non-2xx; persistente
    fouten landen in de API's ``scheduler_runs`` audit row én in
    de standaard worker error-log via APScheduler's
    ``EVENT_JOB_ERROR`` listener.
    """

    return _post(base_url, "/sell-signals/sweep", timeout_seconds)


def trigger_macro_feed_refresh(
    *, base_url: str | None, timeout_seconds: float
) -> dict[str, Any] | None:
    """POST ``/markets/macro-snapshot/refresh`` on the API (V1.2 §BT).

    GAPS.md P1-10 — verse VIX + SPX bars zijn voorwaardelijk voor
    een correcte macro-regime gate (CLAUDE.md §7.2). Tot deze cron
    moest de operator manueel ``sync_macro_feed()`` aanroepen.
    """

    return _post(
        base_url, "/markets/macro-snapshot/refresh", timeout_seconds
    )


def trigger_monthly_archive_auto_generate(
    *, base_url: str | None, timeout_seconds: float
) -> dict[str, Any] | None:
    """POST ``/rapporten/archief/auto-generate`` on the API (V1.2 §BN).

    CLAUDE.md §13 — "elke 1e van de maand wordt een PDF gegenereerd
    en opgeslagen in /rapporten/archief". Deze trigger is de cron-
    aankomst van de operator-uitspraak; de API berekent zelf welke
    maand er gearchiveerd moet worden (vorige kalendermaand).
    """

    return _post(
        base_url, "/rapporten/archief/auto-generate", timeout_seconds
    )


def compose_alert_summary(
    *,
    base_url: str | None,
    timeout_seconds: float,
    kind: str,
    context_text: str,
    alert_lines: list[str],
) -> dict[str, Any] | None:
    """POST ``/notifications/compose-summary`` and return the JSON body.

    Used by the digest + morning-alerts runners to fetch an AI-composed
    Dutch summary header for the email they're about to send. Returns
    ``None`` on transport failure / non-2xx response so the caller falls
    through to template-only — a missing AI header must never block the
    operational email.
    """

    return _post(
        base_url,
        "/notifications/compose-summary",
        timeout_seconds,
        json_body={
            "kind": kind,
            "context_text": context_text,
            "alert_lines": list(alert_lines),
        },
    )


def _post(
    base_url: str | None,
    path: str,
    timeout_seconds: float,
    *,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not base_url:
        logger.warning("api trigger skipped: no api_base_url configured")
        return None
    import httpx  # lazy import — worker already depends on httpx for EODHD

    url = base_url.rstrip("/") + path
    try:
        if json_body is None:
            response = httpx.post(url, timeout=timeout_seconds)
        else:
            response = httpx.post(url, timeout=timeout_seconds, json=json_body)
    except Exception:  # noqa: BLE001 — a scheduled tick must never crash
        logger.exception("api trigger %s failed (transport)", url)
        return None
    if response.status_code >= 400:
        logger.warning(
            "api trigger %s returned HTTP %s", url, response.status_code
        )
        return None
    try:
        body = response.json()
    except Exception:  # noqa: BLE001 — non-JSON body is unexpected but inert
        logger.exception("api trigger %s returned non-JSON body", url)
        return None
    if isinstance(body, dict):
        return cast("dict[str, Any]", body)
    return None


__all__ = [
    "compose_alert_summary",
    "trigger_ibkr_sync",
    "trigger_macro_feed_refresh",
    "trigger_monthly_archive_auto_generate",
    "trigger_morning_chain",
    "trigger_morning_explanation_batch",
    "trigger_sell_signal_sweep",
]
