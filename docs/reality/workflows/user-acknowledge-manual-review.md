# User Acknowledges Manual Review — Queue Housekeeping, Not Case Resolution

**Scope.** User-action workflow narrating the manual-review acknowledgement ritual from the user's perspective — dashboard `<ReconciliationStatusWidget>` shows pending count → user clicks the card → navigates to `/admin/reconciliation` → sees the "Wacht op handmatige beoordeling" table → clicks small dark "Bevestig" button → `window.prompt` for optional note → POST `/reconciliation/manual-review/{id}/acknowledge` → page does a full 4-endpoint refresh → row disappears from the pending list — **but the underlying Action Draft is NOT touched**. The draft stays in `requires_manual_review` forever; only the queue row's `resolution_status` moves to `acknowledged`.

**Sibling functionality reality**: T-020 `docs/reality/workflows/ibkr-reconciliation-passes-a-b-c.md` §5 (Pass C 24-hour escalation that produces the queue rows) + §6.4 (`manual_review_queue` table) + §7.5 (the acknowledge route — the ONLY mutating route in the entire reconciliation API surface). **Component reality**: T-008 `docs/reality/components/web-components-status-and-shared.md` (`<ReconciliationStatusWidget>`).

## 0. TL;DR — the user's journey, in 6 steps

1. **Dashboard sighting**: on the home dashboard (`/`), the `<ReconciliationStatusWidget>` (`apps/web/components/ReconciliationStatusWidget.tsx:42`) shows a card with key reconciliation metrics — including `pending_manual_review_count`. The card has a warn flag (`warn={data.pending_manual_review_count > 0}`) that turns red when there are rows to review. The card is wrapped in a `<Link href="/admin/reconciliation">` (`:88`).
2. **Navigate**: user clicks the widget. Next.js navigates to `/admin/reconciliation`.
3. **Page loads**: the page (`apps/web/app/admin/reconciliation/page.tsx:44-126`) parallel-fetches 4 endpoints (`getReconciliationStatus`, `getReconciliationManualReview`, `getReconciliationUnmatchedExecutions`, `getReconciliationRuns`) via `Promise.all`. Shows "Laden…" until status resolves, then renders the full page.
4. **Read the table** — the "Wacht op handmatige beoordeling ({count})" section at `:185-257`. Table columns: Action Draft (monospace id) / Reden (Dutch label mapped from `reason`) / Gemarkeerd (`flagged_at` in nl-NL locale) / Detail (`details_dutch`) / **(unnamed action column)** with a small dark "Bevestig" button.
5. **Click Bevestig**: triggers `handleAcknowledge(row.id)` at `:89-106`. Fires `window.prompt("Optionele notitie bij het bevestigen:", "")` — a browser-native prompt asking for an OPTIONAL free-text note. User can type a note, leave it blank, or click Cancel.
6. **Server flips queue row state**: `apiClient.acknowledgeManualReview(queueId, note)` → `POST /reconciliation/manual-review/{queueId}/acknowledge?note=...`. Server runs `queue_repo.acknowledge(queue_id, resolved_at=now, note=note)` and returns the updated row. Page calls `await refresh()` → full re-fetch of all 4 endpoints → table re-renders without the acknowledged row (since the listing endpoint filters to `resolution_status="pending"`).

**Total user-visible time**: ~5 seconds. **But the Action Draft is untouched** — see §5.

## 1. The dashboard entry — `<ReconciliationStatusWidget>` card

**File**: `apps/web/components/ReconciliationStatusWidget.tsx:1-201` (201 LOC).

The widget renders a single card with metrics from `GET /reconciliation/status` (T-020 §7.1):
- `latest_run` summary (when, mode, divergences)
- `drafts_healed_last_24h`
- `pending_manual_review_count` (the count the acknowledge flow operates on)
- `unresolved_unmatched_count`

The widget docstring (`:12`) states: "Clicking the card routes to `/admin/reconciliation` for full detail." The entire card is a Next.js `<Link href="/admin/reconciliation">` at `:88-170`.

**On the dashboard**: mounted at `apps/web/app/page.tsx:75` `<ReconciliationStatusWidget />`. The widget IS visible by default for every user who lands on `/` — so the user has a discovery path even though `/admin/reconciliation` is an "admin" URL.

### 1.1 Visual signal — the warn flag

The `pending_manual_review_count` SummaryCell (`:159-161`) has `warn={data.pending_manual_review_count > 0}` — the cell's background turns red when > 0. This is the user's first visual signal that there's work to do.

The widget does NOT show which specific rows are pending or what they're about — only the count. The user must click through to see what they're acknowledging.

## 2. The admin page — `/admin/reconciliation`

**File**: `apps/web/app/admin/reconciliation/page.tsx:1-390` (390 LOC).

Page structure (Dutch sections):
1. **Header** (`:130-133`) — `<h1>IBKR-reconciliatie</h1>` + account ID subtitle.
2. **Status summary** (`:135-183`) — `<SummaryCell>` grid with 5 cells: laatste run mode, Pass A count, Pass B count, Pass C count, total divergences.
3. **Wacht op handmatige beoordeling (Pass C escalations)** (`:185-257`) — the Bevestig table (T-028 scope).
4. **Onbekende IBKR-uitvoeringen (Pass A orphans)** (`:259-...`) — different read-only table (T-028 out of scope).
5. **Reconciliation runs history** (later in the file) — read-only.

The page is **read-only except for the Bevestig button**. No other action surface exists on this page.

### 2.1 Refresh strategy (`:57-83`)

```tsx
const refresh = useCallback(async () => {
  const [statusResult, reviewResult, unmatchedResult, runsResult] =
    await Promise.all([
      apiClient.getReconciliationStatus(),
      apiClient.getReconciliationManualReview(),
      apiClient.getReconciliationUnmatchedExecutions(),
      apiClient.getReconciliationRuns(),
    ]);
  // ... set state based on each result
}, []);
```

The page fetches **4 endpoints in parallel** on mount (`useEffect` at `:85-87`) AND after every successful acknowledge (`:103 await refresh();`). There is no per-row optimistic update — the entire page state is re-derived from a fresh full fetch every time. §9.5.

## 3. The Bevestig button — table-based, not card-based

The pending-review section (`:185-257`) is the **first table-based action surface** in the user-workflow audit so far. T-025 used a single confirmation form; T-026 + T-027 used per-row article cards. T-028 uses a `<table>`.

### 3.1 Per-row UI (`:215-253`)

```tsx
{(pendingReview ?? []).map((row) => (
  <tr key={row.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
    <td style={{ padding: 8, fontFamily: "monospace" }}>
      {row.action_draft_id}
    </td>
    <td>{REASON_LABELS[row.reason] ?? row.reason}</td>
    <td>{new Date(row.flagged_at).toLocaleString("nl-NL")}</td>
    <td style={{ color: "#374151" }}>{row.details_dutch}</td>
    <td style={{ padding: 8 }}>
      <button
        data-testid={`reconciliation-acknowledge-${row.id}`}
        type="button"
        onClick={() => { if (row.id !== null) void handleAcknowledge(row.id); }}
        style={{
          background: "#1f2937",  // dark slate gray
          color: "#ffffff",
          border: "none",
          padding: "4px 10px",
          borderRadius: 4,
          fontSize: 12,
          cursor: "pointer",
        }}
      >
        Bevestig
      </button>
    </td>
  </tr>
))}
```

The "Bevestig" button uses a **dark-slate background (#1f2937)** — neither the green of approval (Goedkeuren, T-026 §3) nor the red of destruction (Annuleer, T-027 §3) nor the yellow of caution. The colour choice carries no semantic gravity signal — the visual rhetoric implies "this is a neutral acknowledgement, not a decision".

### 3.2 The 4-status `REASON_LABELS` map (`:37-41`)

```tsx
const REASON_LABELS: Record<string, string> = {
  timeout_24h_no_data: "24u timeout zonder IBKR-data",
};
```

**Only ONE reason** is currently mapped — `timeout_24h_no_data`, which is the only `reason` value Pass C writes (T-020 §5.2). If a future Pass C-style escalation writes a different reason string, the table falls back to displaying the raw English-style enum string (per `?? row.reason` at `:222`). §9.6.

### 3.3 The empty state (`:190-196`)

When `pendingReview.length === 0`:
```tsx
<p data-testid="reconciliation-no-pending-review" style={{ color: "#6b7280" }}>
  Geen openstaande rijen.
</p>
```

The section heading still shows `({status.pending_manual_review_count})` which would be `(0)` in the empty case. No "all caught up" or success state styling.

## 4. The acknowledge handler — `window.prompt` + `window.alert`

`apps/web/app/admin/reconciliation/page.tsx:89-106`:

```tsx
const handleAcknowledge = useCallback(
  async (queueId: number) => {
    const note = window.prompt(
      "Optionele notitie bij het bevestigen:",
      "",
    );
    const result = await apiClient.acknowledgeManualReview(
      queueId,
      note ?? undefined,
    );
    if (!result.ok) {
      window.alert("Bevestigen mislukt.");
      return;
    }
    await refresh();
  },
  [refresh],
);
```

### 4.1 The 3rd distinct browser-native dialog pattern

Across the 4 user-action workflows so far:

| Workflow | Confirmation gate | Error display |
|----------|-------------------|----------------|
| T-025 BEVESTIG | styled `<input>` with submit button | inline `<p role="alert">` |
| T-026 JA approve | `window.prompt("Type JA...")` | inline `<div>` below card |
| T-027 Annuleer | `window.confirm("Annuleren?")` | inline `<div>` below card |
| **T-028 Bevestig manual review** | `window.prompt("Optionele notitie...")` | **`window.alert("Bevestigen mislukt.")`** |

T-028 is the only surface that uses `window.alert` for errors. The user gets a browser-native modal dialog with an OK button — un-styleable, accessible-by-default in most browsers, but inconsistent with the inline-error pattern of the other surfaces. §9.7.

### 4.2 The prompt is NOT a confirmation gate

This is the key gravity asymmetry: the `window.prompt` here asks for an **optional note**, not for confirmation. The user clicking Cancel on the prompt does NOT abort the acknowledge:

```tsx
const note = window.prompt(...);  // user can press Cancel (returns null)
const result = await apiClient.acknowledgeManualReview(
  queueId,
  note ?? undefined,   // null → undefined → no note sent
);
```

If `note === null` (user clicked Cancel), the code passes `undefined` to the API client, which sends the request without the `note` query param. **The acknowledge still fires.** The prompt is purely for note-capture, NOT for "are you sure?".

This is the **lowest-gravity confirmation gate of all 4 user-action workflows** — even lower than T-027's `window.confirm` (which AT LEAST aborts on Cancel). T-028 has effectively no confirmation gate at all — the Bevestig button is one click + one Enter (or one Cancel) away from server-side execution.

The lower gravity matches the lower stakes: acknowledging a queue row doesn't affect orders, money, or broker state. But §5 documents that the user might mis-perceive it as case resolution.

## 5. The dominant finding — the draft is untouched

**File**: `apps/api/src/portfolio_outlook_api/reconciliation.py:437-473`.

```python
@router.post(
    "/reconciliation/manual-review/{queue_id}/acknowledge",
    response_model=ManualReviewResponse,
)
def acknowledge_manual_review(
    queue_id: int,
    note: str | None = None,
) -> dict[str, object]:
    """Flip a pending manual-review row to ``acknowledged``.

    Idempotent: re-acknowledging an already-acknowledged row returns
    the existing row unchanged. The underlying Action Draft is **not**
    touched — the user reviewed the row and is closing the queue
    item; the draft's terminal status remains whatever the reconciler
    set it to.
    """
    ...
```

**The docstring (`:447-452`) is explicit**: the route flips `manual_review_queue.resolution_status` from `pending` to `acknowledged`. **It does NOT modify the linked `action_drafts` row at all.** The Action Draft stays in `requires_manual_review` forever.

### 5.1 What the user thinks vs what happens

| User's mental model | Reality |
|---------------------|---------|
| "Clicking Bevestig means I've handled this case" | Only the queue row is updated. The Action Draft is untouched. |
| "The draft will go back to a normal state" | No. It stays in `requires_manual_review` forever. |
| "The reconciler ran out of options, but now I've made a decision" | No decision is recorded against the draft. The note (if any) lives on the queue row, NOT on the draft. |
| "If the same condition comes up again, the row will reappear" | No. Pass C only escalates `awaiting_reply_timeout` drafts. Once a draft is in `requires_manual_review`, Pass C never sees it again (its filter at `pass_c_timeout_recovery.py:84` is `action_draft_repo.list_by_status(account_id, "awaiting_reply_timeout")` — exact match, not in-set). The acknowledged-and-forgotten draft is a permanent zombie. |

### 5.2 The draft's permanent fate

A draft escalated to `requires_manual_review` has **no automatic path out**:
- Pass A doesn't move it (Pass A operates on IBKR-side fills, not on draft status).
- Pass B doesn't move it (Pass B filters to "active in-flight" via `action_draft_repo.list_active_for_account(account_id)`; `requires_manual_review` is not in that filter).
- Pass C doesn't move it (Pass C only handles `awaiting_reply_timeout`).
- The acknowledge route doesn't move it.
- No other API route accepts `requires_manual_review` as a from-state for any transition (per T-018 §4 state-machine vocabulary survey — `requires_manual_review` has no documented out-edges).

**The only way out** is a state-machine intervention via a future feature OR an out-of-band SQL update. In current production: a draft escalated to `requires_manual_review` is a permanent zombie row.

The user clicking Bevestig has no awareness that they're closing a notification on a zombie. They believe they're resolving a case.

### 5.3 The `details_dutch` text doesn't warn

The `details_dutch` text Pass C writes (`pass_c_timeout_recovery.py:131-136`):

> "Action Draft is langer dan 24 uur in awaiting_reply_timeout zonder dat IBKR een uitvoering, status-update of annulering heeft teruggemeld. Handmatige beoordeling vereist."

(Translation: "Action Draft has been in awaiting_reply_timeout for more than 24 hours without IBKR reporting an execution, status update, or cancellation. Manual review required.")

The text describes WHY the row was escalated but says nothing about what acknowledging will do. There is no "Note: acknowledging closes this notification but does NOT resolve the underlying draft" disclaimer. The user has no way to learn from the UI that their action is queue-housekeeping and not case-resolution. §9.1.

## 6. The audit trail

The acknowledge route does NOT write a separate audit row (unlike the cancel route at T-027 which writes both a status change AND a lifecycle audit row). The only persistent record of the acknowledgement is the UPDATE on the `manual_review_queue` row itself:

- `resolution_status: "pending" → "acknowledged"`
- `acknowledged_at: NULL → now()` (the existence of this column implies an intent to capture; the route at `reconciliation.py:465-469` confirms it's populated)
- `acknowledgement_note: NULL → note` (or NULL if the user didn't provide one)

There is **no separate event row** capturing the user's action, no actor field, no IP, no UA. The row carries its full history in three columns. T-025 + T-026 + T-027 all wrote separate audit rows for the user's action; T-028 does not.

This is benign but inconsistent — a future audit query for "all user actions in the system" would find the watchlist + approve + cancel rows but would need to separately know about the `manual_review_queue` `acknowledged_at IS NOT NULL` rows. §9.4.

## 7. Failure paths from the user's seat

1. **Clicked Bevestig, server returned non-200** — `window.alert("Bevestigen mislukt.")` fires. Modal-style, blocking, with no detail. The user clicks OK on the alert; the row stays in the pending table. No retry button; user must click Bevestig again.
2. **Clicked Bevestig, network hung** — the `await apiClient.acknowledgeManualReview(...)` is awaited without a timeout. The page sits unresponsive until the network resolves or the user navigates away. No "Bezig…" indicator on the button.
3. **Clicked Bevestig on a stale row (race)** — another user / browser tab / concurrent request already acknowledged this row. The acknowledge is idempotent (per the route docstring), so the second call succeeds returning the same row. The user sees no error; the refresh removes the row from the table. They never know there was a race.
4. **Clicked Bevestig on a row whose underlying draft was somehow modified** — impossible in current production because no path modifies `requires_manual_review` drafts. But if a future feature allowed it, the queue row would still acknowledge — there's no consistency check.
5. **Hit Cancel on the prompt** — note is null → undefined → request sent without note. Acknowledge still succeeds. The user might think Cancel aborted the action; they'd be wrong.
6. **Storage unreachable** — API returns 503; `window.alert("Bevestigen mislukt.")` fires generically (no distinction from other errors). User has no signal that this is a transient infrastructure issue vs a permanent one.

## 8. Intent vs reality — the actions-area gap

T-020 §10.3 already documented that the intent's 4-tier B/C/D/E classification (`docs/intent/reconciliation.md` §3 + §4) is **absent from code** — Pass B + C write flat divergence-type strings, not tier strings.

T-028 adds a related finding: intent §3 says **"D — Suspicious drift | High | Block downstream, surface as system-decision item in actions area"** + intent §1 doctrine §10 mentions "system-decision actions" surface in the dashboard actions area.

**The reality**: Pass-C-escalated rows are NOT surfaced in the actions area. They live on a separate `/admin/reconciliation` admin page, reachable only by clicking the dashboard widget (which is mounted but not visually emphasised as "needs attention" beyond the warn flag on the count cell). The user has to know to look at the widget. §9.2.

The actions area on the dashboard (the doctrine §10 surface for "system-decision items") shows trade-related items only (Decision Packages requiring review, action drafts to approve, etc.) — NOT reconciliation escalations. The two surfaces are silo'd.

## 9. Phase 1c surface (10 findings on the user-action surface)

1. **"Bevestig" means housekeeping, not resolution** (§5) — the dominant misconception. Clicking Bevestig closes the queue notification but does NOT touch the underlying Action Draft. The draft stays in `requires_manual_review` forever, with no automatic path out. The UI does not warn the user of this. Most conceptually misleading ritual in the workflow audit.
2. **Pass-C escalations are not in the dashboard actions area** (§8) — intent §3 + doctrine §10 mandate D-class items appear there. Reality: they live on the separate `/admin/reconciliation` admin page. Combined with T-020 §10.3 (4-tier classification absent), the entire "system-decision items surface in actions area" doctrine is unimplemented for reconciliation.
3. **No automatic path out of `requires_manual_review`** (§5.2) — Pass A, B, C, and the acknowledge route all leave the status untouched. A future feature or manual SQL is required to ever move the draft out.
4. **No separate audit row for the user's acknowledge** (§6) — the row's own columns capture the history. Inconsistent with T-025 / T-026 / T-027 which write dedicated audit rows. Audit queries for "all user actions" need to know about this asymmetry.
5. **The whole admin page does a 4-endpoint refresh after every acknowledge** (§2.1) — not optimistic. Bandwidth-wasteful but consistent with the "fail-closed" pattern elsewhere.
6. **Only one `REASON_LABELS` mapping** (`timeout_24h_no_data`) — any future reason string would display raw English-style enum text. No translation pipeline, no fallback Dutch message; just identity fallback.
7. **`window.alert` for error display** (§4.1) — third distinct browser-native dialog pattern across the user-action surfaces. Inconsistent with T-026/T-027 inline-error pattern.
8. **Note prompt's Cancel doesn't abort** (§4.2) — `null → undefined → still fires`. Lowest-gravity confirmation gate of the 4 user-action workflows. User can mis-believe they cancelled.
9. **The `details_dutch` text doesn't explain what acknowledging does** (§5.3) — Pass C writes a "what happened" message but no "what will happen on acknowledge" disclaimer. UX gap.
10. **Discovery requires the dashboard widget** — the `/admin/reconciliation` URL is the only path to the table. Without seeing the dashboard widget warn cell, users have no entry point. No top-nav link.

## 10. Out of scope (re-confirmed)

- **Reconciliation tick mechanism** (T-020 — merged sibling; the 3-pass system that produces the queue rows).
- **Pass C 24h escalation logic** (T-020 §5; T-028 cross-references).
- **Unmatched-executions surface** (also on `/admin/reconciliation` but different row type; T-020 §7.6).
- **`<ReconciliationStatusWidget>` deep dive** (T-008 component-level; T-028 cites it as the entry point only).
- **4-tier B/C/D/E classification** (T-020 §10.3 — already flagged).

## 11. References

- `apps/web/app/admin/reconciliation/page.tsx:1-390` (full admin page)
- `apps/web/app/admin/reconciliation/page.tsx:89-106` (`handleAcknowledge`)
- `apps/web/app/admin/reconciliation/page.tsx:185-257` (Pending Manual Review section)
- `apps/web/app/admin/reconciliation/page.tsx:37-41` (`REASON_LABELS`)
- `apps/web/components/ReconciliationStatusWidget.tsx:42, :88-170` (dashboard card linking to admin page)
- `apps/web/app/page.tsx:75` (`<ReconciliationStatusWidget />` mount on dashboard)
- `apps/web/lib/apiClient.ts:1677-1685` (`acknowledgeManualReview` TS binding)
- `apps/api/src/portfolio_outlook_api/reconciliation.py:437-473` (acknowledge route — idempotent, draft-unaffecting)
- `apps/api/src/portfolio_outlook_api/reconciliation.py:447-452` (the route docstring stating "The underlying Action Draft is **not** touched")
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_c_timeout_recovery.py:84, :131-136` (Pass C escalation + `details_dutch` text)
- `docs/reality/workflows/ibkr-reconciliation-passes-a-b-c.md` (T-020 — full reconciliation reality doc)
- `docs/reality/workflows/user-confirm-starter-watchlist.md` (T-025 — BEVESTIG asymmetry)
- `docs/reality/workflows/user-approve-action-draft.md` (T-026 — JA asymmetry)
- `docs/reality/workflows/user-cancel-submitted-order.md` (T-027 — Annuleer asymmetry + parallel "UI looks operational, underlying action doesn't happen" pattern)
- `docs/intent/reconciliation.md` §3 + §4 (the 4-tier B/C/D/E classification + D-class actions-area surface mandate)
- `docs/intent/_trading-system-doctrine.md` §10 (the actions area as the home for system-decision items)
