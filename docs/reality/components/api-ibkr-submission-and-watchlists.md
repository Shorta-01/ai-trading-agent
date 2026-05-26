# `apps/api` — IBKR submission and watchlists

**Phase:** 1a (reality components)
**Task:** T-004
**Scope:** five modules in `apps/api/src/portfolio_outlook_api/` that own the IBKR order-submission read surface, the order-submission factory (single gating point), the ibapi order-submission client (the one place `placeOrder` is called in the API tree), the manual-status ibapi client, and the watchlist import surface. Cross-references the action-draft state machine in `packages/portfolio` and the storage-level state-transition map.

This file is descriptive. Every claim cites `path/to/file.py:NNN`. Non-trivial claims carry 3–10 line excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

- `ibkr_submission.py` — five read-only FastAPI routes over the submission audit / lifecycle / active / historiek / executions tables.
- `ibkr_order_submission_factory.py` — single gating-point factory that decides whether a real `placeOrder` is reachable at all.
- `ibkr_ibapi_order_submission_client.py` — the only API-side module that calls `placeOrder` (~570 lines).
- `ibkr_ibapi_manual_status_client.py` — connect + `reqManagedAccts` probe for account-mode classification.
- `ibkr_watchlists.py` — IBKR watchlist import surface (in-memory; no DB writes).

Cross-references throughout: `packages/portfolio/src/portfolio_outlook_portfolio/action_draft_state_machine.py` (portfolio enum) and `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:4820-4911` (storage transition map).

## `ibkr_submission.py`

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_submission.py`

### Public surface (FastAPI routes)

Five read-only `GET` routes on a module-level `router` (`:55`):

- `GET /ibkr-submission/audit` (`:263-290`) — newest-first `IbkrSubmissionAuditEntry` rows for an account.
- `GET /ibkr-submission/lifecycle/{action_draft_id}` (`:293-316`).
- `GET /ibkr-submission/active` (`:319-345`) — drafts in any in-flight status (`submitted` / `accepted` / `working` / `partially_filled` / `pending_cancellation`).
- `GET /ibkr-submission/historiek` (`:348-375`).
- `GET /ibkr-executions` (`:378-406`) — per-asset execution rows keyed by `conid`.

### Response models

Pydantic v2, `extra="forbid"`, Decimal-as-string. Notable typed unions:

- `IbkrSubmissionAuditResponse.result: Literal["placed", "rejected_at_send", "connection_lost"]` (`:78`).
- `IbkrSubmissionLifecycleResponse.event_type: Literal["status_change", "fill", "commission_report", "cancellation_request"]` (`:97-102`).

### Collaborators

Storage repos imported at `:33-45`: `SqlAlchemyActionDraftRepository`, `SqlAlchemyIbkrExecutionsRepository`, `SqlAlchemyIbkrSubmissionAuditRepository`, `SqlAlchemyIbkrSubmissionLifecycleRepository`. `StorageConnectionProvider` / `build_database_connection_settings` for read-only `checked_connection(require_writable=False)` (`:277`). `ActionDraftResponse` + `_serialize_draft` from `portfolio_outlook_api.action_draft` (`:49-52`). `Settings` via `portfolio_outlook_api.config.settings` (`:53`).

### Persistent-state implications

**Read-only.** Reads `ibkr_submission_audit`, `ibkr_submission_lifecycle`, `action_drafts`, `ibkr_executions`. Does not write, does not transition state, does not call `placeOrder`/`cancelOrder`. The grep below confirms zero submission/cancel call sites in this file.

### Notable choices

- `_resolve_account_id` (`:248-255`) falls back to `settings.ibkr_account_id_hint` and raises 404 `"Geen IBKR-rekening geconfigureerd."` when nothing is set.
- `_storage_provider` (`:230-237`) raises HTTP 503 with `"Opslag is niet beschikbaar."` when storage is disabled; same raised on every caught `StorageConnectionError` (`:285-286`).
- Decimal serialisation is forced through `str(...)` to keep wire types JSON-safe (`:188-189, :217-221`).

```python
# ibkr_submission.py:263-290
@router.get("/ibkr-submission/audit", response_model=IbkrSubmissionAuditListResponse)
def list_submission_audit(
    account_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    effective_account = _resolve_account_id(account_id)
    provider = _storage_provider()
    payload: list[dict[str, object]] = []
    try:
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyIbkrSubmissionAuditRepository(checked.connection, checked.readiness)
            rows = repo.list_for_account(ibkr_account_id=effective_account, limit=limit)
            payload = [_serialize_audit(r) for r in rows]
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {"ibkr_account_id": effective_account, "rows": payload}
```

## `ibkr_order_submission_factory.py`

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_order_submission_factory.py`

### Public surface

`build_real_order_submission_client(settings, *, app=None) -> IbapiOrderSubmissionClient | None` (`:29-50`).

### Notable choices

- Module docstring declares this the "**single gating point** for any actual broker order submission" (`:1-7`).
- Post-V1 §21.1: account-mode (paper/live) is **no longer** an app-side gate; only the `ibkr_paper_order_submission_enabled` flag, the `ibkr_paper_order_submission_real_client_enabled` flag, and host/port/client-id are checked (`:10-17`).
- `client_id` and `port` are validated against `None` (`:41-42`), so `client_id=0` is intentionally allowed.
- A `None` return causes `submit_action_draft_to_paper` (`action_draft_submission.py:330-344`) to short-circuit into `blocking_reason="submission_client_unavailable"` without touching storage.

```python
# ibkr_order_submission_factory.py:29-50
def build_real_order_submission_client(
    settings: Settings, *, app: OrderSubmissionAppProtocol | None = None,
) -> IbapiOrderSubmissionClient | None:
    if not settings.ibkr_paper_order_submission_enabled:
        return None
    if not settings.ibkr_paper_order_submission_real_client_enabled:
        return None
    host = settings.ibkr_paper_order_submission_host
    port = settings.ibkr_paper_order_submission_port
    client_id = settings.ibkr_paper_order_submission_client_id
    if not host or port is None or client_id is None:
        return None
    return IbapiOrderSubmissionClient(
        host=host, port=port, client_id=client_id,
        timeout_seconds=settings.ibkr_paper_order_submission_timeout_seconds,
        provider_code=settings.ibkr_paper_order_submission_provider_code,
        app=app,
    )
```

## `ibkr_ibapi_order_submission_client.py` (~570 lines)

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_ibapi_order_submission_client.py`

### Public surface

- Data classes: `OrderSubmissionInputs` (`:50-71`), `OrderSubmissionResult` (`:74-84`).
- Protocols: `OrderSubmissionAppProtocol` (`:87-102`) — `connect / isConnected / disconnect / run / reqIds / placeOrder`. **`cancelOrder` is NOT in this protocol** — this client only places orders.
- Free functions: `build_submission_callbacks` (`:117-192`), `build_contract_and_orders` (`:246-263`), `build_contract_and_order` (`:266-278`), `_build_orders_for_type` (`:281-367`).
- Class: `IbapiOrderSubmissionClient` (`:370-570`) with `submit`, `close`, context-manager support.
- Constants: `CONNECTION_ERROR_CODES = {502, 504, 1100, 1101, 1102, 1300, 2110}` (`:43`); `LOCKED_ORDER_TYPES = {"LMT","MKT","STP","STP_LMT","TRAIL","TRAIL_LMT","BRACKET"}` (`:45-47`).

### Collaborators

`load_ibapi_preflight_modules` from `ibkr_ibapi_client_facade` (`:37, :209, :417`). `IbkrTwsReadonlyAdapterError` from `ibkr_tws_readonly_adapter` is reused as the connection-failed exception type (`:38, :172, :441, :447`). Dynamically imports `ibapi.contract`, `ibapi.order`, `ibapi.client`, `ibapi.wrapper` (`:210-214, :418-422`).

### Persistent-state implications

The client itself writes **nothing** to storage; persistence is the caller's job (`action_draft_submission.py:445-495`). The audit-log doctrine in the storage `SqlAlchemyIbkrSubmissionAuditRepository` notes that audit rows are "Written by the worker immediately after every `placeOrder()` attempt" — confirming this **API-side** client is *not* the production submission path; the production path lives in `apps/worker/.../ibkr_submission/submitter.py`. The API client supports the on-demand approve+submit flow (`action_draft_submission.submit_action_draft_to_paper`).

### Notable choices

- **Order-type validation:** `_validate_common_inputs` (`:195-205`) enforces `action_side ∈ {BUY, SELL}`, `security_type == "STK"`, integral positive `quantity`, `order_type ∈ LOCKED_ORDER_TYPES`.
- **BRACKET orders:** parent + two children built in `_build_orders_for_type` (`:339-367`). Parent `transmit=False`, take-profit `transmit=False`, stop-loss `transmit=True` (final child triggers the group). Child `parentId` patched in `submit` **after** `nextValidId` resolves (`:515-520`).
- **`nextValidId` handshake:** `submit` calls `reqIds(-1)`, waits on `next_order_id_event` for `timeout_seconds` (`:471-481`). Timeout returns `accepted=False, rejected_reason="next_valid_id_timeout"`.
- **`perm_id` capture:** the `openOrder` callback writes parent's `permId` into `_SubmissionState.ibkr_perm_id` under a lock (`:128-142`).
- **`orderStatus` callback** (`:144-162`) treats `status ∈ {"ApiCancelled","Cancelled","Inactive"}` as rejection by writing `rejected_reason=why_held or status`. Otherwise stores the status text.
- **Error handling** (`:164-186`): codes in `CONNECTION_ERROR_CODES` set `state.fatal_error = IbkrTwsReadonlyAdapterError("connection_failed")` and unblock both events; codes `2100-2199` are non-fatal warnings; other codes record `rejected_reason = f"{error_code}:{error_string}"`.
- **Connection lifecycle:** `_ensure_connected` (`:436-458`) is idempotent. Launches a daemon thread named `ibapi-submit-{client_id}` running `self._app.run()`. `close()` (`:549-564`) flips `_closed`, disconnects, joins the thread with `timeout=self._timeout`.
- **No retry policy.** A single `submit` performs a single attempt; no exponential backoff. **No app-managed idempotency keys** — IBKR's `order_id` / `perm_id` are the only identifiers. The state machine prevents double-submit at the storage layer (see §Submission state machine below).
- **No `cancelOrder`** — cancellation lives in the worker.

```python
# ibkr_ibapi_order_submission_client.py:515-520
# For BRACKET (or any multi-order build) wire child ``parentId``
# to the parent's order_id so IBKR groups them.
if len(orders) > 1:
    for child in orders[1:]:
        if hasattr(child, "parentId"):
            child.parentId = order_id
```

```python
# ibkr_ibapi_order_submission_client.py:522-535 — the only placeOrder call site in the API tree
self._state.confirmation_event.clear()
try:
    for offset, order in enumerate(orders):
        self._app.placeOrder(order_id + offset, contract, order)
except Exception as exc:
    return OrderSubmissionResult(
        accepted=False,
        ibkr_order_id=order_id,
        ibkr_perm_id=None,
        ibkr_client_id=self._client_id,
        ibkr_status_text=None,
        rejected_reason="place_order_raised",
        raw_diagnostic=str(exc),
    )
```

```python
# ibkr_ibapi_order_submission_client.py:128-142
def open_order(  # noqa: N802
    _self: Any, order_id: int, _contract: Any, order: Any, order_state: Any,
) -> None:
    with lock:
        perm_id = int(getattr(order, "permId", 0))
        if perm_id:
            state.ibkr_perm_id = perm_id
        status_text = getattr(order_state, "status", None)
        if status_text:
            state.ibkr_status_text = str(status_text)
    state.confirmation_event.set()
```

## `ibkr_ibapi_manual_status_client.py`

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_ibapi_manual_status_client.py`

### Public surface

- `_ManualIbapiAppProtocol` (`:12-19`).
- `_SessionState` dataclass (`:22-25`).
- `IbapiManualReadonlyStatusClient` (`:28-123`) with `connect_readonly`, `is_connected`, `get_account_mode`, `disconnect`.

### Notable choices

- **Account-mode classification heuristic** (`:107-120`): all-`DU*` accounts → `"paper"`; any account starting with `U`, `F`, or `I` → `"live"`; otherwise `None`.
- **Synchronous one-shot:** unlike the submission client, this class does *not* spin a `run()` thread. It relies on the connect callback populating `managedAccounts` before the caller polls `get_account_mode`. Single lock on `_SessionState`.
- **Harsh error handling:** for codes `{502, 504, 1100}` the `_error` callback **raises directly** in the EWrapper thread (`:73-74`); other codes are ignored.
- `timeout_seconds <= 0` in `connect_readonly` is treated as a timeout (`:96-97`).

```python
# ibkr_ibapi_manual_status_client.py:107-120
def get_account_mode(self) -> str | None:
    with self._lock:
        accounts = self._state.managed_accounts
    if not accounts:
        return None
    if all(account.startswith("DU") for account in accounts):
        return "paper"
    if any(
        account.startswith(prefix)
        for prefix in ("U", "F", "I")
        for account in accounts
    ):
        return "live"
    return None
```

No `placeOrder` and no `cancelOrder` — confirmed by grep. Read-only.

## `ibkr_watchlists.py`

**Path:** `apps/api/src/portfolio_outlook_api/ibkr_watchlists.py`

### Public surface

- Frozen dataclasses: `IbkrWatchlistSummary` (`:11-21`), `IbkrWatchlistInstrument` (`:23-37`).
- Adapter classes: abstract `IbkrWatchlistAdapter` (`:39-44`), default `NotConfiguredIbkrWatchlistAdapter` (`:47-52`).
- Module-level mutable singletons: `DEFAULT_ADAPTER` (`:55`), `IMPORT_RUNS: list` (`:56`), `IMPORT_CANDIDATES: dict` (`:57`).
- Functions: `list_ibkr_watchlists` (`:68-94`), `list_ibkr_watchlist_instruments` (`:97-124`), `import_ibkr_watchlist` (`:127-193`), `latest_import` (`:196-197`), `import_by_id` (`:200-204`).

### Persistent-state implications

**None against a real database.** All state is in-process Python lists/dicts:

- `IMPORT_RUNS` (`:56`) — appended on every `import_ibkr_watchlist` call.
- `IMPORT_CANDIDATES` (`:57`) — keyed by `import_run_id`, holds candidate rows.
- The local `STORE` from `portfolio_outlook_api.watchlist` is read but not written here.

These dictionaries are process-local module-level globals; wiped on every restart. No DB-backed persistence in this module.

### Notable choices

- `_configured` (`:60-65`) requires `ibkr_enabled`, `ibkr_gateway_url`, `ibkr_account_id_hint` all set; otherwise responses are `status="not_configured"` + `message_nl="Niet geconfigureerd."`.
- Adapter exceptions swallowed and converted to `status="error"` Dutch payloads (`:82-88, :112-118`).
- The default adapter returns empty lists — a real adapter must be injected explicitly. No real adapter in this file.
- Import categorisation (`:144-174`): empty `ibkr_conid` → `import_status="skipped" / validation_status="unsupported"`; local-store matches → `already_in_local_watchlist`; same-symbol-different-conid → `needs_review`.
- `run_id` is `f"ibkr-watchlist-import-{uuid4()}"` (`:143`).

```python
# ibkr_watchlists.py:147-174
for row in items:
    if not isinstance(row, dict):
        continue
    conid = (row.get("ibkr_conid") or "").strip()
    symbol = (row.get("symbol") or "").strip().upper()
    status = "candidate"
    validation = "imported"
    if conid == "":
        status = "skipped"
        validation = "unsupported"
        needs_review += 1
    else:
        for local in STORE.values():
            if local.status != "active":
                continue
            if (local.ibkr_conid or "").strip() == conid:
                status = "already_in_local_watchlist"
                matched += 1
                break
            if local.symbol == symbol and (local.ibkr_conid or "").strip() != conid:
                status = "needs_review"
                validation = "needs_review"
                needs_review += 1
                break
    row["import_status"] = status
    row["validation_status"] = validation
    candidates.append(row)
IMPORT_CANDIDATES[run_id] = candidates
```

No `placeOrder` / `cancelOrder` — watchlists never touch order submission.

## Submission state machine + `placeOrder` / `cancelOrder` map

### Grep result

```
ibkr_ibapi_order_submission_client.py:100  def placeOrder(  # Protocol method
ibkr_ibapi_order_submission_client.py:525  self._app.placeOrder(order_id + offset, contract, order)
```

The other four in-scope modules contain **zero** `placeOrder` / `cancelOrder` references. The single live `placeOrder` invocation in the API sub-cluster is at `ibkr_ibapi_order_submission_client.py:525`. There is **no `cancelOrder` call anywhere in the API tree** — cancellation is delegated to the worker (see `apps/api/src/portfolio_outlook_api/action_draft.py:792`).

### Two parallel state vocabularies

The codebase carries two state-machine maps that both apply to the same draft:

1. **Portfolio enum** (`packages/portfolio/src/portfolio_outlook_portfolio/action_draft_state_machine.py`):
   - States `DRAFT, SAFETY_CHECKED, USER_APPROVED, SUBMITTED, AWAITING_IBKR_REPLY, REPLY_CONFIRMED, WORKING, FILLED, CANCELLED, REJECTED, RECONCILED, EXPIRED, FAILED` (`:37-50`).
   - `ALLOWED_TRANSITIONS` (`:54-117`); notably `USER_APPROVED → {DRAFT, SUBMITTED, EXPIRED, FAILED}` (`:70-77`) and `SUBMITTED → {AWAITING_IBKR_REPLY, REJECTED, FAILED}` (`:78-83`).
   - `LIVE_AT_BROKER_STATES = {SUBMITTED, AWAITING_IBKR_REPLY, REPLY_CONFIRMED, WORKING}` (`:129-136`).
   - Consumed by `action_draft_submission.py` via `require_transition_allowed` (`:36-38, :258-260, :410-413`).

2. **Storage transition map** (`packages/storage/src/ai_trading_agent_storage/sql_repositories.py:4820-4911`):
   - `proposed → {edited, user_approved, dismissed, deleted, superseded}` (`:4821-4823`)
   - `edited → {user_approved, dismissed, deleted, superseded}` (`:4824-4826`)
   - `user_approved → {submitted, dismissed, deleted}` (`:4831`)
   - `submitted → {accepted, rejected, cancelled, pending_cancellation, awaiting_reply_timeout, working, filled, partially_filled}` (`:4840-4856`)
   - `accepted → {working, cancelled, rejected, pending_cancellation, filled, partially_filled}` (`:4857-4868`)
   - `working → {filled, partially_filled, cancelled, rejected, pending_cancellation}` (`:4869-4877`)
   - `partially_filled → {filled, cancelled, rejected, pending_cancellation}` (`:4878-4880`)
   - `pending_cancellation → {cancelled, filled, partially_filled}` (`:4884-4886`) — explicitly accommodates fill-vs-cancel race.
   - `awaiting_reply_timeout → {filled, partially_filled, cancelled, rejected, requires_manual_review}` (`:4898-4906`) — Task 135 reconciler heal path.
   - Terminals: `dismissed, deleted, superseded, filled, cancelled, rejected, requires_manual_review` (`:4888-4910`).
   - Enforced by `_require_action_draft_transition_allowed` (`:4914-4922`).

The two maps use different state strings (`proposed/edited` vs `DRAFT/SAFETY_CHECKED`; `accepted` is storage-only; `AWAITING_IBKR_REPLY/REPLY_CONFIRMED/RECONCILED/EXPIRED/FAILED` are portfolio-only). The API submit-orchestrator uses the **portfolio** enum; the API cancel route + lifecycle/worker writes use the **storage** vocabulary.

### `placeOrder` trigger map (API submit path)

Full sequence around the lone `placeOrder` call (`ibkr_ibapi_order_submission_client.py:525`):

1. **Inbound trigger:** caller of `submit_action_draft_to_paper(draft, submission_repo, event_repo, submission_client, ...)` in `action_draft_submission.py:313-322`.
2. **Pre-call guards** (`action_draft_submission.py:330-427`), all of which block before any IBKR I/O:
   - `submission_client is None` → `blocking_reason="submission_client_unavailable"` (`:330-344`).
   - `draft.account_mode != "paper"` → `blocking_reason="paper_only_required"` (`:346-357`).
   - `draft.dry_run_status != "passed"` → `blocking_reason="dry_run_not_passed"` (`:359-370`).
   - No prior approval row or `approval_status != "approved"` → `blocking_reason="approval_missing"` (`:372-385`).
   - Approval older than `approval_valid_minutes` → `blocking_reason="approval_expired"` (`:387-407`).
   - `require_transition_allowed(from_state=ActionDraftState(existing_record.state), to_state=ActionDraftState.SUBMITTED)` via the portfolio enum (`:409-427`).
3. **placeOrder loop** at `ibkr_ibapi_order_submission_client.py:524-525`, invoked by `submission_client.submit(inputs)` at `action_draft_submission.py:446`.
4. **Persistence on response** (`action_draft_submission.py:450-495`):
   - One `AssetActionDraftEventRecord` written via `event_repo.save_asset_action_draft_event` with `event_type="submitted"` (success) or `"submission_failed"` (rejection), `to_state=AWAITING_IBKR_REPLY` or `REJECTED`, and details `{"ibkr_order_id", "ibkr_perm_id", "rejected_reason"}` (`:450-473`).
   - One `AssetActionDraftSubmissionRecord` upserted via `submission_repo.upsert_asset_action_draft_submission` carrying `ibkr_order_id`, `ibkr_perm_id`, `ibkr_client_id`, `ibkr_status_text`, `rejected_reason`, `submitted_at=now` (`:475-495`).
   - **Note:** the API submit-path uses the portfolio `AWAITING_IBKR_REPLY` state, which does **not** exist in the storage `_ACTION_DRAFT_TRANSITIONS` map; the bridge between the two vocabularies sits in the worker / lifecycle write path (e.g. the `ibkr_submission_audit` and `ibkr_submission_lifecycle` tables described in `sql_repositories.py:5644-5650`).
5. **What `placeOrder` itself returns:** nothing synchronous — confirmation comes via `openOrder` (perm_id) and `orderStatus` (status text) callbacks. The submit method waits on `confirmation_event` for `timeout_seconds` (`ibkr_ibapi_order_submission_client.py:538`). If no confirmation arrives, `OrderSubmissionResult.accepted` is set by `rejected_reason is None` (`:540-547`).

### `cancelOrder` trigger map (the API does NOT call it)

There is **no `cancelOrder` invocation in the API tree**. The cancel route in the broader API (cited for context, outside the in-scope files):

```python
# apps/api/src/portfolio_outlook_api/action_draft.py:780-793 (excerpt)
@router.post("/action-draft/{action_draft_id}/cancel-submitted", ...)
def cancel_submitted_action_draft(action_draft_id: str) -> dict[str, object]:
    """Task 134 product lock §8 — one-way user-initiated cancellation.
    ...
    Does not call IBKR — the worker picks the row up from the database on its
    next sweep tick and issues ``ib.cancelOrder()`` from the
    long-lived TWS session (locked: only the worker owns the socket).
    """
```

- Cancellable source statuses (`action_draft.py:774-776`): `{"submitted","accepted","working","partially_filled"}` — storage-vocabulary statuses matching `_ACTION_DRAFT_TRANSITIONS`.
- The route calls `repo.apply_lifecycle_transition(... new_status="pending_cancellation", ...)` (`action_draft.py:826-830`), exercising the storage map's `submitted/accepted/working/partially_filled → pending_cancellation` edges.
- Looks up `perm_id` from the most recent audit row (`action_draft.py:840-843`) so the worker has the IBKR identifier when it eventually issues `cancelOrder`.
- Appends an `IbkrSubmissionLifecycleEntry(event_type="cancellation_request", ...)` (`action_draft.py:844-862`).

## Cross-cutting observations

- **One real `placeOrder` site in the API.** Only `ibkr_ibapi_order_submission_client.py:525`. Everything else is a protocol declaration (`:100`), docstring (`:18, :254`), gate (`ibkr_order_submission_factory.py`), or read-only surface (`ibkr_submission.py`).
- **Two state-vocabulary islands.** Both apply to the same draft row but use overlapping-but-non-identical sets. The portfolio enum is consumed by the submit orchestrator (`action_draft_submission.py:36-38`); the storage map is consumed by everything that writes through `SqlAlchemyActionDraftRepository.apply_lifecycle_transition`. The bridging only happens because the persisted submission-record carries the portfolio enum string while the canonical `action_drafts.status` column uses the storage vocabulary — no in-code adapter performs the translation explicitly.
- **Idempotency via state guards, not keys.** No app-side idempotency token for the `placeOrder` call. The double-submit guard is purely the `existing_record.state` check before `require_transition_allowed(... → SUBMITTED)` (`action_draft_submission.py:409-427`). IBKR's `order_id` / `perm_id` are the only persisted identifiers.
- **No retry.** A single `submit` is a single `placeOrder` (or three `placeOrder` calls for BRACKET). On `place_order_raised` the caller closes the client (`action_draft_submission.py:447-448`) and persists a `submission_failed` event; the user must re-approve to retry.
- **Connection-error semantics.** The `CONNECTION_ERROR_CODES` set (`:43`) — `{502, 504, 1100, 1101, 1102, 1300, 2110}` — overlaps with but is broader than the manual-status client's `{502, 504, 1100}` (`ibkr_ibapi_manual_status_client.py:73`). Submission additionally treats `1101, 1102, 1300, 2110` as fatal.
- **API-side vs worker-side submission.** The API has a `submit_action_draft_to_paper` orchestrator (`action_draft_submission.py:313`) **and** the worker has its own `submitter.py` (`apps/worker/.../ibkr_submission/submitter.py:1-3`). The storage docstring on `SqlAlchemyIbkrSubmissionAuditRepository` (`sql_repositories.py:5644-5650`) attributes audit writes to "the worker", so the API submit-path is best understood as a manually-triggered alternative to the worker sweep; both call `placeOrder` but only the worker writes `ibkr_submission_audit` rows.
- **Cancellation is strictly worker-owned.** The API's only role in cancellation is to flip status to `pending_cancellation` and stamp a `cancellation_request` lifecycle row; the long-lived TWS socket is locked to the worker (`action_draft.py:786-795`).
- **Watchlists are unrelated to the submission lifecycle.** `ibkr_watchlists.py` shares only the `ibkr_*` prefix; it never touches the submission tables and never invokes the state machine. Its in-process `IMPORT_RUNS` / `IMPORT_CANDIDATES` globals are a session-scoped scratchpad, not a database.

## Open questions / uncertainty

- Two state-vocabulary islands (portfolio enum vs storage map). Whether to unify them or document the bridge explicitly is for Phase 1b architecture review.
- The API-side `submit_action_draft_to_paper` path overlaps with the worker submitter. Whether one is meant to deprecate the other (e.g. API-side as test-injection only, worker as production) is out of scope here.
- `ibkr_watchlists.py` uses module-level mutable globals (`IMPORT_RUNS`, `IMPORT_CANDIDATES`). Whether this is a deliberate development scratchpad or a candidate for storage backing is out of scope for Phase 1a.
- No app-managed idempotency token for `placeOrder`. The state-machine guard prevents double-submit only if the storage row is updated before the user re-clicks; the design relies on storage as the synchronisation point.
