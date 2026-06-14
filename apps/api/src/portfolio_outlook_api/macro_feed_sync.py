"""Macro-feed sync (V1.2 §BE).

Refresht ``macro_index_snapshots`` voor VIX + S&P-500 via EODHD. De
orchestrator-scoring-leg leest via :mod:`macro_resolver` deze tabel —
zonder deze sync stond de gate vóór deze PR-reeks blind voor echte
volatiliteit.

EODHD-symbool-conventies:
* VIX (CBOE): ``VIX.INDX``
* S&P-500: ``GSPC.INDX``

Beide series leveren EOD-bars; we lezen ~260 dagen achteruit zodat
de macro-gate's 50/200-day MA-crossover een ruime buffer heeft.

Idempotent: ``upsert`` per ``(series_code, bar_date)`` zodat een
herhaalde sync alleen ontbrekende rijen aanvult.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    MACRO_SERIES_SPX,
    MACRO_SERIES_VIX,
    SaveMacroIndexSnapshotRequest,
    SqlAlchemyMacroIndexSnapshotRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)


_VIX_EODHD = "VIX.INDX"
_SPX_EODHD = "GSPC.INDX"
_LOOKBACK_DAYS = 380  # ~260 trading days + buffer voor weekends


@dataclass(frozen=True)
class MacroFeedSyncResult:
    """Wat de sync per call gedaan heeft — voor leg detail_nl."""

    vix_bars_persisted: int
    spx_bars_persisted: int
    error: str | None
    provider_skipped: bool


class _BarProvider(Protocol):
    """Minimaal-shape protocol — zo blijven tests fixture-vrij van
    de echte EODHD-client en kunnen we hier nieuwe providers
    inpluggen zonder de signature te raken."""

    def fetch_eod_bars(
        self,
        eodhd_symbol: str,
        *,
        from_date: date,
        to_date: date,
    ) -> list[Any]:
        ...


def _build_eodhd_client() -> _BarProvider | None:
    """Bouw een ``EodhdClient`` wanneer de API-key gezet is. Geeft
    ``None`` zodat callers cleanly kunnen skippen op een verse
    install zonder key."""

    api_key = getattr(settings, "eodhd_api_key", None)
    if not api_key:
        return None
    # Late-bound import — de eodhd-module heeft een transitive
    # ``urllib`` dependency die we niet bij module-load willen raken
    # in test-runs zonder key.
    from portfolio_outlook_api.eodhd_client import EodhdClient

    return EodhdClient(api_key=api_key)


def _persist_bars(
    repo: SqlAlchemyMacroIndexSnapshotRepository,
    *,
    series_code: str,
    bars: list[Any],
    fetched_at: datetime,
) -> int:
    persisted = 0
    for bar in bars:
        close = getattr(bar, "close_price", None)
        if close is None or close <= 0:
            continue
        bar_date = getattr(bar, "bar_date", None)
        if bar_date is None:
            continue
        repo.upsert(
            SaveMacroIndexSnapshotRequest(
                snapshot_id=str(uuid4()),
                series_code=series_code,
                bar_date=bar_date,
                close_value=Decimal(str(close)),
                raw_payload={
                    "open": str(getattr(bar, "open_price", "") or ""),
                    "high": str(getattr(bar, "high_price", "") or ""),
                    "low": str(getattr(bar, "low_price", "") or ""),
                    "adjusted_close": str(
                        getattr(bar, "adjusted_close", "") or ""
                    ),
                    "volume": str(getattr(bar, "volume", "") or ""),
                },
                provider="eodhd",
                fetched_at=fetched_at,
            )
        )
        persisted += 1
    return persisted


def sync_macro_feed(
    *,
    today: date | None = None,
    provider: _BarProvider | None = None,
) -> MacroFeedSyncResult:
    """Haal de laatste ~380 dagen VIX + S&P-bars op en upsert in
    ``macro_index_snapshots``.

    ``provider`` is injecteerbaar voor tests; in productie bouwen we
    een echte ``EodhdClient``. Wanneer de EODHD-key niet gezet is en
    geen provider geinjecteerd, signaleren we ``provider_skipped`` —
    de orchestrator valt dan terug op de synthetische defaults.
    """

    today = today or datetime.now(UTC).date()
    from_date = today - timedelta(days=_LOOKBACK_DAYS)

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return MacroFeedSyncResult(0, 0, "storage-disabled", True)

    client = provider or _build_eodhd_client()
    if client is None:
        return MacroFeedSyncResult(0, 0, "eodhd-key-missing", True)

    fetched_at = datetime.now(UTC)
    try:
        sp_provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with sp_provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyMacroIndexSnapshotRepository(
                checked.connection, checked.readiness
            )
            vix_bars = client.fetch_eod_bars(
                _VIX_EODHD, from_date=from_date, to_date=today
            )
            vix_persisted = _persist_bars(
                repo,
                series_code=MACRO_SERIES_VIX,
                bars=vix_bars,
                fetched_at=fetched_at,
            )
            spx_bars = client.fetch_eod_bars(
                _SPX_EODHD, from_date=from_date, to_date=today
            )
            spx_persisted = _persist_bars(
                repo,
                series_code=MACRO_SERIES_SPX,
                bars=spx_bars,
                fetched_at=fetched_at,
            )
            checked.connection.commit()
    except StorageConnectionError as exc:
        logger.warning("macro-feed-sync storage error: %s", exc)
        return MacroFeedSyncResult(0, 0, f"storage-error:{exc}", False)
    except Exception as exc:  # noqa: BLE001 — provider boundary
        logger.warning("macro-feed-sync provider error: %s", exc)
        return MacroFeedSyncResult(0, 0, f"provider-error:{exc}", False)

    return MacroFeedSyncResult(
        vix_bars_persisted=vix_persisted,
        spx_bars_persisted=spx_persisted,
        error=None,
        provider_skipped=False,
    )


__all__ = ["MacroFeedSyncResult", "sync_macro_feed"]
