"""Task 129: scheduler-driven EOD market-data step.

Called by the orchestrator when ``mode_detected="normal"`` AND the
fire is ``pre_briefing`` or ``morning_briefing``. Iterates the
union of (confirmed watchlist) + (current IBKR positions) for the
configured account, fetches yesterday's EOD price + the matching
FX rate per asset, and writes the audit-trailed snapshots.

Hourly delta runs (08:00-21:00) skip this step entirely — EOD
prices don't change intraday.

The step never raises: every failed fetch is logged + counted in
the returned ``MarketDataFetchResult`` so the orchestrator can
fold the totals into the ``scheduled_run_audit`` row.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    EodhdNotConfiguredError,
    FxRateRecord,
    MarketDataEodSnapshotEntry,
    SqlAlchemyFxRateRepository,
    SqlAlchemyMarketDataEodSnapshotRepository,
)

from portfolio_outlook_worker.providers.eodhd import (
    PROVIDER_CODE,
    EodhdClient,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AssetForFetch:
    """One asset to refresh: identity + market metadata."""

    ibkr_conid: str
    symbol: str
    exchange: str
    currency_local: str


class _AssetUniverseProtocol(Protocol):
    """Storage adapter returning the per-account fetch universe."""

    def list_assets_for_account(
        self, ibkr_account_id: str
    ) -> tuple[AssetForFetch, ...]: ...


@dataclass(frozen=True)
class _FetchFailure:
    """One failure surfaced in the result for the audit row."""

    ibkr_conid: str
    symbol: str
    error_class: str
    message: str


@dataclass(frozen=True)
class MarketDataFetchResult:
    """Counts + per-failure detail folded into the orchestrator audit."""

    snapshots_attempted: int
    snapshots_succeeded: int
    snapshots_failed: tuple[_FetchFailure, ...]
    fx_rates_attempted: int
    fx_rates_succeeded: int
    fx_rates_failed: tuple[_FetchFailure, ...]

    def as_audit_dict(self) -> dict[str, object]:
        return {
            "snapshots_attempted": self.snapshots_attempted,
            "snapshots_succeeded": self.snapshots_succeeded,
            "snapshots_failed_count": len(self.snapshots_failed),
            "fx_rates_attempted": self.fx_rates_attempted,
            "fx_rates_succeeded": self.fx_rates_succeeded,
            "fx_rates_failed_count": len(self.fx_rates_failed),
        }


def fetch_market_data_for_account(
    *,
    ibkr_account_id: str,
    asset_universe: _AssetUniverseProtocol,
    snapshot_repo: SqlAlchemyMarketDataEodSnapshotRepository,
    fx_rate_repo: SqlAlchemyFxRateRepository,
    eodhd_client: EodhdClient,
    target_date: date,
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC),
    base_currency: str = "EUR",
) -> MarketDataFetchResult:
    """Execute one fetch cycle for ``ibkr_account_id`` on ``target_date``."""

    assets = asset_universe.list_assets_for_account(ibkr_account_id)
    if not assets:
        return MarketDataFetchResult(
            snapshots_attempted=0,
            snapshots_succeeded=0,
            snapshots_failed=tuple(),
            fx_rates_attempted=0,
            fx_rates_succeeded=0,
            fx_rates_failed=tuple(),
        )

    # ---- snapshots --------------------------------------------------
    snap_attempted = 0
    snap_succeeded = 0
    snap_failed: list[_FetchFailure] = []
    needed_currencies: set[str] = set()

    seen_conids: set[str] = set()
    for asset in assets:
        if asset.ibkr_conid in seen_conids:
            continue
        seen_conids.add(asset.ibkr_conid)
        needed_currencies.add(asset.currency_local)

        existing = snapshot_repo.get_for_date(
            ibkr_conid=asset.ibkr_conid,
            as_of_date=target_date,
            provider=PROVIDER_CODE,
        )
        if existing is not None:
            continue  # idempotent — same conid+date already cached

        snap_attempted += 1
        try:
            response = eodhd_client.fetch_eod(
                symbol=asset.symbol,
                exchange=asset.exchange,
                as_of_date=target_date,
            )
        except EodhdNotConfiguredError as exc:
            snap_failed.append(
                _FetchFailure(
                    ibkr_conid=asset.ibkr_conid,
                    symbol=asset.symbol,
                    error_class=type(exc).__name__,
                    message=str(exc),
                )
            )
            continue
        except Exception as exc:  # noqa: BLE001 — boundary
            snap_failed.append(
                _FetchFailure(
                    ibkr_conid=asset.ibkr_conid,
                    symbol=asset.symbol,
                    error_class=type(exc).__name__,
                    message=str(exc),
                )
            )
            continue
        now = now_provider()
        try:
            snapshot_repo.append(
                MarketDataEodSnapshotEntry(
                    snapshot_id=f"mdsnap_{uuid4().hex}",
                    ibkr_conid=asset.ibkr_conid,
                    symbol=asset.symbol,
                    exchange=asset.exchange,
                    currency_local=asset.currency_local,
                    as_of_date=target_date,
                    as_of_close_ts=now,
                    ingested_ts=now,
                    open_local=response.open,
                    high_local=response.high,
                    low_local=response.low,
                    close_local=response.close,
                    adj_close_local=response.adjusted_close,
                    volume=response.volume,
                    provider=PROVIDER_CODE,
                    provider_response_hash=response.raw_hash,
                )
            )
            snap_succeeded += 1
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception(
                "Failed to persist EOD snapshot for %s",
                asset.symbol,
            )
            snap_failed.append(
                _FetchFailure(
                    ibkr_conid=asset.ibkr_conid,
                    symbol=asset.symbol,
                    error_class=type(exc).__name__,
                    message=str(exc),
                )
            )

    # ---- FX rates for non-base currencies --------------------------
    fx_attempted = 0
    fx_succeeded = 0
    fx_failed: list[_FetchFailure] = []

    for currency in sorted(needed_currencies):
        if currency == base_currency:
            continue
        existing_fx = fx_rate_repo.get_rate(
            base_currency=currency,
            quote_currency=base_currency,
            as_of_date=target_date,
            provider=PROVIDER_CODE,
        )
        if existing_fx is not None:
            continue

        fx_attempted += 1
        try:
            fx_response = eodhd_client.fetch_fx(
                base=currency, quote=base_currency, as_of_date=target_date
            )
        except EodhdNotConfiguredError as exc:
            fx_failed.append(
                _FetchFailure(
                    ibkr_conid="",
                    symbol=f"{currency}{base_currency}",
                    error_class=type(exc).__name__,
                    message=str(exc),
                )
            )
            continue
        except Exception as exc:  # noqa: BLE001 — boundary
            fx_failed.append(
                _FetchFailure(
                    ibkr_conid="",
                    symbol=f"{currency}{base_currency}",
                    error_class=type(exc).__name__,
                    message=str(exc),
                )
            )
            continue
        now = now_provider()
        try:
            fx_rate_repo.upsert(
                FxRateRecord(
                    base_currency=currency,
                    quote_currency=base_currency,
                    as_of_date=target_date,
                    rate=fx_response.rate,
                    ingested_ts=now,
                    provider=PROVIDER_CODE,
                )
            )
            fx_succeeded += 1
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception(
                "Failed to persist FX rate %s%s", currency, base_currency
            )
            fx_failed.append(
                _FetchFailure(
                    ibkr_conid="",
                    symbol=f"{currency}{base_currency}",
                    error_class=type(exc).__name__,
                    message=str(exc),
                )
            )

    return MarketDataFetchResult(
        snapshots_attempted=snap_attempted,
        snapshots_succeeded=snap_succeeded,
        snapshots_failed=tuple(snap_failed),
        fx_rates_attempted=fx_attempted,
        fx_rates_succeeded=fx_succeeded,
        fx_rates_failed=tuple(fx_failed),
    )


__all__ = [
    "AssetForFetch",
    "MarketDataFetchResult",
    "fetch_market_data_for_account",
]
