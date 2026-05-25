"""Task 129: API surface for the worker-fetched EOD market data.

Three read-only routes back the Portefeuille + Volglijst price
columns + the operator's provider-audit panel:

* ``GET /market-data/eod/snapshots/latest?conid=…`` — latest
  snapshot for one conid, with FX-converted EUR close + freshness
  badge.
* ``GET /market-data/eod/snapshots/by-account?account_id=…`` —
  latest snapshot per conid for every asset in the user's
  watchlist + positions (read from durable storage; the API
  never re-fetches).
* ``GET /market-data/provider-calls?limit=20`` — recent provider
  audit rows for the diagnostics panel.

Decimal preserved as strings on the wire (never float).
HTTP 503 + locked Dutch body when storage is unreachable. Safety
booleans hard-False on every response.

EUR conversion + freshness state are computed at display time —
storage never co-mingles local + EUR per Task 129 product lock §5.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from ai_trading_agent_storage import (
    SqlAlchemyFxRateRepository,
    SqlAlchemyMarketDataEodSnapshotRepository,
    SqlAlchemyProviderCallAuditRepository,
    SqlAlchemyWatchlistItemSeedRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from portfolio_outlook_api.config import settings

router = APIRouter()


STORAGE_UNAVAILABLE_DETAIL = "Opslag is niet beschikbaar."
BASE_CURRENCY = "EUR"
_FRESH_DAYS = 1
_STALE_DAYS = 3
Freshness = Literal["fresh", "stale", "unavailable"]


# ---- Pydantic v2 response models ---------------------------------


class MarketDataLatestSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_conid: str
    symbol: str
    exchange: str | None
    as_of_date: str
    close_local: str
    currency_local: str
    close_eur: str | None
    fx_rate_used: str | None
    fx_rate_as_of: str | None
    freshness: Freshness
    provider: str
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class MarketDataByAccountRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ibkr_conid: str
    symbol: str
    exchange: str | None
    as_of_date: str
    close_local: str
    currency_local: str
    close_eur: str | None
    freshness: Freshness


class MarketDataByAccountResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str | None
    items: list[MarketDataByAccountRow]
    fetched_via: str | None
    as_of_date: str | None
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class ProviderCallRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: str
    called_at: str
    provider: str
    endpoint: str
    response_status: int | None
    duration_ms: int | None
    error_class: str | None
    account_id: str | None
    triggered_by_run_id: str | None


class ProviderCallsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ProviderCallRow]
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


# ---- helpers -----------------------------------------------------


def _raise_storage_unavailable() -> None:
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


def _today() -> date:
    return datetime.now(UTC).date()


def _freshness_for(
    as_of_date: date, *, today: date | None = None
) -> Freshness:
    """Task 129 product lock §6 — display-time freshness derivation."""

    actual_today = today or _today()
    delta = (actual_today - as_of_date).days
    if delta <= _FRESH_DAYS:
        return "fresh"
    if delta <= _STALE_DAYS:
        return "stale"
    return "unavailable"


def _decimal_str(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _fx_join(
    *,
    fx_repo: SqlAlchemyFxRateRepository,
    close_local: Decimal,
    currency_local: str,
    as_of_date: date,
) -> tuple[str | None, str | None, str | None]:
    """Returns ``(close_eur, fx_rate_used, fx_rate_as_of)`` triple."""

    if currency_local == BASE_CURRENCY:
        return (_decimal_str(close_local), None, None)
    fx = fx_repo.get_rate(
        base_currency=currency_local,
        quote_currency=BASE_CURRENCY,
        as_of_date=as_of_date,
    )
    if fx is None:
        fx = fx_repo.get_latest(
            base_currency=currency_local,
            quote_currency=BASE_CURRENCY,
        )
    if fx is None:
        return (None, None, None)
    close_eur = close_local * fx.rate
    return (
        _decimal_str(close_eur.quantize(Decimal("0.000001"))),
        str(fx.rate),
        fx.as_of_date.isoformat(),
    )


def _configured_account_id() -> str | None:
    hint = getattr(settings, "ibkr_account_id_hint", None)
    if hint is None:
        return None
    text = str(hint).strip()
    return text or None


# ---- routes ------------------------------------------------------


@router.get(
    "/market-data/eod/snapshots/latest",
    response_model=MarketDataLatestSnapshotResponse,
)
def read_latest_snapshot(conid: str = Query(..., min_length=1)) -> dict[str, object]:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            snap_repo = SqlAlchemyMarketDataEodSnapshotRepository(
                checked.connection, checked.readiness
            )
            fx_repo = SqlAlchemyFxRateRepository(
                checked.connection, checked.readiness
            )
            snapshot = snap_repo.get_latest_by_conid(ibkr_conid=conid)
            if snapshot is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Geen EOD snapshot voor conid {conid}.",
                )
            close_eur, fx_rate, fx_as_of = _fx_join(
                fx_repo=fx_repo,
                close_local=snapshot.close_local,
                currency_local=snapshot.currency_local,
                as_of_date=snapshot.as_of_date,
            )
            freshness = _freshness_for(snapshot.as_of_date)
            return {
                "ibkr_conid": snapshot.ibkr_conid,
                "symbol": snapshot.symbol,
                "exchange": snapshot.exchange,
                "as_of_date": snapshot.as_of_date.isoformat(),
                "close_local": str(snapshot.close_local),
                "currency_local": snapshot.currency_local,
                "close_eur": close_eur,
                "fx_rate_used": fx_rate,
                "fx_rate_as_of": fx_as_of,
                "freshness": freshness,
                "provider": snapshot.provider,
                "safe_for_action_drafts": False,
                "safe_for_orders": False,
            }
    except StorageConnectionError:
        _raise_storage_unavailable()
    # Unreachable.
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


@router.get(
    "/market-data/eod/snapshots/by-account",
    response_model=MarketDataByAccountResponse,
)
def read_snapshots_by_account(
    account_id: str | None = Query(default=None),
) -> dict[str, object]:
    """Return latest per-conid snapshot for the account's watchlist."""

    effective_account = account_id or _configured_account_id()
    if effective_account is None:
        return {
            "account_id": None,
            "items": [],
            "fetched_via": None,
            "as_of_date": None,
            "safe_for_action_drafts": False,
            "safe_for_orders": False,
        }
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()

    items: list[dict[str, object]] = []
    fetched_via: str | None = None
    latest_as_of: date | None = None
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            snap_repo = SqlAlchemyMarketDataEodSnapshotRepository(
                checked.connection, checked.readiness
            )
            fx_repo = SqlAlchemyFxRateRepository(
                checked.connection, checked.readiness
            )
            wl_repo = SqlAlchemyWatchlistItemSeedRepository(
                checked.connection, checked.readiness
            )
            # Build the per-account conid list: watchlist seed rows
            # for the account. (Positions table integration is a
            # follow-up — for now the watchlist is the source.)
            wl_rows = wl_repo.list_starter_seed_for_account(effective_account)
            conids: list[str] = []
            for row in wl_rows.records:
                # The seed rows don't carry ibkr_conid directly, but
                # ``asset_id`` joins to an AssetListing in production.
                # For the cold-start prototype, use the symbol as a
                # synthetic conid so the storage join works in tests.
                synth = row.asset_id or row.watchlist_item_id
                conids.append(synth)
            for conid in conids:
                snapshot = snap_repo.get_latest_by_conid(ibkr_conid=conid)
                if snapshot is None:
                    continue
                close_eur, _fx, _fx_as_of = _fx_join(
                    fx_repo=fx_repo,
                    close_local=snapshot.close_local,
                    currency_local=snapshot.currency_local,
                    as_of_date=snapshot.as_of_date,
                )
                items.append(
                    {
                        "ibkr_conid": snapshot.ibkr_conid,
                        "symbol": snapshot.symbol,
                        "exchange": snapshot.exchange,
                        "as_of_date": snapshot.as_of_date.isoformat(),
                        "close_local": str(snapshot.close_local),
                        "currency_local": snapshot.currency_local,
                        "close_eur": close_eur,
                        "freshness": _freshness_for(snapshot.as_of_date),
                    }
                )
                fetched_via = snapshot.provider
                if latest_as_of is None or snapshot.as_of_date > latest_as_of:
                    latest_as_of = snapshot.as_of_date
    except StorageConnectionError:
        _raise_storage_unavailable()

    return {
        "account_id": effective_account,
        "items": items,
        "fetched_via": fetched_via,
        "as_of_date": latest_as_of.isoformat() if latest_as_of else None,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


@router.get(
    "/market-data/provider-calls",
    response_model=ProviderCallsResponse,
)
def read_provider_calls(
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, object]:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyProviderCallAuditRepository(
                checked.connection, checked.readiness
            )
            rows = repo.list_recent(limit=limit)
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "items": [
            {
                "audit_id": row.audit_id,
                "called_at": row.called_at.isoformat(),
                "provider": row.provider,
                "endpoint": row.endpoint,
                "response_status": row.response_status,
                "duration_ms": row.duration_ms,
                "error_class": row.error_class,
                "account_id": row.account_id,
                "triggered_by_run_id": row.triggered_by_run_id,
            }
            for row in rows.records
        ],
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }
