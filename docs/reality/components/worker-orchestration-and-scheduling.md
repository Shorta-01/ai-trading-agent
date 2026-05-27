# Reality — worker orchestration and scheduling

**Scope.** The worker's long-lived runtime: entry point, settings, APScheduler integration, the orchestrator main loop, single-flight `pg_advisory_lock`, IBKR TWS gateway connect lifecycle, storage readiness probe, starter-watchlist seeding, and health helper.

Sibling docs cover the other two worker sub-clusters:

- `docs/reality/components/worker-forecasting-and-decision-package.md` — universe resolver, calibration, forecasting step, historical bootstrap, label translator, market-data step, EODHD provider, decision-package composer + orchestration.
- `docs/reality/components/worker-actions-and-reconciliation.md` — action-draft composer + supersede, IBKR submission cluster (lifecycle, order builder, safety re-check, submitter, sweep), three reconciliation passes.

Intent reference: `docs/architecture.md` (the locked architecture doc).

## In-scope modules

All paths are under `apps/worker/src/portfolio_outlook_worker/`.

| Module | Role |
|---|---|
| `main.py` (131 lines) | entry point — `start_worker()` boots the scheduler |
| `config.py` (85 lines) | `Settings` + `StorageSettings` + `IbkrSettings` + `EodhdSettings` + `SchedulerSettings` (env prefix `WORKER_`) |
| `scheduler.py` (297 lines) | APScheduler `BackgroundScheduler` factory + the three jobs (pre_briefing 06:00, hourly 07–21, heartbeat 60 s) |
| `single_flight_lock.py` (101 lines) | Postgres `pg_advisory_lock` primitive (session-scoped) + in-memory test variant |
| `orchestrator.py` (469 lines) | `run_orchestrator(...)` — the per-fire main loop |
| `ibkr_gateway.py` (558 lines) | TWS connect lifecycle, account-mode tier-two guard, read-only `IbClientProtocol` |
| `storage_readiness.py` (101 lines) | live DB-probe readiness card |
| `starter_watchlist.py` (317 lines) | one-shot 12-row v1 starter seed (idempotent via `cold_start_seed_audit` UNIQUE) |
| `health.py` (13 lines) | `WorkerHealthResponse` + `get_worker_health()` |

## 1. Intent (`docs/architecture.md`)

Key bullets, all from `docs/architecture.md`:

- **Paper-only scope.** "Paper-only. / Geen live trading. / Geen broker execution. / Geen IBKR-verbinding in deze fase." (`docs/architecture.md:25-28`).
- **Audit + paper guardrail.** "Alle architectuurkeuzes ondersteunen eerst controleerbare paper workflows met volledige audittrail en zonder real-money uitvoering." (`docs/architecture.md:30-31`).
- **Execution modes enumerated.** `internal_paper`, `ibkr_paper`, `ibkr_live_read_only`, `ibkr_live_manual`, `blocked_auto`. "Automatische trading blijft geblokkeerd; blocked_auto is altijd blocked." (`docs/architecture.md:32`).
- **IBKR is reference-only.** "IBKR metadata blijft in reference contracts (geen live API-calls)." (`docs/architecture.md:32`).
- **Runtime/topology is contract-only.** "Contract-only update for backend runtime/service topology added in domain models … (no runtime implementation in this PR)." (`docs/architecture.md:40`).
- **Scheduler intent is planning-only.** "Contracts define planning only: plan -> eligibility -> skip/block/run status -> audit trace. Suggestion jobs require gezonde services en verse data; geen job voert trades uit." (`docs/architecture.md:41`).
- **No runtime activation in the API foundation step.** "Er is in deze stap geen runtime-integratie (geen broker, geen OpenAI, geen scheduler, geen worker-activatie)." (`docs/architecture.md:54`).
- **API + worker not wired to Postgres.** "API en worker zijn nog niet aan PostgreSQL gekoppeld." (`docs/architecture.md:99`).
- **DB readiness gates writes; only revision `0006` `migrations_current` unlocks.** (`docs/architecture.md:146-153`).

**Intent-vs-reality flag.** The architecture doc explicitly states "geen scheduler, geen worker-activatie" (`docs/architecture.md:54`) and "geen IBKR-verbinding in deze fase" (`docs/architecture.md:28`), yet the worker code under review **implements** both: APScheduler with two cron jobs (`scheduler.py:141-158`) and an IBKR TWS gateway with `ib_insync` (`ibkr_gateway.py:217-352`). The intent-doc lock is preserved at the *runtime-config-default* level only — both subsystems default to disabled (`config.py:33, 64`).

## 2. `main.py` — entry point

Module logger + log config (`main.py:32-33`); fixed `INFO` level.

`start_worker()` (`main.py:133-143`) is **synchronous** — there is no `asyncio` loop. The boot log line reports `environment`, `paper_only_mode`, `ibkr_enabled`, `scheduler_enabled` (`main.py:134-141`). Entry guard at `main.py:146-147` (`if __name__ == "__main__"`).

`_start_scheduler()` (`main.py:101-130`):

- Constructs `PortfolioScheduler(gateway, storage_settings, ibkr_settings, scheduler_settings)` (`main.py:107-113`).
- Calls `scheduler.start()` (`main.py:115`).
- Holds the instance in module-global `_active_scheduler` (`main.py:36, 102, 119`).
- Registers signal handlers `SIGTERM` (`main.py:128`) + `SIGINT` (`main.py:130`) bound to `_shutdown` → `_active_scheduler.stop()` (`main.py:121-125`). Both registrations wrap `suppress(ValueError)` to tolerate non-main-thread invocation.

`_try_connect_ibkr()` (`main.py:39-98`) — one-shot TWS connect at boot:

- Gated on `settings.ibkr.enabled` AND `settings.ibkr.account_id` set AND `storage.enabled` + non-empty `database_url` (`main.py:40-54`).
- Builds `StorageConnectionProvider` from `build_database_connection_settings(...)` (`main.py:61-64`).
- Inside `provider.checked_connection(require_writable=True)` (`main.py:66`), builds `SqlAlchemyIbkrConnectionAuditRepository` + `IbkrGateway` and calls `gateway.connect(host, port, client_id, account_id)` (`main.py:67-76`).
- Disconnects immediately after probe (`main.py:91-92`). Comment at `main.py:88-90`: "126b adds the durable worker-state row + sync loop that keeps the connection open."

## 3. Settings (`config.py`)

Env prefix `WORKER_`, nested delimiter `__`, `extra="ignore"` (`config.py:78-82`). Module-level singleton `settings = Settings()` (`config.py:85`).

Sub-models (`pydantic.BaseModel`):

- **`StorageSettings`** (`config.py:14-19`): `database_url: str | None = None`, `enabled: bool = False`, `writes_enabled: bool = False`.
- **`IbkrSettings`** (`config.py:22-37`): `enabled=False`, `host="127.0.0.1"`, `port=7497` (paper TWS), `client_id=1`, `account_id: str | None = None`. Docstring (`config.py:23-31`) is explicit: "**The port is NOT a mode indicator** — the configured account ID's prefix + a behavioural check are the locked detection mechanism per Task 126 product lock §2."
- **`EodhdSettings`** (`config.py:40-52`): `api_key`, `base_url="https://eodhd.com/api"`, `rate_limit_per_second=10`, `fetch_enabled=False`.
- **`SchedulerSettings`** (`config.py:55-66`): `enabled=False`, `timezone="Europe/Brussels"` (locked per V1.1 §22.2 morning-chain doctrine, comment `:60-62`), `heartbeat_interval_seconds=60`.

`Settings` (`BaseSettings`) at `config.py:69-82`: `service_name`, `environment`, `paper_only_mode=True`, plus the four nested sub-models. **No `@field_validator` / `@model_validator` decorators** in this file.

## 4. APScheduler (`scheduler.py`)

Module purpose (`scheduler.py:1-11`): "owns the locked 06:00 pre-briefing + hourly 07:00–21:00 cron jobs."

### `PortfolioScheduler` class (`scheduler.py:101-277`)

Constructor (`scheduler.py:111-128`): takes `gateway`, `storage_settings`, `ibkr_settings`, `scheduler_settings`, optional `worker_id` (default `f"worker_{uuid4().hex[:12]}"`, `:125`), optional `scheduler_factory` (`:126`).

`start()` (`scheduler.py:134-175`) is idempotent (`:135-136`). Builds the scheduler via `_build_scheduler(database_url, timezone)` and registers three jobs.

### Registered jobs

| Job | Trigger | Schedule | `job_id` | Target | File:line |
|---|---|---|---|---|---|
| Pre-briefing | `cron` | `hour=6, minute=0` Europe/Brussels | `"pre_briefing"` (`_PRE_BRIEFING_JOB_ID`, `:50`) | `_on_pre_briefing` → `run_orchestrator(run_type="pre_briefing")` | `scheduler.py:141-149, 201-202` |
| Hourly delta | `cron` | `hour="7-21", minute=0` Europe/Brussels | `"hourly"` (`_HOURLY_JOB_ID`, `:51`) | `_on_hourly` → `run_orchestrator(run_type="hourly_delta")` | `scheduler.py:150-158, 204-205` |
| Heartbeat | `interval` | `seconds=heartbeat_interval_seconds` (default 60) | `"heartbeat"` | `_heartbeat` | `scheduler.py:159-165` |

All three use `replace_existing=True` (`:148, :157, :164`).

### Job-store + lifecycle

`_build_scheduler` (`scheduler.py:280-301`) returns `BackgroundScheduler(jobstores=jobstores, timezone=timezone)` (`:301`). With a `database_url`, registers `SQLAlchemyJobStore(url=database_url, tablename="apscheduler_jobs")` under key `"default"` (`:295-300`); without, it falls back to APScheduler's in-memory default (`:294`).

`stop()` (`scheduler.py:177-184`): idempotent; `_scheduler.shutdown(wait=False)`.

### Misfire + coalesce + listeners

- **Misfire policy:** not configured — APScheduler defaults (1 s grace) apply. No `misfire_grace_time=` kwarg appears in this file.
- **Coalesce policy:** not configured — defaults apply (`coalesce=True` for cron triggers).
- **Listeners / error handlers:** **none.** No `add_listener(...)`, no `EVENT_JOB_ERROR` handler. The orchestrator catches its own exceptions and never re-raises (`orchestrator.py:421-446`), so listener-level wiring is absent by design.

### Per-fire wrapper `_run` (`scheduler.py:207-237`)

Each cron job fire:

1. Opens `StorageConnectionProvider.checked_connection(require_writable=True)` (`:217`).
2. Builds `_PositionSnapshotCounts(connection)` (`:221`) — concrete impl of the orchestrator's `_SnapshotCountsProtocol`. Two methods: `position_snapshot_count_for_account(...)` runs `SELECT COUNT(*) FROM ibkr_position_snapshots WHERE ibkr_account_id = :a OR account_ref = :a` (`scheduler.py:67-79`); `watchlist_item_count_for_account(...)` runs `SELECT COUNT(*) FROM watchlist_items WHERE status = 'active'` and silently returns 0 if the table doesn't exist (`scheduler.py:81-98`).
3. Builds the advisory lock via `_build_lock(connection)` → `PostgresAdvisoryLock(connection)` (`:222`, factory `:304-312`).
4. Calls `run_orchestrator(... lock=lock, ...)` (`:226-235`).
5. Storage-disabled fires log a warning and exit early without running the orchestrator (`:208-212`). `StorageConnectionError` on connection acquisition is caught + logged (`:236-237`).

### Heartbeat (`scheduler.py:239-270`)

Same `StorageConnectionProvider` pattern. Builds `SqlAlchemySchedulerStateRepository(connection, readiness)` (`:247-249`), computes `next_pre` + `next_hourly` from `self.next_runs()` filtered by `_is_pre_briefing_run` (which keys on `fire_time.hour == 6`, `:315-325`), and **upserts** `SchedulerStateEntry(worker_id, started_at, last_heartbeat_at, next_pre_briefing_at, next_hourly_at)` (`:260-268`). Initial heartbeat fires synchronously at end of `start()` (`:175`).

## 5. Single-flight lock (`single_flight_lock.py`)

Module purpose (`single_flight_lock.py:1-16`): "Task 127 product lock §3 — only one orchestrator run may execute at a time."

- **Stable key:** `ORCHESTRATOR_LOCK_KEY = 0x504F5F4F5243484F` (the 8-byte hash of `"PO_ORCHO"` packed as bigint) (`single_flight_lock.py:27-30`).
- **Protocol** (`:33-38`): `try_acquire() -> bool` (never blocks) + `release() -> None` (idempotent).
- **`InMemoryLock`** (`:41-56`) — process-local `threading.Lock` for tests.
- **`PostgresAdvisoryLock`** (`:59-101`) — production:
  - `try_acquire`: `SELECT pg_try_advisory_lock(:k)` (`:73-86`). Caches `_held` (`:85`).
  - `release`: returns early if not `_held` (`:89-90`); otherwise `SELECT pg_advisory_unlock(:k)` (`:91-97`); `_held` cleared in `finally` (`:100-101`).
  - **Scope:** Postgres **session**-scoped (`pg_advisory_lock`), not transaction-scoped — the orchestrator must keep the same connection open between `try_acquire` and `release` (docstring `:60-67`).
  - **Multi-process behaviour** (`:14-16`): "Two worker processes on the same Postgres database serialise their fires."
- **Acquisition timeout:** none. `pg_try_advisory_lock` returns boolean immediately (per protocol `:10-11`: "Never blocks.").
- **Release pattern:** manual `try_acquire` … `try/finally: release()` — the orchestrator releases in a `finally` block (`orchestrator.py:447-448`). Not a Python context manager.
- **Failure modes (fails closed):** any SQLAlchemy error on `pg_try_advisory_lock` → logged + returns `False` (`:81-83`) = treated as held by someone else.

## 6. Orchestrator main loop (`orchestrator.py`)

Module docstring (`orchestrator.py:1-27`): "performs the locked cold-start detection algorithm, writes one append-only audit row, and returns. **No other work** — no advice generation, no market data fetch, no discovery." (The current source has since grown to include market-data, forecasting, and decision-package steps — see §6.5 below.)

### Type literals

**`RunType`** (`orchestrator.py:50`):

```python
RunType = Literal["pre_briefing", "morning_briefing", "hourly_delta"]
```

**`ModeDetected`** — six values (`orchestrator.py:51-59`):

| Literal | File:line | When set |
|---|---|---|
| `"cold_start"` | `:52` | `ibkr_account_id is None` OR both position+watchlist counts are zero |
| `"normal"` | `:53` | Account known and either positions or watchlist non-empty |
| `"disconnected"` | `:54` | `gateway.is_connected()` returns False (or top-level exception) |
| `"skipped_locked"` | `:55` | Single-flight lock already held |
| `"skipped_disabled"` | `:56` | Declared in the literal but **never written** by `run_orchestrator` — see §6.5 |
| `"awaiting_watchlist_confirmation"` | `:58` | Task 128 — confirmation state is `"unconfirmed"` |

(There is **no** `"market_closed"` mode in the worker orchestrator — the `T-007` task spec's guess is incorrect.)

**`Outcome`** — two values (`orchestrator.py:60`): `"completed"` | `"error"`. There is no `"success"` / `"partial"` / `"failed"` / `"skipped"` — skip semantics ride on `mode_detected`.

### Protocols + result dataclass

- `_ConfirmationStateProtocol` (`:63-70`) — `get_state(ibkr_account_id) -> str | None`.
- `_SeedRunnerProtocol` (`:73-81`) — `seed(ibkr_account_id) -> bool`; idempotent.
- `_MarketDataRunnerProtocol` (`:84-94`) — `run(*, ibkr_account_id, run_type) -> dict[str, object]`; never raises.
- `_ForecastingRunnerProtocol` (`:97-106`) — `run(*, ibkr_account_id, scheduled_run_id) -> dict[str, object]`; never raises.
- `_CalibrationRunnerProtocol` (`:109-116`) — `run() -> dict[str, object]`; pre_briefing only.
- `_DecisionPackageRunnerProtocol` (`:119-133`) — composes Decision Packages, filtering out `Geblokkeerd` forecasts (`:124-127`).
- `_GatewayProtocol` (`:136-137`) — single method `is_connected() -> bool`.
- `_SnapshotCountsProtocol` (`:140-153`) — position + watchlist counts.

`OrchestratorResult` (frozen, `:156-164`): `run_id`, `run_type`, `mode_detected`, `outcome`, `duration_ms`.

### `run_orchestrator` signature (`orchestrator.py:183-200`)

Keyword-only. Required: `run_type`, `ibkr_account_id`, `gateway`, `snapshot_counts`, `audit_repo`, `lock`. Optional injectables: `now_provider`, `brussels_hour_provider`, `next_scheduled_at`, plus the five runner protocols (`confirmation_state`, `seed_runner`, `market_data_runner`, `forecasting_runner`, `calibration_runner`, `decision_package_runner`). Docstring (`:203-204`): "Never raises — every failure path lands in a `mode_detected` or `outcome='error'` audit row."

### Control flow per tick

1. **Start timer + generate run_id** — `run_id = f"srun_{uuid4().hex}"` (`:208-209`).
2. **Lock acquisition** — `if not lock.try_acquire()` → `mode_detected="skipped_locked"`, `outcome="completed"`, write audit, **return**. Lock not held — no release needed (`:212-233`).
3. **Run-type relabel for 07:00** — `_relabel_morning_briefing` (`:167-180`) flips `hourly_delta` to `morning_briefing` when `brussels_hour_provider() == 7` (`:237-240`).
4. **Gateway probe** — `if not gateway.is_connected()` → `mode_detected="disconnected"`, `outcome="completed"`, write audit, return (`:242-266`).
5. **Cold-start detection** — `ibkr_account_id is None` → `"cold_start"`; else read counts and decide `"cold_start"` vs `"normal"` (`:268-282`).
6. **Task 128 starter seed** — if `mode_detected == "cold_start"` and `seed_runner` wired, call `seed_runner.seed(ibkr_account_id)` (`:283-294`).
7. **Confirmation-state override** — if `state == "unconfirmed"` and `mode_detected != "cold_start"` → `"awaiting_watchlist_confirmation"` (`:296-310`).
8. **Market-data step** — only when `mode_detected=="normal"` AND `run_type in ("pre_briefing", "morning_briefing")` AND `market_data_runner` wired (`:312-330`).
9. **Forecasting step** — only when `mode_detected=="normal"` AND `run_type=="morning_briefing"` AND `forecasting_runner` wired (`:332-346`).
10. **Decision Package composition** — gated on forecasting success: `"error" not in forecast_details` AND same `mode_detected="normal"` + `run_type="morning_briefing"` (`:348-370`).
11. **Calibration step** — only when `mode_detected=="normal"` AND `run_type=="pre_briefing"` (`:372-383`).
12. **Audit-payload assembly + write** — folds runner dicts under keys `"market_data"`, `"forecast"`, `"decision_package"`, `"calibration"` into `error_details_json` (`:385-413`).
13. **Top-level exception handler** — catches everything from the body, writes `mode_detected="disconnected"`, `outcome="error"`, `error_details_json={"reason": "orchestrator_exception", ...}` (`:421-446`).
14. **Lock release** — `lock.release()` in `finally:` (`:447-448`). Runs after both success and exception paths; `skipped_locked` bypasses this (no lock held).

### 6.5 Where the orchestrator stops

`run_orchestrator` invokes market-data → forecasting → decision-package → calibration. It **does not invoke** action-draft composition, IBKR submission, lifecycle handling, or reconciliation — those packages (`action_draft/`, `ibkr_submission/`, `ibkr_reconciliation/`) exist in the worker tree but are wired into the scheduler **separately** (the submission sweep and reconciler register their own APScheduler jobs — see sibling doc `worker-actions-and-reconciliation.md`).

The `skipped_disabled` literal is **declared but never written** (`orchestrator.py:56`). The scheduler's storage-off early-return (`scheduler.py:208-212`) doesn't even invoke the orchestrator, so no audit row is written there.

### `_safe_append` (`orchestrator.py:455-469`)

Wraps every `audit_repo.append(entry)` call. Catches all storage exceptions and logs `"failed to persist scheduled-run audit row"` — **never re-raises** (`:466-469`). Comment (`:459-464`): "the only honest move is to log the failure and move on. APScheduler's next fire will try again."

### Outcome ↔ mode summary

| `mode_detected` | `outcome` | File:line |
|---|---|---|
| `skipped_locked` | `completed` | `orchestrator.py:213-233` |
| `disconnected` (gateway down) | `completed` | `orchestrator.py:244-266` |
| `cold_start` / `awaiting_watchlist_confirmation` / `normal` | `completed` | `orchestrator.py:400-413` |
| `disconnected` (top-level exception) | `error` | `orchestrator.py:424-446` |

## 7. IBKR gateway (`ibkr_gateway.py`)

Module purpose (`ibkr_gateway.py:1-21`): "The worker is the only component that opens a long-lived TWS API session; the API reads worker-persisted state via the storage layer."

### Type definitions

- `AccountMode = Literal["paper", "live", "unknown"]` (`ibkr_gateway.py:39`).
- `_PAPER_PREFIXES = ("DU", "DF")` — Task 126 §2 primary detection (`:44`).
- `_mode_from_prefix(account_id)` (`:121-129`): empty → `"unknown"`; uppercase startswith `("DU","DF")` → `"paper"`; else `"live"`.

### Protocols + dataclasses

- `_AuditRepoProtocol` (`:47-50`).
- `IbClientProtocol` (`:53-75`) — structural Protocol subset of `ib_insync.IB`. Permissive `*args/**kwargs` so it accepts both the real `IB()` and lightweight test fakes (`:56-62`). **Read-only methods only**: `connect, disconnect, isConnected, managedAccounts, reqContractDetails, accountSummary, positions`. **No `placeOrder` / `cancelOrder` / `reqOpenOrders`.**
- `CashSummaryRow` (frozen, `:78-83`), `AccountSummary` (frozen, `:86-91`), `Position` (frozen, `:94-106`), `IbkrConnectionResult` (frozen, `:108-118`).

### `IbkrGateway` class

Constructor (`:169-183`): default factory `_default_ib_factory` lazily imports `ib_insync.IB` (`:531-542`). Holds `_ib, _account_id, _account_mode, _connection_id, _verified_at` (`:179-183`).

### Connect flow (`ibkr_gateway.py:187-352`)

1. **Account-id presence check** (`:197-206`): empty → `_refuse(...)` with Dutch "IBKR_ACCOUNT_ID ontbreekt…" (`:201-205`).
2. **`connect_attempt` audit row** (`:208-217`).
3. **TWS connect** (`:219-221`): `client.connect(host, port, clientId=client_id, readonly=True)` — **`readonly=True` flag**. No `nextValidId` wait (handled by `ib_insync` internally).
4. **Connect-failure path** (`:222-245`): catches all exceptions, writes `connect_refused` audit with `{"reason": "tws_connect_failed", "message": ...}`.
5. **`managedAccounts()` validation** (`:247-273`): if `account_id not in managed`, disconnect + write `connect_refused` with `{"reason": "account_not_managed", "managed_accounts": [...]}`.
6. **Tier-one — prefix-based mode check** (`:275-284`): writes `mode_check_prefix` audit row with `account_mode_detected=prefix_mode`.
7. **Tier-two — behavioural mode check** (`:286-295, 468-500`): probes the live-only contract `Future(symbol="MES", lastTradeDateOrContractMonth="20990101", exchange="CME")` via `client.reqContractDetails(probe)` (`:484-495`). Empty list → `"paper"`; non-empty → `"live"`; any exception → `"paper"` (`:496-500`). Writes `mode_check_behavioural` audit row.
8. **Disagreement guard** (`:297-324`): if `prefix_mode != behavioural_mode` → disconnect + write `connect_refused` with `{"reason": "mode_check_disagreement", "prefix_mode": ..., "behavioural_mode": ...}`. **This is the "tier-two paper-account guard"** — both checks must agree.
9. **Success path** (`:326-352`): `connection_id = f"ibkr_{uuid4().hex[:12]}"` (`:326`). Writes `connect_success` audit. Caches all five session fields. Returns `IbkrConnectionResult(connected=True, ..., audit_ids=(...))` with the five audit_ids collected along the way.

### Disconnect (`ibkr_gateway.py:354-373`)

Early-return if `_ib is None`. Calls `_ib.disconnect()` in `try`. In `finally`: writes a `disconnect` audit row (only if `_account_id` set) and clears all five cached fields.

### Reconnection

**None.** No retry loop, no reconnect helper. `is_connected()` (`:375-381`) just delegates to `_ib.isConnected()` with defensive `try/except` returning `False`. `main.py:88-90` comment: "126b adds the durable worker-state row + sync loop that keeps the connection open" — reconnection is deferred.

### Audit row emitter (`_append_audit`, `:502-528`)

Builds `IbkrConnectionAuditRecord(audit_id=f"icaudit_{uuid4().hex}", event_at=self._clock(), ...)` and calls `_audit_repo.append(record)` inside `try/except` — failures log and return `None` (`:523-528`).

**Event types emitted:** `connect_attempt`, `connect_refused`, `mode_check_prefix`, `mode_check_behavioural`, `connect_success`, `disconnect`.

### Read methods

- `get_account_mode()` (`:383-393`) — returns `"unknown"` if disconnected, else cached `_account_mode`. Comment cites Task 126 §2: re-read per call so a stale session never reports confident mode after the underlying connection dropped.
- `fetch_account_summary()` (`:395-418`) — iterates `_ib.accountSummary(account)`, wraps each entry in `CashSummaryRow` with `_decimal_or_zero(raw_value)`. Returns `AccountSummary` with `as_of=self._clock()`.
- `fetch_positions()` (`:420-440`) — iterates `_ib.positions(account)`, extracts `(conid, symbol, exchange, currency, quantity, avg_cost)` with the same Decimal-via-string helper.

### Decimal-as-string boundary

`_decimal_or_zero(value)` (`:132-148`) — preserves precision via string parsing; never falls back to `float`. Doctrine comment at `:133-137`.

## 8. Storage readiness probe (`storage_readiness.py`)

Entry point `build_worker_storage_readiness(...)` (`storage_readiness.py:34-101`).

Returns `WorkerStorageReadiness` Pydantic model (`:20-27`): `configured`, `connected`, `safe_to_write`, `status_nl`, `message_nl`, `migration_readiness_status`, `writes_status_nl`.

Default `readiness_checker` is `check_online_migration_readiness` from `ai_trading_agent_storage` (`:37`).

Branches:

- Storage disabled → `configured=False`, `status_nl="Niet geconfigureerd"`, "Opslag staat uit." (`:39-48`).
- URL missing → `configured=False`, "Database-url ontbreekt." (`:50-60`).
- Connection failure (`SQLAlchemyError | ValueError`) → builds a `database_not_connected` report, `connected=False`, "Database niet bereikbaar" (`:67-81`); `finally` block closes the connection + disposes the engine (`:82-86`).
- Successful probe → `safe_to_write = migration_readiness_is_safe_to_write(readiness)` (`:88`); `status_nl="Verbonden"` if connected else "Niet verbonden" (`:93`); `message_nl="Migraties klaar"` if `MIGRATIONS_CURRENT` else "Migraties niet klaar" (`:94-98`); `writes_status_nl="Writes toegestaan"` iff `safe_to_write` (`:100`).

"Ready" requires: `storage_settings.enabled` AND non-empty URL AND engine connects AND `migration_readiness_is_safe_to_write(...)` (which per `docs/architecture.md:152-153` means `migrations_current` on revision `0006`).

**Not called from `main.py` or `scheduler.py`** — this is a status-surface helper consumed by an API endpoint. The worker boot uses `StorageConnectionProvider.checked_connection(require_writable=True)` directly (`main.py:66`, `scheduler.py:217, 246`).

## 9. Starter watchlist (`starter_watchlist.py`)

Entry point `seed_starter_watchlist(...)` (`starter_watchlist.py:183-307`). Returns `SeedResult(already_seeded, seeded_count, failed_symbols)` (`:174-180`).

### The 12-row v1 starter set (`STARTER_WATCHLIST_V1`, `:66-154`)

Exactly **12 entries** matching the locked v1 set (`:5-11`):

- **5 broad UCITS ETFs** (`:67-102`): SXR8 (iShares Core S&P 500), VWCE (Vanguard FTSE All-World), EQQQ (Invesco Nasdaq-100), EXSA (iShares Stoxx 600), AGGH (Xtrackers Global Aggregate Bond) — all XETRA, EUR.
- **5 European blue chips** (`:103-138`): ASML (AEB, EUR), MC/LVMH (SBF, EUR), NOVO-B (CPH, DKK), SAP (XETRA, EUR), SHEL (LSE, GBP) — all STK.
- **2 sector UCITS ETFs** (`:139-153`): WTEC (WisdomTree Cybersecurity), IS3N (iShares MSCI World Healthcare) — both XETRA, EUR.

### Tables written

- `watchlist_items` → `watchlist_seed_repo.append(WatchlistItemSeedRecord(..., source="cold_start_seed", is_starter_seed=True, seed_version="v1"))` (`:235-260`).
- `cold_start_seed_audit` → `seed_audit_repo.append(...)` (`:264-273`).
- `watchlist_confirmation_state` → `confirmation_state_repo.upsert(WatchlistConfirmationStateRecord(state="unconfirmed", ...))` (`:282-288`).
- `watchlist_confirmation_audit` → `confirmation_audit_repo.append(WatchlistConfirmationAuditEntry(from_state="absent", to_state="unconfirmed", actor="system", ...))` (`:289-301`).

### Idempotency

- Module docstring (`:1-7`): "at most once per `ibkr_account_id` (idempotency enforced by the `cold_start_seed_audit` table's `UNIQUE` on `ibkr_account_id`)."
- Explicit pre-check at entry (`:210-217`): if `seed_audit_repo.find_by_account_id(ibkr_account_id)` returns a row → `SeedResult(already_seeded=True, ...)` without touching the watchlist.
- Race handler: if a concurrent process inserts the audit row first, `seed_audit_repo.append(...)` raises `ColdStartAlreadySeededError` and the function returns `already_seeded=True` with the local `seeded_count` (`:274-279`).
- Per-asset failure handling (`:223-259`): if `listing_resolver.find_listing(...)` returns `None`, the symbol is appended to `failed` and skipped; the seed continues. Failures serialised into `failed_conids_json` on the audit row (`:270`).

**Not yet wired** into the orchestrator's `seed_runner` slot within the files reviewed — the production wiring is a follow-up integration.

## 10. Health helper (`health.py`)

13 lines. `WorkerHealthResponse(BaseModel)` with `status`, `service`, `mode` (`health.py:6-9`). `get_worker_health()` returns a fixed `WorkerHealthResponse(status="ok", service="worker", mode="paper-only")` (`:12-13`). No readiness check, no dependency probe — pure constant.

## 11. Cross-cutting observations

- **Intent vs reality drift on scheduler + IBKR.** `docs/architecture.md:28, 41, 54` says "no scheduler, no IBKR connection in this phase"; the code implements both, gated by `WORKER_SCHEDULER__ENABLED=false` and `WORKER_IBKR__ENABLED=false` defaults (`config.py:33, 64`).
- **`ModeDetected` has six values, not five.** The task spec missed `"awaiting_watchlist_confirmation"` (Task 128, `orchestrator.py:58`); `"skipped_disabled"` is declared but never written; `"market_closed"` does not exist.
- **`Outcome` has only two values** (`completed`, `error`). Skip semantics ride on `mode_detected`.
- **Orchestrator stops after Decision Package composition.** Action-draft / submission / reconciliation packages exist but are wired into the scheduler separately — see `worker-actions-and-reconciliation.md`.
- **No order authority in this cluster.** `ibkr_gateway.py` connects `readonly=True` (`:221`) and its `IbClientProtocol` exposes only read methods (`:53-75`). No `placeOrder` / `cancelOrder` in any of the 9 files in this doc.
- **Single-flight lock is Postgres session-scoped, not transaction-scoped.** The orchestrator and the lock share one SQLAlchemy `Connection` for the duration of one fire (`scheduler.py:217-235`, `single_flight_lock.py:60-67`).
- **`starter_watchlist.seed_starter_watchlist` is not wired** into the orchestrator's `seed_runner` slot within the files reviewed — production wiring is a follow-up.
- **No APScheduler event listener.** Cron job failures land only in per-fire audit rows + log lines; APScheduler is not informed and there is no recovery hook.
- **No `extra="forbid"` at any boundary.** `Settings` is `extra="ignore"` (`config.py:80`). All Pydantic models in this cluster use defaults.
