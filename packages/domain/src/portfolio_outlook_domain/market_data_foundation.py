from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Protocol


class MarketDataFetchStatus(StrEnum):
    SUCCESS = "success"
    NOT_CONFIGURED = "not_configured"
    MISSING_IDENTITY = "missing_identity"
    IDENTITY_NOT_VALIDATED = "identity_not_validated"
    PROVIDER_PERMISSION_MISSING = "provider_permission_missing"
    PACING_LIMITED = "pacing_limited"
    NO_SNAPSHOT = "no_snapshot"
    PROVIDER_ERROR = "provider_error"
    STORAGE_ERROR = "storage_error"
    STALE_SNAPSHOT = "stale_snapshot"
    SNAPSHOT_AVAILABLE = "snapshot_available"
    PROVIDER_NOT_CONFIGURED = "provider_not_configured"


@dataclass(frozen=True)
class MarketDataIdentity:
    ibkr_conid: str
    identity_validated: bool


@dataclass(frozen=True)
class MarketDataSnapshot:
    ibkr_conid: str
    symbol: str
    currency: str
    requested_at: datetime
    received_at: datetime
    provider_as_of: datetime | None
    stored_at: datetime
    provider_code: str
    provider_environment: str
    provider_account_mode: str
    data_domain: str
    request_kind: str
    source_type: str
    last_price: Decimal | None
    bid_price: Decimal | None
    ask_price: Decimal | None
    day_change_percent: Decimal | None


@dataclass(frozen=True)
class MarketDataFetchResult:
    status: MarketDataFetchStatus
    snapshot: MarketDataSnapshot | None
    message_nl: str


class MarketDataProviderPort(Protocol):
    def fetch_latest_snapshot(self, identity: MarketDataIdentity) -> MarketDataFetchResult: ...


def block_if_identity_invalid(identity: MarketDataIdentity) -> MarketDataFetchResult | None:
    if not identity.ibkr_conid.strip():
        return MarketDataFetchResult(
            status=MarketDataFetchStatus.MISSING_IDENTITY,
            snapshot=None,
            message_nl="Contract ontbreekt: geen gevalideerde conid beschikbaar.",
        )
    if not identity.identity_validated:
        return MarketDataFetchResult(
            status=MarketDataFetchStatus.IDENTITY_NOT_VALIDATED,
            snapshot=None,
            message_nl="Contract niet gevalideerd: snapshot-aanvraag geblokkeerd.",
        )
    return None


class MarketDataFreshnessStatus(StrEnum):
    MISSING_SNAPSHOT = "missing_snapshot"
    FRESH = "fresh"
    NEAR_STALE = "near_stale"
    STALE = "stale"
    UNUSABLE = "unusable"


class MarketDataValuationReadinessStatus(StrEnum):
    NOT_READY = "not_ready"
    READY_FOR_STATUS_ONLY = "ready_for_status_only"
    READY_FOR_VALUATION_PREVIEW = "ready_for_valuation_preview"
    BLOCKED_MISSING_SNAPSHOT = "blocked_missing_snapshot"
    BLOCKED_STALE_SNAPSHOT = "blocked_stale_snapshot"
    BLOCKED_MISSING_PRICE = "blocked_missing_price"


class MarketDataPriceBasis(StrEnum):
    LAST = "last"
    MIDPOINT = "midpoint"
    CLOSE = "close"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class MarketDataReadinessPolicy:
    fresh_within: timedelta = timedelta(minutes=15)
    near_stale_within: timedelta = timedelta(minutes=30)


@dataclass(frozen=True)
class MarketDataReadinessEvaluation:
    freshness_status: MarketDataFreshnessStatus
    valuation_readiness_status: MarketDataValuationReadinessStatus
    price_basis: MarketDataPriceBasis
    usable_price: Decimal | None
    snapshot_age_seconds: int | None


def evaluate_market_data_readiness(
    *,
    snapshot: MarketDataSnapshot | None,
    now: datetime,
    policy: MarketDataReadinessPolicy,
) -> MarketDataReadinessEvaluation:
    if snapshot is None:
        return MarketDataReadinessEvaluation(
            freshness_status=MarketDataFreshnessStatus.MISSING_SNAPSHOT,
            valuation_readiness_status=MarketDataValuationReadinessStatus.BLOCKED_MISSING_SNAPSHOT,
            price_basis=MarketDataPriceBasis.UNAVAILABLE,
            usable_price=None,
            snapshot_age_seconds=None,
        )
    reference_timestamp = snapshot.provider_as_of or snapshot.received_at or snapshot.stored_at
    age_seconds = int((now - reference_timestamp).total_seconds())
    if age_seconds < 0:
        age_seconds = 0
    age = timedelta(seconds=age_seconds)
    if age <= policy.fresh_within:
        freshness = MarketDataFreshnessStatus.FRESH
    elif age <= policy.near_stale_within:
        freshness = MarketDataFreshnessStatus.NEAR_STALE
    else:
        freshness = MarketDataFreshnessStatus.STALE

    if snapshot.last_price is not None:
        basis = MarketDataPriceBasis.LAST
        price = snapshot.last_price
    elif snapshot.bid_price is not None and snapshot.ask_price is not None:
        basis = MarketDataPriceBasis.MIDPOINT
        price = (snapshot.bid_price + snapshot.ask_price) / Decimal("2")
    else:
        basis = MarketDataPriceBasis.UNAVAILABLE
        price = None

    if freshness is MarketDataFreshnessStatus.STALE:
        readiness = MarketDataValuationReadinessStatus.BLOCKED_STALE_SNAPSHOT
    elif price is None:
        readiness = MarketDataValuationReadinessStatus.BLOCKED_MISSING_PRICE
    else:
        readiness = MarketDataValuationReadinessStatus.READY_FOR_VALUATION_PREVIEW
    return MarketDataReadinessEvaluation(
        freshness_status=freshness,
        valuation_readiness_status=readiness,
        price_basis=basis,
        usable_price=price,
        snapshot_age_seconds=age_seconds,
    )
