# User Approves Action Draft — The JA Ritual

**Scope.** User-action workflow narrating the JA approval ritual from the user's perspective — user lands on `/ibkr-acties` "Te keuren" tab → reviews per-row card with quantity / limit price / total notional → clicks "Goedkeuren" → `window.prompt` asks them to type the literal `JA` → on match, frontend calls `POST /action-draft/{id}/approve` → state transitions `proposed | edited → user_approved` → row gets green "Goedgekeurd" badge + an out-of-date banner about future IBKR submission. T-018 covered the full composition + approval functionality at the system level; T-026 covers what the user sees and types.

**Sibling functionality reality**: T-018 `docs/reality/workflows/action-draft-composition-and-approval.md` (composer + 11 A-K dry-run gates + state-machine vocabulary islands + JA token boundary). **Component reality**: T-008 `docs/reality/components/web-components-feature-grids.md` §2 (`<ActionDraftGrid>`). **Submission lifecycle**: T-019 `docs/reality/workflows/ibkr-order-submission-lifecycle.md` (the post-approval submission that the out-of-date banner text misrepresents).

## 0. TL;DR — the user's journey, in 6 steps

1. **Arrive at `/ibkr-acties`**: the user navigates from the dashboard or top-nav. Page loads and shows three tabs — **"Te keuren"** (To Approve), **"Actief bij IBKR"** (Active at IBKR), **"Historiek"** (History). The "Te keuren" tab is the default landing.
2. **See the per-row card**: each pending draft renders as an `<article>` with header (symbol + side badge + status badge) + body (quantity, limit price local, notional EUR, optional user_note). Cards for `user_approved` draft have a light-green background; cards for `proposed`/`edited` have white background.
3. **Click "Goedkeuren"** (green button at the bottom of the card; only visible when status is `proposed`/`edited`): triggers `handleApprove` (`ActionDraftGrid.tsx:140-161`).
4. **Native `window.prompt` appears**: a browser-native modal with the Dutch text `"Type JA om order voor {Q}× {symbol} @ €{price} LMT (totaal €{notional}) goed te keuren."`. The user types either `JA` (match) or anything else (abort).
5. **API call fires** (only if `typed === "JA"` client-side compare succeeds): `apiClient.approveActionDraft(draft.action_draft_id)` → `POST /action-draft/{id}/approve`. Server runs `update_status(new_status="user_approved", transition_actor="user")` and returns the updated draft.
6. **Row turns green + banner appears**: the row card flips to `background: "#f0fdf4"` (light green) + a blue info banner appears: `"Goedgekeurd. IBKR-verzending wordt in een toekomstige update toegevoegd."` (= "Approved. IBKR submission will be added in a future update."). The action buttons disappear (only visible when status is `proposed`/`edited`). The row stays in the "Te keuren" tab until the worker submission sweep picks it up (T-019, not yet APScheduler-wired per T-020 §10.2).

**Total user-visible time**: typically ~3 seconds (1 button click + ~1 second to read the prompt + 2 keystrokes + 1 Enter + 1 server round-trip).

## 1. The dashboard host — `/ibkr-acties` page

**File**: `apps/web/app/ibkr-acties/page.tsx:1-200+`. Three tabs (`:170-209+`):

| Tab | Drafts shown | Component |
|-----|--------------|-----------|
| `te-keuren` (default) | `status ∈ {proposed, edited, user_approved}` | `<ActionDraftGrid>` |
| `actief` | `status ∈ {submitted, accepted, working, partially_filled}` | `<ActiefBijIbkrGrid>` |
| `historiek` | terminal statuses | `<HistoriekGrid>` (not in T-026 scope) |

**Important**: the `user_approved` draft **stays in the "Te keuren" tab** — it doesn't migrate to "Actief bij IBKR" until the worker submission sweep flips its status to `submitted`. The user therefore sees an approved draft persist on the same tab where they just approved it, badged green, with the "future update" banner. This is documented in T-018 §5.2.

The page polls the API for fresh data via the `onChange={refreshTeKeuren}` callback fired after every successful per-row action.

## 2. The grid — `<ActionDraftGrid>` per-row card

**File**: `apps/web/components/ActionDraftGrid.tsx:1-440`.

### 2.1 Per-row state booleans (`:136-138`)

```tsx
const isPending = draft.status === "proposed" || draft.status === "edited";
const isApproved = draft.status === "user_approved";
const isSuperseded = draft.superseded_by_decision_package_id !== null;
```

| Condition | Action buttons visible | Card background |
|-----------|------------------------|------------------|
| `isPending && !editing` | Goedkeuren + Dismiss + Delete + Bewerken | white (#ffffff) |
| `isApproved` | none — only the "Goedgekeurd" banner | light green (#f0fdf4) |
| `editing == true` | Bewerken inline form (T-008 §2 — out of T-026 scope) | varies |
| terminal (dismissed/deleted/submitted/etc.) | none | white |

### 2.2 The 3 per-row actions

The grid uses **three different browser-native dialog types** for three actions:

| Action | Dialog type | Prompt text |
|--------|-------------|-------------|
| **Goedkeuren** | `window.prompt` for typed token | `"Type JA om order voor {Q}× {symbol} @ €{price} LMT (totaal €{notional}) goed te keuren."` |
| **Dismiss** | `window.prompt` for optional reason | `"Optionele reden voor dismiss (mag leeg blijven):"` |
| **Delete** | `window.confirm` (yes/no only) | `"Weet je zeker dat je deze draft wil verwijderen?"` |

The asymmetry across 3 dialog types reflects the gravity asymmetry: approve is the gravest (it sends an order to IBKR), so it gets a typed-literal gate; dismiss is medium (reversible by re-composing), so it gets an optional free-text reason; delete is least-grave (logical delete, audited) so it gets a yes/no confirm.

§9.3 documents that all three are browser-native (un-styleable, behavior varies by browser).

## 3. The JA token — `expectedToken = "JA"` (`ActionDraftGrid.tsx:141`)

```tsx
async function handleApprove() {
  const expectedToken = "JA";
  const typed = window.prompt(
    `Type JA om order voor ${draft.quantity}× ${draft.symbol} @ €${fmtDecimal(
      draft.limit_price_local,
      4,
    )} LMT (totaal €${fmtDecimal(draft.notional_eur)}) goed te keuren.`,
  );
  if (typed !== expectedToken) {
    setError("Goedkeuring geannuleerd. Type exact JA om door te gaan.");
    return;
  }
  setBusy("approving");
  setError(null);
  const result = await apiClient.approveActionDraft(draft.action_draft_id);
  setBusy(null);
  if (!result.ok) {
    setError(result.message || "Goedkeuren mislukt.");
    return;
  }
  onChange();
}
```

### 3.1 Token semantics

- **`expectedToken = "JA"`** is a function-local constant, hard-coded in the component. Not a config, not a server response.
- **Direct strict-equality compare** `typed !== expectedToken` — case-sensitive, no `.trim()`, no `.toUpperCase()`. The user must type exactly `JA` (uppercase, two chars, nothing else).
- **`window.prompt` returns**: `null` if the user clicked Cancel, the typed string if the user clicked OK, or an empty string `""` if they clicked OK without typing. All three values fail `!== "JA"` and trigger the error path.

### 3.2 The error message (`:149`)

`"Goedkeuring geannuleerd. Type exact JA om door te gaan."` (= "Approval cancelled. Type exact JA to continue."). This is the ONLY hint the user gets about the literal — no in-prompt asterisks, no example, no input-side validation pre-display.

### 3.3 Asymmetry vs BEVESTIG (T-025)

| Token | Length | Frequency | Component | Source of truth |
|-------|--------|-----------|-----------|-----------------|
| `BEVESTIG` (T-025) | 8 chars | One-time per account | input field in `<VolglijstColdStartFlow>` | server-side `LOCKED_CONFIRMATION_PHRASE` at `watchlist_confirmation_routes.py:45` + client-side input |
| `JA` (T-026) | 2 chars | Per-order | `window.prompt` in `<ActionDraftGrid>` | client-side only (`expectedToken = "JA"`) |

The asymmetries:
- **Length scales with gravity** — BEVESTIG is one-shot (whole-system initialisation); JA is per-order (frequent).
- **UI surface differs** — BEVESTIG is a styled `<input>` field with the placeholder visible; JA is a `window.prompt` with no in-field hint.
- **Server enforcement differs** — BEVESTIG is server-validated at gate #1 (`watchlist_confirmation_routes.py:202`); **JA is client-side only** (see §4).

## 4. The server-side gap — JA is NOT validated by the API

**File**: `apps/api/src/portfolio_outlook_api/action_draft.py:654-693`.

```python
@router.post(
    "/action-draft/{action_draft_id}/approve",
    response_model=ActionDraftResponse,
)
def approve_action_draft(action_draft_id: str) -> dict[str, object]:
    provider = _storage_provider()
    try:
        with provider.checked_connection(require_writable=True) as checked:
            repo = SqlAlchemyActionDraftRepository(...)
            current = repo.get_by_id(action_draft_id)
            if current is None:
                raise HTTPException(status_code=404, detail="Actiedraft niet gevonden.")
            try:
                updated = repo.update_status(
                    action_draft_id=action_draft_id,
                    new_status="user_approved",
                    transition_actor="user",
                    transition_at=datetime.now(UTC),
                )
            except ActionDraftStateTransitionError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            checked.connection.commit()
            return _serialize_draft(updated)
```

**The route accepts no body.** There is no `confirmation_token`, no `confirmation_phrase`, no `idempotency_key`. The only inputs are:
- the URL path param `action_draft_id`,
- the storage gate (writable connection),
- the state-machine pre-condition (must be in `proposed` or `edited` to legally transition to `user_approved` — enforced by `ActionDraftStateTransitionError` raised from `update_status`).

A `curl` to `POST /action-draft/{id}/approve` (with valid auth, if any — none in scope here) bypasses the JA prompt entirely. The locked AGENTS.md §3.2 doctrine "no order without explicit user approval" is enforced **client-side only**.

**The 422 path** (`:685-688`) fires only when the state machine rejects the transition (e.g., the draft is already `user_approved` or in a terminal state). It does NOT fire for missing-token or wrong-token — there is no token to check.

T-018 §5.3 originated this finding; T-026 re-surfaces it from the user-action perspective. §9.1.

## 5. The state transition — `update_status(actor="user")`

The single repo call at `action_draft.py:679-684`:

```python
updated = repo.update_status(
    action_draft_id=action_draft_id,
    new_status="user_approved",
    transition_actor="user",
    transition_at=datetime.now(UTC),
)
```

The storage layer's `_ACTION_DRAFT_TRANSITIONS` map (T-018 §4) permits:
- `proposed → user_approved` ✓
- `edited → user_approved` ✓
- everything else → `ActionDraftStateTransitionError`

The `transition_actor="user"` literal is hard-coded — the route accepts no actor parameter. Compared with the BEVESTIG audit (T-025 §7), where `actor="user"` is also a hard-coded string, the action-draft path has no infrastructure to distinguish multiple users.

**No `details_json`**: the action-draft state-transition write does NOT capture IP, user-agent, browser session ID, or any forensic data. The audit trail records WHEN approval happened (`transition_at` = server clock at the moment) but not from WHERE or by WHOM beyond the hard-coded `"user"`. §9.4.

## 6. The post-approval banner — out-of-date text

After successful approval (`isApproved === true`), the card renders a blue info banner (`ActionDraftGrid.tsx:329-344`):

```tsx
{isApproved ? (
  <div
    data-testid={`action-draft-approved-banner-${draft.action_draft_id}`}
    style={{
      marginTop: 16,
      padding: 12,
      background: "#dbeafe",
      color: "#1e40af",
      borderRadius: 6,
      fontSize: 13,
    }}
  >
    Goedgekeurd. IBKR-verzending wordt in een toekomstige update
    toegevoegd.
  </div>
) : null}
```

**Translation**: "Approved. IBKR submission will be added in a future update."

**This is out of date.** Per T-019 (merged sibling), the IBKR submission infrastructure exists:
- `submitter.py:240` calls `place_order(contract, order)` to actually submit to IBKR.
- `submission_sweep.py:217` `SubmissionSweep.tick()` orchestrates the locked one-per-tick processing of `user_approved` drafts.
- 12 Tier-1 safety gates run before submission.
- 3 audit tables capture the submission lifecycle.

The infrastructure is shipped. What's NOT shipped (per T-020 §10.2) is the APScheduler wiring — `SubmissionSweep.tick()` and `IbkrReconciler.tick()` are not invoked by any production scheduler. The frontend banner conflates "not wired" with "not implemented", and the user-visible text misleads them about the system's actual state.

§9.5 — Phase 1c should either (a) wire the sweep into APScheduler and update this text, or (b) rephrase to "IBKR-verzending wacht op gescheduled run" if the wiring remains intentional.

The matching docstring in `action_draft.py:660-664` carries the same out-of-date claim:

> "**Does NOT submit to IBKR** — Task 134 will wire the real submit. The locked Dutch info banner *'Goedgekeurd. IBKR-verzending wordt in een toekomstige update toegevoegd.'* is rendered by the UI after a successful approve."

Task 134 has presumably landed (T-019 documents the submitter exists); the docstring is stale.

## 7. The complete error map

| Error | Visible to user | Source |
|-------|-----------------|--------|
| `"Goedkeuring geannuleerd. Type exact JA om door te gaan."` | inline below the card | `ActionDraftGrid.tsx:149` — user typed wrong token or cancelled prompt |
| `"Goedkeuren mislukt."` (default) or server-supplied message | inline below the card | `:157` — API call failed (network, 5xx, etc.) |
| `"Actiedraft niet gevonden."` | server-supplied → inline | API 404 at `action_draft.py:676` — draft id doesn't exist (rare; should only happen if a draft was deleted between page load and click) |
| State-transition error message | server-supplied → inline | API 422 at `:687` — draft is no longer in a transitionable state |
| Storage unavailable | server-supplied → inline | API 503 — `STORAGE_UNAVAILABLE_DETAIL` Dutch message |

The component does NOT distinguish 404 from 422 from 5xx — all paths land in the same red inline error div. The user has no actionable signal for the difference. §9.6.

## 8. Failure paths from the user's seat

1. **User typed `ja` (lowercase)** — `window.prompt` returns `"ja"` → `"ja" !== "JA"` → error renders, no API call. User must re-click Goedkeuren and try again. No hint about case.
2. **User typed `JA` with trailing space** — `"JA " !== "JA"` → error renders. No `.trim()` applied. User must re-click and retype.
3. **User clicked Cancel on the prompt** — `window.prompt` returns `null` → `null !== "JA"` → same error renders as a mis-typed value. The user might genuinely have wanted to cancel; the system treats it as "you typed wrong".
4. **User double-clicks Goedkeuren** — `busy` flag is set at `:152` AFTER the prompt resolves, so the second click would re-fire `window.prompt` before the first API call settles. The user is then presented with two prompts in rapid succession; if they type JA in both, the API gets called twice. The second call would 422 (state machine forbids `user_approved → user_approved`); the user would see the error from the second call after they've already succeeded with the first. §9.7.
5. **Server down mid-prompt** — the prompt completes locally, the API call hangs/fails, error appears inline. The user's typed-JA action is forgotten; they must re-click + re-type. No request deduplication or retry. §9.8.
6. **Draft was superseded between page load and click** — `isSuperseded === true` (a newer DP supersedes this one). The component still shows the buttons (the supersede check is informational only — `:138` reads the flag but doesn't gate the actions). The user approves a superseded draft, the API succeeds, and the user has approved out-of-date analysis. §9.9.

## 9. Phase 1c surface (10 findings on the user-action surface)

1. **JA token enforcement is client-side only** — the API approve endpoint accepts no body; a programmatic POST bypasses the prompt entirely. AGENTS.md §3.2 "no order without explicit user approval" is enforced by the client alone. T-018 §5.3 originating finding re-surfaced.
2. **No idempotency key on the approve request** — a network retry or a double-fire would attempt a second state-transition; the state machine rejects gracefully but the user sees an error instead of a no-op success.
3. **Three different browser-native dialog types across the 3 per-row actions** — `window.prompt` (Goedkeuren + Dismiss reason), `window.confirm` (Delete). Inconsistent UX, un-styleable, behaviour varies across browsers and mobile. No accessible-by-default focus management.
4. **`actor="user"` hard-coded + `details_json` not captured** — same finding as T-025 §9.7-§9.8. No multi-user support; no forensic data (IP/UA/timestamp client-side) recorded on the state transition audit.
5. **Out-of-date "future update" banner text** (§6) — contradicts shipped submission infrastructure (T-019). User is told to wait for a future feature that exists; system actually waits for APScheduler wiring (T-020 §10.2). Phase 1c should either fix the wiring or rephrase the text.
6. **Error messages don't distinguish failure modes** — same red inline div for 404, 422, 5xx, and validation errors. No actionable next step shown.
7. **`busy` flag set after `window.prompt` returns** — racy double-click can spawn two prompts. State machine catches the duplicate but UX is degraded.
8. **No retry path for transient server errors** — failed approve requires re-typing JA. No "retry" button, no auto-retry, no session-persisted "pending approval" state.
9. **Superseded drafts are still approvable** — the `isSuperseded` flag (`:138`) is read for display but NOT used to gate the actions. The user can approve a stale draft.
10. **Prompt text shows price + quantity + notional but NOT TOB or commission** — intent §4 of the Belgian tax doc says expected return should be net-of-TOB; T-022 §10.3 documented TOB-net-expected-return is not implemented. The user doesn't see TOB / commission / FX cost in the approval prompt — they approve a gross-notional number. The TOB cell exists elsewhere on the `/portefeuille` page (T-022 §4.2) but is not in the prompt context.

## 10. Out of scope (re-confirmed)

- **Action-draft composition + 11 A-K dry-run gates** (T-018 — merged sibling; the proposed → edited path before the user clicks Goedkeuren).
- **Submission sweep + 12 Tier-1 gates** (T-019 — merged sibling; the worker-side flow after `user_approved`).
- **`<ActionDraftEditForm>`** (the in-place edit flow; T-008 §2; T-026 covers only the approve path).
- **User-cancel-submitted-order** (T-027 next — covers the cancel surface for drafts already past `user_approved`).
- **AI explanation surface** (T-023 — merged sibling; the explanation icon next to the row).
- **Belgian tax TOB-net-expected-return filter** (T-022 §10.3 — flagged as Phase 1c gap; would inform the approval prompt with net numbers).

## 11. References

- `apps/web/components/ActionDraftGrid.tsx:130-195` (3 per-row handlers — `handleApprove`, `handleDismiss`, `handleDelete`)
- `apps/web/components/ActionDraftGrid.tsx:141` (`expectedToken = "JA"`)
- `apps/web/components/ActionDraftGrid.tsx:329-344` (post-approval banner — out-of-date text)
- `apps/web/app/ibkr-acties/page.tsx:170-209` (three-tab dashboard host)
- `apps/web/lib/apiClient.ts:1576` (`approveActionDraft`)
- `apps/api/src/portfolio_outlook_api/action_draft.py:654-693` (POST `/action-draft/{id}/approve` — no token validation)
- `apps/api/src/portfolio_outlook_api/action_draft.py:660-664` (stale docstring referencing Task 134)
- `docs/reality/workflows/action-draft-composition-and-approval.md` (T-018 — full functionality reality doc)
- `docs/reality/workflows/ibkr-order-submission-lifecycle.md` (T-019 — the post-approval submission infrastructure the banner contradicts)
- `docs/reality/workflows/ibkr-reconciliation-passes-a-b-c.md` (T-020 §10.2 — APScheduler wiring gap)
- `docs/reality/workflows/user-confirm-starter-watchlist.md` (T-025 — sibling user-action doc; BEVESTIG vs JA asymmetry)
- `docs/reality/workflows/belgian-tax-computation.md` (T-022 §10.3 — TOB-net-expected-return gap)
- `docs/reality/components/web-components-feature-grids.md` §2 (T-008 — `<ActionDraftGrid>` component reality)
