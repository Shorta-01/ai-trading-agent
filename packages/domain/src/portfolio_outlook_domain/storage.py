from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from .enums import (
    BackupStatus,
    PersistedEntityKind,
    PersistenceMode,
    RestoreCheckStatus,
    RetentionCategory,
    StorageBackendKind,
    StorageBackendStatus,
    StorageBlockReason,
    StorageReadinessStatus,
    StorageSensitivity,
    StorageWarningReason,
)
from .identifiers import (
    BackupPlanId,
    PersistedRecordReferenceId,
    RestoreCheckId,
    StorageBackendId,
    StorageMigrationPlanId,
    StorageProfileId,
    StorageReadinessCheckId,
    StorageRetentionPolicyId,
    StorageSchemaVersionId,
)


class StorageBackendDefinition(BaseModel):
    storage_backend_id: StorageBackendId
    backend_kind: StorageBackendKind
    status: StorageBackendStatus
    persistence_mode: PersistenceMode
    label_nl: str = Field(min_length=1)
    help_nl: str = Field(min_length=1)
    stores_sensitive_data: bool
    stores_secret_values: bool
    enabled: bool

    @model_validator(mode="after")
    def validate_backend(self) -> "StorageBackendDefinition":
        if self.stores_secret_values:
            raise ValueError("Secret values mogen niet in opslagbackends staan.")
        if self.backend_kind is StorageBackendKind.NOT_CONFIGURED:
            if self.enabled:
                raise ValueError("Niet geconfigureerde backend mag niet enabled zijn.")
            if self.status is not StorageBackendStatus.NOT_CONFIGURED:
                raise ValueError("Niet geconfigureerde backend moet status not_configured hebben.")
            if self.persistence_mode not in {PersistenceMode.NOT_AVAILABLE, PersistenceMode.DISABLED}:
                raise ValueError("Niet geconfigureerde backend heeft ongeldige persistence mode.")
        if self.enabled:
            if self.backend_kind is StorageBackendKind.NOT_CONFIGURED:
                raise ValueError("Enabled backend moet geconfigureerd type hebben.")
            if self.status is StorageBackendStatus.NOT_CONFIGURED:
                raise ValueError("Enabled backend mag geen not_configured status hebben.")
        return self


class StorageSchemaVersion(BaseModel):
    storage_schema_version_id: StorageSchemaVersionId
    version_label: str = Field(min_length=1)
    applied: bool
    planned: bool
    created_at: datetime
    description_nl: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_flags(self) -> "StorageSchemaVersion":
        if self.applied and self.planned:
            raise ValueError("Schema versie kan niet tegelijk applied en planned zijn.")
        return self


class StorageMigrationPlan(BaseModel):
    storage_migration_plan_id: StorageMigrationPlanId
    from_version: str | None = None
    to_version: str = Field(min_length=1)
    required: bool
    safe_to_apply_automatically: bool
    requires_backup_first: bool
    description_nl: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_migration(self) -> "StorageMigrationPlan":
        if self.safe_to_apply_automatically and not self.requires_backup_first:
            raise ValueError("Automatische migratie vereist eerst backup.")
        return self


class StorageRetentionPolicy(BaseModel):
    storage_retention_policy_id: StorageRetentionPolicyId
    entity_kind: PersistedEntityKind
    retention_category: RetentionCategory
    immutable_required: bool
    explanation_nl: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_policy(self) -> "StorageRetentionPolicy":
        if self.entity_kind is PersistedEntityKind.AUDIT_EVENT:
            if self.retention_category is not RetentionCategory.AUDIT_LIFETIME:
                raise ValueError("Audit events vereisen audit_lifetime.")
            if not self.immutable_required:
                raise ValueError("Audit events moeten immutable zijn.")
        if self.entity_kind is PersistedEntityKind.TAX_RECORD:
            if self.retention_category is not RetentionCategory.TAX_LIFETIME:
                raise ValueError("Tax records vereisen tax_lifetime.")
        return self


class PersistedRecordReference(BaseModel):
    persisted_record_reference_id: PersistedRecordReferenceId
    entity_kind: PersistedEntityKind
    storage_backend_id: StorageBackendId
    record_key: str = Field(min_length=1)
    created_at: datetime
    sensitivity: StorageSensitivity
    explanation_nl: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_reference(self) -> "PersistedRecordReference":
        if self.sensitivity is StorageSensitivity.PROHIBITED_SECRET_VALUE:
            raise ValueError("Geheime waarden mogen niet als normaal record worden opgeslagen.")
        return self


class BackupPlan(BaseModel):
    backup_plan_id: BackupPlanId
    status: BackupStatus
    encrypted_required: bool
    restore_test_required: bool
    target_description_nl: str = Field(min_length=1)
    explanation_nl: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_backup(self) -> "BackupPlan":
        if not self.encrypted_required:
            raise ValueError("Backups moeten versleuteld verplichten.")
        if not self.restore_test_required:
            raise ValueError("Restore test moet verplicht zijn.")
        return self


class RestoreCheck(BaseModel):
    restore_check_id: RestoreCheckId
    backup_plan_id: BackupPlanId
    status: RestoreCheckStatus
    checked_at: datetime | None = None
    message_nl: str = Field(min_length=1)
    blocks_persistence: bool

    @model_validator(mode="after")
    def validate_restore(self) -> "RestoreCheck":
        if self.status is RestoreCheckStatus.PASSED:
            if self.checked_at is None or self.blocks_persistence:
                raise ValueError("Passed restore check vereist checked_at en mag niet blokkeren.")
        if self.status in {RestoreCheckStatus.FAILED, RestoreCheckStatus.BLOCKED}:
            if not self.blocks_persistence:
                raise ValueError("Failed/blocked restore check moet persistence blokkeren.")
        return self


class StorageReadinessCheck(BaseModel):
    storage_readiness_check_id: StorageReadinessCheckId
    status: StorageReadinessStatus
    backends: list[StorageBackendDefinition]
    schema_versions: list[StorageSchemaVersion]
    migration_plans: list[StorageMigrationPlan]
    backup_plan: BackupPlan | None = None
    restore_checks: list[RestoreCheck]
    block_reasons: list[StorageBlockReason]
    warning_reasons: list[StorageWarningReason]
    checked_at: datetime
    can_persist_paper_setup: bool
    can_persist_transactions: bool
    can_persist_audit_events: bool
    title_nl: str = Field(min_length=1)
    summary_nl: str = Field(min_length=1)
    help_nl: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_readiness(self) -> "StorageReadinessCheck":
        if self.status is StorageReadinessStatus.READY_FOR_PERSISTENCE:
            if self.block_reasons:
                raise ValueError("Ready_for_persistence mag geen block reasons hebben.")
            if not self.can_persist_paper_setup or not self.can_persist_audit_events:
                raise ValueError("Ready_for_persistence vereist setup en audit persistence.")
            if self.backup_plan is None:
                raise ValueError("Ready_for_persistence vereist backup plan.")
        if self.block_reasons and self.status not in {
            StorageReadinessStatus.BLOCKED,
            StorageReadinessStatus.FAILED,
            StorageReadinessStatus.NOT_READY,
        }:
            raise ValueError("Block reasons vereisen blocked/failed/not_ready status.")
        if self.can_persist_transactions and not self.can_persist_audit_events:
            raise ValueError("Transacties vereisen audit persistence.")
        if self.can_persist_paper_setup and not self.can_persist_audit_events:
            raise ValueError("Setup persistence vereist audit persistence.")
        return self


class StorageProfile(BaseModel):
    storage_profile_id: StorageProfileId
    profile_name: str = Field(min_length=1)
    backends: list[StorageBackendDefinition]
    retention_policies: list[StorageRetentionPolicy]
    backup_plan: BackupPlan | None = None
    created_at: datetime
    explanation_nl: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_profile(self) -> "StorageProfile":
        if not self.backends:
            raise ValueError("Backends mogen niet leeg zijn.")
        backend_ids = [backend.storage_backend_id for backend in self.backends]
        if len(backend_ids) != len(set(backend_ids)):
            raise ValueError("storage_backend_id moet uniek zijn.")
        if any(backend.stores_secret_values for backend in self.backends):
            raise ValueError("Geen backend mag secret values opslaan.")
        if not self.retention_policies:
            raise ValueError("retention_policies mogen niet leeg zijn.")
        return self


def build_default_storage_profile(*, created_at: datetime) -> StorageProfile:
    backends = [
        StorageBackendDefinition(storage_backend_id="postgres_structured", backend_kind=StorageBackendKind.POSTGRES, status=StorageBackendStatus.PLANNED, persistence_mode=PersistenceMode.NOT_AVAILABLE, label_nl="PostgreSQL", help_nl="Toekomstige opslag voor gestructureerde portefeuillegegevens.", stores_sensitive_data=True, stores_secret_values=False, enabled=False),
        StorageBackendDefinition(storage_backend_id="timescaledb_series", backend_kind=StorageBackendKind.TIMESCALEDB, status=StorageBackendStatus.PLANNED, persistence_mode=PersistenceMode.NOT_AVAILABLE, label_nl="TimescaleDB", help_nl="Toekomstige opslag voor tijdreeksen en metingen.", stores_sensitive_data=True, stores_secret_values=False, enabled=False),
        StorageBackendDefinition(storage_backend_id="immutable_raw_archive", backend_kind=StorageBackendKind.IMMUTABLE_ARCHIVE, status=StorageBackendStatus.PLANNED, persistence_mode=PersistenceMode.NOT_AVAILABLE, label_nl="Raw data archief", help_nl="Toekomstig immutable archief van ruwe brondata.", stores_sensitive_data=True, stores_secret_values=False, enabled=False),
        StorageBackendDefinition(storage_backend_id="research_archive", backend_kind=StorageBackendKind.RESEARCH_ARCHIVE, status=StorageBackendStatus.PLANNED, persistence_mode=PersistenceMode.NOT_AVAILABLE, label_nl="Research archief", help_nl="Toekomstige opslag van AI-onderzoek en bronverwijzingen.", stores_sensitive_data=True, stores_secret_values=False, enabled=False),
        StorageBackendDefinition(storage_backend_id="audit_log_append_only", backend_kind=StorageBackendKind.AUDIT_LOG, status=StorageBackendStatus.PLANNED, persistence_mode=PersistenceMode.NOT_AVAILABLE, label_nl="Auditlog", help_nl="Toekomstige append-only auditlog met hash-ready sporen.", stores_sensitive_data=True, stores_secret_values=False, enabled=False),
    ]
    policy_pairs = [
        ("paper_setup", PersistedEntityKind.PAPER_SETUP, RetentionCategory.PORTFOLIO_LIFETIME, False),
        ("paper_cash_account", PersistedEntityKind.PAPER_CASH_ACCOUNT, RetentionCategory.PORTFOLIO_LIFETIME, False),
        ("paper_transaction", PersistedEntityKind.PAPER_TRANSACTION, RetentionCategory.PORTFOLIO_LIFETIME, False),
        ("position_lot", PersistedEntityKind.POSITION_LOT, RetentionCategory.PORTFOLIO_LIFETIME, False),
        ("action_suggestion", PersistedEntityKind.ACTION_SUGGESTION, RetentionCategory.PORTFOLIO_LIFETIME, False),
        ("approval_decision", PersistedEntityKind.APPROVAL_DECISION, RetentionCategory.AUDIT_LIFETIME, True),
        ("source_reference", PersistedEntityKind.SOURCE_REFERENCE, RetentionCategory.RESEARCH_ARCHIVE, True),
        ("ai_research_record", PersistedEntityKind.AI_RESEARCH_RECORD, RetentionCategory.RESEARCH_ARCHIVE, True),
        ("data_quality_check", PersistedEntityKind.DATA_QUALITY_CHECK, RetentionCategory.AUDIT_LIFETIME, True),
        ("scheduler_job_run", PersistedEntityKind.SCHEDULER_JOB_RUN, RetentionCategory.AUDIT_LIFETIME, True),
        ("settings_profile", PersistedEntityKind.SETTINGS_PROFILE, RetentionCategory.USER_CONFIG, False),
        ("api_usage_summary", PersistedEntityKind.API_USAGE_SUMMARY, RetentionCategory.SHORT_TERM_OPERATIONAL, False),
        ("audit_event", PersistedEntityKind.AUDIT_EVENT, RetentionCategory.AUDIT_LIFETIME, True),
        ("tax_record", PersistedEntityKind.TAX_RECORD, RetentionCategory.TAX_LIFETIME, False),
    ]
    retention_policies = [
        StorageRetentionPolicy(
            storage_retention_policy_id=f"retention_{name}",
            entity_kind=kind,
            retention_category=category,
            immutable_required=immutable_required,
            explanation_nl="Bewaarbeleid voor deze recordsoort.",
        )
        for name, kind, category, immutable_required in policy_pairs
    ]
    return StorageProfile(
        storage_profile_id="default_storage_profile",
        profile_name="Standaard opslagprofiel",
        backends=backends,
        retention_policies=retention_policies,
        backup_plan=None,
        created_at=created_at,
        explanation_nl="Opslag is voorbereid maar nog niet ingesteld.",
    )


def build_not_ready_storage_check(*, checked_at: datetime) -> StorageReadinessCheck:
    return StorageReadinessCheck(
        storage_readiness_check_id="storage_check_not_ready",
        status=StorageReadinessStatus.NOT_READY,
        backends=build_default_storage_profile(created_at=checked_at).backends,
        schema_versions=[],
        migration_plans=[],
        backup_plan=None,
        restore_checks=[],
        block_reasons=[StorageBlockReason.BACKEND_NOT_CONFIGURED, StorageBlockReason.AUDIT_STORAGE_MISSING],
        warning_reasons=[StorageWarningReason.PREVIEW_ONLY, StorageWarningReason.BACKUP_NOT_TESTED],
        checked_at=checked_at,
        can_persist_paper_setup=False,
        can_persist_transactions=False,
        can_persist_audit_events=False,
        title_nl="Opslagstatus",
        summary_nl="Opslag is nog niet ingesteld.",
        help_nl="Portefeuilledata blijft voorlopig preview en wordt niet opgeslagen.",
    )


def storage_allows_paper_setup_persistence(check: StorageReadinessCheck) -> bool:
    return (
        check.status is StorageReadinessStatus.READY_FOR_PERSISTENCE
        and check.can_persist_paper_setup
        and check.can_persist_audit_events
        and not check.block_reasons
    )


def storage_allows_transaction_persistence(check: StorageReadinessCheck) -> bool:
    return (
        check.status is StorageReadinessStatus.READY_FOR_PERSISTENCE
        and check.can_persist_transactions
        and check.can_persist_audit_events
        and not check.block_reasons
    )


def storage_blocks_persistence(check: StorageReadinessCheck) -> bool:
    if check.status in {StorageReadinessStatus.BLOCKED, StorageReadinessStatus.FAILED, StorageReadinessStatus.NOT_READY}:
        return True
    return bool(check.block_reasons)


def backup_restore_trusted(*, backup_plan: BackupPlan | None, restore_checks: list[RestoreCheck]) -> bool:
    if backup_plan is None:
        return False
    if not backup_plan.encrypted_required or not backup_plan.restore_test_required:
        return False
    return any(check.status is RestoreCheckStatus.PASSED and not check.blocks_persistence for check in restore_checks)
