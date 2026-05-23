from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ai_trading_agent_storage import (
    SqlAlchemyIbkrSyncSnapshotRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_session_status import IbkrSessionStatusAdapter
from portfolio_outlook_api.ibkr_status import build_ibkr_status_placeholder
from portfolio_outlook_api.ibkr_sync_contracts import (
    IbkrCash,
    IbkrExecution,
    IbkrOpenOrder,
    IbkrPosition,
    IbkrReadOnlyAdapter,
)
from portfolio_outlook_api.ibkr_sync_persistence import (
    IbkrSyncPersistencePayload,
    map_cash_snapshot_record,
    map_execution_snapshot_record,
    map_open_order_snapshot_record,
    map_position_snapshot_record,
    map_sync_run_record,
    persist_ibkr_sync_payload,
)
from portfolio_outlook_api.ibkr_sync_readiness import build_ibkr_sync_readiness
from portfolio_outlook_api.ibkr_sync_validation import validate_ibkr_sync_payloads


class NotConfiguredIbkrAdapter(IbkrReadOnlyAdapter):
    def sync_account_summary(self) -> list[IbkrCash]:
        return []

    def sync_positions(self) -> list[IbkrPosition]:
        return []

    def sync_open_orders(self) -> list[IbkrOpenOrder]:
        return []

    def sync_executions(self) -> list[IbkrExecution]:
        return []


class InMemoryIbkrSyncStore:
    def __init__(self) -> None:
        self.runs: list[dict[str, object]] = []
        self.positions: list[dict[str, object]] = []
        self.cash: list[dict[str, object]] = []
        self.open_orders: list[dict[str, object]] = []
        self.executions: list[dict[str, object]] = []


STORE = InMemoryIbkrSyncStore()


def _configured(settings: Settings) -> bool:
    return bool(
        settings.ibkr_sync_enabled
        and settings.ibkr_sync_host
        and settings.ibkr_sync_port is not None
        and settings.ibkr_sync_client_id is not None
    )


def _resolve_repo(
    settings: Settings,
    *,
    require_writable: bool,
) -> tuple[SqlAlchemyIbkrSyncSnapshotRepository | None, object | None, str]:
    storage = settings.storage
    if not storage.enabled:
        return None, None, "Storage staat uit; alleen geheugenopslag actief."
    if not storage.database_url:
        return None, None, "Storage is niet geconfigureerd; alleen geheugenopslag actief."
    if require_writable and not storage.writes_enabled:
        return None, None, "Storage schrijven staat uit; alleen geheugenopslag actief."
    provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        checked = provider.checked_connection(require_writable=require_writable)
        context = checked.__enter__()
        repo = SqlAlchemyIbkrSyncSnapshotRepository(
            context.connection,
            context.readiness,
        )
        return repo, checked, ""
    except StorageConnectionError:
        return None, None, "Storage niet beschikbaar; alleen geheugenopslag actief."


def _build_readiness(
    settings: Settings,
    session_status_adapter: IbkrSessionStatusAdapter | None = None,
) -> dict[str, object]:
    session_status = build_ibkr_status_placeholder(
        settings, session_status_adapter=session_status_adapter
    )
    return build_ibkr_sync_readiness(settings, session_status)


def run_sync(
    settings: Settings,
    adapter: IbkrReadOnlyAdapter | None = None,
    *,
    session_status_adapter: IbkrSessionStatusAdapter | None = None,
) -> dict[str, object]:
    readiness = _build_readiness(settings, session_status_adapter=session_status_adapter)
    readiness_status = str(readiness["sync_readiness_status"])
    if readiness_status != "ready_for_manual_readonly_sync":
        blocked_status = "sync_readiness_blocked"
        blocked_status_nl = "IBKR-sync geblokkeerd"
        if readiness_status == "needs_control":
            blocked_status = "sync_readiness_needs_control"
            blocked_status_nl = "Controle nodig"
        return read_status(settings, readiness=readiness) | {
            "status": blocked_status,
            "status_nl": blocked_status_nl,
            "sync_run_id": None,
            "persistence_mode": "none",
            "persistence_status_nl": "Geen sync uitgevoerd",
            "persistence_help_nl": (
                "Readiness/preflight blokkeerde handmatige read-only sync."
            ),
            "account_summary_status": "disabled",
            "positions_status": "disabled",
            "open_orders_status": "disabled",
            "executions_status": "disabled",
            "positions_count": 0,
            "cash_values_count": 0,
            "open_orders_count": 0,
            "executions_count": 0,
            "started_at": None,
            "completed_at": None,
            "payload_validation_status": "not_attempted",
            "payload_validation_status_nl": "Niet uitgevoerd",
            "payload_validation_error_count": 0,
            "payload_validation_errors": [],
            "payload_validation_help_nl": "Validatie niet uitgevoerd omdat sync geblokkeerd is.",
        }

    now = datetime.now(UTC)
    run_id = f"ibkr-sync-{uuid4()}"
    result_status = "disabled"
    account_summary_status = "disabled"
    positions_status = "disabled"
    open_orders_status = "disabled"
    executions_status = "disabled"
    positions: list[IbkrPosition] = []
    cash_items: list[IbkrCash] = []
    open_orders: list[IbkrOpenOrder] = []
    executions: list[IbkrExecution] = []

    if not settings.ibkr_sync_enabled:
        result_status = "disabled"
    elif settings.ibkr_sync_account_mode.lower() != "paper":
        result_status = "wrong_account_mode"
    elif not settings.ibkr_sync_readonly:
        result_status = "provider_error"
    elif not _configured(settings):
        result_status = "not_configured"
    else:
        active_adapter = adapter or NotConfiguredIbkrAdapter()
        try:
            cash_items = active_adapter.sync_account_summary()
            positions = active_adapter.sync_positions()
            open_orders = active_adapter.sync_open_orders()
            executions = active_adapter.sync_executions()
            account_summary_status = "account_summary_received" if cash_items else "partial_data"
            positions_status = "positions_received" if positions else "partial_data"
            open_orders_status = "open_orders_received" if open_orders else "no_open_orders"
            executions_status = "executions_received" if executions else "no_executions"
            result_status = "partial_data"
            if cash_items and positions:
                result_status = "paper_account_confirmed"

            validation_result = validate_ibkr_sync_payloads(
                cash_items, positions, open_orders, executions
            )
            if not validation_result.passed:
                return read_status(settings, readiness=readiness) | {
                    "status": "payload_validation_failed",
                    "status_nl": "Payloadvalidatie mislukt",
                    "sync_run_id": None,
                    "persistence_mode": "none",
                    "persistence_status_nl": "Geen sync uitgevoerd",
                    "persistence_help_nl": "Adapterpayload ongeldig; niets opgeslagen.",
                    "account_summary_status": "account_summary_received" if cash_items else "partial_data",
                    "positions_status": "positions_received" if positions else "partial_data",
                    "open_orders_status": "open_orders_received" if open_orders else "no_open_orders",
                    "executions_status": "executions_received" if executions else "no_executions",
                    "positions_count": 0,
                    "cash_values_count": 0,
                    "open_orders_count": 0,
                    "executions_count": 0,
                    "started_at": None,
                    "completed_at": None,
                    "payload_validation_status": "failed",
                    "payload_validation_status_nl": "Mislukt",
                    "payload_validation_error_count": len(validation_result.errors),
                    "payload_validation_errors": [error.__dict__ for error in validation_result.errors],
                    "payload_validation_help_nl": "Controleer adapterpayload; opslag is veilig geblokkeerd.",
                }
        except TimeoutError:
            result_status = "timeout"
            account_summary_status = "timeout"
            positions_status = "timeout"
            open_orders_status = "timeout"
            executions_status = "timeout"
        except Exception:
            result_status = "provider_error"
            account_summary_status = "provider_error"
            positions_status = "provider_error"
            open_orders_status = "provider_error"
            executions_status = "provider_error"

    completed_at = datetime.now(UTC)
    run_record = {
            "sync_run_id": run_id,
            "started_at": now.isoformat(),
            "completed_at": completed_at.isoformat(),
            "provider_code": settings.ibkr_sync_provider_code,
            "provider_environment": settings.ibkr_sync_account_mode,
            "account_mode": settings.ibkr_sync_account_mode,
            "readonly": settings.ibkr_sync_readonly,
            "status": result_status,
            "account_summary_status": account_summary_status,
            "positions_status": positions_status,
            "open_orders_status": open_orders_status,
            "executions_status": executions_status,
            "positions_count": len(positions),
            "cash_values_count": len(cash_items),
            "open_orders_count": len(open_orders),
            "executions_count": len(executions),
        }
    STORE.runs.append(run_record)
    for p in positions:
        STORE.positions.append(
            {
                "sync_run_id": run_id,
                "symbol": p.symbol,
                "quantity": str(p.quantity),
            }
        )
    for c in cash_items:
        STORE.cash.append(
            {
                "sync_run_id": run_id,
                "cash": str(c.cash),
                "account_ref": c.account_ref,
            }
        )
    for order in open_orders:
        STORE.open_orders.append(
            {
                "sync_run_id": run_id,
                "ibkr_order_id": order.ibkr_order_id,
                "symbol": order.symbol,
                "quantity": str(order.quantity),
                "status": order.status,
            }
        )
    for execution in executions:
        STORE.executions.append(
            {
                "sync_run_id": run_id,
                "execution_id": execution.execution_id,
                "symbol": execution.symbol,
                "quantity": str(execution.quantity),
                "price": str(execution.price),
            }
        )

    persistence_mode = "memory"
    persistence_help_nl = "Alleen geheugenopslag actief."
    repo, connection_ctx, storage_help_nl = _resolve_repo(settings, require_writable=True)
    if repo is not None:
        try:
            payload = IbkrSyncPersistencePayload(
                sync_run=map_sync_run_record(
                    sync_run_id=run_id,
                    started_at=now,
                    completed_at=completed_at,
                    provider_code=settings.ibkr_sync_provider_code,
                    provider_environment=settings.ibkr_sync_account_mode,
                    account_mode=settings.ibkr_sync_account_mode,
                    readonly=settings.ibkr_sync_readonly,
                    status=result_status,
                    account_summary_status=account_summary_status,
                    positions_status=positions_status,
                    open_orders_status=open_orders_status,
                    executions_status=executions_status,
                    positions_count=len(positions),
                    cash_values_count=len(cash_items),
                    open_orders_count=len(open_orders),
                    executions_count=len(executions),
                    status_nl=None,
                    next_step_nl=None,
                    help_nl=None,
                ),
                cash_snapshots=[
                    map_cash_snapshot_record(
                        sync_run_id=run_id,
                        item=item,
                        received_at=completed_at,
                        stored_at=completed_at,
                    )
                    for item in cash_items
                ],
                position_snapshots=[
                    map_position_snapshot_record(
                        sync_run_id=run_id,
                        item=item,
                        received_at=completed_at,
                        stored_at=completed_at,
                    )
                    for item in positions
                ],
                open_order_snapshots=[
                    map_open_order_snapshot_record(
                        sync_run_id=run_id,
                        item=item,
                        received_at=completed_at,
                        stored_at=completed_at,
                    )
                    for item in open_orders
                ],
                execution_snapshots=[
                    map_execution_snapshot_record(
                        sync_run_id=run_id,
                        item=item,
                        received_at=completed_at,
                        stored_at=completed_at,
                    )
                    for item in executions
                ],
            )
            persist_ibkr_sync_payload(payload, repo)
            persistence_mode = "durable"
            persistence_help_nl = "Storage-opslag voltooid."
        except Exception:
            persistence_help_nl = "Storage-opslag mislukt; alleen geheugenopslag actief."
        finally:
            if connection_ctx is not None and hasattr(connection_ctx, "__exit__"):
                connection_ctx.__exit__(None, None, None)
    elif storage_help_nl:
        persistence_help_nl = storage_help_nl
    return read_status(settings, readiness=readiness) | {
        "sync_run_id": run_id,
        "persistence_mode": persistence_mode,
        "persistence_status_nl": (
            "Duurzame opslag actief"
            if persistence_mode == "durable"
            else "Geheugenfallback actief"
        ),
        "persistence_help_nl": persistence_help_nl,
        "payload_validation_status": "passed",
        "payload_validation_status_nl": "Geslaagd",
        "payload_validation_error_count": 0,
        "payload_validation_errors": [],
        "payload_validation_help_nl": "Payloadvalidatie geslaagd.",
    }


def _int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def read_status(
    settings: Settings,
    readiness: dict[str, object] | None = None,
) -> dict[str, object]:
    latest = STORE.runs[-1] if STORE.runs else None
    status = "disabled" if not settings.ibkr_sync_enabled else "configured_not_connected"
    status_nl = "IBKR-sync niet geconfigureerd"
    next_step_nl = "Activeer handmatig met paper-only instellingen."
    if status != "disabled":
        status_nl = "Read-only synchronisatie"
        next_step_nl = "Start handmatige sync."
    if latest is not None:
        status = str(latest["status"])
        if status == "wrong_account_mode":
            status_nl = "Alleen papiermodus toegestaan"
            next_step_nl = "Controleer accountmodus paper."
        else:
            status_nl = "Read-only synchronisatie"
            next_step_nl = "Geen orders mogelijk"

    resolved_readiness = readiness
    if resolved_readiness is None:
        resolved_readiness = _build_readiness(settings)
    return {
        "status": status,
        "provider_code": settings.ibkr_sync_provider_code,
        "provider_environment": settings.ibkr_sync_account_mode,
        "account_mode": settings.ibkr_sync_account_mode,
        "readonly": settings.ibkr_sync_readonly,
        "account_summary_status": latest["account_summary_status"] if latest else "disabled",
        "positions_status": latest["positions_status"] if latest else "disabled",
        "open_orders_status": latest["open_orders_status"] if latest else "disabled",
        "executions_status": latest["executions_status"] if latest else "disabled",
        "positions_count": _int_value(latest["positions_count"]) if latest else 0,
        "cash_values_count": _int_value(latest["cash_values_count"]) if latest else 0,
        "open_orders_count": _int_value(latest["open_orders_count"]) if latest else 0,
        "executions_count": _int_value(latest["executions_count"]) if latest else 0,
        "started_at": latest["started_at"] if latest else None,
        "completed_at": latest["completed_at"] if latest else None,
        "status_nl": status_nl,
        "next_step_nl": next_step_nl,
        "help_nl": "Geen brokerdata opgeslagen zonder echte IBKR-respons",
        "payload_validation_status": "not_attempted",
        "payload_validation_status_nl": "Niet uitgevoerd",
        "payload_validation_error_count": 0,
        "payload_validation_errors": [],
        "payload_validation_help_nl": "Validatie wordt uitgevoerd tijdens een toegelaten handmatige sync.",
        "sync_allowed": bool(resolved_readiness.get("manual_sync_allowed", False)),
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
        "can_submit_orders": False,
        "safe_for_orders": False,
        "blocks_orders": True,
    } | resolved_readiness
