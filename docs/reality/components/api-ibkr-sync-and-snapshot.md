# `apps/api` — IBKR sync and snapshot

**Phase:** 1a (reality components)
**Task:** T-004
**Scope:** twelve modules in `apps/api/src/portfolio_outlook_api/` that implement the manual, read-only IBKR sync path and the lighter "account snapshot preflight" path. They sit above `packages/storage`'s `SqlAlchemyIbkrSyncSnapshotRepository` and below the FastAPI router layer.

This file is descriptive. Every claim cites `path/to/file.py:NNN`. Non-trivial claims carry 3–10 line excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

- `ibkr_sync.py` — sync orchestrator (`run_sync`, `read_status`) + in-memory `STORE`.
- `ibkr_sync_adapter_factory.py` — five-gate factory for the real ibapi sync adapter.
- `ibkr_sync_contracts.py` — `IbkrPosition`, `IbkrCash`, `IbkrOpenOrder`, `IbkrExecution`, `IbkrReadOnlyAdapter`.
- `ibkr_sync_persistence.py` — record mappers + `persist_ibkr_sync_payload` (writes five tables).
- `ibkr_sync_read_model.py` — Decimal/datetime serialisers + `read_latest_ibkr_sync_run`.
- `ibkr_sync_readiness.py` — multi-tier readiness ladder (`blocked` / `needs_control` / `ready_for_manual_readonly_sync`).
- `ibkr_sync_validation.py` — payload validator with per-kind dedup and Dutch error codes.
- `ibkr_account_snapshot_persistence.py` — preflight→persistence mapping (writes three tables).
- `ibkr_account_snapshot_preflight.py` — preflight result + readiness skeleton (currently always-blocked).
- `ibkr_market_data.py` — IBKR market-data adapter skeleton + `MarketDataLatestSnapshotRecord` builder.
- `ibkr_ibapi_sync_client.py` — `IbapiReadOnlySyncClient` (read-only EClient/EWrapper, ~676 lines).
- `ibkr_ibapi_account_snapshot_client.py` — snapshot dataclasses + masking + decimal-or-text parsing.

## `ibkr_sync.py` (461 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_sync.py`

### Public surface

- `NotConfiguredIbkrAdapter` — disabled-stub adapter returning empty lists for all four sync methods (`:36-47`).
- `InMemoryIbkrSyncStore` + module-level `STORE` — in-process accumulator for runs, positions, cash, open_orders, executions (`:50-59`).
- `run_sync(settings, adapter=None, *, session_status_adapter=None) -> dict[str, object]` — the orchestrator (`:106-395`).
- `read_status(settings, readiness=None) -> dict[str, object]` (`:402-460`).

### Collaborators

`Settings`, `IbkrSessionStatusAdapter`, `build_ibkr_status_placeholder` (`:13-15`). Sync persistence + validation modules (`:23-33`). `SqlAlchemyIbkrSyncSnapshotRepository`, `StorageConnectionProvider`, `build_database_connection_settings`, `StorageConnectionError` from `ai_trading_agent_storage` (`:6-11`).

### Persistent-state implications

Writes via `SqlAlchemyIbkrSyncSnapshotRepository` to: `ibkr_sync_runs`, `ibkr_account_cash_snapshots`, `ibkr_position_snapshots`, `ibkr_open_order_snapshots`, `ibkr_execution_snapshots` (repo wired at `:87-91`; per-table calls inside `persist_ibkr_sync_payload`). Writes happen only when `storage.enabled`, `storage.database_url` set, `storage.writes_enabled` true, and the readiness/preflight gate passed; otherwise falls back to `STORE` only (`:71-93, :303-376`).

### Notable choices

- **Hard readiness gate** before any work — if `sync_readiness_status != "ready_for_manual_readonly_sync"`, returns a blocked status payload and persists nothing (`:112-142`).
- After fetching, runs `validate_ibkr_sync_payloads`; aborts persistence on failure with `"Adapterpayload ongeldig; niets opgeslagen."` (`:184-218`).
- Three persistence modes communicated to UI: `"durable"`, `"memory"`, `"none"` with explicit Dutch fall-back strings (`:303-389`).
- Connection-context lifetime is manual: `__enter__()` outside try, `__exit__(None,None,None)` in `finally` (`:84-91, :372-374`).
- `read_status` always returns `actions_allowed=False`, `order_submission_allowed=False`, `order_modification_allowed=False`, `order_cancellation_allowed=False`, `suggestions_allowed=False`, `can_submit_orders=False`, `safe_for_orders=False`, `blocks_orders=True` (`:452-460`).

```python
# ibkr_sync.py:71-93
def _resolve_repo(
    settings: Settings, *, require_writable: bool,
) -> tuple[SqlAlchemyIbkrSyncSnapshotRepository | None, object | None, str]:
    storage = settings.storage
    if not storage.enabled:
        return None, None, "Storage staat uit; alleen geheugenopslag actief."
    ...
    provider = StorageConnectionProvider(build_database_connection_settings(storage.database_url))
    try:
        checked = provider.checked_connection(require_writable=require_writable)
        context = checked.__enter__()
        repo = SqlAlchemyIbkrSyncSnapshotRepository(context.connection, context.readiness)
        return repo, checked, ""
    except StorageConnectionError:
        return None, None, "Storage niet beschikbaar; alleen geheugenopslag actief."
```

## `ibkr_sync_adapter_factory.py` (64 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_sync_adapter_factory.py`

### Public surface

`build_real_sync_adapter(settings, *, app=None) -> IbkrReadOnlyAdapter | None` (`:23-63`).

### Notable choices

Five hard gates, all returning `None` (`:42-54`): `ibkr_sync_real_client_enabled`, `ibkr_sync_enabled`, `account_mode == "paper"`, `ibkr_sync_readonly`, host+port+client-id present. Returns `None` (not an empty adapter) so callers distinguish "no real client" from "real client returned nothing" (`:8-11`). Optional `app` parameter for ibapi test injection (`:39-40, :62`).

## `ibkr_sync_contracts.py` (89 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_sync_contracts.py`

### Public surface

Frozen dataclasses: `IbkrPosition` (`:8-18`), `IbkrCash` (`:21-27`), `IbkrOpenOrder` (`:30-53`), `IbkrExecution` (`:56-74`). Abstract `IbkrReadOnlyAdapter` (`:77-88`) with four `NotImplementedError` methods: `sync_account_summary`, `sync_positions`, `sync_open_orders`, `sync_executions`.

### Notable choices

- All money-bearing fields typed `Decimal` / `Decimal | None` (no floats).
- `IbkrOpenOrder` includes split `filled_quantity` + `remaining_quantity` (`:49-50`) and opaque `raw_status_reference: str | None` (`:53`) for provenance.
- `IbkrExecution` carries UTC-naive `execution_time: datetime` (`:70`) and optional `commission`, `commission_currency`, `realized_pnl`, `raw_execution_reference` (`:71-74`).

## `ibkr_sync_persistence.py` (252 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_sync_persistence.py`

### Public surface

- `IbkrSyncPersistenceRepository` Protocol declaring five `save_*` methods (`:27-52`).
- `IbkrSyncPersistencePayload(sync_run, cash_snapshots, position_snapshots, open_order_snapshots, execution_snapshots)` (`:55-61`).
- Mapping helpers: `map_sync_run_record` (`:72-121`), `map_cash_snapshot_record` (`:124-142`), `map_position_snapshot_record` (`:145-168`), `map_open_order_snapshot_record` (`:171-206`), `map_execution_snapshot_record` (`:209-239`).
- `persist_ibkr_sync_payload(payload, repository)` (`:242-251`).
- Customisable `SnapshotIdFactory = Callable[[], str]` defaulting to `uuid4` (`:24, :68-69`).

### Notable choices

- **Writes five table sets in fixed order**: `ibkr_sync_runs`, `ibkr_account_cash_snapshots`, `ibkr_position_snapshots`, `ibkr_open_order_snapshots`, `ibkr_execution_snapshots` (`:247-251`).
- `map_sync_run_record` hard-codes safety booleans `actions_allowed=False`, `order_submission_allowed=False`, `order_modification_allowed=False`, `order_cancellation_allowed=False`, `suggestions_allowed=False` on every persisted run (`:115-119`).
- Position `conid` int is coerced to `str` before persistence (`:153`).
- Snapshot IDs are fresh `uuid4` every map call; idempotency lives at the `sync_run_id` grain.

```python
# ibkr_sync_persistence.py:242-251
def persist_ibkr_sync_payload(
    payload: IbkrSyncPersistencePayload,
    repository: IbkrSyncPersistenceRepository,
) -> None:
    sync_run_id = payload.sync_run.sync_run_id
    repository.save_ibkr_sync_run(payload.sync_run)
    repository.save_ibkr_account_cash_snapshots(sync_run_id, payload.cash_snapshots)
    repository.save_ibkr_position_snapshots(sync_run_id, payload.position_snapshots)
    repository.save_ibkr_open_order_snapshots(sync_run_id, payload.open_order_snapshots)
    repository.save_ibkr_execution_snapshots(sync_run_id, payload.execution_snapshots)
```

## `ibkr_sync_read_model.py` (145 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_sync_read_model.py`

### Public surface

- Serializers: `serialize_sync_status_record` (`:34-70`), `serialize_position_record` (`:73-78`), `serialize_cash_record` (`:81-86`), `serialize_open_order_record` (`:89-96`), `serialize_execution_record` (`:99-106`).
- `DurableIbkrSyncReadResult(latest_run, storage_help_nl)` (`:109-113`).
- `read_latest_ibkr_sync_run(storage)` (`:115-144`).

### Notable choices

- **Read-only** — `require_writable=False` (`:131`); calls `repo.get_latest_ibkr_sync_run()` on `ibkr_sync_runs` (`:137`).
- Serialised status always returns `actions_allowed=False`, `order_submission_allowed=False`, `order_modification_allowed=False`, `order_cancellation_allowed=False`, `suggestions_allowed=False`, `can_submit_orders=False`, `safe_for_orders=False`, `blocks_orders=True` (`:62-69`).
- Storage Decimals/datetimes are stringified (ISO 8601 for datetimes, `str(Decimal)` for money) (`:22-31`).

## `ibkr_sync_readiness.py` (103 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_sync_readiness.py`

### Public surface

`build_ibkr_sync_readiness(settings, session_status) -> dict[str, object]` (`:6-102`).

### Notable choices

- Multi-tier ladder: `blocked` → `needs_control` → `ready_for_manual_readonly_sync` with explicit `reason` codes (`:24-77`).
- **Account-mode mismatch is intentionally not a blocker since V1 §21.1 relock** — comment documents the explicit policy change (`:44-48`). Mode is reported, not gated.
- Connection statuses that block: `connection_failed`, `authentication_required`, `pacing_limited`, `connected_wrong_account_mode`, `unknown` (`:49-59`).
- Status-check disabled / "session not attempted" demote to `needs_control` instead of `blocked` (`:60-68`).
- Returns hard `actions_allowed=False`, `order_submission_allowed=False`, `order_modification_allowed=False`, `order_cancellation_allowed=False`, `suggestions_allowed=False`, `can_submit_orders=False`, `safe_for_orders=False`, `blocks_orders=True`, `safe_for_sync=False`, `readonly_required=True` (`:89-101`).

```python
# ibkr_sync_readiness.py:44-77
# V1 §21.1 relock: account-mode is reported, not gated. The
# previous `version1_paper_only` / `account_mode_mismatch`
# blockers used to fail readiness when the connected account did
# not match the operator's expected mode; both gates are removed.
# The dashboard renders the actual mode IBKR reports as a badge.
elif connection_status in {
    "connection_failed", "authentication_required",
    "pacing_limited", "connected_wrong_account_mode", "unknown",
}:
    status = "blocked"
    ...
elif session_ready and settings_ready and readonly_configured and storage_ready:
    status = "ready_for_manual_readonly_sync"
```

## `ibkr_sync_validation.py` (326 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_sync_validation.py`

### Public surface

- `PayloadValidationError(payload_kind, item_index, field_name, reason_code, message_nl)` frozen dataclass (`:19-25`).
- `PayloadValidationResult(passed, errors)` (`:28-31`).
- `validate_ibkr_sync_payloads(cash_items, positions, open_orders, executions) -> PayloadValidationResult` (`:49-325`).

### Notable choices

- Restricted allow-lists: `_ALLOWED_SECURITY_TYPES = {"STK", "ETF"}` (`:14`), `_ALLOWED_ORDER_SIDES = {"BUY", "SELL"}` (`:15`), `_ALLOWED_EXECUTION_SIDES = {"BUY", "SELL", "BOT", "SLD"}` (`:16`).
- Currency = three uppercase letters (`:34-35`).
- Per-kind dedup keys: positions `(account_ref, symbol, security_type)` (`:78, :127`); open orders by `ibkr_order_id` (`:139, :231`); executions by `execution_id` (`:242, :314`). Duplicate detection appends a per-row error (`duplicate_identity`, `duplicate_order_id`, `duplicate_execution_id`).
- Quantity rules differ by record: positions must be `Decimal` and non-negative (`:104`); open orders and executions require `Decimal > 0` (`:185, :281`).
- Error messages are Dutch-only NL strings.

## `ibkr_account_snapshot_persistence.py` (178 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_account_snapshot_persistence.py`

### Public surface

- `IbkrAccountSnapshotPersistenceRepository` Protocol with three save methods (`:27-40`).
- `IbkrAccountSnapshotPersistencePayload(sync_run, cash_snapshots, position_snapshots)` (`:43-47`).
- `map_preflight_to_persistence_payload(preflight, *, sync_run_id, persisted_at=None, snapshot_id_factory=...)` (`:62-118`).
- `map_cash_preflight_item(...)` (`:121-138`), `map_position_preflight_item(...)` (`:141-162`).
- `persist_account_snapshot_preflight_payload(repository, payload)` (`:165-177`).

### Notable choices

- **Writes three tables in order**: `ibkr_sync_runs`, `ibkr_account_cash_snapshots`, `ibkr_position_snapshots` (`:169-177`). Does **not** touch `ibkr_open_order_snapshots` or `ibkr_execution_snapshots` (snapshot path is account-state only).
- The synthetic `IbkrSyncRunRecord` hard-codes `readonly=True`, `open_orders_status="not_requested"`, `executions_status="not_requested"`, `open_orders_count=0`, `executions_count=0`, plus all five `*_allowed`/`suggestions_allowed=False` (`:70-98`).
- **Tag-routed cash mapping** (`:131-138`): only `TotalCashValue` tag fills `cash`; `AvailableFunds` fills `available_funds`; `BuyingPower` fills `buying_power`; all others land as `None`.
- Persisted `account_ref` on positions is the **masked** account id (`:151`).

## `ibkr_account_snapshot_preflight.py` (104 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_account_snapshot_preflight.py`

### Public surface

- `IbkrAccountSnapshotPreflightResult` frozen dataclass with 30+ fields including `status`, allowed/blocked flags, NL messages, account-mode hints, request/cancel flags, captured `cash_items` and `positions` tuples, completeness flags, `persisted`, valuation/market-data flags, and `suggestions_allowed=False`, `action_drafts_allowed=False`, `orders_allowed=False`, `order_submission_allowed=False`, `order_modification_allowed=False`, `order_cancellation_allowed=False`, `can_submit_orders=False`, `safe_for_orders=False`, `blocks_orders=True` (`:12-49`).
- `run_manual_readonly_account_snapshot_preflight(settings, runtime_client)` (`:80-95`).
- `build_manual_readonly_account_snapshot_preflight_readiness(settings, runtime_client)` (`:98-103`).

### Notable choices

Both public functions currently return a `_base_blocked(...)` result with reason `"snapshot_preflight_completed"` (executor) or `"manual_snapshot_ready"` (readiness). The actual preflight conversation against `runtime_client` is **not implemented** in this skeleton — call shape is validated, but no IBKR I/O happens.

## `ibkr_market_data.py` (113 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_market_data.py`

### Public surface

- `IbkrMarketDataSettings` frozen dataclass (`:19-29`).
- `settings_from_runtime(settings) -> IbkrMarketDataSettings` (`:32-43`).
- `IbkrMarketDataAdapter` with `fetch_latest_snapshot(identity) -> MarketDataFetchResult` (`:46-65`).
- `build_storage_record(snapshot, status, explanation_nl) -> MarketDataLatestSnapshotRecord` (`:78-113`).

### Notable choices

- Adapter is a **deliberate skeleton**: even when `_is_configured()` passes it returns `PROVIDER_ERROR` with Dutch "IBKR marktdata-adapter skeleton actief; providerkoppeling nog niet geïmplementeerd." (`:60-65`).
- `_is_configured` enforces `enabled and readonly and account_mode == "paper"` and host/port/client-id present (`:67-75`).
- Identity validation delegated to `block_if_identity_invalid` (`:51-53`).
- No direct DB write — constructs `MarketDataLatestSnapshotRecord` (for `market_data_latest_snapshots` table) with hard-False `safe_for_analysis`, `safe_for_suggestions`, `safe_for_action_drafts` (`:110-112`), hard-coded `freshness_status="fresh"` (`:105`), and `request_log_id=None`, `provider_source_id=None`, `freshness_audit_id=None` (`:107-109`).

## `ibkr_ibapi_sync_client.py` (676 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_ibapi_sync_client.py`

### Public surface

- `CONNECTION_ERROR_CODES = frozenset({502, 504, 1100, 1101, 1102, 1300, 2110})` (`:38`).
- `IbapiSyncAppProtocol` declaring `connect`, `isConnected`, `disconnect`, `run`, `reqAccountSummary`, `cancelAccountSummary`, `reqPositions`, `cancelPositions`, `reqAllOpenOrders`, `reqExecutions` (`:41-64`).
- Internal row dataclasses: `_AccountSummaryRow` (`:67-72`), `_PositionRow` (`:75-85`), `_OpenOrderRow` (`:88-110`), `_ExecutionRow` (`:113-130`), `_SyncSessionState` (`:133-144`).
- `build_sync_callbacks(state, lock)` (`:198-374`).
- `IbapiReadOnlySyncClient(IbkrReadOnlyAdapter)` (`:377-558`) with `sync_account_summary`, `sync_positions`, `sync_open_orders`, `sync_executions`, `close`, context-manager support.
- `real_sync_client_session(client)` (`:561-574`).

### Notable choices

- **Read-only API surface only.** The Protocol intentionally **does not** declare `placeOrder` / `cancelOrder` (grep confirms zero matches in this file).
- Connection established lazily in `_ensure_connected`; one daemon ibapi event thread `name=f"ibapi-sync-{self._client_id}"` (`:439-462`).
- Per-request blocking with `threading.Event`; `_wait_or_raise` raises `TimeoutError(f"{label}_timeout")` and propagates fatal errors (`:464-468`).
- **Try/finally cancel pattern**: `reqAccountSummary` paired with `cancelAccountSummary`; `reqPositions` paired with `cancelPositions`; cancel-time exceptions ignored (`:476-500`).
- `error()` callback maps any of seven IBKR codes to `fatal_error = IbkrTwsReadonlyAdapterError("connection_failed")` and forces all done-events to set, unblocking waiters (`:339-361`).
- Dynamic class mixes `EWrapper` and `EClient`; `__init__` calls `EClient.__init__(self, self)` so the wrapper is its own client wrapper (`:418-437`).
- Quantity / cost / time parsing tolerates `None`, `""`, `"nan"`, and multiple IBKR datetime formats (`:147-188`). Decimals never become floats; `_parse_decimal_required` defaults to `Decimal("0")` rather than raising (`:162-166`).

```python
# ibkr_ibapi_sync_client.py:339-361
def error(_inner_self, req_id, error_code, error_string, *_extra):
    if error_code in CONNECTION_ERROR_CODES:
        state.fatal_error = IbkrTwsReadonlyAdapterError("connection_failed")
        for event in (
            state.account_summary_done, state.positions_done,
            state.open_orders_done, state.executions_done,
        ):
            event.set()
    else:
        logger.debug(...)
```

## `ibkr_ibapi_account_snapshot_client.py` (42 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_ibapi_account_snapshot_client.py`

### Public surface

- `IbkrAccountCashPreflightItem(tag, currency, value, source, parse_status)` (`:7-13`).
- `IbkrPositionPreflightItem(account_mode, masked_account_id, symbol, sec_type, currency, exchange, primary_exchange, con_id, quantity, average_cost, source)` (`:16-28`).
- `mask_account_id(account_id) -> str` (`:31-35`).
- `parse_decimal_or_text(value) -> tuple[Decimal | str, str]` (`:38-42`).

### Notable choices

The "client" in the name is misleading — this module contains **no ibapi connection logic**, only the snapshot data types and account-ID masking. Masking: ≤3 chars → `"***"`; else first-two + `"****"` + last-three. `parse_decimal_or_text` returns `(Decimal, "parsed")` or `(stripped_str, "unparsed")` on `InvalidOperation`/`ValueError`.

## Storage write-path map

| Module | Repository used | Tables written |
|---|---|---|
| `ibkr_sync.py` | `SqlAlchemyIbkrSyncSnapshotRepository` (`:87-91, :367`) | `ibkr_sync_runs`, `ibkr_account_cash_snapshots`, `ibkr_position_snapshots`, `ibkr_open_order_snapshots`, `ibkr_execution_snapshots` |
| `ibkr_sync_persistence.py` | Caller-supplied repo (in practice `SqlAlchemyIbkrSyncSnapshotRepository`) | Same five tables, sequenced at `:247-251` |
| `ibkr_sync_read_model.py` | `SqlAlchemyIbkrSyncSnapshotRepository` with `require_writable=False` (`:131-138`) | **Read only** — `ibkr_sync_runs` |
| `ibkr_account_snapshot_persistence.py` | Caller-supplied repo (compatible with `SqlAlchemyIbkrSyncSnapshotRepository`) | `ibkr_sync_runs`, `ibkr_account_cash_snapshots`, `ibkr_position_snapshots` (`:169-177`) |
| `ibkr_market_data.py` | None directly | Builds `MarketDataLatestSnapshotRecord` for `market_data_latest_snapshots`; does not persist itself |
| Eight other modules | None | No writes |

These tables match the inventory in `docs/reality/components/storage-package-and-migrations.md` and the metadata definitions at `packages/storage/src/ai_trading_agent_storage/metadata.py:1278` (`ibkr_sync_runs`), `:1314` (`ibkr_account_cash_snapshots`), `:1329` (`ibkr_position_snapshots`), `:1349` (`ibkr_open_order_snapshots`), `:1381` (`ibkr_execution_snapshots`), with per-account indexes at `:1414-1433`.

## Read-only safety boundary

`grep -n "placeOrder\|cancelOrder"` across the twelve in-scope files returns **zero matches**. The read-only contract is reinforced at four layers:

1. **Protocol shape** — `IbapiSyncAppProtocol` (`ibkr_ibapi_sync_client.py:41-64`) declares only data request/cancel methods; there is no `placeOrder` or `cancelOrder` slot.
2. **Adapter base** — `IbkrReadOnlyAdapter` (`ibkr_sync_contracts.py:77-88`) only exposes four read methods.
3. **Factory gating** — `build_real_sync_adapter` returns `None` unless five gates pass including `account_mode == "paper"` and `ibkr_sync_readonly` (`ibkr_sync_adapter_factory.py:42-54`).
4. **Status hard-coding** — every status / readiness / persisted-run payload sets `actions_allowed`, `order_submission_allowed`, `order_modification_allowed`, `order_cancellation_allowed`, `suggestions_allowed`, `can_submit_orders`, `safe_for_orders` = `False`; `blocks_orders=True`. See `ibkr_sync.py:452-460`, `ibkr_sync_read_model.py:62-69`, `ibkr_sync_readiness.py:93-101`, `ibkr_sync_persistence.py:115-119`, `ibkr_account_snapshot_persistence.py:92-97`, `ibkr_account_snapshot_preflight.py:41-49`, `ibkr_market_data.py:110-112`.

## Cross-cutting observations

- **Dual ingest paths converge on the same tables.** `ibkr_sync.py` (full four-stream sync) and `ibkr_account_snapshot_persistence.py` (cash + positions only) both write into `ibkr_sync_runs`; the snapshot path leaves `open_orders_status="not_requested"` and `executions_status="not_requested"` so readers distinguish partial preflight from full sync (`ibkr_account_snapshot_persistence.py:83-88`).
- **Validation gates persistence, not collection.** `validate_ibkr_sync_payloads` runs after the adapter returns but before any repository call; failure produces an explicit `payload_validation_failed` status payload and zero writes (`ibkr_sync.py:184-218`).
- **In-memory `STORE` is always populated**, even when storage is durable; keeps `read_status` fast and lets the UI render a "last run" panel without re-reading the DB (`ibkr_sync.py:265-301, :402-460`).
- **Sync run IDs are namespaced** as `f"ibkr-sync-{uuid4()}"` (`ibkr_sync.py:145`), distinct from snapshot persistence IDs which use unprefixed `uuid4()` (`ibkr_sync_persistence.py:68-69`; `ibkr_account_snapshot_persistence.py:53-55`). The single shared `sync_run_id` ties all child snapshot rows back to one parent run via FKs on `sync_run_id` (`metadata.py:1318, 1333, 1353, 1385`).
- **No retry, no rate-limiting, no freshness windows** in this cluster. The sync client blocks once per request with `timeout_seconds` (`ibkr_ibapi_sync_client.py:464-468`); IBKR error code `2110` is treated identically to outright disconnection (`:38, :339-361`). Pacing handling is delegated upstream to the `connection_status == "pacing_limited"` check inside readiness (`ibkr_sync_readiness.py:49-59`).
- **Localisation is Dutch-only.** Every user-facing string (`status_nl`, `next_step_nl`, `help_nl`, validation `message_nl`) is Dutch; no English fall-back inside this cluster.
- **Snapshot uniqueness is run-scoped, not row-scoped.** Snapshot rows get fresh UUIDs every persistence call; idempotency on re-runs would have to come from the `sync_run_id` PK or a separate dedup layer (not visible in this cluster).
- **No `ibkr_connection_audit` writes** here despite the table being part of the IBKR family in storage; audit logging is owned by other modules (covered by the connection cluster doc).

## Open questions / uncertainty

- `ibkr_account_snapshot_preflight.py` is currently a skeleton — both public functions return `_base_blocked(...)` with no real IBKR conversation. Whether the missing implementation is intentional staging or a TODO is out of scope for Phase 1a.
- `ibkr_market_data.IbkrMarketDataAdapter.fetch_latest_snapshot` returns `PROVIDER_ERROR` even when configured (`:60-65`) — the actual provider wiring is absent. Same staging question.
- Snapshot dedup is run-scoped; if a caller re-runs the same `sync_run_id`, the row-level repository would have to deduplicate. Whether `SqlAlchemyIbkrSyncSnapshotRepository` does so is in the storage reality doc, not here.
- `ibkr_sync_adapter_factory` only constructs a real client when `app=None` defaults to the real ibapi import inside `IbapiReadOnlySyncClient`. Whether this is wired to production runtime is out of scope here.
