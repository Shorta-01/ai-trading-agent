"""Routes for read-only status/settings summaries."""

from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from ai_trading_agent_storage import (
    AssetActionDraftEventRecord,
    AssetActionDraftSubmissionRecord,
    IbkrSyncRunRecord,
    MarketDataBarRecord,
    SqlAlchemyAssetActionDraftEventRepository,
    SqlAlchemyAssetActionDraftRepository,
    SqlAlchemyAssetActionDraftSubmissionRepository,
    SqlAlchemyAssetDecisionPackageRepository,
    SqlAlchemyAssetForecastRepository,
    SqlAlchemyAssetSuggestionRepository,
    SqlAlchemyDailyBriefingRepository,
    SqlAlchemyDecisionPackageExplanationRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
    SqlAlchemyMarketDataBarRepository,
    SqlAlchemyMarketDataSnapshotRepository,
    SqlAlchemyPredictionDiaryRepository,
    SqlAlchemyResearchSourceArchiveRepository,
    SqlAlchemySchedulerRunRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, Body, HTTPException, Request
from portfolio_outlook_domain.market_data_foundation import (
    MarketDataFetchStatus,
    MarketDataIdentity,
    MarketDataPriceBasis,
    MarketDataReadinessPolicy,
    MarketDataSnapshot,
    evaluate_market_data_readiness,
)

from portfolio_outlook_api.action_draft_submission import (
    approve_action_draft,
    serialize_event_for_response,
    serialize_submission_for_response,
    submit_action_draft_to_paper,
)
from portfolio_outlook_api.action_draft_sync import (
    generate_action_drafts,
    serialize_action_draft_for_response,
)
from portfolio_outlook_api.ai_explanation_provider import (
    build_explanation_provider,
)
from portfolio_outlook_api.ai_explanation_sync import (
    generate_explanation,
    serialize_explanation_for_response,
)
from portfolio_outlook_api.config import Settings, settings
from portfolio_outlook_api.daily_briefing_sync import (
    generate_daily_briefing,
    serialize_briefing_for_response,
)
from portfolio_outlook_api.decision_package_sync import (
    build_research_summary_by_symbol,
    serialize_decision_package_for_response,
    sync_decision_packages,
)
from portfolio_outlook_api.forecast_sync import (
    serialize_forecast_for_response,
    sync_forecasts,
)
from portfolio_outlook_api.ibkr_account_snapshot_preflight import (
    build_manual_readonly_account_snapshot_preflight_readiness,
    run_manual_readonly_account_snapshot_preflight,
)
from portfolio_outlook_api.ibkr_contracts import search_ibkr_contracts, validate_ibkr_contract
from portfolio_outlook_api.ibkr_ibapi_manual_status_client import (
    IbapiManualReadonlyStatusClient,
)
from portfolio_outlook_api.ibkr_ibapi_sync_client import real_sync_client_session
from portfolio_outlook_api.ibkr_market_data import IbkrMarketDataAdapter, settings_from_runtime
from portfolio_outlook_api.ibkr_order_submission_factory import (
    build_real_order_submission_client,
)
from portfolio_outlook_api.ibkr_status import build_ibkr_status_placeholder
from portfolio_outlook_api.ibkr_sync import read_status, run_sync
from portfolio_outlook_api.ibkr_sync_adapter_factory import build_real_sync_adapter
from portfolio_outlook_api.ibkr_sync_read_model import (
    read_latest_ibkr_sync_run,
    serialize_cash_record,
    serialize_execution_record,
    serialize_open_order_record,
    serialize_position_record,
    serialize_sync_status_record,
)
from portfolio_outlook_api.ibkr_tws_readonly_adapter import IbkrTwsReadonlyClient
from portfolio_outlook_api.ibkr_tws_readonly_runtime import (
    build_manual_tws_readonly_status_check_readiness,
    run_manual_tws_readonly_status_check,
)
from portfolio_outlook_api.ibkr_watchlists import (
    import_by_id,
    import_ibkr_watchlist,
    latest_import,
    list_ibkr_watchlist_instruments,
    list_ibkr_watchlists,
)
from portfolio_outlook_api.market_data_adapter_factory import build_market_data_provider
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
from portfolio_outlook_api.market_data_sync import sync_market_data_and_fx
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
from portfolio_outlook_api.portfolio_valuation_readiness import (
    PortfolioReconciliationReadinessResponse,
    PortfolioValuationReadinessResponse,
    build_portfolio_reconciliation_readiness,
    build_portfolio_valuation_readiness,
)
from portfolio_outlook_api.prediction_diary_sync import (
    evaluate_prediction_diary,
    serialize_prediction_diary_entry_for_response,
)
from portfolio_outlook_api.reconciliation_sync import reconcile_submissions
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
from portfolio_outlook_api.suggestion_sync import (
    serialize_suggestion_for_response,
    sync_suggestions,
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


def _build_sync_run_diagnostics(run: dict[str, object]) -> dict[str, object]:
    return {
        "sync_run_id": run.get("sync_run_id"),
        "started_at": run.get("started_at"),
        "completed_at": run.get("completed_at"),
        "status": run.get("status", "unknown"),
        "status_nl": "Read-only sync uitgevoerd",
        "provider_code": run.get("provider_code"),
        "provider_environment": run.get("provider_environment"),
        "account_mode": run.get("account_mode"),
        "readonly": run.get("readonly"),
        "account_summary_status": run.get("account_summary_status"),
        "positions_status": run.get("positions_status"),
        "open_orders_status": run.get("open_orders_status"),
        "executions_status": run.get("executions_status"),
        "positions_count": run.get("positions_count", 0),
        "cash_values_count": run.get("cash_values_count", 0),
        "open_orders_count": run.get("open_orders_count", 0),
        "executions_count": run.get("executions_count", 0),
        "persistence_mode": run.get("persistence_mode", "memory"),
        "persistence_status_nl": run.get("persistence_status_nl", "Geheugenfallback actief"),
        "payload_validation_status": run.get("payload_validation_status", "not_available"),
        "payload_validation_status_nl": run.get("payload_validation_status_nl", "Niet beschikbaar"),
        "payload_validation_error_count": run.get("payload_validation_error_count", 0),
        "payload_validation_help_nl": run.get(
            "payload_validation_help_nl",
            "Deze syncrun bevat geen opgeslagen payloadvalidatie-details.",
        ),
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
        "can_submit_orders": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


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


def _run_manual_tws_readonly_status_check_endpoint(
    runtime_settings: Settings,
    runtime_client: IbkrTwsReadonlyClient | None = None,
) -> dict[str, object]:
    return asdict(
        run_manual_tws_readonly_status_check(
            runtime_settings,
            runtime_client=runtime_client,
        )
    )


@router.post("/ibkr/session/manual-readonly-status-check")
def run_manual_readonly_status_check() -> dict[str, object]:
    runtime_client: IbkrTwsReadonlyClient | None = None
    if (
        settings.ibkr_tws_readonly_real_client_enabled
        and settings.ibkr_sync_host is not None
        and settings.ibkr_sync_port is not None
        and settings.ibkr_sync_client_id is not None
    ):
        runtime_client = IbapiManualReadonlyStatusClient(
            host=settings.ibkr_sync_host,
            port=settings.ibkr_sync_port,
            client_id=settings.ibkr_sync_client_id,
        )
    return _run_manual_tws_readonly_status_check_endpoint(settings, runtime_client=runtime_client)


@router.get("/ibkr/session/manual-readonly-status-check/readiness")
def read_manual_readonly_status_check_readiness() -> dict[str, object]:
    return asdict(
        build_manual_tws_readonly_status_check_readiness(
            settings,
            runtime_client=None,
        )
    )


def _run_manual_readonly_account_snapshot_preflight_endpoint(
    runtime_settings: Settings,
    runtime_client: object | None = None,
) -> dict[str, object]:
    return asdict(
        run_manual_readonly_account_snapshot_preflight(
            runtime_settings,
            runtime_client=runtime_client,
        )
    )


@router.post("/ibkr/session/manual-readonly-account-snapshot-preflight")
def run_manual_readonly_account_snapshot_preflight_route() -> dict[str, object]:
    return _run_manual_readonly_account_snapshot_preflight_endpoint(
        settings,
        runtime_client=None,
    )


@router.get("/ibkr/session/manual-readonly-account-snapshot-preflight/readiness")
def read_manual_readonly_account_snapshot_preflight_readiness() -> dict[str, object]:
    return asdict(
        build_manual_readonly_account_snapshot_preflight_readiness(
            settings,
            runtime_client=None,
        )
    )


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
    adapter = build_real_sync_adapter(settings)
    with real_sync_client_session(adapter) as active_adapter:
        return run_sync(settings, adapter=active_adapter)


@router.get("/ibkr/sync/runs")
def read_ibkr_sync_runs() -> dict[str, object]:
    from portfolio_outlook_api.ibkr_sync import STORE

    items = [_build_sync_run_diagnostics(run) for run in reversed(STORE.runs)]
    return {
        "items": items,
        "help_nl": (
            "Recente read-only syncruns in geheugenvolgorde."
            if items
            else "Nog geen read-only syncruns beschikbaar."
        ),
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
        "can_submit_orders": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


@router.get("/ibkr/sync/runs/{sync_run_id}")
def read_ibkr_sync_run_detail(sync_run_id: str) -> dict[str, object]:
    from portfolio_outlook_api.ibkr_sync import STORE

    run = next((item for item in STORE.runs if item.get("sync_run_id") == sync_run_id), None)
    if run is None:
        raise HTTPException(status_code=404, detail="Syncrun niet gevonden.")
    return _build_sync_run_diagnostics(run) | {
        "positions": [item for item in STORE.positions if item.get("sync_run_id") == sync_run_id],
        "cash_values": [item for item in STORE.cash if item.get("sync_run_id") == sync_run_id],
        "open_orders": [
            item for item in STORE.open_orders if item.get("sync_run_id") == sync_run_id
        ],
        "executions": [item for item in STORE.executions if item.get("sync_run_id") == sync_run_id],
        "detail_help_nl": "Read-only syncrun detail zonder ruwe brokerpayloads.",
    }


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


@router.get(
    "/portfolio/valuation/readiness",
    response_model=PortfolioValuationReadinessResponse,
)
def read_portfolio_valuation_readiness() -> PortfolioValuationReadinessResponse:
    durable = read_latest_ibkr_sync_run(settings.storage)
    if durable.storage_help_nl is not None:
        return build_portfolio_valuation_readiness(
            latest_run=None,
            positions=[],
            market_by_conid={},
            cash_snapshots=[],
            fx_snapshots=[],
            storage_available=False,
        )
    if durable.latest_run is None:
        return build_portfolio_valuation_readiness(
            latest_run=None,
            positions=[],
            market_by_conid={},
            cash_snapshots=[],
            fx_snapshots=[],
            storage_available=True,
        )
    provider = StorageConnectionProvider(
        build_database_connection_settings(settings.storage.database_url)
    )
    with provider.checked_connection(require_writable=False) as checked:
        repo = SqlAlchemyIbkrSyncSnapshotRepository(checked.connection, checked.readiness)
        market_repo = SqlAlchemyMarketDataSnapshotRepository(checked.connection, checked.readiness)
        positions = repo.list_ibkr_position_snapshots(durable.latest_run.sync_run_id)
        cash_snapshots = repo.list_ibkr_account_cash_snapshots(durable.latest_run.sync_run_id)
        conids = tuple(item.conid for item in positions if item.conid)
        market_result = market_repo.list_latest_market_data_snapshots_by_conids(conids)
        market_by_conid = {item.ibkr_conid: item for item in market_result.records}
        cash_currencies = sorted({item.base_currency for item in cash_snapshots})
        position_currencies = sorted(
            {(item.currency or "").strip() for item in positions if item.currency}
        )
        valuation_currencies = sorted(set(cash_currencies) | set(position_currencies))
        base_currency = cash_currencies[0] if len(cash_currencies) == 1 else None
        required_pairs: tuple[str, ...] = ()
        if len(valuation_currencies) > 1 and base_currency is not None:
            required_pairs = tuple(
                f"{currency}/{base_currency}"
                for currency in valuation_currencies
                if currency != base_currency
            )
        fx_snapshots = repo.list_latest_fx_rate_snapshots_by_pairs(required_pairs)
    return build_portfolio_valuation_readiness(
        latest_run=durable.latest_run,
        positions=positions,
        market_by_conid=market_by_conid,
        cash_snapshots=cash_snapshots,
        fx_snapshots=fx_snapshots,
        storage_available=True,
    )


@router.get(
    "/portfolio/valuation/reconciliation-readiness",
    response_model=PortfolioReconciliationReadinessResponse,
)
def read_portfolio_reconciliation_readiness() -> PortfolioReconciliationReadinessResponse:
    valuation = read_portfolio_valuation_readiness()
    durable = read_latest_ibkr_sync_run(settings.storage)
    latest = durable.latest_run
    diagnostics_available = latest is not None
    payload_status, payload_status_nl, payload_help = _payload_validation_summary_from_sync_record(
        latest
    )
    return build_portfolio_reconciliation_readiness(
        valuation=valuation,
        payload_validation_status=payload_status,
        payload_validation_status_nl=payload_status_nl,
        payload_validation_help_nl=payload_help,
        diagnostics_available=diagnostics_available,
    )


def _payload_validation_summary_from_sync_record(
    latest_run: IbkrSyncRunRecord | None,
) -> tuple[str, str, str]:
    _ = latest_run
    return (
        "not_available",
        "Niet beschikbaar",
        "Deze syncrun bevat geen opgeslagen payloadvalidatie-details.",
    )


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
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage_settings.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyResearchSourceArchiveRepository(
                checked.connection,
                checked.readiness,
            )
            if ibkr_conid is None:
                return build_asset_listing_gate(
                    status=ReadinessAssetListingGateStatus.MISSING_IBKR_CONID,
                    ibkr_conid=None,
                )
            listing = repo.get_asset_listing_by_ibkr_conid(ibkr_conid)
    except StorageConnectionError:
        return build_asset_listing_gate(
            status=ReadinessAssetListingGateStatus.STORAGE_UNAVAILABLE,
            ibkr_conid=ibkr_conid,
        )

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


def _build_blocked_market_data_sync_response(
    *, reason: str, status_nl: str, help_nl: str
) -> dict[str, object]:
    return {
        "status": "blocked",
        "status_nl": status_nl,
        "help_nl": help_nl,
        "reason": reason,
        "provider_code": settings.market_data_provider,
        "asset_total": 0,
        "asset_success": 0,
        "asset_skipped_unknown_exchange": 0,
        "asset_failed": 0,
        "fx_total": 0,
        "fx_success": 0,
        "fx_failed": 0,
        "failures": [],
        "market_snapshots_persisted": 0,
        "fx_snapshots_persisted": 0,
        "base_currency": None,
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


@router.post("/market-data/sync")
def run_market_data_sync() -> dict[str, object]:
    """Run one market-data + FX sync cycle using the configured provider.

    The route is disabled by default. Even when enabled it only persists
    read-only snapshots into the existing market-data and FX storage tables;
    no suggestions, action drafts, orders or broker actions are produced.
    """

    provider = build_market_data_provider(settings)
    if provider is None:
        return _build_blocked_market_data_sync_response(
            reason="market_data_provider_not_configured",
            status_nl="Marktdata-sync niet geconfigureerd",
            help_nl=(
                "Stel `MARKET_DATA_SYNC_ENABLED=true`, "
                "`MARKET_DATA_PROVIDER=eodhd`, `EODHD_ENABLED=true` en "
                "`EODHD_API_KEY=...` in om marktdata op te halen."
            ),
        )

    storage = settings.storage
    if not storage.enabled or not storage.database_url or not storage.writes_enabled:
        return _build_blocked_market_data_sync_response(
            reason="storage_not_writable",
            status_nl="Opslag niet beschikbaar",
            help_nl=(
                "Marktdata-sync vereist een schrijfbare opslag; "
                "controleer STORAGE__ENABLED, STORAGE__DATABASE_URL en "
                "STORAGE__WRITES_ENABLED."
            ),
        )

    provider_obj = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with provider_obj.checked_connection(require_writable=True) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection,
                checked.readiness,
            )
            market_repo = SqlAlchemyMarketDataSnapshotRepository(
                checked.connection,
                checked.readiness,
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            if latest_run is None:
                return _build_blocked_market_data_sync_response(
                    reason="no_ibkr_sync_run",
                    status_nl="Geen IBKR-sync gevonden",
                    help_nl=(
                        "Marktdata-sync gebruikt de laatst opgeslagen IBKR-sync "
                        "om te bepalen voor welke posities prijzen nodig zijn; "
                        "voer eerst een handmatige read-only IBKR-sync uit."
                    ),
                )
            positions = ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id)
            cash_snapshots = ibkr_repo.list_ibkr_account_cash_snapshots(latest_run.sync_run_id)
            report = sync_market_data_and_fx(
                provider=provider,
                market_repo=market_repo,
                fx_repo=ibkr_repo,
                positions=list(positions),
                cash_snapshots=list(cash_snapshots),
                max_assets=settings.market_data_sync_max_assets,
            )
    except StorageConnectionError:
        return _build_blocked_market_data_sync_response(
            reason="storage_connection_failed",
            status_nl="Opslag niet bereikbaar",
            help_nl="De opslag kon niet worden bereikt; geen marktdata opgeslagen.",
        )

    return {
        "status": "completed",
        "status_nl": report.status_nl,
        "help_nl": report.help_nl,
        "provider_code": report.provider_code,
        "requested_at": report.requested_at.isoformat(),
        "completed_at": report.completed_at.isoformat(),
        "asset_total": report.asset_total,
        "asset_success": report.asset_success,
        "asset_skipped_unknown_exchange": report.asset_skipped_unknown_exchange,
        "asset_failed": report.asset_failed,
        "fx_total": report.fx_total,
        "fx_success": report.fx_success,
        "fx_failed": report.fx_failed,
        "failures": [dict(item) for item in report.failures],
        "market_snapshots_persisted": report.market_snapshots_persisted,
        "fx_snapshots_persisted": report.fx_snapshots_persisted,
        "base_currency": report.base_currency,
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


def _build_blocked_forecast_response(
    *, reason: str, status_nl: str, help_nl: str
) -> dict[str, object]:
    return {
        "status": "blocked",
        "status_nl": status_nl,
        "help_nl": help_nl,
        "reason": reason,
        "model_code": "baseline_gbm",
        "asset_total": 0,
        "asset_success": 0,
        "asset_skipped_unknown_exchange": 0,
        "asset_skipped_missing_market_data": 0,
        "asset_failed": 0,
        "forecasts_persisted": 0,
        "bars_persisted": 0,
        "failures": [],
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


@router.post("/forecasts/compute")
def run_forecast_sync() -> dict[str, object]:
    """Run one baseline-forecast cycle and persist a forecast per position.

    Default-off. Even when enabled, only deterministic GBM forecasts are
    persisted; no suggestions, action drafts or orders are produced.
    """

    if not settings.forecast_sync_enabled:
        return _build_blocked_forecast_response(
            reason="forecast_sync_disabled",
            status_nl="Voorspellingssync uitgeschakeld",
            help_nl="Stel `FORECAST_SYNC_ENABLED=true` in om de baseline-engine te activeren.",
        )

    provider = build_market_data_provider(settings)
    if provider is None:
        return _build_blocked_forecast_response(
            reason="market_data_provider_not_configured",
            status_nl="Marktdataprovider niet geconfigureerd",
            help_nl=(
                "Voorspellingen vereisen EODHD; configureer "
                "`MARKET_DATA_PROVIDER=eodhd`, `EODHD_ENABLED=true` en "
                "`EODHD_API_KEY=...`."
            ),
        )

    storage = settings.storage
    if not storage.enabled or not storage.database_url or not storage.writes_enabled:
        return _build_blocked_forecast_response(
            reason="storage_not_writable",
            status_nl="Opslag niet beschikbaar",
            help_nl=(
                "Voorspellingen vereisen schrijfbare opslag; controleer "
                "STORAGE__ENABLED, STORAGE__DATABASE_URL en STORAGE__WRITES_ENABLED."
            ),
        )

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=True) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            market_repo = SqlAlchemyMarketDataSnapshotRepository(
                checked.connection, checked.readiness
            )
            bar_repo = SqlAlchemyMarketDataBarRepository(
                checked.connection, checked.readiness
            )
            forecast_repo = SqlAlchemyAssetForecastRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            if latest_run is None:
                return _build_blocked_forecast_response(
                    reason="no_ibkr_sync_run",
                    status_nl="Geen IBKR-sync gevonden",
                    help_nl=(
                        "Voorspellingen gebruiken de laatst opgeslagen IBKR-sync; "
                        "voer eerst een handmatige read-only IBKR-sync uit."
                    ),
                )
            positions = list(ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id))
            if not positions:
                return _build_blocked_forecast_response(
                    reason="no_positions",
                    status_nl="Geen posities in laatste IBKR-sync",
                    help_nl=(
                        "De laatste IBKR-sync bevat geen posities; voer een "
                        "nieuwe sync uit zodra je posities aanhoudt."
                    ),
                )
            conids = tuple(p.conid for p in positions if p.conid)
            market_result = market_repo.list_latest_market_data_snapshots_by_conids(conids)
            market_by_conid = {item.ibkr_conid: item for item in market_result.records}
            report = sync_forecasts(
                provider=provider,
                bar_repo=bar_repo,
                forecast_repo=forecast_repo,
                positions=positions,
                market_snapshots_by_conid=market_by_conid,
                history_lookback_days=settings.forecast_history_lookback_days,
                horizon_trading_days=settings.forecast_horizon_trading_days,
                minimum_bars_required=settings.forecast_minimum_bars_required,
                max_assets=settings.forecast_max_assets_per_run,
                valid_minutes=settings.forecast_valid_minutes,
            )
    except StorageConnectionError:
        return _build_blocked_forecast_response(
            reason="storage_connection_failed",
            status_nl="Opslag niet bereikbaar",
            help_nl="De opslag kon niet worden bereikt; geen voorspellingen opgeslagen.",
        )

    return {
        "status": "completed",
        "status_nl": report.status_nl,
        "help_nl": report.help_nl,
        "model_code": report.model_code,
        "model_version": report.model_version,
        "horizon_trading_days": report.horizon_trading_days,
        "requested_at": report.requested_at.isoformat(),
        "completed_at": report.completed_at.isoformat(),
        "asset_total": report.asset_total,
        "asset_success": report.asset_success,
        "asset_skipped_unknown_exchange": report.asset_skipped_unknown_exchange,
        "asset_skipped_missing_market_data": report.asset_skipped_missing_market_data,
        "asset_failed": report.asset_failed,
        "forecasts_persisted": report.forecasts_persisted,
        "bars_persisted": report.bars_persisted,
        "failures": [dict(item) for item in report.failures],
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


@router.get("/forecasts/latest")
def read_latest_forecasts() -> dict[str, object]:
    """Read the latest persisted baseline forecast per current position."""

    base = {
        "items": [],
        "help_nl": "Voorspellingen zijn read-only baseline-resultaten.",
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return base | {
            "status": "not_configured",
            "status_nl": "Opslag niet geconfigureerd",
        }

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=False) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            forecast_repo = SqlAlchemyAssetForecastRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            if latest_run is None:
                return base | {
                    "status": "no_ibkr_sync_run",
                    "status_nl": "Geen IBKR-sync gevonden",
                }
            positions = list(ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id))
            conids = tuple(p.conid for p in positions if p.conid)
            if not conids:
                return base | {
                    "status": "no_positions",
                    "status_nl": "Geen posities",
                }
            result = forecast_repo.list_latest_asset_forecasts_by_conids(conids)
            return base | {
                "status": "ok",
                "status_nl": (
                    "Voorspellingen beschikbaar"
                    if result.records
                    else "Nog geen voorspellingen"
                ),
                "items": [serialize_forecast_for_response(r) for r in result.records],
            }
    except StorageConnectionError:
        return base | {
            "status": "storage_unavailable",
            "status_nl": "Opslag niet bereikbaar",
        }


def _build_blocked_suggestion_response(
    *, reason: str, status_nl: str, help_nl: str
) -> dict[str, object]:
    return {
        "status": "blocked",
        "status_nl": status_nl,
        "help_nl": help_nl,
        "reason": reason,
        "model_code": "baseline_label_translator",
        "risk_profile": settings.suggestions_risk_profile,
        "suggestion_total": 0,
        "suggestion_persisted": 0,
        "suggestion_failed": 0,
        "held_positions": 0,
        "cold_start_positions": 0,
        "failures": [],
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


@router.post("/suggestions/compute")
def run_suggestions_sync() -> dict[str, object]:
    """Translate the latest baseline forecasts into locked Dutch labels.

    AI never decides the label; this is a pure-Python rule engine over
    evidence-gated inputs. Default-off. No action drafts or orders.
    """

    if not settings.suggestions_sync_enabled:
        return _build_blocked_suggestion_response(
            reason="suggestions_sync_disabled",
            status_nl="Suggesties uitgeschakeld",
            help_nl="Stel `SUGGESTIONS_SYNC_ENABLED=true` in om de label-translator te activeren.",
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url or not storage.writes_enabled:
        return _build_blocked_suggestion_response(
            reason="storage_not_writable",
            status_nl="Opslag niet beschikbaar",
            help_nl=(
                "Suggesties vereisen schrijfbare opslag; controleer "
                "STORAGE__ENABLED, STORAGE__DATABASE_URL en STORAGE__WRITES_ENABLED."
            ),
        )

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=True) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            forecast_repo = SqlAlchemyAssetForecastRepository(
                checked.connection, checked.readiness
            )
            suggestion_repo = SqlAlchemyAssetSuggestionRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            positions = (
                list(ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id))
                if latest_run is not None
                else []
            )
            conids = tuple(p.conid for p in positions if p.conid)
            if not conids:
                return _build_blocked_suggestion_response(
                    reason="no_positions",
                    status_nl="Geen posities beschikbaar",
                    help_nl=(
                        "Suggesties draaien op het IBKR-positie-universum. "
                        "Voer eerst een IBKR-sync uit."
                    ),
                )
            forecast_result = forecast_repo.list_latest_asset_forecasts_by_conids(conids)
            forecasts = list(forecast_result.records)
            if not forecasts:
                return _build_blocked_suggestion_response(
                    reason="no_forecasts",
                    status_nl="Geen voorspellingen beschikbaar",
                    help_nl=(
                        "Suggesties hebben recente baseline-voorspellingen nodig. "
                        "Voer eerst een forecast-sync uit."
                    ),
                )
            report = sync_suggestions(
                forecasts=forecasts,
                positions=positions,
                risk_profile=settings.suggestions_risk_profile,
                repo=suggestion_repo,
                valid_minutes=settings.suggestions_valid_minutes,
            )
    except StorageConnectionError:
        return _build_blocked_suggestion_response(
            reason="storage_connection_failed",
            status_nl="Opslag niet bereikbaar",
            help_nl="De opslag kon niet worden bereikt; geen suggesties opgeslagen.",
        )

    return {
        "status": "completed",
        "status_nl": report.status_nl,
        "help_nl": report.help_nl,
        "model_code": report.model_code,
        "model_version": report.model_version,
        "risk_profile": report.risk_profile,
        "requested_at": report.requested_at.isoformat(),
        "completed_at": report.completed_at.isoformat(),
        "suggestion_total": report.suggestion_total,
        "suggestion_persisted": report.suggestion_persisted,
        "suggestion_failed": report.suggestion_failed,
        "held_positions": report.held_positions,
        "cold_start_positions": report.cold_start_positions,
        "failures": [dict(item) for item in report.failures],
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


@router.get("/suggestions/latest")
def read_latest_suggestions() -> dict[str, object]:
    """Return the latest persisted suggestion per current position."""

    base = {
        "items": [],
        "help_nl": (
            "Suggesties zijn deterministische Python-uitkomsten op basis van "
            "evidence-gated baseline-voorspellingen. Geen action drafts, "
            "geen orders, geen broker-submission."
        ),
        "risk_profile": settings.suggestions_risk_profile,
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return base | {
            "status": "not_configured",
            "status_nl": "Opslag niet geconfigureerd",
        }

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=False) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            suggestion_repo = SqlAlchemyAssetSuggestionRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            if latest_run is None:
                return base | {
                    "status": "no_ibkr_sync_run",
                    "status_nl": "Geen IBKR-sync gevonden",
                }
            positions = list(ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id))
            conids = tuple(p.conid for p in positions if p.conid)
            if not conids:
                return base | {
                    "status": "no_positions",
                    "status_nl": "Geen posities",
                }
            result = suggestion_repo.list_latest_asset_suggestions_by_conids(conids)
            return base | {
                "status": "ok",
                "status_nl": (
                    "Suggesties beschikbaar"
                    if result.records
                    else "Nog geen suggesties"
                ),
                "items": [serialize_suggestion_for_response(r) for r in result.records],
            }
    except StorageConnectionError:
        return base | {
            "status": "storage_unavailable",
            "status_nl": "Opslag niet bereikbaar",
        }


def _build_blocked_decision_package_response(
    *, reason: str, status_nl: str, help_nl: str
) -> dict[str, object]:
    return {
        "status": "blocked",
        "status_nl": status_nl,
        "help_nl": help_nl,
        "reason": reason,
        "risk_profile": settings.suggestions_risk_profile,
        "package_total": 0,
        "package_persisted": 0,
        "package_failed": 0,
        "package_skipped_missing_inputs": 0,
        "failures": [],
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }


@router.post("/decision-packages/compute")
def run_decision_packages_sync() -> dict[str, object]:
    """Bundle the latest evidence chain into one immutable Decision Package
    per current suggestion. Packages are insert-only and hash-anchored.

    Disabled-by-default. No action drafts, no orders, no broker submission.
    """

    if not settings.decision_packages_sync_enabled:
        return _build_blocked_decision_package_response(
            reason="decision_packages_sync_disabled",
            status_nl="Decision Packages uitgeschakeld",
            help_nl=(
                "Stel `DECISION_PACKAGES_SYNC_ENABLED=true` in om Decision "
                "Packages te activeren."
            ),
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url or not storage.writes_enabled:
        return _build_blocked_decision_package_response(
            reason="storage_not_writable",
            status_nl="Opslag niet beschikbaar",
            help_nl="Decision Packages vereisen schrijfbare opslag.",
        )

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=True) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            forecast_repo = SqlAlchemyAssetForecastRepository(
                checked.connection, checked.readiness
            )
            suggestion_repo = SqlAlchemyAssetSuggestionRepository(
                checked.connection, checked.readiness
            )
            market_repo = SqlAlchemyMarketDataSnapshotRepository(
                checked.connection, checked.readiness
            )
            package_repo = SqlAlchemyAssetDecisionPackageRepository(
                checked.connection, checked.readiness
            )
            research_repo = SqlAlchemyResearchSourceArchiveRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            if latest_run is None:
                return _build_blocked_decision_package_response(
                    reason="no_ibkr_sync_run",
                    status_nl="Geen IBKR-sync gevonden",
                    help_nl="Voer eerst een IBKR-sync uit.",
                )
            positions = list(ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id))
            cash_snapshots = list(
                ibkr_repo.list_ibkr_account_cash_snapshots(latest_run.sync_run_id)
            )
            conids = tuple(p.conid for p in positions if p.conid)
            if not conids:
                return _build_blocked_decision_package_response(
                    reason="no_positions",
                    status_nl="Geen posities beschikbaar",
                    help_nl="Voer eerst een IBKR-sync uit met posities.",
                )
            suggestion_records = list(
                suggestion_repo.list_latest_asset_suggestions_by_conids(conids).records
            )
            if not suggestion_records:
                return _build_blocked_decision_package_response(
                    reason="no_suggestions",
                    status_nl="Geen suggesties beschikbaar",
                    help_nl="Voer eerst een suggesties-sync uit.",
                )
            forecast_ids = tuple(
                s.forecast_id for s in suggestion_records if s.forecast_id
            )
            forecast_records = (
                list(forecast_repo.list_latest_asset_forecasts_by_conids(conids).records)
            )
            forecasts_by_id = {f.forecast_id: f for f in forecast_records}
            # Also key forecasts by conid so a suggestion missing forecast_id
            # but pointing at the same conid still resolves.
            forecasts_by_conid = {f.ibkr_conid: f for f in forecast_records}
            market_records = list(
                market_repo.list_latest_market_data_snapshots_by_conids(conids).records
            )
            market_by_conid = {m.ibkr_conid: m for m in market_records}
            positions_by_conid = {p.conid: p for p in positions if p.conid}
            cash_currencies = sorted({c.base_currency for c in cash_snapshots if c.base_currency})
            base_currency = cash_currencies[0] if len(cash_currencies) == 1 else None
            cash_by_currency = {c.base_currency: c for c in cash_snapshots}
            required_pairs: list[str] = []
            if base_currency:
                position_currencies = {p.currency.upper() for p in positions if p.currency}
                all_currencies = sorted(position_currencies | set(cash_currencies))
                required_pairs = [
                    f"{c}/{base_currency}" for c in all_currencies if c and c != base_currency
                ]
            fx_records = (
                list(ibkr_repo.list_latest_fx_rate_snapshots_by_pairs(tuple(required_pairs)))
                if required_pairs
                else []
            )
            fx_by_pair = {f.pair: f for f in fx_records}

            # Hydrate forecasts_by_id with the conid-keyed fallback so the
            # orchestrator can look up forecast by id and still find data.
            for record in forecast_records:
                forecasts_by_id.setdefault(record.forecast_id, record)
            _ = forecasts_by_conid, forecast_ids  # silenced unused for now

            symbols = sorted({s.symbol for s in suggestion_records if s.symbol})
            research_summary_by_symbol = build_research_summary_by_symbol(
                symbols,
                research_repo=research_repo,
                now=datetime.now(UTC),
            )
            report = sync_decision_packages(
                suggestions=suggestion_records,
                forecasts_by_id=forecasts_by_id,
                positions_by_conid=positions_by_conid,
                cash_by_currency=cash_by_currency,
                market_by_conid=market_by_conid,
                fx_by_pair=fx_by_pair,
                base_currency=base_currency,
                risk_profile=settings.suggestions_risk_profile,
                repo=package_repo,
                valid_minutes=settings.decision_packages_valid_minutes,
                research_summary_by_symbol=research_summary_by_symbol,
            )
    except StorageConnectionError:
        return _build_blocked_decision_package_response(
            reason="storage_connection_failed",
            status_nl="Opslag niet bereikbaar",
            help_nl="De opslag kon niet worden bereikt.",
        )

    return {
        "status": "completed",
        "status_nl": report.status_nl,
        "help_nl": report.help_nl,
        "risk_profile": report.risk_profile,
        "requested_at": report.requested_at.isoformat(),
        "completed_at": report.completed_at.isoformat(),
        "package_total": report.package_total,
        "package_persisted": report.package_persisted,
        "package_failed": report.package_failed,
        "package_skipped_missing_inputs": report.package_skipped_missing_inputs,
        "failures": [dict(item) for item in report.failures],
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }


@router.get("/decision-packages/latest")
def read_latest_decision_packages() -> dict[str, object]:
    """Return the latest Decision Package per current position."""

    base = {
        "items": [],
        "help_nl": (
            "Decision Packages zijn immutable, gehashte evidence-bundels die "
            "elke suggestion ondersteunen. Geen action drafts of orders."
        ),
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return base | {
            "status": "not_configured",
            "status_nl": "Opslag niet geconfigureerd",
        }

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=False) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            package_repo = SqlAlchemyAssetDecisionPackageRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            if latest_run is None:
                return base | {
                    "status": "no_ibkr_sync_run",
                    "status_nl": "Geen IBKR-sync gevonden",
                }
            positions = list(ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id))
            conids = tuple(p.conid for p in positions if p.conid)
            if not conids:
                return base | {"status": "no_positions", "status_nl": "Geen posities"}
            result = package_repo.list_latest_asset_decision_packages_by_conids(conids)
            return base | {
                "status": "ok",
                "status_nl": (
                    "Decision Packages beschikbaar"
                    if result.records
                    else "Nog geen Decision Packages"
                ),
                "items": [
                    serialize_decision_package_for_response(r) for r in result.records
                ],
            }
    except StorageConnectionError:
        return base | {
            "status": "storage_unavailable",
            "status_nl": "Opslag niet bereikbaar",
        }


@router.get("/decision-packages/{ibkr_conid}/latest")
def read_latest_decision_package_for_conid(ibkr_conid: str) -> dict[str, object]:
    """Return the latest Decision Package for one conid (per-row drilldown)."""

    base: dict[str, object] = {
        "item": None,
        "help_nl": "Decision Package detail; immutable evidence-bundel.",
        "actions_allowed": False,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return base | {"status": "not_configured", "status_nl": "Opslag niet geconfigureerd"}

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=False) as checked:
            package_repo = SqlAlchemyAssetDecisionPackageRepository(
                checked.connection, checked.readiness
            )
            result = package_repo.get_latest_asset_decision_package_by_conid(ibkr_conid)
            if not result.found or result.record is None:
                return base | {
                    "status": "not_found",
                    "status_nl": "Geen Decision Package voor deze positie",
                }
            return base | {
                "status": "ok",
                "status_nl": "Decision Package beschikbaar",
                "item": serialize_decision_package_for_response(result.record),
            }
    except StorageConnectionError:
        return base | {"status": "storage_unavailable", "status_nl": "Opslag niet bereikbaar"}


def _build_blocked_explanation_response(
    *, reason: str, status_nl: str, help_nl: str
) -> dict[str, object]:
    return {
        "status": "blocked",
        "status_nl": status_nl,
        "help_nl": help_nl,
        "reason": reason,
        "explanation_id": None,
        "explanation": None,
        "safe_for_self_learning": False,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


@router.post("/decision-packages/{decision_package_id}/explanation")
def run_explanation_for_decision_package(
    decision_package_id: str,
) -> dict[str, object]:
    """Generate (or refresh) the AI explanation for one Decision Package.

    AI is gated five ways; defaults are all False so the route returns
    ``blocked`` until the runtime is explicitly enabled.
    """

    if not settings.ai_explanation_enabled:
        return _build_blocked_explanation_response(
            reason="ai_explanation_disabled",
            status_nl="AI uitleg uitgeschakeld",
            help_nl=(
                "Stel `AI_EXPLANATION_ENABLED=true` in om uitleg te activeren."
            ),
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url or not storage.writes_enabled:
        return _build_blocked_explanation_response(
            reason="storage_not_writable",
            status_nl="Opslag niet beschikbaar",
            help_nl="AI uitleg vereist schrijfbare opslag.",
        )

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=True) as checked:
            package_repo = SqlAlchemyAssetDecisionPackageRepository(
                checked.connection, checked.readiness
            )
            explanation_repo = SqlAlchemyDecisionPackageExplanationRepository(
                checked.connection, checked.readiness
            )
            research_repo = SqlAlchemyResearchSourceArchiveRepository(
                checked.connection, checked.readiness
            )
            # The decision_package_id path-parameter resolves to a single
            # record; we read it back rather than trusting the caller.
            # The repository exposes get-by-conid; we use the latest
            # package per conid here since the package_id-by-id read is
            # only required by tests. For V1 we ground the route in the
            # most recent package per conid, which is the user-facing
            # version anyway.
            #
            # However the route argument is the decision_package_id, so
            # we filter against it on the listing helper for accuracy.
            all_packages = package_repo.list_latest_asset_decision_packages_by_conids(
                tuple()
            )
            package = next(
                (
                    r
                    for r in all_packages.records
                    if r.decision_package_id == decision_package_id
                ),
                None,
            )
            if package is None:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "status": "not_found",
                        "status_nl": "Decision Package niet gevonden",
                    },
                )
            research_sources = research_repo.list_research_sources_for_asset(
                package.symbol
            )
            provider = build_explanation_provider(settings)
            report = generate_explanation(
                package=package,
                research_sources=research_sources,
                provider=provider,
                repo=explanation_repo,
                max_output_chars=settings.ai_explanation_max_output_chars,
            )
    except StorageConnectionError:
        return _build_blocked_explanation_response(
            reason="storage_connection_failed",
            status_nl="Opslag niet bereikbaar",
            help_nl="De opslag kon niet worden bereikt.",
        )

    explanation_payload: dict[str, object] | None = None
    if report.explanation_id is not None:
        try:
            with storage_provider.checked_connection(require_writable=False) as checked:
                explanation_repo = SqlAlchemyDecisionPackageExplanationRepository(
                    checked.connection, checked.readiness
                )
                latest = explanation_repo.get_latest_explanation_for_package(
                    decision_package_id
                )
                if latest.found and latest.record is not None:
                    explanation_payload = serialize_explanation_for_response(
                        latest.record
                    )
        except StorageConnectionError:
            explanation_payload = None

    return {
        "status": report.status,
        "status_nl": report.status_nl,
        "help_nl": report.help_nl,
        "requested_at": report.requested_at.isoformat(),
        "completed_at": report.completed_at.isoformat(),
        "explanation_id": report.explanation_id,
        "blocking_reason": report.blocking_reason,
        "hallucinated_numbers": list(report.hallucinated_numbers),
        "explanation": explanation_payload,
        "safe_for_self_learning": False,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


@router.get("/decision-packages/{decision_package_id}/explanation")
def read_explanation_for_decision_package(
    decision_package_id: str,
) -> dict[str, object]:
    """Return the latest persisted AI explanation for one Decision Package."""

    base: dict[str, object] = {
        "item": None,
        "help_nl": (
            "AI uitleg is een samenvatting van het Decision Package; "
            "AI bedacht geen nieuwe getallen."
        ),
        "safe_for_self_learning": False,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return base | {"status": "not_configured", "status_nl": "Opslag niet geconfigureerd"}

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=False) as checked:
            explanation_repo = SqlAlchemyDecisionPackageExplanationRepository(
                checked.connection, checked.readiness
            )
            result = explanation_repo.get_latest_explanation_for_package(
                decision_package_id
            )
            if not result.found or result.record is None:
                return base | {
                    "status": "not_found",
                    "status_nl": "Geen AI uitleg voor deze package",
                }
            return base | {
                "status": "ok",
                "status_nl": "AI uitleg beschikbaar",
                "item": serialize_explanation_for_response(result.record),
            }
    except StorageConnectionError:
        return base | {"status": "storage_unavailable", "status_nl": "Opslag niet bereikbaar"}


def _build_blocked_action_draft_response(
    *, reason: str, status_nl: str, help_nl: str
) -> dict[str, object]:
    return {
        "status": "blocked",
        "status_nl": status_nl,
        "help_nl": help_nl,
        "reason": reason,
        "draft_total": 0,
        "draft_persisted": 0,
        "draft_skipped_non_actionable": 0,
        "draft_skipped_sizing_blocked": 0,
        "draft_failed": 0,
        "dry_run_passed": 0,
        "dry_run_failed": 0,
        "failures": [],
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "safe_for_submission": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }


@router.post("/action-drafts/compute")
def run_action_drafts_sync() -> dict[str, object]:
    """Generate one editable LMT/DAY/whole-share draft per actionable
    Decision Package, persist with Orderimpact + dry-run.

    No order submission, no broker action — drafts only.
    """

    if not settings.action_drafts_sync_enabled:
        return _build_blocked_action_draft_response(
            reason="action_drafts_sync_disabled",
            status_nl="Action drafts uitgeschakeld",
            help_nl=(
                "Stel `ACTION_DRAFTS_SYNC_ENABLED=true` in om de "
                "action-draft generator te activeren."
            ),
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url or not storage.writes_enabled:
        return _build_blocked_action_draft_response(
            reason="storage_not_writable",
            status_nl="Opslag niet beschikbaar",
            help_nl="Action drafts vereisen schrijfbare opslag.",
        )

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=True) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            package_repo = SqlAlchemyAssetDecisionPackageRepository(
                checked.connection, checked.readiness
            )
            draft_repo = SqlAlchemyAssetActionDraftRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            if latest_run is None:
                return _build_blocked_action_draft_response(
                    reason="no_ibkr_sync_run",
                    status_nl="Geen IBKR-sync gevonden",
                    help_nl="Voer eerst een IBKR-sync uit.",
                )
            positions = list(
                ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id)
            )
            cash_snapshots = list(
                ibkr_repo.list_ibkr_account_cash_snapshots(latest_run.sync_run_id)
            )
            conids = tuple(p.conid for p in positions if p.conid)
            if not conids:
                return _build_blocked_action_draft_response(
                    reason="no_positions",
                    status_nl="Geen posities",
                    help_nl="Voer eerst een IBKR-sync uit met posities.",
                )
            package_records = list(
                package_repo.list_latest_asset_decision_packages_by_conids(conids).records
            )
            if not package_records:
                return _build_blocked_action_draft_response(
                    reason="no_decision_packages",
                    status_nl="Geen Decision Packages beschikbaar",
                    help_nl="Voer eerst decision-packages-sync uit.",
                )
            exchanges = {
                p.conid: (p.exchange, p.primary_exchange)
                for p in positions
                if p.conid
            }
            cash_currencies = sorted({c.base_currency for c in cash_snapshots if c.base_currency})
            base_currency = cash_currencies[0] if len(cash_currencies) == 1 else None
            total_portfolio_value: Decimal | None = None  # left None for V1 slice
            report = generate_action_drafts(
                decision_packages=package_records,
                repo=draft_repo,
                expected_account_mode=settings.ibkr_expected_environment,
                total_portfolio_value=total_portfolio_value,
                base_currency=base_currency,
                default_buy_value=Decimal(settings.action_drafts_default_buy_value),
                top_up_pct=Decimal(settings.action_drafts_top_up_pct),
                reduce_pct=Decimal(settings.action_drafts_reduce_pct),
                position_exchange_by_conid=exchanges,
            )
    except StorageConnectionError:
        return _build_blocked_action_draft_response(
            reason="storage_connection_failed",
            status_nl="Opslag niet bereikbaar",
            help_nl="De opslag kon niet worden bereikt.",
        )

    return {
        "status": "completed",
        "status_nl": report.status_nl,
        "help_nl": report.help_nl,
        "requested_at": report.requested_at.isoformat(),
        "completed_at": report.completed_at.isoformat(),
        "draft_total": report.draft_total,
        "draft_persisted": report.draft_persisted,
        "draft_skipped_non_actionable": report.draft_skipped_non_actionable,
        "draft_skipped_sizing_blocked": report.draft_skipped_sizing_blocked,
        "draft_failed": report.draft_failed,
        "dry_run_passed": report.dry_run_passed,
        "dry_run_failed": report.dry_run_failed,
        "failures": [dict(item) for item in report.failures],
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "safe_for_submission": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }


@router.get("/action-drafts/latest")
def read_latest_action_drafts() -> dict[str, object]:
    """Return the latest action draft per current position."""

    base: dict[str, object] = {
        "items": [],
        "help_nl": (
            "Action drafts zijn bewerkbaar maar nooit auto-verzonden. Geen "
            "broker submission in deze slice."
        ),
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "safe_for_submission": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return base | {"status": "not_configured", "status_nl": "Opslag niet geconfigureerd"}

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=False) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            draft_repo = SqlAlchemyAssetActionDraftRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            if latest_run is None:
                return base | {
                    "status": "no_ibkr_sync_run",
                    "status_nl": "Geen IBKR-sync gevonden",
                }
            positions = list(
                ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id)
            )
            conids = tuple(p.conid for p in positions if p.conid)
            if not conids:
                return base | {"status": "no_positions", "status_nl": "Geen posities"}
            result = draft_repo.list_latest_asset_action_drafts_by_conids(conids)
            return base | {
                "status": "ok",
                "status_nl": (
                    "Action drafts beschikbaar"
                    if result.records
                    else "Nog geen action drafts"
                ),
                "items": [serialize_action_draft_for_response(r) for r in result.records],
            }
    except StorageConnectionError:
        return base | {"status": "storage_unavailable", "status_nl": "Opslag niet bereikbaar"}


@router.get("/action-drafts/{draft_id}")
def read_action_draft_by_id(draft_id: str) -> dict[str, object]:
    """Single-draft drilldown."""

    base: dict[str, object] = {
        "item": None,
        "help_nl": "Action draft detail; geen submission.",
        "actions_allowed": False,
        "safe_for_submission": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return base | {"status": "not_configured", "status_nl": "Opslag niet geconfigureerd"}

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=False) as checked:
            draft_repo = SqlAlchemyAssetActionDraftRepository(
                checked.connection, checked.readiness
            )
            result = draft_repo.get_asset_action_draft_by_id(draft_id)
            if not result.found or result.record is None:
                return base | {"status": "not_found", "status_nl": "Geen draft gevonden"}
            return base | {
                "status": "ok",
                "status_nl": "Action draft beschikbaar",
                "item": serialize_action_draft_for_response(result.record),
            }
    except StorageConnectionError:
        return base | {"status": "storage_unavailable", "status_nl": "Opslag niet bereikbaar"}


def _build_blocked_submission_response(
    *, reason: str, status_nl: str, help_nl: str, state: str = "draft"
) -> dict[str, object]:
    return {
        "status": "blocked",
        "status_nl": status_nl,
        "help_nl": help_nl,
        "reason": reason,
        "submission_id": None,
        "state": state,
        "ibkr_order_id": None,
        "ibkr_perm_id": None,
        "ibkr_status_text": None,
        "blocking_reason": reason,
        "failures": [],
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "safe_for_submission": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }


@router.post("/action-drafts/{draft_id}/approve")
def approve_action_draft_endpoint(draft_id: str) -> dict[str, object]:
    """Final-confirmation step: re-validate the draft and persist approval."""

    storage = settings.storage
    if not storage.enabled or not storage.database_url or not storage.writes_enabled:
        return _build_blocked_submission_response(
            reason="storage_not_writable",
            status_nl="Opslag niet beschikbaar",
            help_nl="Approval vereist schrijfbare opslag.",
        )

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=True) as checked:
            draft_repo = SqlAlchemyAssetActionDraftRepository(
                checked.connection, checked.readiness
            )
            submission_repo = SqlAlchemyAssetActionDraftSubmissionRepository(
                checked.connection, checked.readiness
            )
            event_repo = SqlAlchemyAssetActionDraftEventRepository(
                checked.connection, checked.readiness
            )
            draft_result = draft_repo.get_asset_action_draft_by_id(draft_id)
            if not draft_result.found or draft_result.record is None:
                raise HTTPException(status_code=404, detail="Action draft not found.")
            result = approve_action_draft(
                draft=draft_result.record,
                submission_repo=submission_repo,
                event_repo=event_repo,
                expected_account_mode=settings.ibkr_expected_environment,
                provider_code=settings.ibkr_paper_order_submission_provider_code,
            )
    except StorageConnectionError:
        return _build_blocked_submission_response(
            reason="storage_connection_failed",
            status_nl="Opslag niet bereikbaar",
            help_nl="De opslag kon niet worden bereikt.",
        )

    return {
        "status": result.status,
        "status_nl": result.status_nl,
        "help_nl": result.help_nl,
        "submission_id": result.submission_id,
        "state": result.state,
        "blocking_reason": result.blocking_reason,
        "failures": list(result.failures),
        "actions_allowed": False,
        "order_submission_allowed": result.status == "approved",
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "safe_for_submission": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }


@router.post("/action-drafts/{draft_id}/submit-to-ibkr-paper")
def submit_action_draft_to_paper_endpoint(draft_id: str) -> dict[str, object]:
    """Submit a previously-approved draft to the IBKR paper gateway."""

    if not settings.ibkr_paper_order_submission_enabled:
        return _build_blocked_submission_response(
            reason="ibkr_paper_order_submission_disabled",
            status_nl="Submission uitgeschakeld",
            help_nl=(
                "Stel `IBKR_PAPER_ORDER_SUBMISSION_ENABLED=true` (plus de real-"
                "client flag en host/port/client-id) in om paper orders te kunnen "
                "verzenden."
            ),
        )

    storage = settings.storage
    if not storage.enabled or not storage.database_url or not storage.writes_enabled:
        return _build_blocked_submission_response(
            reason="storage_not_writable",
            status_nl="Opslag niet beschikbaar",
            help_nl="Submission vereist schrijfbare opslag.",
        )

    submission_client = build_real_order_submission_client(settings)
    if submission_client is None:
        return _build_blocked_submission_response(
            reason="submission_client_unavailable",
            status_nl="Submission client niet geconfigureerd",
            help_nl=(
                "Real ibapi submission client niet beschikbaar; controleer de "
                "submission-flags + host/port/client-id en paper account-mode."
            ),
        )

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=True) as checked:
            draft_repo = SqlAlchemyAssetActionDraftRepository(
                checked.connection, checked.readiness
            )
            submission_repo = SqlAlchemyAssetActionDraftSubmissionRepository(
                checked.connection, checked.readiness
            )
            event_repo = SqlAlchemyAssetActionDraftEventRepository(
                checked.connection, checked.readiness
            )
            draft_result = draft_repo.get_asset_action_draft_by_id(draft_id)
            if not draft_result.found or draft_result.record is None:
                raise HTTPException(status_code=404, detail="Action draft not found.")
            result = submit_action_draft_to_paper(
                draft=draft_result.record,
                submission_repo=submission_repo,
                event_repo=event_repo,
                submission_client=submission_client,
                expected_account_mode=settings.ibkr_expected_environment,
                provider_code=settings.ibkr_paper_order_submission_provider_code,
                approval_valid_minutes=settings.action_draft_approval_valid_minutes,
            )
    except StorageConnectionError:
        return _build_blocked_submission_response(
            reason="storage_connection_failed",
            status_nl="Opslag niet bereikbaar",
            help_nl="De opslag kon niet worden bereikt.",
        )

    return {
        "status": result.status,
        "status_nl": result.status_nl,
        "help_nl": result.help_nl,
        "submission_id": result.submission_id,
        "state": result.state,
        "ibkr_order_id": result.ibkr_order_id,
        "ibkr_perm_id": result.ibkr_perm_id,
        "ibkr_status_text": result.ibkr_status_text,
        "blocking_reason": result.blocking_reason,
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "safe_for_submission": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }


@router.get("/action-drafts/{draft_id}/status")
def read_action_draft_status(draft_id: str) -> dict[str, object]:
    """Return current submission state + event audit log for one draft."""

    base: dict[str, object] = {
        "submission": None,
        "events": [],
        "help_nl": "Read-only status van de draft + audit-log.",
        "actions_allowed": False,
        "safe_for_submission": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return base | {"status": "not_configured", "status_nl": "Opslag niet geconfigureerd"}

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=False) as checked:
            submission_repo = SqlAlchemyAssetActionDraftSubmissionRepository(
                checked.connection, checked.readiness
            )
            event_repo = SqlAlchemyAssetActionDraftEventRepository(
                checked.connection, checked.readiness
            )
            submission_result = submission_repo.get_submission_by_draft_id(draft_id)
            event_list = event_repo.list_asset_action_draft_events(draft_id)
            submission_payload = (
                serialize_submission_for_response(submission_result.record)
                if submission_result.found and submission_result.record is not None
                else None
            )
            return base | {
                "status": "ok",
                "status_nl": (
                    "Submission gevonden"
                    if submission_payload is not None
                    else "Nog geen submission"
                ),
                "submission": submission_payload,
                "events": [serialize_event_for_response(r) for r in event_list.records],
            }
    except StorageConnectionError:
        return base | {"status": "storage_unavailable", "status_nl": "Opslag niet bereikbaar"}


def _build_blocked_reconciliation_response(
    *, reason: str, status_nl: str, help_nl: str
) -> dict[str, object]:
    return {
        "status": "blocked",
        "status_nl": status_nl,
        "help_nl": help_nl,
        "reason": reason,
        "submissions_total": 0,
        "submissions_filled": 0,
        "submissions_cancelled": 0,
        "submissions_rejected": 0,
        "submissions_still_working": 0,
        "submissions_unchanged": 0,
        "submissions_failed": 0,
        "failures": [],
        "actions_allowed": False,
        "order_submission_allowed": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }


@router.post("/action-drafts/reconcile")
def run_action_drafts_reconciliation() -> dict[str, object]:
    """Match in-flight submissions against IBKR sync open-orders +
    executions, then transition to FILLED / CANCELLED / REJECTED →
    RECONCILED."""

    if not settings.reconciliation_sync_enabled:
        return _build_blocked_reconciliation_response(
            reason="reconciliation_sync_disabled",
            status_nl="Reconciliatie uitgeschakeld",
            help_nl="Stel `RECONCILIATION_SYNC_ENABLED=true` in om reconciliatie te activeren.",
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url or not storage.writes_enabled:
        return _build_blocked_reconciliation_response(
            reason="storage_not_writable",
            status_nl="Opslag niet beschikbaar",
            help_nl="Reconciliatie vereist schrijfbare opslag.",
        )

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=True) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            draft_repo = SqlAlchemyAssetActionDraftRepository(
                checked.connection, checked.readiness
            )
            submission_repo = SqlAlchemyAssetActionDraftSubmissionRepository(
                checked.connection, checked.readiness
            )
            event_repo = SqlAlchemyAssetActionDraftEventRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            if latest_run is None:
                return _build_blocked_reconciliation_response(
                    reason="no_ibkr_sync_run",
                    status_nl="Geen IBKR-sync gevonden",
                    help_nl=(
                        "Voer eerst een IBKR-sync uit zodat open orders "
                        "+ executions beschikbaar zijn."
                    ),
                )
            positions = list(
                ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id)
            )
            conids = tuple(p.conid for p in positions if p.conid)
            submissions: list[AssetActionDraftSubmissionRecord] = []
            submitted_quantity_by_draft_id: dict[str, Decimal] = {}
            if conids:
                drafts = list(
                    draft_repo.list_latest_asset_action_drafts_by_conids(conids).records
                )
                for draft in drafts:
                    submission_result = submission_repo.get_submission_by_draft_id(
                        draft.draft_id
                    )
                    if submission_result.found and submission_result.record is not None:
                        submissions.append(submission_result.record)
                        submitted_quantity_by_draft_id[draft.draft_id] = draft.quantity
            open_orders = list(
                ibkr_repo.list_ibkr_open_order_snapshots(latest_run.sync_run_id)
            )
            executions = list(
                ibkr_repo.list_ibkr_execution_snapshots(latest_run.sync_run_id)
            )
            report = reconcile_submissions(
                submissions=submissions,
                open_orders=open_orders,
                executions=executions,
                submitted_quantity_by_draft_id=submitted_quantity_by_draft_id,
                submission_repo=submission_repo,
                event_repo=event_repo,
            )
    except StorageConnectionError:
        return _build_blocked_reconciliation_response(
            reason="storage_connection_failed",
            status_nl="Opslag niet bereikbaar",
            help_nl="De opslag kon niet worden bereikt.",
        )

    return {
        "status": "completed",
        "status_nl": report.status_nl,
        "help_nl": report.help_nl,
        "requested_at": report.requested_at.isoformat(),
        "completed_at": report.completed_at.isoformat(),
        "submissions_total": report.submissions_total,
        "submissions_filled": report.submissions_filled,
        "submissions_cancelled": report.submissions_cancelled,
        "submissions_rejected": report.submissions_rejected,
        "submissions_still_working": report.submissions_still_working,
        "submissions_unchanged": report.submissions_unchanged,
        "submissions_failed": report.submissions_failed,
        "failures": [dict(item) for item in report.failures],
        "actions_allowed": False,
        "order_submission_allowed": False,
        "safe_for_orders": False,
        "safe_for_broker_submission": False,
        "blocks_orders": True,
    }


def _build_blocked_diary_response(
    *, reason: str, status_nl: str, help_nl: str
) -> dict[str, object]:
    return {
        "status": "blocked",
        "status_nl": status_nl,
        "help_nl": help_nl,
        "reason": reason,
        "suggestion_total": 0,
        "entry_total": 0,
        "entries_persisted": 0,
        "entries_skipped_no_forecast": 0,
        "entries_failed": 0,
        "failures": [],
        "safe_for_self_learning": False,
        "safe_for_model_retraining": False,
    }


@router.post("/prediction-diary/evaluate")
def run_prediction_diary_evaluation() -> dict[str, object]:
    """Build/refresh one Prediction Diary entry per suggestion using the
    persisted EOD bars at 1d/1w/1m after the issue date."""

    if not settings.prediction_diary_sync_enabled:
        return _build_blocked_diary_response(
            reason="prediction_diary_sync_disabled",
            status_nl="Prediction Diary uitgeschakeld",
            help_nl="Stel `PREDICTION_DIARY_SYNC_ENABLED=true` in om de diary te activeren.",
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url or not storage.writes_enabled:
        return _build_blocked_diary_response(
            reason="storage_not_writable",
            status_nl="Opslag niet beschikbaar",
            help_nl="Prediction Diary vereist schrijfbare opslag.",
        )

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=True) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            forecast_repo = SqlAlchemyAssetForecastRepository(
                checked.connection, checked.readiness
            )
            suggestion_repo = SqlAlchemyAssetSuggestionRepository(
                checked.connection, checked.readiness
            )
            bar_repo = SqlAlchemyMarketDataBarRepository(
                checked.connection, checked.readiness
            )
            diary_repo = SqlAlchemyPredictionDiaryRepository(
                checked.connection, checked.readiness
            )
            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            positions = (
                list(ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id))
                if latest_run is not None
                else []
            )
            conids = tuple(p.conid for p in positions if p.conid)
            if not conids:
                return _build_blocked_diary_response(
                    reason="no_positions",
                    status_nl="Geen posities",
                    help_nl="Voer eerst een IBKR-sync uit met posities.",
                )
            suggestions = list(
                suggestion_repo.list_latest_asset_suggestions_by_conids(conids).records
            )
            forecast_result = forecast_repo.list_latest_asset_forecasts_by_conids(conids)
            forecasts_by_id = {f.forecast_id: f for f in forecast_result.records}
            bars: list[MarketDataBarRecord] = []
            for conid in conids:
                bars.extend(bar_repo.list_market_data_bars_by_conid(conid).records)
            tolerance = Decimal(settings.prediction_diary_inconclusive_tolerance_pct)
            report = evaluate_prediction_diary(
                suggestions=suggestions,
                forecasts_by_id=forecasts_by_id,
                bars=bars,
                repo=diary_repo,
                inconclusive_tolerance_pct=tolerance,
            )
    except StorageConnectionError:
        return _build_blocked_diary_response(
            reason="storage_connection_failed",
            status_nl="Opslag niet bereikbaar",
            help_nl="De opslag kon niet worden bereikt.",
        )

    return {
        "status": "completed",
        "status_nl": report.status_nl,
        "help_nl": report.help_nl,
        "requested_at": report.requested_at.isoformat(),
        "completed_at": report.completed_at.isoformat(),
        "suggestion_total": report.suggestion_total,
        "entry_total": report.entry_total,
        "entries_persisted": report.entries_persisted,
        "entries_skipped_no_forecast": report.entries_skipped_no_forecast,
        "entries_failed": report.entries_failed,
        "failures": [dict(item) for item in report.failures],
        "safe_for_self_learning": False,
        "safe_for_model_retraining": False,
    }


@router.get("/prediction-diary")
def read_prediction_diary() -> dict[str, object]:
    """Return all Prediction Diary entries (most recent first)."""

    base: dict[str, object] = {
        "items": [],
        "help_nl": (
            "Prediction Diary entries zijn deterministisch geclassificeerd. "
            "Geen AI-scoring, geen silent self-learning."
        ),
        "safe_for_self_learning": False,
        "safe_for_model_retraining": False,
    }

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return base | {"status": "not_configured", "status_nl": "Opslag niet geconfigureerd"}

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=False) as checked:
            diary_repo = SqlAlchemyPredictionDiaryRepository(
                checked.connection, checked.readiness
            )
            result = diary_repo.list_prediction_diary_entries()
            return base | {
                "status": "ok",
                "status_nl": (
                    "Prediction Diary entries beschikbaar"
                    if result.records
                    else "Nog geen entries"
                ),
                "items": [
                    serialize_prediction_diary_entry_for_response(r) for r in result.records
                ],
            }
    except StorageConnectionError:
        return base | {"status": "storage_unavailable", "status_nl": "Opslag niet bereikbaar"}


def _build_blocked_briefing_response(
    *, reason: str, status_nl: str, help_nl: str
) -> dict[str, object]:
    return {
        "status": "blocked",
        "status_nl": status_nl,
        "help_nl": help_nl,
        "reason": reason,
        "briefing_id": None,
        "alert_count": 0,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


@router.post("/briefings/daily/compute")
def run_daily_briefing() -> dict[str, object]:
    """Build and persist one deterministic daily Dutch briefing.

    The briefing is computed from the persisted positions / cash /
    suggestions / Decision Packages / action drafts / diary entries /
    critical events. AI never authors the summary.
    """

    if not settings.daily_briefing_sync_enabled:
        return _build_blocked_briefing_response(
            reason="daily_briefing_sync_disabled",
            status_nl="Dagbriefing uitgeschakeld",
            help_nl=(
                "Stel `DAILY_BRIEFING_SYNC_ENABLED=true` in om de "
                "dagbriefing te activeren."
            ),
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url or not storage.writes_enabled:
        return _build_blocked_briefing_response(
            reason="storage_not_writable",
            status_nl="Opslag niet beschikbaar",
            help_nl="Dagbriefing vereist schrijfbare opslag.",
        )

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=True) as checked:
            ibkr_repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            suggestion_repo = SqlAlchemyAssetSuggestionRepository(
                checked.connection, checked.readiness
            )
            package_repo = SqlAlchemyAssetDecisionPackageRepository(
                checked.connection, checked.readiness
            )
            draft_repo = SqlAlchemyAssetActionDraftRepository(
                checked.connection, checked.readiness
            )
            event_repo = SqlAlchemyAssetActionDraftEventRepository(
                checked.connection, checked.readiness
            )
            diary_repo = SqlAlchemyPredictionDiaryRepository(
                checked.connection, checked.readiness
            )
            briefing_repo = SqlAlchemyDailyBriefingRepository(
                checked.connection, checked.readiness
            )

            latest_run = ibkr_repo.get_latest_ibkr_sync_run()
            positions = (
                list(ibkr_repo.list_ibkr_position_snapshots(latest_run.sync_run_id))
                if latest_run is not None
                else []
            )
            cash_snapshots = (
                list(
                    ibkr_repo.list_ibkr_account_cash_snapshots(latest_run.sync_run_id)
                )
                if latest_run is not None
                else []
            )
            conids = tuple(p.conid for p in positions if p.conid)
            suggestions = (
                list(
                    suggestion_repo.list_latest_asset_suggestions_by_conids(
                        conids
                    ).records
                )
                if conids
                else []
            )
            decision_packages = (
                list(
                    package_repo.list_latest_asset_decision_packages_by_conids(
                        conids
                    ).records
                )
                if conids
                else []
            )
            action_drafts = (
                list(
                    draft_repo.list_latest_asset_action_drafts_by_conids(
                        conids
                    ).records
                )
                if conids
                else []
            )
            diary_entries = list(diary_repo.list_prediction_diary_entries().records)
            critical_events: list[AssetActionDraftEventRecord] = []
            for draft in action_drafts:
                events_result = event_repo.list_asset_action_draft_events(
                    draft.draft_id
                )
                critical_events.extend(
                    e for e in events_result.records if e.severity == "critical"
                )

            base_currencies = sorted(
                {c.base_currency for c in cash_snapshots if c.base_currency}
            )
            base_currency = (
                base_currencies[0] if len(base_currencies) == 1 else None
            )

            report = generate_daily_briefing(
                positions=positions,
                cash_snapshots=cash_snapshots,
                suggestions=suggestions,
                decision_packages=decision_packages,
                action_drafts=action_drafts,
                diary_entries=diary_entries,
                critical_events=critical_events,
                base_currency=base_currency,
                fx_freshness_status=None,
                lookback_hours=settings.daily_briefing_lookback_hours,
                repo=briefing_repo,
            )
    except StorageConnectionError:
        return _build_blocked_briefing_response(
            reason="storage_connection_failed",
            status_nl="Opslag niet bereikbaar",
            help_nl="De opslag kon niet worden bereikt.",
        )

    return {
        "status": report.status,
        "status_nl": report.status_nl,
        "help_nl": report.help_nl,
        "requested_at": report.requested_at.isoformat(),
        "completed_at": report.completed_at.isoformat(),
        "briefing_id": report.briefing_id,
        "alert_count": report.alert_count,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    }


@router.get("/briefings/daily/latest")
def read_latest_daily_briefing() -> dict[str, object]:
    """Return the latest persisted daily briefing + its alerts."""

    base: dict[str, object] = {
        "item": None,
        "help_nl": (
            "Dagbriefings zijn deterministisch gebouwd uit reeds opgeslagen "
            "evidence. AI schrijft geen briefings."
        ),
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return base | {"status": "not_configured", "status_nl": "Opslag niet geconfigureerd"}

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=False) as checked:
            briefing_repo = SqlAlchemyDailyBriefingRepository(
                checked.connection, checked.readiness
            )
            result = briefing_repo.get_latest_daily_briefing()
            if not result.found or result.record is None:
                return base | {
                    "status": "not_found",
                    "status_nl": "Nog geen dagbriefing",
                }
            alerts = briefing_repo.list_alerts_for_briefing(
                result.record.briefing_id
            )
            return base | {
                "status": "ok",
                "status_nl": "Dagbriefing beschikbaar",
                "item": serialize_briefing_for_response(result.record, alerts.records),
            }
    except StorageConnectionError:
        return base | {"status": "storage_unavailable", "status_nl": "Opslag niet bereikbaar"}


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
                str(record.day_change_percent) if record.day_change_percent is not None else None
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
                str(readiness.usable_price) if readiness.usable_price is not None else None
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


@router.get("/scheduler/jobs")
def read_scheduler_jobs(request: Request) -> dict[str, object]:
    """List scheduler jobs currently registered.

    Returns an empty list when the scheduler is disabled. Each entry
    carries the job name, cron expression and next-fire timestamp.
    """

    from portfolio_outlook_api.scheduler import list_jobs

    scheduler = getattr(request.app.state, "scheduler", None)
    jobs = list_jobs(scheduler)
    return {
        "status": "ok" if scheduler is not None else "disabled",
        "status_nl": (
            "Scheduler actief" if scheduler is not None else "Scheduler uitgeschakeld"
        ),
        "help_nl": (
            "Stel `SCHEDULER_ENABLED=true` in om de in-process scheduler te starten."
        ),
        "scheduler_enabled": settings.scheduler_enabled,
        "scheduler_timezone": settings.scheduler_timezone,
        "scheduler_daily_briefing_cron": settings.scheduler_daily_briefing_cron,
        "items": [
            {
                "job_id": j.job_id,
                "job_name": j.job_name,
                "cron_expression": j.cron_expression,
                "next_run_at": j.next_run_at.isoformat() if j.next_run_at else None,
            }
            for j in jobs
        ],
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


@router.get("/scheduler/runs/latest")
def read_latest_scheduler_run(job_name: str | None = None) -> dict[str, object]:
    """Return the most recent scheduler run (optionally filtered by job)."""

    base: dict[str, object] = {
        "item": None,
        "help_nl": (
            "Scheduler-runs zijn audit-rows; één per fire. Een succesvolle "
            "run promoveert nooit naar een order."
        ),
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return base | {"status": "not_configured", "status_nl": "Opslag niet geconfigureerd"}

    storage_provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with storage_provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemySchedulerRunRepository(
                checked.connection, checked.readiness
            )
            result = repo.get_latest_scheduler_run(job_name=job_name)
            if not result.found or result.record is None:
                return base | {
                    "status": "not_found",
                    "status_nl": "Nog geen scheduler-run",
                }
            record = result.record
            return base | {
                "status": "ok",
                "status_nl": "Laatste scheduler-run opgehaald",
                "item": {
                    "run_id": record.run_id,
                    "job_name": record.job_name,
                    "scheduled_at": record.scheduled_at.isoformat(),
                    "started_at": record.started_at.isoformat(),
                    "finished_at": (
                        record.finished_at.isoformat() if record.finished_at else None
                    ),
                    "status": record.status,
                    "error_text": record.error_text,
                    "triggered_by": record.triggered_by,
                },
            }
    except StorageConnectionError:
        return base | {"status": "storage_unavailable", "status_nl": "Opslag niet bereikbaar"}


@router.get("/ibkr/account/mode")
def read_ibkr_account_mode() -> dict[str, object]:
    """Report the IBKR account mode (paper / live) for the dashboard badge.

    Per the §21.1 doctrine relock the account-mode is reported, not
    gated. The detected mode comes from the configured
    ``ibkr_sync_account_mode`` setting (which mirrors the connected
    account); future slices will derive this from the IBKR session
    response directly.
    """

    detected = (settings.ibkr_sync_account_mode or "").strip().lower() or "unknown"
    display = "PAPER" if detected == "paper" else "LIVE" if detected == "live" else "UNKNOWN"
    return {
        "status": "ok",
        "mode": detected,
        "display_label": display,
        "expected_environment": settings.ibkr_expected_environment,
        "help_nl": (
            "De modus wordt door het verbonden IBKR-account bepaald, niet "
            "door een app-side gate. Het dashboard toont de modus voor "
            "elke approval."
        ),
        "safe_for_orders": False,
        "blocks_orders": True,
    }
