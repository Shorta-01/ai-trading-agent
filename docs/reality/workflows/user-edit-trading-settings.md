# User Edits Trading Settings — One Visible Field Out of Eleven

**Scope.** User-action workflow narrating the trading-settings edit ritual from the user's perspective — `/instellingen` arrival → see one input field labelled "Cashbuffer (EUR)" → type a number → click "Opslaan" → success message renders. The dominant finding: the domain model `UserStrategySettings` defines **11+ fields** but the Instellingen page exposes **exactly one** of them (`user_buffer_eur`). The other ten — `portfolio_goal`, `risk_level`, `asset_mix_preference`, `preferred_regions`, `preferred_sectors`, `avoided_sectors`, `max_position_pct`, `min_cash_reserve_pct`, `currency_preference`, `prefer_simple_belgian_tax_admin` — are passed through unchanged via read-modify-write and never appear in any user-facing surface.

**Sibling functionality reality**: T-006 `docs/reality/components/api-infrastructure-and-ai.md` (settings API surface), T-061 `docs/reality/components/settings-and-credentials-infrastructure.md` (the 5-category split). **Domain reality**: T-002 `docs/reality/components/portfolio-money-and-accounting.md` (Kelly fraction collision finding cross-references here).

## 0. TL;DR — the user's journey, in 4 steps

1. **Navigate to `/instellingen`**: from the top navigation. Page mounts, `apiClient.getTradingSettings()` fires → `GET /settings/trading` → server reads `trading_settings` row (or falls back to `domain_defaults` if storage is off / no row exists yet) → response contains full `allowed_universe` + `user_strategy` JSON.
2. **See the form**: a single `<section>` titled "Actie-instellingen" with one labelled input — "Cashbuffer (EUR)" — pre-populated from `data.user_strategy.user_buffer_eur` or `"0"` if absent. Below the input: explanatory Dutch paragraph: "De cashbuffer wordt afgetrokken van je beschikbare cash voordat de voorgestelde aankoophoeveelheid wordt berekend. Standaard €0." A blue "Opslaan" button.
3. **Type a number + click Opslaan**: client-side validates `Number(buffer) >= 0` (rejects negative or NaN); on pass, `apiClient.updateTradingSettings({...})` fires `PUT /settings/trading` with the **full** `allowed_universe` + `user_strategy` (with the new `user_buffer_eur`) + a **hard-coded** `reason_nl="Cashbuffer voor actiedrafts aangepast."`.
4. **See success**: server upserts the `trading_settings` row (`settings_id="default"`, `updated_at=now()`, `source="api"`, `status="active"`, `explanation_nl=reason_nl`). Response triggers `await refresh()` → page re-fetches → green "Instellingen opgeslagen." message appears next to the button.

**Total user-visible time**: ~3 seconds. **What the user accomplished**: changed the cashbuffer. **What the user could NOT change via the UI**: 10 other fields including portfolio goal, risk level, sector preferences, position caps, cash reserve %, currency preference. They remain at whatever value was previously persisted (or domain defaults if never persisted).

## 1. The page — `/instellingen`

**File**: `apps/web/app/instellingen/page.tsx:1-171` (171 LOC).

### 1.1 The page docstring acknowledges the scope (`:3-13`)

> "Task 133: Instellingen page. Surfaces the persisted trading settings (allowed universe + user strategy). **For Task 133 the only editable field added here is `user_buffer_eur`** — the EUR headroom subtracted from `available_funds` when sizing BUY drafts. Other fields (portfolio goal, risk level, sector preferences) live in the same JSON column and can be wired through later UI work; the page currently shows the buffer **+ a read-only summary of the other user-strategy settings**."

The docstring is intellectually honest about Task 133's scope limitation. But the closing claim — "a read-only summary of the other user-strategy settings" — is **NOT actually rendered**. The page renders the Cashbuffer section and nothing else. The other fields are present in the response data (`data.user_strategy.portfolio_goal`, `data.user_strategy.risk_level`, etc.) but the component never displays them. §9.1.

### 1.2 The only editable input (`:103-119`)

```tsx
<label
  style={{ display: "grid", gap: 4, maxWidth: 320 }}
  htmlFor="user-buffer-eur-input"
>
  <span style={{ fontWeight: 600, fontSize: 13 }}>
    Cashbuffer (EUR)
  </span>
  <input
    id="user-buffer-eur-input"
    data-testid="instellingen-user-buffer-input"
    type="number"
    min="0"
    step="1"
    value={buffer}
    onChange={(event) => setBuffer(event.target.value)}
  />
</label>
```

- `type="number"` with `min="0"` and `step="1"` — browser-native validation for non-negative integers.
- `value={buffer}` is a `string`, not a number — the `setBuffer(event.target.value)` keeps it as a string, allowing the user to type intermediate values like `"5."` without React truncating.
- The conversion to `Decimal` happens server-side via Pydantic (`domain/settings.py:177-182`).

### 1.3 The save button + states (`:120-150`)

```tsx
<button
  type="button"
  data-testid="instellingen-save-button"
  onClick={handleSave}
  disabled={saving}
  ...
>
  {saving ? "Bezig…" : "Opslaan"}
</button>
{savedMessage ? (
  <span style={{ color: "#15803d", fontSize: 13 }}>
    {savedMessage}  // "Instellingen opgeslagen."
  </span>
) : null}
```

Three success states displayed in series after the save click:
1. Button label "Bezig…" (during the async call).
2. Button re-enables + green inline "Instellingen opgeslagen." message renders.
3. (Implicit) The page state is re-fetched via `await refresh()` so any server-side normalisation surfaces.

There is no "discard changes" or "revert" button. The user's only path back to the previous value is to re-type it.

## 2. The handler — `handleSave` (`:52-78`)

```tsx
async function handleSave() {
  if (data === null) return;
  const numeric = Number(buffer);
  if (Number.isNaN(numeric) || numeric < 0) {
    setError("Cashbuffer moet ≥ 0 zijn.");
    return;
  }
  setSaving(true);
  setError(null);
  setSavedMessage(null);
  const next_user_strategy = {
    ...(data.user_strategy as Record<string, unknown>),
    user_buffer_eur: buffer,
  };
  const result = await apiClient.updateTradingSettings({
    allowed_universe: data.allowed_universe,
    user_strategy: next_user_strategy,
    reason_nl: "Cashbuffer voor actiedrafts aangepast.",
  });
  setSaving(false);
  if (!result.ok) {
    setError("Opslaan mislukt. Controleer of de API beschikbaar is.");
    return;
  }
  setSavedMessage("Instellingen opgeslagen.");
  await refresh();
}
```

Three architectural facts visible in 27 LOC:

### 2.1 The read-modify-write pattern (`:62-65`)

```tsx
const next_user_strategy = {
  ...(data.user_strategy as Record<string, unknown>),
  user_buffer_eur: buffer,
};
```

The client spreads the entire `data.user_strategy` from the last fetch + overrides `user_buffer_eur` with the new value. Then sends the FULL object back via PUT.

**Implication**: if another user (or another browser tab) changed `risk_level` between this user's page load and this user's Opslaan click, the second user's PUT would silently overwrite that change with the stale `risk_level` from the first fetch. Last-writer-wins; no version stamp; no optimistic concurrency check. §9.3.

### 2.2 The hard-coded `reason_nl` (`:69`)

```tsx
reason_nl: "Cashbuffer voor actiedrafts aangepast."
```

**Always the same string, regardless of what changed.** If a future UI exposes more fields and the user edits, say, `risk_level`, the audit reason will still claim "cashbuffer was adjusted". The user is not asked WHY they made the change.

Intent §4 of `docs/intent/reconciliation.md` mandates "Thresholds changes are audit-logged with `{user, pass, field, from, to, changed_at}`". `docs/intent/ai-usage.md` §4 mandates the budget extension is "audit-logged with the user's reason (free-text note)". The same audit-logged-reason principle applies here — but the implementation is just a hard-coded constant. §9.4.

### 2.3 Client-side validation is `numeric < 0` only (`:55-58`)

```tsx
const numeric = Number(buffer);
if (Number.isNaN(numeric) || numeric < 0) {
  setError("Cashbuffer moet ≥ 0 zijn.");
  return;
}
```

Two failure modes caught:
- `Number(buffer)` is NaN (e.g., user typed letters).
- `numeric < 0` (negative).

What's NOT validated client-side:
- Absurdly large values (e.g., €100,000,000) — would pass validation and be sent to server.
- Decimal precision beyond what Decimal can represent.
- Whether `numeric` is consistent with cash actually available (which the UI doesn't know).

Server-side, Pydantic enforces the same `>= 0` check at `domain/settings.py:177-182`. The `reject_float` validator at `:161-168` rejects float values (forcing Decimal), but the client sends a string (`user_buffer_eur: buffer` where buffer is a string), which Pydantic parses as Decimal — so this validator doesn't fire on the user path.

## 3. The 11-field domain model vs the 1-field UI

`packages/domain/src/portfolio_outlook_domain/settings.py:142-159` defines `UserStrategySettings`:

```python
class UserStrategySettings(DomainBaseModel):
    portfolio_goal: PortfolioGoal = PortfolioGoal.BALANCED_GROWTH_RISK
    risk_level: StrategyRiskLevel = StrategyRiskLevel.MEDIUM
    asset_mix_preference: AssetMixPreference = AssetMixPreference.ETF_AND_STOCK_MIX
    preferred_regions: tuple[RegionPreference, ...] = (RegionPreference.GLOBAL,)
    preferred_sectors: tuple[SectorPreference, ...] = ()
    avoided_sectors: tuple[SectorPreference, ...] = ()
    max_position_pct: Decimal = Decimal("10")
    min_cash_reserve_pct: Decimal = Decimal("5")
    currency_preference: CurrencyPreference = CurrencyPreference.EUR_PREFERRED_USD_ALLOWED
    prefer_simple_belgian_tax_admin: bool = True
    user_buffer_eur: Decimal = Decimal("0")  # ← THE ONE field the UI exposes
    explanation_nl: str = (
        "Dit is je voorkeurlaag voor ranking en fit, niet voor harde blokkeringen."
    )
```

11 user-strategy fields + 1 `explanation_nl` metadata field. The UI exposes 1.

Plus `AllowedUniverseSettings` at `:130-139`:

```python
class AllowedUniverseSettings(DomainBaseModel):
    allow_etfs: bool = True
    allow_stocks: bool = True
    allow_currencies_watch_only: bool = False
    allow_bond_etfs: bool = False
    allow_commodity_etfs: bool = False
    blocked_asset_types: tuple[BlockedAssetType, ...] = (...)
    explanation_nl: str = "Dit is de harde veiligheidsfilter voor toegestane beleggingen."
```

6 allowed-universe toggles. The UI exposes 0 of them.

**Total**: 17 settings fields in the domain; 1 in the UI. The user cannot:
- Change their portfolio goal or risk level.
- Adjust position-size caps (`max_position_pct=10%`).
- Adjust cash reserve floor (`min_cash_reserve_pct=5%`).
- Add or remove preferred / avoided sectors.
- Toggle which asset types the universe allows.
- Express currency preference.

All these are locked at domain defaults unless an out-of-band SQL UPDATE writes them. §9.2.

## 4. The PUT route — `update_trading_settings`

**File**: `apps/api/src/portfolio_outlook_api/trading_settings.py:134-197`.

### 4.1 The 3 short-circuits before the write (`:145-160`)

```python
if not storage_settings.enabled:
    return {... "updated": False ...}

database_url = storage_settings.database_url
if database_url is None or database_url.strip() == "":
    return {... "updated": False ...}
```

If storage is disabled or no database URL is configured, the route returns a 200 response with `"updated": False`. **No HTTP error is raised**; the client interprets this as success unless it inspects the `updated` field. The Instellingen page does NOT inspect `updated` — it only checks `result.ok` (which is true for 200). The user would see "Instellingen opgeslagen." but nothing was actually saved. §9.5.

### 4.2 The save call (`:164-175`)

```python
with provider.checked_connection(require_writable=True) as checked:
    repository = repository_factory(checked.connection, checked.readiness)
    request = SaveTradingSettingsRequest(
        settings_id="default",
        updated_at=datetime.now(UTC),
        allowed_universe=payload.allowed_universe.model_dump(mode="json"),
        user_strategy=payload.user_strategy.model_dump(mode="json"),
        source="api",
        status="active",
        explanation_nl=payload.reason_nl or "Instellingen aangepast door gebruiker.",
    )
    repository.save_settings(request)
```

- `settings_id="default"` — hard-coded; **the system supports only ONE settings row**. No per-user, no per-account settings. §9.6.
- `source="api"` — distinguishes from CLI-driven or scheduled-job saves.
- `status="active"` — written as-is; the storage layer's status enum supports `"active" / "deprecated" / "draft"` but the API route always writes `active`.
- `explanation_nl=payload.reason_nl or "Instellingen aangepast door gebruiker."` — if the client omits `reason_nl`, the server falls back to the generic Dutch string. The Instellingen page always sends the hard-coded "Cashbuffer voor actiedrafts aangepast." so the server fallback never fires from this path.

### 4.3 The 3 failure paths

| Exception | Response | Note |
|-----------|----------|------|
| `StoragePersistenceBlockedError` | 200 with `"updated": False`, `status_nl="Geblokkeerd"` | writes blocked at storage layer |
| `StorageConnectionError` | 200 with `"updated": False`, `status_nl="Niet opgeslagen"` | network / connection error |
| Pydantic validation error on input | 422 HTTP from FastAPI machinery | catches negative buffer, invalid enum values, etc. |

The 200-with-updated-False pattern is unusual — most APIs would return 5xx for storage errors. The route's intent is "graceful degradation" but the client doesn't surface the degradation correctly. §9.5.

## 5. The audit row — single mutating column, no history

The `trading_settings` table is **upsert-only** on `settings_id="default"` — every save overwrites the previous row in place. There is no `trading_settings_audit` table that captures history.

The `explanation_nl` column carries only the MOST RECENT reason. A reader of the table cannot see what was changed in the previous edit, who made it, when prior changes occurred, or whether the same field was edited multiple times. The only forensic data is the current `updated_at` and the current `explanation_nl`.

This violates intent §4 / AGENTS.md "Every decision must be logged" — for trading settings, only the LAST decision is captured. The history of past decisions is lost on each upsert. §9.7.

T-061 §3 already documented this for the broader settings infrastructure; T-029 surfaces it from the user-action angle.

## 6. Re-read after save (`:77`)

```tsx
setSavedMessage("Instellingen opgeslagen.");
await refresh();
```

After a successful save, the page re-fetches the trading settings. The re-fetch:
1. Re-renders the buffer input with the server-confirmed value.
2. Silently normalises any client-side oddities (e.g., if the user typed `"5.50"`, the server normalises to `Decimal("5.50")` and the input may now show `"5.5"` depending on the serialisation).
3. Replaces the in-memory `data.user_strategy` with the server's full object — closing the read-modify-write race window for THIS user (other users / tabs are still stale).

The refresh strategy is the same fail-closed pattern documented in T-025 / T-027 / T-028: every state-changing UI update waits for server confirmation. Acceptable for a low-frequency edit; same "system feels slower than it should" pattern documented across the user-action surfaces.

## 7. Failure paths from the user's seat

1. **Typed letters** — Client validation catches NaN. Inline red "Cashbuffer moet ≥ 0 zijn." error. No retry indicator; user must clear and re-type.
2. **Typed negative number** — same client validation; same error message.
3. **Network call fails (5xx, timeout)** — `result.ok === false`. Generic "Opslaan mislukt. Controleer of de API beschikbaar is." error appears. No retry button.
4. **Storage was off when save fired** — server returns 200 with `"updated": False`. **Client interprets as success** (per §4.1). User sees "Instellingen opgeslagen." but nothing was saved. The next page load (or refresh) would show the un-saved value, signalling the failure — but only if the user notices the discrepancy.
5. **Concurrent edit by another tab / user** — last-writer-wins. User's save silently overwrites the other party's recent change. No conflict surface. §9.3.
6. **Tried to save a setting other than buffer** — impossible from this UI; would require curl or a future UI.

## 8. The Category split (T-061 cross-reference)

T-061 §2 documented the 5-category settings split (per intent across multiple intent docs):

| Category | Description | UI surface |
|----------|-------------|------------|
| **1** | API keys + per-provider budgets | Partial — keys live in `.env`; cap visible in `claude_ai_budget_monthly_eur` but no UI to change it (T-023 §10.5) |
| **2** | Portfolio / trading settings (the 17 fields in `AllowedUniverseSettings` + `UserStrategySettings`) | **T-029 scope** — 1 of 17 fields exposed |
| **3** | Reconciliation thresholds (B/C/D/E tiers per intent) + speculative classification thresholds | **None** — T-020 §10.3 documented these are absent from settings infrastructure entirely |
| **4** | Notification preferences | **None** — no email/push/webhook config surface |
| **5** | On-demand triggers (manual sync, manual reconciliation, manual backtest, etc.) | **Scattered** — `POST /ibkr/sync/run` exists (T-013); `POST /predictor/backtest/run` exists (T-024 §3.1, gated off); `POST /watchlist/confirm` exists (T-025); no central "trigger" surface |

T-029's user-edit Instellingen page = Category 2 partial only. **Of the 5 user-facing categories in the intent specification, 1 is fully absent (4), 2 are mostly absent (1, 3), 1 is scattered (5), and 1 is partially implemented (2 — exactly 1 of 17 fields).**

This is the most cumulative "intent-vs-reality settings surface gap" finding in the audit.

## 9. Phase 1c surface (10 findings on the user-action surface)

1. **The "read-only summary of other settings" promised by the page docstring is not rendered** (§1.1) — `instellingen/page.tsx:6-13` claims it; the page body shows only the buffer section.
2. **10 of 11 user-strategy fields invisible** (§3) — `portfolio_goal`, `risk_level`, `asset_mix_preference`, `preferred_regions`, `preferred_sectors`, `avoided_sectors`, `max_position_pct`, `min_cash_reserve_pct`, `currency_preference`, `prefer_simple_belgian_tax_admin` are all locked at defaults unless out-of-band SQL changes them. Plus all 6 `allowed_universe` toggles also invisible.
3. **No optimistic concurrency control** (§2.1) — read-modify-write with last-writer-wins. Two tabs editing simultaneously can silently overwrite each other.
4. **`reason_nl` is hard-coded** (§2.2) — always "Cashbuffer voor actiedrafts aangepast." regardless of what changed. Intent's "audit-logged with the user's reason" principle compromised.
5. **200-with-`updated=False` swallows storage failure** (§4.1 / §7.4) — when storage is off, the route returns 200 + `"updated": False`. Client only checks `result.ok` so "Instellingen opgeslagen." renders despite no write. Silent data loss.
6. **Single global settings row** (§4.2) — `settings_id="default"` hard-coded. No per-user, no per-account settings. Multi-user accounts cannot have different preferences.
7. **No `trading_settings_audit` history table** (§5) — only the most recent edit's `explanation_nl` is captured. Prior reasons are lost on each upsert.
8. **Category 1, 3, 4, 5 all absent or partial** (§8) — of the 5 intent categories, only Category 2 has a UI, and it's 1-of-17. Reconciliation thresholds, AI budget caps, notification preferences, on-demand triggers all need out-of-band changes or scattered routes.
9. **No "revert" or "discard changes" button** (§1.3) — if the user types a value but doesn't want to save it, they must manually re-type the previous value or reload the page.
10. **Server-side `reject_float` validator never fires from this path** (§2.3) — the client sends `user_buffer_eur` as a string, which Pydantic parses to Decimal directly. The validator catches floats only if a future client sends a JSON float; the current Instellingen page never does.

## 10. Out of scope (re-confirmed)

- **Credentials infrastructure** (T-061 — merged sibling; Category 1 API keys + budgets).
- **Settings ingest mechanism** (T-061 §2 — `.env` flow through Pydantic).
- **Reconciliation thresholds** (T-020 §10.3 — Category 3 absent; cross-referenced).
- **AI provider budget cap settings UI** (T-023 — Category 1; cross-referenced).
- **Speculative classification thresholds** (T-022 §10.7 — Category 3; cross-referenced).
- **Kelly fraction 0.5-vs-0.25 collision** (T-002 + T-061 — recorded; not user-editable from this UI).

## 11. References

- `apps/web/app/instellingen/page.tsx:1-171` (the entire Instellingen page)
- `apps/web/app/instellingen/page.tsx:3-13` (docstring acknowledging Task 133 scope)
- `apps/web/app/instellingen/page.tsx:52-78` (`handleSave` — read-modify-write + hard-coded reason)
- `apps/web/app/instellingen/page.tsx:103-119` (the single input field)
- `apps/web/lib/apiClient.ts` (`getTradingSettings` / `updateTradingSettings` TS bindings)
- `apps/api/src/portfolio_outlook_api/status_routes.py:244` (`GET /settings/trading`)
- `apps/api/src/portfolio_outlook_api/status_routes.py:410-412` (`PUT /settings/trading`)
- `apps/api/src/portfolio_outlook_api/trading_settings.py:134-197` (`update_trading_settings_response`)
- `packages/domain/src/portfolio_outlook_domain/settings.py:130-139` (`AllowedUniverseSettings` — 6 fields)
- `packages/domain/src/portfolio_outlook_domain/settings.py:142-159` (`UserStrategySettings` — 11 fields)
- `packages/domain/src/portfolio_outlook_domain/settings.py:161-182` (validators)
- `docs/reality/components/settings-and-credentials-infrastructure.md` (T-061 — 5-category split)
- `docs/reality/components/api-infrastructure-and-ai.md` (T-006 — settings API surface)
- `docs/reality/workflows/ai-explanation-and-budget.md` (T-023 — Category 1 partial)
- `docs/reality/workflows/ibkr-reconciliation-passes-a-b-c.md` (T-020 §10.3 — Category 3 absent)
- `docs/reality/workflows/belgian-tax-computation.md` (T-022 §10.7 — speculative thresholds absent)
- `docs/reality/workflows/user-confirm-starter-watchlist.md` (T-025), `user-approve-action-draft.md` (T-026), `user-cancel-submitted-order.md` (T-027), `user-acknowledge-manual-review.md` (T-028) — sibling user-action workflow docs
