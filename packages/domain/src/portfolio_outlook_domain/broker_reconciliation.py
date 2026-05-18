from datetime import datetime
from decimal import Decimal

from pydantic import model_validator

from .enums import (
    BrokerAccountMode,
    BrokerActivityOrigin,
    BrokerConnectionStatus,
    BrokerDataKind,
    BrokerSourceOfTruthStatus,
    BrokerSuggestionPolicy,
    BrokerSyncMode,
    BrokerSystem,
    IBKRDataSourceType,
    ReconciliationDifferenceKind,
    ReconciliationSeverity,
    ReconciliationStatus,
)
from .identifiers import (
    AuditEventId,
    BrokerAccountId,
    BrokerCashSnapshotId,
    BrokerCommissionSnapshotId,
    BrokerExecutionSnapshotId,
    BrokerPositionSnapshotId,
    BrokerReconciliationDifferenceId,
    BrokerReconciliationReportId,
    BrokerSnapshotId,
    BrokerSyncRunId,
    ExternalBrokerActivityId,
    SourceReferenceId,
)
from .primitives import DomainBaseModel


class BrokerSourceOfTruthPolicy(DomainBaseModel):
    broker_system: BrokerSystem
    source_of_truth_status: BrokerSourceOfTruthStatus
    ibkr_is_authoritative_for_broker_facts: bool
    local_system_is_authoritative_for_suggestions: bool
    local_system_is_authoritative_for_approvals: bool
    local_system_is_authoritative_for_explanations: bool
    no_silent_correction: bool
    title_nl: str
    summary_nl: str
    help_nl: str

    @model_validator(mode="after")
    def validate_policy(self) -> "BrokerSourceOfTruthPolicy":
        if (
            self.broker_system is not BrokerSystem.IBKR
            or not self.ibkr_is_authoritative_for_broker_facts
        ):
            raise ValueError("IBKR must be authoritative for broker facts.")
        if not self.local_system_is_authoritative_for_suggestions:
            raise ValueError("Local suggestions authority must be true.")
        if not self.local_system_is_authoritative_for_approvals:
            raise ValueError("Local approvals authority must be true.")
        if not self.local_system_is_authoritative_for_explanations:
            raise ValueError("Local explanations authority must be true.")
        if not self.no_silent_correction:
            raise ValueError("Silent correction is not allowed.")
        return self


class BrokerAccountIdentity(DomainBaseModel):
    broker_account_id: BrokerAccountId
    broker_system: BrokerSystem
    account_mode: BrokerAccountMode
    connection_status: BrokerConnectionStatus
    source_reference_ids: list[SourceReferenceId]
    label_nl: str
    help_nl: str
    configured: bool
    paper_account: bool
    live_trading_allowed: bool

    @model_validator(mode="after")
    def validate_identity(self) -> "BrokerAccountIdentity":
        if self.broker_system is not BrokerSystem.IBKR or self.live_trading_allowed:
            raise ValueError("Only paper-safe IBKR identity is allowed.")
        if self.connection_status is BrokerConnectionStatus.NOT_CONFIGURED and self.configured:
            raise ValueError("Not configured connection cannot be configured=true.")
        if not self.configured and self.connection_status not in {
            BrokerConnectionStatus.NOT_CONFIGURED,
            BrokerConnectionStatus.DISCONNECTED,
            BrokerConnectionStatus.BLOCKED,
        }:
            raise ValueError("Unconfigured account must have a safe status.")
        return self


class BrokerSyncPlan(DomainBaseModel):
    broker_sync_run_id: BrokerSyncRunId
    broker_account_id: BrokerAccountId | None
    broker_system: BrokerSystem
    sync_mode: BrokerSyncMode
    planned_data_kinds: list[BrokerDataKind]
    data_source_types: list[IBKRDataSourceType]
    requires_ibkr_configuration: bool
    requires_broker_session: bool
    blocks_suggestions_until_complete: bool
    title_nl: str
    summary_nl: str
    help_nl: str

    @model_validator(mode="after")
    def validate_sync_plan(self) -> "BrokerSyncPlan":
        if self.broker_system is not BrokerSystem.IBKR:
            raise ValueError("Only IBKR sync plans are supported.")
        if self.sync_mode is BrokerSyncMode.NOT_CONFIGURED:
            if not self.requires_ibkr_configuration:
                raise ValueError("not_configured sync mode must require IBKR configuration.")
        else:
            if not self.planned_data_kinds or not self.data_source_types:
                raise ValueError("Configured sync plans need data kinds and source types.")
        return self


class BrokerPositionSnapshot(DomainBaseModel):
    broker_position_snapshot_id: BrokerPositionSnapshotId
    broker_snapshot_id: BrokerSnapshotId
    broker_account_id: BrokerAccountId
    broker_system: BrokerSystem
    imported_at: datetime
    asset_identifier: str
    asset_symbol: str
    asset_type: str
    currency: str
    quantity: Decimal
    average_cost: Decimal | None
    market_value: Decimal | None
    source_data_kind: BrokerDataKind
    origin: BrokerActivityOrigin
    source_reference_ids: list[SourceReferenceId]
    explanation_nl: str


class BrokerCashBalanceSnapshot(DomainBaseModel):
    broker_cash_snapshot_id: BrokerCashSnapshotId
    broker_snapshot_id: BrokerSnapshotId
    broker_account_id: BrokerAccountId
    broker_system: BrokerSystem
    imported_at: datetime
    currency: str
    cash_amount: Decimal
    source_data_kind: BrokerDataKind
    origin: BrokerActivityOrigin
    source_reference_ids: list[SourceReferenceId]
    explanation_nl: str


class BrokerExecutionSnapshot(DomainBaseModel):
    broker_execution_snapshot_id: BrokerExecutionSnapshotId
    broker_snapshot_id: BrokerSnapshotId
    broker_account_id: BrokerAccountId
    broker_system: BrokerSystem
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
    origin: BrokerActivityOrigin
    source_reference_ids: list[SourceReferenceId]
    explanation_nl: str


class BrokerCommissionSnapshot(DomainBaseModel):
    broker_commission_snapshot_id: BrokerCommissionSnapshotId
    broker_snapshot_id: BrokerSnapshotId
    broker_account_id: BrokerAccountId
    broker_system: BrokerSystem
    imported_at: datetime
    execution_id: str
    commission_amount: Decimal
    currency: str
    realized_pnl: Decimal | None
    source_reference_ids: list[SourceReferenceId]
    explanation_nl: str


class ExternalBrokerActivity(DomainBaseModel):
    external_broker_activity_id: ExternalBrokerActivityId
    broker_account_id: BrokerAccountId
    broker_system: BrokerSystem
    detected_at: datetime
    origin: BrokerActivityOrigin
    data_kind: BrokerDataKind
    related_execution_id: str | None
    related_asset_identifier: str | None
    summary_nl: str
    help_nl: str
    source_reference_ids: list[SourceReferenceId]
    audit_event_ids: list[AuditEventId]


class BrokerReconciliationDifference(DomainBaseModel):
    broker_reconciliation_difference_id: BrokerReconciliationDifferenceId
    difference_kind: ReconciliationDifferenceKind
    severity: ReconciliationSeverity
    broker_account_id: BrokerAccountId
    broker_system: BrokerSystem
    detected_at: datetime
    broker_value: str | None
    local_value: str | None
    asset_identifier: str | None
    currency: str | None
    blocks_suggestions: bool
    requires_manual_review: bool
    summary_nl: str
    help_nl: str
    source_reference_ids: list[SourceReferenceId]
    audit_event_ids: list[AuditEventId]

    @model_validator(mode="after")
    def validate_difference(self) -> "BrokerReconciliationDifference":
        if self.severity in {ReconciliationSeverity.BLOCKING, ReconciliationSeverity.CRITICAL}:
            if not self.blocks_suggestions:
                raise ValueError("Blocking and critical differences must block suggestions.")
        return self


class BrokerReconciliationReport(DomainBaseModel):
    broker_reconciliation_report_id: BrokerReconciliationReportId
    broker_sync_run_id: BrokerSyncRunId
    broker_account_id: BrokerAccountId | None
    broker_system: BrokerSystem
    status: ReconciliationStatus
    differences: list[BrokerReconciliationDifference]
    checked_at: datetime
    source_of_truth_policy: BrokerSourceOfTruthPolicy
    suggestion_policy: BrokerSuggestionPolicy
    can_create_suggestions: bool
    can_create_orders: bool
    title_nl: str
    summary_nl: str
    help_nl: str

    @model_validator(mode="after")
    def validate_report(self) -> "BrokerReconciliationReport":
        if self.can_create_orders:
            raise ValueError("can_create_orders must stay false in paper mode.")
        if self.status is ReconciliationStatus.CLEAN and self.differences:
            raise ValueError("Clean status must not include differences.")
        if (
            self.status
            in {
                ReconciliationStatus.DIFFERENCES_FOUND,
                ReconciliationStatus.MANUAL_REVIEW_REQUIRED,
            }
            and not self.differences
        ):
            raise ValueError("Differences are required for this status.")
        if (
            has_blocking_reconciliation_differences(self.differences)
            and self.can_create_suggestions
        ):
            raise ValueError("Blocking differences cannot allow suggestions.")
        return self

def build_ibkr_source_of_truth_policy() -> BrokerSourceOfTruthPolicy:
    return BrokerSourceOfTruthPolicy(
        broker_system=BrokerSystem.IBKR,
        source_of_truth_status=BrokerSourceOfTruthStatus.BROKER_AUTHORITATIVE,
        ibkr_is_authoritative_for_broker_facts=True,
        local_system_is_authoritative_for_suggestions=True,
        local_system_is_authoritative_for_approvals=True,
        local_system_is_authoritative_for_explanations=True,
        no_silent_correction=True,
        title_nl="Bron van waarheid",
        summary_nl="IBKR is leidend voor brokerfeiten.",
        help_nl=(
            "IBKR is de bron van waarheid voor cash, posities en uitgevoerde transacties. "
            "AI-Trading-Agent bewaart later een lokale kopie voor analyse en audit."
        ),
    )


def build_not_configured_broker_account_identity() -> BrokerAccountIdentity:
    return BrokerAccountIdentity(
        broker_account_id="ibkr_not_configured",
        broker_system=BrokerSystem.IBKR,
        account_mode=BrokerAccountMode.UNKNOWN,
        connection_status=BrokerConnectionStatus.NOT_CONFIGURED,
        source_reference_ids=[],
        label_nl="IBKR account",
        help_nl=(
            "IBKR is nog niet ingesteld. "
            "Het systeem kan daarom nog geen brokerposities of cash synchroniseren."
        ),
        configured=False,
        paper_account=False,
        live_trading_allowed=False,
    )


def build_not_configured_broker_sync_plan() -> BrokerSyncPlan:
    return BrokerSyncPlan(
        broker_sync_run_id="broker_sync_not_configured",
        broker_account_id=None,
        broker_system=BrokerSystem.IBKR,
        sync_mode=BrokerSyncMode.NOT_CONFIGURED,
        planned_data_kinds=[],
        data_source_types=[],
        requires_ibkr_configuration=True,
        requires_broker_session=False,
        blocks_suggestions_until_complete=True,
        title_nl="IBKR synchronisatie",
        summary_nl="Nog niet ingesteld.",
        help_nl=(
            "Na het instellen van IBKR kan het systeem later cash, "
            "posities en uitvoeringen synchroniseren."
        ),
    )


def build_empty_reconciliation_report(
    *,
    broker_sync_run_id: BrokerSyncRunId,
    checked_at: datetime,
) -> BrokerReconciliationReport:
    return BrokerReconciliationReport(
        broker_reconciliation_report_id="broker_reconciliation_not_available",
        broker_sync_run_id=broker_sync_run_id,
        broker_account_id=None,
        broker_system=BrokerSystem.IBKR,
        status=ReconciliationStatus.NOT_AVAILABLE,
        differences=[],
        checked_at=checked_at,
        source_of_truth_policy=build_ibkr_source_of_truth_policy(),
        suggestion_policy=BrokerSuggestionPolicy.BLOCK_UNTIL_IBKR_CONFIGURED,
        can_create_suggestions=False,
        can_create_orders=False,
        title_nl="Reconciliatie",
        summary_nl="Nog niet beschikbaar.",
        help_nl="IBKR is nog niet ingesteld. Daarom is brokerreconciliatie nog niet beschikbaar.",
    )


def has_blocking_reconciliation_differences(
    differences: list[BrokerReconciliationDifference],
) -> bool:
    return any(
        diff.blocks_suggestions
        or diff.severity
        in {ReconciliationSeverity.BLOCKING, ReconciliationSeverity.CRITICAL}
        for diff in differences
    )


def reconciliation_blocks_suggestions(report: BrokerReconciliationReport) -> bool:
    if report.status in {
        ReconciliationStatus.BLOCKED,
        ReconciliationStatus.FAILED,
        ReconciliationStatus.DIFFERENCES_FOUND,
        ReconciliationStatus.MANUAL_REVIEW_REQUIRED,
        ReconciliationStatus.NOT_AVAILABLE,
    }:
        return True
    if has_blocking_reconciliation_differences(report.differences):
        return True
    return report.suggestion_policy.value.startswith("block") or not (
        report.status is ReconciliationStatus.CLEAN and report.can_create_suggestions
    )


def classify_external_broker_activity_from_difference(
    difference: BrokerReconciliationDifference,
    *,
    external_broker_activity_id: ExternalBrokerActivityId,
) -> ExternalBrokerActivity:
    return ExternalBrokerActivity(
        external_broker_activity_id=external_broker_activity_id,
        broker_account_id=difference.broker_account_id,
        broker_system=difference.broker_system,
        detected_at=difference.detected_at,
        origin=BrokerActivityOrigin.DIRECT_IBKR_ORDER,
        data_kind=BrokerDataKind.OTHER,
        related_execution_id=None,
        related_asset_identifier=difference.asset_identifier,
        summary_nl="Rechtstreeks in IBKR uitgevoerd.",
        help_nl="Er is externe brokeractiviteit gevonden. Controleer het verschil handmatig.",
        source_reference_ids=difference.source_reference_ids,
        audit_event_ids=difference.audit_event_ids,
    )
