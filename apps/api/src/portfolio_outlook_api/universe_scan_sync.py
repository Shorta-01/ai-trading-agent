"""Universe scan orchestrator (Slice 17).

Iterates the locked universe (Bel20 + AEX + CAC40 + DAX40 + S&P 100 +
NASDAQ 100 extra) and, per ticker:

1. Fetches EODHD fundamentals + recent EOD bars.
2. Computes 6-month and 12-month total returns from the bars (when
   absent from the fundamentals payload).
3. Persists an :class:`AssetFundamentalsSnapshotRecord`.
4. Accumulates the running snapshot universe for downstream QVM
   ranking — Slice 18+ wires the ranking persistence; this slice just
   reports the candidate count.

Capped by ``universe_scan_max_tickers_per_run`` so a single run cannot
blow through the EODHD daily quota. Per-ticker failures are captured
but never abort the batch. Returns a structured
:class:`UniverseScanReport`.

Pure boundary code: the EODHD client and the storage repository are
both injected so tests can run offline.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    AssetFundamentalsSnapshotRecord,
    UniverseScanRunRecord,
)
from portfolio_outlook_portfolio import (
    FundamentalsEntry,
    UniverseFundamentals,
)

from portfolio_outlook_api.eodhd_client import (
    EodhdBar,
    EodhdClientError,
    EodhdFundamentals,
)
from portfolio_outlook_api.universe_registry import UniverseEntry, locked_universe

logger = logging.getLogger(__name__)

PROVIDER_CODE = "eodhd"


@dataclass(frozen=True)
class UniverseScanReport:
    run_id: str
    requested_at: datetime
    completed_at: datetime
    status: str
    status_nl: str
    help_nl: str
    universe_size: int
    scanned_count: int
    persisted_count: int
    failed_count: int
    ranked_count: int
    blocking_reason: str | None
    failures: tuple[dict[str, str], ...]


class _EodhdClientProtocol(Protocol):
    def fetch_fundamentals(self, eodhd_symbol: str) -> EodhdFundamentals: ...

    def fetch_eod_bars(
        self, eodhd_symbol: str, *, from_date: date, to_date: date
    ) -> list[EodhdBar]: ...


class _SnapshotRepoProtocol(Protocol):
    def save_snapshot(
        self, record: AssetFundamentalsSnapshotRecord
    ) -> object: ...

    def get_latest_snapshot_for_symbol(
        self, eodhd_symbol: str
    ) -> object: ...


class _ScanRunRepoProtocol(Protocol):
    def save_run(self, record: UniverseScanRunRecord) -> object: ...

    def update_run(self, record: UniverseScanRunRecord) -> object: ...


def _return_pct(bars: Sequence[EodhdBar], days_back: int) -> Decimal | None:
    """Compute the total return % between the last bar and the bar
    approximately ``days_back`` trading days earlier."""

    if len(bars) <= days_back:
        return None
    last = bars[-1].adjusted_close or bars[-1].close_price
    earlier = bars[-(days_back + 1)].adjusted_close or bars[-(days_back + 1)].close_price
    if last is None or earlier is None or earlier <= 0:
        return None
    return (last / earlier - Decimal("1")) * Decimal("100")


def _to_fundamentals_entry(
    record: AssetFundamentalsSnapshotRecord,
) -> FundamentalsEntry:
    """Translate a persisted snapshot to the predictor's input shape."""

    return FundamentalsEntry(
        symbol=record.symbol,
        sector=record.sector,
        pe_ratio=record.pe_ratio,
        pb_ratio=record.pb_ratio,
        ev_ebitda=record.ev_ebitda,
        roic_pct=record.roic_pct,
        gross_margin_pct=record.gross_margin_pct,
        return_6m_pct=record.return_6m_pct,
        return_12m_pct=record.return_12m_pct,
    )


def _has_any_qvm_factor(record: AssetFundamentalsSnapshotRecord) -> bool:
    return any(
        v is not None
        for v in (
            record.roic_pct,
            record.gross_margin_pct,
            record.pe_ratio,
            record.pb_ratio,
            record.ev_ebitda,
            record.return_6m_pct,
            record.return_12m_pct,
        )
    )


def _build_snapshot(
    *,
    entry: UniverseEntry,
    fundamentals: EodhdFundamentals,
    bars: Sequence[EodhdBar],
    now: datetime,
) -> AssetFundamentalsSnapshotRecord:
    # If EODHD didn't ship 6m/12m returns directly, derive them from bars.
    return_6m_pct = fundamentals.return_6m_pct or _return_pct(bars, 126)
    return_12m_pct = fundamentals.return_12m_pct or _return_pct(bars, 252)
    return AssetFundamentalsSnapshotRecord(
        snapshot_id=f"fnd_{uuid4().hex}",
        ibkr_conid=None,
        eodhd_symbol=fundamentals.eodhd_symbol,
        symbol=entry.symbol,
        sector=fundamentals.sector or entry.sector,
        currency=fundamentals.currency,
        market_cap=fundamentals.market_cap,
        pe_ratio=fundamentals.pe_ratio,
        pb_ratio=fundamentals.pb_ratio,
        ev_ebitda=fundamentals.ev_ebitda,
        roic_pct=fundamentals.roic_pct,
        gross_margin_pct=fundamentals.gross_margin_pct,
        dividend_yield_pct=fundamentals.dividend_yield_pct,
        return_6m_pct=return_6m_pct,
        return_12m_pct=return_12m_pct,
        raw_payload_hash=fundamentals.raw_payload_hash,
        provider_code=PROVIDER_CODE,
        fetched_at=now,
        stored_at=now,
    )


def scan_universe(
    *,
    client: _EodhdClientProtocol,
    snapshot_repo: _SnapshotRepoProtocol,
    scan_repo: _ScanRunRepoProtocol,
    max_tickers: int,
    history_lookback_days: int,
    triggered_by: str = "manual",
    universe: Sequence[UniverseEntry] | None = None,
    universe_set: str | None = None,
    cache_ttl_hours: int = 0,
    now: datetime | None = None,
) -> UniverseScanReport:
    """Run one universe scan.

    Reports per-ticker failures rather than raising. The scan run row
    is written as ``running`` first, then updated to
    ``succeeded`` / ``failed`` on completion so the audit chain shows
    in-progress state.

    V1.1 §22.4: when ``universe_set`` is supplied it selects the
    operator-locked set (``SP500`` / ``EU600`` / ``ALL_5K``); when
    ``universe`` is supplied explicitly it overrides the set; when
    neither is supplied the default ``SP500`` set is used.

    V1.1 §22.4 cache TTL: when ``cache_ttl_hours > 0`` the scan
    skips any symbol whose latest persisted snapshot is younger
    than the TTL — keeps EODHD call volume sane on the ALL_5K set.
    """

    requested_at = datetime.now(UTC)
    actual_now = now or requested_at
    if universe is not None:
        target_universe = tuple(universe)
    elif universe_set is not None:
        target_universe = locked_universe(universe_set)
    else:
        target_universe = locked_universe()
    universe_size = len(target_universe)
    batch = target_universe[: max(0, max_tickers)]
    run_id = f"usr_{uuid4().hex}"
    cache_cutoff = (
        actual_now - timedelta(hours=cache_ttl_hours)
        if cache_ttl_hours > 0
        else None
    )

    initial = UniverseScanRunRecord(
        run_id=run_id,
        started_at=actual_now,
        finished_at=None,
        status="running",
        triggered_by=triggered_by,
        scanned_count=0,
        persisted_count=0,
        failed_count=0,
        ranked_count=0,
        universe_size=universe_size,
        error_text=None,
    )
    try:
        scan_repo.save_run(initial)
    except Exception:
        logger.exception("could not persist initial universe-scan run")

    failures: list[dict[str, str]] = []
    persisted: list[AssetFundamentalsSnapshotRecord] = []
    failed = 0

    from_date = actual_now.date() - timedelta(days=max(history_lookback_days, 60))
    to_date = actual_now.date()

    for entry in batch:
        # V1.1 §22.4 cache-TTL skip: if the persisted snapshot is
        # younger than the TTL, reuse it and avoid the EODHD call.
        if cache_cutoff is not None:
            try:
                cached = snapshot_repo.get_latest_snapshot_for_symbol(
                    entry.eodhd_symbol
                )
            except Exception:  # noqa: BLE001 — cache lookup is opportunistic
                cached = None
            cached_record = getattr(cached, "record", None)
            if cached_record is not None:
                fetched_at = getattr(cached_record, "fetched_at", None)
                if fetched_at is not None and fetched_at >= cache_cutoff:
                    persisted.append(cached_record)
                    continue

        try:
            fundamentals = client.fetch_fundamentals(entry.eodhd_symbol)
        except EodhdClientError as exc:
            failed += 1
            failures.append(
                {
                    "eodhd_symbol": entry.eodhd_symbol,
                    "reason": "fundamentals_fetch_failed",
                    "detail": str(exc),
                }
            )
            continue
        try:
            bars = client.fetch_eod_bars(
                entry.eodhd_symbol, from_date=from_date, to_date=to_date
            )
        except EodhdClientError as exc:
            bars = []
            failures.append(
                {
                    "eodhd_symbol": entry.eodhd_symbol,
                    "reason": "bars_fetch_failed",
                    "detail": str(exc),
                }
            )
        record = _build_snapshot(
            entry=entry,
            fundamentals=fundamentals,
            bars=bars,
            now=actual_now,
        )
        try:
            snapshot_repo.save_snapshot(record)
        except Exception as exc:  # noqa: BLE001 — boundary catch
            failed += 1
            failures.append(
                {
                    "eodhd_symbol": entry.eodhd_symbol,
                    "reason": "persistence_failed",
                    "detail": str(exc),
                }
            )
            continue
        persisted.append(record)

    scanned_count = len(batch)
    persisted_count = len(persisted)
    ranked_count = sum(1 for r in persisted if _has_any_qvm_factor(r))

    completed_at = datetime.now(UTC)
    if scanned_count == 0:
        status = "skipped"
        status_nl = "Geen tickers in de batch"
        help_nl = "Verhoog `universe_scan_max_tickers_per_run` of vul de universe-registry."
    elif persisted_count == 0:
        status = "failed"
        status_nl = "Universe-scan zonder geslaagde tickers"
        help_nl = "Controleer failures voor EODHD-fouten of opslagproblemen."
    else:
        status = "succeeded"
        status_nl = "Universe-scan voltooid"
        help_nl = (
            f"{persisted_count}/{scanned_count} tickers gepersisteerd; "
            f"{ranked_count} kandidaten met QVM-bouwstenen."
        )

    final = UniverseScanRunRecord(
        run_id=run_id,
        started_at=actual_now,
        finished_at=completed_at,
        status=status,
        triggered_by=triggered_by,
        scanned_count=scanned_count,
        persisted_count=persisted_count,
        failed_count=failed,
        ranked_count=ranked_count,
        universe_size=universe_size,
        error_text=None,
    )
    try:
        scan_repo.update_run(final)
    except Exception:
        logger.exception("could not update universe-scan run to final state")

    return UniverseScanReport(
        run_id=run_id,
        requested_at=requested_at,
        completed_at=completed_at,
        status=status,
        status_nl=status_nl,
        help_nl=help_nl,
        universe_size=universe_size,
        scanned_count=scanned_count,
        persisted_count=persisted_count,
        failed_count=failed,
        ranked_count=ranked_count,
        blocking_reason=None if status == "succeeded" else status,
        failures=tuple(failures),
    )


def build_universe_fundamentals(
    snapshots: Sequence[AssetFundamentalsSnapshotRecord],
) -> UniverseFundamentals:
    """Translate persisted snapshots into the QVM predictor's input."""

    return UniverseFundamentals(
        entries=tuple(_to_fundamentals_entry(s) for s in snapshots)
    )


__all__ = [
    "UniverseScanReport",
    "scan_universe",
    "build_universe_fundamentals",
    "PROVIDER_CODE",
]
