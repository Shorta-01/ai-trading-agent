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

    V1 scope (locked in `version-1-product-experience-locks.md §10` and
    `release-1-functional-workflow-blueprint.md §10`):

    * stocks/ETFs only, whole shares only
    * ``order_type == "LMT"`` only
    * ``tif == "DAY"`` only
    * ``action_side`` is ``"BUY"`` or ``"SELL"``

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
        if self.order_type != "LMT":
            raise ValueError(
                "V1 action-drafts only support LMT order_type."
            )
        if self.tif != "DAY":
            raise ValueError("V1 action-drafts only support DAY tif.")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive.")
        if self.limit_price <= 0:
            raise ValueError("limit_price must be positive.")
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
