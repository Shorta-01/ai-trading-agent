from __future__ import annotations

from dataclasses import asdict
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import Table, select
from sqlalchemy.engine import Connection, RowMapping

from ai_trading_agent_storage.metadata import (
    asset_identifier_aliases,
    asset_master_records,
    broker_accounts,
    broker_cash_snapshots,
    broker_commission_snapshots,
    broker_execution_snapshots,
    broker_position_snapshots,
    broker_reconciliation_differences,
    broker_reconciliation_reports,
    broker_sync_runs,
    external_broker_activities,
    market_data_snapshots,
    paper_portfolio_setups,
    research_document_classifications,
    research_document_set_members,
    research_document_sets,
    research_extracted_texts,
    research_source_asset_links,
    research_source_prompt_injection_scans,
    research_source_credibility_assessments,
    research_source_conflict_findings,
    source_to_asset_links,
    research_source_evidence_ledger_links,
    research_source_evidence_items,
    research_gate_outcomes,
    research_source_processing_status,
    research_sources,
    research_uploaded_file_metadata,
    research_url_metadata,
    research_user_notes,
    system_events,
    trading_settings,
)
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    migration_readiness_is_safe_to_write,
)
from ai_trading_agent_storage.repository_contracts import (
    AssetIdentifierAliasRecord,
    AssetMasterRecord,
    BrokerAccountRecord,
    BrokerCashSnapshotRecord,
    BrokerCommissionSnapshotRecord,
    BrokerExecutionSnapshotRecord,
    BrokerPositionSnapshotRecord,
    BrokerReconciliationDifferenceRecord,
    BrokerReconciliationReportRecord,
    BrokerSyncRunRecord,
    CreatePaperPortfolioSetupRequest,
    CreateSystemEventRequest,
    ExternalBrokerActivityRecord,
    MarketDataSnapshotRecord,
    PaperPortfolioSetupRecord,
    RepositoryHealthStatus,
    ResearchDocumentClassificationRecord,
    ResearchDocumentSetMemberRecord,
    ResearchDocumentSetRecord,
    ResearchExtractedTextRecord,
    ResearchSourceAssetLinkRecord,
    ResearchSourcePromptInjectionScanRecord,
    ResearchSourceCredibilityAssessmentRecord,
    ResearchSourceConflictFindingRecord,
    SourceToAssetLinkRecord,
    ResearchSourceEvidenceItemRecord,
    ResearchSourceEvidenceLedgerLinkRecord,
    ResearchGateOutcomeRecord,
    ResearchSourceProcessingStatusRecord,
    ResearchSourceRecord,
    ResearchUploadedFileMetadataRecord,
    ResearchUrlMetadataRecord,
    ResearchUserNoteRecord,
    SaveTradingSettingsRequest,
    StorageListResult,
    StorageReadResult,
    StorageWriteResult,
    SystemEventRecord,
    TradingSettingsRecord,
)


class StoragePersistenceBlockedError(RuntimeError):
    pass


def ensure_persistence_allowed(report: MigrationReadinessReport) -> None:
    if not migration_readiness_is_safe_to_write(report):
        raise StoragePersistenceBlockedError(
            "Persistence is geblokkeerd totdat migratiestatus schrijven toestaat."
        )


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _json_tuple_or_none(value: tuple[str, ...] | list[str] | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    return tuple(value)


def _json_list_or_none(value: tuple[str, ...] | list[str] | None) -> list[str] | None:
    if value is None:
        return None
    return list(value)



def _row_to_source_to_asset_link_record(row: RowMapping) -> SourceToAssetLinkRecord:
    raw_audit_context = row["audit_context_json"]
    audit_context_json: dict[str, str] | None = None
    if raw_audit_context is not None:
        if not isinstance(raw_audit_context, (str, bytes, bytearray)):
            raise TypeError("audit_context_json moet een JSON-string zijn of None.")
        parsed = json.loads(raw_audit_context)
        audit_context_json = {str(key): str(value) for key, value in dict(parsed).items()}

    return SourceToAssetLinkRecord(
        link_id=str(row["link_id"]),
        asset_id=str(row["asset_id"]),
        target_type=str(row["target_type"]),
        target_id=str(row["target_id"]),
        link_reason_nl=str(row["link_reason_nl"]),
        audit_context_json=audit_context_json,
        safe_to_use_for_suggestions=cast(bool, row["safe_to_use_for_suggestions"]),
        blocks_suggestions=cast(bool, row["blocks_suggestions"]),
        created_at=cast(datetime, row["created_at"]),
        created_by=str(row["created_by"]),
        explanation_nl=str(row["explanation_nl"]),
    )

def _row_to_gate_outcome_record(row: Any) -> ResearchGateOutcomeRecord:
    values = dict(row)
    values["source_reference_ids_json"] = _json_tuple_or_none(
        None
        if values.get("source_reference_ids_json") is None
        else json.loads(values["source_reference_ids_json"])
    )
    values["audit_context_json"] = (
        None
        if values.get("audit_context_json") is None
        else dict(json.loads(values["audit_context_json"]))
    )
    return ResearchGateOutcomeRecord(**values)


def _row_to_conflict_finding_record(row: Any) -> ResearchSourceConflictFindingRecord:
    values = dict(row)
    values["source_reference_ids_json"] = _json_tuple_or_none(
        None
        if values.get("source_reference_ids_json") is None
        else json.loads(values["source_reference_ids_json"])
    )
    values["audit_context_json"] = (
        None
        if values.get("audit_context_json") is None
        else dict(json.loads(values["audit_context_json"]))
    )
    return ResearchSourceConflictFindingRecord(**values)


def _row_to_asset_master_record(row: Any) -> AssetMasterRecord:
    values = dict(row)
    values["source_reference_ids_json"] = _json_tuple_or_none(
        values.get("source_reference_ids_json")
    )
    values["audit_context_json"] = (
        None if values.get("audit_context_json") is None else dict(values["audit_context_json"])
    )
    return AssetMasterRecord(**values)


def _read_one_by_column(
    connection: Connection,
    table: Table,
    column_name: str,
    value: str,
) -> Any | None:
    statement = select(table).where(getattr(table.c, column_name) == value)
    return connection.execute(statement).mappings().first()


def _read_many_by_column(
    connection: Connection,
    table: Table,
    column_name: str,
    value: str,
) -> list[Any]:
    statement = select(table).where(getattr(table.c, column_name) == value)
    return list(connection.execute(statement).mappings().all())


class _Base:
    def __init__(self, connection: Connection, readiness_report: MigrationReadinessReport) -> None:
        self._connection = connection
        self._readiness_report = readiness_report

    def _insert(self, table: Table, values: dict[str, Any]) -> None:
        ensure_persistence_allowed(self._readiness_report)
        self._connection.execute(table.insert().values(**values))


class SqlAlchemyBrokerAccountRepository(_Base):
    def get_by_id(self, broker_account_id: str) -> StorageReadResult[BrokerAccountRecord]:
        row = _read_one_by_column(
            self._connection,
            broker_accounts,
            "broker_account_id",
            broker_account_id,
        )
        if row is None:
            return StorageReadResult(
                found=False,
                record=None,
                table_name=broker_accounts.name,
                explanation_nl="Brokeraccount niet gevonden.",
            )

        return StorageReadResult(
            found=True,
            record=BrokerAccountRecord(**row),
            table_name=broker_accounts.name,
            explanation_nl="Brokeraccount gevonden.",
        )

    def list_accounts(self) -> StorageListResult[BrokerAccountRecord]:
        rows = self._connection.execute(select(broker_accounts)).mappings().all()
        return StorageListResult(
            records=tuple(BrokerAccountRecord(**row) for row in rows),
            table_name=broker_accounts.name,
            explanation_nl="Brokeraccounts opgehaald.",
        )

    def save_account(self, record: BrokerAccountRecord) -> StorageWriteResult:
        self._insert(broker_accounts, asdict(record))
        return StorageWriteResult(
            accepted=True,
            record_id=record.broker_account_id,
            table_name=broker_accounts.name,
            audit_required=True,
            explanation_nl="Brokeraccount opgeslagen.",
        )


class SqlAlchemyBrokerSyncRunRepository(_Base):
    def get_by_id(self, broker_sync_run_id: str) -> StorageReadResult[BrokerSyncRunRecord]:
        row = _read_one_by_column(
            self._connection,
            broker_sync_runs,
            "broker_sync_run_id",
            broker_sync_run_id,
        )
        if row is None:
            return StorageReadResult(
                False, None, broker_sync_runs.name, "Synchronisatierun niet gevonden."
            )

        values = dict(row)
        values["planned_data_kinds_json"] = _json_tuple_or_none(
            values.get("planned_data_kinds_json")
        )
        values["data_source_types_json"] = _json_tuple_or_none(values.get("data_source_types_json"))
        values["source_reference_ids_json"] = None
        values["audit_event_ids_json"] = None
        return StorageReadResult(
            True,
            BrokerSyncRunRecord(**values),
            broker_sync_runs.name,
            "Synchronisatierun gevonden.",
        )

    def list_for_account(self, broker_account_id: str) -> StorageListResult[BrokerSyncRunRecord]:
        rows = _read_many_by_column(
            self._connection, broker_sync_runs, "broker_account_id", broker_account_id
        )
        records: list[BrokerSyncRunRecord] = []
        for row in rows:
            values = dict(row)
            values["planned_data_kinds_json"] = _json_tuple_or_none(
                values.get("planned_data_kinds_json")
            )
            values["data_source_types_json"] = _json_tuple_or_none(
                values.get("data_source_types_json")
            )
            values["source_reference_ids_json"] = None
            values["audit_event_ids_json"] = None
            records.append(BrokerSyncRunRecord(**values))
        return StorageListResult(
            tuple(records), broker_sync_runs.name, "Synchronisatieruns opgehaald."
        )

    def save_sync_run(self, record: BrokerSyncRunRecord) -> StorageWriteResult:
        values = asdict(record)
        values["planned_data_kinds_json"] = _json_list_or_none(record.planned_data_kinds_json)
        values["data_source_types_json"] = _json_list_or_none(record.data_source_types_json)
        values.pop("source_reference_ids_json", None)
        values.pop("audit_event_ids_json", None)
        self._insert(broker_sync_runs, values)
        return StorageWriteResult(
            True,
            record.broker_sync_run_id,
            broker_sync_runs.name,
            True,
            "Synchronisatierun opgeslagen.",
        )


class SqlAlchemyPaperPortfolioSetupRepository(_Base):
    def create_setup(self, request: CreatePaperPortfolioSetupRequest) -> StorageWriteResult:
        self._insert(
            paper_portfolio_setups,
            {
                "setup_id": request.setup_id,
                "portfolio_name": request.portfolio_name,
                "base_currency": request.base_currency,
                "starting_cash_amount": request.starting_cash_amount,
                "paper_only": True,
                "real_money_used": False,
                "broker_order_created": False,
                "live_trading_enabled": False,
                "user_confirmed_paper_only": True,
                "user_confirmed_no_real_money": True,
                "user_confirmed_no_broker_order": True,
                "status": request.status,
                "created_at": request.created_at,
                "updated_at": None,
                "explanation_nl": request.explanation_nl,
            },
        )
        return StorageWriteResult(
            True,
            request.setup_id,
            paper_portfolio_setups.name,
            True,
            "Papieren portfolio-opzet opgeslagen.",
        )

    def get_by_id(self, setup_id: str) -> StorageReadResult[PaperPortfolioSetupRecord]:
        row = _read_one_by_column(self._connection, paper_portfolio_setups, "setup_id", setup_id)
        if row is None:
            return StorageReadResult(
                False,
                None,
                paper_portfolio_setups.name,
                "Papieren portfolio-opzet niet gevonden.",
            )
        values = dict(row)
        values["starting_cash_amount"] = _to_decimal(values.get("starting_cash_amount"))
        return StorageReadResult(
            True,
            PaperPortfolioSetupRecord(**values),
            paper_portfolio_setups.name,
            "Papieren portfolio-opzet gevonden.",
        )

    def get_latest(self) -> StorageReadResult[PaperPortfolioSetupRecord]:
        statement = select(paper_portfolio_setups).order_by(
            paper_portfolio_setups.c.created_at.desc()
        )
        row = self._connection.execute(statement).mappings().first()
        if row is None:
            return StorageReadResult(
                False,
                None,
                paper_portfolio_setups.name,
                "Geen papieren portfolio-opzet beschikbaar.",
            )
        values = dict(row)
        values["starting_cash_amount"] = _to_decimal(values.get("starting_cash_amount"))
        return StorageReadResult(
            True,
            PaperPortfolioSetupRecord(**values),
            paper_portfolio_setups.name,
            "Laatste papieren portfolio-opzet gevonden.",
        )


class SqlAlchemyTradingSettingsRepository(_Base):
    def save_settings(self, request: SaveTradingSettingsRequest) -> StorageWriteResult:
        ensure_persistence_allowed(self._readiness_report)
        existing = _read_one_by_column(
            self._connection,
            trading_settings,
            "settings_id",
            request.settings_id,
        )

        if existing is None:
            values = {
                "settings_id": request.settings_id,
                "created_at": request.updated_at,
                "updated_at": request.updated_at,
                "version": 1,
                "allowed_universe_json": request.allowed_universe,
                "user_strategy_json": request.user_strategy,
                "source": request.source,
                "status": request.status,
                "explanation_nl": request.explanation_nl,
            }
            self._connection.execute(trading_settings.insert().values(**values))
            return StorageWriteResult(
                True,
                request.settings_id,
                trading_settings.name,
                True,
                "Trading instellingen opgeslagen.",
            )

        new_version = int(existing["version"]) + 1
        self._connection.execute(
            trading_settings.update()
            .where(trading_settings.c.settings_id == request.settings_id)
            .values(
                updated_at=request.updated_at,
                version=new_version,
                allowed_universe_json=request.allowed_universe,
                user_strategy_json=request.user_strategy,
                source=request.source,
                status=request.status,
                explanation_nl=request.explanation_nl,
            )
        )
        return StorageWriteResult(
            True,
            request.settings_id,
            trading_settings.name,
            True,
            "Trading instellingen bijgewerkt.",
        )

    def get_settings(
        self, settings_id: str = "default"
    ) -> StorageReadResult[TradingSettingsRecord]:
        row = _read_one_by_column(self._connection, trading_settings, "settings_id", settings_id)
        if row is None:
            return StorageReadResult(
                found=False,
                record=None,
                table_name=trading_settings.name,
                explanation_nl="Trading instellingen niet gevonden.",
            )
        return StorageReadResult(
            found=True,
            record=TradingSettingsRecord(
                settings_id=row["settings_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                version=row["version"],
                allowed_universe=dict(row["allowed_universe_json"]),
                user_strategy=dict(row["user_strategy_json"]),
                source=row["source"],
                status=row["status"],
                explanation_nl=row["explanation_nl"],
            ),
            table_name=trading_settings.name,
            explanation_nl="Trading instellingen gevonden.",
        )


class SqlAlchemyBrokerSnapshotRepository(_Base):
    def _list(
        self, table: Table, column_name: str, value: str, ctor: Any
    ) -> StorageListResult[Any]:
        rows = _read_many_by_column(self._connection, table, column_name, value)
        records = []
        for row in rows:
            row_dict = dict(row)
            for key in (
                "quantity",
                "average_cost",
                "market_value",
                "cash_amount",
                "price",
                "commission_amount",
                "realized_pnl",
            ):
                if key in row_dict:
                    row_dict[key] = _to_decimal(row_dict[key])
            if "source_reference_ids_json" in row_dict:
                row_dict["source_reference_ids_json"] = _json_tuple_or_none(
                    row_dict["source_reference_ids_json"]
                )
            records.append(ctor(**row_dict))
        return StorageListResult(tuple(records), table.name, f"{table.name} opgehaald.")

    def list_position_snapshots(
        self, broker_sync_run_id: str
    ) -> StorageListResult[BrokerPositionSnapshotRecord]:
        return self._list(
            broker_position_snapshots,
            "broker_sync_run_id",
            broker_sync_run_id,
            BrokerPositionSnapshotRecord,
        )

    def list_cash_snapshots(
        self, broker_sync_run_id: str
    ) -> StorageListResult[BrokerCashSnapshotRecord]:
        return self._list(
            broker_cash_snapshots,
            "broker_sync_run_id",
            broker_sync_run_id,
            BrokerCashSnapshotRecord,
        )

    def list_execution_snapshots(
        self, broker_sync_run_id: str
    ) -> StorageListResult[BrokerExecutionSnapshotRecord]:
        return self._list(
            broker_execution_snapshots,
            "broker_sync_run_id",
            broker_sync_run_id,
            BrokerExecutionSnapshotRecord,
        )

    def list_commission_snapshots(
        self, broker_sync_run_id: str
    ) -> StorageListResult[BrokerCommissionSnapshotRecord]:
        return self._list(
            broker_commission_snapshots,
            "broker_sync_run_id",
            broker_sync_run_id,
            BrokerCommissionSnapshotRecord,
        )

    def save_position_snapshot(self, record: BrokerPositionSnapshotRecord) -> StorageWriteResult:
        values = asdict(record)
        values["source_reference_ids_json"] = _json_list_or_none(record.source_reference_ids_json)
        self._insert(broker_position_snapshots, values)
        return StorageWriteResult(
            True,
            record.broker_position_snapshot_id,
            broker_position_snapshots.name,
            True,
            "Positiemomentopname opgeslagen.",
        )

    def save_cash_snapshot(self, record: BrokerCashSnapshotRecord) -> StorageWriteResult:
        values = asdict(record)
        values["source_reference_ids_json"] = _json_list_or_none(record.source_reference_ids_json)
        self._insert(broker_cash_snapshots, values)
        return StorageWriteResult(
            True,
            record.broker_cash_snapshot_id,
            broker_cash_snapshots.name,
            True,
            "Cashmomentopname opgeslagen.",
        )

    def save_execution_snapshot(self, record: BrokerExecutionSnapshotRecord) -> StorageWriteResult:
        values = asdict(record)
        values["source_reference_ids_json"] = _json_list_or_none(record.source_reference_ids_json)
        self._insert(broker_execution_snapshots, values)
        return StorageWriteResult(
            True,
            record.broker_execution_snapshot_id,
            broker_execution_snapshots.name,
            True,
            "Uitvoeringsmomentopname opgeslagen.",
        )

    def save_commission_snapshot(
        self, record: BrokerCommissionSnapshotRecord
    ) -> StorageWriteResult:
        values = asdict(record)
        values["source_reference_ids_json"] = _json_list_or_none(record.source_reference_ids_json)
        self._insert(broker_commission_snapshots, values)
        return StorageWriteResult(
            True,
            record.broker_commission_snapshot_id,
            broker_commission_snapshots.name,
            True,
            "Commissiemomentopname opgeslagen.",
        )


class SqlAlchemyMarketDataSnapshotRepository(_Base):
    def get_latest_by_ibkr_conid(
        self,
        ibkr_conid: str,
    ) -> StorageReadResult[MarketDataSnapshotRecord]:
        row = (
            self._connection.execute(
                select(market_data_snapshots)
                .where(market_data_snapshots.c.ibkr_conid == ibkr_conid)
                .order_by(market_data_snapshots.c.stored_at.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        if row is None:
            return StorageReadResult(
                found=False,
                record=None,
                table_name=market_data_snapshots.name,
                explanation_nl="Geen market-data snapshot gevonden voor conid.",
            )
        return StorageReadResult(
            found=True,
            record=MarketDataSnapshotRecord(**dict(row)),
            table_name=market_data_snapshots.name,
            explanation_nl="Laatste market-data snapshot opgehaald voor conid.",
        )

    def list_by_ibkr_conid(self, ibkr_conid: str) -> StorageListResult[MarketDataSnapshotRecord]:
        rows = (
            self._connection.execute(
                select(market_data_snapshots)
                .where(market_data_snapshots.c.ibkr_conid == ibkr_conid)
                .order_by(market_data_snapshots.c.stored_at.desc())
            )
            .mappings()
            .all()
        )
        return StorageListResult(
            records=tuple(MarketDataSnapshotRecord(**dict(row)) for row in rows),
            table_name=market_data_snapshots.name,
            explanation_nl="Market-data snapshots opgehaald voor conid.",
        )

    def list_by_watchlist_item(
        self,
        watchlist_item_id: str,
    ) -> StorageListResult[MarketDataSnapshotRecord]:
        rows = (
            self._connection.execute(
                select(market_data_snapshots)
                .where(market_data_snapshots.c.watchlist_item_id == watchlist_item_id)
                .order_by(market_data_snapshots.c.stored_at.desc())
            )
            .mappings()
            .all()
        )
        return StorageListResult(
            records=tuple(MarketDataSnapshotRecord(**dict(row)) for row in rows),
            table_name=market_data_snapshots.name,
            explanation_nl="Market-data snapshots opgehaald voor volglijst-item.",
        )


class SqlAlchemyBrokerReconciliationRepository(_Base):
    def get_report_by_id(
        self, broker_reconciliation_report_id: str
    ) -> StorageReadResult[BrokerReconciliationReportRecord]:
        row = _read_one_by_column(
            self._connection,
            broker_reconciliation_reports,
            "broker_reconciliation_report_id",
            broker_reconciliation_report_id,
        )
        if row is None:
            return StorageReadResult(
                False,
                None,
                broker_reconciliation_reports.name,
                "Reconciliatierapport niet gevonden.",
            )
        return StorageReadResult(
            True,
            BrokerReconciliationReportRecord(**dict(row)),
            broker_reconciliation_reports.name,
            "Reconciliatierapport gevonden.",
        )

    def list_reports_for_sync_run(
        self, broker_sync_run_id: str
    ) -> StorageListResult[BrokerReconciliationReportRecord]:
        rows = _read_many_by_column(
            self._connection,
            broker_reconciliation_reports,
            "broker_sync_run_id",
            broker_sync_run_id,
        )
        return StorageListResult(
            tuple(BrokerReconciliationReportRecord(**dict(row)) for row in rows),
            broker_reconciliation_reports.name,
            "Reconciliatierapporten opgehaald.",
        )

    def list_differences_for_report(
        self, broker_reconciliation_report_id: str
    ) -> StorageListResult[BrokerReconciliationDifferenceRecord]:
        rows = _read_many_by_column(
            self._connection,
            broker_reconciliation_differences,
            "broker_reconciliation_report_id",
            broker_reconciliation_report_id,
        )
        records: list[BrokerReconciliationDifferenceRecord] = []
        for row in rows:
            values = dict(row)
            values["source_reference_ids_json"] = _json_tuple_or_none(
                values.get("source_reference_ids_json")
            )
            values["audit_event_ids_json"] = _json_tuple_or_none(values.get("audit_event_ids_json"))
            records.append(BrokerReconciliationDifferenceRecord(**values))
        return StorageListResult(
            tuple(records),
            broker_reconciliation_differences.name,
            "Reconciliatieverschillen opgehaald.",
        )

    def save_report(self, record: BrokerReconciliationReportRecord) -> StorageWriteResult:
        self._insert(broker_reconciliation_reports, asdict(record))
        return StorageWriteResult(
            True,
            record.broker_reconciliation_report_id,
            broker_reconciliation_reports.name,
            True,
            "Reconciliatierapport opgeslagen.",
        )

    def save_difference(self, record: BrokerReconciliationDifferenceRecord) -> StorageWriteResult:
        values = asdict(record)
        values["source_reference_ids_json"] = _json_list_or_none(record.source_reference_ids_json)
        values["audit_event_ids_json"] = _json_list_or_none(record.audit_event_ids_json)
        self._insert(broker_reconciliation_differences, values)
        return StorageWriteResult(
            True,
            record.broker_reconciliation_difference_id,
            broker_reconciliation_differences.name,
            True,
            "Reconciliatieverschil opgeslagen.",
        )


class SqlAlchemyExternalBrokerActivityRepository(_Base):
    def get_by_id(
        self, external_broker_activity_id: str
    ) -> StorageReadResult[ExternalBrokerActivityRecord]:
        row = _read_one_by_column(
            self._connection,
            external_broker_activities,
            "external_broker_activity_id",
            external_broker_activity_id,
        )
        if row is None:
            return StorageReadResult(
                False,
                None,
                external_broker_activities.name,
                "Externe brokeractiviteit niet gevonden.",
            )

        values = dict(row)
        values["source_reference_ids_json"] = _json_tuple_or_none(
            values.get("source_reference_ids_json")
        )
        values["audit_event_ids_json"] = _json_tuple_or_none(values.get("audit_event_ids_json"))
        return StorageReadResult(
            True,
            ExternalBrokerActivityRecord(**values),
            external_broker_activities.name,
            "Externe brokeractiviteit gevonden.",
        )

    def list_for_account(
        self, broker_account_id: str
    ) -> StorageListResult[ExternalBrokerActivityRecord]:
        rows = _read_many_by_column(
            self._connection,
            external_broker_activities,
            "broker_account_id",
            broker_account_id,
        )
        records: list[ExternalBrokerActivityRecord] = []
        for row in rows:
            values = dict(row)
            values["source_reference_ids_json"] = _json_tuple_or_none(
                values.get("source_reference_ids_json")
            )
            values["audit_event_ids_json"] = _json_tuple_or_none(values.get("audit_event_ids_json"))
            records.append(ExternalBrokerActivityRecord(**values))
        return StorageListResult(
            tuple(records),
            external_broker_activities.name,
            "Externe brokeractiviteiten opgehaald.",
        )

    def save_external_activity(self, record: ExternalBrokerActivityRecord) -> StorageWriteResult:
        values = asdict(record)
        values["source_reference_ids_json"] = _json_list_or_none(record.source_reference_ids_json)
        values["audit_event_ids_json"] = _json_list_or_none(record.audit_event_ids_json)
        self._insert(external_broker_activities, values)
        return StorageWriteResult(
            True,
            record.external_broker_activity_id,
            external_broker_activities.name,
            True,
            "Externe brokeractiviteit opgeslagen.",
        )


class SqlAlchemyResearchSourceArchiveRepository(_Base):
    def save_asset_master_record(self, record: AssetMasterRecord) -> AssetMasterRecord:
        values = asdict(record)
        values["source_reference_ids_json"] = _json_list_or_none(record.source_reference_ids_json)
        values["audit_context_json"] = (
            None if record.audit_context_json is None else json.dumps(record.audit_context_json)
        )
        self._insert(asset_master_records, values)
        return record

    def get_asset_by_asset_id(self, asset_id: str) -> AssetMasterRecord | None:
        row = _read_one_by_column(self._connection, asset_master_records, "asset_id", asset_id)
        return None if row is None else _row_to_asset_master_record(row)

    def get_asset_by_canonical_symbol(self, canonical_symbol: str) -> AssetMasterRecord | None:
        row = _read_one_by_column(
            self._connection, asset_master_records, "canonical_symbol", canonical_symbol
        )
        return None if row is None else _row_to_asset_master_record(row)

    def list_asset_master_records(self) -> tuple[AssetMasterRecord, ...]:
        rows = self._connection.execute(select(asset_master_records)).mappings().all()
        return tuple(_row_to_asset_master_record(row) for row in rows)

    def save_asset_identifier_alias(
        self, record: AssetIdentifierAliasRecord
    ) -> AssetIdentifierAliasRecord:
        self._insert(asset_identifier_aliases, asdict(record))
        return record

    def list_asset_identifier_aliases(
        self, asset_id: str
    ) -> tuple[AssetIdentifierAliasRecord, ...]:
        rows = _read_many_by_column(
            self._connection, asset_identifier_aliases, "asset_id", asset_id
        )
        return tuple(AssetIdentifierAliasRecord(**dict(row)) for row in rows)

    def save_research_source(self, record: ResearchSourceRecord) -> ResearchSourceRecord:
        self._insert(research_sources, asdict(record))
        return record

    def get_research_source(self, library_source_id: str) -> ResearchSourceRecord | None:
        row = _read_one_by_column(
            self._connection, research_sources, "library_source_id", library_source_id
        )
        return None if row is None else ResearchSourceRecord(**dict(row))

    def list_research_sources_for_asset(
        self, asset_symbol: str
    ) -> tuple[ResearchSourceRecord, ...]:
        rows = _read_many_by_column(
            self._connection, research_sources, "asset_symbol", asset_symbol
        )
        return tuple(ResearchSourceRecord(**dict(row)) for row in rows)

    def list_active_research_sources(self) -> tuple[ResearchSourceRecord, ...]:
        statement = select(research_sources).where(research_sources.c.archived_at.is_(None))
        rows = self._connection.execute(statement).mappings().all()
        return tuple(ResearchSourceRecord(**dict(row)) for row in rows)

    def save_uploaded_file_metadata(
        self, record: ResearchUploadedFileMetadataRecord
    ) -> ResearchUploadedFileMetadataRecord:
        self._insert(research_uploaded_file_metadata, asdict(record))
        return record

    def get_uploaded_file_metadata(
        self, library_source_id: str
    ) -> ResearchUploadedFileMetadataRecord | None:
        row = _read_one_by_column(
            self._connection,
            research_uploaded_file_metadata,
            "library_source_id",
            library_source_id,
        )
        return None if row is None else ResearchUploadedFileMetadataRecord(**dict(row))

    def save_url_metadata(self, record: ResearchUrlMetadataRecord) -> ResearchUrlMetadataRecord:
        self._insert(research_url_metadata, asdict(record))
        return record

    def get_url_metadata(self, library_source_id: str) -> ResearchUrlMetadataRecord | None:
        row = _read_one_by_column(
            self._connection, research_url_metadata, "library_source_id", library_source_id
        )
        return None if row is None else ResearchUrlMetadataRecord(**dict(row))

    def save_user_note(self, record: ResearchUserNoteRecord) -> ResearchUserNoteRecord:
        self._insert(research_user_notes, asdict(record))
        return record

    def get_user_note(self, library_source_id: str) -> ResearchUserNoteRecord | None:
        row = _read_one_by_column(
            self._connection, research_user_notes, "library_source_id", library_source_id
        )
        return None if row is None else ResearchUserNoteRecord(**dict(row))

    def save_document_set(self, record: ResearchDocumentSetRecord) -> ResearchDocumentSetRecord:
        self._insert(research_document_sets, asdict(record))
        return record

    def get_document_set(self, document_set_id: str) -> ResearchDocumentSetRecord | None:
        row = _read_one_by_column(
            self._connection, research_document_sets, "document_set_id", document_set_id
        )
        return None if row is None else ResearchDocumentSetRecord(**dict(row))

    def save_document_set_member(
        self, record: ResearchDocumentSetMemberRecord
    ) -> ResearchDocumentSetMemberRecord:
        self._insert(research_document_set_members, asdict(record))
        return record

    def list_document_set_members(
        self, document_set_id: str
    ) -> tuple[ResearchDocumentSetMemberRecord, ...]:
        statement = (
            select(research_document_set_members)
            .where(research_document_set_members.c.document_set_id == document_set_id)
            .order_by(
                research_document_set_members.c.sort_order.asc(),
                research_document_set_members.c.created_at.asc(),
            )
        )
        rows = self._connection.execute(statement).mappings().all()
        return tuple(ResearchDocumentSetMemberRecord(**dict(row)) for row in rows)

    def save_document_classification(
        self, record: ResearchDocumentClassificationRecord
    ) -> ResearchDocumentClassificationRecord:
        self._insert(research_document_classifications, asdict(record))
        return record

    def get_latest_classification(
        self, library_source_id: str
    ) -> ResearchDocumentClassificationRecord | None:
        statement = (
            select(research_document_classifications)
            .where(research_document_classifications.c.library_source_id == library_source_id)
            .order_by(
                research_document_classifications.c.classified_at.desc(),
                research_document_classifications.c.classification_id.desc(),
            )
        )
        row = self._connection.execute(statement).mappings().first()
        return None if row is None else ResearchDocumentClassificationRecord(**dict(row))


    def save_source_to_asset_link(
        self, record: SourceToAssetLinkRecord
    ) -> SourceToAssetLinkRecord:
        values = asdict(record)
        values["audit_context_json"] = (
            None if record.audit_context_json is None else json.dumps(record.audit_context_json)
        )
        self._insert(source_to_asset_links, values)
        return record

    def list_source_to_asset_links_for_asset(
        self, asset_id: str
    ) -> tuple[SourceToAssetLinkRecord, ...]:
        rows = (
            self._connection.execute(
                select(source_to_asset_links)
                .where(source_to_asset_links.c.asset_id == asset_id)
                .order_by(
                    source_to_asset_links.c.created_at.desc(),
                    source_to_asset_links.c.link_id.desc(),
                )
            )
            .mappings()
            .all()
        )
        return tuple(_row_to_source_to_asset_link_record(row) for row in rows)

    def save_source_asset_link(
        self, record: ResearchSourceAssetLinkRecord
    ) -> ResearchSourceAssetLinkRecord:
        self._insert(research_source_asset_links, asdict(record))
        return record

    def list_asset_links_for_source(
        self, library_source_id: str
    ) -> tuple[ResearchSourceAssetLinkRecord, ...]:
        rows = _read_many_by_column(
            self._connection, research_source_asset_links, "library_source_id", library_source_id
        )
        return tuple(ResearchSourceAssetLinkRecord(**dict(row)) for row in rows)

    def list_unconfirmed_detected_asset_links(
        self,
    ) -> tuple[ResearchSourceAssetLinkRecord, ...]:
        statement = select(research_source_asset_links).where(
            research_source_asset_links.c.link_type == "detected_new_asset",
            research_source_asset_links.c.requires_user_confirmation.is_(True),
            research_source_asset_links.c.confirmed_by_user.is_(False),
        )
        rows = self._connection.execute(statement).mappings().all()
        return tuple(ResearchSourceAssetLinkRecord(**dict(row)) for row in rows)

    def save_processing_status(
        self, record: ResearchSourceProcessingStatusRecord
    ) -> ResearchSourceProcessingStatusRecord:
        self._insert(research_source_processing_status, asdict(record))
        return record

    def get_latest_processing_status(
        self, library_source_id: str
    ) -> ResearchSourceProcessingStatusRecord | None:
        statement = (
            select(research_source_processing_status)
            .where(research_source_processing_status.c.library_source_id == library_source_id)
            .order_by(
                research_source_processing_status.c.checked_at.desc(),
                research_source_processing_status.c.processing_id.desc(),
            )
        )
        row = self._connection.execute(statement).mappings().first()
        return None if row is None else ResearchSourceProcessingStatusRecord(**dict(row))

    def save_prompt_injection_scan(
        self, record: ResearchSourcePromptInjectionScanRecord
    ) -> ResearchSourcePromptInjectionScanRecord:
        values = asdict(record)
        values["detected_signals_json"] = _json_list_or_none(record.detected_signals_json)
        self._insert(research_source_prompt_injection_scans, values)
        return record

    def get_latest_prompt_injection_scan(
        self, library_source_id: str
    ) -> ResearchSourcePromptInjectionScanRecord | None:
        statement = (
            select(research_source_prompt_injection_scans)
            .where(research_source_prompt_injection_scans.c.library_source_id == library_source_id)
            .order_by(
                research_source_prompt_injection_scans.c.checked_at.desc(),
                research_source_prompt_injection_scans.c.scan_id.desc(),
            )
        )
        row = self._connection.execute(statement).mappings().first()
        if row is None:
            return None
        values = dict(row)
        values["detected_signals_json"] = _json_tuple_or_none(values.get("detected_signals_json"))
        return ResearchSourcePromptInjectionScanRecord(**values)

    def save_source_credibility_assessment(
        self, record: ResearchSourceCredibilityAssessmentRecord
    ) -> ResearchSourceCredibilityAssessmentRecord:
        values = asdict(record)
        values["credibility_signals_json"] = (
            None
            if record.credibility_signals_json is None
            else json.dumps(list(record.credibility_signals_json))
        )
        self._insert(research_source_credibility_assessments, values)
        return record

    def get_latest_source_credibility_assessment(
        self, library_source_id: str
    ) -> ResearchSourceCredibilityAssessmentRecord | None:
        statement = (
            select(research_source_credibility_assessments)
            .where(research_source_credibility_assessments.c.library_source_id == library_source_id)
            .order_by(
                research_source_credibility_assessments.c.checked_at.desc(),
                research_source_credibility_assessments.c.assessment_id.desc(),
            )
        )
        row = self._connection.execute(statement).mappings().first()
        if row is None:
            return None
        values = dict(row)
        raw_signals = values.get("credibility_signals_json")
        values["credibility_signals_json"] = (
            None if raw_signals is None else tuple(json.loads(raw_signals))
        )
        return ResearchSourceCredibilityAssessmentRecord(**values)

    def save_source_evidence_item(
        self, record: ResearchSourceEvidenceItemRecord
    ) -> ResearchSourceEvidenceItemRecord:
        self._insert(research_source_evidence_items, asdict(record))
        return record

    def list_source_evidence_items(
        self, library_source_id: str
    ) -> tuple[ResearchSourceEvidenceItemRecord, ...]:
        statement = (
            select(research_source_evidence_items)
            .where(research_source_evidence_items.c.library_source_id == library_source_id)
            .order_by(
                research_source_evidence_items.c.extracted_at.desc(),
                research_source_evidence_items.c.created_at.desc(),
                research_source_evidence_items.c.evidence_item_id.desc(),
            )
        )
        rows = self._connection.execute(statement).mappings().all()
        return tuple(ResearchSourceEvidenceItemRecord(**dict(row)) for row in rows)

    def save_source_evidence_ledger_link(
        self, record: ResearchSourceEvidenceLedgerLinkRecord
    ) -> ResearchSourceEvidenceLedgerLinkRecord:
        self._insert(research_source_evidence_ledger_links, asdict(record))
        return record

    def list_source_evidence_ledger_links(
        self, library_source_id: str
    ) -> tuple[ResearchSourceEvidenceLedgerLinkRecord, ...]:
        statement = (
            select(research_source_evidence_ledger_links)
            .where(research_source_evidence_ledger_links.c.library_source_id == library_source_id)
            .order_by(
                research_source_evidence_ledger_links.c.created_at.desc(),
                research_source_evidence_ledger_links.c.link_id.desc(),
            )
        )
        rows = self._connection.execute(statement).mappings().all()
        return tuple(ResearchSourceEvidenceLedgerLinkRecord(**dict(row)) for row in rows)

    def list_evidence_item_ledger_links(
        self, evidence_item_id: str
    ) -> tuple[ResearchSourceEvidenceLedgerLinkRecord, ...]:
        statement = (
            select(research_source_evidence_ledger_links)
            .where(research_source_evidence_ledger_links.c.evidence_item_id == evidence_item_id)
            .order_by(
                research_source_evidence_ledger_links.c.created_at.desc(),
                research_source_evidence_ledger_links.c.link_id.desc(),
            )
        )
        rows = self._connection.execute(statement).mappings().all()
        return tuple(ResearchSourceEvidenceLedgerLinkRecord(**dict(row)) for row in rows)

    def save_research_gate_outcome(
        self, record: ResearchGateOutcomeRecord
    ) -> ResearchGateOutcomeRecord:
        values = asdict(record)
        values["source_reference_ids_json"] = (
            None
            if record.source_reference_ids_json is None
            else json.dumps(list(record.source_reference_ids_json))
        )
        values["audit_context_json"] = (
            None if record.audit_context_json is None else json.dumps(record.audit_context_json)
        )
        self._insert(research_gate_outcomes, values)
        return record

    def list_research_gate_outcomes_by_source(
        self, library_source_id: str
    ) -> tuple[ResearchGateOutcomeRecord, ...]:
        rows = (
            self._connection.execute(
                select(research_gate_outcomes)
                .where(research_gate_outcomes.c.library_source_id == library_source_id)
                .order_by(
                    research_gate_outcomes.c.checked_at.desc(),
                    research_gate_outcomes.c.gate_outcome_id.desc(),
                )
            )
            .mappings()
            .all()
        )
        return tuple(_row_to_gate_outcome_record(row) for row in rows)

    def list_research_gate_outcomes_by_evidence_item(
        self, evidence_item_id: str
    ) -> tuple[ResearchGateOutcomeRecord, ...]:
        rows = (
            self._connection.execute(
                select(research_gate_outcomes)
                .where(research_gate_outcomes.c.evidence_item_id == evidence_item_id)
                .order_by(
                    research_gate_outcomes.c.checked_at.desc(),
                    research_gate_outcomes.c.gate_outcome_id.desc(),
                )
            )
            .mappings()
            .all()
        )
        return tuple(_row_to_gate_outcome_record(row) for row in rows)

    def save_source_conflict_finding(
        self, record: ResearchSourceConflictFindingRecord
    ) -> ResearchSourceConflictFindingRecord:
        values = asdict(record)
        values["source_reference_ids_json"] = (
            None
            if record.source_reference_ids_json is None
            else json.dumps(list(record.source_reference_ids_json))
        )
        values["audit_context_json"] = (
            None if record.audit_context_json is None else json.dumps(record.audit_context_json)
        )
        self._insert(research_source_conflict_findings, values)
        return record

    def list_conflict_findings_by_source(
        self, primary_source_id: str
    ) -> tuple[ResearchSourceConflictFindingRecord, ...]:
        rows = (
            self._connection.execute(
                select(research_source_conflict_findings)
                .where(research_source_conflict_findings.c.primary_source_id == primary_source_id)
                .order_by(
                    research_source_conflict_findings.c.checked_at.desc(),
                    research_source_conflict_findings.c.conflict_finding_id.desc(),
                )
            )
            .mappings()
            .all()
        )
        return tuple(_row_to_conflict_finding_record(row) for row in rows)

    def list_conflict_findings_by_evidence_item(
        self, evidence_item_id: str
    ) -> tuple[ResearchSourceConflictFindingRecord, ...]:
        rows = (
            self._connection.execute(
                select(research_source_conflict_findings).where(
                    (
                        research_source_conflict_findings.c.primary_evidence_item_id
                        == evidence_item_id
                    )
                    | (
                        research_source_conflict_findings.c.conflicting_evidence_item_id
                        == evidence_item_id
                    )
                )
            )
            .mappings()
            .all()
        )
        return tuple(_row_to_conflict_finding_record(row) for row in rows)

    def list_conflict_findings_by_asset_symbol(
        self, asset_symbol: str
    ) -> tuple[ResearchSourceConflictFindingRecord, ...]:
        rows = (
            self._connection.execute(
                select(research_source_conflict_findings)
                .where(research_source_conflict_findings.c.asset_symbol == asset_symbol)
                .order_by(
                    research_source_conflict_findings.c.checked_at.desc(),
                    research_source_conflict_findings.c.conflict_finding_id.desc(),
                )
            )
            .mappings()
            .all()
        )
        return tuple(_row_to_conflict_finding_record(row) for row in rows)

    def save_extracted_text(
        self, record: ResearchExtractedTextRecord
    ) -> ResearchExtractedTextRecord:
        self._insert(research_extracted_texts, asdict(record))
        return record

    def get_extracted_text(self, extracted_text_id: str) -> ResearchExtractedTextRecord | None:
        row = _read_one_by_column(
            self._connection, research_extracted_texts, "extracted_text_id", extracted_text_id
        )
        return None if row is None else ResearchExtractedTextRecord(**dict(row))

    def list_extracted_texts_for_source(
        self, library_source_id: str
    ) -> tuple[ResearchExtractedTextRecord, ...]:
        statement = (
            select(research_extracted_texts)
            .where(research_extracted_texts.c.library_source_id == library_source_id)
            .order_by(
                research_extracted_texts.c.created_at.asc(),
                research_extracted_texts.c.extracted_text_id.asc(),
            )
        )
        rows = self._connection.execute(statement).mappings().all()
        return tuple(ResearchExtractedTextRecord(**dict(row)) for row in rows)

    def get_latest_extracted_text_for_source(
        self, library_source_id: str
    ) -> ResearchExtractedTextRecord | None:
        statement = (
            select(research_extracted_texts)
            .where(research_extracted_texts.c.library_source_id == library_source_id)
            .order_by(
                research_extracted_texts.c.extracted_at.desc().nullslast(),
                research_extracted_texts.c.created_at.desc(),
                research_extracted_texts.c.extracted_text_id.desc(),
            )
        )
        row = self._connection.execute(statement).mappings().first()
        return None if row is None else ResearchExtractedTextRecord(**dict(row))


class SqlAlchemyBrokerStorageUnitOfWork:
    def __init__(self, connection: Connection, readiness_report: MigrationReadinessReport) -> None:
        self._connection = connection
        self._readiness_report = readiness_report
        self.broker_accounts = SqlAlchemyBrokerAccountRepository(connection, readiness_report)
        self.broker_sync_runs = SqlAlchemyBrokerSyncRunRepository(connection, readiness_report)
        self.broker_snapshots = SqlAlchemyBrokerSnapshotRepository(connection, readiness_report)
        self.broker_reconciliation = SqlAlchemyBrokerReconciliationRepository(
            connection,
            readiness_report,
        )
        self.external_broker_activities = SqlAlchemyExternalBrokerActivityRepository(
            connection,
            readiness_report,
        )

    def health(self) -> RepositoryHealthStatus:
        return RepositoryHealthStatus(
            available=True,
            connected=self._readiness_report.database_connected,
            migrations_current=(self._readiness_report.status.value == "migrations_current"),
            read_only=(not migration_readiness_is_safe_to_write(self._readiness_report)),
            explanation_nl="Repository-status op basis van aangeleverde readiness.",
        )

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class SqlAlchemySystemEventRepository(_Base):
    def create_event(self, request: CreateSystemEventRequest) -> StorageWriteResult:
        self._insert(
            system_events,
            {
                "system_event_id": request.system_event_id,
                "created_at": request.created_at,
                "severity": request.severity,
                "category": request.category,
                "source_service": request.source_service,
                "source_component": request.source_component,
                "event_code": request.event_code,
                "title_nl": request.title_nl,
                "message_nl": request.message_nl,
                "help_nl": request.help_nl,
                "technical_summary": request.technical_summary,
                "redacted_details_json": request.redacted_details_json,
                "stack_trace_redacted": request.stack_trace_redacted,
                "related_entity_type": request.related_entity_type,
                "related_entity_id": request.related_entity_id,
                "blocks_suggestions": request.blocks_suggestions,
                "blocks_writes": request.blocks_writes,
                "blocks_ai_explanation": request.blocks_ai_explanation,
                "status": request.status,
                "resolved_at": None,
                "archived_at": None,
                "copied_for_codex_at": None,
                "explanation_nl": request.explanation_nl,
            },
        )
        return StorageWriteResult(
            True,
            request.system_event_id,
            system_events.name,
            True,
            "Systeemmelding opgeslagen.",
        )

    def get_by_id(self, system_event_id: str) -> StorageReadResult[SystemEventRecord]:
        row = _read_one_by_column(
            self._connection,
            system_events,
            "system_event_id",
            system_event_id,
        )
        if row is None:
            return StorageReadResult(
                False,
                None,
                system_events.name,
                "Systeemmelding niet gevonden.",
            )
        return StorageReadResult(
            True,
            SystemEventRecord(**dict(row)),
            system_events.name,
            "Systeemmelding gevonden.",
        )

    def list_open_events(self) -> StorageListResult[SystemEventRecord]:
        rows = (
            self._connection.execute(select(system_events).where(system_events.c.status == "open"))
            .mappings()
            .all()
        )
        return StorageListResult(
            records=tuple(SystemEventRecord(**dict(row)) for row in rows),
            table_name=system_events.name,
            explanation_nl="Open systeemmeldingen opgehaald.",
        )

    def mark_resolved(
        self, system_event_id: str, *, reason_nl: str | None = None
    ) -> StorageWriteResult:
        return self._mark_event_status(
            system_event_id=system_event_id,
            status="resolved",
            reason_nl=reason_nl,
            explanation_nl="Systeemmelding gemarkeerd als opgelost.",
        )

    def mark_archived(
        self, system_event_id: str, *, reason_nl: str | None = None
    ) -> StorageWriteResult:
        return self._mark_event_status(
            system_event_id=system_event_id,
            status="archived",
            reason_nl=reason_nl,
            explanation_nl="Systeemmelding gearchiveerd.",
        )

    def _mark_event_status(
        self,
        *,
        system_event_id: str,
        status: str,
        reason_nl: str | None,
        explanation_nl: str,
    ) -> StorageWriteResult:
        ensure_persistence_allowed(self._readiness_report)
        row = _read_one_by_column(
            self._connection,
            system_events,
            "system_event_id",
            system_event_id,
        )
        if row is None:
            return StorageWriteResult(
                accepted=False,
                record_id=None,
                table_name=system_events.name,
                audit_required=True,
                explanation_nl="Systeemmelding niet gevonden.",
            )

        now = datetime.now(UTC)
        cleaned_reason = reason_nl.strip() if reason_nl else ""
        stored_explanation_nl = cleaned_reason or explanation_nl
        update_values: dict[str, Any] = {
            "status": status,
            "explanation_nl": stored_explanation_nl,
        }
        if status == "resolved":
            update_values["resolved_at"] = now
        if status == "archived":
            update_values["archived_at"] = now

        self._connection.execute(
            system_events.update()
            .where(system_events.c.system_event_id == system_event_id)
            .values(**update_values)
        )
        return StorageWriteResult(
            accepted=True,
            record_id=system_event_id,
            table_name=system_events.name,
            audit_required=True,
            explanation_nl=explanation_nl,
        )
