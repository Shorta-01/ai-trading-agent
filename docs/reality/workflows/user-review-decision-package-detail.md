# User Reviews Decision Package Detail — Seven Locked Dutch Sections

**Scope.** User-action workflow narrating the Decision Package detail review ritual from the user's perspective — user on `/volglijst` opens `<ForecastExplanationPanel>` for an asset → clicks the "Decision Package" link → navigates to `/decision-package/{id}` → page does single `GET /decision-package/{id}` fetch → renders 7 locked Dutch sections → optionally clicks "Maak actie" (only for `{Kopen, Verminderen, Verkopen}` labels) → an action draft is created → router navigates to `/ibkr-acties?new={draft_id}`.

**Sibling functionality reality**: T-017 `docs/reality/workflows/decision-package-composition.md` (the composer that produces the DP this page renders) + T-023 `docs/reality/workflows/ai-explanation-and-budget.md` (the LLM explanation surface — lives separately on `/portefeuille`, NOT on this page; §6). **Component reality**: T-008 `docs/reality/components/web-components-feature-grids.md` (`<ForecastExplanationPanel>` — the single entry point) + T-008 component-level coverage of the DP detail surfaces.

## 0. TL;DR — the user's journey, in 5 steps

1. **Navigate from `/volglijst`**: on the watchlist page, the user expands an asset's `<ForecastExplanationPanel>` (T-008). The panel contains a hyperlink "Decision Package" (`apps/web/components/ForecastExplanationPanel.tsx:248`) pointing to `/decision-package/{id}`. Clicking it navigates the user to the detail page.
2. **Page loads**: `apps/web/app/decision-package/[id]/page.tsx:34-53` fires `apiClient.getDecisionPackage(params.id)`. Three render states: `loading` ("Bezig met laden…"), `unavailable` ("Decision Package niet gevonden."), or full render.
3. **Read through 7 sections**: the `<DecisionPackageDetail>` component renders the locked 7-section layout (per `:6` docstring: "Renders the seven locked Dutch sections defined in the brief"). Each section is identified by a `data-testid="dp-section-*"` for stable test selection.
4. **Optionally inspect the audit chain**: the Audit section truncates the SHA-256 hash to 12 chars with a "Toon volledig" button to expand. The previous-package hash also shown (or "Eerste Decision Package voor dit asset" if first).
5. **Click "Maak actie"** (only for `Kopen / Verminderen / Verkopen` labels): `apiClient.createActionDraft({decision_package_id})` → server creates an action draft → router pushes to `/ibkr-acties?new={action_draft_id}` (which lands the user on T-026's approval surface with the new draft).

**Total user-visible time**: depends entirely on reading speed — the page is read-heavy with 7 dense sections. The actual API call is ~1 second.

## 1. The entry point — `<ForecastExplanationPanel>`

**File**: `apps/web/components/ForecastExplanationPanel.tsx:248`.

```tsx
<Link
  href={`/decision-package/${encodeURIComponent(decisionPackageId)}`}
  ...
>
```

**This is the ONLY link** to `/decision-package/{id}` in the entire frontend (grep verification: `grep -rn "/decision-package/" apps/web/` returns only matches in `apiClient.ts` for the API call + this single Link). There is:
- No top-nav entry for "Decision Packages".
- No dashboard widget linking here.
- No breadcrumb back to the watchlist from the DP detail page.
- No "previous DP" / "next DP" pagination.

A user who lands on a DP detail page via direct URL (e.g., a bookmark or someone sharing a link) has no UI path to discover other DPs. They must navigate back to `/volglijst`, expand the right asset's explanation panel, and click through again. §9.1.

The `decisionPackageId` is `encodeURIComponent`d — defensive against IDs with reserved URL characters, though the SHA-256-prefixed IDs in T-017 §5 don't typically contain any.

## 2. The thin page wrapper — `/decision-package/[id]/page.tsx`

**File**: `apps/web/app/decision-package/[id]/page.tsx:1-76` (76 LOC).

### 2.1 The `useParams` choice (`:10-15`)

The docstring is explicit about a debugging artefact:

> "Uses `useParams()` rather than the `use(params)` Promise-unwrap pattern — `use()` suspends and requires a Suspense boundary, which the parent layout doesn't provide, leaving the page blank in production builds (caught by the Task 132 e2e suite, fixed in the Task 132 hot-fix)."

A historic blank-page bug was caught by tests after a production build difference vs dev. The fix replaced React's new `use()` API with the older `useParams()` hook. The docstring preserves the rationale for future maintainers. §9.2 — not a bug, but a brittle architectural note for any future migration to Suspense.

### 2.2 The 3 render states (`:55-75`)

```tsx
if (unavailable) {
  return <p data-testid="decision-package-not-found">Decision Package niet gevonden.</p>;
}
if (pkg === null) {
  return <p data-testid="decision-package-loading">Bezig met laden…</p>;
}
return <DecisionPackageDetail package={pkg} />;
```

### 2.3 The 404+503 collapse (`:43-46`)

```tsx
} else {
  // apiClient.getJson collapses all non-OK responses (404 + 503) to
  // ``not_reachable`` — surface a single Dutch fallback rather
  // than guessing which one happened.
  setUnavailable(true);
}
```

**404 (DP doesn't exist) and 503 (storage unavailable) collapse to the same error state.** The user cannot distinguish "this DP id was never created" from "the storage layer is down". Both surface as "Decision Package niet gevonden." The collapse is acknowledged in the comment as an `apiClient.getJson` limitation. §9.3.

A user landing on a stale URL right when storage hiccups would conclude "the system deleted my DP", which is false. The DP may exist but be temporarily unreadable.

## 3. The 7 locked Dutch sections — `<DecisionPackageDetail>`

**File**: `apps/web/components/DecisionPackageDetail.tsx:104-440`. The component is **pure presentational** (`:9-11`): "All values come straight from the API — no client-side rendering of forecast math, no client-side translation."

### 3.1 Section 1 — Header (`:109-153`)

```tsx
<header data-testid="dp-section-header">
  <h1>{pkg.symbol}</h1>
  <span data-testid="dp-label-badge" style={{background: labelColor.bg, color: labelColor.fg, ...}}>
    {pkg.suggested_action_label}
  </span>
  <span data-testid="dp-confidence-badge">
    Betrouwbaarheid: {CONFIDENCE_LABEL[pkg.forecast_confidence_level]}
  </span>
  <p data-testid="dp-header-timing">
    Samengesteld op {fmtTs(pkg.composed_at)} — geldig tot {fmtTs(pkg.valid_until)}
  </p>
</header>
```

Three color schemes for the 5 labels (`:19-28`):

| Label | bg | fg | Semantic |
|-------|-----|-----|----------|
| `Kopen` | green | dark green | actionable BUY |
| `Verminderen` | orange | dark orange | actionable PARTIAL SELL |
| `Verkopen` | red | dark red | actionable FULL SELL |
| `Houden` | blue | dark blue | informational hold |
| `Bekijken` | yellow | dark yellow | informational watch |

`Geblokkeerd` (6th locked label per T-015) is NOT mapped in `LABEL_COLOR` — per the comment at `:67-68`: "the underlying CHECK constraint already excludes Geblokkeerd from Decision Packages". If a row with `Geblokkeerd` ever appeared, the badge would error out at `labelColor.bg` lookup. §9.4.

### 3.2 Section 2 — Voorspelling (Forecast, `:155-200`)

`<dl>` of 4 fields:
- **Bandbreedte (EUR)**: `{p10} (p10) — {p50} (mediaan) — {p90} (p90)` — the 3-quantile range from T-015 §3.
- **Kans op stijging**: `{prob_positive * 100}%` rounded to 0 decimals.
- **Kans op verlies (>5%)**: `{prob_loss_gt_5pct * 100}%` — the threshold-specific downside probability.
- **Verwachte volatiliteit**: `{expected_volatility_annualized * 100}% per jaar` rounded to 1 decimal.

All percentages are rendered with Dutch decimal commas via the `fmtPct` helper (`:59-62`). The doctrine "never re-render financial numbers on the client" (commented in `fmtEUR` at `:53-55`) is **loosely held** — `Number(value).toFixed(2)` IS re-rendering. The doctrine more precisely means "don't re-derive financial values from primitives"; pure presentation rounding is acceptable.

### 3.3 Section 3 — Huidige situatie (Current state, `:202-240`)

Three rows:
- **Huidige prijs**: `{current_price_local} {currency_local} ({current_price_eur})` — dual-currency display.
- **Marktdata**: `{FRESHNESS_LABEL[freshness_state]} — {data_age_trading_days} dagen oud` (Vers / Verouderd / Niet beschikbaar — per T-014 §4 freshness classifier).
- **Positie**: `{quantity} stuks (gemiddelde kostprijs: ...)` OR `"Niet in portefeuille."` if `user_holds_position` is false.

The position display reads `held_quantity` + `held_avg_cost_local` directly from the DP payload — which means at compose time, the DP captures a snapshot. If positions change between compose time and review, the user sees the snapshot, not live state. T-017 §6.3 documented the snapshot capture. §9.5.

### 3.4 Section 4 — Gate-uitkomsten (Gate outcomes, `:242-283`)

Table of 5 rows (one per gate from T-017 §3) with columns: Gate / Status / Reden.

- **Gate name** — rendered raw (e.g., `cash_sufficient`). No Dutch translation; the user sees the English-style enum string directly.
- **Status** — "Geslaagd" (green) / "Gefaald" (red).
- **Reden** — `gate.reason_nl` (Dutch) or "—" if empty.

**`gate_name` is not translated** — the user sees `cash_sufficient`, `position_sufficient`, `mode_match`, etc. as-is. The Reden column carries the Dutch human-readable reason when present. §9.6 — the gate-name column is technical English in an otherwise-Dutch page.

### 3.5 Section 5 — Bewijsbronnen (Evidence sources, `:285-301`)

`<ul>` of `evidence_references`. Each item: `<strong>{source_type}</strong>: {claim_summary}`.

`source_type` strings are also raw (e.g., `eodhd_fundamentals`, `ibkr_position`, `prediction_diary`). The `claim_summary` is the Dutch text. Same English-technical-key + Dutch-explanation pattern as gates. §9.6.

### 3.6 Section 6 — Onderbouwing (Explanation, `:303-320`)

**This is the most surprising surface in the audit.** The DP detail page renders:

```tsx
<p data-testid="dp-explanation-text">
  {pkg.deterministic_dutch_explanation}
</p>
```

**The DETERMINISTIC template-driven Dutch text** (the worker DP composer per T-017 §6). **NOT the LLM-generated explanation** from the `decision_package_explanations` cache (T-023).

The LLM explanation `explanation_nl` lives on a different page entirely — `apps/web/app/portefeuille/page.tsx:641-663` renders it per-DP with "Genereer" + "Laad" buttons.

**The two surfaces show DIFFERENT Dutch text for the same DP**:
- `/decision-package/{id}` Section 6 → deterministic template (always the same for the same DP inputs).
- `/portefeuille` per-DP block → LLM paraphrase (which per T-023 §1.2 is a "twee tot drie zinnen" — 2-3 sentence — rewrite, NOT the intent §1 6-element structured output).

There is **no cross-link**. A user reading the DP detail page is unaware the LLM paraphrase exists; a user on `/portefeuille` is unaware they can see the full deterministic template at `/decision-package/{id}`. The two Dutch explanations describe the same DP but the user can only see one at a time. §9.7.

### 3.7 Section 7 — Audit (`:322-387`)

Three rows:
- **Samengesteld op** — `composed_at` timestamp (UTC, per the `fmtTs` choice at `:45-50`).
- **Audit-hash** — `audit_trail_hash.slice(0, 12) + "…"` with a `"Toon volledig"` button that toggles to the full SHA-256 hex.
- **Vorige package** — `previous_package_hash.slice(0, 12) + "…"` (also truncated) OR "Eerste Decision Package voor dit asset." if first.

The truncate-with-toggle pattern preserves screen real estate while exposing forensic detail on demand. The hash chain (T-017 §5: `previous_package_hash` linking each DP to its predecessor) is visible. §9.8 — only the immediate parent is shown; the full chain (parent of parent of...) requires navigating to the previous DP separately. There's no "show full chain" view.

### 3.8 Optional Section 8 — Maak actie (`:389-437`)

```tsx
const canCreateDraft = ACTIONABLE_LABELS.has(pkg.suggested_action_label);
```

Where `ACTIONABLE_LABELS = new Set(["Kopen", "Verminderen", "Verkopen"])` (`:69-73`). Houden / Bekijken / Geblokkeerd get NO "Maak actie" button — the entire section is conditionally hidden.

The button color is green (`#15803d`), the same as Goedkeuren in T-026 §2.2. The text "Maak actie" (= "Create action"). On click:

```tsx
const result = await apiClient.createActionDraft({
  decision_package_id: pkg.decision_package_id,
});
router.push(`/ibkr-acties?new=${encodeURIComponent(result.data.action_draft_id)}`);
```

The `?new=...` query param lands the user on the action drafts page with the new draft highlighted (T-026 §1). Single click + automatic navigation — no confirmation token (compare BEVESTIG / JA / window.confirm). The rationale: creating a draft is itself revocable (T-026 dismisses + deletes available); the irreversible step is the JA approval inside the draft.

The error path: `setDraftError(result.message || "Aanmaken van actiedraft mislukt.")` — red inline div similar to T-026 pattern. No auto-retry.

## 4. Formatting helpers — money, percent, timestamp

The component defines 3 helpers (`:45-62`):

```tsx
function fmtTs(value: string): string {
  return value.replace("T", " ").replace(/\+00:00$/, " UTC");
}

function fmtEUR(value: string): string {
  return `€${Number(value).toFixed(2).replace(".", ",")}`;
}

function fmtPct(value: string, decimals = 0): string {
  const pct = Number(value) * 100;
  return `${pct.toFixed(decimals).replace(".", ",")}%`;
}
```

### 4.1 `fmtTs` — keeps UTC, no localization (`:45-50`)

> "The API returns ISO 8601 already; just slice the wall-time without converting to local TZ — the package is timezone-aware (UTC) and surfacing it as UTC keeps the audit chain readable."

A user in Brussels reading a DP composed at `2026-05-27T06:00:00+00:00` sees "2026-05-27 06:00:00 UTC" rather than "2026-05-27 08:00:00 Europe/Brussels". The trade-off: cross-timezone consistency (audit) vs local readability (UX). The choice favors the former. §9.9.

### 4.2 `fmtEUR` and `fmtPct` — Dutch decimal comma

Both helpers replace the `.` with `,` for Dutch locale. They use `Number(value).toFixed(N)` which **does** convert from the API's full-precision string to a JS number — losing precision for very large values (> 2^53). The doctrine boundary "never re-render financial numbers" is loosened here for display purposes. T-008 §1.4 documented the broader Decimal-as-string discipline. §9.10.

## 5. Failure paths from the user's seat

1. **`/decision-package/invalid_id`** — apiClient returns non-200 → `setUnavailable(true)` → "Decision Package niet gevonden." Cannot distinguish 404 from 503.
2. **Page loads but `/maak-actie` fails** — green button shows "Bezig…" briefly, then red error inline: "Aanmaken van actiedraft mislukt." The DP is still readable; user can retry.
3. **DP has `Geblokkeerd` label** — `LABEL_COLOR[pkg.suggested_action_label]` returns `undefined`; the badge style throws. **Crash.** The CHECK constraint per `:67-68` is supposed to prevent this from ever reaching the page; if it does (bug in constraint, dev data), the user sees a blank screen or a React error boundary if one is configured. §9.4.
4. **Page navigated to from `/volglijst` but the DP has been superseded** — DP detail page renders as normal (no visual indication that a newer DP exists). The user might act on stale analysis. Cross-reference: T-026 §9.9 documented that superseded drafts are still approvable; same applies to DPs.
5. **`previous_package_hash` chain has a missing parent** — page shows the truncated parent hash. Clicking it does NOT navigate anywhere (it's a plain monospace span, not a link). User can copy the hash but has no UI to look up the parent DP. §9.8.

## 6. Phase 1c surface (10 findings on the user-action surface)

1. **Single entry point** (§1) — only `<ForecastExplanationPanel>` links to `/decision-package/{id}`. No top-nav, no dashboard widget, no breadcrumb. URL-shared DP links have no contextual navigation back.
2. **`useParams` vs `use()` brittleness note** (§2.1) — the docstring preserves a historic blank-page bug rationale. Any future Suspense-aware refactor must keep this in mind.
3. **404 + 503 collapse to single Dutch fallback** (§2.3) — user cannot distinguish "DP never existed" from "storage temporarily unreachable".
4. **`Geblokkeerd` label has no `LABEL_COLOR` mapping** (§3.1) — relies on CHECK constraint to prevent the row from ever reaching the page. Defense-in-depth missing on the frontend.
5. **`held_quantity` is snapshotted at compose time, not live** (§3.3) — DP shows the position as it was at composition; if positions change before review, user sees stale data.
6. **`gate_name` and `source_type` rendered raw English** (§3.4, §3.5) — Dutch page has English-style enum keys in two sections. Inconsistent translation discipline.
7. **Deterministic vs LLM explanation surface fragmentation** (§3.6) — DP detail shows the deterministic template; LLM paraphrase lives on `/portefeuille`. Same DP, two different Dutch texts, no cross-link. **Most surprising finding of T-030.**
8. **Hash chain shows immediate parent only** (§3.7, §5.5) — no "show full chain" view; parent hash is monospace text, not a link. Forensic chain navigation requires manual URL construction.
9. **Timestamp displayed in UTC, not local** (§4.1) — audit-friendly choice; less readable for users.
10. **`Number(value).toFixed(N)` in formatters** (§4.2) — Decimal-as-string discipline loosened for display. Acceptable today; could break for absurdly large amounts (> 2^53).

## 7. Out of scope (re-confirmed)

- **DP composer mechanics** (T-017 — merged sibling; the path that produces the row this page renders).
- **LLM explanation surface** (T-023 — merged sibling; the parallel surface on `/portefeuille`).
- **Action draft creation flow** (T-018 — merged sibling; downstream of "Maak actie" click).
- **5 composition gates deep dive** (T-017 §3 — referenced from the rendered gate-outcomes table).
- **Predictor backtest / leaderboard** (T-024 — merged sibling).

## 8. References

- `apps/web/app/decision-package/[id]/page.tsx:1-76` (thin client page)
- `apps/web/components/DecisionPackageDetail.tsx:1-440` (7-section view)
- `apps/web/components/DecisionPackageDetail.tsx:19-28` (`LABEL_COLOR` — 5 of 6 labels mapped)
- `apps/web/components/DecisionPackageDetail.tsx:45-62` (formatters)
- `apps/web/components/DecisionPackageDetail.tsx:69-73` (`ACTIONABLE_LABELS`)
- `apps/web/components/DecisionPackageDetail.tsx:88-102` (`handleMaakActie`)
- `apps/web/components/DecisionPackageDetail.tsx:303-320` (Section 6 — deterministic explanation)
- `apps/web/components/DecisionPackageDetail.tsx:322-387` (Section 7 — Audit)
- `apps/web/components/ForecastExplanationPanel.tsx:248` (the SINGLE entry point Link)
- `apps/web/app/portefeuille/page.tsx:109-159, :641-663` (the parallel LLM explanation surface; T-023 cross-ref)
- `apps/web/lib/apiClient.ts:1532` (`getDecisionPackage` TS binding)
- `docs/reality/workflows/decision-package-composition.md` (T-017)
- `docs/reality/workflows/ai-explanation-and-budget.md` (T-023 — LLM explanation surface)
- `docs/reality/workflows/forecast-generation-and-labelling.md` (T-015 — 6 labels including `Geblokkeerd`)
- `docs/reality/workflows/market-data-pipeline.md` (T-014 §4 — freshness classifier feeding `freshness_state`)
- `docs/reality/components/web-components-feature-grids.md` (T-008 — `<ForecastExplanationPanel>` component reality)
