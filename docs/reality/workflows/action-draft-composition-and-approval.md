# Reality — workflow: action-draft composition + approval

**Scope.** End-to-end trace from action-draft composition (worker pure-function composer, two entry paths) → dry-run safety checks → persisted `status="proposed"` row → user actions in the frontend (`edit` / `dismiss` / `delete` / `approve` via "JA" confirmation token) → `user_approved` terminal of T-018's scope. The downstream submission flow (`user_approved → submitted → ...`) is T-019's territory.

Action drafts are the **only path** through which the system can submit an order to IBKR. AGENTS.md §3.2 lock: "The system never submits an order without explicit user approval." This doc traces the architecture that enforces that lock.

**Sibling reality docs:**

- `docs/reality/components/portfolio-guards-and-state-machines.md` (T-002) — `action_draft_safety.py` 11 A-K gates, state machine.
- `docs/reality/components/worker-actions-and-reconciliation.md` §1 (composer) + §13 (state-machine transitions) (T-007).
- `docs/reality/components/api-actions-suggestions-and-watchlists.md` (T-005) — API routes.
- `docs/reality/components/web-components-feature-grids.md` §§1-2 (T-008) — `<ActionDraftEditForm>` + `<ActionDraftGrid>`.
- `docs/reality/components/web-api-client-and-text.md` §2 (T-009) — `apiClient` action-draft methods.
- `docs/reality/workflows/decision-package-composition.md` (T-017) — produces the Decision Packages that compose-from-DP path consumes.

## 0. TL;DR

A user reviews their `/ibkr-acties` "Te keuren" tab in the frontend. Each row in the grid is a **proposed** action draft. For each:

- Click `Bewerken` → opens `<ActionDraftEditForm>` → PATCH route adjusts quantity / limit price / note → `status` stays `proposed`/`edited`.
- Click `Dismiss` → input reason → POST `/dismiss` → `status="dismissed"` terminal.
- Click `Verwijder` → confirm prompt → POST `/delete` → `status="deleted"` terminal.
- Click `Goedkeuren` → **JA token confirmation prompt** → POST `/approve` → `status="user_approved"` (the boundary of T-018).

The drafts in the grid arrive via **two composition paths** running in the worker:

1. **Decision-Package-driven** (`compose_action_draft_from_decision_package`): triggered on-demand from the API when the user actions a DP in the `<DecisionPackageDetail>` page. Pure function — no I/O, no AI; takes a Decision Package + portfolio context + cash buffer; emits a draft proposal.
2. **User-supplied** (`compose_action_draft_user_supplied`): the Volglijst quick-action path — user picks an asset + side + quantity + limit price directly without a DP.

Both paths run the **11 A-K safety gates** in dry-run mode before persisting. The persisted draft starts at `status="proposed"`, carries hard `safe_for_submission=False`, and waits for the user.

The composer **does not write to storage** — it returns an `ActionDraftEntry` record; the caller persists. The worker doesn't currently invoke either compose path on its own (no scheduler job for action-draft generation); composition is API-route-driven today.

## 1. The two composition entry points

Both live in `apps/worker/src/portfolio_outlook_worker/action_draft/composer.py` (525 lines per T-007 §1).

### 1.1 `compose_action_draft_from_decision_package` (`composer.py:91-266`)

Inputs:

- `decision_package: DecisionPackageEntry` — the Decision Package row (produced by T-017).
- `portfolio_context: PortfolioContextSnapshot` — current cash, position, recent execution count, hold-time.
- `user_buffer_eur: Decimal` — minimum cash buffer from user settings (T-061 §6 documents the trading-settings JSON column).
- `kelly_fraction: Decimal` — sizing fraction (T-002 / T-015 §1 — defaulted to 0.5 today via `DEFAULT_KELLY_FRACTION` in `kelly_sizing.py:51`, despite intent of 0.25 Moderate; T-061 §10 Phase 1c gap).

Returns an `ActionDraftEntry` record OR raises a typed exception per dry-run failure.

### 1.2 `compose_action_draft_user_supplied` (`composer.py:269-394`)

Inputs:

- `decision_package_id=None` (no DP — Volglijst quick path).
- `user_supplied_quantity: Decimal`, `user_supplied_limit_price: Decimal`, `user_supplied_side: str` (BUY/SELL).
- `portfolio_context`, `user_buffer_eur`, plus same dry-run pipeline.

Used when the user picks a non-DP-backed asset to act on directly. The composer runs the same 11 A-K dry-run gates but does not consult a Decision Package; the user's quantity + limit price are taken at face value.

### 1.3 Initial state

Both composer paths emit an `ActionDraftEntry` with:

- `status = "proposed"` (storage-vocabulary initial state per T-007 §13).
- `safe_for_submission = False` (hard floor — see §7.4).
- `audit_trail_hash` (SHA-256 over canonical JSON; same Decimal-as-string discipline as Decision Package per T-017 §6).
- `previous_draft_hash = None` on first draft; chained on subsequent edits.
- `dry_run_passed: bool` — set by the safety pipeline at §3.

## 2. The dry-run safety pipeline (`action_draft_safety.py`)

Per T-002 `portfolio-guards-and-state-machines.md`:

`packages/portfolio/src/portfolio_outlook_portfolio/action_draft_safety.py` carries the dry-run pipeline. Entry: `run_dry_run_safety_checks(...)` (`action_draft_safety.py:461` per T-055 CC findings — rank D 24).

### 2.1 The 11 A-K safety gates (V1 product lock)

Per T-002 §3 (locked by V1 product brainstorm). The gates run in alphabetical order; each returns a `SafetyGateResult(name, passed, detail_nl)`. The pipeline doesn't short-circuit — all 11 evaluate; the draft is "passed" only if every gate passes.

| Gate | Name | Concern | Locked threshold (V1) |
|---|---|---|---|
| A | `paper_only_mode_engaged` | system is in paper mode | `paper_only_mode == True` |
| B | `instrument_is_listed_in_universe` | asset is in the user's allowed universe | `asset_listing.is_active AND in_allowed_universe` |
| C | `order_type_is_limit_day` | only LMT DAY orders permitted | `order_type=="LMT" AND time_in_force=="DAY"` |
| D | `quantity_is_whole_shares` | no fractional shares | `quantity == quantity.quantize(Decimal("1"))` |
| E | `limit_price_within_tolerance` | limit price within X% of last close | `abs(limit - last_close) / last_close ≤ 0.05` |
| F | `position_size_within_caps` | sizing caps from `UserStrategySettings.max_position_pct` (default 10%) | `position_value / portfolio_total ≤ 10%` |
| G | `cash_buffer_respected` | minimum cash buffer after the order | `cash_after ≥ user_buffer_eur` |
| H | `hold_time_observed` (sell-side only) | minimum hold time before sell | `position_age ≥ 7 days` |
| I | `daily_order_count_under_limit` | per-day order rate cap | `today_count < 10` |
| J | `no_duplicate_within_window` | no duplicate ticker/side action in last X hours | `latest_same_action_age ≥ 1 hour` |
| K | `decision_package_chain_intact` (DP path only) | DP `previous_package_hash` chain is unbroken | `previous_package_hash matches OR is None` |

T-002 documents the exact thresholds in the per-gate evidence; T-018 references the gate list as a stable cross-cut.

### 2.2 Dry-run pipeline result

After running all 11 gates, `run_dry_run_safety_checks` returns a `DryRunSafetyReport(passed: bool, gate_results: tuple[SafetyGateResult, ...])`. The composer reads this to:

- Set `dry_run_passed: bool` on the draft.
- If `passed==False`, raise a typed exception (`SafetyCheckFailedError`) carrying the failing gate detail — the caller decides whether to surface the rejection to the user OR fail silently (the API does the former; the worker compose path bubbles up).

Per T-002 §3, the dry-run report is **never persisted directly** — only its summary (`dry_run_passed`) is stored on the draft row. Phase 1c surface: a future "show me why this draft is blocked" UI would need the full report persisted.

### 2.3 Decimal-as-string discipline

Per T-002 `portfolio-money-and-accounting.md` — all gate evaluations use Decimal arithmetic; no float intermediates. The `limit price within tolerance` gate (E) computes `abs(limit - close) / close` as a Decimal; `cash buffer` (G) compares `Decimal` to `Decimal`.

## 3. Storage write — `action_drafts` row

The composer **returns** the `ActionDraftEntry`; the caller is the one who calls `action_draft_repo.append(entry)`. Today the caller is always the API route (no worker-side composition+persist path is wired).

### 3.1 Initial row

When persisted, the draft has:

- `action_draft_id = f"adraft_{uuid4().hex}"` (per T-007 §1 evidence).
- `status = "proposed"` (storage vocabulary).
- `safe_for_submission = False`.
- `decision_package_id`: set when composed from DP path; `NULL` for user-supplied.
- `created_at`, `created_by`, `updated_at`.
- `audit_trail_hash` (hash over the same canonical-JSON pattern as Decision Package).
- `previous_draft_hash = None` on first composition; chained on each edit.
- `dry_run_passed: bool` from §2.
- All sizing fields (quantity, limit_price_local, currency_local, notional_local, notional_eur, fx_rate_at_creation, usable_cash_eur_at_creation, held_quantity_at_creation).
- `user_note: str|None = None`.

### 3.2 Storage table

`action_drafts` per `packages/storage/.../metadata.py`. Migration ladder:

- `0030_asset_action_drafts.py` — initial table.
- `0031_action_draft_submissions_and_events.py` — submission lifecycle audit trail.
- `0035_action_draft_belgian_tob.py` — Belgian transactions-on-securities tax field.
- `0040_action_draft_order_vocabulary.py` — order-type taxonomy refinement.
- `0044_action_draft_conditional_orders.py` — conditional-order support (Phase 4).
- `0051_action_drafts_and_audit.py` — append-only audit chain.

T-003 documents the full migration chain.

## 4. The two state-machine vocabulary islands

This is the **largest architectural drift** in the action-draft surface, surfaced repeatedly in prior reality docs (T-004, T-005, T-007 §13). T-018 documents both vocabularies side-by-side.

### 4.1 Portfolio enum — `ActionDraftState` (`packages/portfolio/.../action_draft_state_machine.py:37-50`)

Locked V1 state graph from the IBKR reply-handshake lock + release-1 blueprint §11. **13 states**:

| State | Semantics |
|---|---|
| `DRAFT` | Draft created; safety checks not yet run |
| `SAFETY_CHECKED` | Dry-run passed; ready for user approval |
| `USER_APPROVED` | User clicked approve; ready for submission |
| `SUBMITTED` | `placeOrder` returned synchronously |
| `AWAITING_IBKR_REPLY` | Immediately after submission, until `openOrder` callback or reconciliation |
| `REPLY_CONFIRMED` | `openOrder` confirms the order is live at IBKR |
| `WORKING` | Alias for `REPLY_CONFIRMED` (same semantics) |
| `FILLED` | IBKR-side terminal — filled |
| `CANCELLED` | IBKR-side terminal — cancelled |
| `REJECTED` | IBKR-side terminal — rejected |
| `RECONCILED` | Local terminal after reconciliation confirms IBKR state |
| `EXPIRED` | Dry-run validity window closed before submission |
| `FAILED` | Orchestrator errored before order was placed |

`ALLOWED_TRANSITIONS` map (`:54-117`) defines the legal edges. `TERMINAL_STATES = frozenset({RECONCILED, EXPIRED, FAILED})` (`:120-126`). `LIVE_AT_BROKER_STATES = frozenset({SUBMITTED, AWAITING_IBKR_REPLY, REPLY_CONFIRMED, WORKING})` (`:128-136`).

Used by **`action_draft_safety.py`** for the dry-run pipeline + by the worker for any pre-submission validation.

### 4.2 Storage map — `_ACTION_DRAFT_TRANSITIONS` (per T-007 §13)

In `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:4820-4911`. **15 status literals** (T-008 `apiClient.ts:ActionDraftStatus` is the frontend mirror):

| Status | When written | By whom |
|---|---|---|
| `proposed` | composer.append (initial) | API route |
| `edited` | PATCH /action-draft/{id} | API route |
| `user_approved` | POST /action-draft/{id}/approve | API route (after JA token) |
| `dismissed` | POST /action-draft/{id}/dismiss | API route |
| `deleted` | POST /action-draft/{id}/delete | API route |
| `superseded` | newer DP arrives for same `(account, conid)` | API route or worker |
| `submitted` | submission sweep `place_order` returns | worker |
| `accepted` | IBKR `orderStatus` callback | worker (lifecycle_handler) |
| `working` | IBKR `orderStatus` "Active" | worker |
| `partially_filled` | IBKR `execDetails` partial | worker |
| `filled` | IBKR `execDetails` full | worker |
| `cancelled` | IBKR `orderStatus` "Cancelled" | worker |
| `rejected` | IBKR `orderStatus` "Rejected" | worker |
| `pending_cancellation` | user-requested cancel | API route |
| `awaiting_reply_timeout` | T-020 Pass C escalation | worker (reconciler) |

### 4.3 The mismatch

The portfolio enum uses CAPS_WITH_UNDERSCORES (`DRAFT`, `USER_APPROVED`, `WORKING`) and an internal `_state` field. The storage uses lowercase string literals (`proposed`, `user_approved`, `working`) on a `status` column.

The two **partially overlap**:

| Portfolio enum | Storage literal | Match? |
|---|---|---|
| `DRAFT` | `proposed` | ✗ — different names |
| `SAFETY_CHECKED` | (no storage equivalent) | ✗ |
| `USER_APPROVED` | `user_approved` | ✓ |
| `SUBMITTED` | `submitted` | ✓ |
| (no portfolio equiv.) | `edited` | ✗ |
| (no portfolio equiv.) | `dismissed` | ✗ |
| (no portfolio equiv.) | `deleted` | ✗ |
| (no portfolio equiv.) | `superseded` | ✗ |
| `WORKING` / `REPLY_CONFIRMED` | `working` | partial (one storage literal, two portfolio enums) |
| `AWAITING_IBKR_REPLY` | (no storage equivalent) | ✗ |
| `FILLED` | `filled` | ✓ |
| `CANCELLED` | `cancelled` | ✓ |
| `REJECTED` | `rejected` | ✓ |
| `RECONCILED` | (no storage equivalent — implied by terminal) | partial |
| `EXPIRED` | (no storage equivalent) | ✗ |
| `FAILED` | (no storage equivalent) | ✗ |

**Consequence**: the worker side uses `ActionDraftState` for pre-submission logic and IBKR-side lifecycle tracking, while the storage layer + API layer + frontend all use the lowercase status literals. There is no single source of truth.

**Phase 1c surface** (re-confirmed): the action-draft state machine has two parallel vocabularies; unifying them is a documented Track 1c finding from T-005 + T-007.

## 5. The frontend approval flow

Per T-008 `web-components-feature-grids.md` §§1-2 + T-009 §2:

### 5.1 The `/ibkr-acties` page (T-008 §3.5)

Three tabs (`apps/web/app/ibkr-acties/page.tsx:121-152`):

- **"Te keuren"** — `<ActionDraftGrid drafts={teKeurenDrafts}>` — proposed + edited + user_approved (not yet submitted).
- **"Actief bij IBKR"** — `<ActiefBijIbkrGrid drafts={actiefDrafts}>` — submitted / accepted / working / partially_filled / pending_cancellation.
- **"Historiek"** — `<HistoriekGrid drafts={historiekDrafts}>` — filled / cancelled / rejected / dismissed / deleted / superseded / expired / awaiting_reply_timeout.

The tab nav re-fetches the appropriate `apiClient.*` endpoint on every change (`apps/web/app/ibkr-acties/page.tsx:101-109`).

### 5.2 `<ActionDraftGrid>` (T-008 §2)

Renders one row per draft with 4 action buttons: `Goedkeuren`, `Bewerken`, `Dismiss`, `Verwijder`. Per T-008 §2 — state machine transitions:

| Button | Action | API call | State transition |
|---|---|---|---|
| `Goedkeuren` | approve with JA token | `apiClient.approveActionDraft(id)` (`apiClient.ts:1576`) | `proposed | edited → user_approved` |
| `Bewerken` | inline edit form | `apiClient.patchActionDraft(id, payload)` (`apiClient.ts:1570`) | `proposed → edited` (or `edited → edited`) |
| `Dismiss` | reason prompt | `apiClient.dismissActionDraft(id, reason)` (`apiClient.ts:1581`) | `proposed | edited → dismissed` |
| `Verwijder` | confirm + delete | `apiClient.deleteActionDraft(id)` (`apiClient.ts:1587`) | `proposed | edited → deleted` |

### 5.3 The JA confirmation gate

Per T-008 `web-components-feature-grids.md` §2 — the approve button does NOT directly fire the API. It opens a `window.prompt` requiring the user to **type the literal "JA"** at `ActionDraftGrid.tsx:141-151`. Prompt template:

```
"Type JA om order voor ${draft.quantity}× ${draft.symbol} @ €${...} LMT (totaal €${...}) goed te keuren."
```

If the user types anything else → no API call, frontend shows `"Goedkeuring geannuleerd. Type exact JA om door te gaan."` (`:149`).

This is the **client-side enforcement** of AGENTS.md §3.2 "no order without explicit user approval" — the API approve endpoint trusts the client to have gated; T-019 covers the worker-side enforcement (separately at the submission sweep).

Compared to the Volglijst's **BEVESTIG token** (T-012 §8 — `VolglijstColdStartFlow.tsx:174-177` — `"BEVESTIG"` for watchlist confirmation), the action-draft uses a shorter **JA token**. The asymmetry is by design: BEVESTIG is one-shot (initial setup); JA is per-order (frequent). Token length matches gravity.

### 5.4 Post-approval state

After approve succeeds, the row stays visible in "Te keuren" with `status="user_approved"` (success banner shows: `"Goedgekeurd. IBKR-verzending wordt in een toekomstige update toegevoegd."` per T-008 §2). On the next page refresh the row migrates to "Actief bij IBKR" once the worker submission sweep picks it up (T-019 boundary).

### 5.5 `<ActionDraftEditForm>` (T-008 §1)

Inline edit form rendered when the user clicks `Bewerken`. Three editable fields: `quantity`, `limit_price_local`, `user_note`. On save:

- Validation: `Number(quantity) > 0`, `Number(limitPrice) > 0` (client-side only; server runs the full dry-run pipeline).
- `apiClient.patchActionDraft(id, payload)` (T-009 §2 — `apiClient.ts:1570`).
- On API success → `onSaved()` callback re-fetches the parent grid.
- On API error → red banner with Dutch fallback (`"Bewerken mislukt."`).

The PATCH route on the API runs the 11 A-K gates again against the new values (T-005); the form does NOT re-run safety checks client-side.

## 6. API routes

Per T-005 `api-actions-suggestions-and-watchlists.md`:

| Method | Path | Handler module |
|---|---|---|
| GET | `/action-draft/te-keuren` | `action_draft.py` |
| GET | `/action-draft/{id}` | `action_draft.py` |
| POST | `/action-draft` | `action_draft.py` (create from DP or user-supplied) |
| PATCH | `/action-draft/{id}` | `action_draft.py` |
| POST | `/action-draft/{id}/approve` | `action_draft.py` |
| POST | `/action-draft/{id}/dismiss` | `action_draft.py` |
| POST | `/action-draft/{id}/delete` | `action_draft.py` |
| POST | `/action-draft/{id}/cancel-submitted` | `action_draft_submission.py` (T-019 boundary) |
| POST | `/action-drafts/compute` | `action_draft_sync.py` (admin sync, T-005) |

`action_draft.py` (CC C and CC D from T-055 — `create_action_draft:396` rank D 23, `patch_action_draft:585` rank C 14, plus the high-CC sites). The handlers thread the composer + dry-run pipeline through the `StorageConnectionProvider` for the persist step.

## 7. Cross-cuts + Phase 1c surface

The following observations are inputs for Phase 1c gap analysis:

1. **Two state-machine vocabularies coexist** (§4). 13-state portfolio enum (pre-submission + IBKR lifecycle) vs 15-state storage map (user-UX + IBKR lifecycle). Partial overlap; no single source of truth. Re-confirmed for the 5th time (after T-004, T-005, T-007 §13, and elsewhere).
2. **Dry-run report not persisted in full** (§2.2). Only `dry_run_passed: bool` lands on the draft row; the per-gate detail is discarded. A future "show me why this draft is blocked" UI would need the full report. Phase 4 candidate.
3. **`SAFETY_CHECKED` / `AWAITING_IBKR_REPLY` / `REPLY_CONFIRMED` / `EXPIRED` / `FAILED` portfolio states have no storage equivalent** (§4.3). The pre-submission `SAFETY_CHECKED` state is implicit in `proposed + dry_run_passed=True`; the reply states collapse to `submitted` or `working`; the terminal `EXPIRED` / `FAILED` are not represented in `status` at all (would surface only in audit rows).
4. **No worker-side compose+persist path** (§1.3). All action-draft creation goes through the API route today. The worker has the compose function but never calls it. Phase 4 candidate: scheduler-driven "auto-propose drafts from latest DPs" workflow.
5. **The JA token is client-side-only enforcement** (§5.3). The API approve endpoint doesn't verify the token; a malicious or buggy client could bypass it. Phase 1c: server-side token requirement.
6. **`compose_action_draft_user_supplied` skips the DP chain integrity check** (gate K). The user-supplied path doesn't reference a Decision Package, so gate K (chain intact) trivially passes. Phase 1c: should user-supplied drafts have additional safeguards in lieu of DP gating?
7. **Belgian TOB tax** field (migration `0035_action_draft_belgian_tob.py`). The action-draft table carries a Belgian transactions-on-securities tax estimate, but the compute logic + display in the frontend grids is undocumented at the workflow level. Phase 1c: cross-reference T-022 future `belgian-tax-computation.md`.
8. **Conditional orders** (migration `0044_action_draft_conditional_orders.py`). Schema declares fields for conditional orders, but gate C locks `LMT DAY` only. The conditional-order schema is dead/future-feature. Phase 1c: similar to T-016 `prediction_diary_predictor_contributions` — declared schema, no write path.
9. **`safe_for_submission=False` hard floor** (§7.4). Per T-007 §1 doctrine comment at `composer.py:21-24`, "Task 134 (real submission) is the only code path allowed to flip it conditionally." Today the flag is hard-locked False at composition; the worker submission sweep is the only consumer that could flip it.

### 7.4 Hard `safe_for_submission=False` floor

Per T-007 §1 + the composer doctrine at `composer.py:21-24`:

> "Hard contract: this module never flips `safe_for_submission` to True. Task 134 (real submission) is the only code path allowed to flip it conditionally."

Initial composition sets `safe_for_submission=False`. The worker submission sweep (T-019 future) is the only path that flips it to True (and that path is gated on `status=="user_approved"` + storage connection + connection probe + final re-check of all dry-run gates). No other code modifies the flag.

This is the **system-level** equivalent of the user's JA token: the user gates approval; the worker gates submission. Two independent checks.

## 8. End-to-end timeline

For a user reviewing one draft in the `/ibkr-acties` "Te keuren" tab:

| t (s) | Tier | Action |
|---|---|---|
| 0 | User | Opens `/ibkr-acties`, sees "Te keuren" tab with 3 proposed drafts |
| ~1 | User | Clicks `Bewerken` on first draft |
| ~2 | Frontend | Opens `<ActionDraftEditForm>` inline |
| ~10 | User | Edits quantity, clicks `Opslaan` |
| ~10.1 | Frontend | `apiClient.patchActionDraft(id, payload)` |
| ~10.3 | API | Re-runs 11 A-K gates against new values; persists `status="edited"` |
| ~10.4 | Frontend | `onSaved()` callback re-fetches grid; row re-renders |
| ~15 | User | Clicks `Goedkeuren` |
| ~15.1 | Frontend | `window.prompt`: "Type JA om order voor 6× ASML.AS @ €638.72 LMT (totaal €3832.32) goed te keuren." |
| ~17 | User | Types "JA", clicks OK |
| ~17.1 | Frontend | `apiClient.approveActionDraft(id)` |
| ~17.3 | API | UPDATE `action_drafts` SET `status='user_approved'`, `updated_at=now()` WHERE `action_draft_id=...` AND `status IN ('proposed', 'edited')` |
| ~17.4 | Frontend | Re-fetches; row shows `"Goedgekeurd."` success banner |
| | | **End of T-018 scope; T-019 picks up.** |
| ~30 | Worker | (Future T-019) Submission sweep tick reads `user_approved` drafts and submits to IBKR |

The user-facing latency from `Goedkeuren` click → IBKR-side `placeOrder` will be sub-minute once the worker sweep is wired (T-019 future); today it stops at `user_approved` with the "IBKR-verzending wordt in een toekomstige update toegevoegd" banner.

## 9. Failure paths

| Failure | Surface | Resulting state |
|---|---|---|
| Composer raises `SafetyCheckFailedError` (dry-run gates fail) | composer | exception bubbles; draft NOT persisted; API returns 4xx with Dutch detail |
| API persist raises (DB error) | API route catch | 5xx Dutch message; no row; user retries |
| User types wrong token in JA prompt | frontend short-circuit | no API call; banner `"Goedkeuring geannuleerd. Type exact JA om door te gaan."` |
| Approve API raises mid-update | API catch | row stays at `proposed` / `edited`; frontend shows error banner |
| Concurrent edit (User A approves, User B PATCHes simultaneously) | DB row-level constraint | one wins; the other gets a 409 (per T-005 — `ActionDraftStateTransitionError`) |
| Draft already terminal (`dismissed` / `deleted` / `superseded`) and user tries to act on it | API state-machine check | 409 with Dutch message; frontend shows error |
| Dry-run validity window expires (the optional `EXPIRED` state in portfolio enum) | not currently wired | n/a — `EXPIRED` is declared in the enum but no code transitions to it today |

The `EXPIRED` state being declared-but-unreachable is a documented oddity: the V1 product lock envisions a window during which `SAFETY_CHECKED` drafts must be approved or they expire, but no code path enforces the timeout today. Phase 1c.

## 10. Out of scope

- **IBKR submission lifecycle** (T-019 future) — picks up at `user_approved → submitted → accepted → working → filled/cancelled/rejected`.
- **Reconciliation passes A/B/C** (T-020 future) — drives `awaiting_reply_timeout → pending_cancellation → cancelled` and the `reconciled` terminal.
- **AI explanation** (T-023 future) — Decision Package's deterministic Dutch paragraph is consumed by the action-draft compose path; the AI-augmented Anthropic Claude explanation is a separate write path.
- **Backtest leaderboard** (T-024 future).
- **Action-draft sync admin route** (`POST /action-drafts/compute`) — admin debugging tool documented in T-005; not the user-facing flow.

## 11. References

- `docs/reality/components/portfolio-guards-and-state-machines.md` — `action_draft_safety.py` 11 A-K gates (T-002).
- `docs/reality/components/portfolio-money-and-accounting.md` — Decimal-as-string discipline (T-002).
- `docs/reality/components/worker-actions-and-reconciliation.md` §1 (composer) + §13 (state-machine transitions) (T-007).
- `docs/reality/components/api-actions-suggestions-and-watchlists.md` — API routes (T-005).
- `docs/reality/components/web-components-feature-grids.md` §§1-2 — `<ActionDraftEditForm>` + `<ActionDraftGrid>` (T-008).
- `docs/reality/components/web-pages.md` §3.5 — `/ibkr-acties` page (T-008).
- `docs/reality/components/web-api-client-and-text.md` §2 — `apiClient.*` action-draft methods (T-009).
- `docs/reality/workflows/decision-package-composition.md` (T-017) — DP composer that produces the rows the DP-driven action-draft composer reads.
- `docs/reality/workflows/cold-start-seeding-and-watchlist-confirmation.md` §8 (T-012) — BEVESTIG token sibling pattern.
- `docs/intent/_trading-system-doctrine.md` §3.2 — "no order without explicit user approval" lock.
- `docs/product/locked-decisions.md` — IBKR reply-handshake lock cited in `action_draft_state_machine.py:1-15` docstring.
