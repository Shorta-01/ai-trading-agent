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


@dataclass(frozen=True)
class EvidenceItemRecord:
    evidence_id: str
    asset_symbol: str | None
    evidence_type: str
    evidence_direction: str
    title_nl: str
    summary_nl: str
    claim_nl: str
    source_credibility_level: str
    freshness_status: str | None
    prompt_injection_risk_level: str | None
    supports_buy: bool
    supports_hold: bool
    supports_sell: bool
    supports_avoid: bool
    blocks_action: bool
    confidence_score: Decimal | None
    observed_at: datetime | None
    created_at: datetime
    valid_until: datetime | None
    schema_version: str
    metadata_json: dict[str, str] | None
    explanation_nl: str


@dataclass(frozen=True)
class EvidenceSourceLinkRecord:
    link_id: str
    evidence_id: str
    source_id: str
    source_kind: str | None
    source_title: str | None
    source_reference_nl: str | None
    source_excerpt_nl: str | None
    source_url: str | None
    page_number: int | None
    section_label: str | None
    created_at: datetime


@dataclass(frozen=True)
class EventSignalRecord:
    event_signal_id: str
    event_type: str
    status: str
    title_nl: str
    summary_nl: str
    impact_direction: str
    impact_horizon: str
    confidence: str
    confidence_score: Decimal | None
    source_credibility_level: str
    prompt_injection_risk_level: str
    market_reaction_check_required: bool
    scenario_impact_id: str | None
    market_reaction_check_id: str | None
    extracted_at: datetime
    valid_until: datetime | None
    schema_version: str
    metadata_json: dict[str, str] | None
    explanation_nl: str


@dataclass(frozen=True)
class EventSignalSourceLinkRecord:
    link_id: str
    event_signal_id: str
    source_candidate_id: str | None
    source_id: str | None
    source_kind: str | None
    source_title: str | None
    source_url: str | None
    source_credibility_level: str | None
    novelty_level: str | None
    relevance_level: str | None
    created_at: datetime


@dataclass(frozen=True)
class EventSignalAssetLinkRecord:
    link_id: str
    event_signal_id: str
    entity_type: str
    entity_name: str
    asset_symbol: str | None
    conid: str | None
    isin: str | None
    sector: str | None
    region: str | None
    mapping_confidence: str
    direct_relevance: bool
    reason_nl: str
    created_at: datetime


@dataclass(frozen=True)
class ModelEvidenceLinkRecord:
    link_id: str
    evidence_id: str
    model_result_id: str
    model_run_id: str | None
    model_id: str | None
    model_version: str | None
    model_family: str | None
    link_reason_nl: str
    created_at: datetime


@dataclass(frozen=True)
class SuggestionEvidenceLinkRecord:
    link_id: str
    suggestion_id: str
    evidence_id: str | None
    event_signal_id: str | None
    model_result_id: str | None
    freshness_assessment_id: str | None
    source_conflict_id: str | None
    link_type: str
    supports_action: bool
    limits_action: bool
    blocks_action: bool
    reason_nl: str
    created_at: datetime


@dataclass(frozen=True)
class SourceConflictRecord:
    source_conflict_id: str
    asset_symbol: str | None
    conflict_type: str
    severity: str
    title_nl: str
    summary_nl: str
    source_ids_json: tuple[str, ...] | None
    evidence_ids_json: tuple[str, ...] | None
    event_signal_ids_json: tuple[str, ...] | None
    blocks_suggestions: bool
    requires_user_review: bool
    detected_at: datetime
    resolved_at: datetime | None
    resolution_nl: str | None
    explanation_nl: str


@dataclass(frozen=True)
class SystemEventRecord:
    system_event_id: str
    created_at: datetime
    severity: str
    category: str
    source_service: str
    source_component: str
    event_code: str
    title_nl: str
    message_nl: str
    help_nl: str
    technical_summary: str | None
    redacted_details_json: dict[str, str] | None
    stack_trace_redacted: str | None
    related_entity_type: str | None
    related_entity_id: str | None
    blocks_suggestions: bool
    blocks_writes: bool
    blocks_ai_explanation: bool
    status: str
    resolved_at: datetime | None
    archived_at: datetime | None
    copied_for_codex_at: datetime | None
    explanation_nl: str


@dataclass(frozen=True)
class CreateSystemEventRequest:
    system_event_id: str
    created_at: datetime
    severity: str
    category: str
    source_service: str
    source_component: str
    event_code: str
    title_nl: str
    message_nl: str
    help_nl: str
    technical_summary: str | None
    redacted_details_json: dict[str, str] | None
    stack_trace_redacted: str | None
    related_entity_type: str | None
    related_entity_id: str | None
    blocks_suggestions: bool
    blocks_writes: bool
    blocks_ai_explanation: bool
    status: str
    explanation_nl: str


class SystemEventRepositoryProtocol(Protocol):
    def create_event(self, request: CreateSystemEventRequest) -> StorageWriteResult:
        ...

    def get_by_id(self, system_event_id: str) -> StorageReadResult[SystemEventRecord]:
        ...

    def list_open_events(self) -> StorageListResult[SystemEventRecord]:
        ...

    def mark_resolved(
        self, system_event_id: str, *, reason_nl: str | None = None
    ) -> StorageWriteResult:
        ...

    def mark_archived(
        self, system_event_id: str, *, reason_nl: str | None = None
    ) -> StorageWriteResult:
        ...
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


@dataclass(frozen=True)
class TradingSettingsRecord:
    settings_id: str
    created_at: datetime
    updated_at: datetime
    version: int
    allowed_universe: dict[str, object]
    user_strategy: dict[str, object]
    source: str
    status: str
    explanation_nl: str


@dataclass(frozen=True)
class SaveTradingSettingsRequest:
    settings_id: str
    allowed_universe: dict[str, object]
    user_strategy: dict[str, object]
    source: str
    status: str
    explanation_nl: str
    updated_at: datetime


class TradingSettingsRepositoryProtocol(Protocol):
    def save_settings(self, request: SaveTradingSettingsRequest) -> StorageWriteResult:
        ...

    def get_settings(
        self, settings_id: str = "default"
    ) -> StorageReadResult[TradingSettingsRecord]:
        ...


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
        TradingSettingsRecord,
        SaveTradingSettingsRequest,
        TradingSettingsRepositoryProtocol,
    )
    return True
