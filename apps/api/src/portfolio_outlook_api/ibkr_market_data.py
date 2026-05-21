from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from ai_trading_agent_storage import MarketDataLatestSnapshotRecord
from portfolio_outlook_domain.market_data_foundation import (
    MarketDataFetchResult,
    MarketDataFetchStatus,
    MarketDataIdentity,
    MarketDataSnapshot,
    block_if_identity_invalid,
)

from .config import Settings


@dataclass(frozen=True)
class IbkrMarketDataSettings:
    enabled: bool = False
    host: str | None = None
    port: int | None = None
    client_id: int | None = None
    readonly: bool = True
    account_mode: str = "paper"
    market_data_type: str = "delayed"
    snapshot_timeout_seconds: int = 5
    provider_code: str = "ibkr"


def settings_from_runtime(settings: Settings) -> IbkrMarketDataSettings:
    return IbkrMarketDataSettings(
        enabled=settings.ibkr_market_data_enabled,
        host=settings.ibkr_market_data_host,
        port=settings.ibkr_market_data_port,
        client_id=settings.ibkr_market_data_client_id,
        readonly=settings.ibkr_market_data_readonly,
        account_mode=settings.ibkr_market_data_account_mode,
        market_data_type=settings.ibkr_market_data_type,
        snapshot_timeout_seconds=settings.ibkr_market_data_snapshot_timeout_seconds,
        provider_code=settings.ibkr_market_data_provider_code,
    )


class IbkrMarketDataAdapter:
    def __init__(self, settings: IbkrMarketDataSettings) -> None:
        self._settings = settings

    def fetch_latest_snapshot(self, identity: MarketDataIdentity) -> MarketDataFetchResult:
        blocked = block_if_identity_invalid(identity)
        if blocked is not None:
            return blocked
        if not self._is_configured():
            return MarketDataFetchResult(
                status=MarketDataFetchStatus.NOT_CONFIGURED,
                snapshot=None,
                message_nl="IBKR marktdata is niet geconfigureerd.",
            )
        return MarketDataFetchResult(
            status=MarketDataFetchStatus.PROVIDER_ERROR,
            snapshot=None,
            message_nl=("IBKR marktdata-adapter skeleton actief; "
            "providerkoppeling nog niet geïmplementeerd."),
        )

    def _is_configured(self) -> bool:
        return (
            self._settings.enabled
            and self._settings.readonly
            and self._settings.account_mode == "paper"
            and bool(self._settings.host)
            and self._settings.port is not None
            and self._settings.client_id is not None
        )


def build_storage_record(
    snapshot: MarketDataSnapshot,
    status: str,
    explanation_nl: str,
) -> MarketDataLatestSnapshotRecord:
    return MarketDataLatestSnapshotRecord(
        snapshot_id=f"md_latest_{uuid4().hex}",
        ibkr_conid=snapshot.ibkr_conid,
        symbol=snapshot.symbol,
        currency=snapshot.currency,
        asset_class=None,
        exchange=None,
        primary_exchange=None,
        provider_code=snapshot.provider_code,
        provider_environment=snapshot.provider_environment,
        provider_account_mode=snapshot.provider_account_mode,
        market_data_type=snapshot.request_kind,
        requested_at=snapshot.requested_at,
        received_at=snapshot.received_at,
        provider_as_of=snapshot.provider_as_of,
        stored_at=datetime.now(UTC),
        last_price=snapshot.last_price,
        bid_price=snapshot.bid_price,
        ask_price=snapshot.ask_price,
        close_price=None,
        day_change_percent=snapshot.day_change_percent,
        status=status,
        freshness_status="fresh",
        explanation_nl=explanation_nl,
        request_log_id=None,
        provider_source_id=None,
        freshness_audit_id=None,
        safe_for_analysis=False,
        safe_for_suggestions=False,
        safe_for_action_drafts=False,
    )
