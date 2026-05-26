# `packages/storage` and the Alembic chain

**Phase:** 1a (reality components)
**Task:** T-003
**Scope:** all eight Python modules in `packages/storage/src/ai_trading_agent_storage/` (≈15.6k lines) plus an overview of the 53-migration Alembic chain at `packages/storage/alembic/versions/`. The package is the persistence layer: SQLAlchemy Core tables, frozen-dataclass record contracts, gate-checked SQL repositories, and the migration-readiness chain that authorises writes.

This file is descriptive. Every claim cites `path/to/file.py:NNN` with short excerpts on non-trivial claims. No verdicts, no gaps, no fix proposals.

## Modules covered

- `__init__.py` — public-facade re-exports (≈250 names).
- `metadata.py` — single shared `MetaData()` carrying every table (≈60 tables).
- `settings.py` — `DatabaseConnectionSettings` + URL redaction.
- `alembic_helpers.py` — `get_target_metadata` for the Alembic env.
- `connection_provider.py` — `StorageConnectionProvider` (engine per call, readiness-gated writes).
- `migration_readiness.py` — expected-revisions inventory + the online readiness gate.
- `repository_contracts.py` — frozen-dataclass records, Protocol interfaces, locked vocabularies.
- `sql_repositories.py` — gate-checked SQLAlchemy-Core repositories.

Intent references: `docs/storage-architecture.md`, ADR `docs/adr/0001-database-and-migrations.md`.

## `__init__.py` — public facade

**Path:** `packages/storage/src/ai_trading_agent_storage/__init__.py` (~523 lines)

A pure facade. Imports every public symbol from the seven concrete modules and re-exports them through an `__all__` list of ≈250 names. Surface clusters by domain (broker, IBKR sync, market data, research, prediction diary, action drafts, decision packages, reconciliation), with the readiness types (`StorageConnectionProvider`, `CheckedStorageConnection`, `MigrationReadinessStatus`, `MigrationRevisionInfo`, `MigrationInventory`, `MigrationReadinessReport`) and the explicit error types (`ActionDraftStateTransitionError`, `StoragePersistenceBlockedError`, `ColdStartAlreadySeededError`, `BootstrapInsufficientHistoryError`, `EodhdNotConfiguredError`) sitting at the top of the public API.

## `metadata.py` — the schema

**Path:** `packages/storage/src/ai_trading_agent_storage/metadata.py` (~3116 lines)

Single `sqlalchemy.MetaData()` instance at `metadata.py:33` carrying every persisted table. Module constant `MONEY_NUMERIC = Numeric(precision=20, scale=6)` (`:31`) is the canonical Decimal precision for cash and quantity columns; finer per-table precisions exist where needed (e.g. `Numeric(20, 8)` for FX and forecast log-returns at `:2213, :2249-2307`; `Numeric(20, 10)` for log-return percentiles at `:2263-2265`; `Numeric(8, 6)` / `Numeric(10, 6)` for probabilities; `Numeric(10, 8)` for volatility).

### Table inventory (≈60 tables grouped by domain)

- **Paper foundation:** `paper_portfolio_setups` (`:35-83`, hard-locked CHECK on `base_currency = 'eur'` plus `paper_only IS TRUE`, `real_money_used IS FALSE`), `paper_cash_accounts` (`:85-102`), `audit_events` (hash-chain via `previous_hash`/`event_hash` at `:104-124`).
- **System events + trading settings:** `system_events` (`:127-163`), `trading_settings` (`:165-185`, JSON `allowed_universe_json` + `user_strategy_json` + `version` integer).
- **Broker / IBKR sync:** `broker_accounts` (`:187-219`, hard-locked CHECK on `broker_system = 'ibkr'` + `live_trading_allowed IS FALSE`), `broker_sync_runs` (`:221-252`), per-domain snapshots `broker_position_snapshots` / `broker_cash_snapshots` / `broker_execution_snapshots` / `broker_commission_snapshots` (`:255-421`), reconciliation tables `broker_reconciliation_reports` + `_differences` (`:987-1054`), `external_broker_activities` (`:1056-1081`).
- **Research:** `research_sources` (`:423-447`) and ≈15 follow-up tables for uploaded-file / URL / note metadata, document sets, classifications, source-to-asset links, processing status, prompt-injection scans (`:602-618` — `blocks_suggestions` defaults to `sa_true()`, `safe_to_use_*` defaults to `sa_false()`), credibility assessments, evidence items, ledger links, gate outcomes, conflict findings, extracted texts.
- **Asset identity:** `asset_master_records` (`:884-910`, `canonical_symbol` UNIQUE), `asset_identifier_aliases`, `asset_listings` (`:925-957`, six `safe_to_use_*` / `blocks_*` booleans defaulted to false/true).
- **Watchlist + market data:** `watchlist_items` (`:820-853`, locked `status IN ('active','archived')` + `source IN ('manual','cold_start_seed')`), `market_data_snapshots`, `market_data_latest_snapshots`, `market_data_bars` (`:1496-1526`, UNIQUE `(ibkr_conid, interval_code, bar_date, provider_code)`), `market_data_eod_snapshots` (`:2169-2198`, UNIQUE `(ibkr_conid, as_of_date, provider)` + locked provider enum), `fx_rate_snapshots`, `fx_rates` (`:2206-2219`, composite PK `(base, quote, as_of_date, provider)`).
- **IBKR snapshot / connection audit:** `ibkr_sync_runs` (`:1278-1311`), `ibkr_account_cash_snapshots`, `ibkr_position_snapshots`, `ibkr_open_order_snapshots`, `ibkr_execution_snapshots`, per-account indexes from Task 126 (`:1414-1433`), `ibkr_connection_audit` (`:1440-1472`, locked event-type CHECK).
- **Request / provider / freshness skeleton:** `request_logs` (≈60 cols, `:1111-1173`, all three `safe_for_*` default `sa_false()`), `provider_sources`, `freshness_audit_records`.
- **Forecast / suggestion / decision / action chain:** `asset_forecasts` (`:2013-2050`), `asset_suggestions`, `asset_decision_packages` (`:1919-1980`, `content_hash` UNIQUE), `asset_action_drafts` (`:1529-1580`), submissions, events, `prediction_diary_entries`, `decision_package_explanations` (`:1673-1701`, UNIQUE `(decision_package_id, decision_package_content_hash)`), `explanation_evidence_ledger`, `daily_briefings` (UNIQUE on `briefing_date`), `briefing_alerts`, `scheduler_runs`, `universe_scan_runs`, `predictor_backtest_runs`, `prediction_diary_predictor_contributions`, `claude_ai_budget_usage`, `action_draft_order_conditions`, `asset_fundamentals_snapshots`.
- **Task 127–135 V1.1 audit + state chain:** `scheduled_run_audit` (`:2054-2086`), `scheduler_state`, `cold_start_seed_audit` (UNIQUE `ibkr_account_id`), `watchlist_confirmation_state` + `_audit`, `provider_call_audit`, **`forecasts`** (`:2249-2307`, UNIQUE `(conid, generated_at)`, locked CHECKs on method/label/confidence), `calibration_diary`, **`decision_packages`** (`:2347-2492`, per-asset hash chain; locked CHECK refuses `suggested_action_label='Geblokkeerd'`; hard-False `safe_for_*` enforced by CHECK at `:2470-2477`), **`action_drafts`** (`:2502-2632`, 16-status locked enum at `:2603-2610`, FK to `decision_packages`, hard-False `safe_for_submission` CHECK at `:2628-2631`), `action_draft_audit`, `ibkr_submission_audit`, `ibkr_submission_lifecycle`, `ibkr_executions` (UNIQUE `ibkr_exec_id`), `behavioural_guardrail_settings` (`:2830-2913`, brainstorm-locked defaults: `daily_max_approvals=5`, `cooldown_seconds=60`, etc.), `reconciliation_audit`, `unmatched_execution_audit`, `manual_review_queue`, `reconciliation_run_audit`.

### Notable implementation choices

- **All money-like columns use `Numeric` (Decimal).** Never `Float`.
- **"Safety boolean" pattern.** Tables that *might* feed broker actions carry `safe_for_action_drafts`, `safe_for_orders`, `safe_for_broker_submission`, `safe_for_submission`, `safe_for_self_learning`, `safe_for_model_retraining`, `safe_for_analysis`, `safe_for_suggestions`. They default to `false` via `server_default=sa_false()` or string `"0"` / `"false"`; for the newest tables (`decision_packages`, `action_drafts`) `CheckConstraint` *enforces* `= FALSE` at the row level (`:2470-2477`, `:2628-2631`). Mirrored at the Python dataclass layer (defense in depth).
- **Locked enum vocabularies live in CHECK constraints** (e.g. `action_drafts.status` 16-value enum at `:2603-2610`; `decision_packages.suggested_action_label` explicitly excludes `"Geblokkeerd"` at `:2453-2457`).
- **All timestamps `DateTime(timezone=True)`.**
- **Foreign keys are inlined** `ForeignKey("table.column")` without explicit `name=`; Alembic/SQLAlchemy auto-name them.
- **Hash-chain columns:** `audit_events` (`previous_hash` / `event_hash`), `decision_packages` (`previous_package_hash` / `audit_trail_hash`), `action_drafts` (`previous_draft_hash` / `audit_trail_hash`). The chain pattern: one row writes the previous row's hash + a new hash of canonical JSON of the current row's audit-relevant fields.

```python
# metadata.py:2603-2632 — locked enum + hard-False CHECK on action_drafts
CheckConstraint(
    "status IN ('proposed', 'edited', 'user_approved', "
    "'dismissed', 'deleted', 'superseded', 'submitted', "
    ...
    "'awaiting_reply_timeout', 'requires_manual_review')",
    name="ck_action_drafts_status",
),
...
CheckConstraint(
    "safe_for_submission = FALSE",
    name="ck_action_drafts_safe_for_submission_false",
),
```

## `settings.py` — DB connection settings + URL redaction

**Path:** `packages/storage/src/ai_trading_agent_storage/settings.py` (61 lines)

### Public surface

- `DatabaseConnectionSettings` frozen dataclass (`:7-14`) — `database_url: str | None`, `database_url_configured: bool`, `safe_database_label: str`, `explanation_nl: str`.
- `redact_database_url(database_url) -> str` (`:31-45`) — `urllib.parse.urlsplit`, replaces the netloc with `username:***@host:port`; returns `"Niet ingesteld"` when missing, `"Ongeldige database-url"` when no scheme.
- `build_database_connection_settings(database_url) -> DatabaseConnectionSettings` (`:48-61`) — pure factory; Dutch explanation `"Databasekoppeling is voorbereid voor latere migraties, maar de app-runtime gebruikt nog geen actieve databaseverbinding."`

### Collaborators

None — pure stdlib.

### Notable choices

Never logs or stores the raw URL externally; the redacted label is what the rest of the app surfaces. Username is preserved (debug aid); password is always masked to `***`.

## `alembic_helpers.py` — env wiring shim

**Path:** `packages/storage/src/ai_trading_agent_storage/alembic_helpers.py` (18 lines)

### Public surface

- `get_target_metadata() -> MetaData` (`:8-11`) — returns the shared `metadata` from `metadata.py`.
- `is_migration_skeleton_ready() -> bool` (`:14-18`) — sanity check that the import returned a `MetaData` instance.

Used by `packages/storage/alembic/env.py:8,15` as `target_metadata=` for both offline and online runs.

## `connection_provider.py` — engine per call, write gate

**Path:** `packages/storage/src/ai_trading_agent_storage/connection_provider.py` (72 lines)

### Public surface

- `StorageConnectionError(RuntimeError)` and `StorageConnectionNotReadyError(StorageConnectionError)` (`:21-26`).
- `CheckedStorageConnection` frozen dataclass (`:29-32`) — wraps a live SQLAlchemy `Connection` with the `MigrationReadinessReport` that authorised it.
- `StorageConnectionProvider` frozen dataclass holding `settings: DatabaseConnectionSettings` (`:35-71`), with one context-manager method `checked_connection(*, require_writable: bool)`.

### Collaborators

`sqlalchemy.create_engine`, `migration_readiness.check_online_migration_readiness`, `migration_readiness.migration_readiness_is_safe_to_write`, `settings.DatabaseConnectionSettings`.

### Notable choices

This is the only place in `packages/storage/` that *opens* a real DB engine. The context manager: creates the engine per call, runs the online readiness check on the live connection, gates writes on the report (`require_writable=True` raises `StorageConnectionNotReadyError` if `migration_readiness_is_safe_to_write` is false), and disposes the engine in `finally`. Engines and connections are never cached.

```python
# connection_provider.py:42-62
@contextmanager
def checked_connection(self, *, require_writable: bool) -> Iterator[CheckedStorageConnection]:
    database_url = self.settings.database_url
    if database_url is None or database_url.strip() == "":
        raise StorageConnectionError(
            "Database-url ontbreekt; expliciete runtimeverbinding kan niet worden geopend."
        )
    engine: Engine | None = None
    connection: Connection | None = None
    try:
        engine = create_engine(database_url)
        connection = engine.connect()
        readiness = check_online_migration_readiness(connection)
        if require_writable and not migration_readiness_is_safe_to_write(readiness):
            raise StorageConnectionNotReadyError(...)
        yield CheckedStorageConnection(connection=connection, readiness=readiness)
```

## `migration_readiness.py` — the chain gate

**Path:** `packages/storage/src/ai_trading_agent_storage/migration_readiness.py` (847 lines)

### Public surface

- `MigrationReadinessStatus(StrEnum)` (`:17-26`) — `NOT_CONNECTED`, `NOT_CHECKED`, `OFFLINE_INVENTORY_VALID`, `OFFLINE_INVENTORY_INVALID`, `MIGRATIONS_CURRENT`, `MIGRATIONS_BEHIND`, `MIGRATIONS_UNKNOWN`, `BLOCKED`, `FAILED`.
- Frozen dataclasses: `MigrationRevisionInfo(revision_id, previous_revision_id, filename, label_nl, description_nl)` (`:30-35`), `MigrationInventory` (`:39-44`), `MigrationReadinessReport` (`:48-57`).
- `_EXPECTED_MIGRATION_REVISIONS` (`:60-628`) — source-of-truth tuple listing all **53 expected revisions**, each entry carrying `revision_id`, `previous_revision_id`, `filename`, Dutch `label_nl`, Dutch `description_nl`.
- `expected_migration_revisions()` (`:631`).
- `build_expected_migration_inventory()` (`:646-659`).
- `build_database_not_connected_readiness_report()` (`:662-677`).
- `check_offline_migration_inventory()` (`:680-718`) — walks `Path(__file__).resolve().parents[2] / "alembic" / "versions"` and verifies each expected filename exists on disk.
- `migration_readiness_is_safe_to_write(report)` (`:721-722`) — equivalent to `report.persistence_allowed and not report.blocks_runtime_writes`.
- `read_database_alembic_revision(connection)` (`:725-733`) — `SELECT version_num FROM alembic_version`; raises `ValueError` if more than one row.
- `check_online_migration_readiness(connection)` (`:736-827`) — **the gating function**. Reads the DB revision and matches against `inventory.latest_expected_revision_id`. Returns one of `MIGRATIONS_CURRENT` (`persistence_allowed=True`), `MIGRATIONS_BEHIND`, `MIGRATIONS_UNKNOWN`, or `FAILED`. Only `MIGRATIONS_CURRENT` allows writes.
- `online_migration_readiness_interfaces_are_defined()` / `migration_readiness_interfaces_are_defined()` introspection helpers (`:830-846`).

### Collaborators

`sqlalchemy.text`, `sqlalchemy.engine.Connection`, stdlib `Path` for filesystem inventory check.

### Notable choices

- **`_is_expected_chain_valid`** (`:635-643`) verifies the `previous_revision_id` linked list is contiguous from `None` through the chain — chain integrity is structural, not by Alembic invocation.
- **Revision-id naming inconsistency.** `0001`–`0014` use bare numeric ids (`"0001"`, …, `"0014"`); `0015` onwards use slug suffixes (e.g. `"0015_research_source_evidence_ledger_links"`). The chain still validates because each `previous_revision_id` is exactly the prior entry's `revision_id`.
- Dutch is the user-facing language throughout (`label_nl`, `description_nl`, `explanation_nl`).

```python
# migration_readiness.py:784-798
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
        ...
    )
```

## `repository_contracts.py` — records, protocols, locked vocab

**Path:** `packages/storage/src/ai_trading_agent_storage/repository_contracts.py` (≈4353 lines)

Module banner: "interface-only protocols and DTO/result contracts. It intentionally does not open sessions, read environment variables, or connect to a database" (`:1-5`).

### Public surface — generic results

- `StorageWriteResult` (`:44-50`) — `accepted`, `record_id`, `table_name`, `audit_required`, `explanation_nl`.
- `StorageReadResult[T]` (`:53-58`) — generic with `found`, `record`, `table_name`, `explanation_nl`.
- `StorageListResult[T]` (`:61-65`) — `records: tuple[T, ...]`, `table_name`, `explanation_nl`.
- `RepositoryHealthStatus` (`:68-74`) — `available`, `connected`, `migrations_current`, `read_only`, `explanation_nl`.
- `build_repository_health_not_connected()` (`:1810-1817`); `repository_interfaces_are_defined()` (`:1820-1858`).

### Public surface — validator helpers (module-private)

`_require_non_empty(value, field_name)` (`:15-18`), `_require_positive_int` (`:21-24`), `_require_non_negative_int` (`:27-30`), `_require_ordered_datetimes(earlier, later, …)` (`:33-37`), `_normalize_value` (`:40-41`). Used in nearly every dataclass `__post_init__`.

### Public surface — record dataclasses (80+)

Every persisted table has a paired frozen dataclass (suffix `Record` or `Entry`). Key examples by domain:

- **Broker:** `BrokerAccountRecord` / `BrokerSyncRunRecord` / `BrokerPositionSnapshotRecord` / `BrokerCashSnapshotRecord` / `BrokerExecutionSnapshotRecord` / `BrokerCommissionSnapshotRecord` (`:77-185`).
- **IBKR sync:** `IbkrSyncRunRecord`, `IbkrAccountCashSnapshotRecord`, `IbkrPositionSnapshotRecord`, `IbkrOpenOrderSnapshotRecord`, `IbkrExecutionSnapshotRecord`, `IbkrConnectionAuditRecord` (`:201-358`).
- **Scheduler:** `ScheduledRunAuditEntry`, `SchedulerStateEntry` (`:380-441`).
- **Reconciliation:** `BrokerReconciliationReportRecord`, `BrokerReconciliationDifferenceRecord`, `ExternalBrokerActivityRecord` (`:462-513`).
- **Research (~15 records):** `EvidenceItemRecord`, `ResearchSourceRecord`, `ResearchUploadedFileMetadataRecord`, `ResearchUrlMetadataRecord`, `ResearchUserNoteRecord`, `ResearchDocumentSetRecord` + member, `ResearchDocumentClassificationRecord`, `ResearchSourceAssetLinkRecord`, `ResearchSourceProcessingStatusRecord`, `ResearchSourcePromptInjectionScanRecord`, `ResearchSourceCredibilityAssessmentRecord`, `ResearchSourceEvidenceItemRecord`, `ResearchGateOutcomeRecord`, `ResearchSourceConflictFindingRecord` (`:516-1131`).
- **Asset identity:** `AssetMasterRecord`, `AssetIdentifierAliasRecord`, `AssetListingRecord`, `SourceToAssetLinkRecord` (`:1133-1308`).
- **System / paper / settings:** `SystemEventRecord` + `CreateSystemEventRequest` + protocol (`:1252-1352`); `PaperPortfolioSetupRecord` + `CreatePaperPortfolioSetupRequest` + protocol (`:1364-1441`); `TradingSettingsRecord` + `SaveTradingSettingsRequest` + protocol (`:1394-1426`).
- **Market data:** `MarketDataSnapshotRecord`, `MarketDataLatestSnapshotRecord`, `RequestLogRecord`, `ProviderSourceRecord`, `FreshnessAuditRecord` (`:1504-1675`); `MarketDataBarRecord` (`:1861-1895`).
- **Forecast / suggestion / decision / draft:** `AssetForecastRecord` (`:1898-1956`), `AssetSuggestionRecord` (`:1959-2011`), `AssetDecisionPackageRecord` (`:2014-2131`, long docstring explaining the content-hash contract), `AssetActionDraftRecord` (`:2134-2276`, per-order-type invariants via `_enforce_order_type_invariants` at `:2300-2400`), `ActionDraftOrderConditionRecord` (`:2403-2474`), submissions, events, `PredictionDiaryEntryRecord`, `DecisionPackageExplanationRecord`, `ExplanationEvidenceLedgerRecord`, `DailyBriefingRecord`, `BriefingAlertRecord`, `UniverseScanRunRecord`, `AssetFundamentalsSnapshotRecord`, `SchedulerRunRecord`, `PredictorBacktestRunRecord`, `PredictionDiaryPredictorContributionRecord`, `ClaudeAiBudgetUsageRecord`.
- **Task 128 cold-start:** `ColdStartSeedAuditEntry`, `WatchlistConfirmationStateRecord`, `WatchlistConfirmationAuditEntry`, `WatchlistItemSeedRecord`, `ColdStartAlreadySeededError` (`:3146-3273`).
- **Task 129 EOD:** `MarketDataEodSnapshotEntry`, `FxRateRecord`, `ProviderCallAuditEntry`, `EodhdNotConfiguredError` (`:3275-3393`).
- **Task 130 forecast:** `ForecastEntry`, `CalibrationDiaryEntry`, `BootstrapInsufficientHistoryError` (`:3395-3530`, `:4352-4353`).
- **Task 132 Decision Package:** `GateOutcome` (`:3542-3560`), `EvidenceReference` (`:3563-3580`), `DecisionPackageEntry` (`:3583-3702` — the big one, with hash chain).
- **Task 133 Action Draft V2:** `ActionDraftEntry` (`:3743-3862`), `ActionDraftAuditEntry` (`:3865-3895`).
- **Task 134 IBKR submission lifecycle:** `IbkrSubmissionAuditEntry`, `IbkrSubmissionLifecycleEntry`, `IbkrExecutionEntry`, `BehaviouralGuardrailSettings` (`:3950-4152`; `default_for_account` classmethod returns brainstorm-locked defaults).
- **Task 135 reconciliation:** `ReconciliationAuditEntry`, `UnmatchedExecutionAuditEntry`, `ManualReviewQueueEntry`, `ReconciliationRunAuditEntry` (`:4190-4349`).

### Public surface — Protocol interfaces

`SystemEventRepositoryProtocol`, `BrokerAccountRepository`, `TradingSettingsRepositoryProtocol`, `PaperPortfolioSetupRepositoryProtocol`, `BrokerSyncRunRepository`, `BrokerSnapshotRepository`, `MarketDataSnapshotRepository`, `FxRateSnapshotRepository`, `BrokerReconciliationRepository`, `ExternalBrokerActivityRepository`, `RequestAuditRepository`, `BrokerStorageUnitOfWork`. Each uses `StorageWriteResult` / `StorageReadResult[T]` / `StorageListResult[T]` for return types.

### Locked vocabularies (module-private `frozenset`s)

- `_LOCKED_IBKR_ACCOUNT_MODES = {"paper", "live", "unknown"}` (`:187`).
- `_LOCKED_IBKR_CONNECTION_EVENT_TYPES` (`:188-198`).
- `_LOCKED_SCHEDULED_RUN_TYPES`, `_LOCKED_SCHEDULED_MODE_DETECTED`, `_LOCKED_SCHEDULED_OUTCOMES` (`:362-377`).
- `LOCKED_ORDER_TYPES = {"LMT","MKT","STP","STP_LMT","TRAIL","TRAIL_LMT","BRACKET","CONDITIONAL"}` (`:2279-2281`) — publicly exported.
- `LOCKED_TIF_SET = {"DAY","GTC","OPG","IOC"}` (`:2284`).
- `LOCKED_CONDITION_KINDS`, `LOCKED_CONDITION_COMPARATORS`, `LOCKED_CONDITION_CONJUNCTIONS`, `LOCKED_CONDITIONAL_PARENT_TYPES` (`:2287-2297`).
- `_LOCKED_WATCHLIST_*` (`:3138-3143`), `_LOCKED_MARKET_DATA_PROVIDERS`, `_LOCKED_FX_RATE_PROVIDERS`, `_LOCKED_FORECAST_METHODS`, `_LOCKED_FORECAST_LABELS`, `_LOCKED_FORECAST_CONFIDENCE`, `_LOCKED_HIT_STATUSES`, `_LOCKED_FORECAST_BLOCK_REASONS`, `_LOCKED_FRESHNESS_STATES`, `_LOCKED_DECISION_PACKAGE_LABELS`, `_LOCKED_ACTION_DRAFT_*`, `_LOCKED_SUBMISSION_*`, `_LOCKED_RECONCILIATION_*`, `_LOCKED_MANUAL_REVIEW_*`.

### Notable implementation choices

- Every record is `@dataclass(frozen=True)` — pure value objects.
- `Decimal` for all money / quantity / probability fields end-to-end. Floats are rejected.
- `__post_init__` validators run cross-field invariants: range checks (`prob_positive in [0,1]`), ordered timestamps, enum membership against locked frozensets, "safety boolean must remain False" guards.
- **Defense-in-depth safety booleans**: e.g. `AssetSuggestionRecord.__post_init__` raises `ValueError` if `safe_for_action_drafts` is True (`:2003-2011`), mirroring the DB CHECK + migration `server_default`. Comments on `DecisionPackageEntry.__post_init__` (`:3687-3696`) call this out explicitly.
- Per-order-type invariants in `_enforce_order_type_invariants` (`:2300-2400`) — e.g. `BRACKET BUY` requires take-profit price > limit_price; structurally validated on construction.

```python
# repository_contracts.py:3667-3699 — locked vocabulary + invariant
if self.suggested_action_label not in _LOCKED_DECISION_PACKAGE_LABELS:
    raise ValueError(
        f"suggested_action_label {self.suggested_action_label!r} "
        f"not in {sorted(_LOCKED_DECISION_PACKAGE_LABELS)} "
        "(Geblokkeerd forecasts get no Decision Package)"
    )
...
if self.safe_for_action_drafts:
    raise ValueError(
        "safe_for_action_drafts must be False until the "
        "Action Center workflow ships (Task 132 product lock §1)"
    )
```

## `sql_repositories.py` — gate-checked Core repositories

**Path:** `packages/storage/src/ai_trading_agent_storage/sql_repositories.py` (≈6617 lines)

Concrete SQLAlchemy-Core implementations of the Protocol contracts in `repository_contracts.py`. Uses Core (not ORM). Every repository takes a live `Connection` plus a `MigrationReadinessReport` in its constructor.

### Public surface — gate function

- `StoragePersistenceBlockedError(RuntimeError)` (`:202-203`).
- `ensure_persistence_allowed(report)` (`:206-210`) — raises unless `migration_readiness_is_safe_to_write(report)`.

### Public surface — base + helpers

- `_Base` (`:327-334`) — base class for every repository. Constructor stores `connection` + `readiness_report`. The `_insert(table, values)` helper runs `ensure_persistence_allowed` then `connection.execute(table.insert().values(**values))`.
- Conversion helpers `_to_decimal`, `_json_tuple_or_none`, `_json_list_or_none` (`:213-228`).
- Typed select helpers `_read_one_by_column`, `_read_many_by_column` (`:307-324`).
- `_bounded_limit(limit)` (`:1971-1974`) clamps any `limit` to `[1, 500]`.

### Public surface — ≈53 repository classes

One per persistence-bearing table or audit topic. Names span `sql_repositories.py:337-6425`. Catalogue by domain:

- **Broker:** `SqlAlchemyBrokerAccountRepository` (`:337-376`), `SqlAlchemyBrokerSyncRunRepository`, `SqlAlchemyBrokerSnapshotRepository`, `SqlAlchemyBrokerReconciliationRepository`, `SqlAlchemyExternalBrokerActivityRepository`.
- **Unit of work:** `SqlAlchemyBrokerStorageUnitOfWork` (`:1798-1827`) — composite exposing the broker repos as properties; `commit()` / `rollback()` are no-ops (callers manage the outer transaction; comment `:1823-1827`).
- **Paper setup:** `SqlAlchemyPaperPortfolioSetupRepository` (`:442-509`) — hardcoded paper-safety booleans on insert (`:451-457`).
- **Settings:** `SqlAlchemyTradingSettingsRepository` (`:512-591`) — upsert pattern, increments `version` on update.
- **System events:** `SqlAlchemySystemEventRepository` (`:1830-1968`) — create / get / list-open with `mark_resolved` / `mark_archived` state transitions.
- **Market data:** `SqlAlchemyMarketDataSnapshotRepository` / `SqlAlchemyMarketDataBarRepository` / `SqlAlchemyMarketDataLatestSnapshotRepository`.
- **IBKR sync / audit:** `SqlAlchemyIbkrSyncSnapshotRepository` (`:850`), `SqlAlchemyIbkrConnectionAuditRepository` (`:3373`).
- **Forecast / calibration:** `SqlAlchemyForecastRepository` (`:4219-4434`, append-only with locked-enum `mark_expired`, plus `list_for_date_summary` for the dashboard at `:4313-4370`); `SqlAlchemyCalibrationDiaryRepository` (`:4437-4573`, coverage stats join against `forecasts`).
- **Decision Package:** `SqlAlchemyDecisionPackageRepository` (`:4578-4790`) — append-only with `list_chain(ibkr_account_id, conid, limit)` returning the per-asset hash chain newest-first. **No `update` or `delete` methods.**
- **Action draft state machine:** `ActionDraftStateTransitionError(ValueError)` (`:4793-4802`) + `_ACTION_DRAFT_TERMINAL_STATUSES` (`:4805-4819`) + `_ACTION_DRAFT_TRANSITIONS` (`:4820-4911`). Locked edges. `_require_action_draft_transition_allowed` (`:4914-4922`) raises if a caller asks for a forbidden edge.
- **Action draft:** `SqlAlchemyActionDraftRepository` (`:4925-5423`) — atomically writes one `action_draft_audit` row per insert / edit / state-transition. **No public `delete()` method**; "delete" is a status transition.
- **Audit + lifecycle:** `SqlAlchemyActionDraftAuditRepository` (`:5424-5487`), `SqlAlchemyIbkrSubmissionAuditRepository` (`:5644-5749`), `SqlAlchemyIbkrSubmissionLifecycleRepository` (`:5752-5829`), `SqlAlchemyIbkrExecutionsRepository` (`:5832-5922`) — all append-only with `RETURNING id` on insert.
- **Behavioural guardrails:** `SqlAlchemyBehaviouralGuardrailSettingsRepository` (`:5925-5992`) — `get_or_default(ibkr_account_id, now)` returns the row if present, else `BehaviouralGuardrailSettings.default_for_account(...)` *without* inserting.
- **Reconciliation:** `SqlAlchemyReconciliationAuditRepository` (`:6101+`), `SqlAlchemyUnmatchedExecutionAuditRepository`, `SqlAlchemyManualReviewQueueRepository`, `SqlAlchemyReconciliationRunAuditRepository`.

### Notable implementation choices

- **Every write goes through the readiness gate.** All repositories receive the `MigrationReadinessReport` in their constructor; `_Base._insert` (or an explicit `ensure_persistence_allowed(self._readiness_report)` call) blocks writes unless `migration_readiness_is_safe_to_write(report)` is True.
- **Reads bypass the gate** — read-only access is allowed even when writes are blocked.
- **`dataclasses.asdict` is the common payload pattern**: `self._insert(broker_accounts, asdict(record))` (`:369`) — relies on dataclass field names matching column names.
- **Append-only repos with autoincrement** use `.returning(table.c.id)` and refill the dataclass with the new id (`:5671-5689`).
- **No engine / session caching.** Per-call connections only; no SQLAlchemy session factory; no thread-local context.
- **JSON columns** stored as Python `list` / `dict` and read back as `list` / `dict` (SQLAlchemy `JSON` type); the repos do small fix-ups (e.g. `_json_tuple_or_none` to make the dataclass field a tuple).
- **Decimal handling.** Rows return either Python `Decimal` or raw strings depending on dialect; `_to_decimal` normalises.
- **State-transition map and terminal-status set live here** (`:4820-4911`), not in `metadata.py`. The DB has the enum CHECK; Python owns the per-edge logic.
- **File-level pragma:** the module begins with `# mypy: disable-error-code="union-attr"` (`:1`) — pre-existing.

```python
# sql_repositories.py:327-335
class _Base:
    def __init__(self, connection: Connection, readiness_report: MigrationReadinessReport) -> None:
        self._connection = connection
        self._readiness_report = readiness_report

    def _insert(self, table: Table, values: dict[str, Any]) -> None:
        ensure_persistence_allowed(self._readiness_report)
        self._connection.execute(table.insert().values(**values))
```

```python
# sql_repositories.py:4869-4911 — action-draft state-transition map (excerpt)
"working": frozenset(
    {"filled", "partially_filled", "cancelled", "rejected", "pending_cancellation"}
),
...
"awaiting_reply_timeout": frozenset(
    {"filled", "partially_filled", "cancelled", "rejected", "requires_manual_review"}
),
"requires_manual_review": frozenset(),
```

## Alembic chain overview

**Path:** `packages/storage/alembic/versions/`

### Inventory

**53 migration files**, `0001_…py` through `0053_…py`. The canonical list is mirrored as `_EXPECTED_MIGRATION_REVISIONS` in `migration_readiness.py:60-628` (each entry carries `revision_id`, `previous_revision_id`, `filename`, Dutch `label_nl`, Dutch `description_nl`). Each migration declares `revision`, `down_revision`, `branch_labels = None`, `depends_on = None` (e.g. `0001_paper_setup_audit_foundation.py:9-12`; `0053_reconciliation_audit_and_manual_review.py:35-38`). The chain is strictly **linear** — no branches, no merges.

### Naming convention

`<4-digit-zero-padded-number>_<snake_case_slug>.py`. The slug describes the topic. In the Python file, the `revision` literal uses the same form (e.g. `revision = "0053_reconciliation_audit_and_manual_review"`); the first 14 migrations use bare numeric ids (`"0001"`–`"0014"`) while 15+ use the full slug.

### Bookends

- **`0001_paper_setup_audit_foundation.py`** (119 lines, `down_revision = None`) creates three tables: `paper_portfolio_setups` (with hardcoded paper-only / live-trading-false CHECK constraints), `paper_cash_accounts` (FK to setups, `currency = 'eur'` lock), and `audit_events` (the hash-chain table).

```python
# alembic/versions/0001_paper_setup_audit_foundation.py:18-44
op.create_table(
    "paper_portfolio_setups",
    sa.Column("setup_id", sa.Text(), nullable=False),
    ...
    sa.CheckConstraint("paper_only IS TRUE", name="ck_paper_portfolio_setups_paper_only_true"),
    sa.CheckConstraint("real_money_used IS FALSE", name="ck_paper_portfolio_setups_real_money_used_false"),
    ...
)
```

- **`0053_reconciliation_audit_and_manual_review.py`** (323 lines, `down_revision = "0052_ibkr_submission_lifecycle_audit_and_executions"`) widens `action_drafts.status` (drop + re-create the CHECK constraint via `batch_alter_table` to add `'requires_manual_review'`), then creates four append-only tables: `reconciliation_audit` (one row per Pass A/B/C action, with `ibkr_evidence_json`), `unmatched_execution_audit` (UNIQUE on `ibkr_exec_id`), `manual_review_queue` (FK to `action_drafts`, locked reason / resolution enums), and `reconciliation_run_audit` (one row per reconciler tick). Downgrade restores the prior 15-status CHECK at `:316-323`.

### Slice categories (filename-grouped)

- Paper setup + audit foundation: `0001`.
- Broker accounts + sync runs: `0002`–`0006`.
- System events / trading settings / evidence ledger: `0007`–`0009`.
- Research source archive + extraction + scans + credibility + evidence + gate outcomes + conflicts: `0010`–`0017`.
- Asset identity (master + listing + alias) + source-to-asset linking: `0018`, `0019`, `0022`.
- Watchlist foundation: `0020`.
- Market data storage / latest snapshots / EOD / bars: `0021`, `0024`, `0027`, `0048`.
- Request log / provider / freshness contracts: `0023`.
- IBKR sync snapshot + FX snapshot: `0025`–`0026`.
- Asset forecasts + suggestions + decision packages + action drafts + submissions: `0027`–`0031`.
- Prediction diary + decision-package explanations + Belgian TOB + daily briefings: `0032`–`0036`.
- Scheduler / universe scan / fundamentals / order vocab: `0037`–`0040`.
- V1.1 expansion — predictor backtests / per-predictor contributions / Claude budget / conditional orders: `0041`–`0044`.
- Task 126 IBKR account-id + connection audit: `0045`.
- Task 127 APScheduler audit + state: `0046`.
- Task 128 cold-start seed + watchlist confirmation: `0047`.
- Task 129 EOD + FX runtime + provider call audit: `0048`.
- Task 130 forecasts + calibration diary: `0049`.
- Tasks 132–135 Decision Package + Action Draft V2 + IBKR submission lifecycle + reconciliation: `0050`–`0053`.

### Cross-cutting migration patterns

- Every migration imports `import sqlalchemy as sa` and `from alembic import op`.
- Chain head identified by `down_revision = None` (only `0001`).
- New tables via `op.create_table(...)`; column additions via `op.add_column(...)`; CHECK enum widening via `op.batch_alter_table(...).drop_constraint + create_check_constraint` (see `0053:62-69`).
- Every `upgrade()` has a matching `downgrade()` (e.g. `0001` drops the three tables in reverse order; `0035_action_draft_belgian_tob.py:28-30` drops the two columns added).
- `server_default=sa.false()` / `sa.true()` mirrors the `metadata.py` defaults.
- Money / quantity columns use `sa.Numeric(20, 6)` (matching `MONEY_NUMERIC`).
- Indexes declared explicitly via `op.create_index("ix_…", "table", ["col1","col2"])` (see `0053:114-123`); mirrored at the metadata level for ORM-side awareness (`metadata.py:1414-1433, :2087-2094, :2199-2203, …`).
- No Postgres-specific features beyond `JSON` (SQLAlchemy generic); the codebase stays SQLite-test-compatible.
- Each migration carries a docstring summarising what it does, the revision id, and a "Create Date" line. Later (Task 126+) migrations include multi-paragraph Dutch + English narrative explaining the product locks.

### Alembic runner config

- `packages/storage/alembic.ini:1-7` — `script_location = alembic`, `prepend_sys_path = src`, placeholder `sqlalchemy.url = postgresql://placeholder_user:placeholder_password@localhost:5432/placeholder_db` with a comment that it must be overridden via env/secret. Logging configured for `sqlalchemy.engine` (WARN) and `alembic` (INFO).
- `packages/storage/alembic/env.py:1-53` — imports `get_target_metadata` from `alembic_helpers`. Runs offline (`literal_binds=True`, `paramstyle="named"`) or online (`engine_from_config` with `poolclass=pool.NullPool`). Both modes set `target_metadata` and `compare_type=True`. Standard scaffolding; no project-specific hooks; no `process_revision_directives`; no `include_object` filter.

```python
# alembic/env.py:34-47
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
```

## Cross-cutting observations

1. **Three layers, one shape.** Every persisted concept exists three times: as a `Table` in `metadata.py`, a frozen-dataclass `Record` / `Entry` in `repository_contracts.py` (with `__post_init__` validators), and one or more `SqlAlchemy…Repository` classes in `sql_repositories.py`. The Alembic migrations are a fourth, independent declaration.

2. **Safety-boolean tri-defense.** The recurring `safe_for_*` boolean pattern is enforced at **three** layers: (a) the migration sets `server_default=sa.false()`; (b) for the newer Task 132/133 tables, a CHECK constraint hardcodes `= FALSE` (`metadata.py:2470-2477, :2628-2631`); (c) the dataclass `__post_init__` raises `ValueError` if a caller sets the field to True. Each layer is documented in adjacent comments as "defense in depth".

3. **Decimal-first money handling.** No `Float` columns appear anywhere. `MONEY_NUMERIC = Numeric(precision=20, scale=6)` is the default; finer scales (`Numeric(20,8)`, `(20,10)`, `(8,6)`) for log returns and probabilities. All dataclass numeric fields are typed `Decimal`; `_to_decimal(value)` (`sql_repositories.py:213-216`) normalises any inbound numeric to a `Decimal`.

4. **Append-only audit tables.** A large subset of tables are explicitly append-only by repository design (no `update_*` / `delete_*` methods exist): `audit_events`, `system_events` (status-only updates), `decision_packages`, `action_draft_audit`, `ibkr_submission_audit`, `ibkr_submission_lifecycle`, `ibkr_executions`, `reconciliation_audit`, `unmatched_execution_audit`, `reconciliation_run_audit`, `scheduled_run_audit`, `watchlist_confirmation_audit`, `ibkr_connection_audit`, `calibration_diary`, `provider_call_audit`, `cold_start_seed_audit`, `prediction_diary_predictor_contributions`. The repositories simply omit mutation methods; the DB itself doesn't enforce immutability.

5. **Per-asset hash chains.** Three tables carry `previous_*_hash` and `audit_trail_hash` (or `event_hash`) columns to form per-asset linked-list audit chains: `audit_events` (`previous_hash` / `event_hash`), `decision_packages` (`previous_package_hash` / `audit_trail_hash`, chained per `(ibkr_account_id, conid)`), `action_drafts` (`previous_draft_hash` / `audit_trail_hash`).

6. **Locked-vocabulary enums everywhere.** Module-private `frozenset`s in `repository_contracts.py` enumerate every accepted value for `status`, `event_type`, `mode_detected`, `pass_name`, `divergence_type`, `provider`, `confidence_level`, `label`, `order_type`, `tif`, `condition_kind`, `comparator`, etc. The migrations mirror them as CHECK constraints. The combination prevents bad enum values both at write time (Python raises before SQL) and at row level (DB rejects an in-flight bypass).

7. **Foreign-key naming.** FKs are declared inline without explicit `name=`, so SQLAlchemy/Alembic auto-generate constraint names — neither `metadata.py` nor the migration files specify them. Cross-table references use `Text` PKs (string UUIDs) for older tables; the append-only audit tables added in Task 134+ use `Integer autoincrement` (`ibkr_submission_audit.id`, `ibkr_submission_lifecycle.id`, `ibkr_executions.id`, `reconciliation_audit.id`, `manual_review_queue.id`, etc.).

8. **All timestamps timezone-aware.** Every `DateTime` column uses `timezone=True`. The dataclasses accept `datetime` without an explicit tzinfo check at the contract level; `_require_ordered_datetimes` enforces ordering on `(created_at, updated_at)`, `(scanned_at, checked_at)`, etc.

9. **Dutch microcopy in every row.** Almost every domain table has at least one `*_nl` column (`explanation_nl`, `summary_nl`, `help_nl`, `rationale_nl`, `reason_nl`, `title_nl`, `body_nl`, `label_nl`). The migration's `MigrationRevisionInfo` carries `label_nl` + `description_nl`. The readiness reports surface Dutch explanations exclusively.

10. **Migration-readiness as the single write gate.** `ensure_persistence_allowed(report)` (`sql_repositories.py:206-210`) is called from every `_Base._insert`. The only way to obtain a `MigrationReadinessReport` whose `persistence_allowed=True` is for `check_online_migration_readiness` to find the DB's `alembic_version.version_num` equal to `inventory.latest_expected_revision_id` — i.e. exactly at the chain head (currently `"0053_reconciliation_audit_and_manual_review"`). Any other revision (older, newer, or unknown) returns a status that blocks writes.

11. **No engine caching, no globals.** `connection_provider.py:42-71` creates an engine per `checked_connection()` call and disposes it in `finally`. There is no global engine, no SQLAlchemy session factory, no thread-local context. The repositories are constructed per-request with a passed-in connection.

12. **Tests vs storage.** Pure validation logic (the `_require_*` helpers, the locked frozensets, the per-order-type invariant function, the state-transition map) is all in plain Python without DB dependence — making contract-level unit tests possible without a live database. The SQL repositories require a live `Connection` but their behaviour is straightforward `dataclasses.asdict` → `table.insert().values(**…)` plus per-row read-back functions, so testing typically uses a SQLite in-memory engine plus the migrations applied via Alembic's `command.upgrade`.

## Open questions / uncertainty

- The revision-id naming inconsistency (`0001`–`0014` bare numeric vs `0015+` slug suffix) (`migration_readiness.py:60-628`) appears to be an artefact of the chain's age — the chain still validates structurally, but the format change is undocumented in the file headers. Whether to retroactively normalise (a downgrade risk) is out of scope for Phase 1a.
- The dataclass-layer "safe_for_*" raises duplicate the DB CHECK constraints by design ("defense in depth"). Whether all three layers need to stay in lockstep or can be loosened in any future refactor is for Phase 1b architecture review.
- `sql_repositories.py:1` opens with `# mypy: disable-error-code="union-attr"` (file-level pragma). Whether this is needed across the whole 6.6k-line file or could be narrowed is out of scope here; recorded in T-051's `_dismissed.md`.
- `migration_readiness.py` enforces `latest_expected_revision_id` equality — there is no "newer than expected" status that allows writes (newer DB returns `MIGRATIONS_UNKNOWN`, which blocks). Whether a forward-compatible mode is desirable is a doctrine-level question.
- The `BrokerStorageUnitOfWork.commit()` / `rollback()` no-ops (`sql_repositories.py:1823-1827`) put the outer-transaction responsibility on the caller. Whether the abstraction earns its keep, or whether it should be removed in favour of explicit per-call transactions, is a Phase 1b architecture-review question.
