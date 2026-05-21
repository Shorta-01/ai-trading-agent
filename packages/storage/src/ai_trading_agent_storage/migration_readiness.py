"""Offline-safe migration readiness contracts and helpers.
This module defines expected migration inventory contracts for storage readiness
without creating database engines/sessions or reading runtime environment values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError


class MigrationReadinessStatus(StrEnum):
    NOT_CONNECTED = "not_connected"
    NOT_CHECKED = "not_checked"
    OFFLINE_INVENTORY_VALID = "offline_inventory_valid"
    OFFLINE_INVENTORY_INVALID = "offline_inventory_invalid"
    MIGRATIONS_CURRENT = "migrations_current"
    MIGRATIONS_BEHIND = "migrations_behind"
    MIGRATIONS_UNKNOWN = "migrations_unknown"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True)
class MigrationRevisionInfo:
    revision_id: str
    previous_revision_id: str | None
    filename: str
    label_nl: str
    description_nl: str


@dataclass(frozen=True)
class MigrationInventory:
    expected_revisions: tuple[MigrationRevisionInfo, ...]
    latest_expected_revision_id: str
    revision_count: int
    inventory_valid: bool
    explanation_nl: str


@dataclass(frozen=True)
class MigrationReadinessReport:
    status: MigrationReadinessStatus
    database_connected: bool
    migrations_checked_against_database: bool
    offline_inventory_valid: bool
    latest_expected_revision_id: str | None
    database_revision_id: str | None
    persistence_allowed: bool
    blocks_runtime_writes: bool
    explanation_nl: str


_EXPECTED_MIGRATION_REVISIONS: tuple[MigrationRevisionInfo, ...] = (
    MigrationRevisionInfo(
        revision_id="0001",
        previous_revision_id=None,
        filename="0001_paper_setup_audit_foundation.py",
        label_nl="Papieren setup en auditbasis",
        description_nl=(
            "Eerste tabellen voor papieren portefeuille-setup, papieren cash en auditbasis."
        ),
    ),
    MigrationRevisionInfo(
        revision_id="0002",
        previous_revision_id="0001",
        filename="0002_broker_accounts_and_sync_runs.py",
        label_nl="Brokeraccounts en synchronisatieruns",
        description_nl="Basis voor IBKR-accountspiegel en synchronisatieruns.",
    ),
    MigrationRevisionInfo(
        revision_id="0003",
        previous_revision_id="0002",
        filename="0003_broker_position_and_cash_snapshots.py",
        label_nl="Brokerposities en cashmomentopnames",
        description_nl="Momentopnames voor toekomstige IBKR-posities en cash.",
    ),
    MigrationRevisionInfo(
        revision_id="0004",
        previous_revision_id="0003",
        filename="0004_broker_execution_and_commission_snapshots.py",
        label_nl="Brokertransacties en kostenmomentopnames",
        description_nl=(
            "Momentopnames voor toekomstige IBKR-uitvoeringen, commissies en "
            "gerealiseerde resultaten."
        ),
    ),
    MigrationRevisionInfo(
        revision_id="0005",
        previous_revision_id="0004",
        filename="0005_broker_reconciliation_schema.py",
        label_nl="Brokerreconciliatie",
        description_nl="Tabellen voor toekomstige reconciliatierapporten en verschillen.",
    ),
    MigrationRevisionInfo(
        revision_id="0006",
        previous_revision_id="0005",
        filename="0006_external_broker_activities.py",
        label_nl="Externe brokeractiviteiten",
        description_nl="Tabel voor toekomstige directe IBKR-activiteiten buiten AI-Trading-Agent.",
    ),
    MigrationRevisionInfo(
        revision_id="0007",
        previous_revision_id="0006",
        filename="0007_system_events.py",
        label_nl="Systeemmeldingen",
        description_nl=(
            "Tabellen voor centrale systeemmeldingen, fouten, waarschuwingen en blokkeringen."
        ),
    ),
    MigrationRevisionInfo(
        revision_id="0008",
        previous_revision_id="0007",
        filename="0008_trading_settings.py",
        label_nl="Trading instellingen",
        description_nl="Tabel voor Toegestane beleggingen en Mijn strategie.",
    ),
    MigrationRevisionInfo(
        revision_id="0009",
        previous_revision_id="0008",
        filename="0009_evidence_ledger.py",
        label_nl="Evidence ledger en eventsignalen",
        description_nl="Opslagfundament voor evidence-items, event-signalen en auditlinks.",
    ),
    MigrationRevisionInfo(
        revision_id="0010",
        previous_revision_id="0009",
        filename="0010_research_source_archive.py",
        label_nl="Research Source Archive opslagfundament",
        description_nl=(
            "Opslagfundament voor research-bronnen, documentsets, classificaties en "
            "verwerkingsstatus."
        ),
    ),
    MigrationRevisionInfo(
        revision_id="0011",
        previous_revision_id="0010",
        filename="0011_research_extracted_text.py",
        label_nl="Research extracted text opslagfundament",
        description_nl="Opslagfundament voor geëxtraheerde-tekstmetadata en archiefverwijzingen.",
    ),
    MigrationRevisionInfo(
        revision_id="0012",
        previous_revision_id="0011",
        filename="0012_research_source_prompt_injection_scan.py",
        label_nl="Research source prompt-injection scan",
        description_nl="Opslagfundament voor prompt-injection scanstatus per research-bron.",
    ),
    MigrationRevisionInfo(
        revision_id="0013",
        previous_revision_id="0012",
        filename="0013_research_source_credibility_assessments.py",
        label_nl="Research source credibility assessments",
        description_nl="Opslagfundament voor bron-credibilitystatus per research-bron.",
    ),
    MigrationRevisionInfo(
        revision_id="0014",
        previous_revision_id="0013",
        filename="0014_research_source_evidence_items.py",
        label_nl="Research source evidence items",
        description_nl="Opslagfundament voor evidence-items gekoppeld aan research-bronnen.",
    ),
    MigrationRevisionInfo(
        revision_id="0015_research_source_evidence_ledger_links",
        previous_revision_id="0014",
        filename="0015_research_source_evidence_ledger_links.py",
        label_nl="Research source evidence-ledger-links",
        description_nl="Opslagfundament voor evidence-lineage links naar Evidence Ledger.",
    ),
    MigrationRevisionInfo(
        revision_id="0016_research_gate_outcomes",
        previous_revision_id="0015_research_source_evidence_ledger_links",
        filename="0016_research_gate_outcomes.py",
        label_nl="Research gate-outcomes en freshness",
        description_nl="Opslagfundament voor gate-uitkomsten en freshnessstatus (audit-only).",
    ),
    MigrationRevisionInfo(
        revision_id="0017_research_source_conflict_findings",
        previous_revision_id="0016_research_gate_outcomes",
        filename="0017_research_source_conflict_findings.py",
        label_nl="Research bronconflict-bevindingen",
        description_nl="Opslagfundament voor auditbare bron/evidence-conflictbevindingen.",
    ),
    MigrationRevisionInfo(
        revision_id="0018_asset_master_identity_foundation",
        previous_revision_id="0017_research_source_conflict_findings",
        filename="0018_asset_master_identity_foundation.py",
        label_nl="Asset master identity foundation",
        description_nl="Opslagfundament voor canonieke asset-identiteit en identifier-aliassen.",
    ),
    MigrationRevisionInfo(
        revision_id="0019_source_to_asset_linking_foundation",
        previous_revision_id="0018_asset_master_identity_foundation",
        filename="0019_source_to_asset_linking_foundation.py",
        label_nl="Source-to-asset linking foundation",
        description_nl="Opslagfundament voor veilige bron-naar-asset links (audit/reference-only).",
    ),
    MigrationRevisionInfo(
        revision_id="0020_watchlist_foundation",
        previous_revision_id="0019_source_to_asset_linking_foundation",
        filename="0020_watchlist_foundation.py",
        label_nl="Watchlist foundation",
        description_nl="Opslagfundament voor lokaal beheerde handmatige volglijst-items.",
    ),
    MigrationRevisionInfo(
        revision_id="0021_market_data_storage_foundation",
        previous_revision_id="0020_watchlist_foundation",
        filename="0021_market_data_storage_foundation.py",
        label_nl="Market data opslag/freshness foundation",
        description_nl=(
            "Conservatief opslagfundament voor conid-gebaseerde market-data snapshotmetadata "
            "en freshness/readinessblokkade-info (zonder runtime fetch)."
        ),
    ),
    MigrationRevisionInfo(
        revision_id="0022_asset_listing_identity_foundation",
        previous_revision_id="0021_market_data_storage_foundation",
        filename="0022_asset_listing_identity_foundation.py",
        label_nl="AssetListing identity foundation",
        description_nl=(
            "Opslagfundament voor listing/instrument/conid-identiteit (reference/status-only)."
        ),
    ),
    MigrationRevisionInfo(
        revision_id="0023_request_log_provider_freshness_contracts",
        previous_revision_id="0022_asset_listing_identity_foundation",
        filename="0023_request_log_provider_freshness_contracts.py",
        label_nl="Request/provider/freshness audit skeleton",
        description_nl=(
            "Non-runtime audit/status skeleton voor request logs, provider/source metadata en "
            "freshness-audit records; voegt geen fetchgedrag toe."
        ),
    ),
    MigrationRevisionInfo(
        revision_id="0024_market_data_latest_snapshots",
        previous_revision_id="0023_request_log_provider_freshness_contracts",
        filename="0024_market_data_latest_snapshots.py",
        label_nl="Market data latest snapshot storage",
        description_nl="Latest market-data snapshotopslag met status/veiligheidsvelden (read-only).",
    ),
)


def expected_migration_revisions() -> tuple[MigrationRevisionInfo, ...]:
    return _EXPECTED_MIGRATION_REVISIONS


def _is_expected_chain_valid(revisions: tuple[MigrationRevisionInfo, ...]) -> bool:
    if not revisions:
        return False
    for index, revision in enumerate(revisions):
        if index == 0 and revision.previous_revision_id is not None:
            return False
        if index > 0 and revision.previous_revision_id != revisions[index - 1].revision_id:
            return False
    return True


def build_expected_migration_inventory() -> MigrationInventory:
    revisions = expected_migration_revisions()
    latest_expected_revision_id = revisions[-1].revision_id if revisions else ""
    inventory_valid = _is_expected_chain_valid(revisions)
    return MigrationInventory(
        expected_revisions=revisions,
        latest_expected_revision_id=latest_expected_revision_id,
        revision_count=len(revisions),
        inventory_valid=inventory_valid,
        explanation_nl=(
            "Dit is alleen een offline inventaris van verwachte migraties en "
            "geen bewijs van toegepaste database-migraties."
        ),
    )


def build_database_not_connected_readiness_report() -> MigrationReadinessReport:
    inventory = build_expected_migration_inventory()
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.NOT_CONNECTED,
        database_connected=False,
        migrations_checked_against_database=False,
        offline_inventory_valid=inventory.inventory_valid,
        latest_expected_revision_id=inventory.latest_expected_revision_id,
        database_revision_id=None,
        persistence_allowed=False,
        blocks_runtime_writes=True,
        explanation_nl=(
            "De database is nog niet verbonden. Runtime writes blijven geblokkeerd "
            "tot de verbinding en migraties echt gecontroleerd zijn."
        ),
    )


def check_offline_migration_inventory() -> MigrationReadinessReport:
    inventory = build_expected_migration_inventory()
    versions_dir = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    missing_files = [
        revision.filename
        for revision in inventory.expected_revisions
        if not (versions_dir / revision.filename).is_file()
    ]
    if inventory.inventory_valid and not missing_files:
        return MigrationReadinessReport(
            status=MigrationReadinessStatus.OFFLINE_INVENTORY_VALID,
            database_connected=False,
            migrations_checked_against_database=False,
            offline_inventory_valid=True,
            latest_expected_revision_id=inventory.latest_expected_revision_id,
            database_revision_id=None,
            persistence_allowed=False,
            blocks_runtime_writes=True,
            explanation_nl=(
                "Offline migratie-inventaris is geldig op basis van verwachte "
                "revisies en lokale bestanden; dit is geen bewijs dat een echte database "
                "gemigreerd is."
            ),
        )
    missing_text = ", ".join(missing_files) if missing_files else "onbekende mismatch"
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.OFFLINE_INVENTORY_INVALID,
        database_connected=False,
        migrations_checked_against_database=False,
        offline_inventory_valid=False,
        latest_expected_revision_id=inventory.latest_expected_revision_id,
        database_revision_id=None,
        persistence_allowed=False,
        blocks_runtime_writes=True,
        explanation_nl=(
            f"Offline migratie-inventaris is ongeldig: ontbrekende of onjuiste "
            f"lokale migratiebestanden ({missing_text}). Dit is geen databasecheck."
        ),
    )


def migration_readiness_is_safe_to_write(report: MigrationReadinessReport) -> bool:
    return report.persistence_allowed and not report.blocks_runtime_writes


def read_database_alembic_revision(connection: Connection) -> str | None:
    rows = connection.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    if not rows:
        return None
    if len(rows) != 1:
        raise ValueError("Expected exactly one alembic_version row.")
    row = rows[0]
    value = row[0]
    return str(value) if value is not None else None


def check_online_migration_readiness(connection: Connection) -> MigrationReadinessReport:
    inventory = build_expected_migration_inventory()
    try:
        database_revision_id = read_database_alembic_revision(connection)
    except ValueError:
        return MigrationReadinessReport(
            status=MigrationReadinessStatus.FAILED,
            database_connected=True,
            migrations_checked_against_database=True,
            offline_inventory_valid=inventory.inventory_valid,
            latest_expected_revision_id=inventory.latest_expected_revision_id,
            database_revision_id=None,
            persistence_allowed=False,
            blocks_runtime_writes=True,
            explanation_nl=(
                "De database-readiness check is mislukt. Runtime writes blijven geblokkeerd."
            ),
        )
    except SQLAlchemyError:
        return MigrationReadinessReport(
            status=MigrationReadinessStatus.FAILED,
            database_connected=False,
            migrations_checked_against_database=False,
            offline_inventory_valid=inventory.inventory_valid,
            latest_expected_revision_id=inventory.latest_expected_revision_id,
            database_revision_id=None,
            persistence_allowed=False,
            blocks_runtime_writes=True,
            explanation_nl=(
                "De database-readiness check is mislukt. Runtime writes blijven geblokkeerd."
            ),
        )
    if database_revision_id is None:
        return MigrationReadinessReport(
            status=MigrationReadinessStatus.MIGRATIONS_UNKNOWN,
            database_connected=True,
            migrations_checked_against_database=True,
            offline_inventory_valid=inventory.inventory_valid,
            latest_expected_revision_id=inventory.latest_expected_revision_id,
            database_revision_id=None,
            persistence_allowed=False,
            blocks_runtime_writes=True,
            explanation_nl=(
                "De Alembic version table kon niet veilig worden gelezen. "
                "Runtime writes blijven geblokkeerd."
            ),
        )
    known_revisions = {revision.revision_id for revision in inventory.expected_revisions}
    if database_revision_id == inventory.latest_expected_revision_id and inventory.inventory_valid:
        return MigrationReadinessReport(
            status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
            database_connected=True,
            migrations_checked_against_database=True,
            offline_inventory_valid=True,
            latest_expected_revision_id=inventory.latest_expected_revision_id,
            database_revision_id=database_revision_id,
            persistence_allowed=True,
            blocks_runtime_writes=False,
            explanation_nl=(
                "De database is verbonden en staat op de verwachte migratie 0006. "
                "Persistence mag pas gebruikt worden door toekomstige repository-implementaties."
            ),
        )
    if database_revision_id in known_revisions:
        return MigrationReadinessReport(
            status=MigrationReadinessStatus.MIGRATIONS_BEHIND,
            database_connected=True,
            migrations_checked_against_database=True,
            offline_inventory_valid=inventory.inventory_valid,
            latest_expected_revision_id=inventory.latest_expected_revision_id,
            database_revision_id=database_revision_id,
            persistence_allowed=False,
            blocks_runtime_writes=True,
            explanation_nl=(
                "De database is verbonden, maar de migraties lopen achter. "
                "Runtime writes blijven geblokkeerd."
            ),
        )
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_UNKNOWN,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=inventory.inventory_valid,
        latest_expected_revision_id=inventory.latest_expected_revision_id,
        database_revision_id=database_revision_id,
        persistence_allowed=False,
        blocks_runtime_writes=True,
        explanation_nl=(
            "De database is verbonden, maar de migratiestatus is onbekend. "
            "Runtime writes blijven geblokkeerd."
        ),
    )


def online_migration_readiness_interfaces_are_defined() -> bool:
    _ = read_database_alembic_revision
    _ = check_online_migration_readiness
    return True


def migration_readiness_interfaces_are_defined() -> bool:
    _ = MigrationReadinessStatus
    _ = MigrationRevisionInfo
    _ = MigrationInventory
    _ = MigrationReadinessReport
    _ = expected_migration_revisions
    _ = build_expected_migration_inventory
    _ = build_database_not_connected_readiness_report
    _ = check_offline_migration_inventory
    _ = migration_readiness_is_safe_to_write
    return True
