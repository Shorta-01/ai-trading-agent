# `packages/portfolio` — daily briefing and tax

**Phase:** 1a (reality components)
**Task:** T-002
**Scope:** four modules in `packages/portfolio/src/portfolio_outlook_portfolio/` that assemble the deterministic daily briefing, summarise research evidence into a Decision-Package block, compute Belgian TOB + dividend withholding, and surface the V1 asset-capability policy table.

This file is descriptive. It states what the code at HEAD does today, with `path/to/file.py:NNN` citations and short excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

- `daily_briefing.py` — Slice-12 deterministic Dutch daily-briefing builder.
- `research_evidence_summary.py` — Slice-9 per-source credibility / freshness / blocking summarizer.
- `belgian_tax.py` — Slice-11 TOB rate table + dividend roerende voorheffing.
- `capabilities.py` — V1 product capability table built on the domain Pydantic models.

All four modules are pure-Python with no I/O; clocks are injected by callers (`now`, `as_of`, `assessed_at`).

## `daily_briefing.py` — deterministic Dutch daily briefing

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/daily_briefing.py`

### Public surface

- **Alert kind constants** (`:20-25`): `ALERT_KIND_NEW_SUGGESTION`, `ALERT_KIND_NEW_DECISION_PACKAGE`, `ALERT_KIND_NEW_ACTION_DRAFT`, `ALERT_KIND_DIARY_OUTCOME_CLOSED`, `ALERT_KIND_CRITICAL_DRAFT_EVENT`, `ALERT_KIND_FX_STALE`.
- **Severity constants** (`:27-29`): `SEVERITY_INFO`, `SEVERITY_WARNING`, `SEVERITY_CRITICAL`.
- **Status constants** (`:31-32`): `STATUS_READY`, `STATUS_BLOCKED` — `STATUS_BLOCKED` is exported but the computed result always sets `STATUS_READY` (`:370`).
- **Frozen `@dataclass` input types** (`:35-99`): `BriefingPositionInput`, `BriefingSuggestionInput`, `BriefingDecisionPackageInput`, `BriefingActionDraftInput`, `BriefingDiaryOutcomeInput`, `BriefingCriticalEventInput`, and the aggregator `BriefingInputs` (carries `now`, `lookback_started_at`, `base_currency`, `fx_freshness_status`, `cash_total_base_currency`, plus six tuples).
- **Result types** `BriefingAlertResult` (`:101-108`) and `BriefingResult` (`:111-125`).
- **Single public entry point** `compute_daily_briefing(inputs: BriefingInputs) -> BriefingResult` (`:311`).

### Collaborators

Stdlib only: `collections.abc.Iterable`, `dataclasses.dataclass/field`, `datetime.date/datetime`, `decimal.Decimal` (`:15-18`). No imports from `portfolio_outlook_domain` or any other internal package — input types are local frozen dataclasses; the caller translates domain rows into them.

### Notable choices

- Module docstring makes doctrinal claims: V1 requires a "once-per-day Dutch summary that references only locked numbers and counts", "AI **never** authors the briefing", and the caller supplies `now` and `lookback_started_at` so counters are reproducible — no `datetime.now()`, no provider calls (`:1-11`).
- Trust signals propagated: position counts and value, cash, FX freshness, "new since cutoff" counts. The summary surfaces FX-stale state (`:283-284`); the alert list adds an FX-stale warning whenever `fx_freshness_status.lower() == "stale"` (`:241-254`).
- Severity escalation: `dry_run_status == "failed"` on a new action draft escalates the alert from INFO to WARNING (`:187-189`). Critical events are always SEVERITY_CRITICAL (`:228`). Diary outcomes with `outcome_label_1m is None` are silently skipped (`:206-207`).
- Decimal sums, not floats: position totals iterate Decimals starting from `Decimal("0")` (`:138-141`); `None` market values filtered out; if no values exist, total is `None`, not zero.
- Help text is a constant Dutch string emphasising determinism and no-AI-authorship (`:353-356`).
- Briefing date comes from `inputs.now.date()` only — no timezone handling (`:359`).
- Hard-coded Dutch templates throughout (e.g. `"Nieuwe suggestie: {symbol} → {action_label_nl}"`); pluralization via `"(s)"` suffixes; no `_en` counterpart.

```python
# daily_briefing.py:241-254
if inputs.fx_freshness_status and inputs.fx_freshness_status.lower() == "stale":
    alerts.append(
        BriefingAlertResult(
            alert_kind=ALERT_KIND_FX_STALE,
            severity=SEVERITY_WARNING,
            reference_kind="fx_freshness",
            reference_id=None,
            title_nl="FX-koersen zijn stale",
            body_nl=(
                "De laatste FX-snapshot is niet vers; portfolio-waarderingen "
                "kunnen afwijken. Voer een market-data sync uit."
            ),
        )
    )
```

```python
# daily_briefing.py:319-340
cutoff = inputs.lookback_started_at
new_suggestions = _filter_after(inputs.suggestions, "generated_at", cutoff)
new_packages = _filter_after(inputs.decision_packages, "generated_at", cutoff)
new_drafts = _filter_after(inputs.action_drafts, "created_at", cutoff)
closed_outcomes = _filter_after(
    inputs.diary_outcomes, "last_evaluated_at", cutoff
)
critical_events = _filter_after(
    inputs.critical_events, "occurred_at", cutoff
)
position_count = len(inputs.positions)
total_position_value = _sum_position_value(inputs.positions)
```

## `research_evidence_summary.py` — research evidence summarizer

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/research_evidence_summary.py`

### Public surface

- **Credibility constants** (`:24-27`): `CREDIBILITY_NO_RESEARCH`, `CREDIBILITY_HIGH`, `CREDIBILITY_MIXED`, `CREDIBILITY_LOW`.
- **Freshness constants** (`:29-32`): `FRESHNESS_NO_RESEARCH`, `FRESHNESS_FRESH`, `FRESHNESS_MIXED`, `FRESHNESS_STALE`.
- **Blocking-reason constants** (`:34-35`): `BLOCKING_REASON_PROMPT_INJECTION_HIGH_RISK`, `BLOCKING_REASON_CREDIBILITY_REJECTED`.
- **Thresholds** (`:40-41`): `FRESHNESS_FRESH_MAX_DAYS = 30`, `FRESHNESS_MIXED_MAX_DAYS = 90`.
- **Dataclasses:** `ResearchEvidenceInputs` (`:44-59`); `ResearchEvidenceSummary(count, credibility_bucket, freshness, blocking_reason, research_snippet_nl)` (`:62-68`).
- **Public function:** `summarize_research_for_asset(sources, *, now)` (`:148-152`).

### Collaborators

Stdlib only (`collections.abc.Iterable`, `dataclasses.dataclass`, `datetime.datetime`, `:20-22`). No internal imports.

### Notable choices

- Docstring cites doctrine: "research can flag a block, but research alone can never *lift* a block" (`:1-16`). The storage invariants `blocks_suggestions=True` on `ResearchSourceEvidenceItemRecord` and `ResearchSourceCredibilityAssessmentRecord` are referenced as the enforcement layer.
- **Block priority order:** prompt-injection `"high"` short-circuits first; only if none is found is `"rejected"` credibility checked (`:175-184`). Order is load-bearing.
- **Credibility aggregation** (`:77-94`): only sources whose level is `{"high","medium","low"}` count as "known"; "unknown" and absent levels are ignored. `CREDIBILITY_HIGH` requires *all* known sources `"high"`; `CREDIBILITY_LOW` requires *all* known `"low"`; otherwise `MIXED`. Empty known set → `MIXED`.
- **Freshness aggregation** (`:97-107`): all ≤30 days → FRESH; all >90 days → STALE; everything else → MIXED. Empty timestamps → MIXED.
- Empty input returns `NO_RESEARCH` sentinels and the Dutch snippet `"Geen onderzoek gekoppeld aan dit asset."` (`:117-118, :162-173`).
- All credibility/risk strings pass through `_normalize` (lowercase + strip, `:71-74`).

```python
# research_evidence_summary.py:77-94
def _aggregate_credibility(levels: list[str]) -> str | None:
    known = [level for level in levels if level in {"high", "medium", "low"}]
    if not known:
        return CREDIBILITY_MIXED
    if all(level == "high" for level in known):
        return CREDIBILITY_HIGH
    if all(level == "low" for level in known):
        return CREDIBILITY_LOW
    return CREDIBILITY_MIXED
```

```python
# research_evidence_summary.py:175-184
blocking_reason: str | None = None
for source in source_list:
    if _normalize(source.prompt_injection_risk_level) == "high":
        blocking_reason = BLOCKING_REASON_PROMPT_INJECTION_HIGH_RISK
        break
if blocking_reason is None:
    for source in source_list:
        if _normalize(source.credibility_level) == "rejected":
            blocking_reason = BLOCKING_REASON_CREDIBILITY_REJECTED
            break
```

## `belgian_tax.py` — TOB + dividend roerende voorheffing

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/belgian_tax.py`

### Public surface

- `TobSecurityClass(StrEnum)` (`:31-43`) — six members: `STANDARD_STOCK`, `DISTRIBUTING_ETF`, `ACCUMULATING_ETF`, `BOND`, `SICAV_REDEMPTION`, `OTHER`. Module docstring: string values are stored on action-draft rows "so the audit chain can prove which rate was applied" (`:33-37`).
- `TobRateInfo(rate: Decimal, cap: Decimal)` frozen dataclass (`:46-49`).
- **Module-level Decimal constants** (`:53-61`):
  - `TOB_RATE_BOND = Decimal("0.0012")`, `TOB_RATE_STANDARD = Decimal("0.0035")`, `TOB_RATE_ACCUMULATING = Decimal("0.0132")`.
  - `TOB_CAP_BOND = Decimal("1300")`, `TOB_CAP_STANDARD = Decimal("1600")`, `TOB_CAP_ACCUMULATING = Decimal("4000")`.
  - `BELGIAN_DIVIDEND_WITHHOLDING_RATE = Decimal("0.30")`.
- `_RATE_TABLE` (`:63-74`) maps `TobSecurityClass → TobRateInfo`. `OTHER` defaults to the standard 0.35% / €1600 cap as a "conservative default".
- `tob_rate_info(security_class)` (`:85`); `compute_tob(*, transaction_value, security_class)` (`:91`); `compute_dividend_withholding(*, gross_dividend)` (`:119`).

### Collaborators

Stdlib only: `dataclasses.dataclass`, `decimal.ROUND_HALF_UP/Decimal`, `enum.StrEnum` (`:26-28`). No internal imports.

### Notable choices

- Module docstring (`:1-22`) locks the 2025 rate schedule and explicitly states the module is **informational** in V1: TOB surfaces on the Decision Package Orderimpact and Action-draft preview but "the doctrine still keeps `safe_for_*` flags hard-False on every persisted row. The TOB does not change order sizing."
- **Rate-class → (rate, cap) mapping:** `STANDARD_STOCK`/`DISTRIBUTING_ETF` → 0.35% / €1600; `ACCUMULATING_ETF`/`SICAV_REDEMPTION` → 1.32% / €4000 (SICAV redemption shares the high rate); `BOND` → 0.12% / €1300; `OTHER` → standard 0.35% / €1600 (conservative default).
- Formula: `min(transaction_value × rate, cap)` rounded `HALF_UP` to cents (`:114-116`).
- `_round_eur_cents` (`:79-82`) quantizes to `Decimal("0.01")` with `ROUND_HALF_UP` and the comment "the convention IBKR + brokers use." This is non-banker's rounding — Python's default Decimal rounding is `ROUND_HALF_EVEN`.
- Strict typing: raises `TypeError` on non-`Decimal` input, `ValueError` on negative inputs (`:108-111, :126-129`). Zero short-circuits to `Decimal("0.00")` before multiplication (`:112-113, :130-131`).
- EUR-only currency assumption — `transaction_value` documented as "the gross transaction value in EUR" (`:98`); no FX conversion in this module.
- "Per-transaction cap" semantics — the cap applies per transaction, not aggregated across day/year (`:96-101`).
- No language fields (no `*_nl` strings on outputs) — module returns Decimal only.

```python
# belgian_tax.py:31-43
class TobSecurityClass(StrEnum):
    """Locked Belgian TOB security classes.

    The string values are stored on the action-draft row so the audit
    chain can prove which rate was applied.
    """

    STANDARD_STOCK = "standard_stock"  # listed equity → 0.35%
    DISTRIBUTING_ETF = "distributing_etf"  # distributing fund/ETF → 0.35%
    ACCUMULATING_ETF = "accumulating_etf"  # accumulating fund/ETF → 1.32%
    BOND = "bond"  # listed bond → 0.12%
    SICAV_REDEMPTION = "sicav_redemption"  # SICAV redemption → 1.32%
    OTHER = "other"  # conservative default → 0.35%
```

```python
# belgian_tax.py:108-116
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

## `capabilities.py` — V1 product capability table

**Path:** `packages/portfolio/src/portfolio_outlook_portfolio/capabilities.py`

### Relationship to `packages/domain/.../capabilities.py`

This module is **not** a duplicate of the domain `capabilities.py` (covered in `domain-portfolio-and-policy.md`). The domain layer defines the Pydantic `AssetCapability` / `CapabilityCheckResult` types with `@model_validator` invariants enforcing the consistency rules between `status` (ALLOWED/WATCH_ONLY/BLOCKED) and the boolean permission flags. This module imports those types and contains the V1 **product policy data** — which categories are ALLOWED vs WATCH_ONLY vs BLOCKED with the Dutch user-facing explanations. The domain layer enforces shape; this module fills in the actual product decisions.

```python
# capabilities.py:1-9
from portfolio_outlook_domain import (
    AssetCapability,
    BlockedReasonCode,
    CapabilityCategory,
    CapabilityStatus,
    CapabilityCheckResult,
)
from .errors import InvalidAccountingInputError
```

### Public surface

- `get_default_asset_capabilities() -> dict[CapabilityCategory, AssetCapability]` (`:55-297`) — builds and returns the full V1 capability table.
- `get_asset_capability(category)` (`:300-302`) — lookup with `UNKNOWN` fallback (fail-closed).
- **Six `check_can_*` functions** returning `CapabilityCheckResult` (`:305-335`): `check_can_watch`, `check_can_research`, `check_can_generate_action_suggestion`, `check_can_create_paper_order`, `check_can_create_paper_transaction`, `check_can_enter_paper_portfolio`.
- **Two `require_can_*` guards** (`:338-351`): `require_can_create_paper_order` and `require_can_create_paper_transaction` — raise `InvalidAccountingInputError` with the Dutch explanation.
- Private helpers `_capability(...)` (`:12-38`) and `_check_result(...)` (`:41-52`).

### Collaborators

`portfolio_outlook_domain` (enums + Pydantic models, `:1-7`); `.errors.InvalidAccountingInputError` (`:9`).

### The V1 policy

- **ALLOWED (all `can_*` True):** `CASH`, `TERM_DEPOSIT`, `UCITS_ETF`, `STOCK`, `FX`, `COMMODITY_ETF_ETC` (`:60-146`).
- **ALLOWED with carve-out:** `BENCHMARK` (`:120-131`) — watch/research/ai-explain only; no suggestions, no orders, no paper-portfolio. `status=ALLOWED` not `WATCH_ONLY`; the domain validator (`packages/domain/.../capabilities.py:24-28`) forbids `blocked_reason_codes` on ALLOWED, and this row has none — so it passes validation but with all action-flags False.
- **WATCH_ONLY** (watch/research/ai-explain True; rest False; ≥1 BlockedReasonCode): `FUTURES`, `OPTIONS`, `LEVERAGE`, `SHORT_SELLING`, `CRYPTO`, `PENNY_STOCK`, `COMPLEX_DERIVATIVE`, `HIGH_FREQUENCY_TRADING` (`:147-266`). Each carries a Dutch explanation ending in "...niet toegestaan in versie 1 en blijft/blijven alleen opvolgbaar".
- **BLOCKED:** `AUTOMATIC_REAL_MONEY_EXECUTION` (`:267-281`) and `UNKNOWN` (`:282-296`). `AUTOMATIC_REAL_MONEY_EXECUTION` still allows `can_ai_explain=True` (so the user can be told *why* it's blocked) but forbids everything else including watch/research. `UNKNOWN` blocks everything including ai_explain.

### Notable choices

- `get_asset_capability` (`:300-302`) returns the `UNKNOWN` row for any category not in the table — fail-closed. Combined with `UNKNOWN`'s all-False permissions, an unrecognised category yields a deny-all `CapabilityCheckResult`.
- `_check_result` defaults reason codes (`:44-45`): if `allowed=False` and the capability has no `blocked_reason_codes`, the result is injected with `NOT_ALLOWED_IN_VERSION_1`. The domain `CapabilityCheckResult` validator requires non-empty `blocked_reason_codes` when `allowed=False`, so this fallback keeps the Pydantic construction valid.
- Multiple reason codes per WATCH_ONLY: `FUTURES` carries `NOT_ALLOWED_IN_VERSION_1` + `DIRECT_COMMODITY_OR_FUTURE_BLOCKED` (`:157-160`); `OPTIONS` carries `NOT_ALLOWED_IN_VERSION_1` + `COMPLEX_DERIVATIVE` (`:173-176`).
- Every capability carries an `explanation_nl` Dutch string; no `_en` counterpart. `require_can_*` interpolates `category.value` and the `explanation_nl` into the exception message (`:341-343, :349-351`).
- `COMMODITY_ETF_ETC` is ALLOWED (`:132-146`) with a softer warning in its Dutch explanation: "...olie blijft extra risicovol" — fully tradeable in paper.
- `get_default_asset_capabilities` rebuilds the dict each call (no caching).

```python
# capabilities.py:41-52
def _check_result(category: CapabilityCategory, allowed: bool) -> CapabilityCheckResult:
    capability = get_asset_capability(category)
    reasons = capability.blocked_reason_codes
    if not allowed and not reasons:
        reasons = [BlockedReasonCode.NOT_ALLOWED_IN_VERSION_1]
    return CapabilityCheckResult(
        category=capability.category,
        allowed=allowed,
        status=capability.status,
        explanation_nl=capability.explanation_nl,
        blocked_reason_codes=reasons,
    )
```

```python
# capabilities.py:267-281
CapabilityCategory.AUTOMATIC_REAL_MONEY_EXECUTION: _capability(
    category=CapabilityCategory.AUTOMATIC_REAL_MONEY_EXECUTION,
    status=B,
    can_watch=False,
    can_research=False,
    can_ai_explain=True,
    can_generate_action_suggestion=False,
    can_create_paper_order=False,
    can_create_paper_transaction=False,
    can_enter_paper_portfolio=False,
    blocked_reason_codes=[BlockedReasonCode.REAL_MONEY_EXECUTION_BLOCKED],
    explanation_nl=(
        "Automatische uitvoering met echt geld is volledig geblokkeerd in versie 1."
    ),
),
```

## Cross-cutting observations

- All four modules are **pure-Python, no-I/O, no `datetime.now()`** (callers inject `now`). Consistent with the doctrine of determinism + auditability cited in `daily_briefing.py:1-11` and `research_evidence_summary.py:1-16`.
- Three of the four (`daily_briefing`, `research_evidence_summary`, `belgian_tax`) have **zero internal imports** — only stdlib. `capabilities.py` is the only one that imports from `portfolio_outlook_domain` and `.errors`.
- **Language convention:** outputs that carry text use a single `*_nl` field (Dutch); no `*_en` parallel anywhere in these files.
- **Decimal-only math:** `daily_briefing.py` and `belgian_tax.py` use Decimal consistently; `belgian_tax.py` actively rejects non-Decimal input via `TypeError`.
- **`ROUND_HALF_UP` (broker convention) in `belgian_tax.py`** (`:82`) rather than Python's Decimal default `ROUND_HALF_EVEN` — load-bearing for IBKR parity.

## Open questions / uncertainty

- `daily_briefing.py` exports `STATUS_BLOCKED` but the computed result always sets `STATUS_READY` (`:370`). Whether this is leftover from an earlier API or intentional placeholder for future blocking is unclear from the file alone.
- `research_evidence_summary.py`'s thresholds (30 days fresh, 90 days mixed-to-stale, `:40-41`) are hard-coded. Whether these are intended to be configurable per `docs/intent/settings-and-credentials.md` Category 2 is out of scope here.
- `belgian_tax.py` uses `ROUND_HALF_UP` "the convention IBKR + brokers use" (`:81`). Whether the rest of the package's money flow should adopt the same rounding (versus the current absence-of-rounding policy described in `portfolio-money-and-accounting.md`) is a Phase 1b architecture-review question.
- `capabilities.py` rebuilds the full table on every `get_asset_capability` call (`:301`). Whether this is a measured pure-function choice or candidate for memoisation is out of scope for Phase 1a.
- `belgian_tax.py` 2025 rates may need version-stamping when 2026 rates land — the module currently embeds them as module-level constants with no versioning hook. `docs/intent/belgian-tax.md` §7 lists "tax rules versioning and annual update mechanism" as an open doctrine question.
