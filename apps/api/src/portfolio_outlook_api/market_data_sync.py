"""Orchestrator that fetches market-data + FX from a provider and persists
them into the existing storage tables consumed by
``portfolio_valuation_readiness``.

The orchestrator does not invent values: every persisted row is grounded in
either an EODHD response or an explicit ``unknown_exchange`` /
``provider_error`` failure record. Default-off; the route handler decides
whether to invoke it based on ``settings.market_data_sync_enabled``.

Identity / exchange mapping
---------------------------

IBKR position snapshots already carry ``conid`` + ``symbol`` +
``primary_exchange``. EODHD uses ``{SYMBOL}.{SUFFIX}`` where the suffix maps
from the IBKR exchange code. ``IBKR_TO_EODHD_EXCHANGE`` keeps the mapping in
one place; unknown exchanges are skipped with a recorded reason.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    FxRateSnapshotRecord,
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    MarketDataLatestSnapshotRecord,
)

from portfolio_outlook_api.eodhd_client import (
    EodhdAuthError,
    EodhdClientError,
    EodhdFxRate,
    EodhdMarketDataProvider,
    EodhdNotFoundError,
    EodhdQuote,
    EodhdRateLimitError,
)

logger = logging.getLogger(__name__)


IBKR_TO_EODHD_EXCHANGE: dict[str, str] = {
    # US listings
    "NYSE": "US",
    "NASDAQ": "US",
    "NASDAQ.NMS": "US",
    "NMS": "US",
    "ARCA": "US",
    "AMEX": "US",
    "BATS": "US",
    "PINK": "US",
    "ISLAND": "US",
    "ISE": "US",
    # Euronext
    "AEB": "AS",
    "EBS": "AS",
    "ENEXT.BE": "BR",
    "EBR": "BR",
    "BRU": "BR",
    "SBF": "PA",
    "EPA": "PA",
    "ENEXT.LIS": "LS",
    # Germany
    "IBIS": "XETRA",
    "IBIS2": "XETRA",
    "XETR": "XETRA",
    "FWB": "F",
    "TRADEGATE": "DE",
    # UK / Ireland
    "LSE": "LSE",
    "LSEETF": "LSE",
    "ISED": "IR",
    # Switzerland
    "EBS.CHE": "SW",
    "SWX": "SW",
    "VIRTX": "VX",
    # Spain
    "BM": "MC",
    # Italy
    "BVME": "MI",
    "MIL": "MI",
    # Nordics
    "SFB": "ST",
    "OMX": "ST",
    "OMXNO": "OL",
    "OSE": "OL",
    "HEX": "HE",
    "OMXC": "CO",
}


PROVIDER_CODE_EODHD = "eodhd"


@dataclass(frozen=True)
class MarketDataSyncReport:
    """Summary of what one sync run did, returned to the route handler."""

    requested_at: datetime
    completed_at: datetime
    provider_code: str
    asset_total: int
    asset_success: int
    asset_skipped_unknown_exchange: int
    asset_failed: int
    fx_total: int
    fx_success: int
    fx_failed: int
    failures: tuple[dict[str, str], ...]
    market_snapshots_persisted: int
    fx_snapshots_persisted: int
    base_currency: str | None
    status_nl: str
    help_nl: str


class _MarketDataRepoProtocol(Protocol):
    def save_latest_market_data_snapshot(
        self, record: MarketDataLatestSnapshotRecord
    ) -> object: ...


class _FxRepoProtocol(Protocol):
    def save_fx_rate_snapshot(self, record: FxRateSnapshotRecord) -> None: ...


def map_ibkr_exchange_to_eodhd(primary_exchange: str | None) -> str | None:
    """Return the EODHD suffix for a given IBKR exchange code, or ``None`` if
    the exchange is unsupported in this version."""

    if primary_exchange is None:
        return None
    key = primary_exchange.strip().upper()
    if not key:
        return None
    return IBKR_TO_EODHD_EXCHANGE.get(key)


def derive_required_fx_pairs(
    *,
    positions: Iterable[IbkrPositionSnapshotRecord],
    cash_snapshots: Iterable[IbkrAccountCashSnapshotRecord],
) -> tuple[list[tuple[str, str]], str | None]:
    """Determine which FX pairs the portfolio needs to value itself.

    Returns ``(pairs, base_currency)`` where ``pairs`` is a list of
    ``(base, quote)`` tuples like ``("USD", "EUR")`` meaning "I need the price
    of 1 USD expressed in EUR". This matches the
    ``portfolio_valuation_readiness`` consumer, which calls the pair
    ``"USD/EUR"`` and reads it as the rate to convert USD into EUR.

    ``base_currency`` is the single cash currency if all cash is in one
    currency, otherwise ``None`` — the same rule the valuation engine uses.
    """

    cash_currencies = sorted({c.base_currency for c in cash_snapshots if c.base_currency})
    base_currency = cash_currencies[0] if len(cash_currencies) == 1 else None
    if base_currency is None:
        return [], None
    portfolio_currencies = {
        (p.currency or "").strip().upper() for p in positions if (p.currency or "").strip()
    }
    all_currencies = sorted({c.upper() for c in cash_currencies} | portfolio_currencies)
    pairs = [
        (currency, base_currency.upper())
        for currency in all_currencies
        if currency and currency != base_currency.upper()
    ]
    return pairs, base_currency.upper()


def build_eodhd_market_snapshot_record(
    *,
    position: IbkrPositionSnapshotRecord,
    quote: EodhdQuote,
    eodhd_suffix: str,
    requested_at: datetime,
    received_at: datetime,
    stored_at: datetime,
) -> MarketDataLatestSnapshotRecord:
    """Map an EODHD quote + the originating IBKR position to a storage record.

    All ``safe_for_*`` flags stay ``False`` per the V1 safety contract.
    """

    explanation = (
        f"EODHD real-time quote ({position.symbol}.{eodhd_suffix}); read-only, "
        "geen analyse, geen suggesties, geen orders."
    )
    return MarketDataLatestSnapshotRecord(
        snapshot_id=f"md_latest_eodhd_{uuid4().hex}",
        ibkr_conid=position.conid or "",
        symbol=position.symbol,
        currency=position.currency,
        asset_class=position.security_type,
        exchange=position.exchange,
        primary_exchange=position.primary_exchange,
        provider_code=PROVIDER_CODE_EODHD,
        provider_environment="real",
        provider_account_mode="none",
        market_data_type="eod",
        requested_at=requested_at,
        received_at=received_at,
        provider_as_of=quote.provider_as_of,
        stored_at=stored_at,
        last_price=quote.last_price,
        bid_price=None,
        ask_price=None,
        close_price=quote.last_price,
        day_change_percent=quote.day_change_percent,
        status="snapshot_available" if quote.last_price is not None else "missing_price",
        freshness_status="fresh" if quote.last_price is not None else "unusable",
        explanation_nl=explanation,
        request_log_id=None,
        provider_source_id=None,
        freshness_audit_id=None,
    )


def build_eodhd_fx_snapshot_record(
    *,
    rate: EodhdFxRate,
    requested_at: datetime,
    received_at: datetime,
    stored_at: datetime,
) -> FxRateSnapshotRecord:
    """Map an EODHD FX rate to an ``FxRateSnapshotRecord`` keyed by
    ``base_currency/quote_currency``. EODHD's ``BASEQUOTE.FOREX`` returns
    "1 BASE = X QUOTE" which matches the valuation engine's interpretation.
    """

    rate_value = rate.rate
    if rate_value is None or rate_value <= 0:
        validation_status = "invalid"
        reason_code = "missing_rate" if rate_value is None else "non_positive_rate"
        freshness = "unusable"
        usable_rate = Decimal("0")
    else:
        validation_status = "valid"
        reason_code = "ok"
        freshness = "fresh"
        usable_rate = rate_value
    return FxRateSnapshotRecord(
        snapshot_id=f"fx_eodhd_{uuid4().hex}",
        provider=PROVIDER_CODE_EODHD,
        source="real-time",
        base_currency=rate.base_currency,
        quote_currency=rate.quote_currency,
        pair=f"{rate.base_currency.upper()}/{rate.quote_currency.upper()}",
        rate=usable_rate,
        rate_type="spot",
        as_of=rate.provider_as_of or received_at,
        received_at=received_at,
        stored_at=stored_at,
        freshness_status=freshness,
        validation_status=validation_status,
        reason_code=reason_code,
        metadata_json={"previous_close": str(rate.previous_close)} if rate.previous_close else None,
    )


def sync_market_data_and_fx(
    *,
    provider: EodhdMarketDataProvider,
    market_repo: _MarketDataRepoProtocol,
    fx_repo: _FxRepoProtocol,
    positions: list[IbkrPositionSnapshotRecord],
    cash_snapshots: list[IbkrAccountCashSnapshotRecord],
    max_assets: int,
) -> MarketDataSyncReport:
    """Run one full sync cycle and persist every successful row.

    The caller is responsible for fetching the latest position + cash
    snapshots from storage. This function only orchestrates and persists. It
    catches provider errors per-asset so one bad symbol doesn't sink the
    whole batch.
    """

    requested_at = datetime.now(UTC)
    failures: list[dict[str, str]] = []
    asset_success = 0
    asset_skipped = 0
    asset_failed = 0
    market_persisted = 0

    # De-duplicate positions by conid (a single conid may appear multiple
    # times across cash splits etc.) and limit to ``max_assets`` to avoid
    # blowing through EODHD quotas on the first run.
    seen_conids: set[str] = set()
    unique_positions: list[IbkrPositionSnapshotRecord] = []
    for position in positions:
        conid_key = (position.conid or "").strip()
        if not conid_key or conid_key in seen_conids:
            continue
        seen_conids.add(conid_key)
        unique_positions.append(position)
        if len(unique_positions) >= max_assets:
            break

    for position in unique_positions:
        symbol = (position.symbol or "").strip()
        if not symbol:
            asset_failed += 1
            failures.append(
                {
                    "kind": "market_data",
                    "conid": position.conid or "",
                    "reason": "missing_symbol",
                }
            )
            continue
        suffix = map_ibkr_exchange_to_eodhd(position.primary_exchange or position.exchange)
        if suffix is None:
            asset_skipped += 1
            failures.append(
                {
                    "kind": "market_data",
                    "conid": position.conid or "",
                    "symbol": symbol,
                    "primary_exchange": position.primary_exchange or position.exchange or "",
                    "reason": "unknown_exchange",
                }
            )
            continue
        eodhd_symbol = f"{symbol}.{suffix}"
        try:
            quote = provider.fetch_quote(eodhd_symbol)
        except EodhdAuthError as exc:
            asset_failed += 1
            failures.append(
                {
                    "kind": "market_data",
                    "conid": position.conid or "",
                    "symbol": eodhd_symbol,
                    "reason": "auth_error",
                    "detail": str(exc),
                }
            )
            # An auth error will hit every subsequent call too; stop early.
            break
        except EodhdNotFoundError as exc:
            asset_failed += 1
            failures.append(
                {
                    "kind": "market_data",
                    "conid": position.conid or "",
                    "symbol": eodhd_symbol,
                    "reason": "not_found",
                    "detail": str(exc),
                }
            )
            continue
        except EodhdRateLimitError as exc:
            asset_failed += 1
            failures.append(
                {
                    "kind": "market_data",
                    "conid": position.conid or "",
                    "symbol": eodhd_symbol,
                    "reason": "rate_limited",
                    "detail": str(exc),
                }
            )
            break
        except EodhdClientError as exc:
            asset_failed += 1
            failures.append(
                {
                    "kind": "market_data",
                    "conid": position.conid or "",
                    "symbol": eodhd_symbol,
                    "reason": "provider_error",
                    "detail": str(exc),
                }
            )
            continue

        if quote.last_price is None:
            asset_failed += 1
            failures.append(
                {
                    "kind": "market_data",
                    "conid": position.conid or "",
                    "symbol": eodhd_symbol,
                    "reason": "missing_price",
                }
            )
            continue

        received_at = datetime.now(UTC)
        record = build_eodhd_market_snapshot_record(
            position=position,
            quote=quote,
            eodhd_suffix=suffix,
            requested_at=requested_at,
            received_at=received_at,
            stored_at=received_at,
        )
        market_repo.save_latest_market_data_snapshot(record)
        market_persisted += 1
        asset_success += 1

    # FX sync ------------------------------------------------------------
    pairs, base_currency = derive_required_fx_pairs(
        positions=unique_positions,
        cash_snapshots=cash_snapshots,
    )
    fx_persisted = 0
    fx_success = 0
    fx_failed = 0
    for base, quote_ccy in pairs:
        try:
            fx_rate = provider.fetch_fx_rate(base, quote_ccy)
        except EodhdAuthError as exc:
            fx_failed += 1
            failures.append(
                {
                    "kind": "fx",
                    "pair": f"{base}/{quote_ccy}",
                    "reason": "auth_error",
                    "detail": str(exc),
                }
            )
            break
        except EodhdRateLimitError as exc:
            fx_failed += 1
            failures.append(
                {
                    "kind": "fx",
                    "pair": f"{base}/{quote_ccy}",
                    "reason": "rate_limited",
                    "detail": str(exc),
                }
            )
            break
        except EodhdNotFoundError as exc:
            fx_failed += 1
            failures.append(
                {
                    "kind": "fx",
                    "pair": f"{base}/{quote_ccy}",
                    "reason": "not_found",
                    "detail": str(exc),
                }
            )
            continue
        except EodhdClientError as exc:
            fx_failed += 1
            failures.append(
                {
                    "kind": "fx",
                    "pair": f"{base}/{quote_ccy}",
                    "reason": "provider_error",
                    "detail": str(exc),
                }
            )
            continue

        fx_received_at = datetime.now(UTC)
        fx_record = build_eodhd_fx_snapshot_record(
            rate=fx_rate,
            requested_at=requested_at,
            received_at=fx_received_at,
            stored_at=fx_received_at,
        )
        fx_repo.save_fx_rate_snapshot(fx_record)
        fx_persisted += 1
        if fx_record.validation_status == "valid":
            fx_success += 1
        else:
            fx_failed += 1
            failures.append(
                {
                    "kind": "fx",
                    "pair": fx_record.pair,
                    "reason": fx_record.reason_code,
                }
            )

    completed_at = datetime.now(UTC)

    if asset_success == 0 and fx_success == 0:
        status_nl = "Marktdata-sync mislukt"
        help_nl = (
            "Geen marktdata of FX-snapshots opgeslagen. "
            "Controleer EODHD-configuratie en symbol/exchange mapping."
        )
    elif asset_failed > 0 or fx_failed > 0:
        status_nl = "Marktdata-sync gedeeltelijk voltooid"
        help_nl = (
            "Sommige assets of wisselkoersen konden niet worden opgehaald; "
            "details staan in 'failures'."
        )
    else:
        status_nl = "Marktdata-sync voltooid"
        help_nl = "Alle vereiste marktdata en wisselkoersen zijn opgeslagen."

    return MarketDataSyncReport(
        requested_at=requested_at,
        completed_at=completed_at,
        provider_code=PROVIDER_CODE_EODHD,
        asset_total=len(unique_positions),
        asset_success=asset_success,
        asset_skipped_unknown_exchange=asset_skipped,
        asset_failed=asset_failed,
        fx_total=len(pairs),
        fx_success=fx_success,
        fx_failed=fx_failed,
        failures=tuple(failures),
        market_snapshots_persisted=market_persisted,
        fx_snapshots_persisted=fx_persisted,
        base_currency=base_currency,
        status_nl=status_nl,
        help_nl=help_nl,
    )
