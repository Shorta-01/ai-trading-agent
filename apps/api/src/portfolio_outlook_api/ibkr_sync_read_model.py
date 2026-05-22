from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    IbkrAccountCashSnapshotRecord,
    IbkrExecutionSnapshotRecord,
    IbkrOpenOrderSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
    SqlAlchemyIbkrSyncSnapshotRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_api.config import StorageSettings


def _serialize_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def serialize_sync_status_record(record: IbkrSyncRunRecord) -> dict[str, object]:
    return {
        "status": record.status,
        "provider_code": record.provider_code,
        "provider_environment": record.provider_environment,
        "account_mode": record.account_mode,
        "readonly": record.readonly,
        "account_summary_status": record.account_summary_status,
        "positions_status": record.positions_status,
        "open_orders_status": record.open_orders_status,
        "executions_status": record.executions_status,
        "positions_count": record.positions_count,
        "cash_values_count": record.cash_values_count,
        "open_orders_count": record.open_orders_count,
        "executions_count": record.executions_count,
        "started_at": _serialize_datetime(record.started_at),
        "completed_at": _serialize_datetime(record.completed_at),
        "status_nl": record.status_nl or "Read-only synchronisatie",
        "next_step_nl": record.next_step_nl or "Geen orders mogelijk",
        "help_nl": record.help_nl or "Duurzame IBKR-syncstatus beschikbaar.",
        "sync_allowed": True,
        "actions_allowed": False,
        "order_submission_allowed": False,
        "order_modification_allowed": False,
        "order_cancellation_allowed": False,
        "suggestions_allowed": False,
    }


def serialize_position_record(record: IbkrPositionSnapshotRecord) -> dict[str, object]:
    return {
        "sync_run_id": record.sync_run_id,
        "symbol": record.symbol,
        "quantity": _serialize_decimal(record.quantity),
    }


def serialize_cash_record(record: IbkrAccountCashSnapshotRecord) -> dict[str, object]:
    return {
        "sync_run_id": record.sync_run_id,
        "cash": _serialize_decimal(record.cash),
        "account_ref": record.account_ref,
    }


def serialize_open_order_record(record: IbkrOpenOrderSnapshotRecord) -> dict[str, object]:
    return {
        "sync_run_id": record.sync_run_id,
        "ibkr_order_id": record.ibkr_order_id,
        "symbol": record.symbol,
        "quantity": _serialize_decimal(record.quantity),
        "status": record.status,
    }


def serialize_execution_record(record: IbkrExecutionSnapshotRecord) -> dict[str, object]:
    return {
        "sync_run_id": record.sync_run_id,
        "execution_id": record.execution_id,
        "symbol": record.symbol,
        "quantity": _serialize_decimal(record.quantity),
        "price": _serialize_decimal(record.price),
    }


@dataclass(frozen=True)
class DurableIbkrSyncReadResult:
    latest_run: IbkrSyncRunRecord | None
    storage_help_nl: str | None


def read_latest_ibkr_sync_run(storage: StorageSettings) -> DurableIbkrSyncReadResult:
    if not storage.enabled:
        return DurableIbkrSyncReadResult(
            latest_run=None,
            storage_help_nl="Storage staat uit; geheugenfallback actief.",
        )
    if not storage.database_url:
        return DurableIbkrSyncReadResult(
            latest_run=None,
            storage_help_nl="Storage is niet geconfigureerd; geheugenfallback actief.",
        )

    provider = StorageConnectionProvider(
        build_database_connection_settings(storage.database_url)
    )
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection,
                checked.readiness,
            )
            return DurableIbkrSyncReadResult(
                latest_run=repo.get_latest_ibkr_sync_run(),
                storage_help_nl=None,
            )
    except StorageConnectionError:
        return DurableIbkrSyncReadResult(
            latest_run=None,
            storage_help_nl="Storage niet beschikbaar; geheugenfallback actief.",
        )
