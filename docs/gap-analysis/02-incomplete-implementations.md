# Gap Analysis 02 — Incomplete Implementations

**Scope.** Features whose code exists but is incomplete: unwired classes, stranded primitives, asymmetric paths, duplicated orchestrators, schema gaps. Distinct from T-044 (features-that-don't-exist) and T-046/T-047/T-048 (specialised categories). Each entry uses the Track 1c 6-part format.

**Pattern**: most entries are **unwired infrastructure** — classes that exist + are tested + have docstrings claiming production wiring, but are never instantiated outside tests.

## 0. Gap matrix at a glance

15 incomplete-implementation gap entries.

| # | Implementation | Effort | MoSCoW |
|---|----------------|--------|--------|
| 1 | `SubmissionSweep.tick()` not APScheduler-wired | S | **Must** |
| 2 | `IbkrReconciler.tick()` not APScheduler-wired | S | **Must** |
| 3 | Worker `cancel_order` not wired (T-019 §4.8 + T-027 §5) | M | **Must** |
| 4 | `compute_dividend_withholding` stranded (no callers, no dividend events table) | M | Should |
| 5 | `PaperLot` + `FifoLotAllocation` unpersisted (no storage adapter) | L | Should |
| 6 | Worker composer omits TOB while API path populates (asymmetric) | S | Should |
| 7 | `fx_rate_at_fill` schema gap on `ibkr_executions` | S | **Must** |
| 8 | AI Depth-B is 2-3 sentence paraphrase not intent's 6-element structure | M | Should |
| 9 | AI explanation eager-generated not lazy | S | Could |
| 10 | No `prompt_version` column on `decision_package_explanations` cache | S | Should |
| 11 | Dual morning chains (worker + API parallel) | M | Should |
| 12 | Two reconciliation orchestrators (worker 3-pass + API legacy) | M | Should |
| 13 | Two `placeOrder` paths (worker submitter + API direct) | M | **Must** |
| 14 | 4-tier B/C/D/E reconciliation classification absent from code | M | Could |
| 15 | `skipped_locked` ticks produce no audit row | S | Should |

**Distribution**: 5 Must + 8 Should + 2 Could. **Effort**: 7 S + 6 M + 1 L.

## 1. `SubmissionSweep.tick()` not APScheduler-wired

- **Name**: Wire `SubmissionSweep.tick()` into the worker APScheduler.
- **Why it matters**: User-approved action drafts (status `user_approved`) never reach IBKR. T-026 §6 documented the post-approval banner ("IBKR-verzending wordt in een toekomstige update toegevoegd") as out-of-date; T-034 corrected this to **accidentally truthful** — the submission infrastructure (T-019) exists but is uninvoked. Without this fix, every approval pile up indefinitely.
- **Where it would live**: `apps/worker/src/portfolio_outlook_worker/scheduler.py:130-175` — add a 4th `add_job` call invoking `SubmissionSweep.tick()` on an interval trigger (cadence TBD per T-034 §6).
- **Effort**: **Small** — the class is fully implemented + tested. Wiring is ~10 LOC + cadence choice.
- **Dependency**: None code-wise. Requires architectural decision on cadence (1min / 5min / event-driven).
- **MoSCoW**: **Must**. The system claims to submit orders; without wiring it doesn't.
- **Originating reality**: T-019 §4 + T-020 §10.1 + T-034 §2.

## 2. `IbkrReconciler.tick()` not APScheduler-wired

- **Name**: Wire `IbkrReconciler.tick()` into the worker APScheduler.
- **Why it matters**: Divergences between local state and IBKR truth accumulate undetected. T-027's stuck `pending_cancellation` drafts, T-019's ghost-order recovery, T-020's Pass A/B/C — all depend on the reconciler tick running. **0 of 7 intent-§1 trigger paths implemented** (T-035 §5).
- **Where it would live**: Same `scheduler.py:130-175` extension as item 1. Intent §1 mandates 15min market-hours + 1h off-hours cadence + 5 event triggers.
- **Effort**: **Small** — class implemented + tested. Wiring is ~15 LOC for the periodic cadence; event triggers (after-fill, after-reconnect, 07:00-block) are separate items.
- **Dependency**: Companion to item 1 — both ticks share the single-flight lock. Item 7 (user-trigger from T-044) provides the manual escape hatch.
- **MoSCoW**: **Must**. The backstop architecture is non-functional without it.
- **Originating reality**: T-020 §10.1 + T-035 §1.2.

## 3. Worker `cancel_order` not wired

- **Name**: Implement worker-side `cancel_order` loop consuming `pending_cancellation` drafts.
- **Why it matters**: T-027 §5 documented the most operationally dangerous gap in the audit: the user clicks Annuleer, the API writes `pending_cancellation` + a lifecycle audit row, and **nothing else happens**. The route docstring (`action_draft.py:786-795`) describes a worker that picks up the row and calls `ib.cancelOrder()` — that worker doesn't exist. Orders may still fill 30 minutes after a "successful" cancel.
- **Where it would live**: New `apps/worker/src/portfolio_outlook_worker/ibkr_submission/cancel_sweep.py` (parallel to `submission_sweep.py`) polling `pending_cancellation` drafts + invoking the existing `submitter.py:89` `cancel_order` Protocol method.
- **Effort**: **Medium** — protocol exists; the adapter implementation + the polling loop + audit-row writing + lock-sharing is medium.
- **Dependency**: Items 1 + 2 (APScheduler wiring infrastructure must be in place).
- **MoSCoW**: **Must**. Live trading without working cancel is a regulatory + operational risk.
- **Originating reality**: T-019 §4.8 + T-027 §5 + §9.1.

## 4. `compute_dividend_withholding` stranded

- **Name**: Wire `compute_dividend_withholding` to dividend-event ingestion.
- **Why it matters**: The primitive exists at `belgian_tax.py:119` (T-022 §1.5) with locked 30% rate, HALF_UP rounding, fully tested. But there are **zero production callers**. The reason: there is no `dividend_events` table, no dividend-event ingestion path in either API or worker. The annual report Section 2 (dividends + withholding, T-044 item 3) is blocked on this.
- **Where it would live**: New `dividend_events` storage table + IBKR-side `accountSummary` callback ingestion (or EODHD dividend data per T-014) + reporting pipeline.
- **Effort**: **Medium** — table schema + ingestion + tests. The primitive is ready.
- **Dependency**: Annual tax report (T-044 item 3). Foreign-source income summary (T-044 item 13) layers on top.
- **MoSCoW**: Should — blocks the annual report; not critical to per-order trading.
- **Originating reality**: T-022 §5 + §10.

## 5. `PaperLot` + `FifoLotAllocation` unpersisted

- **Name**: Add storage persistence for the `PaperLot` + `FifoLotAllocation` domain models.
- **Why it matters**: T-021 §10.1 documented the biggest data-model intent-vs-reality drift: intent §1 of `portfolio-valuation.md` mandates per-lot storage with `lot_id` / `acquisition_date` / `unit_cost_local` / `fx_rate_at_acquisition`. The domain models exist (`packages/domain/.../lots.py:11-72`) but have no storage adapter. The system stores aggregate `average_cost` only. FIFO display (T-044 item 8) + tax-correct cost basis depend on this.
- **Where it would live**: New `position_lots` storage table + lifecycle handler updates to consume buy fills into lots + sell fills into FIFO allocations.
- **Effort**: **Large** — schema design + ingestion + FIFO depletion logic + migration of existing aggregate data + UI updates.
- **Dependency**: `fx_rate_at_fill` (item 7) — without execution-time FX, lots cannot record `fx_rate_at_acquisition` accurately. FIFO display setting (T-044 item 8) depends.
- **MoSCoW**: Should — intent §1 mandates it explicitly; v1 trades function with aggregate.
- **Originating reality**: T-021 §1.3 + §10.1 + §10.2.

## 6. Worker composer omits TOB while API path populates

- **Name**: Add TOB computation to the worker `compose_action_draft_from_decision_package` path.
- **Why it matters**: T-022 §9.1 documented the asymmetry: action drafts created via the API `action_draft_sync.py` path have `estimated_belgian_tob` + `belgian_tob_security_class` populated. Drafts composed by the worker from Decision Packages do NOT — they leave the columns NULL. The Dutch UI surfaces this as "Geen TOB beschikbaar" tooltip on those rows. Two action-draft creation paths producing structurally-different rows.
- **Where it would live**: `apps/worker/src/portfolio_outlook_worker/action_draft/composer.py` — invoke `compute_tob` + record `belgian_tob_security_class` in the composed `ActionDraftEntry`.
- **Effort**: **Small** — single function call + field population. The `compute_tob` primitive is ready (T-022 §1).
- **Dependency**: Requires deciding the security-class default (currently always `STANDARD_STOCK` per `action_draft_sync.py`; T-022 §9.2 documented this as a separate gap).
- **MoSCoW**: Should.
- **Originating reality**: T-022 §2.4 + §9.1.

## 7. `fx_rate_at_fill` schema gap

- **Name**: Add `fx_rate_at_fill` + `eur_value_at_fill` columns to `ibkr_executions`.
- **Why it matters**: T-021 §10.8 + T-022 §10.7 originated this finding from two angles. **Intent §4 of `portfolio-valuation.md` mandates "Belgian tax disposal events | Actual execution price × Actual execution-time FX rate".** The system records `fill_price_local` + `fill_time` but **no execution-time FX rate**. Per-disposal realised gain in EUR cannot be correctly computed today. The latest FX snapshot reflects "now", not "fill time". This blocks: annual tax report Section 3 (item 3 above), per-lot disposal (item 5), the entire realised-P&L surface.
- **Where it would live**: New Alembic migration adding 2 columns + IBKR-side FX lookup at fill-time via `reqMktData` on the FX pair OR using `commissionReport.commission_currency` + the stored fx_rate_snapshots at `fill_time`.
- **Effort**: **Small** — schema change is small; the FX-lookup-at-fill-time strategy is the open question.
- **Dependency**: Blocks T-044 item 3 + several T-046/T-047 gaps. Highest leverage among the schema gaps.
- **MoSCoW**: **Must** — without this column, tax-correct realised gains in EUR are unimplementable.
- **Originating reality**: T-021 §10.8 + T-022 §10.7.

## 8. AI Depth-B is 2-3 sentence paraphrase not intent's 6-element structure

- **Name**: Restructure the AI explanation prompt to produce the intent §1 6-element Depth-B output.
- **Why it matters**: T-023 §1.2 documented the hard-coded prompt (`SYSTEM_PROMPT_NL` at `anthropic_explanation_provider.py:55-62`) asks for "twee tot drie zinnen" — 2-3 Dutch sentences. Intent §1 of `ai-usage.md` mandates Depth-B = 6 elements (why action, predictor contributions, ensemble confidence, sizing layer, limit price logic, risk context). What ships is fundamentally narrower than what was locked.
- **Where it would live**: New prompt template loaded from `docs/intent/ai-explanation-prompt.md` at runtime (currently hard-coded; intent §2 Layer 1 mandates the file-based source). Plus output schema: 6 structured fields instead of free-form text.
- **Effort**: **Medium** — prompt redesign + structured-output parsing + cache schema extension + UI updates for the 6-section display.
- **Dependency**: T-044 item 6 (Depth-C surface) — both share the prompt-as-data infrastructure.
- **MoSCoW**: Should — intent §1 is explicit; Phase 2 backlog candidate.
- **Originating reality**: T-023 §10.1.

## 9. AI explanation eager-generated not lazy

- **Name**: Defer AI explanation generation to first explanation-icon click.
- **Why it matters**: T-023 §2.1 documented that the current implementation generates the LLM explanation **at Decision Package composition time** — every composed DP eats LLM budget regardless of whether the user opens the explanation. Intent §1 specifies "lazy-generated on first explanation-icon click". The eager pattern wastes ~80% of LLM budget for DPs the user never opens.
- **Where it would live**: Remove the eager `generate_explanation` call from `decision_package_routes.py`. Add a new on-demand route `POST /decision-packages/{id}/explanation` (or repurpose the existing 2 routes at `apiClient.ts:1453-1457`) that generates + caches on first request.
- **Effort**: **Small** — move the call site from composition path to on-demand route. Cache logic mostly already exists.
- **Dependency**: None.
- **MoSCoW**: Could — operational cost optimisation; doesn't affect correctness.
- **Originating reality**: T-023 §10.3.

## 10. No `prompt_version` column on explanation cache

- **Name**: Add `prompt_version` column to `decision_package_explanations` for reproducibility.
- **Why it matters**: Intent §5 Case C guardrail #1 of `ai-usage.md` mandates "Cached / snapshotted output with timestamp and the prompt version that produced it. Reproducibility is guaranteed." The cache row has `generated_at` but no `prompt_version`. To reproduce an explanation, an operator must git-blame `anthropic_explanation_provider.py:55-62` at the row's `generated_at` — operationally brittle.
- **Where it would live**: New Alembic migration + new column populated from a module-level `PROMPT_VERSION = "v1"` constant bumped on every prompt edit.
- **Effort**: **Small** — single column + version constant + write-site update.
- **Dependency**: None.
- **MoSCoW**: Should — Case C compliance + audit-chain integrity.
- **Originating reality**: T-023 §10.12.

## 11. Dual morning chains (worker + API parallel)

- **Name**: Reconcile the worker `_on_hourly`/`_on_pre_briefing` morning chains with the parallel API `morning_chain.py` orchestrator.
- **Why it matters**: T-032 §5 documented the dominant Track 1a doctrine drift: the worker scheduler pins fixed 06:00 + 07:00 fires; the API has its own APScheduler driving `run_daily_briefing_job` via `SCHEDULER_DAILY_BRIEFING_CRON` (default `"30 6 * * *"` = 06:30). The same config string is read by both but only honored by the API. Both write to the same `forecast_predictions`, `decision_packages`, `asset_action_drafts` tables. No coordination. Both consume LLM cost.
- **Where it would live**: Architectural decision: either (a) delete the API morning chain + consolidate on worker, (b) delete worker morning chain + consolidate on API, or (c) explicitly coordinate (impractical).
- **Effort**: **Medium** — pick one + remove the other + update tests + decision record.
- **Dependency**: None code-wise. Requires architectural commitment.
- **MoSCoW**: Should — doctrine cleanup; not blocking user trading.
- **Originating reality**: T-032 §5 + §10.6-§10.7.

## 12. Two reconciliation orchestrators (worker 3-pass + API legacy)

- **Name**: Retire the legacy `reconciliation_sync.py` API-side orchestrator.
- **Why it matters**: T-020 §10.7 documented the doctrine drift: the API ships **two reconciliation paths** — the new Task 135b 3-pass system (T-020) AND a legacy SUBMITTED→FILLED→RECONCILED orchestrator (`apps/api/src/portfolio_outlook_api/reconciliation_sync.py:1-13`) using the older portfolio state-machine vocabulary. The legacy module is unused by the new 3-pass flow but still importable. Two-vocabulary state-machine island re-confirmed 6th time in Track 1a.
- **Where it would live**: Delete `apps/api/src/portfolio_outlook_api/reconciliation_sync.py`. Update any remaining test references.
- **Effort**: **Medium** — verify no production callers + remove + update tests.
- **Dependency**: Item 11 (dual orchestrators) is the same pattern; deciding one informs the other.
- **MoSCoW**: Should — dead-code removal + vocabulary unification.
- **Originating reality**: T-020 §10.7.

## 13. Two `placeOrder` paths (worker submitter + API direct)

- **Name**: Unify the order-submission surface — single `place_order` authority.
- **Why it matters**: T-019 §4 + §10.1 documented the most safety-critical doctrine drift: **both** the worker (`submitter.py:240`) AND the API (`ibkr_ibapi_order_submission_client.py:525`) can call `placeOrder`. AGENTS.md §3.2 ("no order without explicit user approval") assumes a single authority — but the API path has no user-approval gate. T-019 surfaced this; T-026 §4 noted the JA token is client-side only. The two paths could conflict on shared IBKR session state.
- **Where it would live**: API-side: remove the standalone `placeOrder` call OR convert it to call into the worker via an intra-process message. Worker: stays as the single authority.
- **Effort**: **Medium** — identify any API path that actually invokes the API `placeOrder` + redirect via worker + add tests.
- **Dependency**: Companion to item 1 (worker sweep wiring). Both establish "worker is the single submission authority".
- **MoSCoW**: **Must**. The most safety-critical drift in the audit.
- **Originating reality**: T-019 §4 + §10.1.

## 14. 4-tier B/C/D/E reconciliation classification absent from code

- **Name**: Implement the B/C/D/E tier classification on reconciliation divergences.
- **Why it matters**: Intent §3 + §4 of `reconciliation.md` mandate 4 severity tiers (`tier_b` low → `tier_e` critical) with per-pass threshold tables. T-020 §10.3 documented these strings appear NOWHERE in the reconciliation modules. Code uses flat `divergence_type` strings via a CHECK constraint. Intent's threshold table (B threshold / C threshold / D threshold / E threshold per pass) is purely aspirational.
- **Where it would live**: Extend `reconciliation_audit.divergence_type` to `reconciliation_audit.tier` + per-pass threshold reads from `trading_settings` (Category 3 — also absent per T-029 §8).
- **Effort**: **Medium** — schema + per-pass logic + settings storage.
- **Dependency**: Trading-settings Category 3 (T-029 §8). System-decision item generator (T-018-related — also absent).
- **MoSCoW**: Could — operational severity classification; nice-to-have, not blocking.
- **Originating reality**: T-020 §10.3.

## 15. `skipped_locked` produces no audit row

- **Name**: Write `worker_run_audit` row even when the orchestrator skips on lock contention.
- **Why it matters**: T-020 §10.1 + T-031 §9.2 + T-032 §9.10 + T-033 §9.8 + T-041 §7 all carried this finding. When a tick fails to acquire the single-flight lock, it returns before writing the audit row. Operators cannot reconstruct "did this 06:00 fire today? did it lose the lock?" from `worker_run_audit`. The audit gap is the silence.
- **Where it would live**: `apps/worker/src/portfolio_outlook_worker/orchestrator.py:181-200` — move the `run_audit_repo.append` call to BEFORE the `lock.try_acquire()` attempt, OR add a separate `append` for the lock-fail-fast path.
- **Effort**: **Small** — single audit-row write + minor refactor.
- **Dependency**: None.
- **MoSCoW**: Should — observability fix; couples with T-048's operational gaps.
- **Originating reality**: T-020 §10.1 + multiple T-031-T-035 cross-refs.

## 16. Cross-reference: gap coverage across Track 1c siblings

Some incomplete-implementation findings cross categorical boundaries. Mapping:

| Gap | Covered in T-045 | Cross-ref to | Reason |
|-----|------------------|--------------|--------|
| ADR-0003 1-of-7 predictors (T-024 §10.12) | Briefly via item 5 | T-046 | Quant-specific, full coverage in T-046 |
| Shadow-mode infrastructure (T-024 §10.9) | No | T-046 | Quant-specific |
| Voice-rule Layers 2 + 3 (T-023 §10.5-§10.6) | Item 8 references | T-047 | AI integration deep dive |
| Multi-provider fallback (T-023 §10.8) | No | T-047 | AI-specific |
| Single-worker uvicorn (T-041 §1) | No | T-048 | Operational |
| Pool tuning (T-041 §2) | No | T-048 | Operational |
| Authentication (T-042 §1) | No | T-048 | Operational/security |
| Backup tooling (T-042 §8) | No | T-048 | Operational/security |
| Banner text out-of-date (T-026 §6 / T-034) | No — UI-text gap, low value | (none) | Track 1c may not need to cover |
| Action draft route docstring (T-027 §5.1) | No — docstring inaccuracy | (none) | Documentation fix; not architectural |

T-045 stays focused on **partial code that needs completing**. UI text drift + docstring accuracy belong to a code-cleanup track Phase 1c didn't define; they show up in T-049 summary as "documentation hygiene" cluster.

## 17. Summary

15 incomplete-implementation gap entries. **Distribution**: 5 Must + 8 Should + 2 Could. The 5 Musts are tightly clustered around **the safety-critical operational gap**:

- Items 1 + 2: APScheduler wiring for both backstop ticks.
- Item 3: worker cancel wiring (T-027 §5 — most dangerous user-action gap).
- Item 7: `fx_rate_at_fill` schema (unblocks the entire realised-P&L stack).
- Item 13: Single `place_order` authority (most safety-critical doctrine drift).

These 5 items together would close ~80% of the operational risk Track 1a surfaced. Combined effort: 4 Small + 1 Medium = manageable for a focused Phase 2 sprint.

The 8 Shoulds + 2 Coulds are doctrinal cleanup + observability + tax-stack-prerequisite work. Less urgent; addressable post-Must.

## 18. References

- T-017 / T-018 / T-019 / T-020 reality docs (submission + reconciliation + action-draft gaps)
- T-021 §10.1-§10.2, §10.8 (per-lot storage + fx_rate_at_fill)
- T-022 §1-§5, §9.1, §10.7 (TOB asymmetry + stranded withholding + fx gap)
- T-023 §1.2, §2.1, §10.1-§10.12 (AI explanation prompt + cache gaps)
- T-024 §3 (backtest API exists + leaderboard UI absent — UI covered in T-044, API completeness in T-046)
- T-026 §4-§6 (JA client-only enforcement + out-of-date banner)
- T-027 §5 (cancel-not-wired — dominant operational gap)
- T-029 §8 (trading-settings Category 3 absent)
- T-032 §5 + T-033 §5 (dual morning chains + hourly_delta empty fires)
- T-034 §2 + T-035 §1.2 (both backstop ticks not wired)
- T-041 §1-§2 (single-worker + pool — covered fully in T-048)
- T-042 §1, §8 (auth + backups — covered fully in T-048)
- T-043 §3 (4 critical Track 1c priorities)
- T-044 §16 (cross-reference table — sibling)
- `docs/intent/ai-usage.md` §1, §2, §5 (Depth-B/C + voice + Case C)
- `docs/intent/portfolio-valuation.md` §1, §4 (per-lot + exec-time FX)
- `docs/intent/reconciliation.md` §1, §3, §4 (cadence + tier classification)
- `docs/intent/belgian-tax.md` §1, §3 (compute + record split)
