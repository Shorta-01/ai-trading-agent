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


def _post(
    base_url: str | None, path: str, timeout_seconds: float
) -> dict[str, Any] | None:
    if not base_url:
        logger.warning("api trigger skipped: no api_base_url configured")
        return None
    import httpx  # lazy import — worker already depends on httpx for EODHD

    url = base_url.rstrip("/") + path
    try:
        response = httpx.post(url, timeout=timeout_seconds)
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
    "trigger_ibkr_sync",
    "trigger_morning_chain",
    "trigger_morning_explanation_batch",
]
