# `apps/api` — IBKR connection and status

**Phase:** 1a (reality components)
**Task:** T-004
**Scope:** nine modules in `apps/api/src/portfolio_outlook_api/` that own the IBKR connection surface and the various status / preflight payloads. Sits below the FastAPI router layer and above the worker-persisted `ibkr_connection_audit` table.

This file is descriptive. Every claim cites `path/to/file.py:NNN`. Non-trivial claims carry 3–10 line excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

- `ibkr_connection_read_model.py` — Task 126b worker-audit-derived connection view + serializers + masked account ids.
- `ibkr_connection_routes.py` — four read-only FastAPI routes for connection status / audit / latest positions / latest cash.
- `ibkr_status.py` — legacy `/ibkr/status` placeholder synthesiser (~70-key diagnostic dict).
- `ibkr_session_adapter_factory.py` — chooses the session-status adapter (default-safe vs TWS-readonly).
- `ibkr_session_status.py` — `IbkrSessionStatusAdapter` Protocol + `DefaultSafeIbkrSessionStatusAdapter`.
- `ibkr_tws_readonly_adapter.py` — `IbkrTwsReadonlyClient` Protocol + `IbkrTwsReadonlySessionStatusAdapter` (injected-client only).
- `ibkr_tws_readonly_runtime.py` — eleven-blocker preflight + manual status-check orchestrator (~507 lines).
- `ibkr_ibapi_client_facade.py` — `ibapi` dependency-availability + import-only preflight.
- `ibkr_contracts.py` — contract-search adapter Protocol + `NotConfiguredIbkrContractSearchAdapter`.

## `ibkr_connection_read_model.py`

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_connection_read_model.py`

### Public surface

- `AccountMode = Literal["paper", "live", "unknown"]` (`:38`).
- `STORAGE_UNAVAILABLE_DETAIL = "Opslag is niet beschikbaar."` (`:43`) — locked Dutch HTTP-503 body shared by the four 126b routes.
- `mask_account_id(account_id) -> str | None` (`:49`) — `DU1234567` → `DU•••4567`; IDs ≤ 6 chars returned as-is.
- `IbkrConnectionStatus(connected, account_id, account_mode, verified_at, error_nl)` frozen dataclass (`:70-86`).
- `synthesise_connection_status(audit_rows, *, configured_account_id) -> IbkrConnectionStatus` (`:89`).
- `read_connection_status(storage, *, configured_account_id, audit_limit=200)` (`:194`).
- `list_connection_audit_rows(storage, *, limit, configured_account_id=None)` (`:225`).
- `LatestSyncReadResult(sync_run_id, received_at, positions, cash_rows)` (`:246`).
- `read_latest_sync_payload(storage)` (`:254`).
- Serializers: `serialize_connection_status` (`:295`), `serialize_audit_row` (`:309`), `serialize_position_v126b` (`:321`), `serialize_cash_v126b` (`:349`).

### Collaborators

`SqlAlchemyIbkrConnectionAuditRepository`, `SqlAlchemyIbkrSyncSnapshotRepository`, `StorageConnectionProvider`, `StorageConnectionError`, `build_database_connection_settings`, plus three record dataclasses (`:25-34`). `StorageSettings` from `portfolio_outlook_api.config` (`:36`).

### Notable choices

- **Fail-closed on storage outage:** raises `StorageConnectionError("storage not configured")` if `storage.enabled` or `database_url` missing (`:206-207, :231-232, :257-258`). Docstring at `:13-16` calls out "no in-memory fallback per Task 126 product locks §6".
- **Account-mode classification is delegated to the worker.** The read model trusts only the literals `{"paper","live","unknown"}` persisted in `account_mode_detected`; anything else downgrades to `"unknown"` (`:153-155`).
- **All four serializers hard-code `safe_for_action_drafts: False` and `safe_for_orders: False`** on the wire (`:300-306`).

```python
# ibkr_connection_read_model.py:139-172
if latest_success is None:
    # No prior success: connected=False, mode=unknown.
    ...
connected = later_terminator is None and latest_refused is None
mode: AccountMode = "unknown"
if latest_success.account_mode_detected in ("paper", "live", "unknown"):
    mode = latest_success.account_mode_detected  # type: ignore[assignment]
```

## `ibkr_connection_routes.py`

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_connection_routes.py`

### Public surface (FastAPI routes)

All on a module-level `router = APIRouter()` (`:36`), mounted under the API's IBKR prefix:

- `GET /ibkr/connection/status` → `IbkrConnectionStatusResponse` (`:147-167`).
- `GET /ibkr/connection/audit?limit=20` (1–200) → `IbkrConnectionAuditResponse` (`:169-195`).
- `GET /ibkr/sync/positions/latest` → `IbkrPositionsLatestResponse` (`:198-215`).
- `GET /ibkr/sync/cash/latest` → `IbkrCashLatestResponse` (`:218-235`).

### Response models

Pydantic v2, `extra="forbid"`. Notable typed-False locks:

- `IbkrConnectionStatusResponse(connected, account_id, account_mode: Literal["paper","live","unknown"], verified_at, error, safe_for_action_drafts: Literal[False]=False, safe_for_orders: Literal[False]=False)` (`:42-62`).
- `IbkrConnectionAuditResponse(items, safe_for_action_drafts=False, safe_for_orders=False)` (`:65-82`).
- `IbkrPositionsLatestResponse(items, sync_run_id, as_of, safe_for_action_drafts=False, safe_for_orders=False)` (`:85-112`).
- `IbkrCashLatestResponse(items, ..., safe_for_action_drafts=False, safe_for_orders=False)` (`:115-137`).

### Collaborators

`portfolio_outlook_api.config.settings` (singleton, `:24`) — uses `settings.storage` and `settings.ibkr_account_id_hint`. `portfolio_outlook_api.ibkr_connection_read_model` (all eight read-model functions). `ai_trading_agent_storage.StorageConnectionError` for the 503 mapping.

### Notable choices

- All four responses carry `safe_for_action_drafts: Literal[False] = False` and `safe_for_orders: Literal[False] = False` — type-level lock; impossible to flip at runtime without a type-check failure.
- Audit endpoint description (`:177-181`) explicitly states the table is "Read-only / append-only — the underlying table has no update/delete path".
- Storage failures uniformly mapped via `_raise_storage_unavailable()` → HTTP 503 with `STORAGE_UNAVAILABLE_DETAIL` (`:143-144`).

```python
# ibkr_connection_routes.py:147-166
@router.get("/ibkr/connection/status", response_model=IbkrConnectionStatusResponse)
def read_ibkr_connection_status() -> dict[str, object]:
    ...
    try:
        status = read_connection_status(
            settings.storage,
            configured_account_id=settings.ibkr_account_id_hint,
        )
    except StorageConnectionError:
        _raise_storage_unavailable()
    return serialize_connection_status(status)
```

## `ibkr_status.py`

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_status.py`

### Public surface

- `build_ibkr_status_placeholder(runtime_settings, session_status_adapter=None) -> dict[str, object]` (`:147`) — plain function (not a FastAPI route in this file). Returns ~70-key legacy `/ibkr/status` payload.

Module constants (`:10-19`): `_KNOWN_CONNECTION_STATUSES = {"configured_not_connected", "connected_readonly", "connected_wrong_account_mode", "connection_failed", "authentication_required", "pacing_limited"}`; `_KNOWN_ACCOUNT_MODE_STATUSES = {"unknown", "unverified", "match", "mismatch"}`; `_KNOWN_ACCOUNT_MODES = {"paper", "live"}`.

### Collaborators

`BrokerProvider` from `portfolio_outlook_domain.broker_adapter` (`:1`); `Settings` from `portfolio_outlook_api.config`; `build_ibkr_session_status_adapter` + `IbkrSessionAdapterSelectionDiagnostics` from `ibkr_session_adapter_factory`; `IbkrSessionStatusAdapter` from `ibkr_session_status`.

### Notable choices

- **Version-1 invariants hard-coded** in the return dict (`:247-316`): `paper_only_enforced=True`, `readonly=True`, every `*_allowed` permission boolean = `False`, `safe_for_sync=False`, `safe_for_orders=False`, `blocks_orders=True`.
- Five-way state-machine over `runtime_settings.ibkr_enabled`, `configured`, `runtime_settings.ibkr_status_check_enabled`, optional adapter call, exception path (`:165-241`).
- **Mode-mismatch override** (`:202-213`): adapter `connection_status == "connected_wrong_account_mode"` forces `account_mode_status = "mismatch"`. Conversely, if adapter mode disagrees with `expected_mode`, status is rewritten to `"connected_wrong_account_mode"` + `"mismatch"` + `session_status_reason = "account_mode_mismatch"`.
- **Match upgrade** (`:215-223`): adapter `"unknown"` + concrete mode equal to expected (or no expected set) → upgraded to `"match"`.
- **`_runtime_diagnostics` always returns `runtime_connection_allowed=False`** — every branch terminates at `"not implemented"`, `"status_check_disabled"`, `"explicit_opt_in_required"`, or `"network_runtime_not_implemented"` (`:139-146`).
- 10 distinct Dutch `_nl` copy variants for each `connection_status` (`:45-115`).

```python
# ibkr_status.py:202-213
if final_connection_status == "connected_wrong_account_mode":
    final_account_mode_status = "mismatch"

if (
    final_account_mode_status != "mismatch"
    and expected_mode is not None
    and adapter_account_mode is not None
    and adapter_account_mode != expected_mode
):
    final_connection_status = "connected_wrong_account_mode"
    final_account_mode_status = "mismatch"
    final_session_status_reason = "account_mode_mismatch"
```

## `ibkr_session_adapter_factory.py`

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_session_adapter_factory.py`

### Public surface

- `IbkrSessionAdapterSelectionDiagnostics` frozen dataclass (`:16-29`) — twelve fields including `session_adapter_family`, `session_adapter_source`, `session_adapter_enabled`, `session_adapter_reason`, the TWS-readonly toggles + blocked reasons + Dutch help.
- `build_ibkr_session_status_adapter(settings, client=None) -> tuple[IbkrSessionStatusAdapter, IbkrSessionAdapterSelectionDiagnostics]` (`:32`).

### Collaborators

`DefaultSafeIbkrSessionStatusAdapter`, `IbkrSessionStatusAdapter` from `ibkr_session_status`; `IbkrTwsReadonlyClient`, `IbkrTwsReadonlySessionStatusAdapter` from `ibkr_tws_readonly_adapter`.

### Notable choices

- **Default-safe branch** (`:36-60`): when `ibkr_tws_readonly_adapter_enabled` is false (default), returns `DefaultSafeIbkrSessionStatusAdapter` with diagnostics `session_adapter_enabled=False`, `tws_readonly_adapter_blocked_reasons=("default_safe_adapter", "tws_adapter_disabled", "explicit_opt_in_required", "status_check_disabled")`.
- Even when opted in, the TWS-readonly branch (`:62-106`) only achieves `runtime_available=True` when an **injected `client`** is provided; the production network runtime is still blocked (`"network_runtime_not_implemented"`, `"adapter_selected_but_blocked"`). The factory is test-injection-only.

## `ibkr_session_status.py`

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_session_status.py`

### Public surface

- `IbkrSessionStatusAdapterResult(connection_status, account_mode_status="unknown", account_mode=None, session_status_reason=None, session_check_source="adapter")` (`:9-15`).
- `IbkrSessionStatusAdapter(Protocol)` with `check_session_status(runtime_settings) -> IbkrSessionStatusAdapterResult` (`:18`).
- `DefaultSafeIbkrSessionStatusAdapter` (`:23`) — always returns `connection_status="configured_not_connected"`, `account_mode = settings.ibkr_expected_environment` (`:26-33`), `session_status_reason="default_safe_non_network"`.

### Notable choices

Module is the protocol seam used by both `ibkr_status` and `ibkr_session_adapter_factory`. The "default safe" implementation never opens a socket; it echoes the configured expected environment back as the mode.

## `ibkr_tws_readonly_adapter.py`

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_tws_readonly_adapter.py`

### Public surface

- `IbkrTwsReadonlyClient(Protocol)` with `connect_readonly(timeout_seconds)`, `is_connected()`, `get_account_mode() -> str | None`, `disconnect()` (`:13-26`). **Four read-only methods only — no `placeOrder`/`cancelOrder`.**
- `IbkrTwsReadonlyAdapterError(RuntimeError)` with `code: str` (`:29-31`).
- `IbkrTwsReadonlySessionStatusAdapter(IbkrSessionStatusAdapter)` (`:34`) — injected-client-only TWS status adapter.

### Notable choices

- `_normalize_mode` (`:123-129`) accepts only `{"paper","live"}` after `strip().lower()`; everything else maps to `None` → `connection_status="unknown"`, `session_status_reason="account_mode_unavailable"` (`:66-73`).
- **Mismatch path** (`:75-82`): non-None `expected_mode` ≠ `account_mode` → `connection_status="connected_wrong_account_mode"`, `account_mode_status="mismatch"`, `session_status_reason="account_mode_mismatch"`.
- **Match path** (`:84-90`): `connection_status="connected_readonly"`, `account_mode_status="match"`.
- Exception fan-out (`:91-114`): `TimeoutError` → `"connection_failed"` / `"timeout"`; `IbkrTwsReadonlyAdapterError` → mapped via `_map_error_code` to `{authentication_required, pacing_limited, connection_failed}` else `"unknown"`; bare `Exception` → `"unknown"` / `"unexpected_client_error"`.
- **`finally` clause always disconnects + swallows disconnect errors** (`:115-120`): "Keep status checks resilient; never escalate disconnect errors."

```python
# ibkr_tws_readonly_adapter.py:50-90
self._client.connect_readonly(timeout_seconds=runtime_settings.ibkr_connection_timeout_seconds)
if not self._client.is_connected():
    return IbkrSessionStatusAdapterResult(connection_status="configured_not_connected", ...)
account_mode = _normalize_mode(self._client.get_account_mode())
expected_mode = _normalize_mode(runtime_settings.ibkr_expected_environment)
...
if expected_mode is not None and account_mode != expected_mode:
    return IbkrSessionStatusAdapterResult(
        connection_status="connected_wrong_account_mode",
        account_mode_status="mismatch", ...
    )
return IbkrSessionStatusAdapterResult(
    connection_status="connected_readonly",
    account_mode_status="match", ...
)
```

## `ibkr_tws_readonly_runtime.py` (~507 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_tws_readonly_runtime.py`

### Public surface

Three result dataclasses with hard-False safety defaults:

- `IbkrTwsReadonlyRuntimeGateResult` (`:12-25`) — gate-only outcome.
- `IbkrTwsReadonlyRuntimeCheckResult` (`:28-59`) — full manual-check outcome; defaults: `actions_allowed=False`, `suggestions_allowed=False`, `action_drafts_allowed=False`, `orders_allowed=False`, `order_submission_allowed=False`, `order_modification_allowed=False`, `order_cancellation_allowed=False`, `can_submit_orders=False`, `safe_for_orders=False`, `blocks_orders=True`.
- `IbkrTwsReadonlyStatusCheckReadinessResult` (`:62-99`) — same hard-False safety defaults + per-flag config booleans.

Functions: `check_tws_readonly_runtime_preflight` (`:102`); `run_manual_tws_readonly_status_check` (`:167`); `build_manual_tws_readonly_status_check_readiness` (`:383`) — declares the documented endpoint `/ibkr/session/manual-readonly-status-check` with method `POST` (`:414-415`).

### Notable choices

- **Eleven-blocker preflight** (`:102-149`): all must be green.
  1. `ibkr_tws_readonly_runtime_enabled`
  2. `ibkr_status_check_enabled`
  3. `ibkr_enabled`
  4. `ibkr_tws_readonly_adapter_enabled`
  5. `ibkr_tws_readonly_real_client_enabled`
  6. `paper_only_mode`
  7. `expected_environment` normalises to `"paper"` (else blocker `expected_account_mode_not_paper`) — **hard-locks paper-only**.
  8–10. `ibkr_sync_host`, `ibkr_sync_port`, `ibkr_sync_client_id` non-None.
  11. `runtime_client` injection present.
- Manual check (`:167-356`) wraps every branch in try/except + always-`_disconnect()` (`:179-184, :206, :233, :259, :285, :317, :343`). Disconnect errors swallowed.
- Status taxonomy: `manual_status_check_ready`, `manual_status_check_completed`, `unknown_account_mode`, `wrong_account_mode`, `timeout`, `authentication_required`, `pacing_limited`, `connection_failed`, `unexpected_client_error`.
- Dutch error/status table in `_reason_nl` (`:487-506`) with 15 mappings.

```python
# ibkr_tws_readonly_runtime.py:106-133
if not settings.ibkr_tws_readonly_runtime_enabled:
    blocked_reasons.append("runtime_disabled")
if not settings.ibkr_status_check_enabled:
    blocked_reasons.append("status_check_disabled")
...
if not settings.paper_only_mode:
    blocked_reasons.append("paper_only_required")

expected_mode = _normalize_mode(settings.ibkr_expected_environment)
if expected_mode != "paper":
    blocked_reasons.append("expected_account_mode_not_paper")
```

## `ibkr_ibapi_client_facade.py`

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_ibapi_client_facade.py`

### Public surface

- `IbapiDependencyAvailability` dataclass (`:9-22`) — `runtime_connection_enabled=False`, `connection_attempted=False`, `socket_opened=False`, `production_runtime_wired=False` defaults.
- `IbapiFacadeImportResult` dataclass (`:24-33`) — same hard-False defaults.
- `check_ibapi_dependency_available() -> IbapiDependencyAvailability` (`:36`) — uses `importlib.util.find_spec("ibapi")`; **does not import**.
- `load_ibapi_preflight_modules() -> IbapiFacadeImportResult` (`:66`) — imports `ibapi` + `ibapi.wrapper`; `_assert_module` checks `module.__name__` (`:93`).

### Notable choices

All four "production-runtime" booleans default to `False` and are **never set to True** anywhere in this file — facade exists purely to surface "is the dep installable / importable" without opening sockets. Status strings: `"ibapi_available"`, `"ibapi_not_available"`, `"ibapi_preflight_import_failed"`. Dutch help text repeatedly emphasises "Alleen importcontrole, geen verbinding".

## `ibkr_contracts.py`

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_contracts.py`

### Public surface

- `VALIDATION_STATUSES = {"unvalidated","valid","ambiguous","not_found","unsupported","error"}` (`:9-16`).
- `IbkrContractCandidate` frozen dataclass (`:19-36`).
- `IbkrContractValidationResult` frozen dataclass (`:38-54`).
- `IbkrContractSearchAdapter` abstract class with `search_contracts` and `fetch_contract_details` (`:56`).
- `NotConfiguredIbkrContractSearchAdapter` (`:68`) — returns `[]` for searches and a synthetic `unsupported` validation result with Dutch message "IBKR contractvalidatie is niet ingesteld."
- `DEFAULT_ADAPTER: IbkrContractSearchAdapter = NotConfiguredIbkrContractSearchAdapter()` (`:96`).
- `is_contract_search_configured(settings)` (`:99`); `search_ibkr_contracts(settings, query, *, search_name, adapter=None)` (`:105`); `validate_ibkr_contract(settings, conid, *, security_type, adapter=None, asset_id=None, watchlist_item_id=None)` (`:151`).

### Notable choices

- Query length guard: `< 2` chars → `status="invalid_query"` + Dutch "Zoekterm moet minstens 2 tekens hebben." (`:113-120`).
- All adapter exceptions caught and mapped to `status="error"` + Dutch copy (`:141-148, :178-182`); never re-raised. The contract-search HTTP surface stays fail-soft.
- No transport implementation in this file — only types and a no-op default adapter. Real adapter wiring (Web API or TWS) is deferred per ADR 0003.

## Read-only safety boundary

`grep -n "placeOrder\|cancelOrder"` over the nine in-scope files returns **zero matches**. The order-submission verbs live exclusively in `ibkr_ibapi_order_submission_client.py` (covered by `api-ibkr-submission-and-watchlists.md`). The connection / status cluster is structurally separated from any code path that could place or cancel an order.

Defence-in-depth layers observed in this cluster:

1. **Type-level lock on wire safety booleans.** Every response model uses `Literal[False]` defaults (`ibkr_connection_routes.py:61-62, :81-82, :111-112, :136-137`); Pydantic v2 with `extra="forbid"` enforces this.
2. **Serializer-level lock.** `serialize_connection_status` hardcodes both safety booleans (`ibkr_connection_read_model.py:304-305`).
3. **Read-only DB checkout.** `provider.checked_connection(require_writable=False)` on every storage call (`ibkr_connection_read_model.py:212, :236, :262`).
4. **Read-only client protocol.** `IbkrTwsReadonlyClient` exposes only four read-only methods (`ibkr_tws_readonly_adapter.py:13-26`).
5. **Eleven-blocker preflight** with hard `paper_only_mode` + `expected_environment == "paper"` (`ibkr_tws_readonly_runtime.py:106-133`).
6. **Always-disconnect + swallow-disconnect-errors** in every branch (`ibkr_tws_readonly_adapter.py:115-120`; `ibkr_tws_readonly_runtime.py:179-184` + per-branch disconnects).
7. **Three dataclass-default hard-False sets** in `ibkr_tws_readonly_runtime.py:50-59, :90-99`.
8. **`build_ibkr_status_placeholder`** hard-codes `paper_only_enforced=True`, `readonly=True`, all `*_allowed` keys = `False`, `blocks_orders=True` (`ibkr_status.py:255-316`).
9. **Runtime gate always blocked.** `_runtime_diagnostics` (`ibkr_status.py:139-146`) returns `runtime_connection_allowed=False` in every branch.
10. **`ibapi` facade hard-codes** `runtime_connection_enabled=False`, `connection_attempted=False`, `socket_opened=False`, `production_runtime_wired=False` (`ibkr_ibapi_client_facade.py:18-22, :30-33`).

## Account-mode detection — every site

Four distinct detection / normalisation sites in this cluster.

### Site A — worker-audit-derived (`ibkr_connection_read_model.py:152-155`)

The API trusts whatever the worker persisted in `ibkr_connection_audit.account_mode_detected`; values outside the whitelist downgrade to `"unknown"`. No live IBKR call — the API never re-derives the mode; it only re-projects what was persisted.

### Site B — live TWS adapter (`ibkr_tws_readonly_adapter.py:63-90`)

Three-branch classification: `None` → `unknown`; mismatch → `connected_wrong_account_mode`/`mismatch`; equal → `connected_readonly`/`match`.

### Site C — manual runtime check (`ibkr_tws_readonly_runtime.py:190-258`)

Same classification as B but emits a different `status` taxonomy aimed at the manual-check endpoint payload.

### Site D — placeholder synthesiser (`ibkr_status.py:189-234`)

Combines an adapter result with the configured `expected_environment` using the mismatch-override and match-upgrade rules described above.

### Normalisation rules

All four sites funnel through a `_normalize_mode` / `_normalize_account_mode` (`ibkr_status.py:36-42`; `ibkr_tws_readonly_adapter.py:123-129`; `ibkr_tws_readonly_runtime.py:471-477`) that lowercases-trims and whitelists `{"paper","live"}`, returning `None` for anything else. `ibkr_connection_read_model.AccountMode = Literal["paper","live","unknown"]` (`:38`) uniquely admits `"unknown"` because the worker persists it.

### Status taxonomy

- `account_mode_status`: `{"unknown", "unverified", "match", "mismatch"}` (`ibkr_status.py:18`).
- Connection-status mode-related values: `"connected_readonly"`, `"connected_wrong_account_mode"` (`ibkr_status.py:11-17`).
- Wire literal for `account_mode`: `"paper" | "live" | "unknown"` (`ibkr_connection_routes.py:52`).

## Cross-cutting observations

- **Two parallel status surfaces co-exist.** The Task 126b path (`ibkr_connection_routes.py` → `ibkr_connection_read_model.py`) is the worker-audit-derived, masked, read-only view used by the AccountModeBadge and Portefeuille grid. The older Task 130 path (`ibkr_status.py`) synthesises a per-request status by optionally invoking a session-status adapter. They report different field shapes; `ibkr_status.py` produces ~70-key legacy diagnostic JSON, while the 126b routes return Pydantic-validated 5–7 field bodies.
- **The mask is one-way.** Account-ID masking happens at four serialiser sites; the unmasked ID is only used internally for the `configured_account_id` filter (`ibkr_connection_read_model.py:107-115`).
- **Storage is authoritative for `connected` and `account_mode_detected`** in the 126b read model; the API does not synthesise mode from anything in-process.
- **All Dutch user-facing copy is centralised at the boundary.** No Dutch strings appear in synthesis logic; classification stays English/enum.
- **ADR alignment.** ADR 0002 establishes IBKR as source of truth and the local mirror as read-only / point-in-time snapshots — reflected in the 126b read-only routes. ADR 0003 declares the V1 invariants (paper-only required, no order submission, no credentials, account-mode confirmable) — reflected in the eleven-blocker preflight, the hard-False `*_allowed` / `safe_for_orders` / `blocks_orders=True` defaults, and the absence of `placeOrder`/`cancelOrder` in any of the nine files.

## Open questions / uncertainty

- Two parallel status surfaces (legacy `ibkr_status.py` vs Task 126b routes) coexist. Whether one is meant to deprecate the other is for Phase 1b architecture review.
- `ibkr_tws_readonly_adapter.IbkrTwsReadonlySessionStatusAdapter` is "injected-client-only"; the production network runtime is explicitly blocked. The seam exists but the live wiring does not — out of scope for Phase 1a.
- `ibkr_contracts.NotConfiguredIbkrContractSearchAdapter` is the only adapter ever wired by default; real Web API / TWS contract search is deferred per ADR 0003. Whether this should ship in v1 is a Phase 4 decision.
