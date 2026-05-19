from pydantic import BaseModel

from ai_trading_agent_storage import (
    MigrationReadinessStatus,
    build_database_not_connected_readiness_report,
    build_expected_migration_inventory,
    migration_readiness_is_safe_to_write,
)


class StorageBackendStatusCard(BaseModel):
    label_nl: str
    status_nl: str
    mode: str


class StorageBackupStatus(BaseModel):
    status: str
    encrypted_required: bool
    restore_test_required: bool
    restore_tested: bool


class StorageMigrationReadinessStatus(BaseModel):
    status: str
    status_nl: str
    database_connected: bool
    migrations_checked_against_database: bool
    offline_inventory_valid: bool
    latest_expected_revision_id: str | None
    expected_revision_count: int
    database_revision_id: str | None
    persistence_allowed: bool
    blocks_runtime_writes: bool
    safe_to_write: bool
    explanation_nl: str


class StorageStatusResponse(BaseModel):
    title_nl: str
    summary_nl: str
    help_nl: str
    selected_database_nl: str
    migration_tool_nl: str
    implementation_status_nl: str
    first_persistence_target_nl: str
    storage_ready: bool
    can_persist_paper_setup: bool
    can_persist_transactions: bool
    can_persist_audit_events: bool
    persistence_mode: str
    migrations_available: bool
    block_reasons: list[str]
    warning_reasons: list[str]
    migration_readiness: StorageMigrationReadinessStatus
    backends: list[StorageBackendStatusCard]
    backup: StorageBackupStatus


def _migration_status_nl(status: MigrationReadinessStatus) -> str:
    if status == MigrationReadinessStatus.NOT_CONNECTED:
        return "Database niet verbonden"
    return "Onbekende migratiestatus"


def build_storage_status() -> StorageStatusResponse:
    migration_inventory = build_expected_migration_inventory()
    migration_readiness = build_database_not_connected_readiness_report()

    return StorageStatusResponse(
        title_nl="Opslagstatus",
        summary_nl=(
            "Database niet verbonden; runtime writes blijven geblokkeerd tot"
            " verbinding en migratiecheck expliciet zijn bevestigd."
        ),
        help_nl=(
            "De storage-readiness is gebaseerd op offline migratiecontracten. "
            "Er is geen actieve databaseverbinding in deze statusroute en "
            "runtime writes zijn daarom geblokkeerd."
        ),
        selected_database_nl="PostgreSQL gepland",
        migration_tool_nl="Alembic gepland",
        implementation_status_nl="Nog niet geïmplementeerd",
        first_persistence_target_nl="Eerste paper setup en paper cash",
        storage_ready=False,
        can_persist_paper_setup=False,
        can_persist_transactions=False,
        can_persist_audit_events=False,
        persistence_mode="blocked_not_connected",
        migrations_available=migration_inventory.inventory_valid,
        block_reasons=[
            "database_not_connected",
            "migration_readiness_not_checked_online",
            "runtime_writes_blocked",
            "audit_storage_missing",
        ],
        warning_reasons=["offline_inventory_only", "backup_not_tested"],
        migration_readiness=StorageMigrationReadinessStatus(
            status=migration_readiness.status.value,
            status_nl=_migration_status_nl(migration_readiness.status),
            database_connected=migration_readiness.database_connected,
            migrations_checked_against_database=(
                migration_readiness.migrations_checked_against_database
            ),
            offline_inventory_valid=migration_readiness.offline_inventory_valid,
            latest_expected_revision_id=migration_readiness.latest_expected_revision_id,
            expected_revision_count=migration_inventory.revision_count,
            database_revision_id=migration_readiness.database_revision_id,
            persistence_allowed=migration_readiness.persistence_allowed,
            blocks_runtime_writes=migration_readiness.blocks_runtime_writes,
            safe_to_write=migration_readiness_is_safe_to_write(migration_readiness),
            explanation_nl=migration_readiness.explanation_nl,
        ),
        backends=[
            StorageBackendStatusCard(
                label_nl="PostgreSQL", status_nl="Niet verbonden, writes geblokkeerd", mode="blocked"
            ),
            StorageBackendStatusCard(
                label_nl="TimescaleDB", status_nl="Gepland, niet ingesteld", mode="not_configured"
            ),
            StorageBackendStatusCard(
                label_nl="Auditlog", status_nl="Niet verbonden, writes geblokkeerd", mode="blocked"
            ),
            StorageBackendStatusCard(
                label_nl="Research archief",
                status_nl="Gepland, niet ingesteld",
                mode="not_configured",
            ),
            StorageBackendStatusCard(
                label_nl="Raw data archief",
                status_nl="Gepland, niet ingesteld",
                mode="not_configured",
            ),
        ],
        backup=StorageBackupStatus(
            status="not_configured",
            encrypted_required=True,
            restore_test_required=True,
            restore_tested=False,
        ),
    )
