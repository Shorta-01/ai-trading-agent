# `apps/api` — actions, suggestions, and watchlists

**Phase:** 1a (reality components)
**Task:** T-005
**Scope:** 12 modules in `apps/api/src/portfolio_outlook_api/` covering the action-draft HTTP API + orchestrators, the suggestion sync, two watchlist surfaces, two reconciliation surfaces, paper-setup, trading settings, and the research-source archive API (~5666 lines).

This file is descriptive. Every claim cites `path/to/file.py:NNN`. Non-trivial claims carry 3–10 line excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

- `action_draft.py` — 8-route Action Draft HTTP API (Task 133/134 + 134c cancellation).
- `action_draft_submission.py` — orchestrators for approve / submit-to-paper / record-state-event (portfolio enum vocabulary).
- `action_draft_sync.py` — DP → draft orchestrator (orderimpact + dry-run; no submission).
- `suggestion_sync.py` — forecast → suggestion translator (deterministic Dutch labels).
- `watchlist.py` — 5-route in-memory watchlist + AssetListing readiness.
- `watchlist_confirmation_routes.py` — Task 128 cold-start onboarding (5 routes).
- `reconciliation.py` — 6-route Task 135b reconciliation read + manual-review write.
- `reconciliation_sync.py` — reconciliation orchestrator (action-draft submissions → terminal).
- `paper_setup.py` — paper-setup helpers (no FastAPI router).
- `paper_setup_persistence.py` — first-run paper-setup persistence.
- `trading_settings.py` — read/save trading settings (graceful fallback).
- `research_sources.py` — ~30-route metadata-only Research Source Archive API.

## `action_draft.py` (897 lines)

**Path:** `apps/api/src/portfolio_outlook_api/action_draft.py`

### Public surface (FastAPI routes)

- `GET /action-draft/te-keuren` → `list_te_keuren` (`:279-313`)
- `GET /action-draft/{action_draft_id}` → `read_action_draft` (`:316-332`)
- `POST /action-draft` (201) → `create_action_draft` (`:395-555`)
- `PATCH /action-draft/{action_draft_id}` → `patch_action_draft` (`:582-651`)
- `POST /action-draft/{action_draft_id}/approve` → `approve_action_draft` (`:654-693`)
- `POST /action-draft/{action_draft_id}/dismiss` → `dismiss_action_draft` (`:696-731`)
- `POST /action-draft/{action_draft_id}/delete` → `delete_action_draft` (`:734-767`)
- `POST /action-draft/{action_draft_id}/cancel-submitted` → `cancel_submitted_action_draft` (`:779-867`)

Pydantic models (all `extra="forbid"`): `ActionDraftResponse` (`:72-127`) carrying a `status` Literal union of Task 133 user statuses + Task 134 lifecycle statuses; `ActionDraftListResponse` (`:130-135`); `CreateActionDraftFromPackageRequest` (`:138-142`); `CreateActionDraftUserSuppliedRequest` (`:145-156`); `CreateActionDraftRequest` (discriminated union, `:159-174`); `PatchActionDraftRequest` (`:177-182`); `DismissActionDraftRequest` (`:185-188`).

### Collaborators

`SqlAlchemyActionDraftRepository` (every route — read/append/`update_fields`/`update_status`/`apply_lifecycle_transition`/`list_te_keuren_for_account`/`list_by_status`); `SqlAlchemyDecisionPackageRepository` (`_load_decision_package`, `:335-343`); `SqlAlchemyIbkrSyncSnapshotRepository` (cash + position snapshots in create path, `:346-368`); `SqlAlchemyTradingSettingsRepository` (read `user_buffer_eur` from persisted `user_strategy`, `:371-392`); `SqlAlchemyIbkrSubmissionLifecycleRepository` (append `IbkrSubmissionLifecycleEntry` in cancel route, `:804-862`); `SqlAlchemyIbkrSubmissionAuditRepository` (look up `ibkr_perm_id` via `list_for_draft` in cancel route, `:807-887`); composer from `portfolio_outlook_worker.action_draft.composer` (`:51-57`).

### Notable choices

- **Decimal-as-string boundary**: every numeric field in `_serialize_draft` wrapped (`:196-240`): `str(entry.quantity)`, `str(entry.limit_price_local)`, `str(entry.notional_local)`, `str(entry.notional_eur)`, `str(entry.fx_rate_at_creation)`, `str(entry.usable_cash_eur_at_creation)`, `_dec(entry.held_quantity_at_creation)`. Inbound values via `_to_decimal()` raising HTTP 422 with `"Ongeldige decimale waarde voor {field}."` on `InvalidOperation` (`:247-253`).
- **Worker-owned cancellation**: the cancel route flips status to `pending_cancellation`, looks up the most recent placed perm_id via the audit repo, and writes an `IbkrSubmissionLifecycleEntry` tagged `event_type="cancellation_request"`. **Does not call IBKR** — the worker picks the row up on its next sweep tick (`:786-796`).
- `_CANCELLABLE_STATUSES = frozenset({"submitted","accepted","working","partially_filled"})` (`:770-775`); a second cancel click on `pending_cancellation` returns 422 rather than no-op.
- All routes use `provider.checked_connection(require_writable=...)` and explicitly call `checked.connection.commit()` after mutating writes.
- PATCH re-derives both `notional_local = qty * price` and `notional_eur = notional_local * fx_rate_at_creation` (`:619-631`).
- `_load_fx_rate` is `NoReturn` always raising HTTP 422 (`:558-579`); non-EUR DPs without FX snapshot get Dutch error rather than silent fail.
- `create_action_draft` deducts `approved_drafts_notional_eur` from cash before sizing (`:442-448`).

```python
# action_draft.py:786-793 — worker-owned-cancel pattern (excerpt)
"""Task 134 product lock §8 — one-way user-initiated cancellation.

Valid only for in-flight statuses. Transitions the draft to
``pending_cancellation`` and writes one ``ibkr_submission_lifecycle``
row tagged ``event_type='cancellation_request'``. **Does not call
IBKR** — the worker picks the row up from the database on its
next sweep tick and issues ``ib.cancelOrder()`` from the
long-lived TWS session (locked: only the worker owns the socket)."""
```

## `action_draft_submission.py` (571 lines)

**Path:** `apps/api/src/portfolio_outlook_api/action_draft_submission.py`

### Public surface (Python functions, not FastAPI)

- `approve_action_draft(*, draft, submission_repo, event_repo, expected_account_mode, provider_code) -> ApproveActionDraftResult` (`:173-307`).
- `submit_action_draft_to_paper(*, draft, submission_repo, event_repo, submission_client, expected_account_mode, provider_code, approval_valid_minutes) -> SubmitActionDraftResult` (`:313-522`).
- `serialize_submission_for_response`, `serialize_event_for_response` (`:525-567`).

Dataclasses `ApproveActionDraftResult` (`:51-59`) and `SubmitActionDraftResult` (`:62-72`).

### Collaborators

`ActionDraftState`, `InvalidStateTransitionError`, `require_transition_allowed` from `portfolio_outlook_portfolio` (`:34-38`). `IbapiOrderSubmissionClient`, `OrderSubmissionInputs` (`:40-43`). Storage records `AssetActionDraftEventRecord`, `AssetActionDraftRecord`, `AssetActionDraftSubmissionRecord` (`:29-33`). Protocols `_SubmissionRepoProtocol`, `_EventRepoProtocol` (`:78-89`).

### Notable choices

- **Writes** to `asset_action_draft_submissions` (via `upsert_asset_action_draft_submission`) and `asset_action_draft_events` (via `save_asset_action_draft_event`, critical severity).
- **Uses the portfolio enum vocabulary** (DRAFT / SAFETY_CHECKED / USER_APPROVED / SUBMITTED / AWAITING_IBKR_REPLY / REJECTED), **not** the storage vocabulary used by `action_draft.py`.
- Paper-only enforced twice — at draft level (`draft.account_mode == "paper"`) and at the expected-account-mode parameter (`:190-221`).
- Dry-run-must-pass gate: `draft.dry_run_status != "passed"` → blocked (`:223-245`).
- Idempotency/re-approval blocked: looks up existing submission and reads `existing_record.state` to derive `from_state` (`:247-272`).
- **Approval freshness window**: `submit_action_draft_to_paper` computes `approval_age_seconds` from `existing_record.approved_at` and blocks if older than `approval_valid_minutes * 60` (`:387-407`).
- After `placeOrder` returns: SUBMITTED → AWAITING_IBKR_REPLY (accepted) or → REJECTED (`:475-477`), persisted with `submission_client.close()` in a `finally` block (`:445-448`).
- Dutch microcopy: "Approval geblokkeerd", "Approval verlopen", "Order verzonden naar IBKR paper", "Order afgewezen door IBKR".

```python
# action_draft_submission.py:387-396
if existing_record.approved_at is None:
    approval_age_seconds = approval_valid_minutes * 60 + 1
else:
    approval_age_seconds = (
        datetime.now(UTC) - existing_record.approved_at
    ).total_seconds()
if approval_age_seconds > approval_valid_minutes * 60:
    return SubmitActionDraftResult(
        status="blocked",
        status_nl="Approval verlopen",
```

## `action_draft_sync.py` (357 lines)

**Path:** `apps/api/src/portfolio_outlook_api/action_draft_sync.py`

### Public surface (no FastAPI routes)

- `generate_action_drafts(*, decision_packages, repo, expected_account_mode, total_portfolio_value, base_currency, default_buy_value, top_up_pct, reduce_pct, position_exchange_by_conid=None) -> ActionDraftSyncReport` (`:101-297`).
- `serialize_action_draft_for_response(record)` (`:304-357`).

Dataclass `ActionDraftSyncReport` (`:38-51`).

### Collaborators

`ACTIONABLE_LABELS`, `LOCKED_ORDER_TYPE` (LMT), `LOCKED_TIF` (DAY), `DraftSourceContext`, `compute_orderimpact`, `derive_action_draft_sizing`, `run_dry_run_safety_checks` from `portfolio_outlook_portfolio` (`:25-33`). Repo protocol `_ActionDraftRepoProtocol.save_asset_action_draft(record)` (`:54-57`).

### Notable choices

- **Writes** `AssetActionDraftRecord` → `asset_action_drafts`.
- **Locked LMT/DAY/whole-share constants imported, not computed.**
- Two-stage filtering: `package.suggestion_status != "ready"` and `package.suggestion_action_label not in ACTIONABLE_LABELS` (`:127-149`).
- `dry_run_failures_json` persisted as a tuple-or-None (`:244`).
- Decimal-as-string in `serialize_action_draft_for_response` via `_decimal_or_none_str()` helper (`:300-302`).

## `suggestion_sync.py` (262 lines)

**Path:** `apps/api/src/portfolio_outlook_api/suggestion_sync.py`

### Public surface

- `sync_suggestions(*, forecasts, positions, risk_profile, repo, valid_minutes) -> SuggestionSyncReport` (`:132-231`).
- `serialize_suggestion_for_response(record)` (`:234-262`).

Dataclass `SuggestionSyncReport` (`:40-54`).

### Collaborators

`BASELINE_LABEL_TRANSLATOR_MODEL_CODE`, `BASELINE_LABEL_TRANSLATOR_MODEL_VERSION`, `BaselineForecast`, `SuggestionDecision`, `SuggestionInputs`, `translate_forecast_to_label` from `portfolio_outlook_portfolio` (`:27-35`). Repo protocol `_AssetSuggestionRepoProtocol.save_asset_suggestion(record)`.

### Notable choices

- **Writes** `AssetSuggestionRecord` rows; `valid_until = generated_at + timedelta(minutes=valid_minutes)` (`:178`).
- **AI never decides the label** — deterministic translator from the portfolio layer.
- `has_position` derived from the set of position conids (`:143-164`).
- Empty `ibkr_conid` → recorded as `missing_conid` failure (`:153-163`).
- Decimal-as-string: `"confidence_score": str(record.confidence_score)` (`:253`).

## `watchlist.py` (452 lines)

**Path:** `apps/api/src/portfolio_outlook_api/watchlist.py`

### Public surface (FastAPI routes)

- `GET /watchlist/items` → `list_watchlist_items` (`:347-353`)
- `POST /watchlist/items` → `create_watchlist_item` (`:356-415`)
- `GET /watchlist/items/{watchlist_item_id}` → `get_watchlist_item` (`:418-423`)
- `PATCH /watchlist/items/{watchlist_item_id}` → `patch_watchlist_item` (`:426-440`)
- `DELETE /watchlist/items/{watchlist_item_id}` → `archive_watchlist_item` (`:443-452`)

Pydantic: `AssetIdentitySummary` (`:26-31`), `IbkrContractIdentity` (`:34-44`), `WatchlistItem` (`:47-69`), `WatchlistAssetListingLinkStatus` (StrEnum, `:72-77`), `WatchlistAssetListingReadiness` (`:79-118` — all four `*_ready`/`*_allowed` flags hard-False), `WatchlistItemResponse` (`:121-127`), `CreateWatchlistItemRequest` (`:130-142`), `PatchWatchlistItemRequest` (`:145-147`).

### Notable choices

- **In-memory storage anomaly**: `STORE: dict[str, WatchlistItem] = {}` at module level (`:150`). The watchlist items themselves are **not persisted** in any DB. Only the AssetListing/asset identity *lookups* go through `SqlAlchemyResearchSourceArchiveRepository` (`:157-172`).
- `VALID_STATUSES = {"valid","unvalidated","not_found","ambiguous","error","unsupported"}`; only `ibkr_validation_status == "valid"` is allowed for create (HTTP 422, `:362-365`).
- Duplicate detection: HTTP 409 if active item with matching (conid, exchange, currency) exists (`:373-384`).
- Archive is a soft delete that sets `status="archived"` (`:443-452`).

## `watchlist_confirmation_routes.py` (404 lines)

**Path:** `apps/api/src/portfolio_outlook_api/watchlist_confirmation_routes.py`

### Public surface (FastAPI routes)

- `GET /watchlist/confirmation-state` → `read_watchlist_confirmation_state` (`:139-197`)
- `POST /watchlist/confirm` → `confirm_watchlist` (`:200-284`)
- `GET /watchlist/seed-audit` → `read_cold_start_seed_audit` (`:287-325`)
- `GET /watchlist/cold-start-items` → `read_cold_start_items` (`:328-368`)
- `DELETE /watchlist/cold-start-items/{watchlist_item_id}` → `archive_cold_start_item` (`:371-404`)

Pydantic (`extra="forbid"`): `WatchlistConfirmationStateResponse` (`:57-65`), `WatchlistConfirmRequest` (`:67-70`, locked `confirmation_phrase` with `min/max_length=1/64`), `WatchlistConfirmResponse` (`:73-80`), `ColdStartSeedAuditResponse` (`:83-92`), `ColdStartWatchlistItem` (`:95-103`), `ColdStartWatchlistResponse` (`:106-111`).

### Notable choices

- **Writes** `WatchlistConfirmationStateRecord` (state=`"confirmed"`) and `WatchlistConfirmationAuditEntry` (from `"unconfirmed"` → `"confirmed"`, actor=`"user"`, `row_count_at_event=row_count`) (`:255-272`).
- **Locked confirmation phrase**: `"BEVESTIG"` (`:45`).
- Guard cascade in `confirm_watchlist` (`:200-280`): HTTP 400 on phrase mismatch; HTTP 409 if no account configured or already confirmed; HTTP 422 if `row_count == 0` ("Volglijst is leeg.").
- All responses set `safe_for_action_drafts: Literal[False] = False` and `safe_for_orders: Literal[False] = False`.

```python
# watchlist_confirmation_routes.py:47-51 — locked banner
BANNER_TEXT_NL = (
    "Welkom. Je IBKR-rekening is gesynchroniseerd. Het systeem heeft een "
    "startvoorstel voor je Volglijst klaargezet. Bekijk en bevestig in "
    "Volglijst voordat suggesties starten."
)
```

## `reconciliation.py` (505 lines)

**Path:** `apps/api/src/portfolio_outlook_api/reconciliation.py`

### Public surface (FastAPI routes)

- `GET /reconciliation/status?account_id=` → `get_reconciliation_status` (`:295-347`)
- `GET /reconciliation/runs?account_id=&limit=` → `list_reconciliation_runs` (`:350-377`)
- `GET /reconciliation/audit?account_id=&limit=` → `list_reconciliation_audit` (`:380-407`)
- `GET /reconciliation/manual-review?account_id=` → `list_pending_manual_review` (`:410-434`)
- `POST /reconciliation/manual-review/{queue_id}/acknowledge` → `acknowledge_manual_review` (`:437-473`)
- `GET /reconciliation/unmatched-executions?account_id=` → `list_unmatched_executions` (`:476-502`)

Pydantic (`extra="forbid"`): `ReconciliationRunResponse` (`:63-81`, `mode_detected` Literal: completed / skipped_locked / skipped_disconnected / error); `ReconciliationStatusResponse` (`:91-98`); `ReconciliationAuditResponse` (`:101-117`, `pass_name` Literal: orphaned_execution / stale_in_flight / timeout_recovery); `ManualReviewResponse` (`:127-141`, `reason` Literal: timeout_24h_no_data / terminal_state_divergence / unmatched_execution_no_draft); `UnmatchedExecutionResponse` (`:151-165`, `resolution_status`: unresolved / manually_matched / ignored).

### Notable choices

- **Writes** `manual_review_queue.acknowledge` (`:441-471`) → updates `resolution_status`, `resolved_at`, `resolution_note`. Idempotent: re-acknowledging an already-acknowledged row returns the existing row unchanged. **Action Draft state is not touched.**
- All other routes read-only.
- Decimal-as-string in `_serialize_unmatched` (`:253-254`): `"fill_price_local": str(entry.fill_price_local)`, `"fill_quantity": str(entry.fill_quantity)`.
- `Query(default=50, ge=1, le=200)` limit clamp on listing routes.
- `cutoff = datetime.now(UTC) - timedelta(hours=24)` for the "drafts healed last 24h" stat (`:328`).

## `reconciliation_sync.py` (360 lines)

**Path:** `apps/api/src/portfolio_outlook_api/reconciliation_sync.py`

### Public surface (no FastAPI routes)

`reconcile_submissions(*, submissions, open_orders, executions, submitted_quantity_by_draft_id, submission_repo, event_repo) -> ReconciliationReport` (`:226-360`).

Dataclass `ReconciliationReport` (`:41-54`).

### Collaborators

`ActionDraftState`, `InvalidStateTransitionError`, `coerce_state`, `require_transition_allowed` from `portfolio_outlook_portfolio` (`:31-36`). Storage records `AssetActionDraftEventRecord`, `AssetActionDraftSubmissionRecord`, `IbkrExecutionSnapshotRecord`, `IbkrOpenOrderSnapshotRecord`. Repo protocols `_SubmissionRepoProtocol`, `_EventRepoProtocol` (`:57-66`).

### Notable choices

- **Writes/upserts** `asset_action_draft_submissions`; appends critical-severity `asset_action_draft_events` rows.
- **Uses the portfolio enum vocabulary**, not storage statuses.
- Classification logic (`_classify`, `:93-147`): filled_qty ≥ submitted_quantity → FILLED; not in open_orders + no fills → CANCELLED; `"cancelled"`/`"apicancelled"`/`"inactive"` → CANCELLED; `"submitted"`/`"presubmitted"`/`"working"` → still working.
- **Two-step terminal auto-advance** — terminal IBKR states (FILLED/CANCELLED/REJECTED) immediately get a second upsert to RECONCILED in the same orchestrator call (`:199-222`).
- `reconcilable_states` literal set guards entry (`:257-262`).
- All exceptions converted to `failures: list[dict[str, str]]` in the report (no HTTP layer here).

```python
# reconciliation_sync.py:200-208 — terminal auto-advance to RECONCILED
if next_state in {
    ActionDraftState.FILLED,
    ActionDraftState.CANCELLED,
    ActionDraftState.REJECTED,
}:
    reconciled_now = datetime.now(UTC)
    next_fields = dict(intermediate.__dict__)
    next_fields["state"] = ActionDraftState.RECONCILED.value
    next_fields["last_state_transition_at"] = reconciled_now
```

## `paper_setup.py` (105 lines)

**Path:** `apps/api/src/portfolio_outlook_api/paper_setup.py`

### Public surface

- `SetupPreviewInput` Pydantic model (`:15-28`) with `validate_cash_not_empty` validator.
- `get_setup_status()` (`:31-41`) — returns hard-coded `not_configured` dict.
- `get_setup_defaults()` (`:44-55`) — `default_starting_cash="10000"`, `default_portfolio_name="Mijn paper portefeuille"`, `live_trading_allowed: False`.
- `create_setup_preview(input_data)` (`:58-105`).

Constants: `BASE_CURRENCY_EUR = "eur"`, `SETUP_STATUS_FIRST_RUN = "first_run"`, `SETUP_STATUS_NOT_CONFIGURED = "not_configured"`, `SETUP_STATUS_PREVIEW_READY = "preview_ready"` plus three warning codes (`:6-12`).

### Notable choices

- **Pure-Python helpers**; no FastAPI router. No storage writes — preview never persisted (`"persisted": False`).
- Paper-only enforcement: `create_setup_preview` rejects non-EUR (`:59-60`), `starting_cash <= 0`, and three explicit confirmations (`user_confirmed_paper_only`, `user_confirmed_no_real_money`, `user_confirmed_no_broker_order`) (`:70-75`). All errors via `ValueError` (caller translates to HTTP).

## `paper_setup_persistence.py` (127 lines)

**Path:** `apps/api/src/portfolio_outlook_api/paper_setup_persistence.py`

### Public surface

`persist_first_run_paper_setup(payload, storage_settings, connection_provider_factory=None, repository_factory=None, now_provider=..., id_provider=...) -> PaperSetupPersistenceResult` (`:44-127`).

Dataclass `PaperSetupPersistenceResult` (`:29-32`).

### Notable choices

- **Writes** via `SqlAlchemyPaperPortfolioSetupRepository.create_setup(CreatePaperPortfolioSetupRequest(...))` (`:85-95`) → `paper_portfolio_setups`.
- All three "blocked" branches return Dutch microcopy: `"Opslag staat uit. Opslaan is geblokkeerd."`, `"Database-url ontbreekt. Opslaan is geblokkeerd."`, `"Writes zijn geblokkeerd door migratie-readiness."`, `"Databaseverbinding mislukt. Opslaan is geblokkeerd."` (`:62-126`).
- Catches both `StorageConnectionNotReadyError` (migration-readiness block) and `StorageConnectionError` (general connection failure) separately.
- DI hooks: `connection_provider_factory`, `repository_factory`, `now_provider`, `id_provider` are caller-overridable.

## `trading_settings.py` (197 lines)

**Path:** `apps/api/src/portfolio_outlook_api/trading_settings.py`

### Public surface

- `TradingSettingsUpdateInput` (`:34-37`).
- `build_default_trading_settings_response(...)` (`:76-79`).
- `build_trading_settings_response(...)` (`:82-131`).
- `update_trading_settings_response(...)` (`:134-197`).

### Notable choices

- **Writes** via `SqlAlchemyTradingSettingsRepository.save_settings(SaveTradingSettingsRequest)` (`:166-175`) → `trading_settings` with `settings_id="default"`, `status="active"`, `source="api"`.
- **Graceful fallback to domain defaults** on storage errors: storage off, db-url empty, generic connection error all degrade to defaults with `"Standaardinstellingen geladen door veilige foutafhandeling."`.
- Separate `StoragePersistenceBlockedError` handling for write paths (`:184-190`).
- Locked safety statement on every response (`:69-72`): `"Toegestane beleggingen zijn harde veiligheidsregels. Mijn strategie bepaalt alleen voorkeur en rangschikking."`

## `research_sources.py` (1429 lines)

**Path:** `apps/api/src/portfolio_outlook_api/research_sources.py`

### Public surface (FastAPI routes — ~30 total)

Per the Route catalogue below; the cluster covers research sources / uploaded files / URLs / notes / document sets + members / classifications / asset links / processing statuses / credibility / prompt-injection scans / evidence items / evidence-ledger links / gate outcomes / conflict findings / text extraction.

Pydantic input models (`:86-311`): `ResearchSourceInput`, `ResearchUploadedFileMetadataInput`, `ResearchUrlMetadataInput`, `ResearchUserNoteInput`, `ResearchDocumentSetInput`, `ResearchDocumentSetMemberInput`, `ResearchDocumentClassificationInput`, `ResearchSourceAssetLinkInput`, `ResearchProcessingStatusInput`, `ResearchSourceCredibilityAssessmentInput`, `ResearchSourceEvidenceItemInput`, `ResearchPromptInjectionScanInput`, `ResearchSourceEvidenceLedgerLinkInput`, `ResearchGateOutcomeInput`, `ResearchSourceConflictFindingInput`.

### Notable choices

- **Single repo**: `SqlAlchemyResearchSourceArchiveRepository` via the `_with_repo` helper (`:426-458`) for all routes. Writes to 16 tables (`research_sources`, `research_uploaded_file_metadata`, `research_url_metadata`, `research_user_notes`, `research_document_sets`, `research_document_set_members`, `research_document_classifications`, `research_source_asset_links`, `research_source_processing_statuses`, `research_source_credibility_assessments`, `research_source_evidence_items`, `research_source_prompt_injection_scans`, `research_source_evidence_ledger_links`, `research_gate_outcomes`, `research_source_conflict_findings`, `research_extracted_texts`).
- **Hard "blocks_suggestions" lock**: every persisted record carries `blocks_suggestions=True`, `safe_to_use_for_suggestions=False`, `can_be_used_in_research=False`, `can_be_used_in_suggestions=False`. Even when the input payload tries to set `blocks_suggestions=False` on the prompt-injection scan, it's coerced back: `blocks_suggestions=True if payload.blocks_suggestions is False else payload.blocks_suggestions` (`:1015`).
- **File upload safety** (`_archive_uploaded_file`, `:333-373`): sanitises filename (rejects `/`, `\`, `..`); validates extension and Content-Type; streams in 1 MiB chunks computing `sha256` and total `size`; HTTP 413 if size exceeds `max_file_size_bytes` (`:357-360`); final filename is `f"{library_source_id}-{file_hash[:16]}-{original_name}"` and must resolve inside the archive dir (path-traversal guard).
- **Text extraction safety** (`_extract_plain_research_text`, `:376-423`): UTF-8 only (BOM-aware via `utf-8-sig`); trimmed to `max_output_characters`; hash of output; stored at `{library_source_id}-{text_hash[:16]}.txt`.
- Storage off → HTTP 503 with `"Opslag is niet verbonden. De onderzoeksbibliotheek is nog niet beschikbaar."` (`:438-458`).
- Every `_ok` response carries `status_nl="OK"`, `message_nl`, and `help_nl` Dutch microcopy e.g. *"Zelfs hoge credibility ontgrendelt geen suggesties in versie 1 foundation."* (`:994`).

## Route catalogue (consolidated)

| Method | Path | Handler | Source |
|---|---|---|---|
| GET | `/action-draft/te-keuren` | `list_te_keuren` | `action_draft.py:282` |
| GET | `/action-draft/{action_draft_id}` | `read_action_draft` | `action_draft.py:317` |
| POST | `/action-draft` | `create_action_draft` | `action_draft.py:396` |
| PATCH | `/action-draft/{action_draft_id}` | `patch_action_draft` | `action_draft.py:585` |
| POST | `/action-draft/{action_draft_id}/approve` | `approve_action_draft` | `action_draft.py:658` |
| POST | `/action-draft/{action_draft_id}/dismiss` | `dismiss_action_draft` | `action_draft.py:700` |
| POST | `/action-draft/{action_draft_id}/delete` | `delete_action_draft` | `action_draft.py:738` |
| POST | `/action-draft/{action_draft_id}/cancel-submitted` | `cancel_submitted_action_draft` | `action_draft.py:783` |
| GET | `/watchlist/items` | `list_watchlist_items` | `watchlist.py:348` |
| POST | `/watchlist/items` | `create_watchlist_item` | `watchlist.py:357` |
| GET | `/watchlist/items/{watchlist_item_id}` | `get_watchlist_item` | `watchlist.py:419` |
| PATCH | `/watchlist/items/{watchlist_item_id}` | `patch_watchlist_item` | `watchlist.py:427` |
| DELETE | `/watchlist/items/{watchlist_item_id}` | `archive_watchlist_item` | `watchlist.py:444` |
| GET | `/watchlist/confirmation-state` | `read_watchlist_confirmation_state` | `watchlist_confirmation_routes.py:143` |
| POST | `/watchlist/confirm` | `confirm_watchlist` | `watchlist_confirmation_routes.py:201` |
| GET | `/watchlist/seed-audit` | `read_cold_start_seed_audit` | `watchlist_confirmation_routes.py:291` |
| GET | `/watchlist/cold-start-items` | `read_cold_start_items` | `watchlist_confirmation_routes.py:332` |
| DELETE | `/watchlist/cold-start-items/{watchlist_item_id}` | `archive_cold_start_item` | `watchlist_confirmation_routes.py:372` |
| GET | `/reconciliation/status` | `get_reconciliation_status` | `reconciliation.py:299` |
| GET | `/reconciliation/runs` | `list_reconciliation_runs` | `reconciliation.py:354` |
| GET | `/reconciliation/audit` | `list_reconciliation_audit` | `reconciliation.py:384` |
| GET | `/reconciliation/manual-review` | `list_pending_manual_review` | `reconciliation.py:414` |
| POST | `/reconciliation/manual-review/{queue_id}/acknowledge` | `acknowledge_manual_review` | `reconciliation.py:441` |
| GET | `/reconciliation/unmatched-executions` | `list_unmatched_executions` | `reconciliation.py:480` |
| POST | `/research/sources` | `create_research_source` | `research_sources.py:462` |
| GET | `/research/sources` | `list_research_sources` | `research_sources.py:497` |
| GET | `/research/sources/{library_source_id}` | `get_research_source` | `research_sources.py:482` |
| POST | `/research/sources/{library_source_id}/uploaded-file-metadata` | `create_uploaded_file_metadata` | `research_sources.py:519` |
| POST | `/research/sources/{library_source_id}/upload-file` | `upload_research_source_file` | `research_sources.py:543` |
| GET | `/research/sources/{library_source_id}/uploaded-file-metadata` | `get_uploaded_file_metadata` | `research_sources.py:649` |
| POST | `/research/sources/{library_source_id}/url-metadata` | `create_url_metadata` | `research_sources.py:662` |
| GET | `/research/sources/{library_source_id}/url-metadata` | `get_url_metadata` | `research_sources.py:682` |
| POST | `/research/sources/{library_source_id}/user-note` | `create_user_note` | `research_sources.py:697` |
| GET | `/research/sources/{library_source_id}/user-note` | `get_user_note` | `research_sources.py:723` |
| POST | `/research/document-sets` | `create_document_set` | `research_sources.py:738` |
| GET | `/research/document-sets/{document_set_id}` | `get_document_set` | `research_sources.py:755` |
| POST | `/research/document-sets/{document_set_id}/members` | `add_document_set_member` | `research_sources.py:766` |
| GET | `/research/document-sets/{document_set_id}/members` | `list_document_set_members` | `research_sources.py:787` |
| POST | `/research/sources/{library_source_id}/classifications` | `create_classification` | `research_sources.py:801` |
| GET | `/research/sources/{library_source_id}/classifications/latest` | `get_latest_classification` | `research_sources.py:825` |
| POST | `/research/sources/{library_source_id}/asset-links` | `create_asset_link` | `research_sources.py:842` |
| GET | `/research/sources/{library_source_id}/asset-links` | `list_asset_links_for_source` | `research_sources.py:866` |
| GET | `/research/asset-links/unconfirmed-detected` | `list_unconfirmed_asset_links` | `research_sources.py:882` |
| POST | `/research/sources/{library_source_id}/processing-status` | `create_processing_status` | `research_sources.py:896` |
| GET | `/research/sources/{library_source_id}/processing-status/latest` | `get_latest_processing_status` | `research_sources.py:917` |
| POST | `/research/sources/{library_source_id}/credibility-assessment` | `create_source_credibility_assessment` | `research_sources.py:936` |
| GET | `/research/sources/{library_source_id}/credibility-assessment/latest` | `get_latest_source_credibility_assessment` | `research_sources.py:969` |
| POST | `/research/sources/{library_source_id}/prompt-injection-scan` | `create_prompt_injection_scan_status` | `research_sources.py:1001` |
| GET | `/research/sources/{library_source_id}/prompt-injection-scan/latest` | `get_latest_prompt_injection_scan` | `research_sources.py:1031` |
| POST | `/research/sources/{library_source_id}/classify-deterministic` | `classify_research_source_deterministic` | `research_sources.py:1060` |
| POST | `/research/sources/{library_source_id}/extract-text` | `extract_research_source_text` | `research_sources.py:1131` |
| POST | `/research/sources/{library_source_id}/evidence-items` | `create_source_evidence_item` | `research_sources.py:1225` |
| GET | `/research/sources/{library_source_id}/evidence-items` | `list_source_evidence_items` | `research_sources.py:1261` |
| POST | `/research/sources/{library_source_id}/evidence-ledger-links` | `create_source_evidence_ledger_link` | `research_sources.py:1275` |
| GET | `/research/sources/{library_source_id}/evidence-ledger-links` | `list_source_evidence_ledger_links` | `research_sources.py:1309` |
| GET | `/research/evidence-items/{evidence_item_id}/evidence-ledger-links` | `list_evidence_item_ledger_links` | `research_sources.py:1321` |
| POST | `/research/gate-outcomes` | `create_research_gate_outcome` | `research_sources.py:1331` |
| GET | `/research/sources/{library_source_id}/gate-outcomes` | `list_research_gate_outcomes_by_source` | `research_sources.py:1366` |
| GET | `/research/evidence-items/{evidence_item_id}/gate-outcomes` | `list_research_gate_outcomes_by_evidence_item` | `research_sources.py:1374` |
| POST | `/research/conflict-findings` | `create_source_conflict_finding` | `research_sources.py:1382` |
| GET | `/research/sources/{library_source_id}/conflict-findings` | `list_source_conflict_findings` | `research_sources.py:1417` |
| GET | `/research/evidence-items/{evidence_item_id}/conflict-findings` | `list_evidence_conflict_findings` | `research_sources.py:1425` |

`paper_setup.py`, `paper_setup_persistence.py`, `trading_settings.py`, `action_draft_submission.py`, `action_draft_sync.py`, `suggestion_sync.py`, `reconciliation_sync.py` expose **no FastAPI routes** — they are orchestrators / helpers consumed elsewhere.

## State-machine touchpoints (action-draft cluster)

Two distinct vocabularies coexist:

| Layer | Enum/keys | Defined at |
|---|---|---|
| `portfolio_outlook_portfolio.ActionDraftState` | DRAFT, SAFETY_CHECKED, USER_APPROVED, SUBMITTED, AWAITING_IBKR_REPLY, REPLY_CONFIRMED, WORKING, FILLED, CANCELLED, REJECTED, RECONCILED, EXPIRED, FAILED | `packages/portfolio/src/portfolio_outlook_portfolio/action_draft_state_machine.py:37-50` |
| Storage `_ACTION_DRAFT_TRANSITIONS` keys | proposed, edited, user_approved, submitted, accepted, working, partially_filled, pending_cancellation, dismissed, deleted, superseded, filled, cancelled, rejected, awaiting_reply_timeout, requires_manual_review | `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:4820-4911` |

**Vocabulary mismatch** (already surfaced in T-004's `api-ibkr-submission-and-watchlists.md`): the high-level `action_draft.py` HTTP API uses the **storage** vocabulary — see the `ActionDraftResponse.status` Literal at `action_draft.py:95-113`. The orchestrators `action_draft_submission.py` and `reconciliation_sync.py` use the **portfolio** vocabulary. The two halves do not refer to each other — they map to two parallel storage tables (`action_drafts` vs. `asset_action_draft_submissions`).

**Routes that mutate `action_drafts.status`** (via `SqlAlchemyActionDraftRepository.update_status` / `update_fields` / `apply_lifecycle_transition`):

| Route | Repo method | Storage transition triggered |
|---|---|---|
| `PATCH /action-draft/{id}` | `repo.update_fields(... actor="user")` | Implicit `proposed → edited` when qty/price changes |
| `POST /action-draft/{id}/approve` | `repo.update_status(new_status="user_approved")` | `proposed → user_approved` or `edited → user_approved` |
| `POST /action-draft/{id}/dismiss` | `repo.update_status(new_status="dismissed", dismissed_reason=...)` | `proposed → dismissed`, `edited → dismissed`, or `user_approved → dismissed` |
| `POST /action-draft/{id}/delete` | `repo.update_status(new_status="deleted")` | `proposed → deleted`, `edited → deleted`, or `user_approved → deleted` |
| `POST /action-draft/{id}/cancel-submitted` | `repo.apply_lifecycle_transition(new_status="pending_cancellation")` | `submitted → pending_cancellation`, `accepted → pending_cancellation`, `working → pending_cancellation`, `partially_filled → pending_cancellation` |

Every storage-side rejection bubbles up as `ActionDraftStateTransitionError` and is converted to HTTP 422 with a Dutch detail at each call site (e.g. `action_draft.py:643-646, :685-688, :723-726, :759-762, :831-834`).

The orchestrators in `action_draft_submission.py` and `reconciliation_sync.py` call `portfolio_outlook_portfolio.require_transition_allowed(from_state=..., to_state=...)` against the in-memory `ALLOWED_TRANSITIONS` map — these mutate the `asset_action_draft_submissions.state` column, not `action_drafts.status`.

## Storage write-path map

| Module | Repo used | Tables written |
|---|---|---|
| `action_draft.py` | `SqlAlchemyActionDraftRepository` | `action_drafts` (+ `action_draft_audit` hash-chained per draft via `append`/`update_status`/`update_fields`/`apply_lifecycle_transition`) |
| `action_draft.py` (cancel route) | `SqlAlchemyIbkrSubmissionLifecycleRepository` | `ibkr_submission_lifecycle` (one `event_type="cancellation_request"` row) |
| `action_draft.py` (cancel route, read-only) | `SqlAlchemyIbkrSubmissionAuditRepository.list_for_draft` | reads `ibkr_submission_audit` |
| `action_draft_submission.py` | `_SubmissionRepoProtocol.upsert_asset_action_draft_submission` | `asset_action_draft_submissions` |
| `action_draft_submission.py` | `_EventRepoProtocol.save_asset_action_draft_event` | `asset_action_draft_events` |
| `action_draft_sync.py` | `_ActionDraftRepoProtocol.save_asset_action_draft` | `asset_action_drafts` |
| `suggestion_sync.py` | `_AssetSuggestionRepoProtocol.save_asset_suggestion` | `asset_suggestions` |
| `watchlist.py` | `SqlAlchemyResearchSourceArchiveRepository` (read-only) | reads `asset_listings`, `assets`; **no watchlist writes** — `STORE` is in-memory |
| `watchlist_confirmation_routes.py` | `SqlAlchemyWatchlistConfirmationStateRepository.upsert` | `watchlist_confirmation_states` |
| `watchlist_confirmation_routes.py` | `SqlAlchemyWatchlistConfirmationAuditRepository.append` | `watchlist_confirmation_audit` |
| `watchlist_confirmation_routes.py` | `SqlAlchemyWatchlistItemSeedRepository.archive_by_id` | `watchlist_item_seeds` |
| `watchlist_confirmation_routes.py` (read) | `SqlAlchemyColdStartSeedAuditRepository.find_by_account_id` | reads `cold_start_seed_audit` |
| `reconciliation.py` | `SqlAlchemyManualReviewQueueRepository.acknowledge` | `manual_review_queue` |
| `reconciliation.py` (other routes) | read from `Sql…RunAuditRepository`, `Sql…AuditRepository`, `Sql…UnmatchedExecutionAuditRepository` | reads `reconciliation_run_audit`, `reconciliation_audit`, `unmatched_execution_audit` |
| `reconciliation_sync.py` | `_SubmissionRepoProtocol.upsert_asset_action_draft_submission` | `asset_action_draft_submissions` |
| `reconciliation_sync.py` | `_EventRepoProtocol.save_asset_action_draft_event` | `asset_action_draft_events` (critical severity) |
| `paper_setup_persistence.py` | `SqlAlchemyPaperPortfolioSetupRepository.create_setup` | `paper_portfolio_setups` |
| `trading_settings.py` | `SqlAlchemyTradingSettingsRepository.save_settings` | `trading_settings` |
| `research_sources.py` | `SqlAlchemyResearchSourceArchiveRepository.save_*` | 16 tables (`research_sources`, `research_uploaded_file_metadata`, …) |

**Audit-chain pattern (`action_draft_audit`)**: mutations carry `audit_trail_hash` + `previous_draft_hash` surfaced in `ActionDraftResponse` (`action_draft.py:121-122`) and `_serialize_draft` (`:234-235`). The storage layer appends a hash-chained audit row per draft on every status/field update. The API never computes the hash itself.

## Cross-cutting observations

1. **Two vocabularies, two tables.** `action_draft.py` operates on `action_drafts` using storage-status strings. `action_draft_submission.py` + `reconciliation_sync.py` operate on `asset_action_draft_submissions` using the portfolio `ActionDraftState` enum. They share concepts (approve, submit, cancel) but are not interconnected in this code — the HTTP routes only touch the storage-status path.

2. **Worker-owned-cancel** is consistent. The API only flips status to `pending_cancellation` and writes a `cancellation_request` lifecycle row. The `ib.cancelOrder()` call belongs to the worker. The storage map at `sql_repositories.py:4881-4886` accommodates the race where IBKR fills before the cancel propagates.

3. **Decimal-as-string discipline** is consistent across every wire format. Inbound Decimals always pass through helpers raising HTTP 422 with Dutch microcopy on `InvalidOperation` (`action_draft.py:247-253`).

4. **"Storage unavailable" pattern is uniform.** `STORAGE_UNAVAILABLE_DETAIL = "Opslag is niet beschikbaar."` + `_raise_storage_unavailable()` → HTTP 503. `research_sources.py` uses a longer phrase `"Opslag is niet verbonden. ..."` (`:441`).

5. **Paper-only / safety-flag-False discipline.** Every persisted record exposes `safe_for_submission` / `safe_for_orders` / `safe_for_broker_submission` / `safe_for_action_drafts` set to `False` via Pydantic `Literal[False] = False` defaults. `action_draft_submission.py` further hardens by checking `draft.account_mode.strip().lower() != "paper"` twice.

6. **In-memory watchlist anomaly.** `watchlist.py:150` declares `STORE: dict[str, WatchlistItem] = {}` actively used by all five `/watchlist/items*` routes. This module persists nothing about watchlist items themselves; the persisted parallel lives in `SqlAlchemyWatchlistItemSeedRepository` driven from `watchlist_confirmation_routes.py`. **Two watchlist surfaces co-exist**: the in-memory one used by Volglijst UI, and the seed/confirmation table used by cold-start onboarding.

7. **Dutch microcopy is dense and load-bearing.** Notable locked phrases: `"BEVESTIG"` (`watchlist_confirmation_routes.py:45`), `"Opslag is niet beschikbaar."`, `"Geen IBKR-rekening geconfigureerd."`, `"Actiedraft niet gevonden."`, `"Cancel niet toegestaan: draft is niet in een actief IBKR-status..."` (`action_draft.py:818-821`).

8. **Idempotency / no-op patterns.** `acknowledge_manual_review` returns the existing row unchanged on replay (idempotent). The `cancel-submitted` route excludes `pending_cancellation` from `_CANCELLABLE_STATUSES` so a second click is 422, not no-op. `submit_action_draft_to_paper` re-checks every gate even if state suggests approval was already granted.

9. **Storage migration-readiness gate** is consistently caught: `StorageConnectionNotReadyError` separately from `StorageConnectionError` in `paper_setup_persistence.py:110-127` and `StoragePersistenceBlockedError` in `trading_settings.py:184` and `research_sources.py:454-458`.

10. **The `_load_fx_rate` is a stub**: `action_draft.py:558-579` is declared `NoReturn` and always raises HTTP 422. Non-EUR Decision Packages cannot create drafts without an external FX sync — enforced via the create path's `package.currency_local == "EUR"` branch (`:454-459`).

## Open questions / uncertainty

- The two state-vocabulary islands (portfolio enum vs storage map) are surfaced again — already in T-004's submission doc. Whether to unify is for Phase 1b architecture review.
- The two watchlist surfaces (in-memory `STORE` vs. persisted `watchlist_item_seeds`) coexist with no cross-reference in code. Whether the in-memory surface is candidate for promotion to persistence is out of scope for Phase 1a.
- `_load_fx_rate` always raises HTTP 422 — the API has no path to create non-EUR drafts without an external FX sync. Whether FX needs to be wired earlier in the chain is for Phase 1c gap analysis.
- `research_sources.py` is ~1429 lines with ~30 routes hung on a single repository class. Whether the size warrants splitting is for Phase 1b architecture review.
- `reconciliation_sync.py` two-step terminal auto-advance (FILLED/CANCELLED/REJECTED → RECONCILED in the same call) bypasses the audit row for the intermediate state. Whether this is intentional staging or a candidate for explicit two-event audit is a Phase 1b architecture-review question.
