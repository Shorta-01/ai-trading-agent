"""Routes for read-only status/settings summaries."""

from typing import Annotated

from ai_trading_agent_storage import (
    SqlAlchemyMarketDataSnapshotRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, Body, HTTPException

from portfolio_outlook_api.config import settings
from portfolio_outlook_api.ibkr_contracts import search_ibkr_contracts, validate_ibkr_contract
from portfolio_outlook_api.ibkr_status import build_ibkr_status_placeholder
from portfolio_outlook_api.ibkr_sync import read_status, run_sync
from portfolio_outlook_api.ibkr_watchlists import (
    import_by_id,
    import_ibkr_watchlist,
    latest_import,
    list_ibkr_watchlist_instruments,
    list_ibkr_watchlists,
)
from portfolio_outlook_api.market_data_readiness import (
    LatestSnapshotResponse,
    ReadinessDetailResponse,
    ReadinessListResponse,
    ReadinessRow,
    ReadinessSnapshotMetadata,
    build_latest_snapshot_response,
    build_readiness_row,
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
    return read_status(settings)


@router.post("/ibkr/sync/run")
def start_ibkr_sync_run() -> dict[str, object]:
    return run_sync(settings)


@router.get("/ibkr/portfolio/positions")
def read_ibkr_positions() -> dict[str, object]:
    from portfolio_outlook_api.ibkr_sync import STORE

    return {
        "items": STORE.positions,
        "help_nl": "Alleen gesynchroniseerde IBKR-posities.",
    }


@router.get("/ibkr/account/cash")
def read_ibkr_cash() -> dict[str, object]:
    from portfolio_outlook_api.ibkr_sync import STORE

    return {
        "items": STORE.cash,
        "help_nl": "Alleen gesynchroniseerde IBKR-cashgegevens.",
    }


@router.get("/ibkr/orders/open")
def read_ibkr_open_orders() -> dict[str, object]:
    from portfolio_outlook_api.ibkr_sync import STORE

    return {
        "items": STORE.open_orders,
        "help_nl": "Alleen read-only open-order snapshots uit IBKR-sync.",
    }


@router.get("/ibkr/executions")
def read_ibkr_executions() -> dict[str, object]:
    from portfolio_outlook_api.ibkr_sync import STORE

    return {
        "items": STORE.executions,
        "help_nl": "Alleen read-only execution/fill snapshots uit IBKR-sync.",
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
            repo = SqlAlchemyMarketDataSnapshotRepository(checked.connection, checked.readiness)
            result = repo.get_latest_by_ibkr_conid(ibkr_conid)
            if result.record is None:
                return None
            return ReadinessSnapshotMetadata.model_validate(result.record.__dict__)
    except StorageConnectionError:
        return None

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
                evaluated_at=evaluated_at,
            )
        )
    return rows


@router.get("/market-data/readiness", response_model=ReadinessListResponse)
def read_market_data_readiness() -> ReadinessListResponse:
    return ReadinessListResponse(
        items=_build_market_data_readiness_rows(),
        help_nl=(
            "Task 85 foundation: geen market-data fetch, geen prijzen, "
            "alleen conid-gated readinessstatus."
        ),
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


@router.get("/market-data/snapshots/latest/{ibkr_conid}", response_model=LatestSnapshotResponse)
def read_market_data_snapshot_latest(ibkr_conid: str) -> LatestSnapshotResponse:
    evaluated_at = utc_now_iso()
    storage_settings = settings.storage
    if not storage_settings.enabled or not storage_settings.database_url:
        return build_latest_snapshot_response(
            ibkr_conid,
            None,
            status="not_configured",
            status_nl="Storage niet geconfigureerd.",
            missing_reason="storage_not_configured",
            evaluated_at=evaluated_at,
        )
    provider = StorageConnectionProvider(
        build_database_connection_settings(storage_settings.database_url)
    )
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyMarketDataSnapshotRepository(checked.connection, checked.readiness)
            result = repo.get_latest_by_ibkr_conid(ibkr_conid)
            if result.record is None:
                return build_latest_snapshot_response(
                    ibkr_conid,
                    None,
                    status="missing_snapshot",
                    status_nl="Nog geen snapshotmetadata opgeslagen.",
                    missing_reason="snapshot_not_found",
                    evaluated_at=evaluated_at,
                )
            return build_latest_snapshot_response(
                ibkr_conid,
                ReadinessSnapshotMetadata.model_validate(result.record.__dict__),
                status="snapshot_available",
                status_nl="Snapshotmetadata beschikbaar.",
                evaluated_at=evaluated_at,
            )
    except StorageConnectionError:
        return build_latest_snapshot_response(
            ibkr_conid,
            None,
            status="storage_failure",
            status_nl="Storageverbinding mislukt.",
            blocker_reason="storage_connection_failed",
            evaluated_at=evaluated_at,
        )
