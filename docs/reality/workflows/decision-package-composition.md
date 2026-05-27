# Reality — workflow: Decision Package composition

**Scope.** End-to-end per-asset trace of how a Decision Package is composed and persisted — from the orchestrator's step-10 gate firing at 07:00 morning_briefing → `compose_and_persist_for_run` orchestration iteration over forecasts → per-asset `compose_decision_package` pure function → 5 locked gate sequence → SHA-256 content-addressed hash + `previous_package_hash` chain → deterministic Dutch explanation template → persisted `decision_packages` row.

A Decision Package is the **immutable evidence-bundle** that justifies any future action draft. It carries the issued forecast quantiles + the gate outcomes + the deterministic Dutch narrative + a content-addressed hash for tamper detection. Action drafts (T-018, future) read Decision Packages but never modify them.

**Sibling reality docs (read for module-level detail):**

- `docs/reality/components/worker-forecasting-and-decision-package.md` §§9-11 — composer pure function + Dutch template + orchestration (T-007).
- `docs/reality/components/portfolio-money-and-accounting.md` — Decimal-as-string discipline (T-002).
- `docs/reality/components/api-actions-suggestions-and-watchlists.md` — Decision Package storage + API serialization (T-005).
- `docs/reality/workflows/morning-chain-orchestration.md` §7 — the orchestrator gate that triggers this flow (T-011).
- `docs/reality/workflows/forecast-generation-and-labelling.md` (T-015) — what produces the `ForecastEntry` rows this flow consumes.
- `docs/reality/workflows/market-data-pipeline.md` (T-014) — supplies the market snapshots + FX rates the composer reads.

## 0. TL;DR

The worker orchestrator at 07:00 morning_briefing (T-011 §7) calls `compose_and_persist_for_run(...)`. For each `ForecastEntry` row written by the forecasting step (T-015):

1. **Skip if `label="Geblokkeerd"`** (gate at orchestration layer; the pure-function composer would otherwise raise `GeblokkeerdForecastError`).
2. **Load context**: market snapshot (T-014), FX rate (only if non-EUR), asset listing, current position, **previous Decision Package** (for the chain anchor).
3. **Compose**: call `compose_decision_package(...)` — pure function, no I/O. Evaluates 5 locked gates in order; computes EUR conversions; builds evidence references; renders Dutch explanation paragraph; computes SHA-256 content hash; assembles `DecisionPackageEntry` record.
4. **Persist**: `decision_package_repo.append(package)` — single INSERT.

The hash is **content-addressed**: `composed_at` + `decision_package_id` are deliberately excluded from the hash input, so two runs over identical content yield identical hashes. The `previous_package_hash` field chains each row to its predecessor (`(account, conid)`-scoped chain).

The result row is hard-locked with `safe_for_action_drafts=False`, `safe_for_orders=False` — Decision Packages **never** authorise orders directly; they're evidence the user reviews before approving a draft.

## 1. Trigger gate (orchestrator step 10)

Per `worker-orchestration-and-scheduling.md` §6.5 + `morning-chain-orchestration.md` §7:

The orchestrator at `apps/worker/.../orchestrator.py:348-370` evaluates:

```
if decision_package_runner is not None
   AND forecast_details is not None
   AND "error" not in forecast_details
   AND mode_detected == "normal"
   AND run_type == "morning_briefing"
   AND ibkr_account_id is not None:
    decision_package_runner.run(ibkr_account_id, scheduled_run_id)
```

**Gating semantics**:

- **Gated on forecasting success**: a forecasting-step failure (`"error" in forecast_details`) aborts DP composition for the same run. T-011 §7 documents this — DP composition only attempts if the upstream forecasting succeeded.
- **`morning_briefing` only**: pre_briefing (06:00) skips DP composition; hourly_delta runs (08:00-21:00) also skip. DPs are written exactly once per morning at 07:00 Brussels.
- **`mode_detected="normal"` only**: cold_start, awaiting_watchlist_confirmation, disconnected modes all skip DP composition.

If gated, sets `decision_package_details = {"error": "decision_package_runner_exception"}` on exception (`orchestrator.py:366-370`) — folded into the morning-chain audit row under key `"decision_package"` (T-011 §10).

## 2. Orchestration layer (`compose_and_persist_for_run`)

`apps/worker/.../decision_package/orchestration.py:93-101`:

```python
def compose_and_persist_for_run(
    *,
    ibkr_account_id: str,
    scheduled_run_id: str,
    forecast_source: _ForecastSourceProtocol,
    context_provider: _ContextProviderProtocol,
    decision_package_repo: SqlAlchemyDecisionPackageRepository,
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> DecisionPackageCompositionResult
```

### 2.1 Per-asset iteration (`orchestration.py:119-188`)

For each `ForecastEntry` in `forecast_source.list_forecasts_for_scheduled_run(...)`:

1. **Skip `Geblokkeerd`** — `skipped_geblokkeerd += 1` (`:120-122`). Comment cites the doctrine binding: the composer's pre-check at `composer.py:108-113` would raise `GeblokkeerdForecastError` if a blocked forecast reached it.
2. **Fetch market snapshot** — `context_provider.market_snapshot_for_conid(forecast.conid)` (`:124-126`). If `None` → log warning `"Skipping Decision Package for %s: no market snapshot"`, `missing_context += 1`, continue (`:127-135`).
3. **Conditionally fetch FX** — `fx_rate = context_provider.fx_rate_for_currency(forecast.currency_local) if currency != "EUR" else None` (`:137-143`). EUR-denominated assets skip the FX lookup.
4. **Fetch asset listing** — `context_provider.asset_listing_for_conid(...)` (`:144-146`) — provides the symbol + exchange + asset_class for the gate evaluation (gate 3 below).
5. **Fetch position** — `context_provider.position_for_account_conid(account, conid)` (`:147-149`) — used to compute `user_holds_position`.
6. **Fetch previous Decision Package** — `decision_package_repo.get_latest_for_account_conid(ibkr_account_id, conid)` (`:150-154`). This is the chain anchor for `previous_package_hash`.
7. **Compose** — `compose_decision_package(...)` (`:156-166`). On `GeblokkeerdForecastError` → `skipped_geblokkeerd += 1` (defensive — should not happen post-step-1 skip). On other exception → `composition_errors += 1` (`:167-177`).
8. **Persist** — `decision_package_repo.append(package)` (`:179-181`). On persist exception → log + `composition_errors += 1` (`:182-188`).

### 2.2 Read-only orchestration

The orchestrator does **NOT read** from storage to find the forecasts — they're passed in already-loaded by `forecast_source` (`:189-191`). Indirectly, the context provider does load the 4 supporting context records per asset.

Result: `DecisionPackageCompositionResult(forecasts_seen, composed, skipped_geblokkeerd, missing_context=0, composition_errors=0, persisted_ids=())` (`:66-90`). Documented invariant (`:70-74`): `forecasts_seen == composed + skipped_geblokkeerd + missing_context + composition_errors`.

The audit dict via `as_audit_dict()` (`:83-90`) folds back into the orchestrator's audit row under key `"decision_package"`.

## 3. Pure-function composer (`compose_decision_package`)

`apps/worker/.../decision_package/composer.py:79-89`:

```python
def compose_decision_package(
    *,
    forecast: ForecastEntry,
    ibkr_account_id: str,
    market_snapshot: MarketDataEodSnapshotEntry,
    fx_rate: FxRateRecord | None,
    asset_listing: AssetListingRecord | None,
    position_snapshot: IbkrPositionSnapshotRecord | None,
    previous_package: DecisionPackageEntry | None,
    composed_at: datetime | None = None,
) -> DecisionPackageEntry
```

**Pure function — no I/O.** Takes all inputs as arguments, returns the assembled record. `composed_at` defaults to `datetime.now(UTC)` (`:115-116`).

### 3.1 Geblokkeerd pre-check (`:108-113`)

```python
if forecast.label == "Geblokkeerd":
    raise GeblokkeerdForecastError(...)
```

The composer raises immediately if a blocked forecast reaches it. The orchestrator's per-asset iteration (§2.1 step 1) catches this before it happens.

### 3.2 Doctrine bindings (`composer.py:1-24`, verbatim)

> **"AI never originates a field of the Decision Package.** The label is copied from the forecast; the explanation is generated by the locked Dutch template; the gate outcomes are deterministic boolean checks; the audit hash is SHA-256 of canonical JSON." (`:8-12`)
>
> **"Decimal end-to-end.** No `float` anywhere in the composition path, including inside the hash input. The canonical JSON serializer renders each Decimal as its string repr with full precision so the hash is reproducible." (`:13-17`)
>
> **"Immutable.** `DecisionPackageEntry` is frozen; the composer never mutates input records. Two calls with identical inputs (modulo `composed_at`) yield identical hashes." (`:18-20`)
>
> **"The composer crashes when asked to compose for a `Geblokkeerd` forecast — that's a caller bug.** The orchestrator filters Geblokkeerd forecasts before calling." (`:21-24`)

These four bindings shape every design decision below.

## 4. The 5 locked gate sequence

`composer.py:56-62`:

```python
_GATE_NAMES_IN_ORDER: Final[tuple[str, ...]] = (
    "forecast_valid",
    "data_fresh",
    "asset_listing_resolved",
    "freshness_within_sla",
    "confidence_at_least_medium",
)
```

**Order matters**: per `composer.py:54-55` comment, the order must stay locked "so the explanation template can append 'Let op:' sentences in the same sequence."

### 4.1 Per-gate definition (`evaluate_gates`, `composer.py:287-358`)

Sequential evaluation; each gate runs independently and contributes one `GateOutcome` row to the result. The composer does **not** short-circuit on first failure — all 5 gates always evaluate. Result includes all 5 outcomes in the same order; consumers (Dutch template, frontend) iterate.

| # | Gate | Condition | Dutch fail reason | File:line |
|---|---|---|---|---|
| 1 | `forecast_valid` | Always `True` here (orchestrator pre-filter guarantees non-Geblokkeerd) | n/a — "for completeness + audit traceability" | `:298-309` |
| 2 | `data_fresh` | `freshness_state != "unavailable"` | "Marktdata is niet beschikbaar voor dit asset." | `:310-320` |
| 3 | `asset_listing_resolved` | `asset_listing is not None` | "Asset-listing kon niet worden opgehaald." | `:321-331` |
| 4 | `freshness_within_sla` | `data_age_trading_days <= 3` | `f"Marktdata is {data_age_trading_days} dagen oud; SLA is {_FRESHNESS_SLA_DAYS} dagen."` | `:332-345` |
| 5 | `confidence_at_least_medium` | `forecast.confidence_level in ("Gemiddeld", "Hoog")` | "Betrouwbaarheid is Laag — gebruik met voorzichtigheid." | `:346-357` |

### 4.2 Gate-1 rationale

`forecast_valid` always passes because the orchestrator pre-filters Geblokkeerd forecasts at §2.1 step 1. Per `composer.py:298-300`: kept in the gate list "for completeness + audit traceability" — every Decision Package row carries the full 5-gate audit trail, even where one gate is trivially satisfied.

### 4.3 `_FRESHNESS_SLA_DAYS = 3` (`composer.py:67`)

Same 3-day threshold as the forecasting step's `STALE_MARKET_DATA_THRESHOLD_DAYS` (T-015 §4 — `forecasting_step.py:66`). Both gates measure the same notion of data staleness, applied at different layers — forecasting blocks at >3 days; DP composition recomputes the gate independently with its own copy.

Comment at `composer.py:64-67`: "Anything older than 3 calendar days (same threshold as the Task 131 `stale_market_data` block_reason) trips the gate."

### 4.4 Confidence gate — `Laag` blocks

Gate 5 fails when `forecast.confidence_level == "Laag"`. Per T-015 §6.2, `Laag` is effectively unreachable from `derive_confidence` today (the `gaps_in_last_60_days=0` hardcode) — so in practice gate 5 always passes for live forecasts. The gate exists as a safety floor for any future code path that produces a `Laag` forecast.

## 5. Per-asset derived fields

`composer.py:118-178`:

- `user_holds = position_snapshot is not None and position_snapshot.quantity > 0` (`:118-120`).
- `held_quantity`, `held_avg_cost_local` from snapshot when held (`:121-126`).
- `current_price_eur`, `p10/p50/p90_price_eur` via `_convert_to_eur(amount_local, fx_rate)` (`:129-154`).
- `data_age_trading_days` via `_trading_day_age(...)` (`:500-512`) — calendar-day proxy, **honest about being calendar-day not trading-day** (per `:503-509` — "Real trading-day accounting (skipping weekends + Brussels public holidays) is a future refinement; at the 3-day SLA threshold the calendar approximation is conservative").
- `freshness_state` via `_classify_freshness(...)` (`:515-520`): `<=1 → "fresh"`, `<=3 → "stale"`, else `"unavailable"`.
- `gates = evaluate_gates(...)` (`:164-169`).
- `explanation = render_explanation(...)` (see §7).
- `decision_package_id = f"dp_{uuid4().hex}"` (`:200`).
- `previous_package_hash = previous_package.audit_trail_hash if not None else None` (`:201-205`).

### 5.1 Quantile-to-price math (`_price_at_quantile`, `composer.py:469-475`)

```python
factor = Decimal(repr(math.exp(float(log_return))))
(current_price_local * factor).quantize(Decimal("0.000001"))
```

Goes through `float` for `math.exp` but re-wraps via `repr` into Decimal — same float→str→Decimal pattern as the bootstrap quantisation (T-015 §5.4).

### 5.2 EUR conversion (`_convert_to_eur`, `composer.py:478-497`)

EUR-only assets short-circuit (`:484-485`); missing FX for non-EUR currency falls back **1:1** with a logger warning (`:486-496`). Per the inline comment at `:489-492`: "Composer always has FX for non-EUR in production wiring; tests cover the EUR-only path."

The 1:1 fallback is a **silent degradation** — a Decision Package for a USD asset without FX wired could show USD prices labelled as EUR. Phase 1c surface.

## 6. Hash-chain invariants (`compute_audit_trail_hash`, `composer.py:361-455`)

The cryptographic backbone. SHA-256 over a canonical JSON serialisation at `:452-455`:

```python
canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

### 6.1 Content-addressed invariant (`composer.py:395-401`, verbatim)

> "SHA-256 over canonical JSON of every package-defining field. `composed_at` + `decision_package_id` are deliberately excluded so the hash is content-addressed — two compositions of the same logical content yield identical hashes (the per-asset chain check in `test_compose_idempotent_hash` depends on this)."

**Deliberately excluded from hash**: `composed_at` (changes per run) + `decision_package_id` (fresh UUID per run). All other package-defining fields are included.

### 6.2 Hash-input fields (`composer.py:403-451`)

The hash payload covers:

- `forecast_run_id`, `ibkr_account_id`, `conid`, `symbol`, `exchange`, `currency_local`, `asset_class`, `user_holds_position`.
- `held_quantity`, `held_avg_cost_local` (each via `_decimal_to_canonical`).
- `current_price_local`, `current_price_eur` (Decimal → canonical).
- `as_of_market_data_ts.isoformat()` (`:416`).
- `freshness_state`, `data_age_trading_days`.
- `forecast_method` (always `"historical_bootstrap_v1"` today — see T-015 §2).
- `p10/p50/p90_log_return`, `p10/p50/p90_price_eur` (Decimal).
- `prob_positive`, `prob_loss_gt_5pct`, `expected_volatility_annualized` (Decimal).
- `forecast_confidence_level`, `suggested_action_label`, `block_reason`.
- `gate_outcomes`: list of `{gate_name, passed, reason_nl}` (`:434-441`).
- `evidence_references`: list of `{source_id, source_type, claim_summary}` (`:442-449`).
- `previous_package_hash` (the chain anchor — see §6.4).

### 6.3 Decimal-canonical encoding (`_decimal_to_canonical`, `composer.py:461-466`)

`str(Decimal)` preserves full precision without scientific notation. **No `float()` anywhere in the hash path** — guarantees that running the composer twice over the same inputs (with the same FX/market snapshot) produces byte-identical canonical JSON → identical SHA-256.

### 6.4 The previous_package_hash chain

Per-`(account, conid)` chain. `previous_package_hash` on row N points to `audit_trail_hash` of row N-1 (the latest `DecisionPackageEntry` for the same `(account, conid)` before row N's `composed_at`). The chain is fetched once per asset at §2.1 step 6 via `decision_package_repo.get_latest_for_account_conid(...)`.

Tampering detection: if any field changes in row N-1 retroactively, row N's chain becomes invalid because `previous_package_hash` no longer matches N-1's recomputed hash. Full chain audit can walk forward from the first row.

Initial chain anchor: the first DP for a given `(account, conid)` has `previous_package_hash = None`.

## 7. Evidence references (`_build_evidence_references`, `composer.py:523-564`)

Builds a tuple of `EvidenceReference(source_id, source_type, claim_summary)` rows:

1. **Always include the EOD market-data snapshot** (`:529-538`). `claim_summary = f"EOD-snapshot voor {symbol} op {as_of_date.isoformat()}"`.
2. **Add FX-rate evidence when `fx_rate is not None`** (`:539-552`). `source_id = f"{base}/{quote}@{as_of_date}"`, `claim_summary = f"FX-koers {base}→{quote} = {rate}"`.
3. **Add IBKR position evidence when held** (`:553-563`).

**No news/research evidence** is added by the composer today. The `evidence_references` field carries only the three structural-data evidence types. This is a known gap — ADR-0003 / `docs/ai-policy.md` envisions research/news evidence references but the composer doesn't generate them. Phase 1c.

## 8. Deterministic Dutch explanation template

Module: `apps/worker/.../decision_package/dutch_explanation_template.py`.

**Hard contract** (T-007 §10, verbatim from module header `:1-20`):

> "Pure Python templating. No AI. No conditional prose beyond the locked branches below." (`:3-4`)
>
> "Same forecast + same gate outcomes always produces the exact same paragraph — that's the doctrine: 'AI never originates a field of the Decision Package'." (`:4-6`)
>
> "UI surfaces the paragraph verbatim — no client-side rendering of forecast numbers, no client-side translation." (`:18-20`)

### 8.1 7-sentence locked paragraph structure (`:8-17`)

```
{opening sentence with asset name + label + horizon}
{forecast quantile sentence with p10/p50/p90 prices in EUR}
{probability sentence with prob_positive + prob_loss_gt_5pct}
{risk sentence with annualized volatility}
{confidence sentence}
{validity sentence}
{one "Let op: <reason>" sentence per failed gate}
```

The final "Let op:" sentences are appended **in the locked gate order** (§4), one per `passed=False` gate. A perfectly-clean DP has 6 sentences; a DP with all 5 gates failed has 11 (6 + 5 "Let op:").

### 8.2 Interpolation mechanism

Python f-strings — **not** `str.format`, **not** Jinja, **no AI**. Hand-built concatenation per `render_explanation(...)` (`dutch_explanation_template.py:79-93`).

### 8.3 Locked vocabulary (`_LABEL_PROSE`, `:33-39`)

5-entry dict mapping the 5 actionable labels to Dutch label-prose:

| Label | Dutch prose |
|---|---|
| `Kopen` | `"een koopkans"` |
| `Verminderen` | `"een aanleiding om de positie te verminderen"` |
| `Verkopen` | `"een aanleiding om de positie te verkopen"` |
| `Houden` | `"geen actie nodig"` |
| `Bekijken` | `"een signaal om te bekijken"` |

`Geblokkeerd` is absent (would never reach the template per the §3.1 pre-check).

### 8.4 Dutch month names (`_DUTCH_MONTHS`, `:43-56`)

Hand-coded integer→Dutch-month map (`januari`...`december`) per `:42-43`: "avoid locale-dependent strftime which on CI containers can produce English names."

## 9. Persistence — `DecisionPackageEntry` record

Built at `composer.py:245-284`. The hard order-safety floor lives at `:282-283`:

```python
safe_for_action_drafts=False,
safe_for_orders=False,
```

**These are hard-coded `False` in V1.1.0.** A Decision Package never authorises an action draft or an order directly — the user must explicitly approve a draft built from the package (T-018, future).

### 9.1 Storage table

`decision_packages` table — single INSERT per composed package at orchestration step §2.1 step 8.

### 9.2 Idempotency story — intent vs reality

**Intent** (per `composer.py:18-20` immutability binding): "Two calls with identical inputs (modulo `composed_at`) yield identical hashes." This means `(account, conid, content_hash)` should uniquely identify a Decision Package — re-running the composer over the same morning_briefing data should produce the same hash.

**Reality**: `decision_package_id = f"dp_{uuid4().hex}"` (`composer.py:200`) — fresh UUID per call. Re-running the composer over identical inputs writes a NEW row with a new id but the same hash. The append-only `decision_packages` table does **not** enforce uniqueness on `(account, conid, audit_trail_hash)` — duplicate writes are accepted.

**Consequence**: a re-run after partial failure would produce duplicate rows. Consumers (T-018 action-draft composer; T-008 frontend Decision Package detail page) must dedupe by `(account, conid)` and pick the latest by `composed_at`. Phase 1c surface — the intent contract is documented but the schema doesn't enforce it.

## 10. End-to-end timeline (one asset)

For a typical 07:00 morning_briefing fire with N=20 universe assets:

| t (ms) | Tier | Action |
|---|---|---|
| 0 | Orchestrator | step 10 gate fires (T-011 §7) |
| ~10 | Worker | `compose_and_persist_for_run` enters |
| ~20 | Worker | `forecast_source.list_forecasts_for_scheduled_run(...)` — load N forecasts |
| ~30 | Worker (per asset, skip if Geblokkeerd) | 4 context-provider calls (market, FX, listing, position) |
| ~80 | Worker (per asset) | `decision_package_repo.get_latest_for_account_conid(...)` — chain anchor query |
| ~100 | Worker (per asset) | `compose_decision_package(...)` — pure function, no I/O |
| ~110 | Composer | 5-gate evaluation |
| ~115 | Composer | EUR conversion + price-at-quantile + freshness classification |
| ~120 | Composer | `_build_evidence_references` — 1-3 evidence rows |
| ~125 | Composer | `render_explanation(...)` — 6-11 Dutch sentences |
| ~130 | Composer | `compute_audit_trail_hash` — canonical JSON + SHA-256 |
| ~135 | Composer | Returns `DecisionPackageEntry` |
| ~140 | Worker (per asset) | `decision_package_repo.append(package)` — single INSERT |
| ~150 | Worker | Loop continues to next asset |

For N=20 assets at ~140 ms each = ~2.8 s. Dominated by the per-asset context-provider queries; pure-function composition is sub-millisecond.

## 11. Failure paths

| Failure | Surface | Result |
|---|---|---|
| Orchestrator step-10 gate fails (mode/run_type/forecast error) | step skipped | no `decision_packages` rows; orchestrator audit carries `"decision_package": null` or absent |
| Forecast has `label="Geblokkeerd"` | orchestration §2.1 step 1 skip | `skipped_geblokkeerd += 1` |
| Market snapshot missing | orchestration §2.1 step 2 skip | log warning + `missing_context += 1` |
| FX rate missing for non-EUR currency | composer 1:1 fallback at `composer.py:486-496` | row persisted with USD-labelled-as-EUR (silent degradation) |
| Asset listing missing | composer gate 3 fails | row persisted with `gate_outcomes[2].passed=False`; "Let op:" sentence appended |
| Stale market data (>3 days) | composer gate 4 fails | row persisted with gate failure + "Let op:" |
| Confidence `Laag` | composer gate 5 fails | row persisted with gate failure + "Let op:" |
| Composer raises `GeblokkeerdForecastError` | orchestration §2.1 step 7 catch | `skipped_geblokkeerd += 1` (defensive — should never happen post §2.1 step 1) |
| Composer raises any other exception | orchestration §2.1 step 7 catch | log + `composition_errors += 1` |
| Persist raises | orchestration §2.1 step 8 catch | log + `composition_errors += 1`; row lost (no retry) |
| Whole-step exception | orchestrator step 10 catch | `decision_package_details = {"error": "decision_package_runner_exception"}` folded into morning-chain audit |

The "row persisted with gate failure" path is the **normal** path for partial-quality DPs — the package exists in the table with full audit trail, but the explanation paragraph carries "Let op:" warnings and consumers see the failed gates.

## 12. Cross-cuts + Phase 1c surface

The following observations are inputs for Phase 1c gap analysis:

1. **Idempotency intent vs reality**: composer doctrine says identical inputs → identical hash; storage schema permits duplicate writes. Consumers must dedupe. Phase 4: add UNIQUE on `(account, conid, audit_trail_hash)` or a "latest only" view.
2. **No news/research evidence references**. `_build_evidence_references` builds 3 structural-data types (EOD snapshot, FX rate, position). ADR-0003 / `docs/ai-policy.md` envision research references but the composer doesn't generate them. Phase 4 candidate.
3. **Silent FX 1:1 fallback** for non-EUR currencies with missing FX rate (`composer.py:486-496`). USD prices could display as EUR. Phase 1c: either fail the composition or surface the fallback explicitly.
4. **`_trading_day_age` is calendar-day** (T-007 §9 + here §5). Friday/Monday gaps and Brussels public holidays not accounted for. At the 3-day SLA threshold this is conservative but a Phase 4 refinement candidate.
5. **`forecast_method` always `"historical_bootstrap_v1"`**. ADR-0003 7-vs-1 predictor gap recurs here (T-015 §2): every DP today carries the same method stamp.
6. **Gate-1 `forecast_valid` is always-passing today**. Kept for audit completeness but carries no signal. If a future code path lets Geblokkeerd forecasts reach the composer, gate 1 becomes meaningful — until then, it's a dead branch.
7. **Hash chain breaks silently if a DP row is deleted**. The chain assumes append-only `decision_packages`. There's no DELETE protection in the schema today. Phase 1c: enforce append-only via DB triggers or soft-delete pattern.
8. **`confidence_level == "Laag"` is unreachable from forecast generation today** (T-015 §6.2 — `gaps_in_last_60_days=0` hardcode). Gate 5 has nothing to catch in practice. Same Phase 1c thread as T-015.
9. **The 5-gate sequence has no opt-out**. All Decision Packages, including warning-heavy ones, are written. There is no "block the DP from being written if N gates fail" cutoff today. Consumers (action-draft composer, T-018) decide independently whether to ignore warning-laden packages.

## 13. Out of scope

- **Forecast generation** (T-015) — what produces the `ForecastEntry` rows.
- **AI explanation** (T-023, future) — the Anthropic Claude explanation provider that may add a narrative on top of the deterministic Dutch paragraph. Per T-006 §11 the AI explanation is a separate write path; the Decision Package's `deterministic_dutch_explanation` field is the canonical narrative.
- **Action-draft composition** (T-018, future) — primary downstream consumer.
- **Backtest leaderboard** (T-024, future) — secondary consumer.
- **Frontend Decision Package detail page** (T-008 §3.9, `/decision-package/[id]`) — UI consumer.

## 14. References

- `docs/reality/components/worker-forecasting-and-decision-package.md` §§9-11 — composer + Dutch template + orchestration source-of-truth (T-007).
- `docs/reality/components/portfolio-money-and-accounting.md` — Decimal-as-string discipline (T-002).
- `docs/reality/components/api-actions-suggestions-and-watchlists.md` — API Decision Package surface (T-005).
- `docs/reality/components/storage-package-and-migrations.md` — `decision_packages` table (T-003).
- `docs/reality/workflows/morning-chain-orchestration.md` §7 — orchestrator gate that triggers this flow (T-011).
- `docs/reality/workflows/forecast-generation-and-labelling.md` (T-015) — produces the `ForecastEntry` rows.
- `docs/reality/workflows/market-data-pipeline.md` (T-014) — supplies the market snapshots + FX rates this flow reads.
- `docs/reality/workflows/forecast-calibration-and-prediction-diary.md` (T-016) — sibling that evaluates the issued forecasts after-the-fact.
- `docs/decisions/0003-forecast-engine-architecture.md` — predictor-set ADR (intent for §5.2).
- `docs/ai-policy.md` — `"AI never originates a field of the Decision Package"` doctrine source.
