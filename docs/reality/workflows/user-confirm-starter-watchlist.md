# User Confirms Starter Watchlist — The BEVESTIG Ritual

**Scope.** User-action workflow narrating the BEVESTIG confirmation ritual from the user's perspective — banner sighting on any page (60-second poll) → click "Naar Volglijst" → see the 12-row starter set → optionally delete rows via the optimistic-archive flow → type the literal Dutch token `BEVESTIG` (case-sensitive uppercase) → submit → state transitions `unconfirmed → confirmed`. This is the **user-action** overlay on T-012's cold-start mechanism doc; T-012 covers the worker-side seeding mechanics, T-025 covers what the user sees and types.

**Intent**: `docs/intent/_phase-1-charter.md` (no dedicated user-action intent doc — the BEVESTIG ritual is locked in T-012's functionality doc). **Sibling functionality reality**: T-012 `docs/reality/workflows/cold-start-seeding-and-watchlist-confirmation.md` (the system mechanism this user action triggers). **Component reality**: T-008 `docs/reality/components/web-components-feature-grids.md` §11 (`<VolglijstColdStartFlow>`), T-008 `web-components-status-and-shared.md` §5 (`<ColdStartBanner>`), T-008 `web-pages.md` §3.6 (`/volglijst` page), T-005 `api-actions-suggestions-and-watchlists.md` (the 5 confirmation routes).

## 0. TL;DR — the user's journey, in 7 steps

1. **First-time login**: user lands on any page (dashboard, `/portefeuille`, `/instellingen`, etc.). The global `<ColdStartBanner>` mounted in `app/layout.tsx` polls `/watchlist/confirmation-state` every 60s and surfaces a sticky amber banner: `<state.banner_text>` + a "Naar Volglijst" button. (Until the first poll completes the banner renders `null` — no flash.)
2. **Click "Naar Volglijst"**: navigates to `/volglijst`. The page loads, calls `/watchlist/confirmation-state`, sees `state="unconfirmed"`, renders `<VolglijstColdStartFlow>` instead of the normal watchlist view.
3. **Read the starter list**: 12 starter assets (typically Belgian/European blue chips per the seed config) appear as a list with their symbol + optional name + optional exchange.
4. **Optionally delete rows**: each row has a "Verwijder" button. Click it → optimistic UI removes the row instantly; an `apiClient.deleteColdStartWatchlistItem(watchlist_item_id)` fires in the background and archives the row in storage.
5. **Type `BEVESTIG`**: monospace input field at the bottom. The user must type the literal uppercase Dutch token. Lowercase or any other input → server returns HTTP 400 with a Dutch error.
6. **Click "Volglijst bevestigen"**: the green submit button (gray-disabled until the input has text and the list has ≥1 row). API call goes to `POST /watchlist/confirm` with `{confirmation_phrase: "BEVESTIG"}`.
7. **Server confirms**: server validates 4 gates (phrase, account configured, state pre-condition, row count > 0), upserts `watchlist_confirmation_state` to `confirmed`, appends one `watchlist_confirmation_audit` row with `actor="user"`, and returns `{state: "confirmed", confirmed_at, row_count}`. The page `loadConfirmationState` re-fires, sees `state="confirmed"`, and swaps to `<VolglijstConfirmedView>`. The global banner's next 60s poll sees `state="confirmed"`, renders `null`, and the banner disappears across the whole site.

**Total user-visible time**: typically ~5 seconds (4 keystrokes + 1 click + 1 round-trip). The next worker orchestrator fire (06:00 or hourly) will detect `mode_detected="normal"` and run the full morning chain (T-011).

## 1. The banner — `<ColdStartBanner>` (60-second poll)

**File**: `apps/web/components/ColdStartBanner.tsx:1-93` (93 LOC). Mounted globally in `app/layout.tsx` (docstring `:13`).

### 1.1 Three render states

| `state` returned by API | Banner renders | User sees |
|--------------------------|----------------|-----------|
| `unconfirmed` | Full sticky amber banner (`:53-92`) with `banner_text` + "Naar Volglijst" Link | yellow banner across the top of every page |
| `confirmed` | `null` (`:53-54`) | nothing |
| `no_account_configured` | `null` | nothing |
| (initial — before first poll resolves) | `null` (`state === null` short-circuit) | nothing — prevents flash-of-banner during initial load |

### 1.2 Polling cadence

`POLL_INTERVAL_MS = 60_000` (`ColdStartBanner.tsx:24`). Every 60 seconds the component re-fetches `/watchlist/confirmation-state` (`:35` `apiClient.getWatchlistConfirmationState()`) and re-renders accordingly. Consequence for the user: after the confirmation succeeds, the banner can stay visible on **other** browser tabs for up to 60 seconds while their poll cycle catches up. The local tab that did the confirm sees instant removal (because `<VolglijstColdStartFlow>` calls `onConfirmed` which re-fires the page's own state load, not the banner's poll cycle — see §3.4).

### 1.3 The banner_text comes from the server

The component renders `state.banner_text` verbatim (`:76`). The actual Dutch text is built server-side in `watchlist_confirmation_routes.py` (in the `unconfirmed` branch of `read_watchlist_confirmation_state`). T-025 does not re-document the server text — Phase 1c finding §9.1 flags that the text is server-rendered, which means it cannot be re-translated per user locale by the frontend.

## 2. The `/volglijst` page — conditional render

**File**: `apps/web/app/volglijst/page.tsx:1-200`.

### 2.1 The branch at `:53-69`

```tsx
if (!confirmationLoaded) {
  return <p>Bezig met laden…</p>;
}

if (confirmationState?.state === "unconfirmed") {
  return (
    <VolglijstColdStartFlow
      onConfirmed={() => void loadConfirmationState()}
    />
  );
}

return <VolglijstConfirmedView />;
```

The page calls `apiClient.getWatchlistConfirmationState()` once on mount (`:39-47, :49-51`). Three render states:

| `confirmationLoaded` | `confirmationState.state` | Renders |
|----------------------|----------------------------|---------|
| `false` | — | "Bezig met laden…" (Dutch loading message) |
| `true` | `unconfirmed` | `<VolglijstColdStartFlow>` |
| `true` | `confirmed` / `no_account_configured` / (anything else) | `<VolglijstConfirmedView>` (the normal watchlist surface) |

The `onConfirmed={() => void loadConfirmationState()}` callback (`:64`) is what closes the loop: after a successful BEVESTIG submit, `<VolglijstColdStartFlow>` calls this, the page re-loads the confirmation state, sees `confirmed`, and swaps to `<VolglijstConfirmedView>` — instant UI switch without waiting on the banner's 60s poll.

## 3. The form — `<VolglijstColdStartFlow>`

**File**: `apps/web/components/VolglijstColdStartFlow.tsx:1-225` (225 LOC). Docstring `:4-15` declares the contract:

> "Task 128: cold-start confirmation flow for the Volglijst page... The locked confirmation phrase is the uppercase Dutch word `BEVESTIG`. Lowercase / other input → server returns HTTP 400 with a Dutch detail; we surface it inline."

### 3.1 Three sections rendered top-to-bottom

1. **Yellow info card** (`:89-103`) — `data-testid="cold-start-info-card"`. Text: "Startvoorstel. Verwijder of voeg toe wat je wilt. Klik op 'Volglijst bevestigen' wanneer je tevreden bent." (translation: "Starter proposal. Delete or add what you want. Click 'Confirm watchlist' when you're satisfied.")
2. **Starter list** (`:105-163`) — `data-testid="cold-start-items"`. Lists the 12 seeded rows; each row is `<li data-testid="cold-start-row-{symbol}">` with the symbol + optional name + optional exchange + a "Verwijder" button. Below: a "+ Asset toevoegen" anchor link to `#manual-add` (which is currently a placeholder — see §9.2).
3. **Confirm block** (`:165-222`) — `data-testid="cold-start-confirm-block"`. Heading "Bevestig je Volglijst" + the instruction text + the monospace input + the green submit button + the inline error display.

### 3.2 The submit-button gating (`:85`)

```tsx
const canSubmit = items.length > 0 && phrase.trim().length > 0;
```

Two client-side preconditions:
- The starter list must have ≥1 row (so the user can't confirm an empty watchlist).
- The phrase input must have non-whitespace content.

The button (`:195-211`) is `disabled` when `!canSubmit || submitting`. Visually grayed-out (`background: "#9ca3af"`) when disabled, green (`#15803d`) when enabled. This is a UX-only gate — the server enforces all 4 validations independently (§5).

### 3.3 The optimistic-archive flow (`handleArchive` at `:56-68`)

```tsx
async function handleArchive(watchlistItemId: string) {
  setError(null);
  const result = await apiClient.deleteColdStartWatchlistItem(
    watchlistItemId,
  );
  if (!result.ok) {
    setError(result.message);
    return;
  }
  setItems((prev) =>
    prev.filter((row) => row.watchlist_item_id !== watchlistItemId),
  );
}
```

**Not strictly optimistic**: the local state update happens **after** the server confirms the delete succeeded. If the request fails, the row stays visible and an error renders in `setError`. The naming in the file ("optimistic-archive" — used in the T-012 reality doc) is a loose label; the actual implementation is **fail-closed** (the row only disappears on server confirmation).

### 3.4 The submit handler (`handleConfirm` at `:70-83`)

```tsx
async function handleConfirm() {
  setError(null);
  setSubmitting(true);
  try {
    const result = await apiClient.confirmWatchlist(phrase);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    onConfirmed();
  } finally {
    setSubmitting(false);
  }
}
```

On success → `onConfirmed()` callback fires → parent page reloads state → swaps view. On failure → inline error renders + button re-enables for retry. No automatic retry; user must click again.

## 4. The phrase — `LOCKED_CONFIRMATION_PHRASE = "BEVESTIG"`

**File**: `apps/api/src/portfolio_outlook_api/watchlist_confirmation_routes.py:45`.

```python
LOCKED_CONFIRMATION_PHRASE = "BEVESTIG"
```

**Case-sensitive, exact match.** The validation check at `:202`:

```python
if body.confirmation_phrase != LOCKED_CONFIRMATION_PHRASE:
    raise HTTPException(status_code=400, detail="Bevestigingscode is onjuist.")
```

This is a **direct string compare** — no `.upper()`, no `.strip()`, no fuzzy match. The Pydantic field `confirmation_phrase` at `:70` only validates `min_length=1, max_length=64`; case-sensitivity is enforced solely by the equality check at `:202`.

**User-visible consequence**: typing `bevestig` (lowercase), `Bevestig` (titlecase), `BEVESTIG ` (trailing space — though the user can't easily produce one in the input field), or any other variant returns the same Dutch error "Bevestigingscode is onjuist." with no hint about case-sensitivity. §9.3.

## 5. The 4-validation chain (`POST /watchlist/confirm:200-280`)

In the order checked:

| # | Gate | File:line | HTTP code | Dutch error |
|---|------|-----------|-----------|-------------|
| 1 | `confirmation_phrase == "BEVESTIG"` | `:202-205` | 400 | "Bevestigingscode is onjuist." |
| 2 | `_configured_account_id() is not None` | `:207-212` | 409 | "Geen IBKR-account geconfigureerd." |
| 3 | `existing.state == "unconfirmed"` (not None, not already `confirmed`) | `:231-245` | 409 | "Volglijst is al bevestigd." (if already confirmed) OR "Volglijst-startvoorstel is nog niet geseed. Wacht tot de volgende geplande run." (if no state row) |
| 4 | `wl_repo.count_active_for_account(account_id) > 0` | `:247-252` | 422 | "Volglijst is leeg. Voeg eerst een asset toe." |

Gate ordering matters: a fresh installation with no account configured + no seed run + empty watchlist + the user typing "bevestig" (lowercase) would surface error #1 first ("Bevestigingscode is onjuist."), even though three other things are also wrong. Only after fixing the phrase does the user discover the next blocker. §9.4.

### 5.1 Race on gate #3

If two browser tabs are both showing the cold-start flow and both submit `BEVESTIG` within milliseconds, both pass gate #1 (same phrase), both pass gate #2 (same account), both pass gate #3 read (still `unconfirmed`), both pass gate #4 (same row count), and both attempt the upsert. The `state_repo.upsert` (`:255-261`) will succeed for both — `upsert` is by definition idempotent on the same `(ibkr_account_id, state)` key. But the audit table (§7) will get **two** `unconfirmed → confirmed` rows with the same `actor="user"`, both at near-identical `event_at` timestamps. This is benign (no state corruption) but pollutes the audit chain. §9.5.

### 5.2 Storage error path (`:281-282`)

`except StorageConnectionError: _raise_storage_unavailable()` returns HTTP 503 with the locked `STORAGE_UNAVAILABLE_DETAIL` Dutch message. The user-visible behaviour: their click does nothing visible for a moment, then a Dutch error appears in the inline error spot. No retry-after header; the user is left to refresh and try again.

## 6. Optimistic vs server-confirmed UI moments

| Moment | Optimistic? | Behaviour |
|--------|-------------|-----------|
| Banner appearance on cold start | No | Banner appears only after the first 60s poll resolves with `state="unconfirmed"`. Initial load shows nothing. |
| Delete a row | No (despite naming) — see §3.3 | Row only disappears after server confirms; failure surfaces inline error. |
| Phrase input typing | N/A | Pure client state; no server interaction. |
| Submit button enabled state | Client-only | `canSubmit` recomputes on every render; no server consultation. |
| BEVESTIG submission | No | Submit fires; button shows "Bezig met bevestigen…"; UI swaps only on server success. |
| View swap after confirm | Client-driven on success | `onConfirmed()` re-fires `loadConfirmationState()` immediately; no waiting on the banner's 60s cycle. |
| Banner disappears across other tabs | Lag up to 60s | Other tabs' `<ColdStartBanner>` polls catch up at their next 60s interval. |

The system has **no truly optimistic mutations** in this workflow — every state-changing UI update waits for a server response. This is correct for a confirmation ritual (you want server truth before claiming success) but is a deliberate design choice the user experiences as "the system feels slower than it looks like it should be" — every click waits on a round-trip. §9.6.

## 7. The audit chain from the user's perspective

After a successful BEVESTIG, exactly two storage writes happen (the orchestrator → seed_runner writes from cold start are separate; see T-012):

1. **`watchlist_confirmation_state.upsert`** (`watchlist_confirmation_routes.py:255-261`):
   ```python
   WatchlistConfirmationStateRecord(
       ibkr_account_id=account_id,
       state="confirmed",
       last_updated_at=now,
   )
   ```
   This is a mutating row (the prior `unconfirmed` row is overwritten). The audit table preserves history.

2. **`watchlist_confirmation_audit.append`** (`:262-272`):
   ```python
   WatchlistConfirmationAuditEntry(
       event_at=now,
       ibkr_account_id=account_id,
       from_state="unconfirmed",
       to_state="confirmed",
       actor="user",
       row_count_at_event=row_count,
       details_json=None,
   )
   ```

   **`actor="user"`** is the literal string written here. This is the only place the user's action is distinguished from a system action in the audit table. The schema permits other values (e.g., a hypothetical admin-override path) but in the current code, only `"user"` is ever written from this route. §9.7.

   `details_json=None` — the audit row carries no IP, no user-agent, no session ID, no client timestamp. The only forensic data is `event_at` (server clock) and `row_count_at_event`. §9.8.

The audit table is the source of truth for "did the user confirm? when?" — the state table only carries the current state, not history. A future feature to display "your watchlist was confirmed on YYYY-MM-DD" would read from the audit table.

## 8. Failure paths from the user's seat

1. **Banner doesn't appear** — the user might never know to confirm. Common causes:
   - `IBKR_ACCOUNT_ID_HINT` env var unset → `state="no_account_configured"` → no banner. The user has no IBKR account configured but also no on-screen guidance to set one.
   - Storage unreachable → API returns `state="no_account_configured"` (per `:162-169`, the same defensive fallback) → no banner. The user sees a green-light system that's actually broken upstream. §9.9.
2. **Banner appears but `/volglijst` shows empty list** — the seed_runner didn't run yet (or failed silently per T-012 §6, where exceptions are swallowed in the orchestrator). The user sees the cold-start info card, the "Geen items in het startvoorstel." empty-state message, and the disabled BEVESTIG button (since `canSubmit` requires `items.length > 0`). No actionable next step is shown — the user is told to "add what you want" via the "+ Asset toevoegen" anchor link, which currently points to `#manual-add` (a placeholder). §9.2.
3. **Typed `bevestig` (lowercase)** — HTTP 400, error "Bevestigingscode is onjuist." renders inline. No hint about case-sensitivity. User must guess.
4. **Typed `BEVESTIG` but storage is down** — HTTP 503, generic "Storage onbeschikbaar" Dutch message. User clicks Bezig… → error appears → tries again.
5. **Confirmed in browser tab A, then opens tab B** — tab B's `<VolglijstColdStartFlow>` does its own `getColdStartWatchlistItems()` fetch, sees the items still there (delete-archived rows are filtered server-side), and the user re-types BEVESTIG, then gets gate #3's "Volglijst is al bevestigd." Now they're confused — the local state in tab B says "unconfirmed" (the page state captured at first load) but the server says "confirmed". The 60s banner poll eventually catches up. §9.5.

## 9. Phase 1c surface (10 findings on the user-action surface)

1. **`banner_text` is server-rendered Dutch**, not built client-side — the frontend has no path to localize the banner for English or any other language. The text is locked Dutch.
2. **"+ Asset toevoegen" is a placeholder** — the anchor at `VolglijstColdStartFlow.tsx:157-161` points to `#manual-add` which is not implemented in this component. The user is told they can add assets before confirming, but the actual add-asset surface (`<AssetIdentityPicker>` in the confirmed view) is only reachable AFTER confirmation. Bootstrap paradox.
3. **No case-sensitivity hint on the BEVESTIG input** — error message just says "Bevestigingscode is onjuist." When the user typed `bevestig` they have to guess that case matters. The input placeholder shows `BEVESTIG` in monospace which is the only visual hint.
4. **Gate ordering hides downstream blockers** — a fresh install with 4 simultaneous problems surfaces them one at a time, each requiring a separate retry. No "preflight check" surface that lists all blockers up front.
5. **No idempotency key on the submit** — two near-simultaneous browser tabs can both write `unconfirmed → confirmed` audit rows. Benign for state but pollutes audit. No client-supplied request ID; server doesn't dedupe.
6. **No truly optimistic UI updates** — every state-changing action waits on server response. Acceptable for a one-time ritual but contributes to "system feels sluggish" impression. Compare with deletes on the normal `<VolglijstConfirmedView>` which use a similar fail-closed pattern (T-008 §11).
7. **Audit row's `actor="user"` is a hard-coded string** — no session/user differentiation. If the system ever supports multiple users per account, the audit table cannot tell them apart. The schema permits other actor strings but no other route writes any.
8. **`details_json=None` on confirmation audit** — no IP, no user-agent, no client timestamp captured. Minimal forensic surface. T-012 §5.2 already documented the audit schema; T-025 confirms the route does not populate the `details_json` slot.
9. **Banner stays hidden when storage is down** — the API treats `storage_unavailable` as `state="no_account_configured"` (`:162-169`), which suppresses the banner. The user sees a normal-looking dashboard while the system is actually unable to determine confirmation state. A "storage down" surface should ideally render a distinct alert state, not silently hide the banner.
10. **`<ColdStartBanner>` and `/volglijst/page.tsx` both poll the same endpoint independently** — no shared state. After the user confirms in one tab, the local page swaps view instantly, but other open tabs (and the banner on the same tab) lag up to 60s. A shared client cache (React Query, SWR) would fix this. Currently neither library is used.

## 10. Out of scope (re-confirmed)

- **Cold-start seed mechanism** (T-012 — merged sibling; the worker-side `seed_runner` writing the 12 starter rows).
- **Worker orchestrator detection** (T-007 §6, covered in T-012 §1; `mode_detected="cold_start"` logic).
- **Asset-search via `<AssetIdentityPicker>`** (used only after confirmation; T-008).
- **Post-confirmation morning chain** (T-011 — merged sibling).
- **`<VolglijstConfirmedView>`** (the normal watchlist surface; T-008 covers it at component level).

## 11. References

- `apps/web/components/ColdStartBanner.tsx:1-93` (global 60s-poll banner)
- `apps/web/components/VolglijstColdStartFlow.tsx:1-225` (the confirmation form)
- `apps/web/app/volglijst/page.tsx:1-200` (page-level conditional render)
- `apps/web/lib/apiClient.ts:1482, :1486-1490` (TS bindings: `getWatchlistConfirmationState`, `confirmWatchlist`)
- `apps/api/src/portfolio_outlook_api/watchlist_confirmation_routes.py:45` (`LOCKED_CONFIRMATION_PHRASE = "BEVESTIG"`), `:139-198` (`GET /watchlist/confirmation-state`), `:200-284` (`POST /watchlist/confirm`)
- `docs/reality/workflows/cold-start-seeding-and-watchlist-confirmation.md` (T-012 — the full functionality reality doc that T-025 overlays the user-action narrative onto)
- `docs/reality/components/web-components-feature-grids.md` §11 (T-008 — `<VolglijstColdStartFlow>`)
- `docs/reality/components/web-components-status-and-shared.md` §5 (T-008 — `<ColdStartBanner>`)
- `docs/reality/components/web-pages.md` §3.6 (T-008 — `/volglijst` page)
- `docs/reality/components/api-actions-suggestions-and-watchlists.md` (T-005 — the 5 confirmation routes)
