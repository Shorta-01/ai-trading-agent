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
    asset_listings,
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
    ibkr_account_cash_snapshots,
    ibkr_execution_snapshots,
    ibkr_open_order_snapshots,
    ibkr_position_snapshots,
    ibkr_sync_runs,
    fx_rate_snapshots,
    asset_action_draft_events,
    asset_action_draft_submissions,
    asset_action_drafts,
    asset_decision_packages,
    asset_forecasts,
    asset_suggestions,
    market_data_bars,
    market_data_snapshots,
    prediction_diary_entries,
    market_data_latest_snapshots,
    paper_portfolio_setups,
    request_logs,
    provider_sources,
    freshness_audit_records,
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
    AssetActionDraftEventRecord,
    AssetActionDraftRecord,
    AssetActionDraftSubmissionRecord,
    AssetDecisionPackageRecord,
    PredictionDiaryEntryRecord,
    AssetForecastRecord,
    AssetIdentifierAliasRecord,
    AssetListingRecord,
    AssetMasterRecord,
    AssetSuggestionRecord,
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
    MarketDataLatestSnapshotRecord,
    MarketDataSnapshotRecord,
    PaperPortfolioSetupRecord,
    RequestLogRecord,
    ProviderSourceRecord,
    FreshnessAuditRecord,
    IbkrAccountCashSnapshotRecord,
    IbkrExecutionSnapshotRecord,
    IbkrOpenOrderSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
    FxRateSnapshotRecord,
    MarketDataBarRecord,
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


def _row_to_asset_listing_record(row: Any) -> AssetListingRecord:
    values = dict(row)
    values["source_reference_ids_json"] = _json_tuple_or_none(
        values.get("source_reference_ids_json")
    )
    values["audit_context_json"] = (
        None if values.get("audit_context_json") is None else dict(values["audit_context_json"])
    )
    return AssetListingRecord(**values)


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
    def save_latest_market_data_snapshot(
        self, record: MarketDataLatestSnapshotRecord
    ) -> StorageWriteResult:
        self._insert(market_data_latest_snapshots, asdict(record))
        return StorageWriteResult(
            True,
            record.snapshot_id,
            market_data_latest_snapshots.name,
            True,
            "Latest market-data snapshot opgeslagen.",
        )

    def get_latest_market_data_snapshot_by_conid(
        self, ibkr_conid: str
    ) -> StorageReadResult[MarketDataLatestSnapshotRecord]:
        row = (
            self._connection.execute(
                select(market_data_latest_snapshots)
                .where(market_data_latest_snapshots.c.ibkr_conid == ibkr_conid)
                .order_by(
                    market_data_latest_snapshots.c.stored_at.desc(),
                    market_data_latest_snapshots.c.provider_as_of.desc().nullslast(),
                )
                .limit(1)
            )
            .mappings()
            .first()
        )
        if row is None:
            return StorageReadResult(
                False,
                None,
                market_data_latest_snapshots.name,
                "Geen latest market-data snapshot gevonden voor conid.",
            )
        return StorageReadResult(
            True,
            MarketDataLatestSnapshotRecord(**dict(row)),
            market_data_latest_snapshots.name,
            "Latest market-data snapshot opgehaald voor conid.",
        )

    def list_latest_market_data_snapshots_by_conids(
        self, conids: tuple[str, ...]
    ) -> StorageListResult[MarketDataLatestSnapshotRecord]:
        if not conids:
            return StorageListResult(
                (),
                market_data_latest_snapshots.name,
                "Geen conids opgegeven.",
            )
        rows = (
            self._connection.execute(
                select(market_data_latest_snapshots)
                .where(market_data_latest_snapshots.c.ibkr_conid.in_(conids))
                .order_by(
                    market_data_latest_snapshots.c.ibkr_conid.asc(),
                    market_data_latest_snapshots.c.stored_at.desc(),
                    market_data_latest_snapshots.c.provider_as_of.desc().nullslast(),
                )
            )
            .mappings()
            .all()
        )
        latest: dict[str, MarketDataLatestSnapshotRecord] = {}
        for row in rows:
            rec = MarketDataLatestSnapshotRecord(**dict(row))
            latest.setdefault(rec.ibkr_conid, rec)
        return StorageListResult(
            tuple(latest.values()),
            market_data_latest_snapshots.name,
            "Latest market-data snapshots opgehaald voor conids.",
        )

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


class SqlAlchemyIbkrSyncSnapshotRepository(_Base):
    def save_ibkr_sync_run(self, record: IbkrSyncRunRecord) -> None:
        self._insert(ibkr_sync_runs, asdict(record))

    def get_ibkr_sync_run(self, sync_run_id: str) -> IbkrSyncRunRecord | None:
        row = _read_one_by_column(self._connection, ibkr_sync_runs, "sync_run_id", sync_run_id)
        return None if row is None else IbkrSyncRunRecord(**dict(row))

    def get_latest_ibkr_sync_run(self) -> IbkrSyncRunRecord | None:
        row = (
            self._connection.execute(
                select(ibkr_sync_runs).order_by(
                    ibkr_sync_runs.c.completed_at.desc().nullslast(),
                    ibkr_sync_runs.c.stored_at.desc(),
                    ibkr_sync_runs.c.sync_run_id.desc(),
                )
            )
            .mappings()
            .first()
        )
        return None if row is None else IbkrSyncRunRecord(**dict(row))

    def list_ibkr_sync_runs(self, limit: int = 50) -> list[IbkrSyncRunRecord]:
        rows = (
            self._connection.execute(
                select(ibkr_sync_runs)
                .order_by(
                    ibkr_sync_runs.c.completed_at.desc().nullslast(),
                    ibkr_sync_runs.c.stored_at.desc(),
                    ibkr_sync_runs.c.sync_run_id.desc(),
                )
                .limit(limit)
            )
            .mappings()
            .all()
        )
        return [IbkrSyncRunRecord(**dict(row)) for row in rows]

    def save_ibkr_account_cash_snapshots(
        self,
        sync_run_id: str,
        records: list[IbkrAccountCashSnapshotRecord],
    ) -> None:
        for record in records:
            if record.sync_run_id != sync_run_id:
                raise ValueError("sync_run_id mismatch voor cash snapshot.")
            self._insert(ibkr_account_cash_snapshots, asdict(record))

    def list_ibkr_account_cash_snapshots(
        self,
        sync_run_id: str,
    ) -> list[IbkrAccountCashSnapshotRecord]:
        rows = (
            self._connection.execute(
                select(ibkr_account_cash_snapshots)
                .where(ibkr_account_cash_snapshots.c.sync_run_id == sync_run_id)
                .order_by(
                    ibkr_account_cash_snapshots.c.stored_at.asc(),
                    ibkr_account_cash_snapshots.c.snapshot_id.asc(),
                )
            )
            .mappings()
            .all()
        )
        return [IbkrAccountCashSnapshotRecord(**dict(row)) for row in rows]

    def save_ibkr_position_snapshots(
        self, sync_run_id: str, records: list[IbkrPositionSnapshotRecord]
    ) -> None:
        for record in records:
            if record.sync_run_id != sync_run_id:
                raise ValueError("sync_run_id mismatch voor position snapshot.")
            self._insert(ibkr_position_snapshots, asdict(record))

    def list_ibkr_position_snapshots(self, sync_run_id: str) -> list[IbkrPositionSnapshotRecord]:
        rows = (
            self._connection.execute(
                select(ibkr_position_snapshots)
                .where(ibkr_position_snapshots.c.sync_run_id == sync_run_id)
                .order_by(
                    ibkr_position_snapshots.c.stored_at.asc(),
                    ibkr_position_snapshots.c.snapshot_id.asc(),
                )
            )
            .mappings()
            .all()
        )
        return [IbkrPositionSnapshotRecord(**dict(row)) for row in rows]

    def save_ibkr_open_order_snapshots(
        self, sync_run_id: str, records: list[IbkrOpenOrderSnapshotRecord]
    ) -> None:
        for record in records:
            if record.sync_run_id != sync_run_id:
                raise ValueError("sync_run_id mismatch voor open-order snapshot.")
            self._insert(ibkr_open_order_snapshots, asdict(record))

    def list_ibkr_open_order_snapshots(
        self, sync_run_id: str
    ) -> list[IbkrOpenOrderSnapshotRecord]:
        rows = (
            self._connection.execute(
                select(ibkr_open_order_snapshots)
                .where(ibkr_open_order_snapshots.c.sync_run_id == sync_run_id)
                .order_by(
                    ibkr_open_order_snapshots.c.stored_at.asc(),
                    ibkr_open_order_snapshots.c.snapshot_id.asc(),
                )
            )
            .mappings()
            .all()
        )
        return [IbkrOpenOrderSnapshotRecord(**dict(row)) for row in rows]

    def save_ibkr_execution_snapshots(
        self, sync_run_id: str, records: list[IbkrExecutionSnapshotRecord]
    ) -> None:
        for record in records:
            if record.sync_run_id != sync_run_id:
                raise ValueError("sync_run_id mismatch voor execution snapshot.")
            self._insert(ibkr_execution_snapshots, asdict(record))

    def list_ibkr_execution_snapshots(self, sync_run_id: str) -> list[IbkrExecutionSnapshotRecord]:
        rows = (
            self._connection.execute(
                select(ibkr_execution_snapshots)
                .where(ibkr_execution_snapshots.c.sync_run_id == sync_run_id)
                .order_by(
                    ibkr_execution_snapshots.c.stored_at.asc(),
                    ibkr_execution_snapshots.c.snapshot_id.asc(),
                )
            )
            .mappings()
            .all()
        )
        return [IbkrExecutionSnapshotRecord(**dict(row)) for row in rows]

    def save_fx_rate_snapshot(self, record: FxRateSnapshotRecord) -> None:
        values = asdict(record)
        normalized_base = record.base_currency.upper()
        normalized_quote = record.quote_currency.upper()
        values["base_currency"] = normalized_base
        values["quote_currency"] = normalized_quote
        values["pair"] = f"{normalized_base}/{normalized_quote}"
        self._insert(fx_rate_snapshots, values)

    def get_fx_rate_snapshot(self, snapshot_id: str) -> FxRateSnapshotRecord | None:
        row = _read_one_by_column(self._connection, fx_rate_snapshots, "snapshot_id", snapshot_id)
        return None if row is None else FxRateSnapshotRecord(**dict(row))

    def list_fx_rate_snapshots(self, limit: int = 100) -> list[FxRateSnapshotRecord]:
        rows = (
            self._connection.execute(
                select(fx_rate_snapshots)
                .order_by(
                    fx_rate_snapshots.c.as_of.desc(),
                    fx_rate_snapshots.c.received_at.desc(),
                    fx_rate_snapshots.c.stored_at.desc(),
                    fx_rate_snapshots.c.snapshot_id.desc(),
                )
                .limit(limit)
            )
            .mappings()
            .all()
        )
        return [FxRateSnapshotRecord(**dict(row)) for row in rows]

    def get_latest_fx_rate_snapshot(
        self, base_currency: str, quote_currency: str
    ) -> FxRateSnapshotRecord | None:
        row = (
            self._connection.execute(
                select(fx_rate_snapshots)
                .where(fx_rate_snapshots.c.base_currency == base_currency.upper())
                .where(fx_rate_snapshots.c.quote_currency == quote_currency.upper())
                .order_by(
                    fx_rate_snapshots.c.as_of.desc(),
                    fx_rate_snapshots.c.received_at.desc(),
                    fx_rate_snapshots.c.stored_at.desc(),
                    fx_rate_snapshots.c.snapshot_id.desc(),
                )
                .limit(1)
            )
            .mappings()
            .first()
        )
        return None if row is None else FxRateSnapshotRecord(**dict(row))

    def list_latest_fx_rate_snapshots_by_pairs(
        self, pairs: tuple[str, ...]
    ) -> list[FxRateSnapshotRecord]:
        latest_records: list[FxRateSnapshotRecord] = []
        for pair in pairs:
            base_currency, quote_currency = pair.split("/", maxsplit=1)
            latest = self.get_latest_fx_rate_snapshot(base_currency, quote_currency)
            if latest is not None:
                latest_records.append(latest)
        return latest_records


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

    def save_asset_listing(self, record: AssetListingRecord) -> AssetListingRecord:
        if self.get_asset_by_asset_id(record.asset_id) is None:
            raise ValueError("asset_id moet verwijzen naar een bestaande asset master identiteit.")
        values = asdict(record)
        values["source_reference_ids_json"] = _json_list_or_none(record.source_reference_ids_json)
        values["audit_context_json"] = (
            None if record.audit_context_json is None else json.dumps(record.audit_context_json)
        )
        self._insert(asset_listings, values)
        return record

    def get_asset_listing_by_listing_id(self, listing_id: str) -> AssetListingRecord | None:
        row = _read_one_by_column(self._connection, asset_listings, "listing_id", listing_id)
        return None if row is None else _row_to_asset_listing_record(row)

    def get_asset_listing_by_ibkr_conid(self, ibkr_conid: str) -> AssetListingRecord | None:
        row = _read_one_by_column(self._connection, asset_listings, "ibkr_conid", ibkr_conid)
        return None if row is None else _row_to_asset_listing_record(row)

    def list_asset_listings(self, asset_id: str | None = None) -> tuple[AssetListingRecord, ...]:
        statement = select(asset_listings)
        if asset_id is not None:
            statement = statement.where(asset_listings.c.asset_id == asset_id)
        rows = (
            self._connection.execute(statement.order_by(asset_listings.c.listing_id.asc()))
            .mappings()
            .all()
        )
        return tuple(_row_to_asset_listing_record(row) for row in rows)

    def search_asset_listings(self, query: str, limit: int = 20) -> tuple[AssetListingRecord, ...]:
        normalized = query.strip().lower()
        matches: list[AssetListingRecord] = []
        for record in self.list_asset_listings():
            haystack = [
                record.listing_id,
                record.asset_id,
                record.ibkr_conid or "",
                record.symbol,
                record.local_symbol or "",
                record.trading_class or "",
                record.exchange or "",
                record.primary_exchange or "",
                record.currency,
                record.security_type,
            ]
            if normalized and not any(normalized in item.lower() for item in haystack):
                continue
            matches.append(record)
            if len(matches) >= limit:
                break
        return tuple(matches)

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

    def save_source_to_asset_link(self, record: SourceToAssetLinkRecord) -> SourceToAssetLinkRecord:
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


def _bounded_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be positive.")
    return min(limit, 500)


class SqlAlchemyRequestAuditRepository(_Base):
    def save_request_log(self, record: RequestLogRecord) -> StorageWriteResult:
        self._insert(request_logs, asdict(record))
        return StorageWriteResult(
            True, record.request_log_id, request_logs.name, True, "Requestlog opgeslagen."
        )

    def get_request_log(self, request_log_id: str) -> StorageReadResult[RequestLogRecord]:
        row = _read_one_by_column(self._connection, request_logs, "request_log_id", request_log_id)
        if row is None:
            return StorageReadResult(False, None, request_logs.name, "Requestlog niet gevonden.")
        return StorageReadResult(
            True, RequestLogRecord(**dict(row)), request_logs.name, "Requestlog gevonden."
        )

    def list_request_logs(self, limit: int = 100) -> StorageListResult[RequestLogRecord]:
        rows = (
            self._connection.execute(
                select(request_logs)
                .order_by(request_logs.c.created_at.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        return StorageListResult(
            tuple(RequestLogRecord(**dict(r)) for r in rows),
            request_logs.name,
            "Requestlogs opgehaald.",
        )

    def save_provider_source(self, record: ProviderSourceRecord) -> StorageWriteResult:
        self._insert(provider_sources, asdict(record))
        return StorageWriteResult(
            True,
            record.provider_source_id,
            provider_sources.name,
            True,
            "Provider/source opgeslagen.",
        )

    def get_provider_source(
        self, provider_source_id: str
    ) -> StorageReadResult[ProviderSourceRecord]:
        row = _read_one_by_column(
            self._connection, provider_sources, "provider_source_id", provider_source_id
        )
        if row is None:
            return StorageReadResult(
                False, None, provider_sources.name, "Provider/source niet gevonden."
            )
        return StorageReadResult(
            True,
            ProviderSourceRecord(**dict(row)),
            provider_sources.name,
            "Provider/source gevonden.",
        )

    def list_provider_sources(self, limit: int = 100) -> StorageListResult[ProviderSourceRecord]:
        rows = (
            self._connection.execute(
                select(provider_sources)
                .order_by(provider_sources.c.updated_at.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        return StorageListResult(
            tuple(ProviderSourceRecord(**dict(r)) for r in rows),
            provider_sources.name,
            "Provider/sources opgehaald.",
        )

    def save_freshness_audit(self, record: FreshnessAuditRecord) -> StorageWriteResult:
        self._insert(freshness_audit_records, asdict(record))
        return StorageWriteResult(
            True,
            record.freshness_audit_id,
            freshness_audit_records.name,
            True,
            "Freshness-audit opgeslagen.",
        )

    def get_freshness_audit(
        self, freshness_audit_id: str
    ) -> StorageReadResult[FreshnessAuditRecord]:
        row = _read_one_by_column(
            self._connection, freshness_audit_records, "freshness_audit_id", freshness_audit_id
        )
        if row is None:
            return StorageReadResult(
                False, None, freshness_audit_records.name, "Freshness-audit niet gevonden."
            )
        return StorageReadResult(
            True,
            FreshnessAuditRecord(**dict(row)),
            freshness_audit_records.name,
            "Freshness-audit gevonden.",
        )

    def list_freshness_audits(self, limit: int = 100) -> StorageListResult[FreshnessAuditRecord]:
        rows = (
            self._connection.execute(
                select(freshness_audit_records)
                .order_by(freshness_audit_records.c.evaluated_at.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        return StorageListResult(
            tuple(FreshnessAuditRecord(**dict(r)) for r in rows),
            freshness_audit_records.name,
            "Freshness-audits opgehaald.",
        )


class SqlAlchemyMarketDataBarRepository(_Base):
    def save_market_data_bar(self, record: MarketDataBarRecord) -> StorageWriteResult:
        values = asdict(record)
        self._insert(market_data_bars, values)
        return StorageWriteResult(
            True,
            record.bar_id,
            market_data_bars.name,
            True,
            "Historische marktdata-bar opgeslagen.",
        )

    def save_market_data_bars(
        self, records: list[MarketDataBarRecord]
    ) -> StorageWriteResult:
        count = 0
        for record in records:
            self.save_market_data_bar(record)
            count += 1
        return StorageWriteResult(
            True,
            None,
            market_data_bars.name,
            True,
            f"{count} historische marktdata-bars opgeslagen.",
        )

    def list_market_data_bars_by_conid(
        self,
        ibkr_conid: str,
        *,
        interval_code: str = "1day",
        limit: int = 750,
    ) -> StorageListResult[MarketDataBarRecord]:
        rows = (
            self._connection.execute(
                select(market_data_bars)
                .where(market_data_bars.c.ibkr_conid == ibkr_conid)
                .where(market_data_bars.c.interval_code == interval_code)
                .order_by(market_data_bars.c.bar_date.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        records = tuple(MarketDataBarRecord(**dict(row)) for row in rows)
        # Caller expects chronological order; reverse the desc-sorted batch.
        ordered = tuple(reversed(records))
        return StorageListResult(
            ordered,
            market_data_bars.name,
            f"{len(ordered)} historische bars opgehaald.",
        )


class SqlAlchemyAssetForecastRepository(_Base):
    def save_asset_forecast(self, record: AssetForecastRecord) -> StorageWriteResult:
        values = asdict(record)
        self._insert(asset_forecasts, values)
        return StorageWriteResult(
            True,
            record.forecast_id,
            asset_forecasts.name,
            True,
            "Assetvoorspelling opgeslagen.",
        )

    def get_latest_asset_forecast_by_conid(
        self, ibkr_conid: str
    ) -> StorageReadResult[AssetForecastRecord]:
        row = (
            self._connection.execute(
                select(asset_forecasts)
                .where(asset_forecasts.c.ibkr_conid == ibkr_conid)
                .order_by(asset_forecasts.c.generated_at.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        if row is None:
            return StorageReadResult(
                False,
                None,
                asset_forecasts.name,
                "Geen assetvoorspelling gevonden voor conid.",
            )
        return StorageReadResult(
            True,
            AssetForecastRecord(**dict(row)),
            asset_forecasts.name,
            "Assetvoorspelling opgehaald voor conid.",
        )

    def list_latest_asset_forecasts_by_conids(
        self, conids: tuple[str, ...]
    ) -> StorageListResult[AssetForecastRecord]:
        if not conids:
            return StorageListResult((), asset_forecasts.name, "Geen conids opgegeven.")
        rows = (
            self._connection.execute(
                select(asset_forecasts)
                .where(asset_forecasts.c.ibkr_conid.in_(conids))
                .order_by(
                    asset_forecasts.c.ibkr_conid.asc(),
                    asset_forecasts.c.generated_at.desc(),
                )
            )
            .mappings()
            .all()
        )
        latest: dict[str, AssetForecastRecord] = {}
        for row in rows:
            record = AssetForecastRecord(**dict(row))
            if record.ibkr_conid not in latest:
                latest[record.ibkr_conid] = record
        ordered = tuple(latest[c] for c in conids if c in latest)
        return StorageListResult(
            ordered,
            asset_forecasts.name,
            f"{len(ordered)} assetvoorspellingen opgehaald.",
        )


class SqlAlchemyAssetSuggestionRepository(_Base):
    def save_asset_suggestion(
        self, record: AssetSuggestionRecord
    ) -> StorageWriteResult:
        values = asdict(record)
        # JSON columns must be plain lists (SQLite/Postgres JSON serialisation).
        drivers = values.get("drivers_json")
        if isinstance(drivers, tuple):
            values["drivers_json"] = list(drivers)
        blockers = values.get("blockers_json")
        if isinstance(blockers, tuple):
            values["blockers_json"] = list(blockers)
        self._insert(asset_suggestions, values)
        return StorageWriteResult(
            True,
            record.suggestion_id,
            asset_suggestions.name,
            True,
            "Assetsuggestie opgeslagen.",
        )

    def get_latest_asset_suggestion_by_conid(
        self, ibkr_conid: str
    ) -> StorageReadResult[AssetSuggestionRecord]:
        row = (
            self._connection.execute(
                select(asset_suggestions)
                .where(asset_suggestions.c.ibkr_conid == ibkr_conid)
                .order_by(asset_suggestions.c.generated_at.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        if row is None:
            return StorageReadResult(
                False,
                None,
                asset_suggestions.name,
                "Geen assetsuggestie gevonden voor conid.",
            )
        return StorageReadResult(
            True,
            _suggestion_from_row(row),
            asset_suggestions.name,
            "Assetsuggestie opgehaald voor conid.",
        )

    def list_latest_asset_suggestions_by_conids(
        self, conids: tuple[str, ...]
    ) -> StorageListResult[AssetSuggestionRecord]:
        if not conids:
            return StorageListResult((), asset_suggestions.name, "Geen conids opgegeven.")
        rows = (
            self._connection.execute(
                select(asset_suggestions)
                .where(asset_suggestions.c.ibkr_conid.in_(conids))
                .order_by(
                    asset_suggestions.c.ibkr_conid.asc(),
                    asset_suggestions.c.generated_at.desc(),
                )
            )
            .mappings()
            .all()
        )
        latest: dict[str, AssetSuggestionRecord] = {}
        for row in rows:
            record = _suggestion_from_row(row)
            if record.ibkr_conid not in latest:
                latest[record.ibkr_conid] = record
        ordered = tuple(latest[c] for c in conids if c in latest)
        return StorageListResult(
            ordered,
            asset_suggestions.name,
            f"{len(ordered)} assetsuggesties opgehaald.",
        )


def _suggestion_from_row(row: RowMapping) -> AssetSuggestionRecord:
    data = dict(row)

    def _normalise_json(name: str) -> tuple[str, ...] | None:
        value = data.get(name)
        if value is None:
            return None
        if isinstance(value, list):
            return tuple(str(item) for item in value)
        if isinstance(value, tuple):
            return tuple(str(item) for item in value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, list):
                return tuple(str(item) for item in parsed)
            return None
        return None

    data["drivers_json"] = _normalise_json("drivers_json")
    data["blockers_json"] = _normalise_json("blockers_json")
    return AssetSuggestionRecord(**data)


class SqlAlchemyAssetDecisionPackageRepository(_Base):
    def save_asset_decision_package(
        self, record: AssetDecisionPackageRecord
    ) -> StorageWriteResult:
        values = asdict(record)
        for key in ("gate_outcomes_json", "evidence_links_json", "audit_links_json"):
            raw = values.get(key)
            if isinstance(raw, tuple):
                values[key] = list(raw)
        self._insert(asset_decision_packages, values)
        return StorageWriteResult(
            True,
            record.decision_package_id,
            asset_decision_packages.name,
            True,
            "Decision Package opgeslagen.",
        )

    def get_latest_asset_decision_package_by_conid(
        self, ibkr_conid: str
    ) -> StorageReadResult[AssetDecisionPackageRecord]:
        row = (
            self._connection.execute(
                select(asset_decision_packages)
                .where(asset_decision_packages.c.ibkr_conid == ibkr_conid)
                .order_by(asset_decision_packages.c.generated_at.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        if row is None:
            return StorageReadResult(
                False,
                None,
                asset_decision_packages.name,
                "Geen Decision Package gevonden voor conid.",
            )
        return StorageReadResult(
            True,
            _decision_package_from_row(row),
            asset_decision_packages.name,
            "Decision Package opgehaald voor conid.",
        )

    def list_latest_asset_decision_packages_by_conids(
        self, conids: tuple[str, ...]
    ) -> StorageListResult[AssetDecisionPackageRecord]:
        if not conids:
            return StorageListResult((), asset_decision_packages.name, "Geen conids opgegeven.")
        rows = (
            self._connection.execute(
                select(asset_decision_packages)
                .where(asset_decision_packages.c.ibkr_conid.in_(conids))
                .order_by(
                    asset_decision_packages.c.ibkr_conid.asc(),
                    asset_decision_packages.c.generated_at.desc(),
                )
            )
            .mappings()
            .all()
        )
        latest: dict[str, AssetDecisionPackageRecord] = {}
        for row in rows:
            record = _decision_package_from_row(row)
            if record.ibkr_conid not in latest:
                latest[record.ibkr_conid] = record
        ordered = tuple(latest[c] for c in conids if c in latest)
        return StorageListResult(
            ordered,
            asset_decision_packages.name,
            f"{len(ordered)} Decision Packages opgehaald.",
        )


def _decision_package_from_row(row: RowMapping) -> AssetDecisionPackageRecord:
    data = dict(row)

    def _norm(name: str) -> tuple[str, ...] | None:
        value = data.get(name)
        if value is None:
            return None
        if isinstance(value, list):
            return tuple(str(item) for item in value)
        if isinstance(value, tuple):
            return tuple(str(item) for item in value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, list):
                return tuple(str(item) for item in parsed)
            return None
        return None

    data["gate_outcomes_json"] = _norm("gate_outcomes_json")
    data["evidence_links_json"] = _norm("evidence_links_json")
    data["audit_links_json"] = _norm("audit_links_json")
    return AssetDecisionPackageRecord(**data)


class SqlAlchemyAssetActionDraftRepository(_Base):
    def save_asset_action_draft(
        self, record: AssetActionDraftRecord
    ) -> StorageWriteResult:
        values = asdict(record)
        failures = values.get("dry_run_failures_json")
        if isinstance(failures, tuple):
            values["dry_run_failures_json"] = list(failures)
        self._insert(asset_action_drafts, values)
        return StorageWriteResult(
            True,
            record.draft_id,
            asset_action_drafts.name,
            True,
            "Action draft opgeslagen.",
        )

    def get_asset_action_draft_by_id(
        self, draft_id: str
    ) -> StorageReadResult[AssetActionDraftRecord]:
        row = _read_one_by_column(
            self._connection, asset_action_drafts, "draft_id", draft_id
        )
        if row is None:
            return StorageReadResult(
                False, None, asset_action_drafts.name, "Geen action draft gevonden."
            )
        return StorageReadResult(
            True,
            _action_draft_from_row(row),
            asset_action_drafts.name,
            "Action draft opgehaald.",
        )

    def list_latest_asset_action_drafts_by_conids(
        self, conids: tuple[str, ...]
    ) -> StorageListResult[AssetActionDraftRecord]:
        if not conids:
            return StorageListResult((), asset_action_drafts.name, "Geen conids opgegeven.")
        rows = (
            self._connection.execute(
                select(asset_action_drafts)
                .where(asset_action_drafts.c.ibkr_conid.in_(conids))
                .order_by(
                    asset_action_drafts.c.ibkr_conid.asc(),
                    asset_action_drafts.c.created_at.desc(),
                )
            )
            .mappings()
            .all()
        )
        latest: dict[str, AssetActionDraftRecord] = {}
        for row in rows:
            record = _action_draft_from_row(row)
            if record.ibkr_conid not in latest:
                latest[record.ibkr_conid] = record
        ordered = tuple(latest[c] for c in conids if c in latest)
        return StorageListResult(
            ordered,
            asset_action_drafts.name,
            f"{len(ordered)} action drafts opgehaald.",
        )


def _action_draft_from_row(row: RowMapping) -> AssetActionDraftRecord:
    data = dict(row)
    raw = data.get("dry_run_failures_json")
    if raw is None:
        data["dry_run_failures_json"] = None
    elif isinstance(raw, list):
        data["dry_run_failures_json"] = tuple(str(item) for item in raw)
    elif isinstance(raw, tuple):
        data["dry_run_failures_json"] = tuple(str(item) for item in raw)
    elif isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            data["dry_run_failures_json"] = None
        else:
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                data["dry_run_failures_json"] = None
            else:
                data["dry_run_failures_json"] = (
                    tuple(str(item) for item in parsed)
                    if isinstance(parsed, list)
                    else None
                )
    else:
        data["dry_run_failures_json"] = None
    return AssetActionDraftRecord(**data)


class SqlAlchemyAssetActionDraftSubmissionRepository(_Base):
    def save_asset_action_draft_submission(
        self, record: AssetActionDraftSubmissionRecord
    ) -> StorageWriteResult:
        values = asdict(record)
        failures = values.get("approval_dry_run_failures_json")
        if isinstance(failures, tuple):
            values["approval_dry_run_failures_json"] = list(failures)
        self._insert(asset_action_draft_submissions, values)
        return StorageWriteResult(
            True,
            record.submission_id,
            asset_action_draft_submissions.name,
            True,
            "Submission opgeslagen.",
        )

    def upsert_asset_action_draft_submission(
        self, record: AssetActionDraftSubmissionRecord
    ) -> StorageWriteResult:
        """Insert-or-replace by ``draft_id`` (the 1:1 link).

        Submissions are versioned via the events log, not by row history,
        so an idempotent replace on the same draft is the expected path.
        """

        self._connection.execute(
            asset_action_draft_submissions.delete().where(
                asset_action_draft_submissions.c.draft_id == record.draft_id
            )
        )
        return self.save_asset_action_draft_submission(record)

    def get_submission_by_draft_id(
        self, draft_id: str
    ) -> StorageReadResult[AssetActionDraftSubmissionRecord]:
        row = (
            self._connection.execute(
                select(asset_action_draft_submissions)
                .where(asset_action_draft_submissions.c.draft_id == draft_id)
                .order_by(asset_action_draft_submissions.c.created_at.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        if row is None:
            return StorageReadResult(
                False,
                None,
                asset_action_draft_submissions.name,
                "Geen submission gevonden.",
            )
        return StorageReadResult(
            True,
            _submission_from_row(row),
            asset_action_draft_submissions.name,
            "Submission opgehaald.",
        )


class SqlAlchemyAssetActionDraftEventRepository(_Base):
    def save_asset_action_draft_event(
        self, record: AssetActionDraftEventRecord
    ) -> StorageWriteResult:
        values = asdict(record)
        self._insert(asset_action_draft_events, values)
        return StorageWriteResult(
            True,
            record.event_id,
            asset_action_draft_events.name,
            True,
            "Event opgeslagen.",
        )

    def list_asset_action_draft_events(
        self, draft_id: str, *, limit: int = 100
    ) -> StorageListResult[AssetActionDraftEventRecord]:
        rows = (
            self._connection.execute(
                select(asset_action_draft_events)
                .where(asset_action_draft_events.c.draft_id == draft_id)
                .order_by(asset_action_draft_events.c.occurred_at.asc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        records = tuple(AssetActionDraftEventRecord(**dict(row)) for row in rows)
        return StorageListResult(
            records,
            asset_action_draft_events.name,
            f"{len(records)} events opgehaald.",
        )


def _submission_from_row(row: RowMapping) -> AssetActionDraftSubmissionRecord:
    data = dict(row)
    raw = data.get("approval_dry_run_failures_json")
    if raw is None:
        data["approval_dry_run_failures_json"] = None
    elif isinstance(raw, list | tuple):
        data["approval_dry_run_failures_json"] = tuple(str(item) for item in raw)
    elif isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            data["approval_dry_run_failures_json"] = None
        else:
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                data["approval_dry_run_failures_json"] = None
            else:
                data["approval_dry_run_failures_json"] = (
                    tuple(str(item) for item in parsed)
                    if isinstance(parsed, list)
                    else None
                )
    else:
        data["approval_dry_run_failures_json"] = None
    return AssetActionDraftSubmissionRecord(**data)


class SqlAlchemyPredictionDiaryRepository(_Base):
    def upsert_prediction_diary_entry(
        self, record: PredictionDiaryEntryRecord
    ) -> StorageWriteResult:
        """Insert-or-replace by ``suggestion_id`` (the UNIQUE link).

        Entries evolve over time as horizons mature; replacing in place
        keeps the diary keyed by suggestion while tracking the latest
        realised values.
        """

        self._connection.execute(
            prediction_diary_entries.delete().where(
                prediction_diary_entries.c.suggestion_id == record.suggestion_id
            )
        )
        self._insert(prediction_diary_entries, asdict(record))
        return StorageWriteResult(
            True,
            record.entry_id,
            prediction_diary_entries.name,
            True,
            "Prediction Diary entry opgeslagen.",
        )

    def get_prediction_diary_entry_by_suggestion_id(
        self, suggestion_id: str
    ) -> StorageReadResult[PredictionDiaryEntryRecord]:
        row = _read_one_by_column(
            self._connection, prediction_diary_entries, "suggestion_id", suggestion_id
        )
        if row is None:
            return StorageReadResult(
                False,
                None,
                prediction_diary_entries.name,
                "Geen Prediction Diary entry gevonden.",
            )
        return StorageReadResult(
            True,
            PredictionDiaryEntryRecord(**dict(row)),
            prediction_diary_entries.name,
            "Prediction Diary entry opgehaald.",
        )

    def list_prediction_diary_entries(
        self, *, limit: int = 200
    ) -> StorageListResult[PredictionDiaryEntryRecord]:
        rows = (
            self._connection.execute(
                select(prediction_diary_entries)
                .order_by(prediction_diary_entries.c.issued_at.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        records = tuple(PredictionDiaryEntryRecord(**dict(row)) for row in rows)
        return StorageListResult(
            records,
            prediction_diary_entries.name,
            f"{len(records)} Prediction Diary entries opgehaald.",
        )
