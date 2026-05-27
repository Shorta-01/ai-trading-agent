# Belgian Tax Computation — TOB + Withholding + the Missing Annual Report

**Scope.** End-to-end trace of what the system computes + records for Belgian tax purposes — from the locked `belgian_tax.py` math primitives (TOB per-transaction + dividend withholding) through their single production call site (`compute_orderimpact` in `action_draft_safety.py`) to persistence on action drafts (migration `0035`) and Dutch-rendered display (`/portefeuille` page). The doc also documents what is **NOT** shipped: the 8-section annual report, speculative-classification tracking, Reynders bond-component recording, year-end snapshot, foreign-source income summary, and the `fx_rate_at_fill` column needed for realised-gain-in-EUR computation.

**Intent**: `docs/intent/belgian-tax.md` (locked 2026-05-26). **Decision**: `docs/decisions/0012-belgian-tax-architecture.md`. **Component reality**: T-002 `docs/reality/components/portfolio-money-and-accounting.md`, T-005 `docs/reality/components/api-actions-suggestions-and-watchlists.md`, T-007 `docs/reality/components/worker-actions-and-reconciliation.md`. **Sibling workflow**: T-021 `docs/reality/workflows/portfolio-valuation-and-cost-basis.md` (which §10.8 already flagged the missing `fx_rate_at_fill` on `ibkr_executions`).

## 0. TL;DR

| Item | Intent (locked) | Reality | Status |
|------|-----------------|---------|--------|
| TOB per-transaction compute | required | `belgian_tax.py:91-116` | **Shipped** |
| Dividend withholding compute | required | `belgian_tax.py:119-132` | **Shipped (no callers)** |
| TOB persisted on action draft | required | migration `0035` + `metadata.py:1569-1570` | **Shipped** |
| TOB security class persisted | required | `belgian_tob_security_class` column | **Shipped (default `STANDARD_STOCK` only)** |
| TOB displayed in UI | required | `/portefeuille/page.tsx:517, :541` (Dutch tooltip) | **Shipped** |
| TOB-net expected return filter (intent §4) | required | not implemented — TOB computed but not subtracted from `ensemble_expected_return_pct` | **Phase 1c gap** |
| Speculative classification tracker (intent §4) | required | not implemented | **Phase 1c gap** |
| Realised gain/loss per disposal in EUR (intent §1) | compute | not implemented — no `fx_rate_at_fill` on `ibkr_executions` | **Phase 1c gap** |
| Annual report PDF + 8 CSVs (intent §3) | required | not implemented — no PDF library in deps, no `/tax/report` route | **Phase 1c gap** |
| Reynders bond-component recording (intent §1) | record | not implemented | **Phase 1c gap** |
| Year-end position snapshot (intent §3 §6) | record | not implemented | **Phase 1c gap** |
| Foreign-source income summary (intent §3 §7) | record | not implemented | **Phase 1c gap** |
| Annual securities account tax (€1M threshold) (intent §1) | record | not implemented | **Phase 1c gap** |
| Tax rate versioning (intent §7) | open | hard-coded in `belgian_tax.py:52-59` | **Phase 1c gap** |

**Net summary**: the math primitives are rigorously locked and unit-tested, but **only one of the intent §1 "compute" items and zero of the intent §1 "record" items are wired into a production data path**.

## 1. The compute primitives (`belgian_tax.py:1-148`)

The single 148-LOC module `packages/portfolio/src/portfolio_outlook_portfolio/belgian_tax.py` is the **only** Belgian-tax math home. Pure-function, Decimal-only, no I/O, no `datetime.now()`, no config dependencies (module docstring `:14-16`).

### 1.1 `TobSecurityClass` — 6 locked classes (`belgian_tax.py:31-43`)

```python
class TobSecurityClass(StrEnum):
    STANDARD_STOCK = "standard_stock"          # listed equity → 0.35%
    DISTRIBUTING_ETF = "distributing_etf"      # distributing fund/ETF → 0.35%
    ACCUMULATING_ETF = "accumulating_etf"      # accumulating fund/ETF → 1.32%
    BOND = "bond"                              # listed bond → 0.12%
    SICAV_REDEMPTION = "sicav_redemption"      # SICAV redemption → 1.32%
    OTHER = "other"                            # conservative default → 0.35%
```

The 6 enum values map to **3 distinct rate-cap pairs**. The string values are stored on the action-draft row so the audit chain can prove which rate was applied (docstring `:33-36`).

### 1.2 Locked rates + caps (`belgian_tax.py:52-59`)

| Class group | Rate | Cap |
|-------------|------|-----|
| `BOND` | `TOB_RATE_BOND = 0.0012` (0.12%) | `TOB_CAP_BOND = €1300` |
| `STANDARD_STOCK / DISTRIBUTING_ETF / OTHER` | `TOB_RATE_STANDARD = 0.0035` (0.35%) | `TOB_CAP_STANDARD = €1600` |
| `ACCUMULATING_ETF / SICAV_REDEMPTION` | `TOB_RATE_ACCUMULATING = 0.0132` (1.32%) | `TOB_CAP_ACCUMULATING = €4000` |

Plus the withholding rate at `:61`:
```python
BELGIAN_DIVIDEND_WITHHOLDING_RATE = Decimal("0.30")
```

The module docstring (`:7`) labels these "Locked rates and caps (as of 2025)". The rates are module-level `Decimal` constants; **there is no rate-version table, no migration carrying versions, no config layer** (§9.5).

### 1.3 `compute_tob(...)` (`belgian_tax.py:91-116`)

```python
def compute_tob(
    *,
    transaction_value: Decimal,
    security_class: TobSecurityClass,
) -> Decimal:
    if not isinstance(transaction_value, Decimal):
        raise TypeError("transaction_value must be a Decimal")
    if transaction_value < 0:
        raise ValueError("transaction_value must not be negative")
    if transaction_value == 0:
        return Decimal("0.00")
    info = _RATE_TABLE[security_class]
    raw = transaction_value * info.rate
    return _round_eur_cents(min(raw, info.cap))
```

Three guards (`:108-113`): TypeError on non-`Decimal`, ValueError on negative, short-circuit to `Decimal("0.00")` on exactly zero. The cap is applied via `min(raw, info.cap)` (`:116`) and the result is rounded HALF_UP to cents.

### 1.4 `_round_eur_cents` (`belgian_tax.py:76-82`)

```python
_TWO_DECIMALS = Decimal("0.01")

def _round_eur_cents(value: Decimal) -> Decimal:
    return value.quantize(_TWO_DECIMALS, rounding=ROUND_HALF_UP)
```

HALF_UP is "the convention IBKR + brokers use" (`:80`). The doctrine boundary holds: no float conversion, no `Decimal(0.0035)` traps — every constant is constructed via `Decimal("0.0035")`.

### 1.5 `compute_dividend_withholding(...)` (`belgian_tax.py:119-132`)

```python
def compute_dividend_withholding(*, gross_dividend: Decimal) -> Decimal:
    """Return the Belgian roerende voorheffing on a gross dividend payment.

    Rate is locked at 30%."""
    if not isinstance(gross_dividend, Decimal):
        raise TypeError("gross_dividend must be a Decimal")
    if gross_dividend < 0:
        raise ValueError("gross_dividend must not be negative")
    if gross_dividend == 0:
        return Decimal("0.00")
    return _round_eur_cents(gross_dividend * BELGIAN_DIVIDEND_WITHHOLDING_RATE)
```

Same shape as `compute_tob` but no cap (withholding has no per-event maximum).

## 2. The single production call site — `compute_orderimpact`

### 2.1 The chain (`action_draft_safety.py:388-455`)

`compute_orderimpact(context, sizing, *, belgian_tob_security_class=TobSecurityClass.STANDARD_STOCK)` (`packages/portfolio/src/portfolio_outlook_portfolio/action_draft_safety.py:388-455`) is the **only** production caller of `compute_tob`. The TOB compute is at `:438-441`:

```python
belgian_tob = compute_tob(
    transaction_value=order_value,
    security_class=belgian_tob_security_class,
)
```

`order_value = quantity * limit_price` (`:404`). The result lands on the `Orderimpact` dataclass (`:443-455`) alongside cash before/after, position before/after, weight, concentration:

```python
return Orderimpact(
    estimated_order_value=order_value,
    estimated_cash_before=cash_before,
    estimated_cash_after=cash_after,
    estimated_position_quantity_before=pos_before,
    estimated_position_quantity_after=pos_after,
    estimated_position_value_after=pos_value_after,
    estimated_portfolio_weight_after_pct=weight_after,
    estimated_concentration_impact_pct=concentration,
    base_currency=context.base_currency,
    estimated_belgian_tob=belgian_tob,
    belgian_tob_security_class=belgian_tob_security_class.value,
)
```

### 2.2 The `STANDARD_STOCK` default — no classifier

The parameter default at `:392` is `TobSecurityClass.STANDARD_STOCK`. The docstring (`:396-399`) is explicit:

> "V1 default is `STANDARD_STOCK` (0.35%) because the action-draft scope is locked to listed shares."

**There is no production classifier.** Grep across the codebase for sites that override the default with anything other than `STANDARD_STOCK` returns zero matches outside tests. Consequence: an accumulating-ETF or bond traded through this path would have its TOB silently computed at the wrong rate. §9.2.

### 2.3 The single API route that wires this in — `action_draft_sync.py`

`apps/api/src/portfolio_outlook_api/action_draft_sync.py:203`:

```python
impact = compute_orderimpact(context, sizing)
```

No `belgian_tob_security_class` kwarg — i.e., always defaults to `STANDARD_STOCK`. The result is persisted at `:238-239`:

```python
estimated_belgian_tob=impact.estimated_belgian_tob,
belgian_tob_security_class=impact.belgian_tob_security_class,
```

And serialised back to the client at `:342-343`:

```python
"estimated_belgian_tob": _decimal_or_none_str(record.estimated_belgian_tob),
"belgian_tob_security_class": record.belgian_tob_security_class,
```

### 2.4 The worker composer does NOT compute TOB

Grep across `apps/worker/src/portfolio_outlook_worker/` for `compute_orderimpact`, `compute_tob`, `TobSecurityClass`, `belgian_tob`, `estimated_belgian_tob` returns **zero hits**. The worker's `compose_action_draft_from_decision_package` (`apps/worker/src/portfolio_outlook_worker/action_draft/composer.py:91`) and `compose_action_draft_user_supplied` (`:269`) — both documented in T-018 — produce action-draft records but **do not populate `estimated_belgian_tob` or `belgian_tob_security_class`**.

**Asymmetry**: a draft created via the API `action_draft_sync.py` route gets TOB; a draft composed by the worker from a Decision Package does NOT. Both write to the same `asset_action_drafts` table; the TOB columns are nullable so the worker-composed rows simply leave them `NULL`. §9.1.

## 3. Persistence — migration `0035` + storage columns

### 3.1 Migration `0035_action_draft_belgian_tob.py` (`packages/storage/alembic/versions/0035_action_draft_belgian_tob.py:17-25`)

```python
def upgrade() -> None:
    op.add_column(
        "asset_action_drafts",
        sa.Column("estimated_belgian_tob", sa.Numeric(20, 6), nullable=True),
    )
    op.add_column(
        "asset_action_drafts",
        sa.Column("belgian_tob_security_class", sa.Text(), nullable=True),
    )
```

Two columns: a `Numeric(20, 6)` for the TOB amount (EUR) and a `Text` for the security class enum string. Both nullable — legacy drafts before this migration carry NULLs; worker-composed drafts carry NULLs. Revision ID: `0035_action_draft_belgian_tob`; created 2026-05-30; downstream of `0034_decision_package_explanations`.

### 3.2 Metadata + repository contract

`packages/storage/src/ai_trading_agent_storage/metadata.py:1569-1570`:
```python
Column("estimated_belgian_tob", MONEY_NUMERIC, nullable=True),
Column("belgian_tob_security_class", Text, nullable=True),
```

`MONEY_NUMERIC = Numeric(20, 6)` — matches the migration.

`packages/storage/src/ai_trading_agent_storage/repository_contracts.py:2202-2203`:
```python
estimated_belgian_tob: Decimal | None = None
belgian_tob_security_class: str | None = None
```

Plus validation at `:2265-2266`:
```python
if self.estimated_belgian_tob is not None and self.estimated_belgian_tob < 0:
    raise ValueError("estimated_belgian_tob must not be negative.")
```

The documentation comment at `repository_contracts.py:2199-2200` is explicit:

> "Belgian tax preview (Slice 11). Informational on the draft; **the TOB does not change order sizing**."

This is the doctrinal floor that contradicts intent §4 ("TOB-aware suggestions. Expected return computed net of expected TOB. A trade with a negative net expected return after TOB is not suggested"). §9.3.

### 3.3 The migration_readiness Dutch note

`migration_readiness.py:361-362` carries a Dutch help string referencing the columns:
> "estimated_belgian_tob (geschatte beurstaks in EUR-cent) en belgian_tob_security_class (welke TOB-tariefklasse gebruikt is)."

(Translation: "estimated_belgian_tob (estimated stock-exchange-tax in EUR-cents) and belgian_tob_security_class (which TOB tariff class was used)."). Used by the readiness gate to confirm the migration has been applied before letting the API start serving drafts.

## 4. Display — Dutch UI rendering

### 4.1 API client type (`apps/web/lib/apiClient.ts:1299-1300`)

```typescript
estimated_belgian_tob: string | null;
belgian_tob_security_class: string | null;
```

Decimal-as-string per the doctrine boundary documented in T-008.

### 4.2 Portfolio page rendering (`apps/web/app/portefeuille/page.tsx:517, :541`)

Header at `:517`:
```tsx
<th>TOB (BE)</th>
```

Cell at `:541`:
```tsx
<td title={draft.belgian_tob_security_class
    ? `Beurstaks tarief: ${draft.belgian_tob_security_class}`
    : "Geen TOB beschikbaar"}>
  {displayValue(draft.estimated_belgian_tob)}
</td>
```

The tariff class is surfaced via `title` attribute (tooltip) on the cell. When the draft has no TOB (worker-composed; §2.4), the tooltip reads "Geen TOB beschikbaar" — the only place the asymmetry leaks to the user.

The render is per-draft only; there is **no aggregate "Total TOB this year" surface anywhere in the frontend** (intent §1 compute item #2 "Total TOB for the year" — §9.4).

## 5. `compute_dividend_withholding` — locked but unused

The function is fully implemented and exported at `belgian_tax.py:147` + re-exported from `portfolio_outlook_portfolio/__init__.py:132`. **There are zero production callers** — grep across the codebase outside tests returns zero matches.

The absence cascades:
- **No `dividend_events` / `dividend_payments` table** exists (`metadata.py` search returns only `dividend_yield_pct` in research/fundamentals tables, not a dividend-event ingest table).
- **No dividend ingestion path** — the IBKR adapter (T-004) does not subscribe to `dividend` events; the worker (T-007) does not ingest them.
- **The withholding compute is a stranded primitive** waiting for a consumer that does not exist. §9.6.

## 6. The intent §1 compute/record split — reality coverage

Intent §1 lists 5 compute items + 4 record items. Status today:

### 6.1 Compute (intent §1)

| Compute item | Reality | Status |
|--------------|---------|--------|
| TOB per transaction | `compute_tob` at `belgian_tax.py:91` | **Shipped (with default-class limitation §2.2)** |
| Total TOB for the year | not implemented (no aggregation query, no UI surface) | **Gap §9.4** |
| Withholding tax per dividend | `compute_dividend_withholding` at `belgian_tax.py:119` (no callers) | **Stranded §5** |
| Total withholding for the year | not implemented | **Gap §9.4** |
| Per-disposal realised gain/loss in EUR | not implemented — `ibkr_executions` has no `fx_rate_at_fill` (§7.1) | **Gap §9.7** |

### 6.2 Record (intent §1)

| Record item | Reality | Status |
|-------------|---------|--------|
| Reynders bond-component data per disposal | not implemented (no `reynders` / `bond_component` / `bond_share` columns anywhere) | **Gap §9.8** |
| Capital gains classification context (trade count, turnover, holding period) | not implemented | **Gap §9.9** |
| Foreign withholding reclaim eligibility data (treaty rate vs withheld) | not implemented | **Gap §9.10** |
| Annual securities account tax data (€1M threshold) | not implemented | **Gap §9.11** |

**Score: 1 of 5 compute items + 0 of 4 record items shipped.**

## 7. The realised-gain-in-EUR blocker — `fx_rate_at_fill` absent

### 7.1 `ibkr_executions` schema (`metadata.py:2772-2813`)

```python
ibkr_executions = Table(
    "ibkr_executions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ibkr_exec_id", Text, nullable=False, unique=True),
    Column("ibkr_perm_id", BigInteger, nullable=False),
    Column("action_draft_id", Text, ForeignKey("action_drafts.action_draft_id"), nullable=False),
    Column("account_id", Text, nullable=False),
    Column("conid", Text, nullable=False),
    Column("side", Text, nullable=False),
    Column("fill_price_local", Numeric(precision=20, scale=8), nullable=False),
    Column("fill_quantity", Numeric(precision=20, scale=8), nullable=False),
    Column("fill_time", DateTime(timezone=True), nullable=False),
    Column("commission", Numeric(precision=20, scale=8), nullable=False),
    Column("commission_currency", Text, nullable=False),
    Column("exchange", Text, nullable=False),
    ...
)
```

**No `fx_rate_at_fill` column. No `eur_value_at_fill` column.** Disposal price is recorded in local currency only. The latest FX snapshot is available (T-021 §5) but reflects "now", not "fill time".

Intent §4 valuation-by-purpose row "Belgian tax disposal events" mandates **"Actual execution price × Actual execution-time FX rate"**. Without `fx_rate_at_fill`, the per-disposal realised gain in EUR **cannot be computed correctly** — the system would have to retroactively fetch a historical FX rate (which IBKR does not preserve in a stable way for the worker) or use the current FX rate (which violates intent).

T-021 §10.8 originated this finding; T-022 re-confirms it as the foundational blocker for intent §1 compute item #5.

## 8. The annual-report blocker — zero infrastructure

Intent §3 mandates a Dutch PDF report with 7 sections + 1 CSV section pack:

1. Transactions and TOB
2. Dividends and withholding
3. Realised gains/losses
4. Capital gains classification risk indicator
5. Reynders disposals
6. Year-end position and currency exposure
7. Foreign-source income summary
8. Supporting CSV exports

**The system has none of the inputs for sections 2-7 and no PDF generation infrastructure.**

### 8.1 No PDF library

Grep `pyproject.toml` for `reportlab`, `weasyprint`, `xhtml2pdf`, `fpdf` returns zero matches. There is no PDF generation dependency on the dependency tree.

### 8.2 No tax-report route

Grep `apps/api/src/portfolio_outlook_api/` for `@router.get("/tax/`, `@router.get("/annual/`, `@router.get("/reports/tax`, `@router.get("/reports/annual`, `tax_report`, `annual_report` (where the latter is a tax surface, not a research surface) returns zero production routes. The `annual_report` matches found in `packages/domain/src/portfolio_outlook_domain/research_library.py:190, :268, :324, :330` and `research_suggestions.py:30, :151` are about **company** annual reports as research-source material, not Belgian tax annual reports.

### 8.3 No section input

Even before the PDF question, the section input data is missing:
- **Section 1** (Transactions + TOB): would need TOB on every executed draft — but the worker composer doesn't populate it (§2.4), so worker-composed drafts that fill would have NULL TOB.
- **Section 2** (Dividends + withholding): no `dividend_events` table (§5).
- **Section 3** (Realised gains): no `fx_rate_at_fill` (§7).
- **Section 4** (Speculative classification): no trade-count / turnover tracker (§9.9).
- **Section 5** (Reynders): not recorded (§9.8).
- **Section 6** (Year-end position): no year-end snapshot mechanism (§9.11 — also intersects T-021).
- **Section 7** (Foreign-source income): no `source_country` on dividend events (§9.10) — and no dividend events at all.

Section 1 is the only section with partial data (TOB only on API-route-created drafts; missing for all worker-composed drafts).

## 9. Phase 1c surface (11 findings)

1. **TOB compute asymmetry — worker composer omits TOB** (§2.4) — drafts created via the API `action_draft_sync.py` route get `estimated_belgian_tob` populated; drafts composed by the worker from Decision Packages do NOT. Both write to the same `asset_action_drafts` table; the columns are nullable so worker-composed rows carry NULLs. The Dutch UI surfaces this as "Geen TOB beschikbaar" tooltip text on those rows.
2. **No TOB security classifier** (§2.2) — `compute_orderimpact` defaults its `belgian_tob_security_class` parameter to `STANDARD_STOCK`. The lone production caller (`action_draft_sync.py:203`) passes no override. There is no instrument-metadata-driven classifier — accumulating ETFs and bonds would be silently taxed at the standard rate (0.35% / €1600) instead of the correct rate (1.32% / €4000 for accumulating ETF; 0.12% / €1300 for bond).
3. **Intent §4 "TOB-net expected return" not implemented** (§3.2) — intent says "A trade with a negative net expected return after TOB is not suggested". Reality: TOB is computed and displayed but is NOT subtracted from `ensemble_expected_return_pct` anywhere in sizing (`action_draft_safety.py` Kelly-fraction site does not reference TOB). The repository-contracts comment is explicit: "Informational on the draft; the TOB does not change order sizing."
4. **No "Total TOB for the year" surface** (§6.1, §4.2) — intent §1 compute item #2. No aggregation query, no API route, no frontend surface.
5. **Tax rate versioning absent** (§1.2) — intent §7 open question 1 explicitly flags this. Rates are hard-coded Python constants at `belgian_tax.py:52-59`. A rate change requires a code deployment.
6. **`compute_dividend_withholding` is a stranded primitive** (§5) — exported but zero callers. No `dividend_events` table, no dividend-ingestion path in either the API or the worker IBKR adapters.
7. **No `fx_rate_at_fill` on `ibkr_executions`** (§7.1) — disposal realised-gain in EUR cannot be correctly computed because execution-time FX is not recorded. Intent §4 valuation-by-purpose row "Belgian tax disposal events" is unimplementable as-shipped. Re-confirmed from T-021 §10.8.
8. **Reynders bond-component recording absent** (§6.2) — no `reynders`, `bond_component`, `bond_share` columns anywhere in storage. Intent §1 record item #1.
9. **Speculative classification tracker absent** (§6.2) — no portfolio-level `trade_count`, `turnover`, or `holding_period_distribution` rolling aggregation. The `trade_count` field at `quantitative_research.py:71` is for HistoricalMarketBar data, NOT portfolio activity. Intent §4 mandates a "system-decision item" surfaces when rolling totals approach the thresholds; no surface exists.
10. **Foreign-source income summary absent** (§6.2) — no `source_country`, `country_of_domicile`, `treaty_rate` columns on any dividend or income table (and no dividend table at all). Intent §3 §7 + intent §1 record item #3.
11. **Annual report — zero infrastructure** (§8) — no PDF library dependency, no `/tax/report` route, and 6 of 7 section inputs are unavailable. The only partial section input is section 1 (TOB on executed drafts), and even that's incomplete due to finding §9.1. The €1M securities-account threshold check (intent §1 record item #4) shares the same fate — no column, no aggregation query.

## 10. Out of scope (re-confirmed)

- **Portfolio valuation + cost basis** (T-021 — merged sibling; the source of the `fx_rate_at_fill` finding §9.7 reaffirmed here).
- **AI explanation** (T-023 future).
- **Predictor backtest + leaderboard** (T-024 future).
- **Settings configuration of Category 3 speculative thresholds** — intent §4 mentions Category 3 settings; T-061 (settings inventory) already documented that no speculative-threshold fields exist on the `trading_settings` table.

## 11. References

- `packages/portfolio/src/portfolio_outlook_portfolio/belgian_tax.py:1-148`
- `packages/portfolio/src/portfolio_outlook_portfolio/action_draft_safety.py:23, :170-185, :388-455` (the single TOB call site)
- `packages/portfolio/src/portfolio_outlook_portfolio/__init__.py:131-133, :594-596` (public re-exports)
- `apps/api/src/portfolio_outlook_api/action_draft_sync.py:30, :203, :238-239, :342-343`
- `apps/worker/src/portfolio_outlook_worker/action_draft/composer.py:91, :269` (no TOB references — finding §9.1)
- `packages/storage/alembic/versions/0035_action_draft_belgian_tob.py:1-31`
- `packages/storage/src/ai_trading_agent_storage/metadata.py:1569-1570` (`asset_action_drafts` TOB columns), `:2772-2813` (`ibkr_executions` — no `fx_rate_at_fill`)
- `packages/storage/src/ai_trading_agent_storage/repository_contracts.py:2199-2200, :2202-2203, :2265-2266`
- `packages/storage/src/ai_trading_agent_storage/migration_readiness.py:361-362` (Dutch readiness note)
- `apps/web/lib/apiClient.ts:1299-1300`
- `apps/web/app/portefeuille/page.tsx:517, :541`
- `docs/intent/belgian-tax.md` (locked 2026-05-26)
- `docs/decisions/0012-belgian-tax-architecture.md`
- `docs/reality/components/portfolio-money-and-accounting.md` (T-002)
- `docs/reality/components/api-actions-suggestions-and-watchlists.md` (T-005)
- `docs/reality/workflows/portfolio-valuation-and-cost-basis.md` (T-021 — §10.8 `fx_rate_at_fill` originating finding)
- `docs/reality/components/settings-and-credentials-infrastructure.md` (T-061 — confirms speculative-threshold settings absent)
