from pydantic import BaseModel


class StorageBackendStatusCard(BaseModel):
    label_nl: str
    status_nl: str
    mode: str


class StorageBackupStatus(BaseModel):
    status: str
    encrypted_required: bool
    restore_test_required: bool
    restore_tested: bool


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
    backends: list[StorageBackendStatusCard]
    backup: StorageBackupStatus


def build_storage_status() -> StorageStatusResponse:
    return StorageStatusResponse(
        title_nl="Opslagstatus",
        summary_nl="Opslag gepland, nog niet verbonden.",
        help_nl="De database is gekozen, maar nog niet actief. De app kan je paper portefeuille daarom nog niet bewaren.",
        selected_database_nl="PostgreSQL gepland",
        migration_tool_nl="Alembic gepland",
        implementation_status_nl="Nog niet geïmplementeerd",
        first_persistence_target_nl="Eerste paper setup en paper cash",
        storage_ready=False,
        can_persist_paper_setup=False,
        can_persist_transactions=False,
        can_persist_audit_events=False,
        persistence_mode="not_available",
        migrations_available=False,
        block_reasons=["backend_not_configured", "audit_storage_missing"],
        warning_reasons=["preview_only", "backup_not_tested"],
        backends=[
            StorageBackendStatusCard(
                label_nl="PostgreSQL", status_nl="Gepland, niet ingesteld", mode="not_configured"
            ),
            StorageBackendStatusCard(
                label_nl="TimescaleDB", status_nl="Gepland, niet ingesteld", mode="not_configured"
            ),
            StorageBackendStatusCard(
                label_nl="Auditlog", status_nl="Gepland, niet ingesteld", mode="not_configured"
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
