from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.watchlist import STORE


@dataclass(frozen=True)
class IbkrWatchlistSummary:
    ibkr_watchlist_id: str
    name: str
    read_only: bool | None
    modified_at: str | None
    watchlist_scope: str | None
    source: str
    fetched_at: str
    raw_reference: dict[str, object] | None


@dataclass(frozen=True)
class IbkrWatchlistInstrument:
    ibkr_watchlist_id: str
    ibkr_conid: str | None
    symbol: str | None
    name: str | None
    asset_class: str | None
    exchange: str | None
    primary_exchange: str | None
    currency: str | None
    validation_status: str
    import_status: str
    fetched_at: str
    raw_reference: dict[str, object] | None


class IbkrWatchlistAdapter:
    def list_watchlists(self) -> list[IbkrWatchlistSummary]:
        raise NotImplementedError

    def list_instruments(self, watchlist_id: str) -> list[IbkrWatchlistInstrument]:
        raise NotImplementedError


class NotConfiguredIbkrWatchlistAdapter(IbkrWatchlistAdapter):
    def list_watchlists(self) -> list[IbkrWatchlistSummary]:
        return []

    def list_instruments(self, watchlist_id: str) -> list[IbkrWatchlistInstrument]:
        return []


DEFAULT_ADAPTER: IbkrWatchlistAdapter = NotConfiguredIbkrWatchlistAdapter()
IMPORT_RUNS: list[dict[str, object]] = []
IMPORT_CANDIDATES: dict[str, list[dict[str, object]]] = {}


def _configured(settings: Settings) -> bool:
    return bool(
        settings.ibkr_enabled
        and settings.ibkr_gateway_url
        and settings.ibkr_account_id_hint
    )


def list_ibkr_watchlists(
    settings: Settings,
    *,
    adapter: IbkrWatchlistAdapter | None = None,
) -> dict[str, object]:
    if not _configured(settings):
        return {
            "configured": False,
            "status": "not_configured",
            "items": [],
            "message_nl": "Niet geconfigureerd.",
        }
    try:
        rows = (adapter or DEFAULT_ADAPTER).list_watchlists()
    except Exception:
        return {
            "configured": True,
            "status": "error",
            "items": [],
            "message_nl": "IBKR-watchlists ophalen mislukt.",
        }
    return {
        "configured": True,
        "status": "ok",
        "items": [r.__dict__ for r in rows],
        "message_nl": "IBKR-watchlists opgehaald.",
    }


def list_ibkr_watchlist_instruments(
    settings: Settings,
    watchlist_id: str,
    *,
    adapter: IbkrWatchlistAdapter | None = None,
) -> dict[str, object]:
    if not _configured(settings):
        return {
            "configured": False,
            "status": "not_configured",
            "items": [],
            "message_nl": "Niet geconfigureerd.",
        }
    try:
        rows = (adapter or DEFAULT_ADAPTER).list_instruments(watchlist_id)
    except Exception:
        return {
            "configured": True,
            "status": "error",
            "items": [],
            "message_nl": "Instrumenten ophalen mislukt.",
        }
    return {
        "configured": True,
        "status": "ok",
        "items": [r.__dict__ for r in rows],
        "message_nl": "Instrumenten opgehaald.",
    }


def import_ibkr_watchlist(
    settings: Settings,
    watchlist_id: str,
    *,
    adapter: IbkrWatchlistAdapter | None = None,
) -> dict[str, object]:
    fetched = list_ibkr_watchlist_instruments(settings, watchlist_id, adapter=adapter)
    if fetched["status"] != "ok":
        return fetched
    items = fetched.get("items")
    if not isinstance(items, list):
        return {
            "status": "error",
            "message_nl": "Instrumenten ophalen mislukt.",
        }
    now = datetime.now(UTC).isoformat()
    run_id = f"ibkr-watchlist-import-{uuid4()}"
    candidates: list[dict[str, object]] = []
    matched = 0
    needs_review = 0
    for row in items:
        if not isinstance(row, dict):
            continue
        conid = (row.get("ibkr_conid") or "").strip()
        symbol = (row.get("symbol") or "").strip().upper()
        status = "candidate"
        validation = "imported"
        if conid == "":
            status = "skipped"
            validation = "unsupported"
            needs_review += 1
        else:
            for local in STORE.values():
                if local.status != "active":
                    continue
                if (local.ibkr_conid or "").strip() == conid:
                    status = "already_in_local_watchlist"
                    matched += 1
                    break
                if local.symbol == symbol and (local.ibkr_conid or "").strip() != conid:
                    status = "needs_review"
                    validation = "needs_review"
                    needs_review += 1
                    break
        row["import_status"] = status
        row["validation_status"] = validation
        candidates.append(row)
    IMPORT_CANDIDATES[run_id] = candidates
    run = {
        "import_run_id": run_id,
        "started_at": now,
        "finished_at": datetime.now(UTC).isoformat(),
        "status": "success",
        "selected_ibkr_watchlist_id": watchlist_id,
        "instrument_count": len(candidates),
        "matched_count": matched,
        "skipped_count": len([c for c in candidates if c["import_status"] == "skipped"]),
        "needs_review_count": needs_review,
        "created_at": now,
    }
    IMPORT_RUNS.append(run)
    return {
        "status": "ok",
        "run": run,
        "candidates": candidates,
        "message_nl": "Import voorbereid. Geen automatische verwijdering.",
    }


def latest_import() -> dict[str, object]:
    return {"status": "ok", "run": IMPORT_RUNS[-1] if IMPORT_RUNS else None}


def import_by_id(import_run_id: str) -> dict[str, object]:
    run = next((r for r in IMPORT_RUNS if r["import_run_id"] == import_run_id), None)
    if run is None:
        return {"status": "not_found", "message_nl": "Import-run niet gevonden."}
    return {"status": "ok", "run": run, "candidates": IMPORT_CANDIDATES.get(import_run_id, [])}
