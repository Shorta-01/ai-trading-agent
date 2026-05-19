"""Repository contracts for future broker sync and reconciliation persistence.

This module defines interface-only protocols and DTO/result contracts.
It intentionally does not open sessions, read environment variables, or connect to a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class StorageWriteResult:
    accepted: bool
    record_id: str | None
    table_name: str
    audit_required: bool
    explanation_nl: str


@dataclass(frozen=True)
class StorageReadResult[T]:
    found: bool
    record: T | None
    table_name: str
    explanation_nl: str


@dataclass(frozen=True)
class StorageListResult[T]:
    records: tuple[T, ...]
    table_name: str
    explanation_nl: str


@dataclass(frozen=True)
class RepositoryHealthStatus:
    available: bool
    connected: bool
    migrations_current: bool
    read_only: bool
    explanation_nl: str


@dataclass(frozen=True)
class BrokerAccountRecord:
    broker_account_id: str
    broker_system: str
    ibkr_account_ref: str | None
    account_label: str
    account_mode: str
    connection_status: str
    configured: bool
    paper_account: bool
    live_trading_allowed: bool
    source_of_truth_status: str
    created_at: datetime
    updated_at: datetime | None
    explanation_nl: str


@dataclass(frozen=True)
class BrokerSyncRunRecord:
    broker_sync_run_id: str
    broker_account_id: str | None
    broker_system: str
    sync_mode: str
    sync_status: str
    started_at: datetime
    completed_at: datetime | None
    planned_data_kinds_json: tuple[str, ...] | None
    data_source_types_json: tuple[str, ...] | None
    requires_ibkr_configuration: bool
    requires_broker_session: bool
    blocks_suggestions_until_complete: bool
    summary_nl: str
    help_nl: str
    source_reference_ids_json: tuple[str, ...] | None
    audit_event_ids_json: tuple[str, ...] | None


@dataclass(frozen=True)
class BrokerPositionSnapshotRecord:
    broker_position_snapshot_id: str
    broker_sync_run_id: str
    broker_account_id: str
    broker_system: str
    imported_at: datetime
    asset_identifier: str
    asset_symbol: str
    asset_type: str
    currency: str
    quantity: Decimal
    average_cost: Decimal | None
    market_value: Decimal | None
    source_data_kind: str
    origin: str
    source_reference_ids_json: tuple[str, ...] | None
    explanation_nl: str


@dataclass(frozen=True)
class BrokerCashSnapshotRecord:
    broker_cash_snapshot_id: str
    broker_sync_run_id: str
    broker_account_id: str
    broker_system: str
    imported_at: datetime
    currency: str
    cash_amount: Decimal
    source_data_kind: str
    origin: str
    source_reference_ids_json: tuple[str, ...] | None
    explanation_nl: str


@dataclass(frozen=True)
class BrokerExecutionSnapshotRecord:
    broker_execution_snapshot_id: str
    broker_sync_run_id: str
    broker_account_id: str
    broker_system: str
    imported_at: datetime
    execution_time: datetime
    execution_id: str
    order_id: str | None
    asset_identifier: str
    asset_symbol: str
    asset_type: str
    side: str
    quantity: Decimal
    price: Decimal
    currency: str
    origin: str
    source_reference_ids_json: tuple[str, ...] | None
    explanation_nl: str


@dataclass(frozen=True)
class BrokerCommissionSnapshotRecord:
    broker_commission_snapshot_id: str
    broker_sync_run_id: str
    broker_account_id: str
    broker_system: str
    imported_at: datetime
    execution_time: datetime
    execution_id: str
    commission_amount: Decimal
    currency: str
    realized_pnl: Decimal | None
    source_reference_ids_json: tuple[str, ...] | None
    explanation_nl: str


@dataclass(frozen=True)
class BrokerReconciliationReportRecord:
    broker_reconciliation_report_id: str
    broker_sync_run_id: str
    broker_account_id: str | None
    broker_system: str
    status: str
    suggestion_policy: str
    can_create_suggestions: bool
    can_create_orders: bool
    checked_at: datetime
    title_nl: str
    summary_nl: str
    help_nl: str


@dataclass(frozen=True)
class BrokerReconciliationDifferenceRecord:
    broker_reconciliation_difference_id: str
    broker_reconciliation_report_id: str
    broker_account_id: str
    broker_system: str
    difference_kind: str
    severity: str
    detected_at: datetime
    broker_value: str | None
    local_value: str | None
    asset_identifier: str | None
    currency: str | None
    blocks_suggestions: bool
    requires_manual_review: bool
    summary_nl: str
    help_nl: str
    source_reference_ids_json: tuple[str, ...] | None
    audit_event_ids_json: tuple[str, ...] | None


@dataclass(frozen=True)
class ExternalBrokerActivityRecord:
    external_broker_activity_id: str
    broker_account_id: str
    broker_system: str
    detected_at: datetime
    origin: str
    data_kind: str
    related_execution_id: str | None
    related_asset_identifier: str | None
    summary_nl: str
    help_nl: str
    source_reference_ids_json: tuple[str, ...] | None
    audit_event_ids_json: tuple[str, ...] | None


class BrokerAccountRepository(Protocol):
    def get_by_id(self, broker_account_id: str) -> StorageReadResult[BrokerAccountRecord]:
        ...

    def list_accounts(self) -> StorageListResult[BrokerAccountRecord]:
        ...

    def save_account(self, record: BrokerAccountRecord) -> StorageWriteResult:
        ...


@dataclass(frozen=True)
class PaperPortfolioSetupRecord:
    setup_id: str
    portfolio_name: str
    base_currency: str
    starting_cash_amount: Decimal
    paper_only: bool
    real_money_used: bool
    broker_order_created: bool
    live_trading_enabled: bool
    user_confirmed_paper_only: bool
    user_confirmed_no_real_money: bool
    user_confirmed_no_broker_order: bool
    status: str
    created_at: datetime
    updated_at: datetime | None
    explanation_nl: str


@dataclass(frozen=True)
class CreatePaperPortfolioSetupRequest:
    setup_id: str
    portfolio_name: str
    base_currency: str
    starting_cash_amount: Decimal
    status: str
    created_at: datetime
    explanation_nl: str


class PaperPortfolioSetupRepositoryProtocol(Protocol):
    def create_setup(
        self, request: CreatePaperPortfolioSetupRequest
    ) -> StorageWriteResult:
        ...

    def get_by_id(
        self, setup_id: str
    ) -> StorageReadResult[PaperPortfolioSetupRecord]:
        ...

    def get_latest(self) -> StorageReadResult[PaperPortfolioSetupRecord]:
        ...


class BrokerSyncRunRepository(Protocol):
    def get_by_id(self, broker_sync_run_id: str) -> StorageReadResult[BrokerSyncRunRecord]:
        ...

    def list_for_account(
        self,
        broker_account_id: str,
    ) -> StorageListResult[BrokerSyncRunRecord]:
        ...

    def save_sync_run(self, record: BrokerSyncRunRecord) -> StorageWriteResult:
        ...


class BrokerSnapshotRepository(Protocol):
    def list_position_snapshots(
        self,
        broker_sync_run_id: str,
    ) -> StorageListResult[BrokerPositionSnapshotRecord]:
        ...

    def list_cash_snapshots(
        self,
        broker_sync_run_id: str,
    ) -> StorageListResult[BrokerCashSnapshotRecord]:
        ...

    def list_execution_snapshots(
        self,
        broker_sync_run_id: str,
    ) -> StorageListResult[BrokerExecutionSnapshotRecord]:
        ...

    def list_commission_snapshots(
        self,
        broker_sync_run_id: str,
    ) -> StorageListResult[BrokerCommissionSnapshotRecord]:
        ...

    def save_position_snapshot(
        self,
        record: BrokerPositionSnapshotRecord,
    ) -> StorageWriteResult:
        ...

    def save_cash_snapshot(self, record: BrokerCashSnapshotRecord) -> StorageWriteResult:
        ...

    def save_execution_snapshot(
        self,
        record: BrokerExecutionSnapshotRecord,
    ) -> StorageWriteResult:
        ...

    def save_commission_snapshot(
        self,
        record: BrokerCommissionSnapshotRecord,
    ) -> StorageWriteResult:
        ...


class BrokerReconciliationRepository(Protocol):
    def get_report_by_id(
        self,
        broker_reconciliation_report_id: str,
    ) -> StorageReadResult[BrokerReconciliationReportRecord]:
        ...

    def list_reports_for_sync_run(
        self,
        broker_sync_run_id: str,
    ) -> StorageListResult[BrokerReconciliationReportRecord]:
        ...

    def list_differences_for_report(
        self,
        broker_reconciliation_report_id: str,
    ) -> StorageListResult[BrokerReconciliationDifferenceRecord]:
        ...

    def save_report(self, record: BrokerReconciliationReportRecord) -> StorageWriteResult:
        ...

    def save_difference(
        self,
        record: BrokerReconciliationDifferenceRecord,
    ) -> StorageWriteResult:
        ...


class ExternalBrokerActivityRepository(Protocol):
    def get_by_id(
        self,
        external_broker_activity_id: str,
    ) -> StorageReadResult[ExternalBrokerActivityRecord]:
        ...

    def list_for_account(
        self,
        broker_account_id: str,
    ) -> StorageListResult[ExternalBrokerActivityRecord]:
        ...

    def save_external_activity(
        self,
        record: ExternalBrokerActivityRecord,
    ) -> StorageWriteResult:
        ...


class BrokerStorageUnitOfWork(Protocol):
    @property
    def broker_accounts(self) -> BrokerAccountRepository:
        ...

    @property
    def broker_sync_runs(self) -> BrokerSyncRunRepository:
        ...

    @property
    def broker_snapshots(self) -> BrokerSnapshotRepository:
        ...

    @property
    def broker_reconciliation(self) -> BrokerReconciliationRepository:
        ...

    @property
    def external_broker_activities(self) -> ExternalBrokerActivityRepository:
        ...

    def health(self) -> RepositoryHealthStatus:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...


def build_repository_health_not_connected() -> RepositoryHealthStatus:
    return RepositoryHealthStatus(
        available=False,
        connected=False,
        migrations_current=False,
        read_only=True,
        explanation_nl="De repository-laag is gepland, maar nog niet verbonden met de database.",
    )


def repository_interfaces_are_defined() -> bool:
    _ = (
        BrokerAccountRepository,
        BrokerSyncRunRepository,
        BrokerSnapshotRepository,
        BrokerReconciliationRepository,
        ExternalBrokerActivityRepository,
        BrokerStorageUnitOfWork,
        BrokerAccountRecord,
        BrokerSyncRunRecord,
        BrokerPositionSnapshotRecord,
        BrokerCashSnapshotRecord,
        BrokerExecutionSnapshotRecord,
        BrokerCommissionSnapshotRecord,
        BrokerReconciliationReportRecord,
        BrokerReconciliationDifferenceRecord,
        ExternalBrokerActivityRecord,
        StorageWriteResult,
        StorageReadResult,
        StorageListResult,
        RepositoryHealthStatus,
    )
    return True
