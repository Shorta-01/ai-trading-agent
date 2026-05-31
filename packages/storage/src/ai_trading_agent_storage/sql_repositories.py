from __future__ import annotations

from dataclasses import asdict
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import Table, func, select
from sqlalchemy.engine import Connection, RowMapping

from ai_trading_agent_storage.metadata import (
    action_drafts,
    action_draft_audit,
    behavioural_guardrail_settings,
    ibkr_executions,
    ibkr_submission_audit,
    ibkr_submission_lifecycle,
    manual_review_queue,
    reconciliation_audit,
    reconciliation_run_audit,
    unmatched_execution_audit,
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
    ibkr_nav_snapshots,
    runtime_config,
    ibkr_connection_audit,
    ibkr_execution_snapshots,
    ibkr_open_order_snapshots,
    ibkr_position_snapshots,
    ibkr_sync_runs,
    cold_start_seed_audit,
    calibration_diary,
    decision_packages,
    forecasts,
    fx_rates,
    market_data_eod_snapshots,
    provider_call_audit,
    scheduled_run_audit,
    scheduler_state,
    watchlist_confirmation_audit,
    watchlist_confirmation_state,
    watchlist_items,
    fx_rate_snapshots,
    asset_action_draft_events,
    asset_action_draft_submissions,
    asset_action_drafts,
    asset_decision_packages,
    asset_forecasts,
    asset_fundamentals_snapshots,
    asset_suggestions,
    briefing_alerts,
    daily_briefings,
    decision_package_explanations,
    explanation_evidence_ledger,
    action_draft_order_conditions,
    claude_ai_budget_usage,
    prediction_diary_predictor_contributions,
    predictor_backtest_runs,
    scheduler_runs,
    universe_scan_runs,
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
    ActionDraftAuditEntry,
    ActionDraftEntry,
    BehaviouralGuardrailSettings,
    RuntimeConfigRecord,
    IbkrExecutionEntry,
    IbkrSubmissionAuditEntry,
    IbkrSubmissionLifecycleEntry,
    ManualReviewQueueEntry,
    ReconciliationAuditEntry,
    ReconciliationRunAuditEntry,
    UnmatchedExecutionAuditEntry,
    AssetActionDraftEventRecord,
    AssetActionDraftRecord,
    AssetActionDraftSubmissionRecord,
    AssetDecisionPackageRecord,
    AssetFundamentalsSnapshotRecord,
    BriefingAlertRecord,
    DailyBriefingRecord,
    DecisionPackageExplanationRecord,
    ExplanationEvidenceLedgerRecord,
    ActionDraftOrderConditionRecord,
    ClaudeAiBudgetUsageRecord,
    PredictionDiaryEntryRecord,
    PredictionDiaryPredictorContributionRecord,
    PredictorBacktestRunRecord,
    SchedulerRunRecord,
    UniverseScanRunRecord,
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
    IbkrNavSnapshotRecord,
    IbkrConnectionAuditRecord,
    IbkrExecutionSnapshotRecord,
    IbkrOpenOrderSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
    CalibrationDiaryEntry,
    ColdStartAlreadySeededError,
    ColdStartSeedAuditEntry,
    DecisionPackageEntry,
    EvidenceReference,
    ForecastEntry,
    GateOutcome,
    FxRateRecord,
    MarketDataEodSnapshotEntry,
    ProviderCallAuditEntry,
    ScheduledRunAuditEntry,
    SchedulerStateEntry,
    WatchlistConfirmationAuditEntry,
    WatchlistConfirmationStateRecord,
    WatchlistItemSeedRecord,
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

    def get_latest_account_cash_snapshot(
        self, *, ibkr_account_id: str
    ) -> IbkrAccountCashSnapshotRecord | None:
        """Task 133: latest cash row for the (account) across all runs."""

        row = (
            self._connection.execute(
                select(ibkr_account_cash_snapshots)
                .where(
                    ibkr_account_cash_snapshots.c.ibkr_account_id
                    == ibkr_account_id
                )
                .order_by(ibkr_account_cash_snapshots.c.stored_at.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        return (
            None
            if row is None
            else IbkrAccountCashSnapshotRecord(**dict(row))
        )

    def get_latest_position_snapshot_for_conid(
        self, *, ibkr_account_id: str, conid: str
    ) -> IbkrPositionSnapshotRecord | None:
        """Task 133: latest position row for (account, conid)."""

        row = (
            self._connection.execute(
                select(ibkr_position_snapshots)
                .where(
                    ibkr_position_snapshots.c.ibkr_account_id
                    == ibkr_account_id
                )
                .where(ibkr_position_snapshots.c.conid == conid)
                .order_by(ibkr_position_snapshots.c.stored_at.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        return (
            None
            if row is None
            else IbkrPositionSnapshotRecord(**dict(row))
        )

    def save_ibkr_nav_snapshot(self, record: IbkrNavSnapshotRecord) -> None:
        """Append one portfolio NAV point (T-045 §2 drawdown history)."""

        self._insert(ibkr_nav_snapshots, asdict(record))

    def list_ibkr_nav_snapshots_since(
        self, *, ibkr_account_id: str, since: datetime
    ) -> list[IbkrNavSnapshotRecord]:
        """NAV points for an account recorded at/after ``since``, oldest first."""

        rows = (
            self._connection.execute(
                select(ibkr_nav_snapshots)
                .where(ibkr_nav_snapshots.c.ibkr_account_id == ibkr_account_id)
                .where(ibkr_nav_snapshots.c.recorded_at >= since)
                .order_by(ibkr_nav_snapshots.c.recorded_at.asc())
            )
            .mappings()
            .all()
        )
        return [IbkrNavSnapshotRecord(**dict(row)) for row in rows]

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

    def delete_event(self, system_event_id: str) -> StorageWriteResult:
        """Permanently remove a system event (error-log delete action)."""

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
        self._connection.execute(
            system_events.delete().where(
                system_events.c.system_event_id == system_event_id
            )
        )
        return StorageWriteResult(
            accepted=True,
            record_id=system_event_id,
            table_name=system_events.name,
            audit_required=True,
            explanation_nl="Systeemmelding verwijderd.",
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

    def expire_stale_asset_suggestions(self, *, now: datetime) -> int:
        """Flip every ``status='ready'`` row whose ``valid_until`` has
        passed to ``status='expired'`` with a stable blocking_reason.

        Returns the number of rows updated. Idempotent — only ``ready``
        rows are touched, so re-running on the same cutoff is a no-op
        after the first run. Called from the morning chain and from a
        nightly cleanup so a stale ``Bekijken`` doesn't silt up the
        watchlist forever.
        """

        update = (
            asset_suggestions.update()
            .where(asset_suggestions.c.status == "ready")
            .where(asset_suggestions.c.valid_until < now)
            .values(
                status="expired",
                blocking_reason="past_valid_until",
            )
        )
        result = self._connection.execute(update)
        return int(result.rowcount or 0)


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


class SqlAlchemyDecisionPackageExplanationRepository(_Base):
    def save_decision_package_explanation(
        self, record: DecisionPackageExplanationRecord
    ) -> StorageWriteResult:
        values = asdict(record)
        values["hallucinated_numbers_json"] = (
            None
            if record.hallucinated_numbers_json is None
            else list(record.hallucinated_numbers_json)
        )
        self._insert(decision_package_explanations, values)
        return StorageWriteResult(
            True,
            record.explanation_id,
            decision_package_explanations.name,
            True,
            "Explanation opgeslagen.",
        )

    def get_latest_explanation_for_package(
        self, decision_package_id: str
    ) -> StorageReadResult[DecisionPackageExplanationRecord]:
        statement = (
            select(decision_package_explanations)
            .where(
                decision_package_explanations.c.decision_package_id == decision_package_id
            )
            .order_by(decision_package_explanations.c.generated_at.desc())
            .limit(1)
        )
        row = self._connection.execute(statement).mappings().first()
        if row is None:
            return StorageReadResult(
                False,
                None,
                decision_package_explanations.name,
                "Geen explanation gevonden voor dit Decision Package.",
            )
        values = dict(row)
        values["hallucinated_numbers_json"] = _json_tuple_or_none(
            values.get("hallucinated_numbers_json")
        )
        return StorageReadResult(
            True,
            DecisionPackageExplanationRecord(**values),
            decision_package_explanations.name,
            "Explanation opgehaald.",
        )

    def get_explanation_for_package_version(
        self,
        *,
        decision_package_id: str,
        content_hash: str,
    ) -> StorageReadResult[DecisionPackageExplanationRecord]:
        statement = select(decision_package_explanations).where(
            decision_package_explanations.c.decision_package_id == decision_package_id,
            decision_package_explanations.c.decision_package_content_hash == content_hash,
        )
        row = self._connection.execute(statement).mappings().first()
        if row is None:
            return StorageReadResult(
                False,
                None,
                decision_package_explanations.name,
                "Geen explanation gevonden voor deze package versie.",
            )
        values = dict(row)
        values["hallucinated_numbers_json"] = _json_tuple_or_none(
            values.get("hallucinated_numbers_json")
        )
        return StorageReadResult(
            True,
            DecisionPackageExplanationRecord(**values),
            decision_package_explanations.name,
            "Explanation opgehaald.",
        )

    def save_explanation_evidence_ledger_entry(
        self, record: ExplanationEvidenceLedgerRecord
    ) -> StorageWriteResult:
        self._insert(explanation_evidence_ledger, asdict(record))
        return StorageWriteResult(
            True,
            record.ledger_id,
            explanation_evidence_ledger.name,
            True,
            "Evidence ledger entry opgeslagen.",
        )

    def list_evidence_ledger_for_explanation(
        self, explanation_id: str
    ) -> StorageListResult[ExplanationEvidenceLedgerRecord]:
        rows = _read_many_by_column(
            self._connection,
            explanation_evidence_ledger,
            "explanation_id",
            explanation_id,
        )
        records = tuple(ExplanationEvidenceLedgerRecord(**dict(row)) for row in rows)
        return StorageListResult(
            records,
            explanation_evidence_ledger.name,
            f"{len(records)} evidence ledger entries opgehaald.",
        )


class SqlAlchemyDailyBriefingRepository(_Base):
    def upsert_daily_briefing(
        self, record: DailyBriefingRecord
    ) -> StorageWriteResult:
        """Insert-or-replace by ``briefing_date`` (UNIQUE).

        A briefing can be re-run mid-day; the latest snapshot wins.
        """

        self._connection.execute(
            daily_briefings.delete().where(
                daily_briefings.c.briefing_date == record.briefing_date
            )
        )
        self._insert(daily_briefings, asdict(record))
        return StorageWriteResult(
            True,
            record.briefing_id,
            daily_briefings.name,
            True,
            "Daily briefing opgeslagen.",
        )

    def get_latest_daily_briefing(
        self,
    ) -> StorageReadResult[DailyBriefingRecord]:
        statement = (
            select(daily_briefings)
            .order_by(daily_briefings.c.briefing_date.desc())
            .limit(1)
        )
        row = self._connection.execute(statement).mappings().first()
        if row is None:
            return StorageReadResult(
                False,
                None,
                daily_briefings.name,
                "Nog geen daily briefing.",
            )
        return StorageReadResult(
            True,
            DailyBriefingRecord(**dict(row)),
            daily_briefings.name,
            "Daily briefing opgehaald.",
        )

    def save_briefing_alert(
        self, record: BriefingAlertRecord
    ) -> StorageWriteResult:
        self._insert(briefing_alerts, asdict(record))
        return StorageWriteResult(
            True,
            record.alert_id,
            briefing_alerts.name,
            True,
            "Briefing alert opgeslagen.",
        )

    def list_alerts_for_briefing(
        self, briefing_id: str
    ) -> StorageListResult[BriefingAlertRecord]:
        rows = _read_many_by_column(
            self._connection, briefing_alerts, "briefing_id", briefing_id
        )
        records = tuple(BriefingAlertRecord(**dict(row)) for row in rows)
        return StorageListResult(
            records,
            briefing_alerts.name,
            f"{len(records)} briefing alerts opgehaald.",
        )

    def delete_alerts_for_briefing(self, briefing_id: str) -> StorageWriteResult:
        """Used when a briefing is re-run: drop the old alerts for the day."""

        self._connection.execute(
            briefing_alerts.delete().where(
                briefing_alerts.c.briefing_id == briefing_id
            )
        )
        return StorageWriteResult(
            True,
            briefing_id,
            briefing_alerts.name,
            True,
            "Briefing alerts verwijderd.",
        )


class SqlAlchemySchedulerRunRepository(_Base):
    def save_scheduler_run(self, record: SchedulerRunRecord) -> StorageWriteResult:
        self._insert(scheduler_runs, asdict(record))
        return StorageWriteResult(
            True,
            record.run_id,
            scheduler_runs.name,
            True,
            "Scheduler-run opgeslagen.",
        )

    def update_scheduler_run(self, record: SchedulerRunRecord) -> StorageWriteResult:
        self._connection.execute(
            scheduler_runs.delete().where(scheduler_runs.c.run_id == record.run_id)
        )
        self._insert(scheduler_runs, asdict(record))
        return StorageWriteResult(
            True,
            record.run_id,
            scheduler_runs.name,
            True,
            "Scheduler-run bijgewerkt.",
        )

    def get_latest_scheduler_run(
        self, *, job_name: str | None = None
    ) -> StorageReadResult[SchedulerRunRecord]:
        statement = select(scheduler_runs)
        if job_name is not None:
            statement = statement.where(scheduler_runs.c.job_name == job_name)
        statement = statement.order_by(scheduler_runs.c.started_at.desc()).limit(1)
        row = self._connection.execute(statement).mappings().first()
        if row is None:
            return StorageReadResult(
                False,
                None,
                scheduler_runs.name,
                "Nog geen scheduler-run.",
            )
        return StorageReadResult(
            True,
            SchedulerRunRecord(**dict(row)),
            scheduler_runs.name,
            "Scheduler-run opgehaald.",
        )

    def list_scheduler_runs(
        self, *, limit: int = 50
    ) -> StorageListResult[SchedulerRunRecord]:
        rows = (
            self._connection.execute(
                select(scheduler_runs)
                .order_by(scheduler_runs.c.started_at.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        records = tuple(SchedulerRunRecord(**dict(row)) for row in rows)
        return StorageListResult(
            records,
            scheduler_runs.name,
            f"{len(records)} scheduler-runs opgehaald.",
        )


class SqlAlchemyActionDraftOrderConditionRepository(_Base):
    """V1.1 Slice 32: per-draft order-condition repository.

    Single child table keyed on ``(draft_id, condition_index)``;
    callers persist one condition per row and read them back in
    ``condition_index`` order so the conjunction chain is stable.
    """

    def save_condition(
        self, record: ActionDraftOrderConditionRecord
    ) -> StorageWriteResult:
        self._insert(action_draft_order_conditions, asdict(record))
        return StorageWriteResult(
            True,
            record.condition_id,
            action_draft_order_conditions.name,
            True,
            "Action-draft order-conditie opgeslagen.",
        )

    def list_conditions_for_draft(
        self, draft_id: str
    ) -> StorageListResult[ActionDraftOrderConditionRecord]:
        statement = (
            select(action_draft_order_conditions)
            .where(action_draft_order_conditions.c.draft_id == draft_id)
            .order_by(action_draft_order_conditions.c.condition_index.asc())
        )
        rows = self._connection.execute(statement).mappings().all()
        records = tuple(
            ActionDraftOrderConditionRecord(**dict(row)) for row in rows
        )
        return StorageListResult(
            records,
            action_draft_order_conditions.name,
            f"{len(records)} order-condities opgehaald.",
        )

    def delete_conditions_for_draft(
        self, draft_id: str
    ) -> StorageWriteResult:
        self._connection.execute(
            action_draft_order_conditions.delete().where(
                action_draft_order_conditions.c.draft_id == draft_id
            )
        )
        return StorageWriteResult(
            True,
            draft_id,
            action_draft_order_conditions.name,
            True,
            "Order-condities verwijderd.",
        )


class SqlAlchemyClaudeAiBudgetUsageRepository(_Base):
    """V1.1 Slice 29: Anthropic Claude budget-usage audit repository.

    The provider checks the running monthly total via
    :meth:`monthly_total_eur` before issuing a call; once the total
    exceeds the locked ``CLAUDE_AI_BUDGET_MONTHLY_EUR`` cap the
    provider refuses and the orchestrator falls back to the stub.
    """

    def save_usage(
        self, record: ClaudeAiBudgetUsageRecord
    ) -> StorageWriteResult:
        self._insert(claude_ai_budget_usage, asdict(record))
        return StorageWriteResult(
            True,
            record.usage_id,
            claude_ai_budget_usage.name,
            True,
            "Claude AI budget-usage opgeslagen.",
        )

    def monthly_total_eur(self, budget_month: str) -> Decimal:
        statement = select(claude_ai_budget_usage.c.cost_eur).where(
            claude_ai_budget_usage.c.budget_month == budget_month
        )
        rows = self._connection.execute(statement).all()
        return sum((row[0] for row in rows), Decimal("0"))

    def list_recent_usage(
        self,
        *,
        budget_month: str | None = None,
        limit: int = 100,
    ) -> StorageListResult[ClaudeAiBudgetUsageRecord]:
        statement = select(claude_ai_budget_usage)
        if budget_month is not None:
            statement = statement.where(
                claude_ai_budget_usage.c.budget_month == budget_month
            )
        statement = statement.order_by(
            claude_ai_budget_usage.c.called_at.desc()
        ).limit(_bounded_limit(limit))
        rows = self._connection.execute(statement).mappings().all()
        records = tuple(
            ClaudeAiBudgetUsageRecord(**dict(row)) for row in rows
        )
        return StorageListResult(
            records,
            claude_ai_budget_usage.name,
            f"{len(records)} budget-usage rijen opgehaald.",
        )


class SqlAlchemyPredictionDiaryPredictorContributionRepository(_Base):
    """V1.1 Slice 26: per-(diary_entry, predictor) outcome repository.

    Writes one row per `(diary_entry_id, model_code)` so the auto-
    weighted ensemble can read a rolling per-predictor Brier score.
    """

    def save_contribution(
        self, record: PredictionDiaryPredictorContributionRecord
    ) -> StorageWriteResult:
        self._insert(
            prediction_diary_predictor_contributions, asdict(record)
        )
        return StorageWriteResult(
            True,
            record.contribution_id,
            prediction_diary_predictor_contributions.name,
            True,
            "Predictor-contributie opgeslagen.",
        )

    def list_recent_contributions(
        self,
        *,
        model_code: str | None = None,
        diary_entry_id: str | None = None,
        limit: int = 200,
    ) -> StorageListResult[PredictionDiaryPredictorContributionRecord]:
        statement = select(prediction_diary_predictor_contributions)
        if model_code is not None:
            statement = statement.where(
                prediction_diary_predictor_contributions.c.model_code == model_code
            )
        if diary_entry_id is not None:
            statement = statement.where(
                prediction_diary_predictor_contributions.c.diary_entry_id == diary_entry_id
            )
        statement = statement.order_by(
            prediction_diary_predictor_contributions.c.created_at.desc()
        ).limit(_bounded_limit(limit))
        rows = self._connection.execute(statement).mappings().all()
        records = tuple(
            PredictionDiaryPredictorContributionRecord(**dict(row))
            for row in rows
        )
        return StorageListResult(
            records,
            prediction_diary_predictor_contributions.name,
            f"{len(records)} predictor-contributies opgehaald.",
        )


class SqlAlchemyPredictorBacktestRunRepository(_Base):
    """V1.1 Slice 24: predictor backtest audit repository.

    Slice 25 (backtesting framework) wires the harness that writes
    rows; Slice 26 (feedback loop) aggregates rolling Brier scores
    for the auto-weighted ensemble strategy.
    """

    def save_backtest_run(
        self, record: PredictorBacktestRunRecord
    ) -> StorageWriteResult:
        self._insert(predictor_backtest_runs, asdict(record))
        return StorageWriteResult(
            True,
            record.run_id,
            predictor_backtest_runs.name,
            True,
            "Predictor-backtest opgeslagen.",
        )

    def update_backtest_run(
        self, record: PredictorBacktestRunRecord
    ) -> StorageWriteResult:
        self._connection.execute(
            predictor_backtest_runs.delete().where(
                predictor_backtest_runs.c.run_id == record.run_id
            )
        )
        self._insert(predictor_backtest_runs, asdict(record))
        return StorageWriteResult(
            True,
            record.run_id,
            predictor_backtest_runs.name,
            True,
            "Predictor-backtest bijgewerkt.",
        )

    def list_recent_backtest_runs(
        self,
        *,
        model_code: str | None = None,
        asset_symbol: str | None = None,
        limit: int = 100,
    ) -> StorageListResult[PredictorBacktestRunRecord]:
        statement = select(predictor_backtest_runs)
        if model_code is not None:
            statement = statement.where(
                predictor_backtest_runs.c.model_code == model_code
            )
        if asset_symbol is not None:
            statement = statement.where(
                predictor_backtest_runs.c.asset_symbol == asset_symbol
            )
        statement = statement.order_by(
            predictor_backtest_runs.c.started_at.desc()
        ).limit(_bounded_limit(limit))
        rows = self._connection.execute(statement).mappings().all()
        records = tuple(
            PredictorBacktestRunRecord(**dict(row)) for row in rows
        )
        return StorageListResult(
            records,
            predictor_backtest_runs.name,
            f"{len(records)} predictor-backtest runs opgehaald.",
        )


class SqlAlchemyAssetFundamentalsSnapshotRepository(_Base):
    def save_snapshot(
        self, record: AssetFundamentalsSnapshotRecord
    ) -> StorageWriteResult:
        self._insert(asset_fundamentals_snapshots, asdict(record))
        return StorageWriteResult(
            True,
            record.snapshot_id,
            asset_fundamentals_snapshots.name,
            True,
            "Fundamentals snapshot opgeslagen.",
        )

    def get_latest_snapshot_for_symbol(
        self, eodhd_symbol: str
    ) -> StorageReadResult[AssetFundamentalsSnapshotRecord]:
        statement = (
            select(asset_fundamentals_snapshots)
            .where(asset_fundamentals_snapshots.c.eodhd_symbol == eodhd_symbol)
            .order_by(asset_fundamentals_snapshots.c.fetched_at.desc())
            .limit(1)
        )
        row = self._connection.execute(statement).mappings().first()
        if row is None:
            return StorageReadResult(
                False,
                None,
                asset_fundamentals_snapshots.name,
                "Nog geen fundamentals snapshot voor dit symbool.",
            )
        return StorageReadResult(
            True,
            AssetFundamentalsSnapshotRecord(**dict(row)),
            asset_fundamentals_snapshots.name,
            "Fundamentals snapshot opgehaald.",
        )

    def list_latest_universe_snapshots(
        self,
        *,
        limit: int = 5000,
        min_factor_count: int = 0,
    ) -> StorageListResult[AssetFundamentalsSnapshotRecord]:
        """Return the most-recent snapshot per symbol, up to ``limit`` rows.

        V1.1 §22.4 paging surface: ``limit`` caps the row count so the
        briefing panel can request the top-N candidates without loading
        the full ALL_5K universe. ``min_factor_count`` filters to rows
        with at least N non-null QVM factor columns (out of the 6
        scored columns: pe_ratio, pb_ratio, ev_ebitda, roic_pct,
        gross_margin_pct, return_12m_pct) — useful for ranking when
        the operator wants stable cross-section z-scores.
        """

        # Two-step: rank by fetched_at within (eodhd_symbol), keep the
        # first per symbol. SQLite + Postgres both support the
        # window-function path; here we use a simpler self-join that
        # works on every backend we run against.
        latest_by_symbol = (
            select(
                asset_fundamentals_snapshots.c.eodhd_symbol,
                func.max(asset_fundamentals_snapshots.c.fetched_at).label("latest"),
            )
            .group_by(asset_fundamentals_snapshots.c.eodhd_symbol)
            .subquery()
        )
        statement = (
            select(asset_fundamentals_snapshots)
            .join(
                latest_by_symbol,
                (asset_fundamentals_snapshots.c.eodhd_symbol == latest_by_symbol.c.eodhd_symbol)
                & (asset_fundamentals_snapshots.c.fetched_at == latest_by_symbol.c.latest),
            )
            .order_by(asset_fundamentals_snapshots.c.eodhd_symbol.asc())
            .limit(_bounded_limit(limit))
        )
        rows = self._connection.execute(statement).mappings().all()
        records = tuple(
            AssetFundamentalsSnapshotRecord(**dict(row)) for row in rows
        )
        if min_factor_count > 0:
            scored_columns = (
                "pe_ratio",
                "pb_ratio",
                "ev_ebitda",
                "roic_pct",
                "gross_margin_pct",
                "return_12m_pct",
            )
            records = tuple(
                r
                for r in records
                if sum(
                    1 for col in scored_columns if getattr(r, col, None) is not None
                )
                >= min_factor_count
            )
        return StorageListResult(
            records,
            asset_fundamentals_snapshots.name,
            f"{len(records)} fundamentals snapshots in latest universe.",
        )


class SqlAlchemyUniverseScanRunRepository(_Base):
    def save_run(self, record: UniverseScanRunRecord) -> StorageWriteResult:
        self._insert(universe_scan_runs, asdict(record))
        return StorageWriteResult(
            True,
            record.run_id,
            universe_scan_runs.name,
            True,
            "Universe-scan run opgeslagen.",
        )

    def update_run(self, record: UniverseScanRunRecord) -> StorageWriteResult:
        self._connection.execute(
            universe_scan_runs.delete().where(
                universe_scan_runs.c.run_id == record.run_id
            )
        )
        self._insert(universe_scan_runs, asdict(record))
        return StorageWriteResult(
            True,
            record.run_id,
            universe_scan_runs.name,
            True,
            "Universe-scan run bijgewerkt.",
        )

    def get_latest_run(
        self,
    ) -> StorageReadResult[UniverseScanRunRecord]:
        statement = (
            select(universe_scan_runs)
            .order_by(universe_scan_runs.c.started_at.desc())
            .limit(1)
        )
        row = self._connection.execute(statement).mappings().first()
        if row is None:
            return StorageReadResult(
                False,
                None,
                universe_scan_runs.name,
                "Nog geen universe-scan run.",
            )
        return StorageReadResult(
            True,
            UniverseScanRunRecord(**dict(row)),
            universe_scan_runs.name,
            "Universe-scan run opgehaald.",
        )

    def list_runs(
        self, *, limit: int = 50
    ) -> StorageListResult[UniverseScanRunRecord]:
        rows = (
            self._connection.execute(
                select(universe_scan_runs)
                .order_by(universe_scan_runs.c.started_at.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        records = tuple(UniverseScanRunRecord(**dict(row)) for row in rows)
        return StorageListResult(
            records,
            universe_scan_runs.name,
            f"{len(records)} universe-scan runs opgehaald.",
        )


class SqlAlchemyIbkrConnectionAuditRepository(_Base):
    """Task 126: append-only IBKR connection lifecycle audit.

    Both mode-detection checks (prefix + behavioural) plus
    ``connect_attempt``, ``connect_success``, ``connect_refused``,
    ``disconnect``, ``session_error`` events land here. Append-only —
    no update or delete methods. Safety booleans hard-False per
    project doctrine.
    """

    def append(
        self, record: IbkrConnectionAuditRecord
    ) -> StorageWriteResult:
        payload = asdict(record)
        # `details_json` is stored as a JSON column; the dataclass
        # carries it as the already-serialised JSON string so callers
        # don't need to dump every event.
        self._insert(ibkr_connection_audit, payload)
        return StorageWriteResult(
            True,
            record.audit_id,
            ibkr_connection_audit.name,
            True,
            "IBKR connection-audit rij opgeslagen.",
        )

    def list_recent(
        self,
        *,
        ibkr_account_id: str | None = None,
        limit: int = 50,
    ) -> StorageListResult[IbkrConnectionAuditRecord]:
        statement = select(ibkr_connection_audit)
        if ibkr_account_id is not None:
            statement = statement.where(
                ibkr_connection_audit.c.ibkr_account_id == ibkr_account_id
            )
        statement = statement.order_by(
            ibkr_connection_audit.c.event_at.desc()
        ).limit(_bounded_limit(limit))
        rows = self._connection.execute(statement).mappings().all()
        records = tuple(
            IbkrConnectionAuditRecord(
                audit_id=row["audit_id"],
                event_at=row["event_at"],
                ibkr_account_id=row["ibkr_account_id"],
                event_type=row["event_type"],
                account_mode_detected=row["account_mode_detected"],
                connection_id=row["connection_id"],
                details_json=row["details_json"],
            )
            for row in rows
        )
        return StorageListResult(
            records,
            ibkr_connection_audit.name,
            f"{len(records)} IBKR connection-audit rijen opgehaald.",
        )


class SqlAlchemyScheduledRunAuditRepository(_Base):
    """Task 127: append-only scheduler-run audit repository.

    Task 127 product lock §5: rows are append-only — no update or
    delete methods. Each scheduled run writes one row capturing the
    detected mode + outcome. Safety booleans hard-False on every
    insert.
    """

    def append(
        self, record: ScheduledRunAuditEntry
    ) -> StorageWriteResult:
        payload = asdict(record)
        self._insert(scheduled_run_audit, payload)
        return StorageWriteResult(
            True,
            record.run_id,
            scheduled_run_audit.name,
            True,
            "Scheduled-run audit-rij opgeslagen.",
        )

    def list_recent(
        self,
        *,
        limit: int = 20,
    ) -> StorageListResult[ScheduledRunAuditEntry]:
        statement = (
            select(scheduled_run_audit)
            .order_by(scheduled_run_audit.c.run_at.desc())
            .limit(_bounded_limit(limit))
        )
        rows = self._connection.execute(statement).mappings().all()
        records = tuple(
            ScheduledRunAuditEntry(
                run_id=row["run_id"],
                run_at=row["run_at"],
                run_type=row["run_type"],
                ibkr_account_id=row["ibkr_account_id"],
                mode_detected=row["mode_detected"],
                duration_ms=row["duration_ms"],
                outcome=row["outcome"],
                error_details_json=row["error_details_json"],
                next_scheduled_at=row["next_scheduled_at"],
            )
            for row in rows
        )
        return StorageListResult(
            records,
            scheduled_run_audit.name,
            f"{len(records)} scheduled-run audit-rijen opgehaald.",
        )

    def list_by_run_type(
        self,
        *,
        run_type: str,
        limit: int = 20,
    ) -> StorageListResult[ScheduledRunAuditEntry]:
        statement = (
            select(scheduled_run_audit)
            .where(scheduled_run_audit.c.run_type == run_type)
            .order_by(scheduled_run_audit.c.run_at.desc())
            .limit(_bounded_limit(limit))
        )
        rows = self._connection.execute(statement).mappings().all()
        records = tuple(
            ScheduledRunAuditEntry(
                run_id=row["run_id"],
                run_at=row["run_at"],
                run_type=row["run_type"],
                ibkr_account_id=row["ibkr_account_id"],
                mode_detected=row["mode_detected"],
                duration_ms=row["duration_ms"],
                outcome=row["outcome"],
                error_details_json=row["error_details_json"],
                next_scheduled_at=row["next_scheduled_at"],
            )
            for row in rows
        )
        return StorageListResult(
            records,
            scheduled_run_audit.name,
            f"{len(records)} scheduled-run audit-rijen opgehaald.",
        )


class SqlAlchemySchedulerStateRepository(_Base):
    """Task 127: per-worker scheduler heartbeat + next-fire surface.

    Single row per worker process; the scheduler updates its row
    every 60 seconds. ``upsert`` replaces or inserts atomically.
    The API reads these rows to compute ``/scheduler/status``.
    """

    def upsert(self, record: SchedulerStateEntry) -> StorageWriteResult:
        existing = self._connection.execute(
            select(scheduler_state).where(
                scheduler_state.c.worker_id == record.worker_id
            )
        ).first()
        payload = asdict(record)
        if existing is None:
            self._insert(scheduler_state, payload)
            return StorageWriteResult(
                True,
                record.worker_id,
                scheduler_state.name,
                True,
                "Scheduler-state rij ingevoegd.",
            )
        self._connection.execute(
            scheduler_state.update()
            .where(scheduler_state.c.worker_id == record.worker_id)
            .values(**payload)
        )
        return StorageWriteResult(
            True,
            record.worker_id,
            scheduler_state.name,
            True,
            "Scheduler-state rij bijgewerkt.",
        )

    def list_all(self) -> StorageListResult[SchedulerStateEntry]:
        rows = (
            self._connection.execute(
                select(scheduler_state).order_by(
                    scheduler_state.c.last_heartbeat_at.desc()
                )
            )
            .mappings()
            .all()
        )
        records = tuple(
            SchedulerStateEntry(
                worker_id=row["worker_id"],
                started_at=row["started_at"],
                last_heartbeat_at=row["last_heartbeat_at"],
                next_pre_briefing_at=row["next_pre_briefing_at"],
                next_hourly_at=row["next_hourly_at"],
            )
            for row in rows
        )
        return StorageListResult(
            records,
            scheduler_state.name,
            f"{len(records)} scheduler-state rijen opgehaald.",
        )


class SqlAlchemyColdStartSeedAuditRepository(_Base):
    """Task 128: per-account cold-start seed audit (one-time enforced).

    Inserts raise :class:`ColdStartAlreadySeededError` if a row for the
    same ``ibkr_account_id`` already exists (the unique primary-key
    constraint at the DB level + an explicit pre-check inside the
    repository give the seed function a clean idempotency signal).
    """

    def append(
        self, record: ColdStartSeedAuditEntry
    ) -> StorageWriteResult:
        existing = self._connection.execute(
            select(cold_start_seed_audit).where(
                cold_start_seed_audit.c.ibkr_account_id
                == record.ibkr_account_id
            )
        ).first()
        if existing is not None:
            raise ColdStartAlreadySeededError(
                f"Account {record.ibkr_account_id} is already seeded."
            )
        payload = asdict(record)
        self._insert(cold_start_seed_audit, payload)
        return StorageWriteResult(
            True,
            record.ibkr_account_id,
            cold_start_seed_audit.name,
            True,
            "Cold-start seed-audit rij opgeslagen.",
        )

    def find_by_account_id(
        self, ibkr_account_id: str
    ) -> ColdStartSeedAuditEntry | None:
        row = self._connection.execute(
            select(cold_start_seed_audit).where(
                cold_start_seed_audit.c.ibkr_account_id == ibkr_account_id
            )
        ).mappings().first()
        if row is None:
            return None
        return ColdStartSeedAuditEntry(
            seeded_at=row["seeded_at"],
            ibkr_account_id=row["ibkr_account_id"],
            seeded_count=row["seeded_count"],
            failed_conids_json=row["failed_conids_json"] or "[]",
            seed_version=row["seed_version"],
        )

    def list_recent(
        self, *, limit: int = 20
    ) -> StorageListResult[ColdStartSeedAuditEntry]:
        rows = (
            self._connection.execute(
                select(cold_start_seed_audit)
                .order_by(cold_start_seed_audit.c.seeded_at.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        records = tuple(
            ColdStartSeedAuditEntry(
                seeded_at=row["seeded_at"],
                ibkr_account_id=row["ibkr_account_id"],
                seeded_count=row["seeded_count"],
                failed_conids_json=row["failed_conids_json"] or "[]",
                seed_version=row["seed_version"],
            )
            for row in rows
        )
        return StorageListResult(
            records,
            cold_start_seed_audit.name,
            f"{len(records)} cold-start seed-audit rijen opgehaald.",
        )


class SqlAlchemyWatchlistConfirmationStateRepository(_Base):
    """Task 128: per-account ``unconfirmed`` / ``confirmed`` state."""

    def upsert(
        self, record: WatchlistConfirmationStateRecord
    ) -> StorageWriteResult:
        existing = self._connection.execute(
            select(watchlist_confirmation_state).where(
                watchlist_confirmation_state.c.ibkr_account_id
                == record.ibkr_account_id
            )
        ).first()
        payload = asdict(record)
        if existing is None:
            self._insert(watchlist_confirmation_state, payload)
            return StorageWriteResult(
                True,
                record.ibkr_account_id,
                watchlist_confirmation_state.name,
                True,
                "Watchlist confirmation-state ingevoegd.",
            )
        self._connection.execute(
            watchlist_confirmation_state.update()
            .where(
                watchlist_confirmation_state.c.ibkr_account_id
                == record.ibkr_account_id
            )
            .values(**payload)
        )
        return StorageWriteResult(
            True,
            record.ibkr_account_id,
            watchlist_confirmation_state.name,
            True,
            "Watchlist confirmation-state bijgewerkt.",
        )

    def get_by_account_id(
        self, ibkr_account_id: str
    ) -> WatchlistConfirmationStateRecord | None:
        row = self._connection.execute(
            select(watchlist_confirmation_state).where(
                watchlist_confirmation_state.c.ibkr_account_id
                == ibkr_account_id
            )
        ).mappings().first()
        if row is None:
            return None
        return WatchlistConfirmationStateRecord(
            ibkr_account_id=row["ibkr_account_id"],
            state=row["state"],
            last_updated_at=row["last_updated_at"],
        )

    def list_all(
        self,
    ) -> StorageListResult[WatchlistConfirmationStateRecord]:
        rows = (
            self._connection.execute(
                select(watchlist_confirmation_state).order_by(
                    watchlist_confirmation_state.c.last_updated_at.desc()
                )
            )
            .mappings()
            .all()
        )
        records = tuple(
            WatchlistConfirmationStateRecord(
                ibkr_account_id=row["ibkr_account_id"],
                state=row["state"],
                last_updated_at=row["last_updated_at"],
            )
            for row in rows
        )
        return StorageListResult(
            records,
            watchlist_confirmation_state.name,
            f"{len(records)} watchlist confirmation-state rijen opgehaald.",
        )


class SqlAlchemyWatchlistConfirmationAuditRepository(_Base):
    """Task 128: append-only state-transition audit trail."""

    def append(
        self, record: WatchlistConfirmationAuditEntry
    ) -> StorageWriteResult:
        from uuid import uuid4

        payload = asdict(record)
        audit_id = f"wca_{uuid4().hex}"
        payload["audit_id"] = audit_id
        self._insert(watchlist_confirmation_audit, payload)
        return StorageWriteResult(
            True,
            audit_id,
            watchlist_confirmation_audit.name,
            True,
            "Watchlist confirmation-audit rij opgeslagen.",
        )

    def list_by_account_id(
        self,
        *,
        ibkr_account_id: str,
        limit: int = 50,
    ) -> StorageListResult[WatchlistConfirmationAuditEntry]:
        rows = (
            self._connection.execute(
                select(watchlist_confirmation_audit)
                .where(
                    watchlist_confirmation_audit.c.ibkr_account_id
                    == ibkr_account_id
                )
                .order_by(watchlist_confirmation_audit.c.event_at.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        records = tuple(
            WatchlistConfirmationAuditEntry(
                event_at=row["event_at"],
                ibkr_account_id=row["ibkr_account_id"],
                from_state=row["from_state"],
                to_state=row["to_state"],
                actor=row["actor"],
                row_count_at_event=row["row_count_at_event"],
                details_json=row["details_json"],
            )
            for row in rows
        )
        return StorageListResult(
            records,
            watchlist_confirmation_audit.name,
            f"{len(records)} watchlist confirmation-audit rijen opgehaald.",
        )


class SqlAlchemyWatchlistItemSeedRepository(_Base):
    """Task 128: thin write/read repo for the cold-start seed path.

    Touches a subset of the ``watchlist_items`` columns — the legacy
    STORE-backed API routes in ``apps/api/.../watchlist.py`` are not
    aware of these rows and don't need to be (the cold-start UI
    reads them via a dedicated endpoint).
    """

    def append(
        self, record: WatchlistItemSeedRecord
    ) -> StorageWriteResult:
        payload = asdict(record)
        self._insert(watchlist_items, payload)
        return StorageWriteResult(
            True,
            record.watchlist_item_id,
            watchlist_items.name,
            True,
            "Watchlist-item (cold-start seed) opgeslagen.",
        )

    def count_active_for_account(self, ibkr_account_id: str) -> int:
        from sqlalchemy import func as sqla_func

        result = self._connection.execute(
            select(sqla_func.count())
            .select_from(watchlist_items)
            .where(watchlist_items.c.ibkr_account_id == ibkr_account_id)
            .where(watchlist_items.c.status == "active")
        ).scalar()
        return int(result or 0)

    def list_active_for_account(
        self, ibkr_account_id: str
    ) -> StorageListResult[WatchlistItemSeedRecord]:
        """Task 131: all active watchlist items for an account.

        Same shape as ``list_starter_seed_for_account`` but without the
        ``is_starter_seed`` filter — used by the multi-asset forecast
        universe resolver after the user has confirmed and possibly
        added their own items beyond the cold-start starter set.
        """

        rows = (
            self._connection.execute(
                select(watchlist_items)
                .where(watchlist_items.c.ibkr_account_id == ibkr_account_id)
                .where(watchlist_items.c.status == "active")
                .order_by(watchlist_items.c.symbol.asc())
            )
            .mappings()
            .all()
        )
        records = tuple(
            WatchlistItemSeedRecord(
                watchlist_item_id=row["watchlist_item_id"],
                ibkr_account_id=row["ibkr_account_id"],
                asset_id=row["asset_id"],
                symbol=row["symbol"],
                name=row["name"],
                exchange=row["exchange"],
                currency=row["currency"],
                security_type=row["security_type"],
                status=row["status"],
                source=row["source"],
                is_starter_seed=bool(row["is_starter_seed"]),
                seed_version=row["seed_version"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        )
        return StorageListResult(
            records,
            watchlist_items.name,
            f"{len(records)} actieve watchlist-items opgehaald.",
        )

    def list_starter_seed_for_account(
        self, ibkr_account_id: str
    ) -> StorageListResult[WatchlistItemSeedRecord]:
        rows = (
            self._connection.execute(
                select(watchlist_items)
                .where(watchlist_items.c.ibkr_account_id == ibkr_account_id)
                .where(watchlist_items.c.is_starter_seed.is_(True))
                .where(watchlist_items.c.status == "active")
                .order_by(watchlist_items.c.symbol.asc())
            )
            .mappings()
            .all()
        )
        records = tuple(
            WatchlistItemSeedRecord(
                watchlist_item_id=row["watchlist_item_id"],
                ibkr_account_id=row["ibkr_account_id"],
                asset_id=row["asset_id"],
                symbol=row["symbol"],
                name=row["name"],
                exchange=row["exchange"],
                currency=row["currency"],
                security_type=row["security_type"],
                status=row["status"],
                source=row["source"],
                is_starter_seed=bool(row["is_starter_seed"]),
                seed_version=row["seed_version"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        )
        return StorageListResult(
            records,
            watchlist_items.name,
            f"{len(records)} cold-start watchlist-items opgehaald.",
        )

    def archive_by_id(
        self, *, watchlist_item_id: str, ibkr_account_id: str
    ) -> bool:
        from datetime import UTC, datetime

        result = self._connection.execute(
            watchlist_items.update()
            .where(watchlist_items.c.watchlist_item_id == watchlist_item_id)
            .where(watchlist_items.c.ibkr_account_id == ibkr_account_id)
            .values(status="archived", updated_at=datetime.now(UTC))
        )
        return bool(result.rowcount)


class SqlAlchemyMarketDataEodSnapshotRepository(_Base):
    """Task 129: append-only EOD snapshot repository.

    Idempotency is enforced via the ``UNIQUE (ibkr_conid,
    as_of_date, provider)`` constraint at the DB level — a second
    ``append`` for the same triple raises an integrity error. The
    market-data step checks ``get_for_date`` first and skips the
    fetch when a row already exists.
    """

    def append(
        self, record: MarketDataEodSnapshotEntry
    ) -> StorageWriteResult:
        self._insert(market_data_eod_snapshots, asdict(record))
        return StorageWriteResult(
            True,
            record.snapshot_id,
            market_data_eod_snapshots.name,
            True,
            "EOD market-data snapshot opgeslagen.",
        )

    def get_for_date(
        self,
        *,
        ibkr_conid: str,
        as_of_date: Any,
        provider: str = "eodhd",
    ) -> MarketDataEodSnapshotEntry | None:
        row = (
            self._connection.execute(
                select(market_data_eod_snapshots)
                .where(market_data_eod_snapshots.c.ibkr_conid == ibkr_conid)
                .where(market_data_eod_snapshots.c.as_of_date == as_of_date)
                .where(market_data_eod_snapshots.c.provider == provider)
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return self._row_to_record(row)

    def get_latest_by_conid(
        self,
        *,
        ibkr_conid: str,
        provider: str = "eodhd",
    ) -> MarketDataEodSnapshotEntry | None:
        row = (
            self._connection.execute(
                select(market_data_eod_snapshots)
                .where(market_data_eod_snapshots.c.ibkr_conid == ibkr_conid)
                .where(market_data_eod_snapshots.c.provider == provider)
                .order_by(market_data_eod_snapshots.c.as_of_date.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return self._row_to_record(row)

    def list_latest_per_conid(
        self,
        *,
        ibkr_conids: tuple[str, ...],
        provider: str = "eodhd",
    ) -> StorageListResult[MarketDataEodSnapshotEntry]:
        if not ibkr_conids:
            return StorageListResult(
                tuple(),
                market_data_eod_snapshots.name,
                "0 EOD snapshots opgehaald.",
            )
        records: list[MarketDataEodSnapshotEntry] = []
        for conid in ibkr_conids:
            row = self.get_latest_by_conid(
                ibkr_conid=conid, provider=provider
            )
            if row is not None:
                records.append(row)
        return StorageListResult(
            tuple(records),
            market_data_eod_snapshots.name,
            f"{len(records)} EOD snapshots opgehaald.",
        )

    @staticmethod
    def _row_to_record(row: Any) -> MarketDataEodSnapshotEntry:
        return MarketDataEodSnapshotEntry(
            snapshot_id=row["snapshot_id"],
            ibkr_conid=row["ibkr_conid"],
            symbol=row["symbol"],
            exchange=row["exchange"],
            currency_local=row["currency_local"],
            as_of_date=row["as_of_date"],
            as_of_close_ts=row["as_of_close_ts"],
            ingested_ts=row["ingested_ts"],
            open_local=row["open_local"],
            high_local=row["high_local"],
            low_local=row["low_local"],
            close_local=row["close_local"],
            adj_close_local=row["adj_close_local"],
            volume=row["volume"],
            provider=row["provider"],
            provider_response_hash=row["provider_response_hash"],
        )


class SqlAlchemyFxRateRepository(_Base):
    """Task 129: per-day FX rate repository (PK = base+quote+date+provider)."""

    def upsert(self, record: FxRateRecord) -> StorageWriteResult:
        existing = self._connection.execute(
            select(fx_rates).where(
                fx_rates.c.base_currency == record.base_currency,
                fx_rates.c.quote_currency == record.quote_currency,
                fx_rates.c.as_of_date == record.as_of_date,
                fx_rates.c.provider == record.provider,
            )
        ).first()
        payload = asdict(record)
        if existing is None:
            self._insert(fx_rates, payload)
            return StorageWriteResult(
                True,
                f"{record.base_currency}->{record.quote_currency}"
                f"@{record.as_of_date}",
                fx_rates.name,
                True,
                "FX-rate rij ingevoegd.",
            )
        self._connection.execute(
            fx_rates.update()
            .where(fx_rates.c.base_currency == record.base_currency)
            .where(fx_rates.c.quote_currency == record.quote_currency)
            .where(fx_rates.c.as_of_date == record.as_of_date)
            .where(fx_rates.c.provider == record.provider)
            .values(rate=record.rate, ingested_ts=record.ingested_ts)
        )
        return StorageWriteResult(
            True,
            f"{record.base_currency}->{record.quote_currency}"
            f"@{record.as_of_date}",
            fx_rates.name,
            True,
            "FX-rate rij bijgewerkt.",
        )

    def get_rate(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        as_of_date: Any,
        provider: str = "eodhd",
    ) -> FxRateRecord | None:
        row = (
            self._connection.execute(
                select(fx_rates)
                .where(fx_rates.c.base_currency == base_currency)
                .where(fx_rates.c.quote_currency == quote_currency)
                .where(fx_rates.c.as_of_date == as_of_date)
                .where(fx_rates.c.provider == provider)
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return FxRateRecord(
            base_currency=row["base_currency"],
            quote_currency=row["quote_currency"],
            as_of_date=row["as_of_date"],
            rate=row["rate"],
            ingested_ts=row["ingested_ts"],
            provider=row["provider"],
        )

    def get_latest(
        self,
        *,
        base_currency: str,
        quote_currency: str,
        provider: str = "eodhd",
    ) -> FxRateRecord | None:
        row = (
            self._connection.execute(
                select(fx_rates)
                .where(fx_rates.c.base_currency == base_currency)
                .where(fx_rates.c.quote_currency == quote_currency)
                .where(fx_rates.c.provider == provider)
                .order_by(fx_rates.c.as_of_date.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return FxRateRecord(
            base_currency=row["base_currency"],
            quote_currency=row["quote_currency"],
            as_of_date=row["as_of_date"],
            rate=row["rate"],
            ingested_ts=row["ingested_ts"],
            provider=row["provider"],
        )


class SqlAlchemyProviderCallAuditRepository(_Base):
    """Task 129: append-only audit for every provider HTTP call."""

    def append(
        self, record: ProviderCallAuditEntry
    ) -> StorageWriteResult:
        self._insert(provider_call_audit, asdict(record))
        return StorageWriteResult(
            True,
            record.audit_id,
            provider_call_audit.name,
            True,
            "Provider-call audit-rij opgeslagen.",
        )

    def list_recent(
        self, *, limit: int = 20
    ) -> StorageListResult[ProviderCallAuditEntry]:
        rows = (
            self._connection.execute(
                select(provider_call_audit)
                .order_by(provider_call_audit.c.called_at.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        records = tuple(self._row_to_record(row) for row in rows)
        return StorageListResult(
            records,
            provider_call_audit.name,
            f"{len(records)} provider-call audit-rijen opgehaald.",
        )

    def list_for_run(
        self, *, run_id: str, limit: int = 50
    ) -> StorageListResult[ProviderCallAuditEntry]:
        rows = (
            self._connection.execute(
                select(provider_call_audit)
                .where(provider_call_audit.c.triggered_by_run_id == run_id)
                .order_by(provider_call_audit.c.called_at.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        records = tuple(self._row_to_record(row) for row in rows)
        return StorageListResult(
            records,
            provider_call_audit.name,
            f"{len(records)} provider-call audit-rijen voor run.",
        )

    @staticmethod
    def _row_to_record(row: Any) -> ProviderCallAuditEntry:
        return ProviderCallAuditEntry(
            audit_id=row["audit_id"],
            called_at=row["called_at"],
            provider=row["provider"],
            endpoint=row["endpoint"],
            request_params_json=row["request_params_json"],
            response_status=row["response_status"],
            response_size_bytes=row["response_size_bytes"],
            duration_ms=row["duration_ms"],
            error_class=row["error_class"],
            error_details_json=row["error_details_json"],
            account_id=row["account_id"],
            triggered_by_run_id=row["triggered_by_run_id"],
        )


class SqlAlchemyForecastRepository(_Base):
    """Task 130: append-only probabilistic-forecast repository.

    Locked CHECK constraints + UNIQUE on (conid, generated_at) at
    the DB level enforce method/label/confidence + one-row-per-fire
    semantics. ``mark_expired`` updates ``expired_at`` only (never
    the forecast values themselves).
    """

    def append(self, record: ForecastEntry) -> StorageWriteResult:
        self._insert(forecasts, asdict(record))
        return StorageWriteResult(
            True,
            record.forecast_run_id,
            forecasts.name,
            True,
            "Forecast opgeslagen.",
        )

    def get_by_run_id(
        self, forecast_run_id: str
    ) -> ForecastEntry | None:
        row = (
            self._connection.execute(
                select(forecasts).where(
                    forecasts.c.forecast_run_id == forecast_run_id
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return self._row_to_record(row)

    def get_latest_valid_for_conid(
        self,
        *,
        conid: str,
        now: datetime,
    ) -> ForecastEntry | None:
        row = (
            self._connection.execute(
                select(forecasts)
                .where(forecasts.c.conid == conid)
                .where(forecasts.c.forecast_valid_until > now)
                .order_by(forecasts.c.generated_at.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return self._row_to_record(row)

    def get_latest_valid_for_conids(
        self,
        *,
        conids: tuple[str, ...],
        now: datetime,
    ) -> tuple[ForecastEntry, ...]:
        """Task 131: latest valid forecast per conid in the input set.

        Returns at most one ``ForecastEntry`` per conid (the most
        recent generated_at with forecast_valid_until > now). Conids
        with no valid forecast are omitted from the result; the
        caller is responsible for surfacing "no forecast yet" in
        Dutch microcopy.
        """

        if not conids:
            return ()
        rows = (
            self._connection.execute(
                select(forecasts)
                .where(forecasts.c.conid.in_(conids))
                .where(forecasts.c.forecast_valid_until > now)
                .order_by(
                    forecasts.c.conid.asc(),
                    forecasts.c.generated_at.desc(),
                )
            )
            .mappings()
            .all()
        )
        latest_by_conid: dict[str, Any] = {}
        for row in rows:
            if row["conid"] not in latest_by_conid:
                latest_by_conid[row["conid"]] = row
        return tuple(
            self._row_to_record(row) for row in latest_by_conid.values()
        )

    def list_for_date_summary(
        self,
        *,
        conids: tuple[str, ...],
        as_of_date: date,
    ) -> dict[str, Any]:
        """Task 131: per-label counts for the latest forecasts generated on a date.

        Counts the latest forecast per conid whose ``generated_at``
        falls on ``as_of_date`` (UTC). Returns
        ``{label_counts, total_forecasts, total_blocked,
        block_reasons}`` — the shape the day-summary API surfaces.
        """

        if not conids:
            return {
                "label_counts": {},
                "total_forecasts": 0,
                "total_blocked": 0,
                "block_reasons": {},
            }
        from datetime import datetime as _dt
        from datetime import time as _time

        day_start = _dt.combine(as_of_date, _time.min, tzinfo=UTC)
        day_end = _dt.combine(as_of_date, _time.max, tzinfo=UTC)
        rows = (
            self._connection.execute(
                select(forecasts)
                .where(forecasts.c.conid.in_(conids))
                .where(forecasts.c.generated_at >= day_start)
                .where(forecasts.c.generated_at <= day_end)
                .order_by(
                    forecasts.c.conid.asc(),
                    forecasts.c.generated_at.desc(),
                )
            )
            .mappings()
            .all()
        )
        latest_by_conid: dict[str, Any] = {}
        for row in rows:
            if row["conid"] not in latest_by_conid:
                latest_by_conid[row["conid"]] = row
        label_counts: dict[str, int] = {}
        block_reasons: dict[str, int] = {}
        for row in latest_by_conid.values():
            label = row["label"]
            label_counts[label] = label_counts.get(label, 0) + 1
            if label == "Geblokkeerd" and row["block_reason"] is not None:
                reason = row["block_reason"]
                block_reasons[reason] = block_reasons.get(reason, 0) + 1
        return {
            "label_counts": label_counts,
            "total_forecasts": len(latest_by_conid),
            "total_blocked": label_counts.get("Geblokkeerd", 0),
            "block_reasons": block_reasons,
        }

    def list_expired_unprocessed(
        self, *, now: datetime, limit: int = 100
    ) -> StorageListResult[ForecastEntry]:
        rows = (
            self._connection.execute(
                select(forecasts)
                .where(forecasts.c.forecast_valid_until <= now)
                .where(forecasts.c.expired_at.is_(None))
                .order_by(forecasts.c.forecast_valid_until.asc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        records = tuple(self._row_to_record(row) for row in rows)
        return StorageListResult(
            records,
            forecasts.name,
            f"{len(records)} verlopen forecasts opgehaald.",
        )

    def mark_expired(
        self, *, forecast_run_id: str, expired_at: datetime
    ) -> StorageWriteResult:
        result = self._connection.execute(
            forecasts.update()
            .where(forecasts.c.forecast_run_id == forecast_run_id)
            .values(expired_at=expired_at)
        )
        ok = bool(result.rowcount)
        return StorageWriteResult(
            ok,
            forecast_run_id,
            forecasts.name,
            True,
            "Forecast gemarkeerd als verlopen." if ok else "Forecast niet gevonden.",
        )

    @staticmethod
    def _row_to_record(row: Any) -> ForecastEntry:
        return ForecastEntry(
            forecast_run_id=row["forecast_run_id"],
            conid=row["conid"],
            generated_at=row["generated_at"],
            generated_by_scheduled_run_id=row["generated_by_scheduled_run_id"],
            horizon_trading_days=row["horizon_trading_days"],
            forecast_valid_until=row["forecast_valid_until"],
            method=row["method"],
            history_window_days=row["history_window_days"],
            history_closes_count=row["history_closes_count"],
            current_price_local=row["current_price_local"],
            currency_local=row["currency_local"],
            p10_log_return=row["p10_log_return"],
            p50_log_return=row["p50_log_return"],
            p90_log_return=row["p90_log_return"],
            prob_positive=row["prob_positive"],
            prob_loss_gt_5pct=row["prob_loss_gt_5pct"],
            expected_volatility_annualized=row["expected_volatility_annualized"],
            confidence_level=row["confidence_level"],
            label=row["label"],
            block_reason=row["block_reason"],
            expired_at=row["expired_at"],
        )


class SqlAlchemyCalibrationDiaryRepository(_Base):
    """Task 130: append-only calibration diary.

    UNIQUE on ``forecast_run_id`` so the calibration step is
    idempotent — re-running for the same forecast raises the DB
    integrity error rather than double-counting.
    """

    def append(
        self, record: CalibrationDiaryEntry
    ) -> StorageWriteResult:
        self._insert(calibration_diary, asdict(record))
        return StorageWriteResult(
            True,
            record.forecast_run_id,
            calibration_diary.name,
            True,
            "Calibratie-dagboek rij opgeslagen.",
        )

    def list_recent(
        self, *, limit: int = 20
    ) -> StorageListResult[CalibrationDiaryEntry]:
        rows = (
            self._connection.execute(
                select(calibration_diary)
                .order_by(calibration_diary.c.evaluated_at.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        records = tuple(
            CalibrationDiaryEntry(
                forecast_run_id=row["forecast_run_id"],
                evaluated_at=row["evaluated_at"],
                realized_log_return=row["realized_log_return"],
                hit_status=row["hit_status"],
                realized_close_price=row["realized_close_price"],
            )
            for row in rows
        )
        return StorageListResult(
            records,
            calibration_diary.name,
            f"{len(records)} calibratie-rijen opgehaald.",
        )

    def coverage_stats(self, *, window_days: int = 90) -> dict[str, Any]:
        """Rolling coverage over the past ``window_days`` evaluations.

        Returns a small dict with the four locked summary stats the
        ``/calibration/coverage`` route surfaces.
        """

        from datetime import timedelta as _td

        cutoff_now = datetime.now(UTC)
        cutoff = cutoff_now - _td(days=window_days)
        rows = (
            self._connection.execute(
                select(calibration_diary)
                .where(calibration_diary.c.evaluated_at >= cutoff)
            )
            .mappings()
            .all()
        )
        evaluated = len(rows)
        if evaluated == 0:
            return {
                "forecasts_evaluated": 0,
                "hit_rate_within_band": None,
                "p10_p90_coverage_percent": None,
                "mean_realized_minus_p50": None,
            }
        within = sum(1 for row in rows if row["hit_status"] == "realized_within_p10_p90")
        hit_rate = Decimal(within) / Decimal(evaluated)
        return {
            "forecasts_evaluated": evaluated,
            "hit_rate_within_band": hit_rate,
            "p10_p90_coverage_percent": hit_rate * Decimal("100"),
            "mean_realized_minus_p50": None,
        }

    def coverage_stats_by_conid(
        self, *, conid: str, window_days: int = 90, min_sample_size: int = 5
    ) -> dict[str, Any]:
        """Task 131: per-asset rolling coverage stats.

        Joins ``calibration_diary`` against ``forecasts`` to filter by
        conid. Returns the same shape as ``coverage_stats`` plus a
        ``sufficient_history`` flag: ``True`` iff
        ``forecasts_evaluated >= min_sample_size``. Callers surface
        the "Onvoldoende historiek" fallback in the explanation panel
        when ``sufficient_history`` is False.
        """

        from datetime import timedelta as _td

        cutoff = datetime.now(UTC) - _td(days=window_days)
        rows = (
            self._connection.execute(
                select(calibration_diary, forecasts.c.conid)
                .select_from(
                    calibration_diary.join(
                        forecasts,
                        calibration_diary.c.forecast_run_id
                        == forecasts.c.forecast_run_id,
                    )
                )
                .where(forecasts.c.conid == conid)
                .where(calibration_diary.c.evaluated_at >= cutoff)
            )
            .mappings()
            .all()
        )
        evaluated = len(rows)
        sufficient = evaluated >= min_sample_size
        if evaluated == 0:
            return {
                "conid": conid,
                "forecasts_evaluated": 0,
                "hit_rate_within_band": None,
                "p10_p90_coverage_percent": None,
                "sufficient_history": sufficient,
            }
        within = sum(
            1 for row in rows if row["hit_status"] == "realized_within_p10_p90"
        )
        hit_rate = Decimal(within) / Decimal(evaluated)
        return {
            "conid": conid,
            "forecasts_evaluated": evaluated,
            "hit_rate_within_band": hit_rate,
            "p10_p90_coverage_percent": hit_rate * Decimal("100"),
            "sufficient_history": sufficient,
        }




class SqlAlchemyDecisionPackageRepository(_Base):
    """Task 132: append-only Decision Package repository.

    No ``update`` / ``delete`` methods exist by design — Decision
    Packages are immutable per Task 132 product lock §4. Storage-side
    CHECK constraints reject ``safe_for_action_drafts=True`` or
    ``safe_for_orders=True``; the dataclass enforces the same
    invariant at the Python layer (defense in depth).
    """

    def append(
        self, record: DecisionPackageEntry
    ) -> StorageWriteResult:
        if record.safe_for_action_drafts or record.safe_for_orders:
            raise ValueError(
                "safe_for_action_drafts and safe_for_orders must be "
                "False (Task 132 product lock §1)"
            )
        payload = {
            "decision_package_id": record.decision_package_id,
            "forecast_run_id": record.forecast_run_id,
            "composed_at": record.composed_at,
            "valid_until": record.valid_until,
            "ibkr_account_id": record.ibkr_account_id,
            "conid": record.conid,
            "symbol": record.symbol,
            "exchange": record.exchange,
            "currency_local": record.currency_local,
            "asset_class": record.asset_class,
            "user_holds_position": record.user_holds_position,
            "held_quantity": record.held_quantity,
            "held_avg_cost_local": record.held_avg_cost_local,
            "current_price_local": record.current_price_local,
            "current_price_eur": record.current_price_eur,
            "as_of_market_data_ts": record.as_of_market_data_ts,
            "freshness_state": record.freshness_state,
            "data_age_trading_days": record.data_age_trading_days,
            "forecast_method": record.forecast_method,
            "p10_log_return": record.p10_log_return,
            "p50_log_return": record.p50_log_return,
            "p90_log_return": record.p90_log_return,
            "p10_price_eur": record.p10_price_eur,
            "p50_price_eur": record.p50_price_eur,
            "p90_price_eur": record.p90_price_eur,
            "prob_positive": record.prob_positive,
            "prob_loss_gt_5pct": record.prob_loss_gt_5pct,
            "expected_volatility_annualized": (
                record.expected_volatility_annualized
            ),
            "forecast_confidence_level": record.forecast_confidence_level,
            "suggested_action_label": record.suggested_action_label,
            "block_reason": record.block_reason,
            "gate_outcomes_json": [
                {
                    "gate_name": g.gate_name,
                    "passed": g.passed,
                    "reason_nl": g.reason_nl,
                }
                for g in record.gate_outcomes
            ],
            "evidence_references_json": [
                {
                    "source_id": e.source_id,
                    "source_type": e.source_type,
                    "claim_summary": e.claim_summary,
                }
                for e in record.evidence_references
            ],
            "deterministic_dutch_explanation": (
                record.deterministic_dutch_explanation
            ),
            "audit_trail_hash": record.audit_trail_hash,
            "previous_package_hash": record.previous_package_hash,
            "safe_for_action_drafts": record.safe_for_action_drafts,
            "safe_for_orders": record.safe_for_orders,
        }
        self._insert(decision_packages, payload)
        return StorageWriteResult(
            True,
            record.decision_package_id,
            decision_packages.name,
            True,
            "Decision Package opgeslagen.",
        )

    def get_by_id(
        self, decision_package_id: str
    ) -> DecisionPackageEntry | None:
        row = (
            self._connection.execute(
                select(decision_packages).where(
                    decision_packages.c.decision_package_id
                    == decision_package_id
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return self._row_to_record(row)

    def get_latest_for_account_conid(
        self, *, ibkr_account_id: str, conid: str
    ) -> DecisionPackageEntry | None:
        row = (
            self._connection.execute(
                select(decision_packages)
                .where(
                    decision_packages.c.ibkr_account_id == ibkr_account_id
                )
                .where(decision_packages.c.conid == conid)
                .order_by(decision_packages.c.composed_at.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return self._row_to_record(row)

    def list_chain(
        self,
        *,
        ibkr_account_id: str,
        conid: str,
        limit: int = 20,
    ) -> StorageListResult[DecisionPackageEntry]:
        """Return the per-asset Decision Package chain, newest first."""

        rows = (
            self._connection.execute(
                select(decision_packages)
                .where(
                    decision_packages.c.ibkr_account_id == ibkr_account_id
                )
                .where(decision_packages.c.conid == conid)
                .order_by(decision_packages.c.composed_at.desc())
                .limit(_bounded_limit(limit))
            )
            .mappings()
            .all()
        )
        records = tuple(self._row_to_record(row) for row in rows)
        return StorageListResult(
            records,
            decision_packages.name,
            f"{len(records)} Decision Packages opgehaald.",
        )

    @staticmethod
    def _row_to_record(row: Any) -> DecisionPackageEntry:
        gates_payload = row["gate_outcomes_json"] or []
        evidence_payload = row["evidence_references_json"] or []
        return DecisionPackageEntry(
            decision_package_id=row["decision_package_id"],
            forecast_run_id=row["forecast_run_id"],
            composed_at=row["composed_at"],
            valid_until=row["valid_until"],
            ibkr_account_id=row["ibkr_account_id"],
            conid=row["conid"],
            symbol=row["symbol"],
            exchange=row["exchange"],
            currency_local=row["currency_local"],
            asset_class=row["asset_class"],
            user_holds_position=bool(row["user_holds_position"]),
            held_quantity=row["held_quantity"],
            held_avg_cost_local=row["held_avg_cost_local"],
            current_price_local=row["current_price_local"],
            current_price_eur=row["current_price_eur"],
            as_of_market_data_ts=row["as_of_market_data_ts"],
            freshness_state=row["freshness_state"],
            data_age_trading_days=row["data_age_trading_days"],
            forecast_method=row["forecast_method"],
            p10_log_return=row["p10_log_return"],
            p50_log_return=row["p50_log_return"],
            p90_log_return=row["p90_log_return"],
            p10_price_eur=row["p10_price_eur"],
            p50_price_eur=row["p50_price_eur"],
            p90_price_eur=row["p90_price_eur"],
            prob_positive=row["prob_positive"],
            prob_loss_gt_5pct=row["prob_loss_gt_5pct"],
            expected_volatility_annualized=(
                row["expected_volatility_annualized"]
            ),
            forecast_confidence_level=row["forecast_confidence_level"],
            suggested_action_label=row["suggested_action_label"],
            block_reason=row["block_reason"],
            gate_outcomes=tuple(
                GateOutcome(
                    gate_name=g["gate_name"],
                    passed=bool(g["passed"]),
                    reason_nl=g["reason_nl"],
                )
                for g in gates_payload
            ),
            evidence_references=tuple(
                EvidenceReference(
                    source_id=e["source_id"],
                    source_type=e["source_type"],
                    claim_summary=e["claim_summary"],
                )
                for e in evidence_payload
            ),
            deterministic_dutch_explanation=(
                row["deterministic_dutch_explanation"]
            ),
            audit_trail_hash=row["audit_trail_hash"],
            previous_package_hash=row["previous_package_hash"],
            safe_for_action_drafts=bool(row["safe_for_action_drafts"]),
            safe_for_orders=bool(row["safe_for_orders"]),
        )


class ActionDraftStateTransitionError(ValueError):
    """Raised when an Action Draft status transition is not allowed.

    The locked transition map mirrors Task 133 product lock §7:

    * ``proposed``  → ``edited`` | ``user_approved`` | ``dismissed`` | ``deleted`` | ``superseded``
    * ``edited``    → ``user_approved`` | ``dismissed`` | ``deleted`` | ``superseded``
    * ``user_approved`` is terminal for V1 (Task 134 will extend).
    * ``dismissed`` / ``deleted`` / ``superseded`` are terminal.
    """


_ACTION_DRAFT_TERMINAL_STATUSES = frozenset(
    {
        "dismissed",
        "deleted",
        "superseded",
        # Task 134 lifecycle terminal states.
        "filled",
        "cancelled",
        "rejected",
        "awaiting_reply_timeout",
        # Task 135 escalation terminal — written by Pass C when an
        # awaiting_reply_timeout draft has had no IBKR data for >24h.
        "requires_manual_review",
    }
)
_ACTION_DRAFT_TRANSITIONS: dict[str, frozenset[str]] = {
    "proposed": frozenset(
        {"edited", "user_approved", "dismissed", "deleted", "superseded"}
    ),
    "edited": frozenset(
        {"user_approved", "dismissed", "deleted", "superseded"}
    ),
    # Task 134b widens user_approved with the IBKR submission lifecycle.
    # ``dismissed``/``deleted`` stay reachable so the user can still
    # withdraw an approval before the worker sweeps it; ``submitted``
    # is the worker's entry into the IBKR lifecycle.
    "user_approved": frozenset({"submitted", "dismissed", "deleted"}),
    # Task 134 lifecycle transitions. IBKR's reply-handshake walks
    # ``submitted → accepted → working`` and then either fills,
    # cancels, or rejects. ``awaiting_reply_timeout`` is the safety
    # bucket when no callback arrives within 60s (Task 135 reconciles).
    # User-initiated cancellation can fire at any in-flight status:
    # the Task 134c ``cancel-submitted`` API route transitions to
    # ``pending_cancellation`` from ``submitted``, ``accepted``,
    # ``working``, or ``partially_filled``.
    "submitted": frozenset(
        {
            "accepted",
            "rejected",
            "cancelled",
            "pending_cancellation",
            "awaiting_reply_timeout",
            # Task 135 reconciliation heals: the IBKR fill or terminal
            # callback may have arrived in the gap between submit and
            # the worker's next callback poll; allow the heal to skip
            # the intermediate ``accepted``/``working`` states rather
            # than fabricate callback rows that never happened.
            "working",
            "filled",
            "partially_filled",
        }
    ),
    "accepted": frozenset(
        {
            "working",
            "cancelled",
            "rejected",
            "pending_cancellation",
            # Task 135 reconciliation heals — same rationale as
            # ``submitted`` above.
            "filled",
            "partially_filled",
        }
    ),
    "working": frozenset(
        {
            "filled",
            "partially_filled",
            "cancelled",
            "rejected",
            "pending_cancellation",
        }
    ),
    "partially_filled": frozenset(
        {"filled", "cancelled", "rejected", "pending_cancellation"}
    ),
    # The user requested cancellation, but IBKR may still fill or
    # partially-fill before the cancel propagates — that's a race the
    # state machine has to accommodate.
    "pending_cancellation": frozenset(
        {"cancelled", "filled", "partially_filled"}
    ),
    # Terminal — no transitions out.
    "dismissed": frozenset(),
    "deleted": frozenset(),
    "superseded": frozenset(),
    "filled": frozenset(),
    "cancelled": frozenset(),
    "rejected": frozenset(),
    # Task 135: ``awaiting_reply_timeout`` was terminal in Task 134,
    # but the reconciler can now heal it once IBKR-side evidence
    # arrives, or escalate it to ``requires_manual_review`` after the
    # 24h cut-off.
    "awaiting_reply_timeout": frozenset(
        {
            "filled",
            "partially_filled",
            "cancelled",
            "rejected",
            "requires_manual_review",
        }
    ),
    # Task 135 escalation terminal — Pass C writes here when an
    # awaiting_reply_timeout sits without IBKR data for >24h. The
    # user resolves the queue row to close the loop.
    "requires_manual_review": frozenset(),
}


def _require_action_draft_transition_allowed(
    from_status: str, to_status: str
) -> None:
    allowed = _ACTION_DRAFT_TRANSITIONS.get(from_status)
    if allowed is None or to_status not in allowed:
        raise ActionDraftStateTransitionError(
            f"Action Draft transition {from_status!r} → {to_status!r} "
            "is not allowed (Task 133 product lock §7)."
        )


class SqlAlchemyActionDraftRepository(_Base):
    """Task 133: ``action_drafts`` repository.

    Append-on-write; mutations go through ``update_fields`` /
    ``update_status`` / ``mark_superseded`` which also write one
    ``action_draft_audit`` row atomically. There is no ``delete()`` — a
    "delete" is a status transition that keeps the row intact (Task 133
    product lock §3).
    """

    def append(self, record: ActionDraftEntry) -> ActionDraftEntry:
        if record.safe_for_submission:
            raise ValueError(
                "safe_for_submission must be False (Task 133 product lock §3)"
            )
        self._insert(action_drafts, _new_action_draft_to_payload(record))
        self._connection.execute(
            action_draft_audit.insert().values(
                action_draft_id=record.action_draft_id,
                event_at=record.created_at,
                event_type="created",
                before_state_json=None,
                after_state_json=_new_action_draft_state_snapshot(record),
                actor=record.created_by,
            )
        )
        return record

    def get_by_id(
        self, action_draft_id: str
    ) -> ActionDraftEntry | None:
        row = (
            self._connection.execute(
                select(action_drafts).where(
                    action_drafts.c.action_draft_id == action_draft_id
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return _new_action_draft_from_row(row)

    def list_te_keuren_for_account(
        self, ibkr_account_id: str
    ) -> tuple[ActionDraftEntry, ...]:
        """Drafts in proposed/edited/user_approved (Task 133 §7)."""

        rows = (
            self._connection.execute(
                select(action_drafts)
                .where(action_drafts.c.ibkr_account_id == ibkr_account_id)
                .where(
                    action_drafts.c.status.in_(
                        ("proposed", "edited", "user_approved")
                    )
                )
                .order_by(action_drafts.c.created_at.desc())
            )
            .mappings()
            .all()
        )
        return tuple(_new_action_draft_from_row(row) for row in rows)

    def list_by_status(
        self, ibkr_account_id: str, status: str
    ) -> tuple[ActionDraftEntry, ...]:
        rows = (
            self._connection.execute(
                select(action_drafts)
                .where(action_drafts.c.ibkr_account_id == ibkr_account_id)
                .where(action_drafts.c.status == status)
                .order_by(action_drafts.c.created_at.desc())
            )
            .mappings()
            .all()
        )
        return tuple(_new_action_draft_from_row(row) for row in rows)

    def list_pending_for_conid(
        self, *, ibkr_account_id: str, conid: str
    ) -> tuple[ActionDraftEntry, ...]:
        """Pending drafts (``proposed`` / ``edited``) for a (conid, account).

        Used by the supersede check — only drafts the user has not yet
        resolved are eligible to be flagged superseded.
        """

        rows = (
            self._connection.execute(
                select(action_drafts)
                .where(action_drafts.c.ibkr_account_id == ibkr_account_id)
                .where(action_drafts.c.conid == conid)
                .where(action_drafts.c.status.in_(("proposed", "edited")))
                .order_by(action_drafts.c.created_at.desc())
            )
            .mappings()
            .all()
        )
        return tuple(_new_action_draft_from_row(row) for row in rows)

    def update_status(
        self,
        *,
        action_draft_id: str,
        new_status: str,
        transition_actor: str,
        transition_at: datetime,
        dismissed_reason: str | None = None,
    ) -> ActionDraftEntry:
        current = self.get_by_id(action_draft_id)
        if current is None:
            raise LookupError(
                f"Action Draft {action_draft_id!r} niet gevonden."
            )
        _require_action_draft_transition_allowed(
            current.status, new_status
        )
        if transition_actor not in {"user", "system"}:
            raise ValueError(
                f"transition_actor {transition_actor!r} not in "
                "{'user','system'}"
            )
        updates: dict[str, Any] = {"status": new_status}
        if new_status == "user_approved":
            updates["user_approved_at"] = transition_at
        elif new_status == "dismissed":
            updates["dismissed_at"] = transition_at
            if dismissed_reason is not None:
                updates["dismissed_reason"] = dismissed_reason
            updates["superseded_by_decision_package_id"] = None
        elif new_status == "deleted":
            updates["deleted_at"] = transition_at
            updates["superseded_by_decision_package_id"] = None
        elif new_status == "edited":
            updates["last_edited_at"] = transition_at

        self._connection.execute(
            action_drafts.update()
            .where(action_drafts.c.action_draft_id == action_draft_id)
            .values(**updates)
        )
        updated = self.get_by_id(action_draft_id)
        if updated is None:  # pragma: no cover — defensive
            raise LookupError(
                f"Action Draft {action_draft_id!r} disappeared after update."
            )
        event_type = _STATUS_TO_EVENT_TYPE[new_status]
        self._connection.execute(
            action_draft_audit.insert().values(
                action_draft_id=action_draft_id,
                event_at=transition_at,
                event_type=event_type,
                before_state_json=_new_action_draft_state_snapshot(current),
                after_state_json=_new_action_draft_state_snapshot(updated),
                actor=transition_actor,
            )
        )
        return updated

    def update_fields(
        self,
        *,
        action_draft_id: str,
        quantity: Decimal | None = None,
        limit_price_local: Decimal | None = None,
        notional_local: Decimal | None = None,
        notional_eur: Decimal | None = None,
        user_note: str | None = None,
        actor: str,
        edited_at: datetime,
    ) -> ActionDraftEntry:
        current = self.get_by_id(action_draft_id)
        if current is None:
            raise LookupError(
                f"Action Draft {action_draft_id!r} niet gevonden."
            )
        if current.status not in ("proposed", "edited"):
            raise ActionDraftStateTransitionError(
                f"Edits niet toegestaan in status {current.status!r}."
            )
        updates: dict[str, Any] = {"last_edited_at": edited_at}
        if current.status == "proposed":
            updates["status"] = "edited"
        if quantity is not None:
            updates["quantity"] = quantity
        if limit_price_local is not None:
            updates["limit_price_local"] = limit_price_local
        if notional_local is not None:
            updates["notional_local"] = notional_local
        if notional_eur is not None:
            updates["notional_eur"] = notional_eur
        if user_note is not None:
            updates["user_note"] = user_note
        self._connection.execute(
            action_drafts.update()
            .where(action_drafts.c.action_draft_id == action_draft_id)
            .values(**updates)
        )
        updated = self.get_by_id(action_draft_id)
        if updated is None:  # pragma: no cover — defensive
            raise LookupError(
                f"Action Draft {action_draft_id!r} disappeared after edit."
            )
        self._connection.execute(
            action_draft_audit.insert().values(
                action_draft_id=action_draft_id,
                event_at=edited_at,
                event_type="edited",
                before_state_json=_new_action_draft_state_snapshot(current),
                after_state_json=_new_action_draft_state_snapshot(updated),
                actor=actor,
            )
        )
        return updated

    def mark_superseded(
        self,
        *,
        action_draft_id: str,
        by_decision_package_id: str,
        marked_at: datetime,
    ) -> ActionDraftEntry:
        """Flag a pending draft as superseded (Task 133 product lock §6).

        Only ``proposed`` / ``edited`` drafts are eligible — already
        dismissed / deleted / approved drafts are NOT touched.
        """

        current = self.get_by_id(action_draft_id)
        if current is None:
            raise LookupError(
                f"Action Draft {action_draft_id!r} niet gevonden."
            )
        if current.status not in ("proposed", "edited"):
            raise ActionDraftStateTransitionError(
                f"Cannot supersede draft in status {current.status!r}."
            )
        self._connection.execute(
            action_drafts.update()
            .where(action_drafts.c.action_draft_id == action_draft_id)
            .values(
                superseded_by_decision_package_id=by_decision_package_id,
            )
        )
        updated = self.get_by_id(action_draft_id)
        if updated is None:  # pragma: no cover — defensive
            raise LookupError(
                f"Action Draft {action_draft_id!r} disappeared after "
                "supersede."
            )
        self._connection.execute(
            action_draft_audit.insert().values(
                action_draft_id=action_draft_id,
                event_at=marked_at,
                event_type="superseded",
                before_state_json=_new_action_draft_state_snapshot(current),
                after_state_json=_new_action_draft_state_snapshot(updated),
                actor="system",
            )
        )
        return updated

    # -----------------------------------------------------------------
    # Task 134b — IBKR lifecycle helpers.
    # The user-facing audit chain (``action_draft_audit``) records only
    # user actions (created/edited/approved/dismissed/deleted/superseded);
    # the in-flight IBKR transitions (submitted/accepted/working/filled/
    # ...) have their own audit table ``ibkr_submission_lifecycle``
    # written by ``lifecycle_handler`` separately. That's why
    # ``apply_lifecycle_transition`` updates draft state without
    # writing an ``action_draft_audit`` row.
    # -----------------------------------------------------------------

    def apply_lifecycle_transition(
        self,
        *,
        action_draft_id: str,
        new_status: str,
        transitioned_at: datetime,
    ) -> ActionDraftEntry:
        """Apply an IBKR-driven status transition (Task 134 lock §6).

        Validates against ``_ACTION_DRAFT_TRANSITIONS`` and sets the
        appropriate lifecycle timestamp (``submission_started_at`` on
        ``submitted`` entry; ``terminal_state_at`` on terminal states).
        Does not write ``action_draft_audit`` — the lifecycle handler
        writes ``ibkr_submission_lifecycle`` itself.
        """

        current = self.get_by_id(action_draft_id)
        if current is None:
            raise LookupError(
                f"Action Draft {action_draft_id!r} niet gevonden."
            )
        _require_action_draft_transition_allowed(
            current.status, new_status
        )
        updates: dict[str, Any] = {"status": new_status}
        if new_status == "submitted":
            updates["submission_started_at"] = transitioned_at
            # Clear any prior block reason — the sweep is committing.
            updates["submission_block_reason"] = None
        if new_status in _ACTION_DRAFT_TERMINAL_STATUSES:
            updates["terminal_state_at"] = transitioned_at
        self._connection.execute(
            action_drafts.update()
            .where(action_drafts.c.action_draft_id == action_draft_id)
            .values(**updates)
        )
        updated = self.get_by_id(action_draft_id)
        if updated is None:  # pragma: no cover — defensive
            raise LookupError(
                f"Action Draft {action_draft_id!r} disappeared after "
                "lifecycle transition."
            )
        return updated

    def set_submission_block_reason(
        self,
        *,
        action_draft_id: str,
        reason: str,
        set_at: datetime,
    ) -> ActionDraftEntry:
        """Stamp a block reason without changing status (Task 134 lock §3).

        The draft stays at ``user_approved`` so the UI can surface the
        Dutch ``submission_block_reason`` badge on the Te keuren tab.
        The sweep retries on the next tick; the reason gets replaced
        if a different gate trips, or cleared on a successful
        ``submitted`` transition.
        """

        current = self.get_by_id(action_draft_id)
        if current is None:
            raise LookupError(
                f"Action Draft {action_draft_id!r} niet gevonden."
            )
        if current.status != "user_approved":
            raise ActionDraftStateTransitionError(
                "submission_block_reason kan alleen op user_approved "
                f"drafts gezet worden; status is {current.status!r}."
            )
        self._connection.execute(
            action_drafts.update()
            .where(action_drafts.c.action_draft_id == action_draft_id)
            .values(submission_block_reason=reason)
        )
        # ``set_at`` is captured for downstream observability in the
        # sweep tick log but not persisted on the draft row itself
        # (the column doesn't exist — we'd otherwise need a new
        # column for last_block_at, which is out of scope for 134b).
        _ = set_at  # kept in the signature for future expansion.
        updated = self.get_by_id(action_draft_id)
        if updated is None:  # pragma: no cover — defensive
            raise LookupError(
                f"Action Draft {action_draft_id!r} disappeared after "
                "block-reason update."
            )
        return updated

    def list_in_flight_for_conid(
        self, *, ibkr_account_id: str, conid: str
    ) -> tuple[ActionDraftEntry, ...]:
        """In-flight drafts for the (account, conid) duplicate-detection gate.

        Returns drafts in any status the Tier 1 safety_recheck treats
        as "already going to IBKR": submitted / accepted / working /
        partially_filled / pending_cancellation. Used by the sweep to
        block a second draft for the same asset while one is still
        live.
        """

        rows = (
            self._connection.execute(
                select(action_drafts)
                .where(action_drafts.c.ibkr_account_id == ibkr_account_id)
                .where(action_drafts.c.conid == conid)
                .where(
                    action_drafts.c.status.in_(
                        (
                            "submitted",
                            "accepted",
                            "working",
                            "partially_filled",
                            "pending_cancellation",
                        )
                    )
                )
                .order_by(action_drafts.c.created_at.desc())
            )
            .mappings()
            .all()
        )
        return tuple(_new_action_draft_from_row(row) for row in rows)

    def list_user_approved_for_sweep(
        self, *, ibkr_account_id: str
    ) -> tuple[ActionDraftEntry, ...]:
        """FIFO list of ``user_approved`` drafts for the sweep job.

        Ordered by ``user_approved_at`` ascending so the oldest
        approval gets the next sweep tick. Block-reason drafts (still
        ``user_approved`` but with a non-NULL ``submission_block_reason``)
        are still returned — the gate evaluation may pass on the next
        tick and clear the reason.
        """

        rows = (
            self._connection.execute(
                select(action_drafts)
                .where(action_drafts.c.ibkr_account_id == ibkr_account_id)
                .where(action_drafts.c.status == "user_approved")
                .order_by(action_drafts.c.user_approved_at.asc())
            )
            .mappings()
            .all()
        )
        return tuple(_new_action_draft_from_row(row) for row in rows)

    def list_pending_cancellation(
        self, *, ibkr_account_id: str
    ) -> tuple[ActionDraftEntry, ...]:
        """FIFO list of ``pending_cancellation`` drafts for the cancel sweep.

        Ordered by ``terminal_state_at`` (when the cancel was requested)
        ascending so the oldest cancellation request is sent first. The
        cancel is fire-and-forget; the reconciler's Pass B converges the
        draft to ``cancelled`` once IBKR confirms.
        """

        rows = (
            self._connection.execute(
                select(action_drafts)
                .where(action_drafts.c.ibkr_account_id == ibkr_account_id)
                .where(action_drafts.c.status == "pending_cancellation")
                .order_by(action_drafts.c.terminal_state_at.asc())
            )
            .mappings()
            .all()
        )
        return tuple(_new_action_draft_from_row(row) for row in rows)

    def list_active_for_account(
        self, *, ibkr_account_id: str
    ) -> tuple[ActionDraftEntry, ...]:
        """Task 134c — drafts shown in the "Actief bij IBKR" tab.

        Returns drafts in any in-flight status:
        ``submitted`` / ``accepted`` / ``working`` / ``partially_filled``
        / ``pending_cancellation``. Newest-first by
        ``submission_started_at`` so the most recent submission sits at
        the top of the grid.
        """

        rows = (
            self._connection.execute(
                select(action_drafts)
                .where(action_drafts.c.ibkr_account_id == ibkr_account_id)
                .where(
                    action_drafts.c.status.in_(
                        (
                            "submitted",
                            "accepted",
                            "working",
                            "partially_filled",
                            "pending_cancellation",
                        )
                    )
                )
                .order_by(
                    action_drafts.c.submission_started_at.desc().nullslast()
                )
            )
            .mappings()
            .all()
        )
        return tuple(_new_action_draft_from_row(row) for row in rows)

    def list_terminal_for_account(
        self, *, ibkr_account_id: str, limit: int = 50
    ) -> tuple[ActionDraftEntry, ...]:
        """Task 134c — drafts shown in the "Historiek" tab.

        Returns drafts in any terminal status (filled / cancelled /
        rejected / awaiting_reply_timeout / dismissed / deleted /
        superseded), newest-first by ``terminal_state_at`` falling back
        to ``created_at`` for the legacy user-terminal rows that
        pre-date the lifecycle columns.
        """

        rows = (
            self._connection.execute(
                select(action_drafts)
                .where(action_drafts.c.ibkr_account_id == ibkr_account_id)
                .where(
                    action_drafts.c.status.in_(
                        (
                            "filled",
                            "cancelled",
                            "rejected",
                            "awaiting_reply_timeout",
                            "dismissed",
                            "deleted",
                            "superseded",
                        )
                    )
                )
                .order_by(
                    action_drafts.c.terminal_state_at.desc().nullslast(),
                    action_drafts.c.created_at.desc(),
                )
                .limit(_ibkr_audit_bounded_limit(limit, upper=200))
            )
            .mappings()
            .all()
        )
        return tuple(_new_action_draft_from_row(row) for row in rows)


class SqlAlchemyActionDraftAuditRepository(_Base):
    """Task 133: append-only ``action_draft_audit`` repository."""

    def append(
        self, entry: ActionDraftAuditEntry
    ) -> ActionDraftAuditEntry:
        result = self._connection.execute(
            action_draft_audit.insert()
            .values(
                action_draft_id=entry.action_draft_id,
                event_at=entry.event_at,
                event_type=entry.event_type,
                before_state_json=entry.before_state_json,
                after_state_json=entry.after_state_json,
                actor=entry.actor,
            )
            .returning(action_draft_audit.c.id)
        )
        row = result.first()
        new_id = int(row[0]) if row is not None else None
        return ActionDraftAuditEntry(
            action_draft_id=entry.action_draft_id,
            event_at=entry.event_at,
            event_type=entry.event_type,
            before_state_json=entry.before_state_json,
            after_state_json=entry.after_state_json,
            actor=entry.actor,
            id=new_id,
        )

    def list_for_draft(
        self, action_draft_id: str
    ) -> tuple[ActionDraftAuditEntry, ...]:
        rows = (
            self._connection.execute(
                select(action_draft_audit)
                .where(
                    action_draft_audit.c.action_draft_id == action_draft_id
                )
                .order_by(action_draft_audit.c.event_at)
            )
            .mappings()
            .all()
        )
        return tuple(
            ActionDraftAuditEntry(
                id=int(row["id"]),
                action_draft_id=row["action_draft_id"],
                event_at=row["event_at"],
                event_type=row["event_type"],
                before_state_json=(
                    dict(row["before_state_json"])
                    if row["before_state_json"] is not None
                    else None
                ),
                after_state_json=(
                    dict(row["after_state_json"])
                    if row["after_state_json"] is not None
                    else None
                ),
                actor=row["actor"],
            )
            for row in rows
        )


_STATUS_TO_EVENT_TYPE: dict[str, str] = {
    "edited": "edited",
    "user_approved": "approved",
    "dismissed": "dismissed",
    "deleted": "deleted",
    "superseded": "superseded",
}


def _new_action_draft_to_payload(record: ActionDraftEntry) -> dict[str, Any]:
    return {
        "action_draft_id": record.action_draft_id,
        "decision_package_id": record.decision_package_id,
        "forecast_run_id": record.forecast_run_id,
        "created_at": record.created_at,
        "created_by": record.created_by,
        "ibkr_account_id": record.ibkr_account_id,
        "conid": record.conid,
        "symbol": record.symbol,
        "exchange": record.exchange,
        "currency_local": record.currency_local,
        "side": record.side,
        "quantity": record.quantity,
        "order_type": record.order_type,
        "limit_price_local": record.limit_price_local,
        "time_in_force": record.time_in_force,
        "notional_local": record.notional_local,
        "notional_eur": record.notional_eur,
        "fx_rate_at_creation": record.fx_rate_at_creation,
        "usable_cash_eur_at_creation": record.usable_cash_eur_at_creation,
        "held_quantity_at_creation": record.held_quantity_at_creation,
        "status": record.status,
        "last_edited_at": record.last_edited_at,
        "user_approved_at": record.user_approved_at,
        "dismissed_at": record.dismissed_at,
        "deleted_at": record.deleted_at,
        "dismissed_reason": record.dismissed_reason,
        "user_note": record.user_note,
        "superseded_by_decision_package_id": (
            record.superseded_by_decision_package_id
        ),
        "audit_trail_hash": record.audit_trail_hash,
        "previous_draft_hash": record.previous_draft_hash,
        "safe_for_submission": record.safe_for_submission,
        "submission_block_reason": record.submission_block_reason,
        "submission_started_at": record.submission_started_at,
        "terminal_state_at": record.terminal_state_at,
    }


def _new_action_draft_from_row(row: Any) -> ActionDraftEntry:
    return ActionDraftEntry(
        action_draft_id=row["action_draft_id"],
        decision_package_id=row["decision_package_id"],
        forecast_run_id=row["forecast_run_id"],
        created_at=row["created_at"],
        created_by=row["created_by"],
        ibkr_account_id=row["ibkr_account_id"],
        conid=row["conid"],
        symbol=row["symbol"],
        exchange=row["exchange"],
        currency_local=row["currency_local"],
        side=row["side"],
        quantity=_to_decimal(row["quantity"]) or Decimal("0"),
        order_type=row["order_type"],
        limit_price_local=(
            _to_decimal(row["limit_price_local"]) or Decimal("0")
        ),
        time_in_force=row["time_in_force"],
        notional_local=_to_decimal(row["notional_local"]) or Decimal("0"),
        notional_eur=_to_decimal(row["notional_eur"]) or Decimal("0"),
        fx_rate_at_creation=(
            _to_decimal(row["fx_rate_at_creation"]) or Decimal("0")
        ),
        usable_cash_eur_at_creation=(
            _to_decimal(row["usable_cash_eur_at_creation"]) or Decimal("0")
        ),
        held_quantity_at_creation=_to_decimal(
            row["held_quantity_at_creation"]
        ),
        status=row["status"],
        last_edited_at=row["last_edited_at"],
        user_approved_at=row["user_approved_at"],
        dismissed_at=row["dismissed_at"],
        deleted_at=row["deleted_at"],
        dismissed_reason=row["dismissed_reason"],
        user_note=row["user_note"],
        superseded_by_decision_package_id=row[
            "superseded_by_decision_package_id"
        ],
        audit_trail_hash=row["audit_trail_hash"],
        previous_draft_hash=row["previous_draft_hash"],
        safe_for_submission=bool(row["safe_for_submission"]),
        submission_block_reason=row.get(
            "submission_block_reason"
        ),
        submission_started_at=row.get("submission_started_at"),
        terminal_state_at=row.get("terminal_state_at"),
    )


def _new_action_draft_state_snapshot(
    record: ActionDraftEntry,
) -> dict[str, object]:
    """Canonical JSON-friendly snapshot for the audit table.

    Decimals → strings (full precision); datetimes → ISO 8601. Used as
    both ``before_state_json`` and ``after_state_json``.
    """

    def _dec(value: Decimal | None) -> str | None:
        return None if value is None else str(value)

    def _ts(value: datetime | None) -> str | None:
        return None if value is None else value.isoformat()

    return {
        "action_draft_id": record.action_draft_id,
        "decision_package_id": record.decision_package_id,
        "forecast_run_id": record.forecast_run_id,
        "created_at": _ts(record.created_at),
        "created_by": record.created_by,
        "ibkr_account_id": record.ibkr_account_id,
        "conid": record.conid,
        "symbol": record.symbol,
        "exchange": record.exchange,
        "currency_local": record.currency_local,
        "side": record.side,
        "quantity": _dec(record.quantity),
        "order_type": record.order_type,
        "limit_price_local": _dec(record.limit_price_local),
        "time_in_force": record.time_in_force,
        "notional_local": _dec(record.notional_local),
        "notional_eur": _dec(record.notional_eur),
        "fx_rate_at_creation": _dec(record.fx_rate_at_creation),
        "usable_cash_eur_at_creation": _dec(
            record.usable_cash_eur_at_creation
        ),
        "held_quantity_at_creation": _dec(record.held_quantity_at_creation),
        "status": record.status,
        "last_edited_at": _ts(record.last_edited_at),
        "user_approved_at": _ts(record.user_approved_at),
        "dismissed_at": _ts(record.dismissed_at),
        "deleted_at": _ts(record.deleted_at),
        "dismissed_reason": record.dismissed_reason,
        "user_note": record.user_note,
        "superseded_by_decision_package_id": (
            record.superseded_by_decision_package_id
        ),
        "audit_trail_hash": record.audit_trail_hash,
        "previous_draft_hash": record.previous_draft_hash,
    }


class SqlAlchemyIbkrSubmissionAuditRepository(_Base):
    """Task 134: append-only ``ibkr_submission_audit`` repository.

    Written by the worker immediately after every ``placeOrder()``
    attempt. No update/delete methods exist — fixes for a corrupt row
    are recorded as a new compensating row.
    """

    def append(
        self, entry: IbkrSubmissionAuditEntry
    ) -> IbkrSubmissionAuditEntry:
        result = self._connection.execute(
            ibkr_submission_audit.insert()
            .values(
                action_draft_id=entry.action_draft_id,
                submitted_at=entry.submitted_at,
                sent_to_account_id=entry.sent_to_account_id,
                sent_account_mode=entry.sent_account_mode,
                ibkr_perm_id=entry.ibkr_perm_id,
                ibkr_order_id=entry.ibkr_order_id,
                contract_json=entry.contract_json,
                order_json=entry.order_json,
                gateway_session_id=entry.gateway_session_id,
                result=entry.result,
                error_class=entry.error_class,
                error_message_dutch=entry.error_message_dutch,
            )
            .returning(ibkr_submission_audit.c.id)
        )
        row = result.first()
        new_id = int(row[0]) if row is not None else None
        return IbkrSubmissionAuditEntry(
            action_draft_id=entry.action_draft_id,
            submitted_at=entry.submitted_at,
            sent_to_account_id=entry.sent_to_account_id,
            sent_account_mode=entry.sent_account_mode,
            ibkr_perm_id=entry.ibkr_perm_id,
            ibkr_order_id=entry.ibkr_order_id,
            contract_json=entry.contract_json,
            order_json=entry.order_json,
            gateway_session_id=entry.gateway_session_id,
            result=entry.result,
            error_class=entry.error_class,
            error_message_dutch=entry.error_message_dutch,
            id=new_id,
        )

    def list_for_account(
        self, *, ibkr_account_id: str, limit: int = 50
    ) -> tuple[IbkrSubmissionAuditEntry, ...]:
        rows = (
            self._connection.execute(
                select(ibkr_submission_audit)
                .where(
                    ibkr_submission_audit.c.sent_to_account_id
                    == ibkr_account_id
                )
                .order_by(
                    ibkr_submission_audit.c.submitted_at.desc()
                )
                .limit(_ibkr_audit_bounded_limit(limit, upper=200))
            )
            .mappings()
            .all()
        )
        return tuple(_ibkr_submission_audit_from_row(r) for r in rows)

    def list_for_draft(
        self, action_draft_id: str
    ) -> tuple[IbkrSubmissionAuditEntry, ...]:
        rows = (
            self._connection.execute(
                select(ibkr_submission_audit)
                .where(
                    ibkr_submission_audit.c.action_draft_id
                    == action_draft_id
                )
                .order_by(ibkr_submission_audit.c.submitted_at)
            )
            .mappings()
            .all()
        )
        return tuple(_ibkr_submission_audit_from_row(r) for r in rows)

    def get_action_draft_id_for_perm_id(
        self, ibkr_perm_id: int
    ) -> str | None:
        """Task 135 Pass A — reverse-lookup the draft that placed a
        perm_id. Returns the most recent submission's draft when
        multiple audit rows exist (which only happens on retries with
        the same perm_id, which IBKR doesn't issue)."""

        row = (
            self._connection.execute(
                select(
                    ibkr_submission_audit.c.action_draft_id
                ).where(
                    ibkr_submission_audit.c.ibkr_perm_id
                    == ibkr_perm_id
                )
                .order_by(ibkr_submission_audit.c.submitted_at.desc())
                .limit(1)
            )
            .first()
        )
        return None if row is None else str(row[0])


class SqlAlchemyIbkrSubmissionLifecycleRepository(_Base):
    """Task 134: append-only ``ibkr_submission_lifecycle`` repository."""

    def append(
        self, entry: IbkrSubmissionLifecycleEntry
    ) -> IbkrSubmissionLifecycleEntry:
        result = self._connection.execute(
            ibkr_submission_lifecycle.insert()
            .values(
                action_draft_id=entry.action_draft_id,
                event_at=entry.event_at,
                ibkr_perm_id=entry.ibkr_perm_id,
                event_type=entry.event_type,
                from_status=entry.from_status,
                to_status=entry.to_status,
                ibkr_raw_status=entry.ibkr_raw_status,
                fill_price_local=entry.fill_price_local,
                fill_quantity=entry.fill_quantity,
                commission=entry.commission,
                commission_currency=entry.commission_currency,
                raw_callback_json=entry.raw_callback_json,
            )
            .returning(ibkr_submission_lifecycle.c.id)
        )
        row = result.first()
        new_id = int(row[0]) if row is not None else None
        return IbkrSubmissionLifecycleEntry(
            action_draft_id=entry.action_draft_id,
            event_at=entry.event_at,
            ibkr_perm_id=entry.ibkr_perm_id,
            event_type=entry.event_type,
            from_status=entry.from_status,
            to_status=entry.to_status,
            ibkr_raw_status=entry.ibkr_raw_status,
            fill_price_local=entry.fill_price_local,
            fill_quantity=entry.fill_quantity,
            commission=entry.commission,
            commission_currency=entry.commission_currency,
            raw_callback_json=entry.raw_callback_json,
            id=new_id,
        )

    def list_for_draft(
        self, action_draft_id: str
    ) -> tuple[IbkrSubmissionLifecycleEntry, ...]:
        rows = (
            self._connection.execute(
                select(ibkr_submission_lifecycle)
                .where(
                    ibkr_submission_lifecycle.c.action_draft_id
                    == action_draft_id
                )
                .order_by(ibkr_submission_lifecycle.c.event_at)
            )
            .mappings()
            .all()
        )
        return tuple(
            _ibkr_submission_lifecycle_from_row(r) for r in rows
        )

    def list_for_perm_id(
        self, ibkr_perm_id: int
    ) -> tuple[IbkrSubmissionLifecycleEntry, ...]:
        rows = (
            self._connection.execute(
                select(ibkr_submission_lifecycle)
                .where(
                    ibkr_submission_lifecycle.c.ibkr_perm_id == ibkr_perm_id
                )
                .order_by(ibkr_submission_lifecycle.c.event_at)
            )
            .mappings()
            .all()
        )
        return tuple(
            _ibkr_submission_lifecycle_from_row(r) for r in rows
        )


class SqlAlchemyIbkrExecutionsRepository(_Base):
    """Task 134: append-only ``ibkr_executions`` repository.

    Unique on ``ibkr_exec_id`` — a duplicate fill notification from
    IBKR raises ``IntegrityError`` at insert time, which is the
    correct behaviour (the caller treats it as already-recorded).
    """

    def append(self, entry: IbkrExecutionEntry) -> IbkrExecutionEntry:
        result = self._connection.execute(
            ibkr_executions.insert()
            .values(
                ibkr_exec_id=entry.ibkr_exec_id,
                ibkr_perm_id=entry.ibkr_perm_id,
                action_draft_id=entry.action_draft_id,
                account_id=entry.account_id,
                conid=entry.conid,
                side=entry.side,
                fill_price_local=entry.fill_price_local,
                fill_quantity=entry.fill_quantity,
                fill_time=entry.fill_time,
                commission=entry.commission,
                commission_currency=entry.commission_currency,
                exchange=entry.exchange,
            )
            .returning(ibkr_executions.c.id)
        )
        row = result.first()
        new_id = int(row[0]) if row is not None else None
        return IbkrExecutionEntry(
            ibkr_exec_id=entry.ibkr_exec_id,
            ibkr_perm_id=entry.ibkr_perm_id,
            action_draft_id=entry.action_draft_id,
            account_id=entry.account_id,
            conid=entry.conid,
            side=entry.side,
            fill_price_local=entry.fill_price_local,
            fill_quantity=entry.fill_quantity,
            fill_time=entry.fill_time,
            commission=entry.commission,
            commission_currency=entry.commission_currency,
            exchange=entry.exchange,
            id=new_id,
        )

    def get_by_exec_id(
        self, ibkr_exec_id: str
    ) -> IbkrExecutionEntry | None:
        row = (
            self._connection.execute(
                select(ibkr_executions).where(
                    ibkr_executions.c.ibkr_exec_id == ibkr_exec_id
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return _ibkr_execution_from_row(row)

    def list_for_account_conid(
        self, *, account_id: str, conid: str
    ) -> tuple[IbkrExecutionEntry, ...]:
        rows = (
            self._connection.execute(
                select(ibkr_executions)
                .where(ibkr_executions.c.account_id == account_id)
                .where(ibkr_executions.c.conid == conid)
                .order_by(ibkr_executions.c.fill_time.desc())
            )
            .mappings()
            .all()
        )
        return tuple(_ibkr_execution_from_row(r) for r in rows)

    def list_for_draft(
        self, action_draft_id: str
    ) -> tuple[IbkrExecutionEntry, ...]:
        rows = (
            self._connection.execute(
                select(ibkr_executions)
                .where(
                    ibkr_executions.c.action_draft_id == action_draft_id
                )
                .order_by(ibkr_executions.c.fill_time)
            )
            .mappings()
            .all()
        )
        return tuple(_ibkr_execution_from_row(r) for r in rows)


class SqlAlchemyBehaviouralGuardrailSettingsRepository(_Base):
    """Task 134: per-account behavioural guardrail thresholds.

    ``get_or_default(ibkr_account_id, now)`` returns the persisted row
    if one exists, otherwise the brainstorm-locked defaults — without
    auto-inserting. The submission sweep calls this on every tick;
    the row only materialises when the user (later, via Task 138)
    explicitly saves a non-default setting.
    """

    def upsert(
        self, settings: BehaviouralGuardrailSettings
    ) -> BehaviouralGuardrailSettings:
        existing = self.get_for_account(settings.ibkr_account_id)
        payload = {
            "ibkr_account_id": settings.ibkr_account_id,
            "daily_max_approvals": settings.daily_max_approvals,
            "cooldown_seconds": settings.cooldown_seconds,
            "anti_revenge_window_hours": settings.anti_revenge_window_hours,
            "anti_revenge_loss_threshold_pct": (
                settings.anti_revenge_loss_threshold_pct
            ),
            "soft_drawdown_pct": settings.soft_drawdown_pct,
            "soft_drawdown_window_days": settings.soft_drawdown_window_days,
            "hard_drawdown_pct": settings.hard_drawdown_pct,
            "hard_drawdown_window_days": settings.hard_drawdown_window_days,
            "fomo_drift_pct": settings.fomo_drift_pct,
            "last_updated_at": settings.last_updated_at,
        }
        if existing is None:
            self._insert(behavioural_guardrail_settings, payload)
        else:
            self._connection.execute(
                behavioural_guardrail_settings.update()
                .where(
                    behavioural_guardrail_settings.c.ibkr_account_id
                    == settings.ibkr_account_id
                )
                .values(**payload)
            )
        return settings

    def get_for_account(
        self, ibkr_account_id: str
    ) -> BehaviouralGuardrailSettings | None:
        row = (
            self._connection.execute(
                select(behavioural_guardrail_settings).where(
                    behavioural_guardrail_settings.c.ibkr_account_id
                    == ibkr_account_id
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return _behavioural_guardrail_settings_from_row(row)

    def get_or_default(
        self, *, ibkr_account_id: str, now: datetime
    ) -> BehaviouralGuardrailSettings:
        existing = self.get_for_account(ibkr_account_id)
        if existing is not None:
            return existing
        return BehaviouralGuardrailSettings.default_for_account(
            ibkr_account_id=ibkr_account_id, last_updated_at=now
        )


class SqlAlchemyRuntimeConfigRepository(_Base):
    """The single ``runtime_config`` row (``config_id="default"``).

    Lets the operator edit the IBKR connection and the Claude AI explanation
    settings from the dashboard. ``upsert`` mirrors the guardrail-settings
    pattern (select existing, then insert or update); the caller commits.
    """

    def get(self) -> RuntimeConfigRecord | None:
        row = (
            self._connection.execute(
                select(runtime_config).where(
                    runtime_config.c.config_id == "default"
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return _runtime_config_from_row(row)

    def upsert(self, record: RuntimeConfigRecord) -> None:
        payload = {
            "config_id": record.config_id,
            "ibkr_enabled": record.ibkr_enabled,
            "ibkr_account_id": record.ibkr_account_id,
            "ibkr_host": record.ibkr_host,
            "ibkr_port": record.ibkr_port,
            "ibkr_client_id": record.ibkr_client_id,
            "ai_explanation_enabled": record.ai_explanation_enabled,
            "claude_ai_explanation_model": record.claude_ai_explanation_model,
            "claude_ai_budget_monthly_eur": record.claude_ai_budget_monthly_eur,
            "claude_ai_api_key": record.claude_ai_api_key,
            "updated_at": record.updated_at,
            "universe_scan_index_codes": record.universe_scan_index_codes,
            "default_buy_value_eur": record.default_buy_value_eur,
            "default_top_up_pct": record.default_top_up_pct,
            "default_reduce_pct": record.default_reduce_pct,
            "max_sector_pct": record.max_sector_pct,
            "cost_dominates_ratio": record.cost_dominates_ratio,
            "suggestion_valid_minutes": record.suggestion_valid_minutes,
            "scheduler_daily_briefing_cron": record.scheduler_daily_briefing_cron,
            "ibkr_sync_interval_minutes": record.ibkr_sync_interval_minutes,
            "forecast_history_lookback_days": record.forecast_history_lookback_days,
            "forecast_minimum_bars_required": record.forecast_minimum_bars_required,
            "daily_briefing_lookback_hours": record.daily_briefing_lookback_hours,
            "universe_scan_cache_ttl_hours": record.universe_scan_cache_ttl_hours,
            "sweep_interval_seconds": record.sweep_interval_seconds,
            "sweep_retry_max_attempts": record.sweep_retry_max_attempts,
            "sweep_retry_backoff_seconds": record.sweep_retry_backoff_seconds,
            "sweep_alert_after_consecutive_errors": (
                record.sweep_alert_after_consecutive_errors
            ),
            "eodhd_rate_limit_per_second": record.eodhd_rate_limit_per_second,
            "ensemble_weight_strategy": record.ensemble_weight_strategy,
            "gbm_drift_window_days": record.gbm_drift_window_days,
            "action_draft_approval_valid_minutes": (
                record.action_draft_approval_valid_minutes
            ),
            "ai_explanation_provider_code": record.ai_explanation_provider_code,
            "sharpe_strong_threshold": record.sharpe_strong_threshold,
            "sharpe_slight_threshold": record.sharpe_slight_threshold,
            "forecast_horizon_trading_days": record.forecast_horizon_trading_days,
            "forecast_ensemble_enabled": record.forecast_ensemble_enabled,
            "suggestions_risk_profile": record.suggestions_risk_profile,
            "universe_set": record.universe_set,
            "market_data_provider": record.market_data_provider,
            "market_data_sync_enabled": record.market_data_sync_enabled,
            "ibkr_market_data_enabled": record.ibkr_market_data_enabled,
            "ibkr_market_data_type": record.ibkr_market_data_type,
            "ibkr_paper_order_submission_enabled": (
                record.ibkr_paper_order_submission_enabled
            ),
            "submission_sweep_enabled": record.submission_sweep_enabled,
            "cancel_sweep_enabled": record.cancel_sweep_enabled,
            "morning_chain_after_pre_briefing": (
                record.morning_chain_after_pre_briefing
            ),
            "forecast_valid_minutes": record.forecast_valid_minutes,
            "decision_packages_valid_minutes": (
                record.decision_packages_valid_minutes
            ),
            "prediction_diary_inconclusive_tolerance_pct": (
                record.prediction_diary_inconclusive_tolerance_pct
            ),
            "gbm_regime_shift_enabled": record.gbm_regime_shift_enabled,
            "gbm_regime_shift_threshold_pct": (
                record.gbm_regime_shift_threshold_pct
            ),
        }
        existing = (
            self._connection.execute(
                select(runtime_config.c.config_id).where(
                    runtime_config.c.config_id == record.config_id
                )
            )
            .mappings()
            .first()
        )
        if existing is None:
            self._insert(runtime_config, payload)
        else:
            self._connection.execute(
                runtime_config.update()
                .where(runtime_config.c.config_id == record.config_id)
                .values(**payload)
            )


def _runtime_config_from_row(row: Any) -> RuntimeConfigRecord:
    return RuntimeConfigRecord(
        config_id=row["config_id"],
        ibkr_enabled=bool(row["ibkr_enabled"]),
        ibkr_account_id=row["ibkr_account_id"],
        ibkr_host=row["ibkr_host"],
        ibkr_port=(
            int(row["ibkr_port"]) if row["ibkr_port"] is not None else None
        ),
        ibkr_client_id=(
            int(row["ibkr_client_id"])
            if row["ibkr_client_id"] is not None
            else None
        ),
        ai_explanation_enabled=bool(row["ai_explanation_enabled"]),
        claude_ai_explanation_model=row["claude_ai_explanation_model"],
        claude_ai_budget_monthly_eur=_to_decimal(
            row["claude_ai_budget_monthly_eur"]
        ),
        claude_ai_api_key=row["claude_ai_api_key"],
        updated_at=row["updated_at"],
        universe_scan_index_codes=row.get("universe_scan_index_codes"),
        default_buy_value_eur=_to_decimal(row.get("default_buy_value_eur")),
        default_top_up_pct=_to_decimal(row.get("default_top_up_pct")),
        default_reduce_pct=_to_decimal(row.get("default_reduce_pct")),
        max_sector_pct=_to_decimal(row.get("max_sector_pct")),
        cost_dominates_ratio=_to_decimal(row.get("cost_dominates_ratio")),
        suggestion_valid_minutes=(
            int(row["suggestion_valid_minutes"])
            if row.get("suggestion_valid_minutes") is not None
            else None
        ),
        scheduler_daily_briefing_cron=row.get("scheduler_daily_briefing_cron"),
        ibkr_sync_interval_minutes=(
            int(row["ibkr_sync_interval_minutes"])
            if row.get("ibkr_sync_interval_minutes") is not None
            else None
        ),
        forecast_history_lookback_days=(
            int(row["forecast_history_lookback_days"])
            if row.get("forecast_history_lookback_days") is not None
            else None
        ),
        forecast_minimum_bars_required=(
            int(row["forecast_minimum_bars_required"])
            if row.get("forecast_minimum_bars_required") is not None
            else None
        ),
        daily_briefing_lookback_hours=(
            int(row["daily_briefing_lookback_hours"])
            if row.get("daily_briefing_lookback_hours") is not None
            else None
        ),
        universe_scan_cache_ttl_hours=(
            int(row["universe_scan_cache_ttl_hours"])
            if row.get("universe_scan_cache_ttl_hours") is not None
            else None
        ),
        sweep_interval_seconds=(
            int(row["sweep_interval_seconds"])
            if row.get("sweep_interval_seconds") is not None
            else None
        ),
        sweep_retry_max_attempts=(
            int(row["sweep_retry_max_attempts"])
            if row.get("sweep_retry_max_attempts") is not None
            else None
        ),
        sweep_retry_backoff_seconds=_to_decimal(
            row.get("sweep_retry_backoff_seconds")
        ),
        sweep_alert_after_consecutive_errors=(
            int(row["sweep_alert_after_consecutive_errors"])
            if row.get("sweep_alert_after_consecutive_errors") is not None
            else None
        ),
        eodhd_rate_limit_per_second=(
            int(row["eodhd_rate_limit_per_second"])
            if row.get("eodhd_rate_limit_per_second") is not None
            else None
        ),
        ensemble_weight_strategy=row.get("ensemble_weight_strategy"),
        gbm_drift_window_days=(
            int(row["gbm_drift_window_days"])
            if row.get("gbm_drift_window_days") is not None
            else None
        ),
        action_draft_approval_valid_minutes=(
            int(row["action_draft_approval_valid_minutes"])
            if row.get("action_draft_approval_valid_minutes") is not None
            else None
        ),
        ai_explanation_provider_code=row.get("ai_explanation_provider_code"),
        sharpe_strong_threshold=(
            Decimal(str(row["sharpe_strong_threshold"]))
            if row.get("sharpe_strong_threshold") is not None
            else None
        ),
        sharpe_slight_threshold=(
            Decimal(str(row["sharpe_slight_threshold"]))
            if row.get("sharpe_slight_threshold") is not None
            else None
        ),
        forecast_horizon_trading_days=(
            int(row["forecast_horizon_trading_days"])
            if row.get("forecast_horizon_trading_days") is not None
            else None
        ),
        forecast_ensemble_enabled=(
            bool(row["forecast_ensemble_enabled"])
            if row.get("forecast_ensemble_enabled") is not None
            else None
        ),
        suggestions_risk_profile=row.get("suggestions_risk_profile"),
        universe_set=row.get("universe_set"),
        market_data_provider=row.get("market_data_provider"),
        market_data_sync_enabled=(
            bool(row["market_data_sync_enabled"])
            if row.get("market_data_sync_enabled") is not None
            else None
        ),
        ibkr_market_data_enabled=(
            bool(row["ibkr_market_data_enabled"])
            if row.get("ibkr_market_data_enabled") is not None
            else None
        ),
        ibkr_market_data_type=row.get("ibkr_market_data_type"),
        ibkr_paper_order_submission_enabled=(
            bool(row["ibkr_paper_order_submission_enabled"])
            if row.get("ibkr_paper_order_submission_enabled") is not None
            else None
        ),
        submission_sweep_enabled=(
            bool(row["submission_sweep_enabled"])
            if row.get("submission_sweep_enabled") is not None
            else None
        ),
        cancel_sweep_enabled=(
            bool(row["cancel_sweep_enabled"])
            if row.get("cancel_sweep_enabled") is not None
            else None
        ),
        morning_chain_after_pre_briefing=(
            bool(row["morning_chain_after_pre_briefing"])
            if row.get("morning_chain_after_pre_briefing") is not None
            else None
        ),
        forecast_valid_minutes=(
            int(row["forecast_valid_minutes"])
            if row.get("forecast_valid_minutes") is not None
            else None
        ),
        decision_packages_valid_minutes=(
            int(row["decision_packages_valid_minutes"])
            if row.get("decision_packages_valid_minutes") is not None
            else None
        ),
        prediction_diary_inconclusive_tolerance_pct=(
            Decimal(str(row["prediction_diary_inconclusive_tolerance_pct"]))
            if row.get("prediction_diary_inconclusive_tolerance_pct") is not None
            else None
        ),
        gbm_regime_shift_enabled=(
            bool(row["gbm_regime_shift_enabled"])
            if row.get("gbm_regime_shift_enabled") is not None
            else None
        ),
        gbm_regime_shift_threshold_pct=(
            Decimal(str(row["gbm_regime_shift_threshold_pct"]))
            if row.get("gbm_regime_shift_threshold_pct") is not None
            else None
        ),
    )


def _ibkr_submission_audit_from_row(row: Any) -> IbkrSubmissionAuditEntry:
    contract_json = row["contract_json"] or {}
    order_json = row["order_json"] or {}
    return IbkrSubmissionAuditEntry(
        id=int(row["id"]) if row["id"] is not None else None,
        action_draft_id=row["action_draft_id"],
        submitted_at=row["submitted_at"],
        sent_to_account_id=row["sent_to_account_id"],
        sent_account_mode=row["sent_account_mode"],
        ibkr_perm_id=(
            int(row["ibkr_perm_id"])
            if row["ibkr_perm_id"] is not None
            else None
        ),
        ibkr_order_id=(
            int(row["ibkr_order_id"])
            if row["ibkr_order_id"] is not None
            else None
        ),
        contract_json=dict(contract_json),
        order_json=dict(order_json),
        gateway_session_id=row["gateway_session_id"],
        result=row["result"],
        error_class=row["error_class"],
        error_message_dutch=row["error_message_dutch"],
    )


def _ibkr_submission_lifecycle_from_row(
    row: Any,
) -> IbkrSubmissionLifecycleEntry:
    return IbkrSubmissionLifecycleEntry(
        id=int(row["id"]) if row["id"] is not None else None,
        action_draft_id=row["action_draft_id"],
        event_at=row["event_at"],
        ibkr_perm_id=int(row["ibkr_perm_id"]),
        event_type=row["event_type"],
        from_status=row["from_status"],
        to_status=row["to_status"],
        ibkr_raw_status=row["ibkr_raw_status"],
        fill_price_local=_to_decimal(row["fill_price_local"]),
        fill_quantity=_to_decimal(row["fill_quantity"]),
        commission=_to_decimal(row["commission"]),
        commission_currency=row["commission_currency"],
        raw_callback_json=dict(row["raw_callback_json"] or {}),
    )


def _ibkr_execution_from_row(row: Any) -> IbkrExecutionEntry:
    return IbkrExecutionEntry(
        id=int(row["id"]) if row["id"] is not None else None,
        ibkr_exec_id=row["ibkr_exec_id"],
        ibkr_perm_id=int(row["ibkr_perm_id"]),
        action_draft_id=row["action_draft_id"],
        account_id=row["account_id"],
        conid=row["conid"],
        side=row["side"],
        fill_price_local=_to_decimal(row["fill_price_local"]) or Decimal("0"),
        fill_quantity=_to_decimal(row["fill_quantity"]) or Decimal("0"),
        fill_time=row["fill_time"],
        commission=_to_decimal(row["commission"]) or Decimal("0"),
        commission_currency=row["commission_currency"],
        exchange=row["exchange"],
    )


def _behavioural_guardrail_settings_from_row(
    row: Any,
) -> BehaviouralGuardrailSettings:
    return BehaviouralGuardrailSettings(
        ibkr_account_id=row["ibkr_account_id"],
        daily_max_approvals=int(row["daily_max_approvals"]),
        cooldown_seconds=int(row["cooldown_seconds"]),
        anti_revenge_window_hours=int(row["anti_revenge_window_hours"]),
        anti_revenge_loss_threshold_pct=(
            _to_decimal(row["anti_revenge_loss_threshold_pct"])
            or Decimal("0")
        ),
        soft_drawdown_pct=(
            _to_decimal(row["soft_drawdown_pct"]) or Decimal("0")
        ),
        soft_drawdown_window_days=int(row["soft_drawdown_window_days"]),
        hard_drawdown_pct=(
            _to_decimal(row["hard_drawdown_pct"]) or Decimal("0")
        ),
        hard_drawdown_window_days=int(row["hard_drawdown_window_days"]),
        fomo_drift_pct=_to_decimal(row["fomo_drift_pct"]) or Decimal("0"),
        last_updated_at=row["last_updated_at"],
    )


def _ibkr_audit_bounded_limit(limit: int, *, upper: int = 50) -> int:
    """Used by the Task 134 IBKR audit repos to clamp ``limit=``."""

    if limit < 1:
        return 1
    if limit > upper:
        return upper
    return limit


# ---------------------------------------------------------------------------
# Task 135 — reconciliation repositories.
# ---------------------------------------------------------------------------


class SqlAlchemyReconciliationAuditRepository(_Base):
    """Task 135: append-only reconciler action log."""

    def append(
        self, entry: ReconciliationAuditEntry
    ) -> ReconciliationAuditEntry:
        result = self._connection.execute(
            reconciliation_audit.insert()
            .values(
                reconciliation_run_id=entry.reconciliation_run_id,
                action_draft_id=entry.action_draft_id,
                event_at=entry.event_at,
                pass_name=entry.pass_name,
                divergence_type=entry.divergence_type,
                before_status=entry.before_status,
                after_status=entry.after_status,
                ibkr_evidence_json=entry.ibkr_evidence_json,
                notes_dutch=entry.notes_dutch,
            )
            .returning(reconciliation_audit.c.id)
        )
        row = result.first()
        new_id = int(row[0]) if row is not None else None
        return ReconciliationAuditEntry(
            reconciliation_run_id=entry.reconciliation_run_id,
            action_draft_id=entry.action_draft_id,
            event_at=entry.event_at,
            pass_name=entry.pass_name,
            divergence_type=entry.divergence_type,
            before_status=entry.before_status,
            after_status=entry.after_status,
            ibkr_evidence_json=entry.ibkr_evidence_json,
            notes_dutch=entry.notes_dutch,
            id=new_id,
        )

    def list_for_account(
        self, *, account_id: str, limit: int = 50
    ) -> tuple[ReconciliationAuditEntry, ...]:
        # ``account_id`` doesn't live on the audit row directly — the
        # join is via ``action_drafts.ibkr_account_id``. For V1 we
        # filter at the action_drafts FK; rows with NULL draft id
        # (unmatched executions) are included if their run touched the
        # account.
        rows = (
            self._connection.execute(
                select(reconciliation_audit)
                .outerjoin(
                    action_drafts,
                    action_drafts.c.action_draft_id
                    == reconciliation_audit.c.action_draft_id,
                )
                .where(
                    (action_drafts.c.ibkr_account_id == account_id)
                    | (reconciliation_audit.c.action_draft_id.is_(None))
                )
                .order_by(reconciliation_audit.c.event_at.desc())
                .limit(_ibkr_audit_bounded_limit(limit, upper=200))
            )
            .mappings()
            .all()
        )
        return tuple(
            _reconciliation_audit_from_row(row) for row in rows
        )

    def list_for_run(
        self, reconciliation_run_id: str
    ) -> tuple[ReconciliationAuditEntry, ...]:
        rows = (
            self._connection.execute(
                select(reconciliation_audit)
                .where(
                    reconciliation_audit.c.reconciliation_run_id
                    == reconciliation_run_id
                )
                .order_by(reconciliation_audit.c.event_at)
            )
            .mappings()
            .all()
        )
        return tuple(
            _reconciliation_audit_from_row(row) for row in rows
        )

    def list_for_draft(
        self, action_draft_id: str
    ) -> tuple[ReconciliationAuditEntry, ...]:
        rows = (
            self._connection.execute(
                select(reconciliation_audit)
                .where(
                    reconciliation_audit.c.action_draft_id
                    == action_draft_id
                )
                .order_by(reconciliation_audit.c.event_at)
            )
            .mappings()
            .all()
        )
        return tuple(
            _reconciliation_audit_from_row(row) for row in rows
        )

    def count_drafts_healed_since(
        self, *, account_id: str, since: datetime
    ) -> int:
        """Healed drafts in the window — for the dashboard widget."""

        rows = (
            self._connection.execute(
                select(reconciliation_audit.c.action_draft_id)
                .outerjoin(
                    action_drafts,
                    action_drafts.c.action_draft_id
                    == reconciliation_audit.c.action_draft_id,
                )
                .where(action_drafts.c.ibkr_account_id == account_id)
                .where(reconciliation_audit.c.event_at >= since)
                .where(
                    reconciliation_audit.c.divergence_type.in_(
                        (
                            "missing_execution_applied",
                            "status_corrected_to_filled",
                            "status_corrected_to_cancelled",
                            "status_corrected_to_rejected",
                            "status_corrected_to_partially_filled",
                            "timeout_recovered_to_terminal",
                        )
                    )
                )
                .distinct()
            )
            .all()
        )
        return len(rows)


class SqlAlchemyUnmatchedExecutionAuditRepository(_Base):
    """Task 135: append-only IBKR-side executions with no matching draft."""

    def append(
        self, entry: UnmatchedExecutionAuditEntry
    ) -> UnmatchedExecutionAuditEntry:
        result = self._connection.execute(
            unmatched_execution_audit.insert()
            .values(
                event_at=entry.event_at,
                ibkr_perm_id=entry.ibkr_perm_id,
                ibkr_exec_id=entry.ibkr_exec_id,
                account_id=entry.account_id,
                conid=entry.conid,
                side=entry.side,
                fill_price_local=entry.fill_price_local,
                fill_quantity=entry.fill_quantity,
                fill_time=entry.fill_time,
                raw_execution_json=entry.raw_execution_json,
                resolution_status=entry.resolution_status,
            )
            .returning(unmatched_execution_audit.c.id)
        )
        row = result.first()
        new_id = int(row[0]) if row is not None else None
        return UnmatchedExecutionAuditEntry(
            event_at=entry.event_at,
            ibkr_perm_id=entry.ibkr_perm_id,
            ibkr_exec_id=entry.ibkr_exec_id,
            account_id=entry.account_id,
            conid=entry.conid,
            side=entry.side,
            fill_price_local=entry.fill_price_local,
            fill_quantity=entry.fill_quantity,
            fill_time=entry.fill_time,
            raw_execution_json=entry.raw_execution_json,
            resolution_status=entry.resolution_status,
            id=new_id,
        )

    def get_by_exec_id(
        self, ibkr_exec_id: str
    ) -> UnmatchedExecutionAuditEntry | None:
        row = (
            self._connection.execute(
                select(unmatched_execution_audit).where(
                    unmatched_execution_audit.c.ibkr_exec_id
                    == ibkr_exec_id
                )
            )
            .mappings()
            .first()
        )
        return (
            None if row is None
            else _unmatched_execution_from_row(row)
        )

    def list_unresolved_for_account(
        self, account_id: str
    ) -> tuple[UnmatchedExecutionAuditEntry, ...]:
        rows = (
            self._connection.execute(
                select(unmatched_execution_audit)
                .where(
                    unmatched_execution_audit.c.account_id == account_id
                )
                .where(
                    unmatched_execution_audit.c.resolution_status
                    == "unresolved"
                )
                .order_by(unmatched_execution_audit.c.fill_time.desc())
            )
            .mappings()
            .all()
        )
        return tuple(
            _unmatched_execution_from_row(row) for row in rows
        )


class SqlAlchemyManualReviewQueueRepository(_Base):
    """Task 135: manual-review queue with pending → resolved transitions.

    The transition is mutation-of-resolution_status only — the
    underlying draft is never re-statused by an acknowledgement.
    """

    def append(
        self, entry: ManualReviewQueueEntry
    ) -> ManualReviewQueueEntry:
        result = self._connection.execute(
            manual_review_queue.insert()
            .values(
                flagged_at=entry.flagged_at,
                action_draft_id=entry.action_draft_id,
                reason=entry.reason,
                details_dutch=entry.details_dutch,
                resolution_status=entry.resolution_status,
                resolved_at=entry.resolved_at,
                resolution_note=entry.resolution_note,
            )
            .returning(manual_review_queue.c.id)
        )
        row = result.first()
        new_id = int(row[0]) if row is not None else None
        return ManualReviewQueueEntry(
            flagged_at=entry.flagged_at,
            action_draft_id=entry.action_draft_id,
            reason=entry.reason,
            details_dutch=entry.details_dutch,
            resolution_status=entry.resolution_status,
            resolved_at=entry.resolved_at,
            resolution_note=entry.resolution_note,
            id=new_id,
        )

    def get_by_id(
        self, queue_id: int
    ) -> ManualReviewQueueEntry | None:
        row = (
            self._connection.execute(
                select(manual_review_queue).where(
                    manual_review_queue.c.id == queue_id
                )
            )
            .mappings()
            .first()
        )
        return None if row is None else _manual_review_from_row(row)

    def acknowledge(
        self,
        *,
        queue_id: int,
        resolved_at: datetime,
        note: str | None = None,
    ) -> ManualReviewQueueEntry:
        existing = self.get_by_id(queue_id)
        if existing is None:
            raise LookupError(
                f"manual_review_queue row {queue_id} niet gevonden."
            )
        # Idempotent: acknowledging an already-acknowledged row is a
        # no-op rather than an error so the UI's double-click is safe.
        if existing.resolution_status != "pending":
            return existing
        self._connection.execute(
            manual_review_queue.update()
            .where(manual_review_queue.c.id == queue_id)
            .values(
                resolution_status="acknowledged",
                resolved_at=resolved_at,
                resolution_note=note,
            )
        )
        updated = self.get_by_id(queue_id)
        assert updated is not None
        return updated

    def list_pending_for_account(
        self, account_id: str
    ) -> tuple[ManualReviewQueueEntry, ...]:
        rows = (
            self._connection.execute(
                select(manual_review_queue)
                .join(
                    action_drafts,
                    action_drafts.c.action_draft_id
                    == manual_review_queue.c.action_draft_id,
                )
                .where(action_drafts.c.ibkr_account_id == account_id)
                .where(
                    manual_review_queue.c.resolution_status == "pending"
                )
                .order_by(manual_review_queue.c.flagged_at.desc())
            )
            .mappings()
            .all()
        )
        return tuple(_manual_review_from_row(row) for row in rows)

    def count_pending_for_account(self, account_id: str) -> int:
        return len(self.list_pending_for_account(account_id))


class SqlAlchemyReconciliationRunAuditRepository(_Base):
    """Task 135: append + complete reconciler-tick records.

    The ``complete_run`` method updates the ``completed_at`` + count
    columns on an existing row — this is the only mutation allowed on
    the table, and it only flips a NULL ``completed_at`` to a value.
    """

    def append(
        self, entry: ReconciliationRunAuditEntry
    ) -> ReconciliationRunAuditEntry:
        result = self._connection.execute(
            reconciliation_run_audit.insert()
            .values(
                reconciliation_run_id=entry.reconciliation_run_id,
                started_at=entry.started_at,
                completed_at=entry.completed_at,
                account_id=entry.account_id,
                pass_a_orphaned_count=entry.pass_a_orphaned_count,
                pass_b_stale_count=entry.pass_b_stale_count,
                pass_c_timeout_count=entry.pass_c_timeout_count,
                divergences_found=entry.divergences_found,
                mode_detected=entry.mode_detected,
                error_details_json=entry.error_details_json,
            )
            .returning(reconciliation_run_audit.c.id)
        )
        row = result.first()
        new_id = int(row[0]) if row is not None else None
        return ReconciliationRunAuditEntry(
            reconciliation_run_id=entry.reconciliation_run_id,
            started_at=entry.started_at,
            completed_at=entry.completed_at,
            account_id=entry.account_id,
            pass_a_orphaned_count=entry.pass_a_orphaned_count,
            pass_b_stale_count=entry.pass_b_stale_count,
            pass_c_timeout_count=entry.pass_c_timeout_count,
            divergences_found=entry.divergences_found,
            mode_detected=entry.mode_detected,
            error_details_json=entry.error_details_json,
            id=new_id,
        )

    def complete_run(
        self,
        *,
        reconciliation_run_id: str,
        completed_at: datetime,
        pass_a_orphaned_count: int,
        pass_b_stale_count: int,
        pass_c_timeout_count: int,
        divergences_found: int,
        mode_detected: str,
        error_details_json: dict[str, object] | None = None,
    ) -> ReconciliationRunAuditEntry:
        self._connection.execute(
            reconciliation_run_audit.update()
            .where(
                reconciliation_run_audit.c.reconciliation_run_id
                == reconciliation_run_id
            )
            .values(
                completed_at=completed_at,
                pass_a_orphaned_count=pass_a_orphaned_count,
                pass_b_stale_count=pass_b_stale_count,
                pass_c_timeout_count=pass_c_timeout_count,
                divergences_found=divergences_found,
                mode_detected=mode_detected,
                error_details_json=error_details_json,
            )
        )
        row = (
            self._connection.execute(
                select(reconciliation_run_audit).where(
                    reconciliation_run_audit.c.reconciliation_run_id
                    == reconciliation_run_id
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise LookupError(
                f"reconciliation_run {reconciliation_run_id!r} not found."
            )
        return _reconciliation_run_audit_from_row(row)

    def get_latest_for_account(
        self, account_id: str
    ) -> ReconciliationRunAuditEntry | None:
        row = (
            self._connection.execute(
                select(reconciliation_run_audit)
                .where(reconciliation_run_audit.c.account_id == account_id)
                .order_by(reconciliation_run_audit.c.started_at.desc())
                .limit(1)
            )
            .mappings()
            .first()
        )
        return (
            None
            if row is None
            else _reconciliation_run_audit_from_row(row)
        )

    def list_for_account(
        self, *, account_id: str, limit: int = 50
    ) -> tuple[ReconciliationRunAuditEntry, ...]:
        rows = (
            self._connection.execute(
                select(reconciliation_run_audit)
                .where(reconciliation_run_audit.c.account_id == account_id)
                .order_by(reconciliation_run_audit.c.started_at.desc())
                .limit(_ibkr_audit_bounded_limit(limit, upper=200))
            )
            .mappings()
            .all()
        )
        return tuple(
            _reconciliation_run_audit_from_row(row) for row in rows
        )


def _reconciliation_audit_from_row(row: Any) -> ReconciliationAuditEntry:
    return ReconciliationAuditEntry(
        id=int(row["id"]) if row["id"] is not None else None,
        reconciliation_run_id=row["reconciliation_run_id"],
        action_draft_id=row["action_draft_id"],
        event_at=row["event_at"],
        pass_name=row["pass_name"],
        divergence_type=row["divergence_type"],
        before_status=row["before_status"],
        after_status=row["after_status"],
        ibkr_evidence_json=dict(row["ibkr_evidence_json"] or {}),
        notes_dutch=row["notes_dutch"],
    )


def _unmatched_execution_from_row(row: Any) -> UnmatchedExecutionAuditEntry:
    return UnmatchedExecutionAuditEntry(
        id=int(row["id"]) if row["id"] is not None else None,
        event_at=row["event_at"],
        ibkr_perm_id=int(row["ibkr_perm_id"]),
        ibkr_exec_id=row["ibkr_exec_id"],
        account_id=row["account_id"],
        conid=row["conid"],
        side=row["side"],
        fill_price_local=(
            _to_decimal(row["fill_price_local"]) or Decimal("0")
        ),
        fill_quantity=(
            _to_decimal(row["fill_quantity"]) or Decimal("0")
        ),
        fill_time=row["fill_time"],
        raw_execution_json=dict(row["raw_execution_json"] or {}),
        resolution_status=row["resolution_status"],
    )


def _manual_review_from_row(row: Any) -> ManualReviewQueueEntry:
    return ManualReviewQueueEntry(
        id=int(row["id"]) if row["id"] is not None else None,
        flagged_at=row["flagged_at"],
        action_draft_id=row["action_draft_id"],
        reason=row["reason"],
        details_dutch=row["details_dutch"],
        resolution_status=row["resolution_status"],
        resolved_at=row["resolved_at"],
        resolution_note=row["resolution_note"],
    )


def _reconciliation_run_audit_from_row(
    row: Any,
) -> ReconciliationRunAuditEntry:
    return ReconciliationRunAuditEntry(
        id=int(row["id"]) if row["id"] is not None else None,
        reconciliation_run_id=row["reconciliation_run_id"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        account_id=row["account_id"],
        pass_a_orphaned_count=int(row["pass_a_orphaned_count"]),
        pass_b_stale_count=int(row["pass_b_stale_count"]),
        pass_c_timeout_count=int(row["pass_c_timeout_count"]),
        divergences_found=int(row["divergences_found"]),
        mode_detected=row["mode_detected"],
        error_details_json=(
            dict(row["error_details_json"])
            if row["error_details_json"] is not None
            else None
        ),
    )
