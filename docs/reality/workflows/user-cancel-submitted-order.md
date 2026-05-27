# User Cancels Submitted Order — A Persistent Request That Hangs

**Scope.** User-action workflow narrating the cancel ritual from the user's perspective — user on `/ibkr-acties` "Actief bij IBKR" tab → sees the red "Annuleer" button on rows with `cancellable` status → clicks → `window.confirm` yes/no → POST `/action-draft/{id}/cancel-submitted` → server flips status to `pending_cancellation` + writes one `ibkr_submission_lifecycle` row with `event_type='cancellation_request'` → row badge updates to "Annulering aangevraagd" — **and the request then hangs because the worker has no loop to consume `pending_cancellation` drafts and issue `cancelOrder` to IBKR**. The user sees success signals; the broker side never gets the request.

**Sibling functionality reality**: T-019 `docs/reality/workflows/ibkr-order-submission-lifecycle.md` §4.8 + §10.4 (the originating finding for the worker-side cancel gap). **Component reality**: T-008 `docs/reality/components/web-components-feature-grids.md` (`<IbkrSubmissionGrids>`). **Reconciliation companion**: T-020 `docs/reality/workflows/ibkr-reconciliation-passes-a-b-c.md` (Pass B detects in-flight drafts IBKR no longer reports, including the corner case where the broker side cancels the order via TWS for unrelated reasons — the only path that could move a stuck `pending_cancellation` row to `cancelled` in the current production state).

## 0. TL;DR — the user's journey, in 4 visible steps + 1 invisible non-event

1. **Arrive at `/ibkr-acties`** and switch to the **"Actief bij IBKR"** tab (`apps/web/app/ibkr-acties/page.tsx:181-206`). The tab shows drafts in submitted/accepted/working/partially_filled/pending_cancellation states via `<ActiefBijIbkrGrid>` (which is the actual exported name; the file is `IbkrSubmissionGrids.tsx`).
2. **See the per-row card** with the red "Annuleer" button at the bottom — but **only** when `cancellable === true` (i.e., status is one of `{submitted, accepted, working, partially_filled}`; a draft already in `pending_cancellation` shows no button). The button uses `background: "#dc2626"` (red).
3. **Click "Annuleer"**: triggers `handleCancel` (`IbkrSubmissionGrids.tsx:179-195`) which fires `window.confirm("Order voor {Q}× {symbol} annuleren?")`. Yes → proceed; No or Esc → abort silently with no UI feedback.
4. **Server flips state**: `apiClient.cancelSubmittedActionDraft(id)` → `POST /action-draft/{id}/cancel-submitted` → server runs 2 storage writes (status → `pending_cancellation`; lifecycle audit row `event_type='cancellation_request'`) and returns the updated draft. Card re-renders with the "Annulering aangevraagd" badge (yellow). The Annuleer button disappears (cancellable is now false).

**Step 5 — the invisible non-event**: at this point the user expects IBKR to receive the cancel request. **It does not.** The worker has no production loop that polls `pending_cancellation` drafts and issues `cancelOrder` on the live IBKR socket. The DB row sits in `pending_cancellation` indefinitely. T-019 §4.8 originating finding: `grep cancel_order under apps/worker/src/portfolio_outlook_worker/ returns zero production call sites` (only the Protocol declaration at `submitter.py:89` and test no-ops).

**Net user experience**: success-looking UI + persistent storage write + zero broker action. If the order fills 30 minutes later (because IBKR never got the cancel), the user is surprised — every signal they saw said the cancel succeeded.

## 1. The dashboard host — `/ibkr-acties` "Actief bij IBKR" tab

The 3-tab structure at `apps/web/app/ibkr-acties/page.tsx:170-209+` (per T-026 §1):

| Tab | Drafts shown | Component |
|-----|--------------|-----------|
| `te-keuren` | `proposed / edited / user_approved` | `<ActionDraftGrid>` (T-026) |
| `actief` | `submitted / accepted / working / partially_filled / pending_cancellation` | `<ActiefBijIbkrGrid>` (T-027 scope) |
| `historiek` | terminal statuses | `<HistoriekGrid>` |

The user must navigate to the "Actief bij IBKR" tab to find the Annuleer button. The Te-keuren tab does NOT offer a cancel UI — drafts there are in pre-submission states (proposed/edited/user_approved); the only way to back out of a `user_approved` draft is via Dismiss or Delete (T-026 §2.2), not via Cancel.

**Asymmetry**: the user has 4 negative-direction actions available in different places:
- **Dismiss** (Te-keuren tab): pre-submission soft drop with optional reason.
- **Delete** (Te-keuren tab): pre-submission logical delete with audit.
- **Cancel** (Actief tab): post-submission cancel request to IBKR.
- (No "withdraw" action between user_approved and submitted — once approved, the only stop is to wait for the worker sweep to pick it up, which currently doesn't happen per T-020 §10.1.)

## 2. The `cancellable` predicate — 4 statuses (`IbkrSubmissionGrids.tsx:173-177`)

```tsx
const cancellable =
  draft.status === "submitted" ||
  draft.status === "accepted" ||
  draft.status === "working" ||
  draft.status === "partially_filled";
```

The same 4 statuses are encoded server-side at `action_draft.py:774-776`:

```python
_CANCELLABLE_STATUSES = frozenset(
    {"submitted", "accepted", "working", "partially_filled"}
)
```

**Duplication across client + server.** Both layers maintain the same hard-coded set. A change to one without the other (e.g., adding `accepted_at_exchange` as a cancellable status) would create a UI/API drift. §9.4.

`pending_cancellation` is **explicitly excluded** from both lists — a double-click on a draft that's already pending cancellation cannot trigger a second cancel request. The button simply isn't rendered (frontend gate) and the server gate at `action_draft.py:815-822` would return HTTP 422 even if a programmatic POST tried.

## 3. The confirm — `window.confirm` (yes/no, not typed token)

`IbkrSubmissionGrids.tsx:179-195`:

```tsx
async function handleCancel() {
  const ok = window.confirm(
    `Order voor ${draft.quantity}× ${draft.symbol} annuleren?`,
  );
  if (!ok) return;
  setBusy(true);
  setError(null);
  const result = await apiClient.cancelSubmittedActionDraft(
    draft.action_draft_id,
  );
  setBusy(false);
  if (!result.ok) {
    setError(result.message || "Annulering mislukt.");
    return;
  }
  onChange();
}
```

### 3.1 The gravity asymmetry across tokens

| Action | Token | Dialog type | Gravity rationale |
|--------|-------|-------------|-------------------|
| BEVESTIG (T-025) | typed `BEVESTIG` (8 chars, uppercase, server-validated) | styled input field | one-time per account; high gravity |
| JA (T-026) | typed `JA` (2 chars, client-side only) | `window.prompt` | per-order approval; medium-high gravity |
| Annuleer (T-027) | yes/no | `window.confirm` | per-order cancel; **medium gravity, but weakest gate** |

The cancel ritual has the **weakest user-side gate** of the three confirmation surfaces. Rationale (implied, not stated in docs): a cancel is conservatively "less dangerous" than a new submission — at worst it stops something. **But** combined with the worker-side gap (§5), this means: the gate that LOOKS the weakest is also the one where the user's action has no real effect, so the gate's strength is moot.

The confirm text shows quantity + symbol but **not** the order's notional value or limit price — the user doesn't see "you're cancelling a €5,000 order" prompt; only "Order voor 10× ASML.AS annuleren?". §9.6.

### 3.2 The `busy` flag and the silent cancel

`setBusy(true)` is set AFTER the confirm resolves (`:184`). The button is disabled (`busy ? "wait" : "pointer"` cursor + `disabled={busy}` at `:284`) only DURING the API call, not during the confirm dialog. A user double-clicking would spawn 2 confirm dialogs in rapid succession — same racy pattern as the JA flow (T-026 §9.7). The state machine at the server would reject the second call with HTTP 422, surfacing as `error` in the UI after the first call had already succeeded.

A user who clicks Cancel/Esc on the confirm gets **no UI feedback at all** (`if (!ok) return;` — no error set, no state update). The button stays clickable, ready for a second attempt. §9.7.

## 4. The server route — `POST /action-draft/{id}/cancel-submitted`

`apps/api/src/portfolio_outlook_api/action_draft.py:779-867`. The docstring at `:786-795` is itself the critical artefact:

> "Task 134 product lock §8 — one-way user-initiated cancellation.
>
> Valid only for in-flight statuses. Transitions the draft to `pending_cancellation` and writes one `ibkr_submission_lifecycle` row tagged `event_type='cancellation_request'`. **Does not call IBKR** — the worker picks the row up from the database on its next sweep tick and issues `ib.cancelOrder()` from the long-lived TWS session (locked: only the worker owns the socket).
>
> The actual `cancelled` status comes from the IBKR callback the worker's lifecycle handler processes."

This describes the intended design (write request → worker polls → worker sends cancel → IBKR callback updates state). T-019 §4.8 and T-027 §5 document that **the worker-polling part is not built**.

### 4.1 The 2 storage writes

The route does, in order:

1. **`repo.apply_lifecycle_transition(action_draft_id, new_status="pending_cancellation", transitioned_at=now)`** (`:826-830`). Same `apply_lifecycle_transition` writer used by the worker submission sweep + reconciliation passes (T-020 §6). State machine validates the transition.
2. **Look up the perm_id** via `_lookup_perm_id_for_draft(audit_repo, action_draft_id)` (`:840-843`). Walks the `ibkr_submission_audit` table for the most recent `placed` row to retrieve the IBKR-side order identifier.
3. **`lifecycle_repo.append(IbkrSubmissionLifecycleEntry(...))`** (`:844-862`) with:
   - `action_draft_id`
   - `event_at = now`
   - `ibkr_perm_id` (or 0 sentinel if no placed row found)
   - `event_type = "cancellation_request"`
   - `from_status = current.status`
   - `to_status = updated.status` (= `"pending_cancellation"`)
   - `ibkr_raw_status = None` (no IBKR data — this is a local-only write)
   - `fill_price_local / fill_quantity / commission / commission_currency = None` (this is not a fill event)
   - `raw_callback_json = {"source": "user_api_cancel", "from_status": current.status}` (the `"source"` tag distinguishes user-driven cancel from IBKR-driven cancelled callbacks)

The lifecycle audit row provides forensic provenance: a future auditor can grep for `event_type='cancellation_request' AND raw_callback_json->>'source' = 'user_api_cancel'` to find every user-driven cancel attempt, regardless of whether the broker eventually processed it.

### 4.2 The 3 error paths

| Condition | HTTP | Dutch detail |
|-----------|------|--------------|
| Draft id not found | 404 | `"Actiedraft niet gevonden."` (`:813`) |
| Status not in `_CANCELLABLE_STATUSES` | 422 | `"Cancel niet toegestaan: draft is niet in een actief IBKR-status (status={status!r})."` (`:816-821`) |
| State machine rejects transition | 422 | message from `ActionDraftStateTransitionError` (`:831-834`) |
| Storage unavailable | 503 | `STORAGE_UNAVAILABLE_DETAIL` Dutch message (`:865-867`) |

The 422 message format embeds the status string verbatim, giving the user a precise debug signal — but the message is also the only place where the user can learn that a `pending_cancellation` draft is non-cancellable (since the UI just hides the button).

## 5. The worker-execution gap — re-surfaced from T-019

This is the dominant finding of T-027 and the most operationally misleading part of the entire frontend audit so far.

### 5.1 The route docstring describes a worker action that doesn't exist

The API route docstring (`action_draft.py:790-793`) describes:

> "the worker picks the row up from the database on its next sweep tick and issues `ib.cancelOrder()` from the long-lived TWS session"

### 5.2 The worker has no such loop

T-019 §4.8 — citing the worker reality:

> "The sweep does **not** itself loop over `pending_cancellation` drafts and issue `cancel_order`. Grep `cancel_order` under `apps/worker/src/portfolio_outlook_worker/` returns **zero** production call sites (only the Protocol declaration at `submitter.py:89` and test no-ops)."

T-019 §10.4: "**`cancel_order` not wired**. The worker has no cancel pathway; user-initiated cancellation requires the API surface."

The `submission_sweep.py` `tick()` polls `user_approved` drafts (T-019 §4) — not `pending_cancellation` drafts. Nothing else in the worker periodically scans for cancellations.

### 5.3 What the user sees vs what actually happens

| User's mental model | Reality |
|---------------------|---------|
| "I clicked Annuleer, the badge changed to 'Annulering aangevraagd', IBKR will cancel the order soon" | Status flipped in DB. Lifecycle audit row written. **IBKR was never contacted.** |
| "If IBKR confirms cancellation, the badge will become 'Geannuleerd'" | Only if the user separately cancels via TWS (out of band) OR if Pass B reconciliation detects IBKR no longer reports the order as in-flight AND that aligns with a cancelled IBKR state |
| "The order won't fill, because I cancelled it" | The order may still fill — IBKR never received the cancel request |
| "I should check back in a few minutes to confirm" | The badge will remain "Annulering aangevraagd" indefinitely unless one of the above out-of-band paths fires |

### 5.4 The only escape paths in current production

A draft stuck in `pending_cancellation` can only reach `cancelled` via:

1. **User cancels manually in TWS desktop** (out of band, not visible to the system until the IBKR callback fires AND the worker's lifecycle handler processes it). Per T-019 §6, the callback handler IS wired to process `cancelledEvent`.
2. **Pass B reconciliation** (T-020 §4) finds IBKR reports the order as `Cancelled` (because of session timeout, broker action, etc.) and writes `status_corrected_to_cancelled`. This requires the broker side to have somehow ended the order, which is independent of the user's click.
3. **Pass C 24-hour timeout** would NOT fire — Pass C only escalates `awaiting_reply_timeout` drafts, not `pending_cancellation` drafts.

There is no automatic timeout for `pending_cancellation`. A draft can sit there forever.

### 5.5 Worst case: fill after "cancel"

If the user clicks Annuleer at 14:00, the badge updates, the user closes the browser, and at 14:15 the order fills (because IBKR never got the cancel), the lifecycle handler will write:
- A `fillEvent` audit row, status transitioning to `filled`.
- BUT — and this is subtle — the state machine widening for `pending_cancellation → filled` may or may not be permitted. T-019 §7 documents the `_RAW_STATUS_MAP` transitions; T-018 §4 documents `_ACTION_DRAFT_TRANSITIONS`. If the storage layer's state-machine map does not permit `pending_cancellation → filled`, the lifecycle handler write would raise `ActionDraftStateTransitionError`, log it, and **leave the draft in `pending_cancellation`** even though IBKR reports it as filled. The user would then see "Annulering aangevraagd" on a filled order — total confusion.

This corner case is not explicitly tested in the reality docs reviewed; T-027 surfaces it as a Phase 1c testing gap. §9.10.

## 6. The post-cancel badge — `<SubmissionLifecycleDrawer>` window

The user can click on a row to open `<SubmissionLifecycleDrawer>` (`apps/web/components/SubmissionLifecycleDrawer.tsx`) which shows the lifecycle audit timeline. The drawer maps status strings to Dutch labels:

`SubmissionLifecycleDrawer.tsx:41`:
```tsx
pending_cancellation: "Annulering aangevraagd",
```

The drawer will show the user's `cancellation_request` event row in the timeline. The user can therefore inspect the audit trail and see when they requested the cancel — but they will NOT see a follow-up "cancel issued to IBKR" event, because no such event is ever written. The timeline ends at the user's request.

For an experienced user who knows to inspect the lifecycle drawer, the absence of a follow-up event is a tell: "my request was recorded, but nothing happened after". For a typical user, the timeline appears complete after the request row, suggesting the cancel is being processed.

## 7. Failure paths from the user's seat

1. **Clicked Annuleer, accidentally clicked Cancel on the confirm** — no UI feedback at all (no toast, no inline message). The button stays clickable. §9.7.
2. **Clicked Annuleer, server returns 422 'Cancel niet toegestaan'** — likely a race where the draft just transitioned to a non-cancellable state (e.g., reconciliation just moved it to `filled`). The user sees the error inline and the button is no longer rendered on the next refresh.
3. **Clicked Annuleer, server returns 503 storage unavailable** — generic Dutch message. The user must wait and retry.
4. **Clicked Annuleer, server returned 200, badge updated, but minutes later the order filled anyway** — the entire §5 failure mode. The user has no UI signal that this is happening; only out-of-band detection (account statement, IBKR email) will reveal it.
5. **Clicked Annuleer on a draft with no `placed` audit row** — `_lookup_perm_id_for_draft` returns `0` as a sentinel (`:874-880`). The lifecycle row gets `ibkr_perm_id=0`. Even if the worker existed, it couldn't issue `cancelOrder` against perm_id 0. §9.8.
6. **Cancel race vs IBKR fill** — if the user clicks Annuleer at the same moment IBKR is sending the fill callback, the state-machine ordering matters. The fill callback path (T-019 §6) and the user-cancel path can both fire near-simultaneously. The first writer wins; the second gets an `ActionDraftStateTransitionError`. The user might see a confusing inline error message about a transition that "shouldn't" fail.

## 8. The 3-tab dashboard structure documented from the user-action angle

| Tab | T-NNN | User actions per row |
|-----|-------|----------------------|
| Te keuren (T-026) | T-026 | Goedkeuren (JA) / Dismiss (free-text reason) / Delete (yes/no) / Bewerken (inline edit) |
| Actief bij IBKR (T-027) | T-027 | Annuleer (yes/no) — only for cancellable statuses |
| Historiek | (not in T-027 scope) | View-only |

The dashboard tabs are the user's only path into per-row actions. There is NO bulk-action surface (no "cancel all" or "approve all" — T-026 §9.10). Every action requires individual click + confirm/prompt. §9.9.

## 9. Phase 1c surface (10 findings on the user-action surface)

1. **Worker-execution gap — the dominant finding** (§5). The cancel request writes are persistent, never-executed records. The user-visible UI gives every signal of success; the broker side never receives the cancel. **A user could cancel an order, see the badge update, close the browser, and have the order fill 30 minutes later.** T-019 §4.8 / §10.4 originating finding re-surfaced from the user-action angle. This is the most operationally dangerous gap surfaced in the entire workflow audit.
2. **Route docstring describes a worker action that doesn't exist** (§5.1) — `action_draft.py:786-795` confidently states "the worker picks the row up from the database on its next sweep tick and issues `ib.cancelOrder()`". The worker has no such loop. The docstring is aspirational, not descriptive. Update needed.
3. **No timeout for `pending_cancellation`** (§5.4) — Pass C only escalates `awaiting_reply_timeout`. A `pending_cancellation` draft can sit forever. Phase 1c should either (a) add a similar timeout for `pending_cancellation` or (b) wire the worker cancel loop and make this moot.
4. **`_CANCELLABLE_STATUSES` duplicated client + server** (§2) — same 4-status frozenset hard-coded at `IbkrSubmissionGrids.tsx:173-177` AND `action_draft.py:774-776`. Drift risk.
5. **Weakest confirmation gate of the 3 user tokens** (§3.1) — `window.confirm` yes/no, no typed token. Compared with BEVESTIG (8-char input field) and JA (typed prompt), Annuleer has the lowest friction. Combined with §5, this means the lowest-friction action is also the most operationally inert.
6. **Confirm text shows quantity + symbol but NOT notional or limit price** (§3.1) — "Order voor 10× ASML.AS annuleren?" leaves out the EUR amount. The user cannot estimate the value at stake from the confirm dialog alone.
7. **Cancel on the confirm dialog gives no UI feedback** (§3.2 + §7.1) — `if (!ok) return;` silently aborts. No toast, no inline message. The user might wonder if their click registered.
8. **`perm_id=0` sentinel for missing placed row** (§7.5) — `_lookup_perm_id_for_draft` returns 0 if no placed audit row exists, and the lifecycle row is written anyway. Even if the worker were wired, it couldn't act on perm_id 0. Cancel requests for draftsthat never placed get silently captured in storage with a useless reference.
9. **No bulk-cancel surface** (§8) — each row requires individual click + confirm. Phase 1c may want to add a "cancel all pending in this account" surface for emergency stops.
10. **`pending_cancellation → filled` transition test gap** (§5.5) — if IBKR fills an order between the user's cancel click and (a hypothetical) worker cancel send, the lifecycle handler must transition `pending_cancellation → filled`. Whether the storage `_ACTION_DRAFT_TRANSITIONS` map permits this transition is not visible in the docs reviewed; needs explicit test.

## 10. Out of scope (re-confirmed)

- **Submission lifecycle** (T-019 — merged sibling; how rows reach `submitted` and the worker `place_order` authority).
- **Approval flow** (T-026 — merged sibling; the path from `proposed` to `user_approved` to `submitted`).
- **Reconciliation Pass B** (T-020 — merged sibling; the only path that could currently rescue a stuck `pending_cancellation` row if the broker side ends the order).
- **`<SubmissionLifecycleDrawer>` deep dive** (T-008 covers it at component level; T-027 cites it for the post-cancel audit-trail viewing).
- **Worker `cancel_order` adapter Protocol implementation** (T-019 §4.8 — the implementation gap; T-027 only re-surfaces from the user-action angle).

## 11. References

- `apps/api/src/portfolio_outlook_api/action_draft.py:770-867` (cancel route + `_CANCELLABLE_STATUSES`)
- `apps/api/src/portfolio_outlook_api/action_draft.py:786-795` (the aspirational docstring describing a worker action that doesn't exist)
- `apps/api/src/portfolio_outlook_api/action_draft.py:870-880` (`_lookup_perm_id_for_draft` — perm_id=0 sentinel)
- `apps/web/components/IbkrSubmissionGrids.tsx:170-301` (cancel button + `handleCancel`)
- `apps/web/components/IbkrSubmissionGrids.tsx:173-177` (`cancellable` predicate — duplicated client-side)
- `apps/web/components/IbkrSubmissionGrids.tsx:179-195` (`handleCancel` with `window.confirm`)
- `apps/web/components/SubmissionLifecycleDrawer.tsx:41` (Dutch label `"Annulering aangevraagd"`)
- `apps/web/app/ibkr-acties/page.tsx:181-209` (3-tab host)
- `apps/web/lib/apiClient.ts:1593-1599` (`cancelSubmittedActionDraft`)
- `docs/reality/workflows/ibkr-order-submission-lifecycle.md` (T-019 — §4.8 + §10.4 originating finding for the worker gap)
- `docs/reality/workflows/ibkr-reconciliation-passes-a-b-c.md` (T-020 — Pass B as the only current escape path)
- `docs/reality/workflows/user-approve-action-draft.md` (T-026 — sibling user-action doc; JA vs Annuleer asymmetry)
- `docs/reality/workflows/user-confirm-starter-watchlist.md` (T-025 — BEVESTIG vs Annuleer asymmetry)
- `docs/reality/components/web-components-feature-grids.md` (T-008 — `<IbkrSubmissionGrids>` component reality)
