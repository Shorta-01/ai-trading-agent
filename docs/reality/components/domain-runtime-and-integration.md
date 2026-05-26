# `packages/domain` — runtime and integration

**Phase:** 1a (reality components)
**Task:** T-001
**Scope:** nine modules in `packages/domain/src/portfolio_outlook_domain/` that describe the runtime topology, scheduling, persistence contracts, broker integration, and order / execution / ledger journal.

This file is descriptive. It states what the code at HEAD does today, with `path/to/file.py:NNN` citations and short excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

- `runtime.py` — runtime services, health, startup plan, background job types, topology.
- `scheduler.py` — scheduled-job definitions, eligibility checks, job-run records, plan.
- `storage.py` — storage backends, schema versions, migration plans, retention, backup, readiness — the package's only non-frozen module (uses raw `BaseModel`). Largest file in the package at 447 lines.
- `broker_adapter.py` — adapter-level snapshot models with their own local enums; `_BrokerDecimalModel` mixin.
- `broker_reconciliation.py` — reconciliation passes, classification, source-of-truth policy.
- `ibkr.py` — IBKR-specific reference types (instrument / order / permission).
- `orders.py` — `PaperOrder`, `ExecutionFill`.
- `execution.py` — `ExecutionTarget`, `ExecutionIntent`, `ExecutionModeSettings`.
- `ledger.py` — `CashLedgerEntry`, `PaperTransaction`.

Every pydantic model in these modules inherits `DomainBaseModel` (`primitives.py:9-10`) **except** `storage.py`, which uses `BaseModel` directly. `broker_adapter.py` and `broker_reconciliation.py` define **local enums** that overlap with the enums in `.enums` — see Cross-cutting observations.

## `runtime.py` — services, topology, jobs

**Path:** `packages/domain/src/portfolio_outlook_domain/runtime.py` (515 lines)

### Public surface

- `RuntimeServiceDefinition` (`runtime.py:27-57`) — fields: `runtime_service_id`, `service_kind`, `service_name`, `criticality`, `startup_phase`, `dependency_service_ids: list[RuntimeServiceId]`, `startup_dependency_policy`, `resource_profile`, `parallel_execution_policy`, `failure_policy`, `enabled_by_default`, `explanation_nl`.
- `RuntimeServiceHealth` (`:60-85`) — `health_check_id`, `runtime_service_id`, `status`, `severity`, `checked_at`, `message_nl`, `blocks_new_suggestions: bool`.
- `StartupPlanStep` (`:88-101`) — `step_order: int`, `startup_phase`, `runtime_service_id`, `required: bool`, `explanation_nl`.
- `StartupPlan` (`:104-120`) — `startup_plan_id`, `plan_name`, `target`, `steps: list[StartupPlanStep]`, `created_at`.
- `RuntimeTopology` (`:123-149`) — `runtime_topology_id`, `topology_name`, `target`, `services: list[RuntimeServiceDefinition]`, `startup_plan: StartupPlan`, `created_at`.
- `BackgroundJobType` (`:152-168`) — `background_job_type_id`, `job_name`, `service_kind`, `resource_profile`, `parallel_execution_policy`, `allowed_on_raspberry_pi_5: bool`, `requires_queue: bool`, `explanation_nl`.
- Functions: `build_default_runtime_topology(*, created_at)` (`:171-382`) returns a canonical topology of 13 services with deterministic startup plan; `build_default_background_job_types()` (`:385-467`); `find_service(topology, service_kind)` (`:470-477`); `service_blocks_suggestions(service, health)` (`:480-502`); `required_services(topology)` (`:505-506`); `parallel_safe_services(topology)` (`:509-515`).

### Collaborators

Twelve enums from `.enums` (`RuntimeServiceCriticality`, `RuntimeServiceKind`, `StartupPhase`, `RuntimeServiceStatus`, `RuntimeHealthSeverity`, `ServiceFailurePolicy`, `ParallelExecutionPolicy`, `RuntimeResourceProfile`, `StartupDependencyPolicy`, `RuntimeDeploymentTarget`, etc.) (`runtime.py:5-16`); typed IDs from `.identifiers` (`:17-23`); `DomainBaseModel` from `.primitives` (`:24`).

### Notable choices

- All validation via `@model_validator(mode="after")` with Dutch error strings.
- Cross-field rules in `RuntimeServiceDefinition`: required services must be `enabled_by_default=True` (`:45-49`); a service cannot depend on itself (`:50-51`); `HEAVY` resource profile cannot be `PARALLEL_SAFE` (`:52-56`).
- `RuntimeServiceHealth` enforces that critical severity, or unhealthy + error/critical, must set `blocks_new_suggestions=True` (`:73-84`).
- `RuntimeTopology` enforces unique `service_id`s, that the startup plan only refers to known services, and that every REQUIRED service is in the plan (`:135-148`).
- `service_blocks_suggestions` has explicit early-return short-circuits for `blocks_new_suggestions`, `CRITICAL` severity, then a permissive branch for `OPTIONAL` services with `DISABLE_OPTIONAL_FEATURE`, then the general `BLOCK_SUGGESTIONS` rule against `DEGRADED`/`UNHEALTHY`/`STOPPED`/`BLOCKED`.

```python
# runtime.py:41-57
@model_validator(mode="after")
def validate_model(self) -> "RuntimeServiceDefinition":
    if not self.service_name.strip() or not self.explanation_nl.strip():
        raise ValueError("service_name en explanation_nl zijn verplicht")
    if (
        self.criticality is RuntimeServiceCriticality.REQUIRED
        and not self.enabled_by_default
    ):
        raise ValueError("required service moet enabled_by_default=True hebben")
```

```python
# runtime.py:480-502
def service_blocks_suggestions(service, health) -> bool:
    if health.blocks_new_suggestions:
        return True
    if health.severity is RuntimeHealthSeverity.CRITICAL:
        return True
    if (service.criticality is RuntimeServiceCriticality.OPTIONAL
        and service.failure_policy is ServiceFailurePolicy.DISABLE_OPTIONAL_FEATURE):
        return False
    return (service.failure_policy is ServiceFailurePolicy.BLOCK_SUGGESTIONS
        and health.status in {RuntimeServiceStatus.DEGRADED, ...})
```

## `scheduler.py` — scheduled jobs and eligibility

**Path:** `packages/domain/src/portfolio_outlook_domain/scheduler.py` (372 lines)

### Public surface

- `RetryPolicy` (`scheduler.py:33-49`) — `retry_policy_id`, `backoff_policy: RetryBackoffPolicy`, `max_attempts: int = Field(ge=0)`, `delay_seconds: int = Field(ge=0)`, `explanation_nl`.
- `ScheduledJobDefinition` (`:52-87`) — `scheduled_job_id`, `background_job_type_id`, `job_name`, `cadence`, `priority`, `safety_impact`, `resource_limit`, `required_service_ids`, `required_data_domains`, `retry_policy`, `enabled_by_default`, `explanation_nl`.
- `JobEligibilityCheck` (`:90-117`) — `job_eligibility_check_id`, `scheduled_job_id`, `checked_at`, `status`, `skip_reasons`, `block_reasons`, `service_health_ids`, `source_reference_ids`, `data_quality_status`, `explanation_nl`.
- `JobRunRecord` (`:120-148`) — `job_run_id`, `scheduled_job_id`, `status`, `started_at: datetime | None`, `finished_at: datetime | None`, `attempt_number: int = Field(ge=1)`, `eligibility_check_id?`, `audit_event_ids`, `message_nl`.
- `SchedulerPlan` (`:151-167`) — `scheduler_plan_id`, `plan_name`, `target`, `jobs: list[ScheduledJobDefinition]`, `created_at`.
- Functions: `build_default_scheduler_plan(*, created_at)` (`:190-313`, 8 default jobs); `job_can_create_suggestions`, `job_requires_queue`, `job_allowed_on_raspberry_pi` (`:316-336`); `build_blocked_eligibility_check(...)` (`:339-356`); `build_eligible_check(...)` (`:359-372`). Private: `_default_retry_none`, `_default_retry_exp` (`:170-187`).

### Collaborators

Eleven enums from `.enums` (`ScheduleCadence`, `JobPriority`, `JobSafetyImpact`, `JobResourceLimit`, `ScheduledJobStatus`, `JobSkipReason`, `JobBlockReason`, `DataDomain`, `DataQualityStatus`, `RetryBackoffPolicy`, `RuntimeDeploymentTarget`); typed IDs from `.identifiers`; `DomainBaseModel` from `.primitives`.

### Notable choices

- `JobRunRecord` is shaped to be a journal entry per attempt (`attempt_number`, `started_at` / `finished_at`, link to `JobEligibilityCheck`).
- `build_default_scheduler_plan` forces `created_at.astimezone(UTC)` — explicit timezone normalisation (`:312`).
- `RetryPolicy` enforces semantic coherence: `NONE` policy must have `max_attempts==0 and delay_seconds==0`; `MANUAL_ONLY` must have `max_attempts==0` (`:44-48`).
- `ScheduledJobDefinition` cross-field rules: `MAY_CREATE_SUGGESTIONS` jobs require both `required_service_ids` and `required_data_domains`; `EXTERNAL_WORKER_RECOMMENDED` jobs cannot run `EVERY_5_MINUTES`; `BLOCKED_ON_RASPBERRY_PI` cannot be `enabled_by_default` (`:72-86`).
- `JobEligibilityCheck` enforces three-way consistency between `status`, `skip_reasons`, and `block_reasons` (`:106-116`).
- `JobRunRecord` lifecycle: `RUNNING` requires `started_at` and no `finished_at`; `COMPLETED`/`FAILED` require both and `finished_at >= started_at`; `BLOCKED`/`SKIPPED` require an `eligibility_check_id` (`:135-147`).

```python
# scheduler.py:72-86
if self.safety_impact is JobSafetyImpact.MAY_CREATE_SUGGESTIONS:
    if not self.required_service_ids:
        raise ValueError("suggestie-jobs vereisen required_service_ids")
    if not self.required_data_domains:
        raise ValueError("suggestie-jobs vereisen required_data_domains")
if (self.resource_limit is JobResourceLimit.EXTERNAL_WORKER_RECOMMENDED
    and self.cadence is ScheduleCadence.EVERY_5_MINUTES):
    raise ValueError("external_worker_recommended mag niet every_5_minutes zijn")
```

```python
# scheduler.py:135-147
if self.status is ScheduledJobStatus.RUNNING:
    if self.started_at is None or self.finished_at is not None:
        raise ValueError("running vereist started_at en geen finished_at")
if self.status in {ScheduledJobStatus.COMPLETED, ScheduledJobStatus.FAILED}:
    if self.started_at is None or self.finished_at is None:
        raise ValueError("completed/failed vereist started_at en finished_at")
    if self.finished_at < self.started_at:
        raise ValueError("finished_at moet na started_at liggen")
```

## `storage.py` — backends, schema, retention, backup, readiness

**Path:** `packages/domain/src/portfolio_outlook_domain/storage.py` (447 lines — largest module in the package)

### Public surface

> Note: this module extends `pydantic.BaseModel` directly (NOT `DomainBaseModel`), so models are **not frozen** here, unlike every other module in this group (`storage.py:3, :31`).

- `StorageBackendDefinition` (`:31-61`) — `storage_backend_id`, `backend_kind`, `status`, `persistence_mode`, `label_nl`, `help_nl` (both `min_length=1`), `stores_sensitive_data`, `stores_secret_values`, `enabled`.
- `StorageSchemaVersion` (`:64-76`) — `storage_schema_version_id`, `version_label`, `applied: bool`, `planned: bool`, `created_at`, `description_nl`.
- `StorageMigrationPlan` (`:79-92`) — `storage_migration_plan_id`, `from_version: str | None`, `to_version`, `required`, `safe_to_apply_automatically`, `requires_backup_first`, `description_nl`.
- `StorageRetentionPolicy` (`:95-112`) — `storage_retention_policy_id`, `entity_kind`, `retention_category`, `immutable_required`, `explanation_nl`.
- `PersistedRecordReference` (`:115-128`) — `persisted_record_reference_id`, `entity_kind`, `storage_backend_id`, `record_key: str (min_length=1)`, `created_at`, `sensitivity`, `explanation_nl`.
- `BackupPlan` (`:131-145`) — `backup_plan_id`, `status`, `encrypted_required`, `restore_test_required`, `target_description_nl`, `explanation_nl`.
- `RestoreCheck` (`:148-164`) — `restore_check_id`, `backup_plan_id`, `status`, `checked_at?`, `message_nl`, `blocks_persistence: bool`.
- `StorageReadinessCheck` (`:167-204`) — `storage_readiness_check_id`, `status`, `backends`, `schema_versions`, `migration_plans`, `backup_plan?`, `restore_checks`, `block_reasons`, `warning_reasons`, `checked_at`, three `can_persist_*: bool` flags, `title_nl`, `summary_nl`, `help_nl`.
- `StorageProfile` (`:207-227`) — `storage_profile_id`, `profile_name`, `backends`, `retention_policies`, `backup_plan?`, `created_at`, `explanation_nl`.
- Functions: `build_default_storage_profile(*, created_at)` (`:230-382`) — builds 5 PLANNED/disabled backends and 14 retention-policy pairs; `build_not_ready_storage_check(*, checked_at)` (`:385-406`); `storage_allows_paper_setup_persistence` (`:409-415`); `storage_allows_transaction_persistence` (`:418-424`); `storage_blocks_persistence` (`:427-434`); `backup_restore_trusted(*, backup_plan, restore_checks)` (`:437-447`).

### Collaborators

Twelve enums from `.enums`; nine ID aliases from `.identifiers`. Does **not** import `.primitives`.

### Notable choices

- This module **describes** persistence plans rather than performing persistence — every backend in `build_default_storage_profile` is `StorageBackendStatus.PLANNED` with `PersistenceMode.NOT_AVAILABLE` and `enabled=False`. The corresponding readiness helper returns `NOT_READY` with explicit block_reasons (`:387-406`).
- 14 retention-policy pairs (`:288-363`) map every `PersistedEntityKind` to a `RetentionCategory` and `immutable_required` flag — canonical retention contracts for PAPER_SETUP, PAPER_TRANSACTION, POSITION_LOT, ACTION_SUGGESTION, APPROVAL_DECISION, SOURCE_REFERENCE, AI_RESEARCH_RECORD, DATA_QUALITY_CHECK, SCHEDULER_JOB_RUN, SETTINGS_PROFILE, API_USAGE_SUMMARY, AUDIT_EVENT, TAX_RECORD, PAPER_CASH_ACCOUNT.
- `stores_secret_values=True` raises in `StorageBackendDefinition` (`:43-45`); `StorageSensitivity.PROHIBITED_SECRET_VALUE` raises in `PersistedRecordReference` (`:124-128`).
- All text fields use `Field(min_length=1)` — declared at field level rather than via a `.strip()` model validator, in contrast to other modules.
- `StorageRetentionPolicy` hard-couples kind to category: `AUDIT_EVENT` must be `AUDIT_LIFETIME` + immutable; `TAX_RECORD` must be `TAX_LIFETIME` (`:102-112`).
- `BackupPlan` is constructed *invariantly trusted*: `encrypted_required` and `restore_test_required` must both be true; otherwise the validator raises (`:139-145`).
- `RestoreCheck`: PASSED implies non-null `checked_at` and `blocks_persistence=False`; FAILED/BLOCKED imply `blocks_persistence=True` (`:156-164`).
- `StorageReadinessCheck` cross-rules: `READY_FOR_PERSISTENCE` forbids block_reasons, requires paper_setup + audit persistence, requires a `backup_plan` (`:186-193`); transaction persistence implies audit persistence; paper-setup persistence implies audit persistence (`:200-203`).
- `StorageMigrationPlan`: `safe_to_apply_automatically` requires `requires_backup_first` (`:88-92`).
- `backup_restore_trusted` is strict: only trusts if backup_plan exists, both `encrypted_required` and `restore_test_required`, AND at least one `RestoreCheck` is PASSED with non-blocking status (`:437-447`).

```python
# storage.py:186-204
@model_validator(mode="after")
def validate_readiness(self) -> "StorageReadinessCheck":
    if self.status is StorageReadinessStatus.READY_FOR_PERSISTENCE:
        if self.block_reasons:
            raise ValueError("Ready_for_persistence mag geen block reasons hebben.")
        if not self.can_persist_paper_setup or not self.can_persist_audit_events:
            raise ValueError("Ready_for_persistence vereist setup en audit persistence.")
        if self.backup_plan is None:
            raise ValueError("Ready_for_persistence vereist backup plan.")
    if self.can_persist_transactions and not self.can_persist_audit_events:
        raise ValueError("Transacties vereisen audit persistence.")
    if self.can_persist_paper_setup and not self.can_persist_audit_events:
        raise ValueError("Setup persistence vereist audit persistence.")
```

```python
# storage.py:437-447
def backup_restore_trusted(*, backup_plan, restore_checks) -> bool:
    if backup_plan is None:
        return False
    if not backup_plan.encrypted_required or not backup_plan.restore_test_required:
        return False
    return any(
        check.status is RestoreCheckStatus.PASSED and not check.blocks_persistence
        for check in restore_checks
    )
```

## `broker_adapter.py` — adapter-level snapshot models

**Path:** `packages/domain/src/portfolio_outlook_domain/broker_adapter.py` (172 lines)

### Public surface

- Local `StrEnum`s (defined inline, not in `.enums`): `BrokerProvider` (`ibkr` only); `BrokerEnvironment` (paper/live/unknown); `BrokerConnectionStatus` (8 values incl. authenticated/established/degraded); `BrokerAccountModeStatus` (confirmed_paper/live/unknown/blocked); `BrokerDataFreshnessStatus` (fresh/stale/missing/unknown); `BrokerPermissionStatus` (allowed/missing_permission/unknown/blocked) (`broker_adapter.py:10-49`).
- `_BrokerDecimalModel(DomainBaseModel)` — private mixin with a wildcard `@field_validator("*", mode="before")` that rejects float values (`:52-58`).
- `BrokerIntegrationSettings` (`:61-68`) — `ibkr_enabled=False`, `ibkr_provider`, `ibkr_expected_environment=PAPER`, `ibkr_account_id_hint`, `ibkr_gateway_url`, `ibkr_connection_timeout_seconds=10`, `ibkr_status_check_enabled=True`.
- `BrokerConnectionSnapshot` (`:71-78`).
- `BrokerAccountIdentity` (`:81-84`).
- `BrokerAccountModeCheck` (`:87-94`).
- `BrokerCashSnapshot` (`:97-108`) — Decimal fields: `total_cash_value`, `settled_cash`, `buying_power`, `net_liquidation`.
- `BrokerPositionSnapshot` (`:111-126`).
- `BrokerOpenOrderSnapshot` (`:129-141`) — note `status: str` (broker-string passthrough, not enum).
- `BrokerExecutionSnapshot` (`:144-157`).
- `BrokerAdapterError` (`:160-163`) — `code`, `message_nl`, `blocked=False`.
- `BrokerAdapterHealth` (`:166-172`).

### Collaborators

Only `.primitives.DomainBaseModel` and stdlib (`datetime`, `decimal.Decimal`, `enum.StrEnum`). This module **does not** import `.enums` — it defines its own enums. There are therefore two distinct `BrokerProvider` / `BrokerConnectionStatus` enums in the package (the canonical ones live in `.enums`; `broker_reconciliation.py` and `ibkr.py` use those).

### Notable choices

- All snapshot models include both `source_timestamp` (when the broker observed it) and `received_at` (when the adapter recorded it) — designed for an append-only adapter event log with provenance.
- `Decimal` enforced on every monetary/quantity field through `_BrokerDecimalModel`'s wildcard `@field_validator("*", mode="before")` — applies float rejection to every field. Non-Decimal-bearing models inherit `DomainBaseModel` directly.
- `can_submit_orders` defaults to `False` across `BrokerConnectionSnapshot` / `BrokerAccountModeCheck` / `BrokerAdapterHealth` — safe-by-default posture.

```python
# broker_adapter.py:52-58
class _BrokerDecimalModel(DomainBaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def reject_float_values(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float values are not allowed in broker contracts; use Decimal.")
        return value
```

```python
# broker_adapter.py:97-108
class BrokerCashSnapshot(_BrokerDecimalModel):
    broker_provider: BrokerProvider
    account_id: str
    currency: str
    total_cash_value: Decimal
    settled_cash: Decimal
    buying_power: Decimal
    net_liquidation: Decimal
    source_timestamp: datetime
    received_at: datetime
    freshness_status: BrokerDataFreshnessStatus
    raw_source_reference: str | None = None
```

## `broker_reconciliation.py` — reconciliation passes and classification

**Path:** `packages/domain/src/portfolio_outlook_domain/broker_reconciliation.py` (419 lines)

### Public surface

- Private helper `_reject_float_decimal_input(value)` (`:38-41`) — narrow per-field validator (vs. wildcard in `broker_adapter.py`).
- `BrokerSourceOfTruthPolicy` (`:44-71`) — five boolean authority flags + status + i18n trio. Validates: IBKR-is-broker-authoritative AND local-is-suggestions/approvals/explanations-authoritative AND `no_silent_correction`.
- `BrokerAccountIdentity` (`:74-98`) — fields incl. `configured`, `paper_account`, `live_trading_allowed`. Validates IBKR-only + paper-only.
- `BrokerSyncPlan` (`:101-125`).
- `BrokerPositionSnapshot` (`:128-149`) — Decimal `quantity`, optional Decimal `average_cost`/`market_value`. Distinct from `broker_adapter.BrokerPositionSnapshot`.
- `BrokerCashBalanceSnapshot` (`:152-168`).
- `BrokerExecutionSnapshot` (`:171-194`).
- `BrokerCommissionSnapshot` (`:197-213`).
- `ExternalBrokerActivity` (`:216-228`).
- `BrokerReconciliationDifference` (`:231-254`) — fields incl. `difference_kind`, `severity`, `broker_value: str | None`, `local_value: str | None`, `blocks_suggestions`, `requires_manual_review`. BLOCKING/CRITICAL severity must block suggestions.
- `BrokerReconciliationReport` (`:257-293`) — wraps a list of differences with `status`, `source_of_truth_policy`, `suggestion_policy`, `can_create_suggestions`, `can_create_orders`.
- Functions: `build_ibkr_source_of_truth_policy()` (`:295-310`); `build_not_configured_broker_account_identity()` (`:313-328`); `build_not_configured_broker_sync_plan()` (`:331-348`); `build_empty_reconciliation_report(*, broker_sync_run_id, checked_at)` (`:351-371`); `has_blocking_reconciliation_differences(differences)` (`:374-382`); `reconciliation_blocks_suggestions(report)` (`:385-398`); `classify_external_broker_activity_from_difference(...)` (`:401-419`).

### Collaborators

Twelve broker/IBKR/reconciliation enums from `.enums`; eleven typed IDs from `.identifiers`; `DomainBaseModel` from `.primitives`.

### Notable choices

- Per-field decimal float rejection (`@field_validator("quantity", "average_cost", "market_value", mode="before")` on each snapshot — `:146-149`, `:165-168`, `:191-194`, `:210-213`).
- **Hard safety:** `BrokerReconciliationReport.can_create_orders` *must* be `False` (`:274-276`) — version-1 paper-only invariant.
- `BrokerAccountIdentity` enforces IBKR-only & paper-only at the model level (`:88-89`).
- `reconciliation_blocks_suggestions` blocks on five non-clean statuses, on any blocking difference, on a `suggestion_policy` that starts with `"block"`, or unless CLEAN + `can_create_suggestions` — defaults to "block" (`:385-398`).
- `classify_external_broker_activity_from_difference` always tags `origin=DIRECT_IBKR_ORDER`, `data_kind=OTHER` (`:411-412`).

```python
# broker_reconciliation.py:273-293
@model_validator(mode="after")
def validate_report(self) -> "BrokerReconciliationReport":
    if self.can_create_orders:
        raise ValueError("can_create_orders must stay false in paper mode.")
    if self.status is ReconciliationStatus.CLEAN and self.differences:
        raise ValueError("Clean status must not include differences.")
    if (self.status in {ReconciliationStatus.DIFFERENCES_FOUND,
                        ReconciliationStatus.MANUAL_REVIEW_REQUIRED}
            and not self.differences):
        raise ValueError("Differences are required for this status.")
    if (has_blocking_reconciliation_differences(self.differences)
            and self.can_create_suggestions):
        raise ValueError("Blocking differences cannot allow suggestions.")
```

## `ibkr.py` — IBKR-specific reference rows

**Path:** `packages/domain/src/portfolio_outlook_domain/ibkr.py` (86 lines)

### Public surface

- `IBKRInstrumentReference` (`ibkr.py:18-49`) — `broker_reference_id`, `instrument_id`, `conid`, `symbol`, `sec_type`, `exchange`, `primary_exchange`, `currency: CurrencyCode`, `local_symbol`, `trading_class`, `multiplier: Decimal | None`, `market_name`, `min_tick: Decimal | None`, `valid_exchanges: list[str]`, `is_fractional_supported: bool | None`, `market_data_permission_status`, `trading_permission_status`.
- `IBKROrderReference` (`:52-70`) — `broker_order_reference_id`, `order_id`, `broker_provider`, `account_mode`, `ibkr_account_id`, `ibkr_order_id`, `ibkr_perm_id`, `client_id`, `transmission_status`, `submitted_at`, `last_status_at`, `status_message`.
- `IBKRDataPermissionSnapshot` (`:73-86`) — `broker_reference_id`, `instrument_id`, two permission statuses, `checked_at`, `explanation_nl`.

### Collaborators

`BrokerAccountMode`, `BrokerProvider`, `IBKRMarketDataPermissionStatus`, `IBKROrderTransmissionStatus`, `IBKRSecurityType`, `IBKRTradingPermissionStatus` from `.enums`; `BrokerOrderReferenceId`, `BrokerReferenceId`, `InstrumentId`, `OrderId` from `.identifiers`; `CurrencyCode`, `DomainBaseModel` from `.primitives`.

### Notable choices

- Designed as durable reference rows linking internal `InstrumentId` / `OrderId` to IBKR's identifiers (`conid`, `ibkr_order_id`, `ibkr_perm_id`).
- `IBKRDataPermissionSnapshot` records `checked_at` and `explanation_nl` — designed for an audit-trail row per permission check.
- `Decimal | None` for `multiplier` and `min_tick`; a shared `validate_positive_decimal` field validator enforces `> 0` when present (`:44-49`).
- `symbol` validated as non-empty after `.strip()` (`:37-42`).
- `IBKROrderReference` requires `broker_provider == BrokerProvider.INTERACTIVE_BROKERS` (note: this uses the `.enums.BrokerProvider` value `INTERACTIVE_BROKERS`, not `IBKR` from `broker_adapter.py`) (`:66-70`).

```python
# ibkr.py:44-49
@field_validator("multiplier", "min_tick")
@classmethod
def validate_positive_decimal(cls, value: Decimal | None) -> Decimal | None:
    if value is not None and value <= 0:
        raise ValueError("Decimal value must be positive")
    return value
```

```python
# ibkr.py:66-70
@model_validator(mode="after")
def validate_provider(self) -> "IBKROrderReference":
    if self.broker_provider != BrokerProvider.INTERACTIVE_BROKERS:
        raise ValueError("IBKROrderReference requires interactive_brokers provider")
    return self
```

## `orders.py` — paper orders and execution fills

**Path:** `packages/domain/src/portfolio_outlook_domain/orders.py` (88 lines)

### Public surface

- `PaperOrder` (`orders.py:12-64`) — `order_id`, `portfolio_id`, `instrument_id`, `side: TransactionSide`, `order_type: OrderType`, `status: OrderStatus`, `requested_quantity: Quantity | None`, `requested_amount: Money | None`, `limit_price: Money | None`, `suggested_by: SuggestionId | None`, `created_at`, `submitted_at`, `expires_at`, `reason_nl`, `mode: PaperLiveMode = PaperLiveMode.PAPER`.
- `ExecutionFill` (`:67-88`) — `fill_id`, `order_id`, `transaction_id`, `filled_quantity: Quantity`, `fill_price: Money`, `gross_amount: Money`, `costs: list[CostEstimate]`, `filled_at`, `status_after_fill: OrderStatus`.

### Collaborators

`CostEstimate` from `.costs`; `OrderStatus`, `OrderType`, `PaperLiveMode`, `TransactionSide` from `.enums`; five typed IDs from `.identifiers`; `DomainBaseModel`, `Money`, `Quantity` from `.primitives`.

### Notable choices

- `PaperOrder` is the canonical order row in the paper-trading model. Forces `mode == PaperLiveMode.PAPER` at model level — version-1 paper-only contract enforced in the type itself.
- Exactly one of `requested_quantity` / `requested_amount` required (`:41-46`), each must be `> 0` (`:48-59`).
- `LIMIT` order requires `limit_price` (`:61-63`).
- `mode != PAPER` raises (`:38-39`).
- `ExecutionFill` enforces `filled_quantity > 0`, `fill_price >= 0`, gross/fill currency match, and `status_after_fill ∈ {PARTIALLY_FILLED, FILLED}` (`:78-87`).

```python
# orders.py:41-63
has_quantity = self.requested_quantity is not None
has_amount = self.requested_amount is not None
if not has_quantity and not has_amount:
    raise ValueError("Either requested_quantity or requested_amount must be provided.")
if has_quantity and has_amount:
    raise ValueError("Provide requested_quantity or requested_amount, not both.")
...
if self.order_type is OrderType.LIMIT and self.limit_price is None:
    raise ValueError("limit_price is required for limit orders.")
```

```python
# orders.py:78-87
@model_validator(mode="after")
def validate_fill(self) -> "ExecutionFill":
    if self.filled_quantity.value <= Decimal("0"):
        raise ValueError("filled_quantity must be greater than zero.")
    if self.fill_price.amount < Decimal("0"):
        raise ValueError("fill_price amount must be zero or positive.")
    if self.gross_amount.currency != self.fill_price.currency:
        raise ValueError("gross_amount currency must match fill_price currency.")
    if self.status_after_fill not in {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED}:
        raise ValueError("status_after_fill must be partially_filled or filled.")
```

## `execution.py` — execution targets, intents, settings

**Path:** `packages/domain/src/portfolio_outlook_domain/execution.py` (137 lines)

### Public surface

- `ExecutionTarget` (`execution.py:25-76`) — `execution_target_id`, `mode`, `kind`, `provider`, `account_mode`, `status`, `approval_requirement`, four capability booleans (`can_submit_orders`, `can_submit_real_money_orders`, `can_read_account_data`, `can_read_market_data`), `explanation_nl`.
- `ExecutionIntent` (`:79-105`) — `execution_intent_id`, `suggestion_id`, `portfolio_id`, `instrument_id`, `action: AdviceAction`, `requested_amount?`, `requested_quantity?`, `target_execution_mode`, `status: ExecutionIntentStatus`, `reason_nl`, `created_at`.
- `ExecutionModeSettings` (`:108-137`) — `default_execution_mode = INTERNAL_PAPER`, six allow-flags (defaults: `allow_internal_paper=True`, others `False`), `approval_required_for_all_orders=True`.

### Collaborators

`AdviceAction`, `ApprovalRequirement`, `BrokerAccountMode`, `BrokerProvider`, `ExecutionIntentStatus`, `ExecutionMode`, `ExecutionModeStatus`, `ExecutionTargetKind` from `.enums`; five IDs from `.identifiers`; `DomainBaseModel`, `Money`, `Quantity` from `.primitives`.

### Notable choices

- Hard policy invariants in `ExecutionTarget`:
  - INTERNAL_PAPER / IBKR_PAPER / IBKR_LIVE_MANUAL → `approval_requirement == ALWAYS_REQUIRED` (`:48-53`).
  - `BLOCKED_AUTO` → must be `status==BLOCKED`, can_submit_orders=False, can_submit_real_money_orders=False (`:54-60`).
  - `IBKR_LIVE_READ_ONLY` → cannot `can_submit_orders` (`:61-62`).
  - Paper modes cannot `can_submit_real_money_orders` (`:63-67`).
  - `IBKR_LIVE_MANUAL` with real-money capability cannot be `status==AVAILABLE` by default (`:68-75`).
- `ExecutionIntent` requires one of amount/quantity and forbids `BLOCKED_AUTO` as a target (`:101-105`).
- `ExecutionModeSettings` enforces global safety: `approval_required_for_all_orders` must be `True`; `allow_blocked_auto` must be `False`; `default_execution_mode != BLOCKED_AUTO`; defaults paired with allow-flags (`:117-137`).

```python
# execution.py:46-67
@model_validator(mode="after")
def validate_rules(self) -> "ExecutionTarget":
    if self.mode in {ExecutionMode.INTERNAL_PAPER, ExecutionMode.IBKR_PAPER,
                     ExecutionMode.IBKR_LIVE_MANUAL,
                    } and self.approval_requirement != ApprovalRequirement.ALWAYS_REQUIRED:
        raise ValueError("approval_requirement must be always_required")
    if self.mode == ExecutionMode.BLOCKED_AUTO:
        if (self.status != ExecutionModeStatus.BLOCKED
                or self.can_submit_orders
                or self.can_submit_real_money_orders):
            raise ValueError("blocked_auto mode must stay blocked and non-submittable")
```

```python
# execution.py:117-137
@model_validator(mode="after")
def validate_settings(self) -> "ExecutionModeSettings":
    if not self.approval_required_for_all_orders:
        raise ValueError("approval_required_for_all_orders must be true")
    if self.allow_blocked_auto:
        raise ValueError("allow_blocked_auto must be false")
    if self.default_execution_mode == ExecutionMode.BLOCKED_AUTO:
        raise ValueError("default_execution_mode cannot be blocked_auto")
```

## `ledger.py` — cash ledger entries and paper transactions

**Path:** `packages/domain/src/portfolio_outlook_domain/ledger.py` (83 lines)

### Public surface

- `CashLedgerEntry` (`ledger.py:20-38`) — `ledger_entry_id`, `portfolio_id`, `entry_type: LedgerEntryType`, `amount: Money`, `occurred_at`, `reason_nl`, optional `related_instrument_id` / `related_transaction_id` / `related_order_id` / `related_suggestion_id`, `source_run_id?`.
- `PaperTransaction` (`:41-83`) — `transaction_id`, `portfolio_id`, `instrument_id`, `side: TransactionSide`, `status: TransactionStatus`, `quantity: Quantity`, `price: Money`, `gross_amount: Money`, `net_amount: Money`, `costs: list[CostEstimate]`, `occurred_at`, `settlement_date: date | None`, `reason_nl`, optional `related_order_id` / `related_suggestion_id`, `mode: PaperLiveMode = PaperLiveMode.PAPER`.

### Collaborators

`CostEstimate` from `.costs`; `LedgerEntryType`, `PaperLiveMode`, `TransactionSide`, `TransactionStatus` from `.enums`; seven IDs from `.identifiers`; `DomainBaseModel`, `Money`, `Quantity` from `.primitives`.

### Notable choices

- These are the journal-row shapes for the paper-trading ledger and transaction log. Both carry rich provenance (`source_run_id`, `related_*` FKs) for double-entry-style traceability across runs, suggestions, orders, and instruments.
- `reason_nl` required non-empty on both (`:33-38`, `:59-64`).
- `mode != PAPER` raises — paper-only invariant pinned in the row type (`:67-69`).
- `quantity > 0`, `price >= 0`, gross_amount/net_amount currencies must match price currency (`:71-81`). `net_amount` can be **less than** `gross_amount` (costs deducted) but currencies must agree.
- `settlement_date: date | None` is the only non-datetime time field (T+N settlement support).

```python
# ledger.py:66-83
@model_validator(mode="after")
def validate_transaction(self) -> "PaperTransaction":
    if self.mode is not PaperLiveMode.PAPER:
        raise ValueError("Version 1 is paper-only. PaperTransaction.mode must be 'paper'.")
    if self.quantity.value <= Decimal("0"):
        raise ValueError("quantity must be greater than zero.")
    if self.price.amount < Decimal("0"):
        raise ValueError("price amount must be zero or positive.")
    price_currency = self.price.currency
    if self.gross_amount.currency != price_currency:
        raise ValueError("gross_amount currency must match price currency.")
    if self.net_amount.currency != price_currency:
        raise ValueError("net_amount currency must match price currency.")
```

## Cross-cutting observations

- **Base model.** All modules in this group extend `DomainBaseModel` (`primitives.py:9-10`) **except** `storage.py`, which uses plain `pydantic.BaseModel` and is therefore *not* frozen (`storage.py:3, :31`).
- **Float-rejection patterns differ across modules.**
  - `broker_adapter._BrokerDecimalModel` uses a wildcard `@field_validator("*", mode="before")` (`broker_adapter.py:53-58`).
  - `broker_reconciliation.py` uses per-field `@field_validator(...)` decorators with a shared helper `_reject_float_decimal_input` (`broker_reconciliation.py:38-41, :146-149`).
  - `primitives.Money` / `Quantity` / `Percentage` reject floats individually (`primitives.py:25-30, :42-45, :58-63`).
- **Two `BrokerProvider` enums coexist.** `broker_adapter.BrokerProvider` is a local `StrEnum("ibkr")` (`broker_adapter.py:10-11`); `enums.BrokerProvider` value `INTERACTIVE_BROKERS` is used by `ibkr.py` (`ibkr.py:66-70`). Likewise `broker_adapter.BrokerConnectionStatus` is distinct from `enums.BrokerConnectionStatus` used in `broker_reconciliation.py`.
- **Dutch-language safety messages.** Validation error strings and `*_nl` description fields are consistently Dutch — a deliberate user-facing-trace convention.
- **Paper-only invariant in version 1** is encoded at multiple type layers: `PaperOrder.mode` (`orders.py:38`), `PaperTransaction.mode` (`ledger.py:68`), `BrokerAccountIdentity.live_trading_allowed=False` (`broker_reconciliation.py:88`), `BrokerReconciliationReport.can_create_orders=False` (`broker_reconciliation.py:275`), `ExecutionModeSettings.allow_blocked_auto=False` + `approval_required_for_all_orders=True` (`execution.py:117-122`).

## Open questions / uncertainty

- `storage.py` is the package's only non-frozen module — every model here is mutable. Whether this is deliberate (e.g. to allow mutation by orchestration code) or an oversight is not visible from the file alone (no module-level comment explaining the choice).
- The duplication of `BrokerProvider` / `BrokerConnectionStatus` across `.enums` and `broker_adapter.py` may be intentional (adapter layer keeps its own vocabulary for SDK-shaped types) or candidate for consolidation; Phase 1b architecture review will assess.
- `runtime.py` and `scheduler.py` define large `build_default_*` factories. Whether these defaults are consumed by production code or only by tests is out of scope for this Phase 1a doc.
- `broker_reconciliation.classify_external_broker_activity_from_difference` always tags `origin=DIRECT_IBKR_ORDER` and `data_kind=OTHER` (`:411-412`) regardless of the difference's nature — this looks like a placeholder; whether it is intentional pending future classification logic is unclear without cross-module tracing.
