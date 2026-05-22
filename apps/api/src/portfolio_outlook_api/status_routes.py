"""Routes for read-only status/settings summaries."""

from datetime import UTC, datetime
from typing import Annotated

from ai_trading_agent_storage import (
    SqlAlchemyIbkrSyncSnapshotRepository,
    SqlAlchemyMarketDataSnapshotRepository,
    SqlAlchemyResearchSourceArchiveRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, Body, HTTPException
from portfolio_outlook_domain.market_data_foundation import (
    MarketDataFetchStatus,
    MarketDataIdentity,
    MarketDataPriceBasis,
    MarketDataReadinessPolicy,
    MarketDataSnapshot,
    evaluate_market_data_readiness,
)

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.ibkr_contracts import search_ibkr_contracts, validate_ibkr_contract
from portfolio_outlook_api.ibkr_market_data import IbkrMarketDataAdapter, settings_from_runtime
from portfolio_outlook_api.ibkr_status import build_ibkr_status_placeholder
from portfolio_outlook_api.ibkr_sync import read_status, run_sync
from portfolio_outlook_api.ibkr_sync_read_model import (
    read_latest_ibkr_sync_run,
    serialize_cash_record,
    serialize_execution_record,
    serialize_open_order_record,
    serialize_position_record,
    serialize_sync_status_record,
)
from portfolio_outlook_api.ibkr_watchlists import (
    import_by_id,
    import_ibkr_watchlist,
    latest_import,
    list_ibkr_watchlist_instruments,
    list_ibkr_watchlists,
)
from portfolio_outlook_api.market_data_readiness import (
    READINESS_HELP_NL,
    LatestSnapshotResponse,
    LatestSnapshotStatus,
    ReadinessAssetListingGate,
    ReadinessAssetListingGateStatus,
    ReadinessDetailResponse,
    ReadinessListResponse,
    ReadinessRow,
    ReadinessSnapshotMetadata,
    build_asset_listing_gate,
    build_latest_snapshot_response,
    build_readiness_row,
    build_readiness_snapshot_metadata,
    utc_now_iso,
)
from portfolio_outlook_api.online_storage_status import (
    OnlineStorageStatusResponse,
    build_online_storage_status,
)
from portfolio_outlook_api.paper_setup import (
    SetupPreviewInput,
    create_setup_preview,
    get_setup_defaults,
    get_setup_status,
)
from portfolio_outlook_api.paper_setup_persistence import persist_first_run_paper_setup
from portfolio_outlook_api.status_builders import (
    build_ai_usage_summary,
    build_dutch_labels_summary,
    build_integrations_summary,
    build_settings_summary,
    build_system_status_summary,
)
from portfolio_outlook_api.status_models import (
    AiUsageSummary,
    DutchLabelsSummary,
    IntegrationsSummary,
    SettingsSummary,
    SystemStatusSummary,
)
from portfolio_outlook_api.storage_status import (
    StorageStatusResponse,
    build_storage_status,
)
from portfolio_outlook_api.system_event_mutations import (
    SystemEventMutationInput,
    mark_system_event_archived,
    mark_system_event_resolved,
)
from portfolio_outlook_api.system_event_reader import (
    ActiveSystemEventsResponse,
    list_active_system_events,
)
from portfolio_outlook_api.trading_settings import (
    TradingSettingsUpdateInput,
    build_trading_settings_response,
    update_trading_settings_response,
)

router = APIRouter()


@router.get("/system/status", response_model=SystemStatusSummary)
def read_system_status() -> SystemStatusSummary:
    return build_system_status_summary()


@router.get("/settings/summary", response_model=SettingsSummary)
def read_settings_summary() -> SettingsSummary:
    return build_settings_summary()


@router.get("/settings/trading")
def read_trading_settings() -> dict[str, object]:
    return build_trading_settings_response(settings.storage)


@router.get("/usage/ai/summary", response_model=AiUsageSummary)
def read_ai_usage_summary() -> AiUsageSummary:
    return build_ai_usage_summary()


@router.get("/integrations/summary", response_model=IntegrationsSummary)
def read_integrations_summary() -> IntegrationsSummary:
    return build_integrations_summary()


@router.get("/ui/dutch-labels", response_model=DutchLabelsSummary)
def read_dutch_labels() -> DutchLabelsSummary:
    return build_dutch_labels_summary()


@router.get("/broker/ibkr/status")
def read_ibkr_status() -> dict[str, object]:
    return build_ibkr_status_placeholder(settings)


@router.get("/ibkr/session/status")
def read_ibkr_session_status() -> dict[str, object]:
    return build_ibkr_status_placeholder(settings)


@router.get("/portfolio/setup/status")
def read_portfolio_setup_status() -> dict[str, object]:
    return get_setup_status()


@router.get("/portfolio/setup/defaults")
def read_portfolio_setup_defaults() -> dict[str, object]:
    return get_setup_defaults()


@router.post("/portfolio/setup/preview")
def preview_portfolio_setup(payload: SetupPreviewInput) -> dict[str, object]:
    try:
        create_setup_preview(payload)
        result = persist_first_run_paper_setup(payload, settings.storage)
        if result.blocked:
            raise HTTPException(status_code=409, detail=result.response["message_nl"])
        return result.response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/storage/status", response_model=StorageStatusResponse)
def read_storage_status() -> StorageStatusResponse:
    return build_storage_status()


@router.get("/storage/status/online", response_model=OnlineStorageStatusResponse)
def read_storage_status_online() -> OnlineStorageStatusResponse:
    return build_online_storage_status(settings.storage)


@router.get("/system/events/active", response_model=ActiveSystemEventsResponse)
def read_active_system_events() -> ActiveSystemEventsResponse:
    return list_active_system_events(settings.storage)


@router.post("/system/events/{system_event_id}/resolve")
def resolve_system_event(
    system_event_id: str,
    payload: Annotated[SystemEventMutationInput | None, Body()] = None,
) -> dict[str, object]:
    mutation_payload = payload or SystemEventMutationInput()
    result = mark_system_event_resolved(system_event_id, settings.storage, mutation_payload)
    if result.not_found:
        raise HTTPException(status_code=404, detail=result.response["message_nl"])
    if result.blocked:
        raise HTTPException(status_code=409, detail=result.response["message_nl"])
    return result.response


@router.post("/system/events/{system_event_id}/archive")
def archive_system_event(
    system_event_id: str,
    payload: Annotated[SystemEventMutationInput | None, Body()] = None,
) -> dict[str, object]:
    mutation_payload = payload or SystemEventMutationInput()
    result = mark_system_event_archived(system_event_id, settings.storage, mutation_payload)
    if result.not_found:
        raise HTTPException(status_code=404, detail=result.response["message_nl"])
    if result.blocked:
        raise HTTPException(status_code=409, detail=result.response["message_nl"])
    return result.response


@router.put("/settings/trading")
def update_trading_settings(payload: TradingSettingsUpdateInput) -> dict[str, object]:
    return update_trading_settings_response(payload, settings.storage)


@router.get("/ibkr/sync/status")
def read_ibkr_sync_status() -> dict[str, object]:
    from portfolio_outlook_api.ibkr_sync import STORE

    durable = read_latest_ibkr_sync_run(settings.storage)
    if durable.latest_run is not None:
        return serialize_sync_status_record(durable.latest_run)

    memory_status = read_status(settings)
    if durable.storage_help_nl is not None:
        if STORE.runs:
            memory_status["help_nl"] = durable.storage_help_nl
        else:
            memory_status["help_nl"] = "Geen duurzame IBKR-syncrun gevonden."
    return memory_status


@router.post("/ibkr/sync/run")
def start_ibkr_sync_run() -> dict[str, object]:
    return run_sync(settings)


@router.get("/ibkr/portfolio/positions")
def read_ibkr_positions() -> dict[str, object]:
    from portfolio_outlook_api.ibkr_sync import STORE

    durable = read_latest_ibkr_sync_run(settings.storage)
    if durable.latest_run is not None:
        provider = StorageConnectionProvider(
            build_database_connection_settings(settings.storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyIbkrSyncSnapshotRepository(checked.connection, checked.readiness)
            records = repo.list_ibkr_position_snapshots(durable.latest_run.sync_run_id)
        return {
            "items": [serialize_position_record(item) for item in records],
            "help_nl": "Alleen gesynchroniseerde IBKR-posities (duurzame opslag).",
        }
    return {
        "items": STORE.positions,
        "help_nl": "Alleen gesynchroniseerde IBKR-posities.",
    }


@router.get("/ibkr/account/cash")
def read_ibkr_cash() -> dict[str, object]:
    from portfolio_outlook_api.ibkr_sync import STORE
    durable = read_latest_ibkr_sync_run(settings.storage)
    if durable.latest_run is not None:
        provider = StorageConnectionProvider(
            build_database_connection_settings(settings.storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyIbkrSyncSnapshotRepository(checked.connection, checked.readiness)
            records = repo.list_ibkr_account_cash_snapshots(durable.latest_run.sync_run_id)
        return {
            "items": [serialize_cash_record(item) for item in records],
            "help_nl": "Alleen gesynchroniseerde IBKR-cashgegevens (duurzame opslag).",
        }
    return {
        "items": STORE.cash,
        "help_nl": "Alleen gesynchroniseerde IBKR-cashgegevens.",
    }


@router.get("/ibkr/orders/open")
def read_ibkr_open_orders() -> dict[str, object]:
    from portfolio_outlook_api.ibkr_sync import STORE
    durable = read_latest_ibkr_sync_run(settings.storage)
    if durable.latest_run is not None:
        provider = StorageConnectionProvider(
            build_database_connection_settings(settings.storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyIbkrSyncSnapshotRepository(checked.connection, checked.readiness)
            records = repo.list_ibkr_open_order_snapshots(durable.latest_run.sync_run_id)
        return {
            "items": [serialize_open_order_record(item) for item in records],
            "help_nl": "Open orders alleen-lezen (duurzame opslag).",
            "actions_allowed": False,
        }
    return {
        "items": STORE.open_orders,
        "help_nl": "Open orders alleen-lezen",
        "actions_allowed": False,
    }


@router.get("/ibkr/executions")
def read_ibkr_executions() -> dict[str, object]:
    from portfolio_outlook_api.ibkr_sync import STORE
    durable = read_latest_ibkr_sync_run(settings.storage)
    if durable.latest_run is not None:
        provider = StorageConnectionProvider(
            build_database_connection_settings(settings.storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyIbkrSyncSnapshotRepository(checked.connection, checked.readiness)
            records = repo.list_ibkr_execution_snapshots(durable.latest_run.sync_run_id)
        return {
            "items": [serialize_execution_record(item) for item in records],
            "help_nl": "Uitvoeringen alleen-lezen (duurzame opslag).",
            "actions_allowed": False,
        }
    return {
        "items": STORE.executions,
        "help_nl": "Uitvoeringen alleen-lezen",
        "actions_allowed": False,
    }




@router.get("/ibkr/watchlists")
def read_ibkr_watchlists() -> dict[str, object]:
    return list_ibkr_watchlists(settings)


@router.get("/ibkr/watchlists/{watchlist_id}/instruments")
def read_ibkr_watchlist_instruments(watchlist_id: str) -> dict[str, object]:
    return list_ibkr_watchlist_instruments(settings, watchlist_id)


@router.post("/ibkr/watchlists/{watchlist_id}/import")
def prepare_ibkr_watchlist_import(watchlist_id: str) -> dict[str, object]:
    return import_ibkr_watchlist(settings, watchlist_id)


@router.get("/ibkr/watchlists/imports/latest")
def read_latest_ibkr_watchlist_import() -> dict[str, object]:
    return latest_import()


@router.get("/ibkr/watchlists/imports/{import_run_id}")
def read_ibkr_watchlist_import(import_run_id: str) -> dict[str, object]:
    return import_by_id(import_run_id)
@router.get("/ibkr/contracts/search")
def search_contracts(query: str = "", name: bool = False) -> dict[str, object]:
    return search_ibkr_contracts(settings, query, search_name=name)


@router.get("/ibkr/contracts/{conid}/details")
def contract_details(conid: str, security_type: str | None = None) -> dict[str, object]:
    return validate_ibkr_contract(settings, conid, security_type=security_type)


@router.post("/ibkr/contracts/validate")
def validate_contract(payload: dict[str, object]) -> dict[str, object]:
    conid = str(payload.get("ibkr_conid") or "")
    security_type = payload.get("security_type")
    return validate_ibkr_contract(
        settings,
        conid,
        security_type=None if security_type is None else str(security_type),
        asset_id=None if payload.get("asset_id") is None else str(payload.get("asset_id")),
        watchlist_item_id=(
            None
            if payload.get("watchlist_item_id") is None
            else str(payload.get("watchlist_item_id"))
        ),
    )


def _read_snapshot_metadata(ibkr_conid: str | None) -> ReadinessSnapshotMetadata | None:
    if not ibkr_conid:
        return None
    storage_settings = settings.storage
    if not storage_settings.enabled or not storage_settings.database_url:
        return None
    provider = StorageConnectionProvider(
        build_database_connection_settings(storage_settings.database_url)
    )
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyMarketDataSnapshotRepository(
                checked.connection,
                checked.readiness,
            )
            result = repo.get_latest_by_ibkr_conid(ibkr_conid)
            if result.record is None:
                return None
            return build_readiness_snapshot_metadata(result.record)
    except StorageConnectionError:
        return None



def _read_asset_listing_gate(item: object) -> ReadinessAssetListingGate:
    ibkr_conid = str(getattr(item, "ibkr_conid", "") or "").strip() or None
    storage_settings = settings.storage
    if not storage_settings.enabled or not storage_settings.database_url:
        return build_asset_listing_gate(
            status=ReadinessAssetListingGateStatus.STORAGE_UNAVAILABLE,
            ibkr_conid=ibkr_conid,
        )
    provider = StorageConnectionProvider(
        build_database_connection_settings(storage_settings.database_url)
    )
    try:
        with provider.checked_connection(require_writable=False) as checked:
            if ibkr_conid is None:
                return build_asset_listing_gate(
                    status=ReadinessAssetListingGateStatus.MISSING_IBKR_CONID,
                    ibkr_conid=None,
                )
            repo = SqlAlchemyResearchSourceArchiveRepository(
                checked.connection,
                checked.readiness,
            )
            listing = repo.get_asset_listing_by_ibkr_conid(ibkr_conid)
            if listing is None:
                return build_asset_listing_gate(
                    status=ReadinessAssetListingGateStatus.MISSING_LISTING,
                    ibkr_conid=ibkr_conid,
                )
            gate_status = (
                ReadinessAssetListingGateStatus.VALIDATED_LISTING
                if listing.safe_to_use_for_market_data and not listing.blocks_market_data
                else ReadinessAssetListingGateStatus.UNVALIDATED_LISTING
            )
            return build_asset_listing_gate(
                status=gate_status,
                listing_id=listing.listing_id,
                asset_id=listing.asset_id,
                ibkr_conid=listing.ibkr_conid,
                validation_status=listing.validation_status,
                safe_to_use_for_market_data=listing.safe_to_use_for_market_data,
                blocks_market_data=listing.blocks_market_data,
            )
    except StorageConnectionError:
        return build_asset_listing_gate(
            status=ReadinessAssetListingGateStatus.STORAGE_UNAVAILABLE,
            ibkr_conid=ibkr_conid,
        )
def _build_market_data_readiness_rows() -> list[ReadinessRow]:
    from portfolio_outlook_api.watchlist import STORE

    evaluated_at = utc_now_iso()
    rows: list[ReadinessRow] = []
    for item in STORE.values():
        if item.status != "active":
            continue
        conid = (item.ibkr_conid or "").strip()
        snapshot_metadata = _read_snapshot_metadata(conid if conid else None)
        rows.append(
            build_readiness_row(
                item,
                snapshot_metadata,
                _read_asset_listing_gate(item),
                evaluated_at=evaluated_at,
            )
        )
    return rows


@router.get("/market-data/readiness", response_model=ReadinessListResponse)
def read_market_data_readiness() -> ReadinessListResponse:
    return ReadinessListResponse(
        items=_build_market_data_readiness_rows(),
        help_nl=READINESS_HELP_NL,
        analysis_ready=False,
        suggestions_allowed=False,
        action_drafts_allowed=False,
    )


@router.get(
    "/market-data/readiness/watchlist/{watchlist_item_id}",
    response_model=ReadinessDetailResponse,
)
def read_market_data_readiness_watchlist_item(watchlist_item_id: str) -> ReadinessDetailResponse:
    for row in _build_market_data_readiness_rows():
        if row.watchlist_item_id == watchlist_item_id:
            return ReadinessDetailResponse(item=row)
    return ReadinessDetailResponse(item=None, message_nl="Volglijst-item niet gevonden.")




@router.post(
    "/market-data/snapshots/latest/{ibkr_conid}/fetch",
    response_model=LatestSnapshotResponse,
)
def fetch_market_data_snapshot_latest(ibkr_conid: str) -> LatestSnapshotResponse:
    evaluated_at = utc_now_iso()
    adapter = IbkrMarketDataAdapter(settings_from_runtime(settings))
    from portfolio_outlook_api.watchlist import STORE
    item = next(
        (
            w
            for w in STORE.values()
            if (w.ibkr_conid or "").strip() == ibkr_conid and w.status == "active"
        ),
        None,
    )
    identity_validated = bool(item and item.ibkr_validation_status == "valid")
    result = adapter.fetch_latest_snapshot(
        MarketDataIdentity(ibkr_conid=ibkr_conid, identity_validated=identity_validated)
    )
    response = build_latest_snapshot_response(
        ibkr_conid,
        None,
        status=(
            LatestSnapshotStatus.NOT_CONFIGURED
            if result.status == MarketDataFetchStatus.NOT_CONFIGURED
            else LatestSnapshotStatus.MISSING_SNAPSHOT
        ),
        status_nl=(
            "Niet geconfigureerd"
            if result.status == MarketDataFetchStatus.NOT_CONFIGURED
            else "Geen marktdata"
        ),
        evaluated_at=evaluated_at,
    )
    response.provider_code = settings.ibkr_market_data_provider_code
    response.provider_environment = settings.ibkr_expected_environment
    response.provider_account_mode = settings.ibkr_market_data_account_mode
    response.market_data_type = settings.ibkr_market_data_type
    response.next_step_nl = "Alleen status. Nog geen analyse."
    response.help_nl = "Nog geen suggesties mogelijk."
    return response
@router.get("/market-data/snapshots/latest/{ibkr_conid}", response_model=LatestSnapshotResponse)
def read_market_data_snapshot_latest(ibkr_conid: str) -> LatestSnapshotResponse:
    evaluated_at = utc_now_iso()
    storage_settings = settings.storage
    if not storage_settings.enabled or not storage_settings.database_url:
        return build_latest_snapshot_response(
            ibkr_conid,
            None,
            status=LatestSnapshotStatus.NOT_CONFIGURED,
            status_nl="Storage niet geconfigureerd.",
            missing_reason="storage_not_configured",
            evaluated_at=evaluated_at,
        )
    provider = StorageConnectionProvider(
        build_database_connection_settings(storage_settings.database_url)
    )
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyMarketDataSnapshotRepository(
                checked.connection,
                checked.readiness,
            )
            result = repo.get_latest_market_data_snapshot_by_conid(ibkr_conid)
            if result.record is None:
                return build_latest_snapshot_response(
                    ibkr_conid,
                    None,
                    status=LatestSnapshotStatus.MISSING_SNAPSHOT,
                    status_nl="Geen marktdata",
                    missing_reason="snapshot_not_found",
                    evaluated_at=evaluated_at,
                )
            record = result.record
            status = (
                LatestSnapshotStatus.STALE_SNAPSHOT
                if record.freshness_status == "stale"
                else LatestSnapshotStatus.SNAPSHOT_AVAILABLE
            )
            response = build_latest_snapshot_response(
                ibkr_conid,
                None,
                status=status,
                status_nl=(
                    "Data verouderd"
                    if status is LatestSnapshotStatus.STALE_SNAPSHOT
                    else "Snapshot beschikbaar"
                ),
                evaluated_at=evaluated_at,
            )
            response.provider_code = record.provider_code
            response.provider_environment = record.provider_environment
            response.provider_account_mode = record.provider_account_mode
            response.market_data_type = record.market_data_type
            response.requested_at = record.requested_at
            response.received_at = record.received_at
            response.provider_as_of = record.provider_as_of
            response.stored_at = record.stored_at
            response.freshness_status = record.freshness_status
            response.snapshot_available = True
            response.stale = status is LatestSnapshotStatus.STALE_SNAPSHOT
            response.last_price = str(record.last_price) if record.last_price is not None else None
            response.bid_price = str(record.bid_price) if record.bid_price is not None else None
            response.ask_price = str(record.ask_price) if record.ask_price is not None else None
            response.close_price = (
                str(record.close_price) if record.close_price is not None else None
            )
            response.day_change_percent = (
                str(record.day_change_percent)
                if record.day_change_percent is not None
                else None
            )
            response.currency = record.currency
            snapshot = MarketDataSnapshot(
                ibkr_conid=ibkr_conid,
                symbol=record.symbol or "",
                currency=record.currency or "",
                requested_at=record.requested_at or record.stored_at,
                received_at=record.received_at or record.stored_at,
                provider_as_of=record.provider_as_of,
                stored_at=record.stored_at,
                provider_code=record.provider_code or "unknown",
                provider_environment=record.provider_environment or "unknown",
                provider_account_mode=record.provider_account_mode or "unknown",
                data_domain="market_data",
                request_kind=record.market_data_type or "snapshot",
                source_type="stored_snapshot",
                last_price=record.last_price,
                bid_price=record.bid_price,
                ask_price=record.ask_price,
                day_change_percent=record.day_change_percent,
            )
            readiness = evaluate_market_data_readiness(
                snapshot=snapshot, now=datetime.now(UTC), policy=MarketDataReadinessPolicy()
            )
            response.valuation_readiness_status = readiness.valuation_readiness_status.value
            response.freshness_status = readiness.freshness_status.value
            response.price_basis = readiness.price_basis.value
            response.snapshot_age_seconds = readiness.snapshot_age_seconds
            response.usable_price = (
                str(readiness.usable_price)
                if readiness.usable_price is not None
                else None
            )
            response.price_basis_nl = {
                MarketDataPriceBasis.LAST: "Laatste prijs",
                MarketDataPriceBasis.MIDPOINT: "Midden van bied/laats",
                MarketDataPriceBasis.CLOSE: "Slotkoers",
                MarketDataPriceBasis.UNAVAILABLE: "Geen bruikbare prijs",
            }[readiness.price_basis]
            response.next_step_nl = "Alleen status. Nog geen analyse."
            response.help_nl = "Nog geen suggesties mogelijk."
            return response
    except StorageConnectionError:
        return build_latest_snapshot_response(
            ibkr_conid,
            None,
            status=LatestSnapshotStatus.STORAGE_FAILURE,
            status_nl="Storageverbinding mislukt.",
            blocker_reason="storage_connection_failed",
            evaluated_at=evaluated_at,
        )
