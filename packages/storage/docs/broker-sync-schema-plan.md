# Broker sync schema plan (implementation design for next migration)

## 1. Purpose
Define an implementation-ready database schema design for future IBKR broker mirror synchronization, reconciliation reporting, and external broker activity tracking.

This document is a planning artifact for the **next** migration PR.

## 2. Current status
- Current schema only includes paper setup and audit foundation tables from migration `0001_paper_setup_audit_foundation`.
- No broker sync tables exist yet.
- No IBKR data is currently persisted.
- No app database writes exist yet in API/worker runtime.
- This document does not add or modify schema objects.

## 3. Source-of-truth rule
- Once IBKR is connected, IBKR is authoritative for broker-side facts: accounts, balances, positions, executions, commissions, order-state facts, and broker-side activity.
- AI-Trading-Agent stores a local mirror for analysis, audit trail, explanation, and suggestion gating.
- Local records may not silently override imported IBKR facts.

## 4. Future tables
Schema rollout is split into smaller safe PR slices.

Implemented now:
- `broker_accounts` and `broker_sync_runs` in migration `0002_broker_accounts_and_sync_runs`
- `broker_position_snapshots` and `broker_cash_snapshots` in migration `0003_broker_position_and_cash_snapshots`
- `broker_execution_snapshots` and `broker_commission_snapshots` in migration `0004_broker_execution_and_commission_snapshots`

Future migrations still planned:
- `broker_reconciliation_reports`
- `broker_reconciliation_differences`
- `external_broker_activities`

Original full target set:

1. `broker_accounts`
2. `broker_sync_runs`
3. `broker_position_snapshots`
4. `broker_cash_snapshots`
5. `broker_execution_snapshots`
6. `broker_commission_snapshots`
7. `broker_reconciliation_reports`
8. `broker_reconciliation_differences`
9. `external_broker_activities`

## 5. Table details

### 5.1 `broker_accounts`
Purpose: store IBKR account identity and status metadata (no credentials).

Columns:
- `broker_account_id` text primary key
- `broker_system` text not null
- `ibkr_account_ref` text nullable
- `account_label` text not null
- `account_mode` text not null
- `connection_status` text not null
- `configured` boolean not null
- `paper_account` boolean not null
- `live_trading_allowed` boolean not null
- `source_of_truth_status` text not null
- `created_at` timestamptz not null
- `updated_at` timestamptz nullable
- `explanation_nl` text not null

Constraints:
- `broker_system = 'ibkr'`
- `live_trading_allowed = false`
- `account_label` not empty
- `explanation_nl` not empty

Secret rule:
- No password/token/API-key/credential-value columns.

### 5.2 `broker_sync_runs`
Purpose: store planned/running/completed broker sync attempts.

Columns:
- `broker_sync_run_id` text primary key
- `broker_account_id` text nullable references `broker_accounts(broker_account_id)`
- `broker_system` text not null
- `sync_mode` text not null
- `sync_status` text not null
- `started_at` timestamptz not null
- `completed_at` timestamptz nullable
- `planned_data_kinds_json` json nullable
- `data_source_types_json` json nullable
- `requires_ibkr_configuration` boolean not null
- `requires_broker_session` boolean not null
- `blocks_suggestions_until_complete` boolean not null
- `summary_nl` text not null
- `help_nl` text not null

Constraints:
- `broker_system = 'ibkr'`
- `summary_nl` not empty
- `help_nl` not empty
- `completed_at is null or completed_at >= started_at` (where practical as check constraint)

### 5.3 `broker_position_snapshots`
Purpose: store imported IBKR position facts at point-in-time.

Columns:
- `broker_position_snapshot_id` text primary key
- `broker_sync_run_id` text not null references `broker_sync_runs(broker_sync_run_id)`
- `broker_account_id` text not null references `broker_accounts(broker_account_id)`
- `broker_system` text not null
- `imported_at` timestamptz not null
- `asset_identifier` text not null
- `asset_symbol` text not null
- `asset_type` text not null
- `currency` text not null
- `quantity` numeric(20, 6) not null
- `average_cost` numeric(20, 6) nullable
- `market_value` numeric(20, 6) nullable
- `source_data_kind` text not null
- `origin` text not null
- `source_reference_ids_json` json nullable
- `explanation_nl` text not null

Constraints:
- `broker_system = 'ibkr'`
- `asset_identifier` not empty
- `asset_symbol` not empty
- `asset_type` not empty
- `currency` not empty
- `origin` allows imported IBKR position origin values (including `imported_ibkr_position`)
- `explanation_nl` not empty

### 5.4 `broker_cash_snapshots`
Purpose: store imported IBKR cash balances at point-in-time.

Columns:
- `broker_cash_snapshot_id` text primary key
- `broker_sync_run_id` text not null references `broker_sync_runs(broker_sync_run_id)`
- `broker_account_id` text not null references `broker_accounts(broker_account_id)`
- `broker_system` text not null
- `imported_at` timestamptz not null
- `currency` text not null
- `cash_amount` numeric(20, 6) not null
- `source_data_kind` text not null
- `origin` text not null
- `source_reference_ids_json` json nullable
- `explanation_nl` text not null

Constraints:
- `broker_system = 'ibkr'`
- `currency` not empty
- `origin` allows imported IBKR cash origin values (including `imported_ibkr_cash`)
- `explanation_nl` not empty

### 5.5 `broker_execution_snapshots`
Purpose: store imported IBKR executions/trades (not transmission intent).

Columns:
- `broker_execution_snapshot_id` text primary key
- `broker_sync_run_id` text not null references `broker_sync_runs(broker_sync_run_id)`
- `broker_account_id` text not null references `broker_accounts(broker_account_id)`
- `broker_system` text not null
- `imported_at` timestamptz not null
- `execution_time` timestamptz not null
- `execution_id` text not null
- `order_id` text nullable
- `asset_identifier` text not null
- `asset_symbol` text not null
- `asset_type` text not null
- `side` text not null
- `quantity` numeric(20, 6) not null
- `price` numeric(20, 6) not null
- `currency` text not null
- `origin` text not null
- `source_reference_ids_json` json nullable
- `explanation_nl` text not null

Constraints:
- `broker_system = 'ibkr'`
- `execution_id` not empty
- `asset_identifier` not empty
- `asset_symbol` not empty
- `asset_type` not empty
- `side` not empty
- `quantity > 0`
- `price >= 0`
- `currency` not empty
- `explanation_nl` not empty

Important scope guard:
- No order transmission fields are designed here.
- This table is imported execution fact storage only.

### 5.6 `broker_commission_snapshots`
Purpose: store imported IBKR commission/fee facts linked to executions.

Columns:
- `broker_commission_snapshot_id` text primary key
- `broker_sync_run_id` text not null references `broker_sync_runs(broker_sync_run_id)`
- `broker_account_id` text not null references `broker_accounts(broker_account_id)`
- `broker_system` text not null
- `imported_at` timestamptz not null
- `execution_id` text not null
- `commission_amount` numeric(20, 6) not null
- `currency` text not null
- `realized_pnl` numeric(20, 6) nullable
- `source_reference_ids_json` json nullable
- `explanation_nl` text not null

Constraints:
- `broker_system = 'ibkr'`
- `execution_id` not empty
- `currency` not empty
- `explanation_nl` not empty

### 5.7 `broker_reconciliation_reports`
Purpose: store reconciliation summary between imported broker facts and local mirror state.

Columns:
- `broker_reconciliation_report_id` text primary key
- `broker_sync_run_id` text not null references `broker_sync_runs(broker_sync_run_id)`
- `broker_account_id` text nullable references `broker_accounts(broker_account_id)`
- `broker_system` text not null
- `status` text not null
- `suggestion_policy` text not null
- `can_create_suggestions` boolean not null
- `can_create_orders` boolean not null
- `checked_at` timestamptz not null
- `title_nl` text not null
- `summary_nl` text not null
- `help_nl` text not null

Constraints:
- `broker_system = 'ibkr'`
- `can_create_orders = false` in current product mode
- `title_nl` not empty
- `summary_nl` not empty
- `help_nl` not empty

### 5.8 `broker_reconciliation_differences`
Purpose: store individual mismatches between broker facts and local mirror state.

Columns:
- `broker_reconciliation_difference_id` text primary key
- `broker_reconciliation_report_id` text not null references `broker_reconciliation_reports(broker_reconciliation_report_id)`
- `broker_account_id` text not null references `broker_accounts(broker_account_id)`
- `broker_system` text not null
- `difference_kind` text not null
- `severity` text not null
- `detected_at` timestamptz not null
- `broker_value` text nullable
- `local_value` text nullable
- `asset_identifier` text nullable
- `currency` text nullable
- `blocks_suggestions` boolean not null
- `requires_manual_review` boolean not null
- `summary_nl` text not null
- `help_nl` text not null
- `source_reference_ids_json` json nullable
- `audit_event_ids_json` json nullable

Constraints:
- `broker_system = 'ibkr'`
- `difference_kind` not empty
- `severity` not empty
- If `severity` is blocking/critical, `blocks_suggestions` should be true (where practical as check constraint)
- `summary_nl` not empty
- `help_nl` not empty

### 5.9 `external_broker_activities`
Purpose: store detected broker-side activities not initiated by AI-Trading-Agent.

Columns:
- `external_broker_activity_id` text primary key
- `broker_account_id` text not null references `broker_accounts(broker_account_id)`
- `broker_system` text not null
- `detected_at` timestamptz not null
- `origin` text not null
- `data_kind` text not null
- `related_execution_id` text nullable
- `related_asset_identifier` text nullable
- `summary_nl` text not null
- `help_nl` text not null
- `source_reference_ids_json` json nullable
- `audit_event_ids_json` json nullable

Constraints:
- `broker_system = 'ibkr'`
- `origin` not empty
- `data_kind` not empty
- `summary_nl` not empty
- `help_nl` not empty

## 6. Foreign-key relationships
Required relationships:
- `broker_accounts` 1 -> many `broker_sync_runs`
- `broker_sync_runs` 1 -> many `broker_position_snapshots`
- `broker_sync_runs` 1 -> many `broker_cash_snapshots`
- `broker_sync_runs` 1 -> many `broker_execution_snapshots`
- `broker_sync_runs` 1 -> many `broker_commission_snapshots`
- `broker_sync_runs` 1 -> many `broker_reconciliation_reports`
- `broker_reconciliation_reports` 1 -> many `broker_reconciliation_differences`
- `broker_accounts` 1 -> many `external_broker_activities`

Also required for follow-up phases:
- Snapshot tables should later link to source references.
- Reconciliation reports should later link to `audit_events`.
- External broker activities should later link to `audit_events`.

## 7. Numeric and timestamp rules
- Money, prices, quantities, commissions, and realized P/L must use Decimal-compatible numeric columns.
- Use `numeric(20, 6)` as the standard for financial numeric fields in these tables.
- Do not use `float`, `real`, or `double precision`.
- Snapshot/report/difference/activity records must carry explicit point-in-time timestamps (`imported_at`, `checked_at`, `detected_at`, etc.).
- Next migration should include practical check constraints for timestamp ordering where applicable.

## 8. Secret-handling rules
- Never store IBKR password, API token, session token, OAuth token, refresh token, or full credentials in these tables.
- If future credential integration is needed, only store secret references and status metadata.
- Secret values remain outside normal application relational tables.

## 9. Reconciliation and suggestion blocking rules
- Broker/local differences must be recorded; no silent correction allowed.
- Critical/blocking differences must force `blocks_suggestions = true`.
- Reconciliation report policy fields (`suggestion_policy`, `can_create_suggestions`) should drive later suggestion gating.
- Direct broker-side activity not initiated by AI-Trading-Agent must be captured as `external_broker_activities` and may trigger warning/blocking until reviewed.
- Missing or stale snapshots should later downgrade or block broker-dependent suggestions.

## 10. Migration order
The next migration should create tables in this exact order:
1. `broker_accounts`
2. `broker_sync_runs`
3. `broker_position_snapshots`
4. `broker_cash_snapshots`
5. `broker_execution_snapshots`
6. `broker_commission_snapshots`
7. `broker_reconciliation_reports`
8. `broker_reconciliation_differences`
9. `external_broker_activities`

## 11. Downgrade order
The next migration downgrade should drop tables in this exact order:
1. `external_broker_activities`
2. `broker_reconciliation_differences`
3. `broker_reconciliation_reports`
4. `broker_commission_snapshots`
5. `broker_execution_snapshots`
6. `broker_cash_snapshots`
7. `broker_position_snapshots`
8. `broker_sync_runs`
9. `broker_accounts`

## 12. Acceptance criteria for the next migration PR
- Adds one new Alembic revision implementing all planned tables and constraints from this document.
- Does not introduce Float/REAL/DOUBLE PRECISION for financial fields.
- Applies source-of-truth and paper-only constraints (`broker_system='ibkr'`, `live_trading_allowed=false`, `can_create_orders=false` in current mode).
- Includes explicit foreign keys and check constraints described above.
- Keeps secrets out of relational table columns.
- Adds/updates storage tests to validate migration up/down and core constraints.
- Leaves runtime integration (repositories, IBKR API connections, workers) out of scope unless separately planned.

## 13. What is explicitly not implemented yet
- No Alembic migration revision is created in this PR.
- No SQLAlchemy metadata is changed in this PR.
- No database tables are added in this PR.
- No repository implementation is added.
- No API/worker database write path is added.
- No IBKR API integration is added.
- No credentials UI/settings form is added.
- No broker sync worker or reconciliation engine logic is added.

## 6. Implementatiestatus (Task 25A)
- ✅ Geïmplementeerd in migratie `0002_broker_accounts_and_sync_runs`:
  - `broker_accounts`
  - `broker_sync_runs`
- ⏳ Gepland voor latere migraties (veilig opgesplitst):
  - `broker_position_snapshots`
  - `broker_cash_snapshots`
  - `broker_execution_snapshots`
  - `broker_commission_snapshots`
  - `broker_reconciliation_reports`
  - `broker_reconciliation_differences`
  - `external_broker_activities`

Waarom opgesplitst:
- kleinere PR's beperken migratierisico;
- constraint/FK-validatie blijft beter reviewbaar;
- audit- en source-of-truth guardrails blijven expliciet per stap.

\n\n## Task 25D update (2026-05-19)\n- Added broker_reconciliation_reports and broker_reconciliation_differences in storage schema slice 4.\n- Scope is status/difference storage only; no reconciliation engine, IBKR integration, runtime persistence, repositories, API/worker DB wiring, or order transmission yet.\n- external_broker_activities remains planned for a later migration.


## Task 25E implementation status (2026-05-19)
Implemented migrations:
- 0002: `broker_accounts`, `broker_sync_runs`
- 0003: `broker_position_snapshots`, `broker_cash_snapshots`
- 0004: `broker_execution_snapshots`, `broker_commission_snapshots`
- 0005: `broker_reconciliation_reports`, `broker_reconciliation_differences`
- 0006: `external_broker_activities`

Status:
- Planned broker sync schema foundation is now structurally complete.

Future work remains:
- repository interfaces
- database readiness checks
- IBKR settings/status fields
- IBKR bootstrap preview
- broker snapshot import adapter skeleton
- reconciliation engine foundation
- external broker activity detection logic
