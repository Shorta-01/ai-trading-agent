from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
