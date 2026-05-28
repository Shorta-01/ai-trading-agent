"""Repository contracts for future broker sync and reconciliation persistence.

This module defines interface-only protocols and DTO/result contracts.
It intentionally does not open sessions, read environment variables, or connect to a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol


def _require_non_empty(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must be non-empty.")
    return value


def _require_positive_int(value: int | None, field_name: str) -> int | None:
    if value is not None and value <= 0:
        raise ValueError(f"{field_name} must be positive when provided.")
    return value


def _require_non_negative_int(value: int | None, field_name: str) -> int | None:
    if value is not None and value < 0:
        raise ValueError(f"{field_name} must be non-negative when provided.")
    return value


def _require_ordered_datetimes(
    earlier: datetime, later: datetime, earlier_name: str, later_name: str
) -> None:
    if later < earlier:
        raise ValueError(f"{later_name} must not be before {earlier_name}.")


def _normalize_value(value: str | None) -> str:
    return (value or "").strip().lower()


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


_LOCKED_IBKR_ACCOUNT_MODES = frozenset({"paper", "live", "unknown"})
_LOCKED_IBKR_CONNECTION_EVENT_TYPES = frozenset(
    {
        "connect_attempt",
        "connect_success",
        "connect_refused",
        "mode_check_prefix",
        "mode_check_behavioural",
        "disconnect",
        "session_error",
    }
)


@dataclass(frozen=True)
class IbkrSyncRunRecord:
    sync_run_id: str
    started_at: datetime
    completed_at: datetime | None
    provider_code: str
    provider_environment: str
    account_mode: str
    readonly: bool
    status: str
    account_summary_status: str
    positions_status: str
    open_orders_status: str
    executions_status: str
    positions_count: int
    cash_values_count: int
    open_orders_count: int
    executions_count: int
    status_nl: str | None
    next_step_nl: str | None
    help_nl: str | None
    actions_allowed: bool
    order_submission_allowed: bool
    order_modification_allowed: bool
    order_cancellation_allowed: bool
    suggestions_allowed: bool
    stored_at: datetime
    # Task 126: ibkr_account_id tagging. Nullable in 126a so existing
    # call sites stay valid; 126b's API rewrite populates it everywhere
    # and the column tightens to NOT NULL with a follow-up migration.
    ibkr_account_id: str | None = None
    verified_at: datetime | None = None


@dataclass(frozen=True)
class IbkrAccountCashSnapshotRecord:
    snapshot_id: str
    sync_run_id: str
    account_ref: str | None
    base_currency: str
    cash: Decimal | None
    available_funds: Decimal | None
    buying_power: Decimal | None
    received_at: datetime
    stored_at: datetime
    ibkr_account_id: str | None = None


@dataclass(frozen=True)
class IbkrNavSnapshotRecord:
    """One portfolio net-liquidation (NAV) point, for the drawdown gate.

    Persisted over time so the submission drawdown circuit-breaker can compute
    the decline-from-peak over a lookback window. Always carries the account id
    (unlike the cash-snapshot path) so the per-account NAV series is queryable.
    """

    snapshot_id: str
    ibkr_account_id: str
    base_currency: str
    nav_value: Decimal
    recorded_at: datetime
    stored_at: datetime


@dataclass(frozen=True)
class IbkrPositionSnapshotRecord:
    snapshot_id: str
    sync_run_id: str
    account_ref: str | None
    conid: str | None
    symbol: str
    security_type: str
    currency: str
    exchange: str | None
    primary_exchange: str | None
    quantity: Decimal
    average_cost: Decimal | None
    received_at: datetime
    stored_at: datetime
    ibkr_account_id: str | None = None


@dataclass(frozen=True)
class IbkrOpenOrderSnapshotRecord:
    snapshot_id: str
    sync_run_id: str
    account_ref: str | None
    ibkr_order_id: int
    ibkr_perm_id: int | None
    parent_order_id: int | None
    client_id: int | None
    symbol: str
    security_type: str
    currency: str
    exchange: str | None
    primary_exchange: str | None
    action_side: str
    order_type: str
    quantity: Decimal
    limit_price: Decimal | None
    stop_price: Decimal | None
    tif: str | None
    status: str
    filled_quantity: Decimal
    remaining_quantity: Decimal
    average_fill_price: Decimal | None
    last_status_at: datetime | None
    raw_status_reference: str | None
    received_at: datetime
    stored_at: datetime
    ibkr_account_id: str | None = None


@dataclass(frozen=True)
class IbkrExecutionSnapshotRecord:
    snapshot_id: str
    sync_run_id: str
    account_ref: str | None
    execution_id: str
    ibkr_order_id: int | None
    ibkr_perm_id: int | None
    symbol: str
    security_type: str
    currency: str
    exchange: str | None
    primary_exchange: str | None
    side: str
    quantity: Decimal
    price: Decimal
    execution_time: datetime
    commission: Decimal | None
    commission_currency: str | None
    realized_pnl: Decimal | None
    raw_execution_reference: str | None
    received_at: datetime
    stored_at: datetime
    ibkr_account_id: str | None = None


@dataclass(frozen=True)
class IbkrConnectionAuditRecord:
    """One audit row per IBKR connection lifecycle event.

    Task 126 product lock §2: both mode-detection checks (prefix and
    behavioural) write audit rows; connect_attempt / connect_success /
    connect_refused / disconnect / session_error round out the
    lifecycle. Append-only — never updated, never deleted. Safety
    booleans hard-False; an audit row never authorises an order.
    """

    audit_id: str
    event_at: datetime
    ibkr_account_id: str
    event_type: str
    account_mode_detected: str | None
    connection_id: str | None
    details_json: str | None

    def __post_init__(self) -> None:
        _require_non_empty(self.audit_id, "audit_id")
        _require_non_empty(self.ibkr_account_id, "ibkr_account_id")
        if self.event_type not in _LOCKED_IBKR_CONNECTION_EVENT_TYPES:
            raise ValueError(
                f"event_type {self.event_type!r} is not in the locked set "
                f"{sorted(_LOCKED_IBKR_CONNECTION_EVENT_TYPES)}"
            )
        if (
            self.account_mode_detected is not None
            and self.account_mode_detected not in _LOCKED_IBKR_ACCOUNT_MODES
        ):
            raise ValueError(
                f"account_mode_detected {self.account_mode_detected!r} is not in the "
                f"locked set {sorted(_LOCKED_IBKR_ACCOUNT_MODES)}"
            )


# Task 127: scheduler audit + state surface.
_LOCKED_SCHEDULED_RUN_TYPES = frozenset(
    {"pre_briefing", "morning_briefing", "hourly_delta"}
)
_LOCKED_SCHEDULED_MODE_DETECTED = frozenset(
    {
        "cold_start",
        "normal",
        "disconnected",
        "skipped_locked",
        "skipped_disabled",
        # Task 128: awaiting user confirmation of the starter
        # watchlist seed before normal advice runs resume.
        "awaiting_watchlist_confirmation",
    }
)
_LOCKED_SCHEDULED_OUTCOMES = frozenset({"completed", "error"})


@dataclass(frozen=True)
class ScheduledRunAuditEntry:
    """One row per APScheduler fire.

    Task 127 product lock §5: every scheduled run writes an
    append-only audit row capturing what mode the orchestrator
    detected, how long it took, and whether it completed cleanly.
    Used by the API to surface scheduler status to the dashboard.
    Safety booleans hard-False; an audit row never authorises an
    order.
    """

    run_id: str
    run_at: datetime
    run_type: str
    ibkr_account_id: str | None
    mode_detected: str
    duration_ms: int | None
    outcome: str
    error_details_json: str | None
    next_scheduled_at: datetime | None

    def __post_init__(self) -> None:
        _require_non_empty(self.run_id, "run_id")
        if self.run_type not in _LOCKED_SCHEDULED_RUN_TYPES:
            raise ValueError(
                f"run_type {self.run_type!r} is not in the locked set "
                f"{sorted(_LOCKED_SCHEDULED_RUN_TYPES)}"
            )
        if self.mode_detected not in _LOCKED_SCHEDULED_MODE_DETECTED:
            raise ValueError(
                f"mode_detected {self.mode_detected!r} is not in the locked set "
                f"{sorted(_LOCKED_SCHEDULED_MODE_DETECTED)}"
            )
        if self.outcome not in _LOCKED_SCHEDULED_OUTCOMES:
            raise ValueError(
                f"outcome {self.outcome!r} is not in the locked set "
                f"{sorted(_LOCKED_SCHEDULED_OUTCOMES)}"
            )
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")


@dataclass(frozen=True)
class SchedulerStateEntry:
    """One row per running worker process.

    The scheduler heartbeats this row every 60 seconds with the
    next scheduled fire times for the two cron jobs (pre-briefing
    + hourly). The API reads it to expose the dashboard badge's
    "Volgende run om HH:MM" text.
    """

    worker_id: str
    started_at: datetime
    last_heartbeat_at: datetime
    next_pre_briefing_at: datetime | None
    next_hourly_at: datetime | None

    def __post_init__(self) -> None:
        _require_non_empty(self.worker_id, "worker_id")


@dataclass(frozen=True)
class FxRateSnapshotRecord:
    snapshot_id: str
    provider: str
    source: str
    base_currency: str
    quote_currency: str
    pair: str
    rate: Decimal
    rate_type: str
    as_of: datetime
    received_at: datetime
    stored_at: datetime
    freshness_status: str
    validation_status: str
    reason_code: str
    metadata_json: dict[str, object] | None


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
class ResearchSourceRecord:
    library_source_id: str
    source_kind: str
    status: str
    classification_status: str
    extraction_status: str
    analysis_status: str
    asset_symbol: str | None
    asset_name: str | None
    title: str
    document_type: str
    source_type: str
    source_credibility_level: str | None
    prompt_injection_risk_level: str | None
    content_hash_sha256: str | None
    archive_storage_uri: str | None
    raw_source_available: bool
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    schema_version: str
    explanation_nl: str

    def __post_init__(self) -> None:
        for field_name in (
            "library_source_id", "source_kind", "status", "classification_status",
            "extraction_status", "analysis_status", "title", "document_type",
            "source_type", "schema_version", "explanation_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        _require_ordered_datetimes(self.created_at, self.updated_at, "created_at", "updated_at")
        if self.archived_at is not None:
            _require_ordered_datetimes(
                self.created_at, self.archived_at, "created_at", "archived_at"
            )


@dataclass(frozen=True)
class ResearchUploadedFileMetadataRecord:
    library_source_id: str
    original_file_name: str
    stored_file_name: str | None
    content_type: str | None
    file_size_bytes: int | None
    file_hash_sha256: str | None
    detected_language: str | None
    page_count: int | None
    uploaded_at: datetime
    uploaded_by_user: bool
    explanation_nl: str

    def __post_init__(self) -> None:
        _require_non_empty(self.library_source_id, "library_source_id")
        _require_non_empty(self.original_file_name, "original_file_name")
        _require_non_empty(self.explanation_nl, "explanation_nl")
        _require_positive_int(self.file_size_bytes, "file_size_bytes")
        _require_positive_int(self.page_count, "page_count")


@dataclass(frozen=True)
class ResearchUrlMetadataRecord:
    library_source_id: str
    url: str
    normalized_url: str | None
    domain: str | None
    fetched_at: datetime | None
    snapshot_hash_sha256: str | None
    snapshot_storage_uri: str | None
    http_status_code: int | None
    content_type: str | None
    user_supplied: bool
    explanation_nl: str

    def __post_init__(self) -> None:
        _require_non_empty(self.library_source_id, "library_source_id")
        _require_non_empty(self.url, "url")
        _require_non_empty(self.explanation_nl, "explanation_nl")
        if self.http_status_code is not None and not 100 <= self.http_status_code <= 599:
            raise ValueError("http_status_code must be between 100 and 599 when provided.")


@dataclass(frozen=True)
class ResearchUserNoteRecord:
    library_source_id: str
    asset_symbol: str | None
    title: str
    note_nl: str
    thesis_relevance_nl: str | None
    user_confidence_nl: str | None
    created_at: datetime
    updated_at: datetime
    explanation_nl: str

    def __post_init__(self) -> None:
        _require_non_empty(self.library_source_id, "library_source_id")
        _require_non_empty(self.title, "title")
        _require_non_empty(self.note_nl, "note_nl")
        _require_non_empty(self.explanation_nl, "explanation_nl")
        _require_ordered_datetimes(self.created_at, self.updated_at, "created_at", "updated_at")


@dataclass(frozen=True)
class ResearchDocumentSetRecord:
    document_set_id: str
    asset_symbol: str
    title: str
    set_type: str
    created_at: datetime
    explanation_nl: str

    def __post_init__(self) -> None:
        for field_name in (
            "document_set_id",
            "asset_symbol",
            "title",
            "set_type",
            "explanation_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)


@dataclass(frozen=True)
class ResearchDocumentSetMemberRecord:
    member_id: str
    document_set_id: str
    library_source_id: str
    fiscal_year: int | None
    reporting_period: str | None
    sort_order: int | None
    created_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty(self.member_id, "member_id")
        _require_non_empty(self.document_set_id, "document_set_id")
        _require_non_empty(self.library_source_id, "library_source_id")
        _require_non_negative_int(self.sort_order, "sort_order")
        if self.fiscal_year is not None and not 1900 <= self.fiscal_year <= 2200:
            raise ValueError("fiscal_year must be between 1900 and 2200 when provided.")


@dataclass(frozen=True)
class ResearchDocumentClassificationRecord:
    classification_id: str
    library_source_id: str
    document_type: str
    source_type: str
    confidence: str
    detected_asset_symbol: str | None
    detected_asset_name: str | None
    detected_fiscal_year: int | None
    detected_reporting_period: str | None
    detected_language: str | None
    needs_user_review: bool
    reason_nl: str
    classified_at: datetime
    schema_version: str

    def __post_init__(self) -> None:
        for field_name in (
            "classification_id", "library_source_id", "document_type", "source_type",
            "confidence", "reason_nl", "schema_version",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if (
            _normalize_value(self.confidence) in {"low", "unknown", "unclear"}
            and not self.needs_user_review
        ):
            raise ValueError("needs_user_review must be true for low-confidence classifications.")


@dataclass(frozen=True)
class ResearchSourceAssetLinkRecord:
    link_id: str
    library_source_id: str
    asset_symbol: str | None
    asset_name: str | None
    conid: str | None
    isin: str | None
    link_type: str
    mapping_confidence: str
    auto_linked: bool
    requires_user_confirmation: bool
    confirmed_by_user: bool
    reason_nl: str
    created_at: datetime
    confirmed_at: datetime | None

    def __post_init__(self) -> None:
        for field_name in (
            "link_id",
            "library_source_id",
            "link_type",
            "mapping_confidence",
            "reason_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.confirmed_at is not None:
            _require_ordered_datetimes(
                self.created_at, self.confirmed_at, "created_at", "confirmed_at"
            )
        if (
            _normalize_value(self.link_type) == "detected_new_asset"
            and not self.requires_user_confirmation
        ):
            raise ValueError(
                "requires_user_confirmation must be true for detected_new_asset links."
            )


@dataclass(frozen=True)
class ResearchSourceProcessingStatusRecord:
    processing_id: str
    library_source_id: str
    classification_status: str
    extraction_status: str
    analysis_status: str
    readiness_status: str
    can_be_used_in_research: bool
    can_be_used_in_suggestions: bool
    needs_user_review: bool
    blocks_suggestions: bool
    last_error_nl: str | None
    checked_at: datetime
    reason_nl: str

    def __post_init__(self) -> None:
        for field_name in (
            "processing_id", "library_source_id", "classification_status", "extraction_status",
            "analysis_status", "readiness_status", "reason_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        blocked = {"blocked", "failed", "rejected", "prompt_injection_blocked"}
        if self.blocks_suggestions and self.can_be_used_in_suggestions:
            raise ValueError(
                "can_be_used_in_suggestions must be false when blocks_suggestions is true."
            )
        if (
            _normalize_value(self.readiness_status) in blocked
            and self.can_be_used_in_suggestions
        ):
            raise ValueError(
                "can_be_used_in_suggestions must be false for blocked readiness_status values."
            )


@dataclass(frozen=True)
class ResearchSourcePromptInjectionScanRecord:
    scan_id: str
    library_source_id: str
    scan_status: str
    risk_level: str
    detected_signals_json: tuple[str, ...] | None
    safe_to_use_as_evidence: bool
    safe_to_use_as_instruction: bool
    blocks_suggestions: bool
    scanned_at: datetime
    checked_at: datetime
    explanation_nl: str

    def __post_init__(self) -> None:
        for field_name in ("scan_id", "library_source_id", "scan_status", "risk_level", "explanation_nl"):
            _require_non_empty(getattr(self, field_name), field_name)
        _require_ordered_datetimes(self.scanned_at, self.checked_at, "scanned_at", "checked_at")
        if self.blocks_suggestions and self.safe_to_use_as_instruction:
            raise ValueError("safe_to_use_as_instruction must be false when blocks_suggestions is true.")


@dataclass(frozen=True)
class ResearchSourceCredibilityAssessmentRecord:
    assessment_id: str
    library_source_id: str
    credibility_status: str
    credibility_level: str
    source_category: str
    assessed_at: datetime
    checked_at: datetime
    confidence_level: str
    credibility_signals_json: tuple[str, ...] | None
    limitation_notes_nl: str | None
    safe_to_use_as_evidence: bool
    safe_to_use_for_suggestions: bool
    blocks_suggestions: bool
    explanation_nl: str

    def __post_init__(self) -> None:
        for field_name in (
            "assessment_id", "library_source_id", "credibility_status", "credibility_level",
            "source_category", "confidence_level", "explanation_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        _require_ordered_datetimes(self.assessed_at, self.checked_at, "assessed_at", "checked_at")
        if self.safe_to_use_for_suggestions:
            raise ValueError("safe_to_use_for_suggestions must remain false in version 1 foundation.")
        if not self.blocks_suggestions:
            raise ValueError("blocks_suggestions must remain true in version 1 foundation.")


@dataclass(frozen=True)
class ResearchSourceEvidenceItemRecord:
    evidence_item_id: str
    library_source_id: str
    evidence_type: str
    evidence_status: str
    extracted_from_kind: str
    source_reference_text: str
    normalized_evidence_text: str
    evidence_summary_nl: str
    asset_symbol: str | None
    reporting_period: str | None
    fiscal_year: int | None
    confidence_level: str
    extraction_method: str
    source_text_hash_sha256: str | None
    extraction_run_id: str | None
    created_at: datetime
    extracted_at: datetime
    safe_to_use_as_evidence: bool
    safe_to_use_for_suggestions: bool
    blocks_suggestions: bool
    explanation_nl: str

    def __post_init__(self) -> None:
        for field_name in (
            "evidence_item_id",
            "library_source_id",
            "evidence_type",
            "evidence_status",
            "extracted_from_kind",
            "source_reference_text",
            "normalized_evidence_text",
            "evidence_summary_nl",
            "confidence_level",
            "extraction_method",
            "explanation_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        _require_ordered_datetimes(self.extracted_at, self.created_at, "extracted_at", "created_at")
        if self.safe_to_use_for_suggestions:
            raise ValueError("safe_to_use_for_suggestions must remain false in version 1 foundation.")
        if not self.blocks_suggestions:
            raise ValueError("blocks_suggestions must remain true in version 1 foundation.")


@dataclass(frozen=True)
class ResearchSourceEvidenceLedgerLinkRecord:
    link_id: str
    library_source_id: str
    evidence_item_id: str
    evidence_ledger_item_id: str
    link_type: str
    link_status: str
    created_at: datetime
    created_by_system: str
    lineage_scope: str
    source_snapshot_reference: str | None
    evidence_text_hash_sha256: str | None
    gate_context_status: str
    safe_to_use_for_suggestions: bool
    blocks_suggestions: bool
    explanation_nl: str

    def __post_init__(self) -> None:
        for field_name in (
            "link_id",
            "library_source_id",
            "evidence_item_id",
            "evidence_ledger_item_id",
            "link_type",
            "link_status",
            "created_by_system",
            "lineage_scope",
            "gate_context_status",
            "explanation_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.safe_to_use_for_suggestions:
            raise ValueError("safe_to_use_for_suggestions must remain false in version 1 foundation.")
        if not self.blocks_suggestions:
            raise ValueError("blocks_suggestions must remain true in version 1 foundation.")


@dataclass(frozen=True)
class ResearchGateOutcomeRecord:
    gate_outcome_id: str
    gate_name: str
    gate_version: str
    target_type: str
    target_id: str
    library_source_id: str | None
    evidence_item_id: str | None
    evidence_ledger_item_id: str | None
    outcome_status: str
    severity: str
    freshness_status: str
    checked_at: datetime
    valid_until: datetime | None
    expires_at: datetime | None
    source_timestamp: datetime | None
    data_age_seconds: int | None
    blocking_reason_code: str | None
    blocks_suggestions: bool
    safe_to_use_as_evidence: bool
    safe_to_use_for_suggestions: bool
    explanation_nl: str
    source_reference_ids_json: tuple[str, ...] | None
    audit_context_json: dict[str, str] | None

    def __post_init__(self) -> None:
        for field_name in (
            "gate_outcome_id",
            "gate_name",
            "gate_version",
            "target_type",
            "target_id",
            "outcome_status",
            "severity",
            "freshness_status",
            "explanation_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        _require_non_negative_int(self.data_age_seconds, "data_age_seconds")
        if self.safe_to_use_for_suggestions:
            raise ValueError("safe_to_use_for_suggestions must remain false in version 1 foundation.")
        if not self.blocks_suggestions and _normalize_value(self.outcome_status) not in {"passed", "warning"}:
            raise ValueError("Non-blocking gate outcomes are only allowed for informational statuses.")


@dataclass(frozen=True)
class ResearchSourceConflictFindingRecord:
    conflict_finding_id: str
    conflict_status: str
    conflict_type: str
    severity: str
    primary_source_id: str
    conflicting_source_id: str | None
    primary_evidence_item_id: str | None
    conflicting_evidence_item_id: str | None
    primary_evidence_ledger_item_id: str | None
    conflicting_evidence_ledger_item_id: str | None
    gate_outcome_id: str | None
    asset_symbol: str | None
    fiscal_year: int | None
    reporting_period: str | None
    detected_at: datetime
    checked_at: datetime
    conflict_summary_nl: str
    conflict_reason_nl: str
    source_reference_ids_json: tuple[str, ...] | None
    audit_context_json: dict[str, str] | None
    safe_to_use_as_evidence: bool
    safe_to_use_for_suggestions: bool
    blocks_suggestions: bool
    explanation_nl: str

    def __post_init__(self) -> None:
        for field_name in (
            "conflict_finding_id",
            "conflict_status",
            "conflict_type",
            "severity",
            "primary_source_id",
            "conflict_summary_nl",
            "conflict_reason_nl",
            "explanation_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.safe_to_use_for_suggestions:
            raise ValueError("safe_to_use_for_suggestions must remain false in version 1 foundation.")
        if not self.blocks_suggestions and _normalize_value(self.conflict_status) == "open":
            raise ValueError("Open conflicts must block suggestions in this foundation.")


@dataclass(frozen=True)
class SourceToAssetLinkRecord:
    link_id: str
    asset_id: str
    target_type: str
    target_id: str
    link_reason_nl: str
    audit_context_json: dict[str, str] | None
    safe_to_use_for_suggestions: bool
    blocks_suggestions: bool
    created_at: datetime
    created_by: str
    explanation_nl: str

    def __post_init__(self) -> None:
        for field_name in (
            "link_id", "asset_id", "target_type", "target_id", "link_reason_nl", "created_by", "explanation_nl"
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.safe_to_use_for_suggestions:
            raise ValueError("safe_to_use_for_suggestions must remain false in this foundation.")
        if not self.blocks_suggestions:
            raise ValueError("blocks_suggestions must remain true in this foundation.")


@dataclass(frozen=True)
class AssetMasterRecord:
    asset_id: str
    canonical_symbol: str
    asset_name: str
    asset_type: str
    primary_exchange: str | None
    primary_currency: str | None
    country: str | None
    isin: str | None
    figi: str | None
    cusip: str | None
    ibkr_contract_id: str | None
    sector: str | None
    industry: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    identity_confidence: str
    identity_source: str
    source_reference_ids_json: tuple[str, ...] | None
    audit_context_json: dict[str, str] | None
    safe_to_use_for_suggestions: bool
    blocks_suggestions: bool
    explanation_nl: str

    def __post_init__(self) -> None:
        for field_name in ("asset_id", "canonical_symbol", "asset_name", "asset_type", "status", "identity_confidence", "identity_source", "explanation_nl"):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.safe_to_use_for_suggestions:
            raise ValueError("safe_to_use_for_suggestions must remain false in this foundation.")
        if not self.blocks_suggestions:
            raise ValueError("blocks_suggestions must remain true in this foundation.")


@dataclass(frozen=True)
class AssetIdentifierAliasRecord:
    alias_id: str
    asset_id: str
    identifier_type: str
    identifier_value: str
    source: str
    confidence_level: str
    created_at: datetime
    explanation_nl: str

@dataclass(frozen=True)
class ResearchExtractedTextRecord:
    extracted_text_id: str
    library_source_id: str
    source_file_hash_sha256: str | None
    extraction_status: str
    extraction_method: str
    detected_content_type: str | None
    detected_language: str | None
    character_count: int | None
    line_count: int | None
    text_hash_sha256: str | None
    extracted_text_storage_uri: str | None
    preview_text_nl: str | None
    can_be_used_in_research: bool
    can_be_used_in_suggestions: bool
    needs_user_review: bool
    blocks_suggestions: bool
    created_at: datetime
    extracted_at: datetime | None
    schema_version: str
    reason_nl: str

    def __post_init__(self) -> None:
        for field_name in (
            "extracted_text_id",
            "library_source_id",
            "extraction_status",
            "extraction_method",
            "schema_version",
            "reason_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        _require_non_negative_int(self.character_count, "character_count")
        _require_non_negative_int(self.line_count, "line_count")
        if self.extracted_at is not None:
            _require_ordered_datetimes(
                self.created_at, self.extracted_at, "created_at", "extracted_at"
            )
        if self.blocks_suggestions and self.can_be_used_in_suggestions:
            raise ValueError(
                "can_be_used_in_suggestions must be false when blocks_suggestions is true."
            )
        if self.preview_text_nl is not None and len(self.preview_text_nl) > 1000:
            raise ValueError("preview_text_nl must be 1000 characters or less when provided.")


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
class AssetListingRecord:
    listing_id: str
    asset_id: str
    ibkr_conid: str | None
    symbol: str
    local_symbol: str | None
    trading_class: str | None
    security_type: str
    asset_class: str | None
    exchange: str | None
    primary_exchange: str | None
    currency: str
    listing_country: str | None
    listing_status: str
    validation_status: str
    validation_source: str | None
    validated_at: datetime | None
    identity_confidence: str
    identity_source: str
    created_at: datetime
    updated_at: datetime
    source_reference_ids_json: tuple[str, ...] | None
    audit_context_json: dict[str, str] | None
    safe_to_use_for_market_data: bool
    safe_to_use_for_analysis: bool
    safe_to_use_for_suggestions: bool
    blocks_market_data: bool
    blocks_analysis: bool
    blocks_suggestions: bool
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

    def delete_event(self, system_event_id: str) -> StorageWriteResult:
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


@dataclass(frozen=True)
class MarketDataSnapshotRecord:
    snapshot_id: str
    watchlist_item_id: str
    asset_id: str | None
    ibkr_conid: str
    symbol: str
    security_type: str
    exchange: str | None
    primary_exchange: str | None
    currency: str
    provider_name: str
    data_kind: str
    captured_at: datetime
    source_timestamp: datetime | None
    stored_at: datetime
    freshness_status: str
    validation_status: str
    blocked_reason: str | None
    raw_reference: str | None
    explanation_nl: str

    def __post_init__(self) -> None:
        for field_name in (
            "snapshot_id",
            "watchlist_item_id",
            "ibkr_conid",
            "symbol",
            "security_type",
            "currency",
            "provider_name",
            "data_kind",
            "freshness_status",
            "validation_status",
            "explanation_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)


@dataclass(frozen=True)
class MarketDataLatestSnapshotRecord:
    snapshot_id: str
    ibkr_conid: str
    symbol: str | None
    currency: str | None
    asset_class: str | None
    exchange: str | None
    primary_exchange: str | None
    provider_code: str | None
    provider_environment: str | None
    provider_account_mode: str | None
    market_data_type: str | None
    requested_at: datetime | None
    received_at: datetime | None
    provider_as_of: datetime | None
    stored_at: datetime
    last_price: Decimal | None
    bid_price: Decimal | None
    ask_price: Decimal | None
    close_price: Decimal | None
    day_change_percent: Decimal | None
    status: str
    freshness_status: str | None
    explanation_nl: str
    request_log_id: str | None
    provider_source_id: str | None
    freshness_audit_id: str | None
    safe_for_analysis: bool = False
    safe_for_suggestions: bool = False
    safe_for_action_drafts: bool = False

    def __post_init__(self) -> None:
        _require_non_empty(self.snapshot_id, "snapshot_id")
        _require_non_empty(self.ibkr_conid, "ibkr_conid")
        _require_non_empty(self.status, "status")
        _require_non_empty(self.explanation_nl, "explanation_nl")
        if self.safe_for_analysis or self.safe_for_suggestions or self.safe_for_action_drafts:
            raise ValueError("All safe_for_* fields must remain false in this non-runtime skeleton.")




@dataclass(frozen=True)
class RequestLogRecord:
    request_log_id: str
    correlation_id: str
    request_family: str
    request_purpose: str
    created_at: datetime
    completed_at: datetime | None
    provider_code: str
    provider_account_mode: str
    provider_environment: str
    source_type: str
    data_domain: str
    request_kind: str
    request_target: str
    request_status: str
    initiated_by: str
    pacing_weight: int | None
    provider_request_budget_remaining: int | None
    retry_count: int | None
    received_record_count: int | None
    stored_record_count: int | None
    rejected_record_count: int | None
    safe_for_analysis: bool = False
    safe_for_suggestions: bool = False
    safe_for_action_drafts: bool = False
    explanation_nl: str = "Read-only audit/status record."

    def __post_init__(self) -> None:
        for n in ("request_log_id","correlation_id","request_family","request_purpose","provider_code","provider_account_mode","provider_environment","source_type","data_domain","request_kind","request_target","request_status","initiated_by","explanation_nl"):
            _require_non_empty(getattr(self,n), n)
        if self.completed_at is not None:
            _require_ordered_datetimes(self.created_at, self.completed_at, "created_at", "completed_at")
        for n in ("pacing_weight","provider_request_budget_remaining","retry_count","received_record_count","stored_record_count","rejected_record_count"):
            _require_non_negative_int(getattr(self,n), n)
        if self.safe_for_analysis or self.safe_for_suggestions or self.safe_for_action_drafts:
            raise ValueError("All safe_for_* fields must remain false in this non-runtime skeleton.")


@dataclass(frozen=True)
class ProviderSourceRecord:
    provider_source_id: str
    provider_code: str
    provider_kind: str
    data_domain: str
    source_type: str
    provider_environment: str
    provider_account_mode: str
    source_effective_from: datetime | None
    source_effective_to: datetime | None
    created_at: datetime
    updated_at: datetime
    explanation_nl: str

    def __post_init__(self) -> None:
        for n in ("provider_source_id","provider_code","provider_kind","data_domain","source_type","provider_environment","provider_account_mode","explanation_nl"):
            _require_non_empty(getattr(self,n), n)
        _require_ordered_datetimes(self.created_at, self.updated_at, "created_at", "updated_at")
        if self.source_effective_from and self.source_effective_to:
            _require_ordered_datetimes(self.source_effective_from, self.source_effective_to, "source_effective_from", "source_effective_to")


@dataclass(frozen=True)
class FreshnessAuditRecord:
    freshness_audit_id: str
    evaluated_at: datetime
    data_domain: str
    freshness_policy_code: str
    freshness_status: str
    snapshot_as_of: datetime | None
    stale_after: datetime | None
    expires_at: datetime | None
    age_seconds: int | None
    freshness_window_seconds: int | None
    safe_for_analysis: bool = False
    safe_for_suggestions: bool = False
    safe_for_action_drafts: bool = False
    explanation_nl: str = "Read-only audit/status record."

    def __post_init__(self) -> None:
        for n in ("freshness_audit_id","data_domain","freshness_policy_code","freshness_status","explanation_nl"):
            _require_non_empty(getattr(self,n), n)
        _require_non_negative_int(self.age_seconds, "age_seconds")
        _require_non_negative_int(self.freshness_window_seconds, "freshness_window_seconds")
        if self.snapshot_as_of and self.stale_after:
            _require_ordered_datetimes(self.snapshot_as_of, self.stale_after, "snapshot_as_of", "stale_after")
        if self.stale_after and self.expires_at:
            _require_ordered_datetimes(self.stale_after, self.expires_at, "stale_after", "expires_at")
        if self.safe_for_analysis or self.safe_for_suggestions or self.safe_for_action_drafts:
            raise ValueError("All safe_for_* fields must remain false in this non-runtime skeleton.")


class RequestAuditRepository(Protocol):
    def save_request_log(self, record: RequestLogRecord) -> StorageWriteResult: ...
    def get_request_log(self, request_log_id: str) -> StorageReadResult[RequestLogRecord]: ...
    def list_request_logs(self, limit: int = 100) -> StorageListResult[RequestLogRecord]: ...
    def save_provider_source(self, record: ProviderSourceRecord) -> StorageWriteResult: ...
    def get_provider_source(self, provider_source_id: str) -> StorageReadResult[ProviderSourceRecord]: ...
    def list_provider_sources(self, limit: int = 100) -> StorageListResult[ProviderSourceRecord]: ...
    def save_freshness_audit(self, record: FreshnessAuditRecord) -> StorageWriteResult: ...
    def get_freshness_audit(self, freshness_audit_id: str) -> StorageReadResult[FreshnessAuditRecord]: ...
    def list_freshness_audits(self, limit: int = 100) -> StorageListResult[FreshnessAuditRecord]: ...

class MarketDataSnapshotRepository(Protocol):
    def save_latest_market_data_snapshot(
        self, record: MarketDataLatestSnapshotRecord
    ) -> StorageWriteResult: ...
    def get_latest_market_data_snapshot_by_conid(
        self, ibkr_conid: str
    ) -> StorageReadResult[MarketDataLatestSnapshotRecord]: ...
    def list_latest_market_data_snapshots_by_conids(
        self, conids: tuple[str, ...]
    ) -> StorageListResult[MarketDataLatestSnapshotRecord]: ...
    def get_latest_by_ibkr_conid(
        self,
        ibkr_conid: str,
    ) -> StorageReadResult[MarketDataSnapshotRecord]:
        ...

    def list_by_ibkr_conid(
        self,
        ibkr_conid: str,
    ) -> StorageListResult[MarketDataSnapshotRecord]:
        ...

    def list_by_watchlist_item(
        self,
        watchlist_item_id: str,
    ) -> StorageListResult[MarketDataSnapshotRecord]:
        ...


class FxRateSnapshotRepository(Protocol):
    def save_fx_rate_snapshot(self, record: FxRateSnapshotRecord) -> None: ...
    def get_fx_rate_snapshot(self, snapshot_id: str) -> FxRateSnapshotRecord | None: ...
    def list_fx_rate_snapshots(self, limit: int = 100) -> list[FxRateSnapshotRecord]: ...
    def get_latest_fx_rate_snapshot(
        self, base_currency: str, quote_currency: str
    ) -> FxRateSnapshotRecord | None: ...
    def list_latest_fx_rate_snapshots_by_pairs(
        self, pairs: tuple[str, ...]
    ) -> list[FxRateSnapshotRecord]: ...


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
        MarketDataSnapshotRepository,
        FxRateSnapshotRepository,
        BrokerReconciliationRepository,
        ExternalBrokerActivityRepository,
        BrokerStorageUnitOfWork,
        BrokerAccountRecord,
        BrokerSyncRunRecord,
        BrokerPositionSnapshotRecord,
        BrokerCashSnapshotRecord,
        BrokerExecutionSnapshotRecord,
        BrokerCommissionSnapshotRecord,
        MarketDataSnapshotRecord,
        FxRateSnapshotRecord,
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
        ResearchSourceRecord,
        ResearchUploadedFileMetadataRecord,
        ResearchUrlMetadataRecord,
        ResearchUserNoteRecord,
        ResearchDocumentSetRecord,
        ResearchDocumentSetMemberRecord,
        ResearchDocumentClassificationRecord,
        ResearchSourceAssetLinkRecord,
        ResearchSourceProcessingStatusRecord,
    )
    return True


@dataclass(frozen=True)
class MarketDataBarRecord:
    bar_id: str
    ibkr_conid: str
    symbol: str
    currency: str
    exchange: str | None
    primary_exchange: str | None
    provider_code: str
    bar_date: date
    interval_code: str
    open_price: Decimal | None
    high_price: Decimal | None
    low_price: Decimal | None
    close_price: Decimal
    adjusted_close_price: Decimal | None
    volume: Decimal | None
    provider_as_of: datetime | None
    received_at: datetime
    stored_at: datetime
    source_type: str
    explanation_nl: str

    def __post_init__(self) -> None:
        for field_name in (
            "bar_id",
            "ibkr_conid",
            "symbol",
            "currency",
            "provider_code",
            "interval_code",
            "source_type",
            "explanation_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)


@dataclass(frozen=True)
class AssetForecastRecord:
    forecast_id: str
    ibkr_conid: str
    symbol: str
    currency: str
    model_code: str
    model_version: str
    horizon_days: int
    generated_at: datetime
    valid_until: datetime
    data_points_used: int
    history_first_bar_date: date | None
    history_last_bar_date: date | None
    current_price: Decimal
    expected_return_pct: Decimal
    p10_price: Decimal
    p50_price: Decimal
    p90_price: Decimal
    prob_gain: Decimal
    prob_loss: Decimal
    prob_loss_gt_5pct: Decimal
    prob_loss_gt_10pct: Decimal
    prob_gain_gt_5pct: Decimal
    prob_gain_gt_10pct: Decimal
    expected_volatility_annual: Decimal
    downside_risk_score: Decimal
    confidence_score: Decimal
    direction_label: str
    direction_label_nl: str
    explanation_nl: str
    status: str
    blocking_reason: str | None
    safe_for_analysis: bool = False
    safe_for_suggestions: bool = False
    safe_for_action_drafts: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "forecast_id",
            "ibkr_conid",
            "symbol",
            "currency",
            "model_code",
            "model_version",
            "direction_label",
            "direction_label_nl",
            "explanation_nl",
            "status",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.horizon_days <= 0:
            raise ValueError("horizon_days must be positive")
        if self.data_points_used < 0:
            raise ValueError("data_points_used must be non-negative")
        if self.safe_for_analysis or self.safe_for_suggestions or self.safe_for_action_drafts:
            raise ValueError(
                "All safe_for_* fields must remain false for V1 baseline forecasts."
            )


@dataclass(frozen=True)
class AssetSuggestionRecord:
    suggestion_id: str
    ibkr_conid: str
    symbol: str
    currency: str
    forecast_id: str | None
    model_code: str
    model_version: str
    generated_at: datetime
    valid_until: datetime
    risk_profile: str
    has_position: bool
    action_label: str
    action_label_nl: str
    confidence_label: str
    confidence_label_nl: str
    confidence_score: Decimal
    rationale_nl: str
    drivers_json: tuple[str, ...] | None
    blockers_json: tuple[str, ...] | None
    status: str
    blocking_reason: str | None
    safe_for_action_drafts: bool = False
    safe_for_orders: bool = False
    safe_for_broker_submission: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "suggestion_id",
            "ibkr_conid",
            "symbol",
            "currency",
            "model_code",
            "model_version",
            "risk_profile",
            "action_label",
            "action_label_nl",
            "confidence_label",
            "confidence_label_nl",
            "rationale_nl",
            "status",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if (
            self.safe_for_action_drafts
            or self.safe_for_orders
            or self.safe_for_broker_submission
        ):
            raise ValueError(
                "Suggestion safety booleans must remain false in V1: suggestions "
                "are never auto-promoted to action drafts or orders."
            )


@dataclass(frozen=True)
class AssetDecisionPackageRecord:
    """Immutable, content-hashed bundle of the evidence that backs one
    suggestion at one point in time.

    The doctrine in ``release-1-functional-workflow-blueprint.md §6`` requires
    a Decision Package before any suggestion may produce an action draft. V1
    Slice 5 persists the parts of the evidence chain that are currently
    grounded (position, cash, market-data, FX, baseline forecast, label
    translator output); research evidence and AI signals fold in once those
    runtimes exist (later slices).

    ``content_hash`` is a SHA-256 of the canonical JSON of the bundle's
    audit-relevant fields; once written, never updated.
    """

    decision_package_id: str
    content_hash: str
    ibkr_conid: str
    symbol: str
    currency: str
    risk_profile: str
    generated_at: datetime
    valid_until: datetime
    # Position evidence (held-position snapshot)
    position_snapshot_id: str | None
    position_quantity: Decimal | None
    position_average_cost: Decimal | None
    # Cash evidence (account-level cash from latest IBKR sync)
    cash_snapshot_id: str | None
    cash_base_currency: str | None
    cash_amount: Decimal | None
    # Market-data evidence
    market_snapshot_id: str | None
    market_last_price: Decimal | None
    market_freshness_status: str | None
    market_provider_code: str | None
    market_provider_as_of: datetime | None
    # FX evidence (only when position currency != base currency)
    fx_pair: str | None
    fx_rate: Decimal | None
    fx_freshness_status: str | None
    # Forecast evidence (denormalised so the package is self-contained)
    forecast_id: str | None
    forecast_model_code: str | None
    forecast_model_version: str | None
    forecast_horizon_days: int | None
    forecast_p10_price: Decimal | None
    forecast_p50_price: Decimal | None
    forecast_p90_price: Decimal | None
    forecast_prob_gain: Decimal | None
    forecast_prob_loss: Decimal | None
    forecast_expected_return_pct: Decimal | None
    forecast_expected_volatility_annual: Decimal | None
    forecast_downside_risk_score: Decimal | None
    forecast_confidence_score: Decimal | None
    # Suggestion (locked-label translator output)
    suggestion_id: str | None
    suggestion_model_code: str | None
    suggestion_action_label: str
    suggestion_action_label_nl: str
    suggestion_confidence_label: str
    suggestion_confidence_label_nl: str
    suggestion_status: str
    has_position: bool
    # Gate / evidence / audit links
    gate_outcomes_json: tuple[str, ...] | None
    evidence_links_json: tuple[str, ...] | None
    audit_links_json: tuple[str, ...] | None
    # Dutch text
    rationale_nl: str
    explanation_nl: str
    # Status
    status: str
    blocking_reason: str | None
    # Safety booleans (must remain False)
    safe_for_action_drafts: bool = False
    safe_for_orders: bool = False
    safe_for_broker_submission: bool = False
    # Research evidence summary (Slice 9). Surfaced as read-only context;
    # research evidence never lifts a block — see
    # ``ResearchSourceEvidenceItemRecord`` for the underlying invariants.
    research_evidence_count: int = 0
    research_credibility_summary: str | None = None
    research_freshness_status: str | None = None
    research_blocking_reason: str | None = None
    research_snippet_nl: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "decision_package_id",
            "content_hash",
            "ibkr_conid",
            "symbol",
            "currency",
            "risk_profile",
            "suggestion_action_label",
            "suggestion_action_label_nl",
            "suggestion_confidence_label",
            "suggestion_confidence_label_nl",
            "suggestion_status",
            "rationale_nl",
            "explanation_nl",
            "status",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if (
            self.safe_for_action_drafts
            or self.safe_for_orders
            or self.safe_for_broker_submission
        ):
            raise ValueError(
                "Decision Package safety booleans must remain false: a "
                "package never auto-promotes to an action draft, order, or "
                "broker submission."
            )
        if self.research_evidence_count < 0:
            raise ValueError("research_evidence_count must be non-negative.")


@dataclass(frozen=True)
class AssetActionDraftRecord:
    """Editable structured action-draft derived from a ready Decision Package.

    V1 scope (locked in `version-1-product-experience-locks.md §10` plus
    the §21.3 order-vocabulary expansion):

    * stocks/ETFs only, whole shares only
    * ``order_type`` ∈ ``{LMT, MKT, STP, STP_LMT, TRAIL, TRAIL_LMT, BRACKET}``
    * ``tif == "DAY"`` only
    * ``action_side`` is ``"BUY"`` or ``"SELL"``

    Per-type required fields:

    * **LMT** — ``limit_price > 0``
    * **MKT** — no extra price fields
    * **STP** — ``stop_price > 0``
    * **STP_LMT** — both ``stop_price > 0`` and ``limit_price > 0``
    * **TRAIL** — exactly one of ``trail_amount > 0`` / ``trail_percent > 0``
    * **TRAIL_LMT** — TRAIL fields + ``limit_price > 0``
    * **BRACKET** — ``limit_price > 0`` + ``bracket_take_profit_limit_price > 0``
      + ``bracket_stop_loss_price > 0``

    A draft never auto-promotes to broker submission. The persisted record
    carries the dry-run outcome + the Orderimpact preview; the actual
    user-approval + submission lives in later slices.
    """

    draft_id: str
    decision_package_id: str
    decision_package_content_hash: str
    ibkr_conid: str
    symbol: str
    currency: str
    exchange: str | None
    primary_exchange: str | None
    account_mode: str
    expected_account_mode: str
    action_side: str
    order_type: str
    tif: str
    quantity: Decimal
    limit_price: Decimal
    estimated_order_value: Decimal | None
    estimated_cash_before: Decimal | None
    estimated_cash_after: Decimal | None
    estimated_position_quantity_before: Decimal | None
    estimated_position_quantity_after: Decimal | None
    estimated_position_value_after: Decimal | None
    estimated_portfolio_weight_after_pct: Decimal | None
    estimated_concentration_impact_pct: Decimal | None
    orderimpact_base_currency: str | None
    source_action_label: str
    source_action_label_nl: str
    status: str
    dry_run_status: str
    dry_run_failures_json: tuple[str, ...] | None
    blocking_reason: str | None
    rationale_nl: str
    explanation_nl: str
    created_at: datetime
    updated_at: datetime
    safe_for_submission: bool = False
    safe_for_orders: bool = False
    safe_for_broker_submission: bool = False
    # Belgian tax preview (Slice 11). Informational on the draft; the TOB
    # does not change order sizing. ``None`` means the value was not
    # computed (older drafts).
    estimated_belgian_tob: Decimal | None = None
    belgian_tob_security_class: str | None = None
    # Order-vocabulary expansion (Slice 20 / §21.3). Each field is only
    # required for the order types listed in the class docstring; the
    # other types must leave them ``None``.
    stop_price: Decimal | None = None
    trail_amount: Decimal | None = None
    trail_percent: Decimal | None = None
    bracket_take_profit_limit_price: Decimal | None = None
    bracket_stop_loss_price: Decimal | None = None
    # V1.1 §22.3: when order_type=CONDITIONAL, the parent order type
    # that fires after every activation condition is met. The
    # condition rows live in a child table
    # (`action_draft_order_conditions`) keyed on `(draft_id,
    # condition_index)`.
    conditional_parent_order_type: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "draft_id",
            "decision_package_id",
            "decision_package_content_hash",
            "ibkr_conid",
            "symbol",
            "currency",
            "account_mode",
            "expected_account_mode",
            "action_side",
            "order_type",
            "tif",
            "source_action_label",
            "source_action_label_nl",
            "status",
            "dry_run_status",
            "rationale_nl",
            "explanation_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.action_side not in {"BUY", "SELL"}:
            raise ValueError(
                f"action_side must be BUY or SELL, got {self.action_side!r}"
            )
        if self.order_type not in LOCKED_ORDER_TYPES:
            raise ValueError(
                f"order_type must be one of {sorted(LOCKED_ORDER_TYPES)}, "
                f"got {self.order_type!r}"
            )
        if self.tif not in LOCKED_TIF_SET:
            raise ValueError(
                f"tif must be one of {sorted(LOCKED_TIF_SET)}, got {self.tif!r}"
            )
        if self.quantity <= 0:
            raise ValueError("quantity must be positive.")
        _enforce_order_type_invariants(self)
        if (
            self.safe_for_submission
            or self.safe_for_orders
            or self.safe_for_broker_submission
        ):
            raise ValueError(
                "Action-draft safety booleans must remain false in V1: a "
                "draft never auto-promotes to a broker submission."
            )
        if self.estimated_belgian_tob is not None and self.estimated_belgian_tob < 0:
            raise ValueError("estimated_belgian_tob must not be negative.")
        for price_field in (
            "stop_price",
            "trail_amount",
            "trail_percent",
            "bracket_take_profit_limit_price",
            "bracket_stop_loss_price",
        ):
            value = getattr(self, price_field)
            if value is not None and value <= 0:
                raise ValueError(f"{price_field} must be positive when provided.")


LOCKED_ORDER_TYPES: frozenset[str] = frozenset(
    {"LMT", "MKT", "STP", "STP_LMT", "TRAIL", "TRAIL_LMT", "BRACKET", "CONDITIONAL"}
)

# V1.1 §22.3 — TIF set extended from V1 DAY-only.
LOCKED_TIF_SET: frozenset[str] = frozenset({"DAY", "GTC", "OPG", "IOC"})

# V1.1 §22.3 — order-condition kinds.
LOCKED_CONDITION_KINDS: frozenset[str] = frozenset(
    {"price", "time", "margin", "volume", "execution"}
)
LOCKED_CONDITION_COMPARATORS: frozenset[str] = frozenset({">=", "<=", "=="})
LOCKED_CONDITION_CONJUNCTIONS: frozenset[str] = frozenset({"and", "or"})

# V1.1 §22.3 — CONDITIONAL parent base types (the underlying order
# type that fires once the conditions are met).
LOCKED_CONDITIONAL_PARENT_TYPES: frozenset[str] = frozenset(
    {"LMT", "MKT", "STP", "STP_LMT"}
)


def _enforce_order_type_invariants(record: AssetActionDraftRecord) -> None:
    """Per-type field requirements for :class:`AssetActionDraftRecord`."""

    order_type = record.order_type
    if order_type == "LMT":
        if record.limit_price <= 0:
            raise ValueError("LMT order_type requires limit_price > 0.")
        return
    if order_type == "MKT":
        # MKT carries no price; ``limit_price`` is still required to
        # exist on the dataclass but we allow 0 here. The dataclass
        # type insists on Decimal — Decimal("0") is fine.
        return
    if order_type == "STP":
        if record.stop_price is None or record.stop_price <= 0:
            raise ValueError("STP order_type requires stop_price > 0.")
        return
    if order_type == "STP_LMT":
        if record.stop_price is None or record.stop_price <= 0:
            raise ValueError("STP_LMT order_type requires stop_price > 0.")
        if record.limit_price <= 0:
            raise ValueError("STP_LMT order_type requires limit_price > 0.")
        return
    if order_type in {"TRAIL", "TRAIL_LMT"}:
        has_amount = record.trail_amount is not None and record.trail_amount > 0
        has_percent = record.trail_percent is not None and record.trail_percent > 0
        if has_amount == has_percent:
            raise ValueError(
                f"{order_type} order_type requires exactly one of "
                "trail_amount or trail_percent (not both, not neither)."
            )
        if order_type == "TRAIL_LMT" and record.limit_price <= 0:
            raise ValueError("TRAIL_LMT order_type requires limit_price > 0.")
        return
    if order_type == "BRACKET":
        if record.limit_price <= 0:
            raise ValueError("BRACKET order_type requires limit_price > 0.")
        if (
            record.bracket_take_profit_limit_price is None
            or record.bracket_take_profit_limit_price <= 0
        ):
            raise ValueError(
                "BRACKET order_type requires bracket_take_profit_limit_price > 0."
            )
        if (
            record.bracket_stop_loss_price is None
            or record.bracket_stop_loss_price <= 0
        ):
            raise ValueError(
                "BRACKET order_type requires bracket_stop_loss_price > 0."
            )
        if record.action_side == "BUY":
            if record.bracket_take_profit_limit_price <= record.limit_price:
                raise ValueError(
                    "BRACKET BUY requires take-profit price > limit_price."
                )
            if record.bracket_stop_loss_price >= record.limit_price:
                raise ValueError(
                    "BRACKET BUY requires stop-loss price < limit_price."
                )
        else:  # SELL
            if record.bracket_take_profit_limit_price >= record.limit_price:
                raise ValueError(
                    "BRACKET SELL requires take-profit price < limit_price."
                )
            if record.bracket_stop_loss_price <= record.limit_price:
                raise ValueError(
                    "BRACKET SELL requires stop-loss price > limit_price."
                )
        return
    if order_type == "CONDITIONAL":
        parent = record.conditional_parent_order_type
        if parent is None or parent not in LOCKED_CONDITIONAL_PARENT_TYPES:
            raise ValueError(
                "CONDITIONAL order_type requires "
                f"conditional_parent_order_type ∈ "
                f"{sorted(LOCKED_CONDITIONAL_PARENT_TYPES)}, got {parent!r}."
            )
        # Per-parent-type price requirements mirror the standalone
        # equivalents — the conditions list lives in a child table so
        # the dataclass invariant can't check it (the dry-run does).
        if parent == "LMT" and record.limit_price <= 0:
            raise ValueError(
                "CONDITIONAL with parent LMT requires limit_price > 0."
            )
        if parent == "STP" and (
            record.stop_price is None or record.stop_price <= 0
        ):
            raise ValueError(
                "CONDITIONAL with parent STP requires stop_price > 0."
            )
        if parent == "STP_LMT":
            if record.stop_price is None or record.stop_price <= 0:
                raise ValueError(
                    "CONDITIONAL with parent STP_LMT requires stop_price > 0."
                )
            if record.limit_price <= 0:
                raise ValueError(
                    "CONDITIONAL with parent STP_LMT requires limit_price > 0."
                )
        return


@dataclass(frozen=True)
class ActionDraftOrderConditionRecord:
    """V1.1 §22.3 — one activation condition row for a CONDITIONAL
    action draft.

    The five locked condition kinds (``price`` / ``time`` /
    ``margin`` / ``volume`` / ``execution``) share one record shape
    with nullable kind-specific fields so the storage chain stays
    single-table. The dry-run safety pass enforces per-kind required
    fields; this dataclass enforces structural integrity (non-empty
    IDs + locked kind/comparator/conjunction sets + hard-False
    safety booleans).
    """

    condition_id: str
    draft_id: str
    condition_index: int
    condition_kind: str
    comparator: str
    conjunction: str  # ``and`` / ``or`` — joins this condition with the next
    trigger_symbol: str | None
    trigger_conid: str | None
    trigger_exchange: str | None
    trigger_price: Decimal | None
    trigger_at_utc: datetime | None
    margin_percent: Decimal | None
    trigger_volume: int | None
    execution_symbol: str | None
    execution_sec_type: str | None
    execution_exchange: str | None
    created_at: datetime
    safe_for_action_drafts: bool = False
    safe_for_orders: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "condition_id",
            "draft_id",
            "condition_kind",
            "comparator",
            "conjunction",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.condition_kind not in LOCKED_CONDITION_KINDS:
            raise ValueError(
                f"condition_kind must be one of {sorted(LOCKED_CONDITION_KINDS)}, "
                f"got {self.condition_kind!r}"
            )
        if self.comparator not in LOCKED_CONDITION_COMPARATORS:
            raise ValueError(
                f"comparator must be one of "
                f"{sorted(LOCKED_CONDITION_COMPARATORS)}, got {self.comparator!r}"
            )
        if self.conjunction not in LOCKED_CONDITION_CONJUNCTIONS:
            raise ValueError(
                f"conjunction must be one of "
                f"{sorted(LOCKED_CONDITION_CONJUNCTIONS)}, got {self.conjunction!r}"
            )
        if self.condition_index < 0:
            raise ValueError("condition_index must be non-negative")
        if self.trigger_volume is not None and self.trigger_volume < 0:
            raise ValueError("trigger_volume must be non-negative when provided")
        if self.margin_percent is not None and not (
            Decimal("0") <= self.margin_percent <= Decimal("100")
        ):
            raise ValueError(
                "margin_percent must be in [0, 100] when provided"
            )
        if self.safe_for_action_drafts or self.safe_for_orders:
            raise ValueError(
                "Action-draft-condition safety booleans must remain false in V1.1."
            )


@dataclass(frozen=True)
class AssetActionDraftSubmissionRecord:
    """1:1 submission record for an :class:`AssetActionDraftRecord`.

    Tracks the locked state machine
    (``draft → safety_checked → user_approved → submitted →
    awaiting_ibkr_reply → reply_confirmed → working → filled/cancelled/
    rejected → reconciled``) and the IBKR-side ids returned by
    ``placeOrder``.

    Safety booleans must remain ``False`` in V1 — the doctrine forbids
    auto-promotion of a submission to a "safe for orders" record.
    """

    submission_id: str
    draft_id: str
    state: str
    approval_status: str
    approved_at: datetime | None
    approved_by: str | None
    approval_dry_run_status: str | None
    approval_dry_run_failures_json: tuple[str, ...] | None
    submitted_at: datetime | None
    ibkr_order_id: int | None
    ibkr_perm_id: int | None
    ibkr_client_id: int | None
    ibkr_status_text: str | None
    filled_quantity: Decimal | None
    remaining_quantity: Decimal | None
    average_fill_price: Decimal | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    rejected_reason: str | None
    reconciled_at: datetime | None
    account_mode: str
    expected_account_mode: str
    provider_code: str
    created_at: datetime
    updated_at: datetime
    last_state_transition_at: datetime
    safe_for_broker_submission: bool = False
    safe_for_orders: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "submission_id",
            "draft_id",
            "state",
            "approval_status",
            "account_mode",
            "expected_account_mode",
            "provider_code",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.safe_for_broker_submission or self.safe_for_orders:
            raise ValueError(
                "Submission safety booleans must remain false in V1."
            )


@dataclass(frozen=True)
class AssetActionDraftEventRecord:
    """Append-only audit log entry for a draft / submission state change."""

    event_id: str
    draft_id: str
    submission_id: str | None
    event_type: str
    severity: str
    from_state: str | None
    to_state: str | None
    occurred_at: datetime
    acknowledged_at: datetime | None
    rationale_nl: str
    details_json: dict[str, str] | None

    def __post_init__(self) -> None:
        for field_name in ("event_id", "draft_id", "event_type", "severity", "rationale_nl"):
            _require_non_empty(getattr(self, field_name), field_name)


@dataclass(frozen=True)
class PredictionDiaryEntryRecord:
    """One Prediction Diary entry per suggestion.

    Captures the *issued* forecast and the *realised* market outcome at
    fixed horizons (1d/1w/1m). The outcome labels are computed by a pure-
    Python rule engine (``packages/portfolio/prediction_diary_eval``);
    AI never assigns the label.

    Safety booleans stay ``False`` in V1 — the doctrine forbids silent
    self-learning. Future model retraining flows must opt in explicitly
    and are out of scope for V1.
    """

    entry_id: str
    suggestion_id: str
    forecast_id: str | None
    ibkr_conid: str
    symbol: str
    currency: str
    issued_at: datetime
    issued_action_label: str
    issued_action_label_nl: str
    issued_confidence_label: str
    issued_horizon_days: int
    issued_price: Decimal
    issued_p10_price: Decimal
    issued_p50_price: Decimal
    issued_p90_price: Decimal
    issued_prob_gain: Decimal
    issued_prob_loss: Decimal
    user_decision: str | None
    realized_price_1d: Decimal | None
    realized_price_1w: Decimal | None
    realized_price_1m: Decimal | None
    realized_return_pct_1d: Decimal | None
    realized_return_pct_1w: Decimal | None
    realized_return_pct_1m: Decimal | None
    outcome_label_1d: str | None
    outcome_label_1w: str | None
    outcome_label_1m: str | None
    outcome_explanation_nl: str
    last_evaluated_at: datetime
    created_at: datetime
    updated_at: datetime
    safe_for_self_learning: bool = False
    safe_for_model_retraining: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "entry_id",
            "suggestion_id",
            "ibkr_conid",
            "symbol",
            "currency",
            "issued_action_label",
            "issued_action_label_nl",
            "issued_confidence_label",
            "outcome_explanation_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.safe_for_self_learning or self.safe_for_model_retraining:
            raise ValueError(
                "Prediction Diary safety booleans must remain false in V1."
            )
        if self.issued_horizon_days <= 0:
            raise ValueError("issued_horizon_days must be positive")


@dataclass(frozen=True)
class DecisionPackageExplanationRecord:
    """One AI-generated Dutch explanation per (decision_package_id,
    decision_package_content_hash) — immutable per package version.

    The doctrine (release-1-functional-workflow-blueprint.md §6 + §8) is
    that AI **never** originates a financial number; an explanation may
    only paraphrase the persisted Decision Package + linked research
    evidence. The boundary is enforced by ``hallucinated_numbers_json``
    being non-null/non-empty → ``status="blocked"``.

    All safety booleans stay ``False`` in V1: an explanation must never
    self-promote into retraining, action drafts, or orders.
    """

    explanation_id: str
    decision_package_id: str
    decision_package_content_hash: str
    ibkr_conid: str
    symbol: str
    model_provider_code: str
    model_name: str
    model_version: str
    input_evidence_hash: str
    output_text_hash: str
    explanation_nl: str
    risk_disclaimer_nl: str
    status: str
    blocking_reason: str | None
    hallucinated_numbers_json: tuple[str, ...] | None
    generated_at: datetime
    created_at: datetime
    safe_for_self_learning: bool = False
    safe_for_action_drafts: bool = False
    safe_for_orders: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "explanation_id",
            "decision_package_id",
            "decision_package_content_hash",
            "ibkr_conid",
            "symbol",
            "model_provider_code",
            "model_name",
            "model_version",
            "input_evidence_hash",
            "output_text_hash",
            "explanation_nl",
            "risk_disclaimer_nl",
            "status",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if (
            self.safe_for_self_learning
            or self.safe_for_action_drafts
            or self.safe_for_orders
        ):
            raise ValueError(
                "Explanation safety booleans must remain false in V1: an "
                "explanation never self-promotes into retraining, action "
                "drafts, or orders."
            )


@dataclass(frozen=True)
class ExplanationEvidenceLedgerRecord:
    """Append-only audit row: which content-hashes did the model see?

    One row per (explanation, evidence_item). The combination of
    ``evidence_kind`` + ``evidence_reference_id`` + ``evidence_content_hash``
    is what makes the input set replayable.
    """

    ledger_id: str
    explanation_id: str
    evidence_kind: str
    evidence_reference_id: str
    evidence_content_hash: str
    linked_at: datetime
    safe_for_self_learning: bool = False
    safe_for_model_retraining: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "ledger_id",
            "explanation_id",
            "evidence_kind",
            "evidence_reference_id",
            "evidence_content_hash",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.safe_for_self_learning or self.safe_for_model_retraining:
            raise ValueError(
                "Evidence ledger safety booleans must remain false in V1."
            )


@dataclass(frozen=True)
class DailyBriefingRecord:
    """One deterministic daily briefing summary.

    UNIQUE on ``briefing_date`` — one briefing per day. Counts are
    derived deterministically from the persisted suggestions / Decision
    Packages / action drafts / diary entries / events that fall after
    the lookback boundary. AI never authors the summary.

    Safety booleans stay ``False`` in V1: a briefing never auto-promotes
    into an order or a draft state change.
    """

    briefing_id: str
    briefing_date: date
    generated_at: datetime
    lookback_started_at: datetime
    position_count: int
    base_currency: str | None
    total_position_value: Decimal | None
    cash_total: Decimal | None
    fx_freshness_status: str | None
    new_suggestion_count: int
    new_decision_package_count: int
    new_action_draft_count: int
    diary_outcomes_closed_count: int
    critical_event_count: int
    alert_count: int
    summary_nl: str
    help_nl: str
    status: str
    blocking_reason: str | None
    safe_for_action_drafts: bool = False
    safe_for_orders: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "briefing_id",
            "summary_nl",
            "help_nl",
            "status",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        for count_name in (
            "position_count",
            "new_suggestion_count",
            "new_decision_package_count",
            "new_action_draft_count",
            "diary_outcomes_closed_count",
            "critical_event_count",
            "alert_count",
        ):
            if getattr(self, count_name) < 0:
                raise ValueError(f"{count_name} must be non-negative.")
        if self.safe_for_action_drafts or self.safe_for_orders:
            raise ValueError(
                "Daily briefing safety booleans must remain false in V1."
            )


@dataclass(frozen=True)
class BriefingAlertRecord:
    """Append-only alert row attached to one daily briefing.

    Used by the operator UI to surface the deterministic counter-based
    findings (new suggestion, FX stale, critical state event, diary
    outcome closed). Safety booleans stay ``False``.
    """

    alert_id: str
    briefing_id: str
    alert_kind: str
    severity: str
    reference_kind: str | None
    reference_id: str | None
    title_nl: str
    body_nl: str
    acknowledged_at: datetime | None
    linked_at: datetime
    safe_for_action_drafts: bool = False
    safe_for_orders: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "alert_id",
            "briefing_id",
            "alert_kind",
            "severity",
            "title_nl",
            "body_nl",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.severity not in {"info", "warning", "critical"}:
            raise ValueError(
                f"severity must be info/warning/critical, got {self.severity!r}"
            )
        if self.safe_for_action_drafts or self.safe_for_orders:
            raise ValueError(
                "Briefing alert safety booleans must remain false in V1."
            )


@dataclass(frozen=True)
class UniverseScanRunRecord:
    """Audit row for one daily universe-scan invocation.

    Locked in `version-1-product-experience-locks.md §21.6` as the
    provenance row that proves which subset of the ~5 000-ticker
    universe was actually scanned today, how many fundamentals were
    persisted, and how many candidates ranked through to the briefing.
    Safety booleans stay False — a scan never promotes anything by
    itself.
    """

    run_id: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    triggered_by: str
    scanned_count: int
    persisted_count: int
    failed_count: int
    ranked_count: int
    universe_size: int
    error_text: str | None
    safe_for_action_drafts: bool = False
    safe_for_orders: bool = False

    def __post_init__(self) -> None:
        for field_name in ("run_id", "status", "triggered_by"):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.status not in {"running", "succeeded", "failed", "skipped"}:
            raise ValueError(
                f"status must be running/succeeded/failed/skipped, got {self.status!r}"
            )
        if self.triggered_by not in {"scheduler", "manual"}:
            raise ValueError(
                f"triggered_by must be scheduler/manual, got {self.triggered_by!r}"
            )
        for count_name in (
            "scanned_count",
            "persisted_count",
            "failed_count",
            "ranked_count",
            "universe_size",
        ):
            if getattr(self, count_name) < 0:
                raise ValueError(f"{count_name} must be non-negative.")
        if self.safe_for_action_drafts or self.safe_for_orders:
            raise ValueError(
                "Universe-scan run safety booleans must remain false in V1."
            )


@dataclass(frozen=True)
class AssetFundamentalsSnapshotRecord:
    """One snapshot of factor-scoring fundamentals for one asset.

    Locked in `version-1-product-experience-locks.md §21.4` as input to
    the QVM (Quality + Value + Momentum) factor predictor. Every value
    is informational; the safety booleans stay False — a fundamentals
    row never promotes a draft or an order.

    Numeric fields are nullable because EODHD's payloads are often
    sparse; the QVM predictor blocks per-asset rather than silently
    treating ``None`` as zero.
    """

    snapshot_id: str
    ibkr_conid: str | None
    eodhd_symbol: str
    symbol: str
    sector: str | None
    currency: str | None
    market_cap: Decimal | None
    pe_ratio: Decimal | None
    pb_ratio: Decimal | None
    ev_ebitda: Decimal | None
    roic_pct: Decimal | None
    gross_margin_pct: Decimal | None
    dividend_yield_pct: Decimal | None
    return_6m_pct: Decimal | None
    return_12m_pct: Decimal | None
    raw_payload_hash: str
    provider_code: str
    fetched_at: datetime
    stored_at: datetime
    safe_for_orders: bool = False
    safe_for_action_drafts: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "snapshot_id",
            "eodhd_symbol",
            "symbol",
            "raw_payload_hash",
            "provider_code",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.safe_for_orders or self.safe_for_action_drafts:
            raise ValueError(
                "Fundamentals-snapshot safety booleans must remain false in V1."
            )


@dataclass(frozen=True)
class SchedulerRunRecord:
    """Audit row for one APScheduler job invocation.

    Locked in `version-1-product-experience-locks.md §21.7`: APScheduler
    runs in-process; every fire is captured here so the operator can
    replay what triggered the daily chain. Safety booleans stay False —
    a scheduled run never auto-promotes into an order; it just queues
    the briefing for the user to read.
    """

    run_id: str
    job_name: str
    scheduled_at: datetime
    started_at: datetime
    finished_at: datetime | None
    status: str
    error_text: str | None
    triggered_by: str
    safe_for_action_drafts: bool = False
    safe_for_orders: bool = False

    def __post_init__(self) -> None:
        for field_name in ("run_id", "job_name", "status", "triggered_by"):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.status not in {"running", "succeeded", "failed", "skipped"}:
            raise ValueError(
                f"status must be running/succeeded/failed/skipped, got {self.status!r}"
            )
        if self.triggered_by not in {"scheduler", "manual"}:
            raise ValueError(
                f"triggered_by must be scheduler/manual, got {self.triggered_by!r}"
            )
        if self.safe_for_action_drafts or self.safe_for_orders:
            raise ValueError(
                "Scheduler-run safety booleans must remain false in V1."
            )


@dataclass(frozen=True)
class PredictorBacktestRunRecord:
    """Audit row for one predictor backtest invocation.

    Locked in `version-1-product-experience-locks.md §22` (V1.1
    expansion). Slice 24 (predictor refactor base) creates the row
    schema; Slice 25 (backtesting framework) writes rows; Slice 26
    (feedback loop + auto-weighting) aggregates the rolling Brier
    score for the ensemble combiner. Safety booleans stay False —
    a backtest result never authorises an order.
    """

    run_id: str
    model_code: str
    model_version: str
    asset_symbol: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    window_days: int
    bars_used: int
    brier_score: Decimal | None
    hit_rate: Decimal | None
    sharpe_ratio: Decimal | None
    blocking_reason: str | None
    explanation_nl: str | None
    safe_for_action_drafts: bool = False
    safe_for_orders: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "run_id",
            "model_code",
            "model_version",
            "asset_symbol",
            "status",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.status not in {"running", "succeeded", "failed", "skipped"}:
            raise ValueError(
                f"status must be running/succeeded/failed/skipped, got {self.status!r}"
            )
        if self.window_days <= 0:
            raise ValueError("window_days must be positive")
        if self.bars_used < 0:
            raise ValueError("bars_used must be non-negative")
        if self.hit_rate is not None and not (
            Decimal("0") <= self.hit_rate <= Decimal("1")
        ):
            raise ValueError("hit_rate must be in [0, 1] when provided")
        if self.brier_score is not None and self.brier_score < 0:
            raise ValueError("brier_score must be non-negative when provided")
        if self.safe_for_action_drafts or self.safe_for_orders:
            raise ValueError(
                "Predictor-backtest safety booleans must remain false in V1.1."
            )


@dataclass(frozen=True)
class PredictionDiaryPredictorContributionRecord:
    """One row per (Prediction Diary entry × predictor) — the V1.1
    Slice 26 feedback-loop surface.

    Slice 26 wires the auto-weighted ensemble strategy on the
    combiner by reading the rolling per-predictor Brier score
    derived from these rows. Each row carries the predictor's
    *issued* numbers + the realised market outcome at the diary's
    locked 1-month horizon. Safety booleans hard-False; the row
    never authorises an order.
    """

    contribution_id: str
    diary_entry_id: str
    model_code: str
    model_version: str
    predicted_return_pct: Decimal
    predicted_prob_gain: Decimal
    predicted_direction: str
    realised_return_pct: Decimal | None
    realised_direction: str | None
    outcome_label: str | None
    brier_score: Decimal | None
    return_spread_pct: Decimal | None
    explanation_nl: str | None
    created_at: datetime
    safe_for_action_drafts: bool = False
    safe_for_orders: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "contribution_id",
            "diary_entry_id",
            "model_code",
            "model_version",
            "predicted_direction",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if not (
            Decimal("0") <= self.predicted_prob_gain <= Decimal("1")
        ):
            raise ValueError(
                "predicted_prob_gain must be in [0, 1]"
            )
        if self.brier_score is not None and self.brier_score < 0:
            raise ValueError(
                "brier_score must be non-negative when provided"
            )
        if self.safe_for_action_drafts or self.safe_for_orders:
            raise ValueError(
                "Predictor-contribution safety booleans must remain false in V1.1."
            )


@dataclass(frozen=True)
class ClaudeAiBudgetUsageRecord:
    """One audit row per Anthropic Claude API call.

    Locked by V1.1 §22.2: the explanation + TS-forecast providers
    consult the running monthly total before issuing a call; once
    the total exceeds ``CLAUDE_AI_BUDGET_MONTHLY_EUR`` the
    provider refuses to call and the orchestrator falls back to
    the stub. Safety booleans hard-False; a budget row never
    authorises an order.
    """

    usage_id: str
    budget_month: str  # ``YYYY-MM``
    provider_code: str
    model_name: str
    called_at: datetime
    input_units: int
    cached_input_units: int
    output_units: int
    cost_eur: Decimal
    call_kind: str  # ``explanation`` | ``ts_forecast``
    explanation_nl: str | None = None
    safe_for_action_drafts: bool = False
    safe_for_orders: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "usage_id",
            "budget_month",
            "provider_code",
            "model_name",
            "call_kind",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if self.call_kind not in {"explanation", "ts_forecast"}:
            raise ValueError(
                f"call_kind must be explanation/ts_forecast, got {self.call_kind!r}"
            )
        if len(self.budget_month) != 7 or self.budget_month[4] != "-":
            raise ValueError(
                f"budget_month must be YYYY-MM, got {self.budget_month!r}"
            )
        for field_name in ("input_units", "cached_input_units", "output_units"):
            value = getattr(self, field_name)
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative")
        if self.cost_eur < 0:
            raise ValueError("cost_eur must be non-negative")
        if self.safe_for_action_drafts or self.safe_for_orders:
            raise ValueError(
                "Claude AI budget-usage safety booleans must remain false in V1.1."
            )


# Task 128: cold-start onboarding records.
_LOCKED_WATCHLIST_CONFIRMATION_STATES = frozenset({"unconfirmed", "confirmed"})
_LOCKED_WATCHLIST_AUDIT_FROM_STATES = frozenset(
    {"absent", "unconfirmed", "confirmed"}
)
_LOCKED_WATCHLIST_AUDIT_TO_STATES = frozenset({"unconfirmed", "confirmed"})
_LOCKED_WATCHLIST_AUDIT_ACTORS = frozenset({"system", "user"})


@dataclass(frozen=True)
class ColdStartSeedAuditEntry:
    """One row per starter-watchlist seed event.

    Task 128 product lock §1: the seed runs at most once per
    ``ibkr_account_id``. The database enforces this via ``UNIQUE`` on
    ``ibkr_account_id``; the repository surfaces ``AlreadySeeded`` if
    a caller tries to seed twice.
    """

    seeded_at: datetime
    ibkr_account_id: str
    seeded_count: int
    failed_conids_json: str
    seed_version: str

    def __post_init__(self) -> None:
        _require_non_empty(self.ibkr_account_id, "ibkr_account_id")
        _require_non_empty(self.seed_version, "seed_version")
        if self.seeded_count < 0:
            raise ValueError("seeded_count must be non-negative")


@dataclass(frozen=True)
class WatchlistConfirmationStateRecord:
    """One row per account; tracks unconfirmed → confirmed flips."""

    ibkr_account_id: str
    state: str
    last_updated_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty(self.ibkr_account_id, "ibkr_account_id")
        if self.state not in _LOCKED_WATCHLIST_CONFIRMATION_STATES:
            raise ValueError(
                f"state {self.state!r} is not in the locked set "
                f"{sorted(_LOCKED_WATCHLIST_CONFIRMATION_STATES)}"
            )


@dataclass(frozen=True)
class WatchlistConfirmationAuditEntry:
    """Append-only row per state transition.

    ``actor='system'`` for the seed (``absent → unconfirmed``);
    ``actor='user'`` for the BEVESTIG confirmation
    (``unconfirmed → confirmed``).
    """

    event_at: datetime
    ibkr_account_id: str
    from_state: str
    to_state: str
    actor: str
    row_count_at_event: int
    details_json: str | None

    def __post_init__(self) -> None:
        _require_non_empty(self.ibkr_account_id, "ibkr_account_id")
        if self.from_state not in _LOCKED_WATCHLIST_AUDIT_FROM_STATES:
            raise ValueError(
                f"from_state {self.from_state!r} not in "
                f"{sorted(_LOCKED_WATCHLIST_AUDIT_FROM_STATES)}"
            )
        if self.to_state not in _LOCKED_WATCHLIST_AUDIT_TO_STATES:
            raise ValueError(
                f"to_state {self.to_state!r} not in "
                f"{sorted(_LOCKED_WATCHLIST_AUDIT_TO_STATES)}"
            )
        if self.actor not in _LOCKED_WATCHLIST_AUDIT_ACTORS:
            raise ValueError(
                f"actor {self.actor!r} not in "
                f"{sorted(_LOCKED_WATCHLIST_AUDIT_ACTORS)}"
            )
        if self.row_count_at_event < 0:
            raise ValueError("row_count_at_event must be non-negative")


@dataclass(frozen=True)
class WatchlistItemSeedRecord:
    """Subset of the locked ``watchlist_items`` columns the Task 128
    seed function writes.

    The legacy ``apps/api/.../watchlist.py`` STORE-backed routes are
    untouched (their cleanup is its own task). This record is the
    only durable path Task 128 uses — for the seed write + the
    cold-start UI's read.
    """

    watchlist_item_id: str
    ibkr_account_id: str
    asset_id: str | None
    symbol: str
    name: str | None
    exchange: str | None
    currency: str | None
    security_type: str | None
    status: str
    source: str
    is_starter_seed: bool
    seed_version: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty(self.watchlist_item_id, "watchlist_item_id")
        _require_non_empty(self.ibkr_account_id, "ibkr_account_id")
        _require_non_empty(self.symbol, "symbol")
        if self.status not in ("active", "archived"):
            raise ValueError(
                f"status {self.status!r} must be one of {'active', 'archived'}"
            )
        if self.source not in ("manual", "cold_start_seed"):
            raise ValueError(
                f"source {self.source!r} must be one of "
                f"{'manual', 'cold_start_seed'}"
            )


class ColdStartAlreadySeededError(RuntimeError):
    """Raised when the seed is invoked twice for the same account.

    Task 128 product lock §1: the cold-start seed is one-time only
    per ``ibkr_account_id``. The repository catches the unique-
    constraint violation and translates it into this typed error so
    the worker can return cleanly without leaking SQLAlchemy types.
    """


# Task 129: EOD market-data runtime records.
_LOCKED_MARKET_DATA_PROVIDERS = frozenset({"eodhd", "manual", "unknown"})
_LOCKED_FX_RATE_PROVIDERS = frozenset({"eodhd", "ecb", "manual"})


@dataclass(frozen=True)
class MarketDataEodSnapshotEntry:
    """One row per (ibkr_conid, as_of_date, provider).

    Task 129 product lock §3: locked OHLCV columns + provider hash
    for audit. All money fields Decimal end-to-end. The UNIQUE
    constraint at the DB level enforces fetch idempotency — the
    second call for the same (conid, date, provider) is a no-op.
    """

    snapshot_id: str
    ibkr_conid: str
    symbol: str
    exchange: str | None
    currency_local: str
    as_of_date: date
    as_of_close_ts: datetime
    ingested_ts: datetime
    open_local: Decimal | None
    high_local: Decimal | None
    low_local: Decimal | None
    close_local: Decimal
    adj_close_local: Decimal | None
    volume: int | None
    provider: str
    provider_response_hash: str

    def __post_init__(self) -> None:
        _require_non_empty(self.snapshot_id, "snapshot_id")
        _require_non_empty(self.ibkr_conid, "ibkr_conid")
        _require_non_empty(self.symbol, "symbol")
        _require_non_empty(self.currency_local, "currency_local")
        _require_non_empty(self.provider_response_hash, "provider_response_hash")
        if self.provider not in _LOCKED_MARKET_DATA_PROVIDERS:
            raise ValueError(
                f"provider {self.provider!r} not in "
                f"{sorted(_LOCKED_MARKET_DATA_PROVIDERS)}"
            )
        if self.close_local < 0:
            raise ValueError("close_local must be non-negative")
        if self.volume is not None and self.volume < 0:
            raise ValueError("volume must be non-negative")


@dataclass(frozen=True)
class FxRateRecord:
    """One row per (base, quote, as_of_date, provider).

    Task 129 product lock §5: the EUR conversion happens at display
    time via the API joining the per-day rate. Stored rate is the
    quote-per-base rate (1 base unit = ``rate`` quote units).
    """

    base_currency: str
    quote_currency: str
    as_of_date: date
    rate: Decimal
    ingested_ts: datetime
    provider: str

    def __post_init__(self) -> None:
        _require_non_empty(self.base_currency, "base_currency")
        _require_non_empty(self.quote_currency, "quote_currency")
        if self.provider not in _LOCKED_FX_RATE_PROVIDERS:
            raise ValueError(
                f"provider {self.provider!r} not in "
                f"{sorted(_LOCKED_FX_RATE_PROVIDERS)}"
            )
        if self.rate < 0:
            raise ValueError("rate must be non-negative")
        if len(self.base_currency) != 3 or len(self.quote_currency) != 3:
            raise ValueError("currency codes must be 3-letter ISO")


@dataclass(frozen=True)
class ProviderCallAuditEntry:
    """One row per outbound provider HTTP call.

    Task 129 product lock §8: every EODHD call (success / 4xx / 5xx)
    writes one row capturing status + duration + size + error
    details. Append-only.
    """

    audit_id: str
    called_at: datetime
    provider: str
    endpoint: str
    request_params_json: str | None
    response_status: int | None
    response_size_bytes: int | None
    duration_ms: int | None
    error_class: str | None
    error_details_json: str | None
    account_id: str | None
    triggered_by_run_id: str | None

    def __post_init__(self) -> None:
        _require_non_empty(self.audit_id, "audit_id")
        _require_non_empty(self.provider, "provider")
        _require_non_empty(self.endpoint, "endpoint")
        if (
            self.response_status is not None
            and not 100 <= self.response_status <= 599
        ):
            raise ValueError("response_status out of range")


class EodhdNotConfiguredError(RuntimeError):
    """Raised by callers attempting EODHD work without an API key.

    Lives in storage so the orchestrator + the worker EODHD client
    can both surface the typed error without circular imports.
    """


# Task 130: historical-bootstrap forecast + calibration diary records.
_LOCKED_FORECAST_METHODS = frozenset({"historical_bootstrap_v1"})
_LOCKED_FORECAST_LABELS = frozenset(
    {"Kopen", "Verminderen", "Verkopen", "Houden", "Bekijken", "Geblokkeerd"}
)
_LOCKED_FORECAST_CONFIDENCE = frozenset({"Laag", "Gemiddeld", "Hoog"})
_LOCKED_HIT_STATUSES = frozenset(
    {
        "realized_within_p10_p90",
        "realized_outside_band",
        "realized_above_p90",
        "realized_below_p10",
    }
)
# Task 131 product lock §5: specific block reasons. The Task 130
# reasons (data_stale, insufficient_history, implausible_volatility,
# data_unavailable) are kept for backwards compatibility with rows
# already in the diary; Task 131 adds the more specific
# `stale_market_data`, `missing_asset_listing`, `computation_error`,
# `excessive_volatility`. The UI maps each to a Dutch microcopy.
_LOCKED_FORECAST_BLOCK_REASONS = frozenset(
    {
        # Task 130 (kept for backwards compat with historical rows).
        "data_stale",
        "insufficient_history",
        "implausible_volatility",
        "data_unavailable",
        "not_held_for_sell_label",
        # Task 131 (newly added, more specific).
        "stale_market_data",
        "missing_asset_listing",
        "computation_error",
        "excessive_volatility",
    }
)


@dataclass(frozen=True)
class ForecastEntry:
    """One probabilistic forecast row.

    Task 130 product lock §3 + §4: locked p10/p50/p90 + probabilities +
    confidence + locked Dutch label. Append-only; UNIQUE on
    (conid, generated_at).
    """

    forecast_run_id: str
    conid: str
    generated_at: datetime
    generated_by_scheduled_run_id: str
    horizon_trading_days: int
    forecast_valid_until: datetime
    method: str
    history_window_days: int
    history_closes_count: int
    current_price_local: Decimal
    currency_local: str
    p10_log_return: Decimal
    p50_log_return: Decimal
    p90_log_return: Decimal
    prob_positive: Decimal
    prob_loss_gt_5pct: Decimal
    expected_volatility_annualized: Decimal
    confidence_level: str
    label: str
    block_reason: str | None
    expired_at: datetime | None

    def __post_init__(self) -> None:
        _require_non_empty(self.forecast_run_id, "forecast_run_id")
        _require_non_empty(self.conid, "conid")
        _require_non_empty(
            self.generated_by_scheduled_run_id, "generated_by_scheduled_run_id"
        )
        if self.horizon_trading_days <= 0:
            raise ValueError("horizon_trading_days must be positive")
        if self.method not in _LOCKED_FORECAST_METHODS:
            raise ValueError(
                f"method {self.method!r} not in "
                f"{sorted(_LOCKED_FORECAST_METHODS)}"
            )
        if self.confidence_level not in _LOCKED_FORECAST_CONFIDENCE:
            raise ValueError(
                f"confidence_level {self.confidence_level!r} not in "
                f"{sorted(_LOCKED_FORECAST_CONFIDENCE)}"
            )
        if self.label not in _LOCKED_FORECAST_LABELS:
            raise ValueError(
                f"label {self.label!r} not in {sorted(_LOCKED_FORECAST_LABELS)}"
            )
        if not (Decimal("0") <= self.prob_positive <= Decimal("1")):
            raise ValueError("prob_positive must be in [0, 1]")
        if not (Decimal("0") <= self.prob_loss_gt_5pct <= Decimal("1")):
            raise ValueError("prob_loss_gt_5pct must be in [0, 1]")
        if self.expected_volatility_annualized < 0:
            raise ValueError("expected_volatility_annualized must be non-negative")
        if self.current_price_local < 0:
            raise ValueError("current_price_local must be non-negative")
        if self.label == "Geblokkeerd" and not self.block_reason:
            raise ValueError(
                "block_reason is required when label is Geblokkeerd"
            )
        if (
            self.block_reason is not None
            and self.block_reason not in _LOCKED_FORECAST_BLOCK_REASONS
        ):
            raise ValueError(
                f"block_reason {self.block_reason!r} not in "
                f"{sorted(_LOCKED_FORECAST_BLOCK_REASONS)}"
            )


@dataclass(frozen=True)
class CalibrationDiaryEntry:
    """One row per evaluated forecast.

    Task 130 product lock §8: append-only; UNIQUE on forecast_run_id.
    The realized return is the actual 20-trading-day-later log-return;
    hit_status is computed deterministically.
    """

    forecast_run_id: str
    evaluated_at: datetime
    realized_log_return: Decimal
    hit_status: str
    realized_close_price: Decimal

    def __post_init__(self) -> None:
        _require_non_empty(self.forecast_run_id, "forecast_run_id")
        if self.hit_status not in _LOCKED_HIT_STATUSES:
            raise ValueError(
                f"hit_status {self.hit_status!r} not in "
                f"{sorted(_LOCKED_HIT_STATUSES)}"
            )
        if self.realized_close_price < 0:
            raise ValueError("realized_close_price must be non-negative")


# Task 132: Decision Package locked enums + records.
_LOCKED_FRESHNESS_STATES = frozenset({"fresh", "stale", "unavailable"})
# Same six labels as the forecast, except 'Geblokkeerd' which gets no
# Decision Package — see Task 132 product lock §2.
_LOCKED_DECISION_PACKAGE_LABELS = frozenset(
    {"Kopen", "Verminderen", "Verkopen", "Houden", "Bekijken"}
)


@dataclass(frozen=True)
class GateOutcome:
    """One row in the Decision Package's ``gate_outcomes`` list.

    Each gate the composer evaluates produces one of these. ``reason_nl``
    is the Dutch sentence the UI surfaces when ``passed=False``; it's
    empty (``""``) when the gate passes — see Task 132 product lock §1.
    """

    gate_name: str
    passed: bool
    reason_nl: str

    def __post_init__(self) -> None:
        _require_non_empty(self.gate_name, "gate_name")
        if not self.passed and not self.reason_nl:
            raise ValueError(
                "reason_nl is required when a gate fails"
            )


@dataclass(frozen=True)
class EvidenceReference:
    """One row in the Decision Package's ``evidence_references`` list.

    Records the source the composer used as evidence for the package.
    For V1.1.0 ``source_type`` ∈ {``market_data_snapshot``, ``fx_rate``,
    ``ibkr_position_snapshot``}. External evidence (news, filings) is
    explicitly out of scope per the Task 132 brief.
    """

    source_id: str
    source_type: str
    claim_summary: str

    def __post_init__(self) -> None:
        _require_non_empty(self.source_id, "source_id")
        _require_non_empty(self.source_type, "source_type")
        _require_non_empty(self.claim_summary, "claim_summary")


@dataclass(frozen=True)
class DecisionPackageEntry:
    """Immutable Decision Package — Task 132 product lock §1 + §4.

    Composed only when the underlying forecast label is NOT
    ``Geblokkeerd`` (validated in ``__post_init__``). Append-only at the
    storage layer; the repository has no ``update`` or ``delete``. Hash
    chained per (ibkr_account_id, conid) via ``previous_package_hash``.

    Safety booleans are hard-False at the dataclass level too, mirroring
    the DB CHECK constraint — defense in depth so a misconfigured caller
    can't slip a True past the repo. They only flip in future tasks
    when the Action Center + approval workflow ship.
    """

    decision_package_id: str
    forecast_run_id: str
    composed_at: datetime
    valid_until: datetime
    ibkr_account_id: str
    conid: str
    symbol: str
    exchange: str | None
    currency_local: str
    asset_class: str | None
    user_holds_position: bool
    held_quantity: Decimal | None
    held_avg_cost_local: Decimal | None
    current_price_local: Decimal
    current_price_eur: Decimal
    as_of_market_data_ts: datetime
    freshness_state: str
    data_age_trading_days: int
    forecast_method: str
    p10_log_return: Decimal
    p50_log_return: Decimal
    p90_log_return: Decimal
    p10_price_eur: Decimal
    p50_price_eur: Decimal
    p90_price_eur: Decimal
    prob_positive: Decimal
    prob_loss_gt_5pct: Decimal
    expected_volatility_annualized: Decimal
    forecast_confidence_level: str
    suggested_action_label: str
    block_reason: str | None
    gate_outcomes: tuple[GateOutcome, ...]
    evidence_references: tuple[EvidenceReference, ...]
    deterministic_dutch_explanation: str
    audit_trail_hash: str
    previous_package_hash: str | None
    safe_for_action_drafts: bool = False
    safe_for_orders: bool = False

    def __post_init__(self) -> None:
        _require_non_empty(
            self.decision_package_id, "decision_package_id"
        )
        _require_non_empty(self.forecast_run_id, "forecast_run_id")
        _require_non_empty(self.ibkr_account_id, "ibkr_account_id")
        _require_non_empty(self.conid, "conid")
        _require_non_empty(self.symbol, "symbol")
        _require_non_empty(self.currency_local, "currency_local")
        _require_non_empty(
            self.deterministic_dutch_explanation,
            "deterministic_dutch_explanation",
        )
        _require_non_empty(self.audit_trail_hash, "audit_trail_hash")
        if self.freshness_state not in _LOCKED_FRESHNESS_STATES:
            raise ValueError(
                f"freshness_state {self.freshness_state!r} not in "
                f"{sorted(_LOCKED_FRESHNESS_STATES)}"
            )
        if self.forecast_method not in _LOCKED_FORECAST_METHODS:
            raise ValueError(
                f"forecast_method {self.forecast_method!r} not in "
                f"{sorted(_LOCKED_FORECAST_METHODS)}"
            )
        if self.forecast_confidence_level not in _LOCKED_FORECAST_CONFIDENCE:
            raise ValueError(
                f"forecast_confidence_level "
                f"{self.forecast_confidence_level!r} not in "
                f"{sorted(_LOCKED_FORECAST_CONFIDENCE)}"
            )
        if self.suggested_action_label not in _LOCKED_DECISION_PACKAGE_LABELS:
            raise ValueError(
                f"suggested_action_label {self.suggested_action_label!r} "
                f"not in {sorted(_LOCKED_DECISION_PACKAGE_LABELS)} "
                "(Geblokkeerd forecasts get no Decision Package)"
            )
        if self.current_price_local < 0:
            raise ValueError("current_price_local must be non-negative")
        if self.current_price_eur < 0:
            raise ValueError("current_price_eur must be non-negative")
        if not (Decimal("0") <= self.prob_positive <= Decimal("1")):
            raise ValueError("prob_positive must be in [0, 1]")
        if not (Decimal("0") <= self.prob_loss_gt_5pct <= Decimal("1")):
            raise ValueError("prob_loss_gt_5pct must be in [0, 1]")
        if self.expected_volatility_annualized < 0:
            raise ValueError(
                "expected_volatility_annualized must be non-negative"
            )
        if self.data_age_trading_days < 0:
            raise ValueError("data_age_trading_days must be non-negative")
        if self.safe_for_action_drafts:
            raise ValueError(
                "safe_for_action_drafts must be False until the "
                "Action Center workflow ships (Task 132 product lock §1)"
            )
        if self.safe_for_orders:
            raise ValueError(
                "safe_for_orders must be False until the order-submission "
                "workflow ships (Task 132 product lock §1)"
            )
        if self.user_holds_position:
            if self.held_quantity is None or self.held_quantity <= 0:
                raise ValueError(
                    "held_quantity must be positive when "
                    "user_holds_position is True"
                )


# Task 133 — Action Draft locked vocabularies.
_LOCKED_ACTION_DRAFT_SIDES = frozenset({"BUY", "SELL"})
_LOCKED_ACTION_DRAFT_ORDER_TYPES = frozenset({"LMT"})
_LOCKED_ACTION_DRAFT_TIME_IN_FORCE = frozenset({"DAY"})
_LOCKED_ACTION_DRAFT_CREATED_BY = frozenset({"user", "system"})
# Task 134 extends this to cover the in-flight + terminal IBKR
# statuses ``ActionDraftEntry`` may be read back with. The original
# six statuses stay valid; the additional nine are the lifecycle
# values the storage layer accepts and that ``ActionDraftEntry`` must
# round-trip.
_LOCKED_ACTION_DRAFT_STATUSES = frozenset(
    {
        "proposed",
        "edited",
        "user_approved",
        "dismissed",
        "deleted",
        "superseded",
        "submitted",
        "accepted",
        "working",
        "filled",
        "partially_filled",
        "cancelled",
        "rejected",
        "pending_cancellation",
        "awaiting_reply_timeout",
        # Task 135: reconciler escalation path for timeouts older than 24h
        # or terminal-state divergence that needs user attention.
        "requires_manual_review",
    }
)
_LOCKED_ACTION_DRAFT_EVENT_TYPES = frozenset(
    {"created", "edited", "approved", "dismissed", "deleted", "superseded"}
)
_LOCKED_ACTION_DRAFT_AUDIT_ACTORS = frozenset({"user", "system"})


@dataclass(frozen=True)
class ActionDraftEntry:
    """Immutable Action Draft — Task 133 product lock §3.

    A user-promotable IBKR-format order proposal derived from a
    non-Geblokkeerd Decision Package (or user-supplied without a package).
    Editable through the repository's ``update_fields`` /
    ``update_status`` paths until ``user_approved``; after that the
    repository refuses further mutation.

    ``safe_for_submission`` is hard-False at the dataclass level too,
    mirroring the DB CHECK constraint — defense in depth so no caller
    can slip a True past the repo until Task 134 (actual submission)
    ships its own product locks.
    """

    action_draft_id: str
    decision_package_id: str | None
    forecast_run_id: str | None
    created_at: datetime
    created_by: str
    ibkr_account_id: str
    conid: str
    symbol: str
    exchange: str
    currency_local: str
    side: str
    quantity: Decimal
    order_type: str
    limit_price_local: Decimal
    time_in_force: str
    notional_local: Decimal
    notional_eur: Decimal
    fx_rate_at_creation: Decimal
    usable_cash_eur_at_creation: Decimal
    held_quantity_at_creation: Decimal | None
    status: str
    last_edited_at: datetime | None
    user_approved_at: datetime | None
    dismissed_at: datetime | None
    deleted_at: datetime | None
    dismissed_reason: str | None
    user_note: str | None
    superseded_by_decision_package_id: str | None
    audit_trail_hash: str
    previous_draft_hash: str | None
    safe_for_submission: bool = False
    # Task 134 lifecycle columns. Optional with safe defaults so
    # existing Task 133 call sites + factories keep working.
    submission_block_reason: str | None = None
    submission_started_at: datetime | None = None
    terminal_state_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.action_draft_id, "action_draft_id")
        _require_non_empty(self.ibkr_account_id, "ibkr_account_id")
        _require_non_empty(self.conid, "conid")
        _require_non_empty(self.symbol, "symbol")
        _require_non_empty(self.exchange, "exchange")
        _require_non_empty(self.currency_local, "currency_local")
        _require_non_empty(self.audit_trail_hash, "audit_trail_hash")
        if self.created_by not in _LOCKED_ACTION_DRAFT_CREATED_BY:
            raise ValueError(
                f"created_by {self.created_by!r} not in "
                f"{sorted(_LOCKED_ACTION_DRAFT_CREATED_BY)}"
            )
        if self.side not in _LOCKED_ACTION_DRAFT_SIDES:
            raise ValueError(
                f"side {self.side!r} not in "
                f"{sorted(_LOCKED_ACTION_DRAFT_SIDES)}"
            )
        if self.order_type not in _LOCKED_ACTION_DRAFT_ORDER_TYPES:
            raise ValueError(
                f"order_type {self.order_type!r} not in "
                f"{sorted(_LOCKED_ACTION_DRAFT_ORDER_TYPES)}"
            )
        if self.time_in_force not in _LOCKED_ACTION_DRAFT_TIME_IN_FORCE:
            raise ValueError(
                f"time_in_force {self.time_in_force!r} not in "
                f"{sorted(_LOCKED_ACTION_DRAFT_TIME_IN_FORCE)}"
            )
        if self.status not in _LOCKED_ACTION_DRAFT_STATUSES:
            raise ValueError(
                f"status {self.status!r} not in "
                f"{sorted(_LOCKED_ACTION_DRAFT_STATUSES)}"
            )
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.limit_price_local <= 0:
            raise ValueError("limit_price_local must be positive")
        if self.notional_local < 0:
            raise ValueError("notional_local must be non-negative")
        if self.notional_eur < 0:
            raise ValueError("notional_eur must be non-negative")
        if self.fx_rate_at_creation <= 0:
            raise ValueError("fx_rate_at_creation must be positive")
        if self.usable_cash_eur_at_creation < 0:
            raise ValueError(
                "usable_cash_eur_at_creation must be non-negative"
            )
        if (
            self.held_quantity_at_creation is not None
            and self.held_quantity_at_creation < 0
        ):
            raise ValueError("held_quantity_at_creation must be non-negative")
        if self.safe_for_submission:
            raise ValueError(
                "safe_for_submission must be False until the "
                "submission workflow ships (Task 133 product lock §3)"
            )
        if (
            self.submission_block_reason is not None
            and self.submission_block_reason
            not in _LOCKED_SUBMISSION_BLOCK_REASONS
        ):
            raise ValueError(
                f"submission_block_reason "
                f"{self.submission_block_reason!r} not in "
                f"{sorted(_LOCKED_SUBMISSION_BLOCK_REASONS)}"
            )


@dataclass(frozen=True)
class ActionDraftAuditEntry:
    """One row in the append-only ``action_draft_audit`` table.

    Task 133 product lock §8. Mirrors the Decision Package chain pattern:
    every status transition or field edit writes one row carrying
    before/after JSON snapshots so the chain is independently verifiable.
    ``id`` is None on insert (the storage layer issues an autoincrement
    primary key); reads populate it from the row.
    """

    action_draft_id: str
    event_at: datetime
    event_type: str
    before_state_json: dict[str, object] | None
    after_state_json: dict[str, object] | None
    actor: str
    id: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.action_draft_id, "action_draft_id")
        if self.event_type not in _LOCKED_ACTION_DRAFT_EVENT_TYPES:
            raise ValueError(
                f"event_type {self.event_type!r} not in "
                f"{sorted(_LOCKED_ACTION_DRAFT_EVENT_TYPES)}"
            )
        if self.actor not in _LOCKED_ACTION_DRAFT_AUDIT_ACTORS:
            raise ValueError(
                f"actor {self.actor!r} not in "
                f"{sorted(_LOCKED_ACTION_DRAFT_AUDIT_ACTORS)}"
            )


# Task 134 — IBKR submission locked vocabularies.
_LOCKED_SUBMISSION_RESULTS = frozenset(
    {"placed", "rejected_at_send", "connection_lost"}
)
_LOCKED_SUBMISSION_ACCOUNT_MODES = frozenset({"paper", "live"})
_LOCKED_SUBMISSION_LIFECYCLE_EVENTS = frozenset(
    {"status_change", "fill", "commission_report", "cancellation_request"}
)
_LOCKED_SUBMISSION_BLOCK_REASONS = frozenset(
    {
        "cash_insufficient",
        "mode_mismatch",
        "connection_down",
        "account_id_mismatch",
        "duplicate_in_flight",
        "market_closed",
        "cooldown",
        "daily_limit",
        "soft_drawdown",
        "hard_drawdown",
        "fomo",
        "tick_size_invalid",
        "unknown",
    }
)
# Alias retained for documentation; the lifecycle set is now the
# same as ``_LOCKED_ACTION_DRAFT_STATUSES`` after Task 134 widened it.
_LOCKED_ACTION_DRAFT_STATUSES_WITH_LIFECYCLE = frozenset(
    {
        "proposed",
        "edited",
        "user_approved",
        "dismissed",
        "deleted",
        "superseded",
        "submitted",
        "accepted",
        "working",
        "filled",
        "partially_filled",
        "cancelled",
        "rejected",
        "pending_cancellation",
        "awaiting_reply_timeout",
        # Task 135: reconciler escalation path for timeouts older than 24h
        # or terminal-state divergence that needs user attention.
        "requires_manual_review",
    }
)
_LOCKED_IBKR_EXECUTION_SIDES = frozenset({"BUY", "SELL"})


@dataclass(frozen=True)
class IbkrSubmissionAuditEntry:
    """One row in ``ibkr_submission_audit`` — Task 134 lock §5.

    Written by the worker immediately after a ``placeOrder()`` attempt.
    Append-only: the storage layer has no update/delete. ``id`` is
    None on insert (the repo issues an autoincrement primary key) and
    populated on read.
    """

    action_draft_id: str
    submitted_at: datetime
    sent_to_account_id: str
    sent_account_mode: str
    ibkr_perm_id: int | None
    ibkr_order_id: int | None
    contract_json: dict[str, object]
    order_json: dict[str, object]
    gateway_session_id: str
    result: str
    error_class: str | None
    error_message_dutch: str | None
    id: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.action_draft_id, "action_draft_id")
        _require_non_empty(self.sent_to_account_id, "sent_to_account_id")
        _require_non_empty(self.gateway_session_id, "gateway_session_id")
        if self.sent_account_mode not in _LOCKED_SUBMISSION_ACCOUNT_MODES:
            raise ValueError(
                f"sent_account_mode {self.sent_account_mode!r} not in "
                f"{sorted(_LOCKED_SUBMISSION_ACCOUNT_MODES)}"
            )
        if self.result not in _LOCKED_SUBMISSION_RESULTS:
            raise ValueError(
                f"result {self.result!r} not in "
                f"{sorted(_LOCKED_SUBMISSION_RESULTS)}"
            )


@dataclass(frozen=True)
class IbkrSubmissionLifecycleEntry:
    """One row in ``ibkr_submission_lifecycle`` — Task 134 lock §6.

    Written by the worker's lifecycle handler in response to every
    IBKR callback (status change, fill, commission report,
    cancellation request). Append-only; the source of truth for the
    full audit chain of an in-flight draft.
    """

    action_draft_id: str
    event_at: datetime
    ibkr_perm_id: int
    event_type: str
    from_status: str | None
    to_status: str | None
    ibkr_raw_status: str | None
    fill_price_local: Decimal | None
    fill_quantity: Decimal | None
    commission: Decimal | None
    commission_currency: str | None
    raw_callback_json: dict[str, object]
    id: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.action_draft_id, "action_draft_id")
        if self.event_type not in _LOCKED_SUBMISSION_LIFECYCLE_EVENTS:
            raise ValueError(
                f"event_type {self.event_type!r} not in "
                f"{sorted(_LOCKED_SUBMISSION_LIFECYCLE_EVENTS)}"
            )
        for status_field in (self.from_status, self.to_status):
            if (
                status_field is not None
                and status_field
                not in _LOCKED_ACTION_DRAFT_STATUSES_WITH_LIFECYCLE
            ):
                raise ValueError(
                    f"status {status_field!r} not in "
                    f"{sorted(_LOCKED_ACTION_DRAFT_STATUSES_WITH_LIFECYCLE)}"
                )


@dataclass(frozen=True)
class IbkrExecutionEntry:
    """One row in ``ibkr_executions`` — Task 134 lock §7.

    Written exactly once per IBKR fill notification. ``ibkr_exec_id``
    is the natural unique key from IBKR. Append-only; if IBKR
    retracts a fill (rare), the system writes a corrective row rather
    than mutating this one.
    """

    ibkr_exec_id: str
    ibkr_perm_id: int
    action_draft_id: str
    account_id: str
    conid: str
    side: str
    fill_price_local: Decimal
    fill_quantity: Decimal
    fill_time: datetime
    commission: Decimal
    commission_currency: str
    exchange: str
    id: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.ibkr_exec_id, "ibkr_exec_id")
        _require_non_empty(self.action_draft_id, "action_draft_id")
        _require_non_empty(self.account_id, "account_id")
        _require_non_empty(self.conid, "conid")
        _require_non_empty(
            self.commission_currency, "commission_currency"
        )
        _require_non_empty(self.exchange, "exchange")
        if self.side not in _LOCKED_IBKR_EXECUTION_SIDES:
            raise ValueError(
                f"side {self.side!r} not in "
                f"{sorted(_LOCKED_IBKR_EXECUTION_SIDES)}"
            )
        if self.fill_price_local <= 0:
            raise ValueError("fill_price_local must be positive")
        if self.fill_quantity <= 0:
            raise ValueError("fill_quantity must be positive")
        if self.commission < 0:
            raise ValueError("commission must be non-negative")


@dataclass(frozen=True)
class BehaviouralGuardrailSettings:
    """One row in ``behavioural_guardrail_settings`` — Task 134 lock §4.

    Brainstorm-locked default thresholds (60s cool-down, 5/day, 72h/1%
    anti-revenge, 5%/5d soft drawdown, 10%/20d hard drawdown, 1.5%
    FOMO drift) are exposed via ``default_for_account`` so the
    submission sweep can act even before the user has explicitly
    saved per-account settings. The UI to edit them ships in Task 138.
    """

    ibkr_account_id: str
    daily_max_approvals: int
    cooldown_seconds: int
    anti_revenge_window_hours: int
    anti_revenge_loss_threshold_pct: Decimal
    soft_drawdown_pct: Decimal
    soft_drawdown_window_days: int
    hard_drawdown_pct: Decimal
    hard_drawdown_window_days: int
    fomo_drift_pct: Decimal
    last_updated_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty(self.ibkr_account_id, "ibkr_account_id")
        if self.daily_max_approvals <= 0:
            raise ValueError("daily_max_approvals must be positive")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        if self.anti_revenge_window_hours < 0:
            raise ValueError(
                "anti_revenge_window_hours must be non-negative"
            )
        if self.anti_revenge_loss_threshold_pct < 0:
            raise ValueError(
                "anti_revenge_loss_threshold_pct must be non-negative"
            )
        if self.soft_drawdown_pct < 0:
            raise ValueError("soft_drawdown_pct must be non-negative")
        if self.soft_drawdown_window_days < 0:
            raise ValueError(
                "soft_drawdown_window_days must be non-negative"
            )
        if self.hard_drawdown_pct < 0:
            raise ValueError("hard_drawdown_pct must be non-negative")
        if self.hard_drawdown_window_days < 0:
            raise ValueError(
                "hard_drawdown_window_days must be non-negative"
            )
        if self.fomo_drift_pct < 0:
            raise ValueError("fomo_drift_pct must be non-negative")

    @classmethod
    def default_for_account(
        cls,
        *,
        ibkr_account_id: str,
        last_updated_at: datetime,
    ) -> BehaviouralGuardrailSettings:
        """Brainstorm-locked defaults, mirroring the migration server_default."""

        return cls(
            ibkr_account_id=ibkr_account_id,
            daily_max_approvals=5,
            cooldown_seconds=60,
            anti_revenge_window_hours=72,
            anti_revenge_loss_threshold_pct=Decimal("1.0"),
            soft_drawdown_pct=Decimal("5.0"),
            soft_drawdown_window_days=5,
            hard_drawdown_pct=Decimal("10.0"),
            hard_drawdown_window_days=20,
            fomo_drift_pct=Decimal("1.5"),
            last_updated_at=last_updated_at,
        )


# Task 135 — Reconciliation locked vocabularies.
_LOCKED_RECONCILIATION_PASS_NAMES = frozenset(
    {"orphaned_execution", "stale_in_flight", "timeout_recovery"}
)
_LOCKED_RECONCILIATION_DIVERGENCE_TYPES = frozenset(
    {
        "missing_execution_applied",
        "status_corrected_to_filled",
        "status_corrected_to_cancelled",
        "status_corrected_to_rejected",
        "status_corrected_to_partially_filled",
        "timeout_recovered_to_terminal",
        "timeout_flagged_manual_review",
        "unmatched_execution",
        "terminal_state_divergence_logged",
    }
)
_LOCKED_UNMATCHED_EXECUTION_RESOLUTIONS = frozenset(
    {"unresolved", "manually_matched", "ignored"}
)
_LOCKED_MANUAL_REVIEW_REASONS = frozenset(
    {
        "timeout_24h_no_data",
        "terminal_state_divergence",
        "unmatched_execution_no_draft",
    }
)
_LOCKED_MANUAL_REVIEW_RESOLUTIONS = frozenset(
    {"pending", "resolved", "acknowledged"}
)
_LOCKED_RECONCILIATION_RUN_MODES = frozenset(
    {"completed", "skipped_locked", "skipped_disconnected", "error"}
)


@dataclass(frozen=True)
class ReconciliationAuditEntry:
    """One row in ``reconciliation_audit`` — Task 135 product lock §6.

    Written by the reconciler whenever a pass detects a divergence and
    applies (or logs) a heal. Append-only; the ``ibkr_evidence_json``
    field captures the raw IBKR response that justified the action so
    every audit row is independently verifiable.
    """

    reconciliation_run_id: str
    action_draft_id: str | None
    event_at: datetime
    pass_name: str
    divergence_type: str
    before_status: str | None
    after_status: str | None
    ibkr_evidence_json: dict[str, object]
    notes_dutch: str | None
    id: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty(
            self.reconciliation_run_id, "reconciliation_run_id"
        )
        if self.pass_name not in _LOCKED_RECONCILIATION_PASS_NAMES:
            raise ValueError(
                f"pass_name {self.pass_name!r} not in "
                f"{sorted(_LOCKED_RECONCILIATION_PASS_NAMES)}"
            )
        if (
            self.divergence_type
            not in _LOCKED_RECONCILIATION_DIVERGENCE_TYPES
        ):
            raise ValueError(
                f"divergence_type {self.divergence_type!r} not in "
                f"{sorted(_LOCKED_RECONCILIATION_DIVERGENCE_TYPES)}"
            )


@dataclass(frozen=True)
class UnmatchedExecutionAuditEntry:
    """One row in ``unmatched_execution_audit`` — Task 135 lock §3 Pass A.

    Written when the reconciler finds an IBKR execution whose
    ``ibkr_perm_id`` doesn't match any draft in the system (typically
    a user-placed-in-TWS order during the worker's offline window).
    UNIQUE on ``ibkr_exec_id`` so duplicate detections are idempotent.
    """

    event_at: datetime
    ibkr_perm_id: int
    ibkr_exec_id: str
    account_id: str
    conid: str
    side: str
    fill_price_local: Decimal
    fill_quantity: Decimal
    fill_time: datetime
    raw_execution_json: dict[str, object]
    resolution_status: str = "unresolved"
    id: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.ibkr_exec_id, "ibkr_exec_id")
        _require_non_empty(self.account_id, "account_id")
        _require_non_empty(self.conid, "conid")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError(
                f"side {self.side!r} must be BUY or SELL"
            )
        if self.fill_price_local <= 0:
            raise ValueError("fill_price_local must be positive")
        if self.fill_quantity <= 0:
            raise ValueError("fill_quantity must be positive")
        if (
            self.resolution_status
            not in _LOCKED_UNMATCHED_EXECUTION_RESOLUTIONS
        ):
            raise ValueError(
                f"resolution_status {self.resolution_status!r} not in "
                f"{sorted(_LOCKED_UNMATCHED_EXECUTION_RESOLUTIONS)}"
            )


@dataclass(frozen=True)
class ManualReviewQueueEntry:
    """One row in ``manual_review_queue`` — Task 135 product lock §3 Pass C.

    Flagged when the reconciler can't heal a divergence automatically
    (24h timeout, terminal-state mismatch, or unmatched execution
    without a matching draft). The user resolves these via the API.
    """

    flagged_at: datetime
    action_draft_id: str
    reason: str
    details_dutch: str
    resolution_status: str = "pending"
    resolved_at: datetime | None = None
    resolution_note: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.action_draft_id, "action_draft_id")
        _require_non_empty(self.details_dutch, "details_dutch")
        if self.reason not in _LOCKED_MANUAL_REVIEW_REASONS:
            raise ValueError(
                f"reason {self.reason!r} not in "
                f"{sorted(_LOCKED_MANUAL_REVIEW_REASONS)}"
            )
        if (
            self.resolution_status
            not in _LOCKED_MANUAL_REVIEW_RESOLUTIONS
        ):
            raise ValueError(
                f"resolution_status {self.resolution_status!r} not in "
                f"{sorted(_LOCKED_MANUAL_REVIEW_RESOLUTIONS)}"
            )


@dataclass(frozen=True)
class ReconciliationRunAuditEntry:
    """One row in ``reconciliation_run_audit`` — Task 135 lock §6.

    One per reconciler tick; ``completed_at`` is None until the tick
    finishes. Per-pass counts let the dashboard widget surface the
    "healed in last 24h" headline.
    """

    reconciliation_run_id: str
    started_at: datetime
    completed_at: datetime | None
    account_id: str
    pass_a_orphaned_count: int
    pass_b_stale_count: int
    pass_c_timeout_count: int
    divergences_found: int
    mode_detected: str
    error_details_json: dict[str, object] | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty(
            self.reconciliation_run_id, "reconciliation_run_id"
        )
        _require_non_empty(self.account_id, "account_id")
        if self.mode_detected not in _LOCKED_RECONCILIATION_RUN_MODES:
            raise ValueError(
                f"mode_detected {self.mode_detected!r} not in "
                f"{sorted(_LOCKED_RECONCILIATION_RUN_MODES)}"
            )
        if self.pass_a_orphaned_count < 0:
            raise ValueError("pass_a_orphaned_count must be non-negative")
        if self.pass_b_stale_count < 0:
            raise ValueError("pass_b_stale_count must be non-negative")
        if self.pass_c_timeout_count < 0:
            raise ValueError("pass_c_timeout_count must be non-negative")
        if self.divergences_found < 0:
            raise ValueError("divergences_found must be non-negative")


class BootstrapInsufficientHistoryError(RuntimeError):
    """Raised when the bootstrap input doesn't have ≥200 daily closes."""
