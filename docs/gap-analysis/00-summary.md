# Gap Analysis 00 — Summary

**Scope.** Synthesis of Track 1c — 5 gap-analysis docs across 70 concrete gap entries. Each entry has the 6-part format (name + why + where + effort + dependency + MoSCoW). This summary is **the input** to Phase 2 backlog planning — it identifies what to fix; Phase 2 decides what to build.

**Track 1c docs**: T-044 `01-missing-features.md` (15 entries), T-045 `02-incomplete-implementations.md` (15), T-046 `03-quant-and-forecasting-gaps.md` (13), T-047 `04-ai-integration-gaps.md` (12), T-048 `05-operational-gaps.md` (15).

**Closes Track 1c.** 6/6 docs complete.

## 0. Aggregate gap distribution

**70 gap entries** across the 5 docs.

| MoSCoW | Count | % |
|--------|-------|---|
| Must | 19 | 27% |
| Should | 38 | 54% |
| Could | 12 | 17% |
| Won't (v1) | 1 | 1% |

| Doc | Must | Should | Could | Won't | Total |
|-----|------|--------|-------|-------|-------|
| T-044 Missing features | 2 | 8 | 4 | 1 | 15 |
| T-045 Incomplete impl | 5 | 8 | 2 | 0 | 15 |
| T-046 Quant + forecasting | 3 | 6 | 4 | 0 | 13 |
| T-047 AI integration | 3 | 8 | 1 | 0 | 12 |
| T-048 Operational | 6 | 8 | 1 | 0 | 15 |
| **Totals** | **19** | **38** | **12** | **1** | **70** |

### Observations on the distribution

1. **27% Must** is high. Most gap analyses produce ~10-15% Must; the codebase has accumulated more pre-production debt than typical. Concentrated in operational + incomplete-impl categories.

2. **Per-track Must counts inversely correlate with the existing discipline** (per Track 1b). The data layer earned T-039's "discipline at value layer" verdict; correspondingly, T-045's data-related Musts are about wiring (not building). Operations earned T-042's "audit-trail discipline + network-defense void" — and T-048 has the most Musts (6).

3. **Only 1 Won't-v1** — €1M securities-account tax (T-044 §14). The codebase has very few "out of v1 scope" items; almost everything in the audit needs to be addressed eventually.

4. **Effort distribution** (across all 70 entries): roughly 27 Small + 28 Medium + 14 Large + 1 cross-cutting (item T-048 §1 auth = L if non-localhost; S if localhost-only). Coarse balance.

## 1. The 19 Must items by sprint-shape grouping

The 19 Musts fall into 5 natural clusters. Phase 2 sequencing recommendation:

### 1.1 Sprint 1 — Pre-prod hardening (Small efforts only)

5 items. All Small. Total effort: ~1-2 weeks for a single engineer.

| Doc | Item | Description |
|-----|------|-------------|
| T-045 §13 | Single `place_order` authority | API-side `placeOrder` removal — convert to worker-only |
| T-048 §3 | Multi-worker uvicorn | Dockerfile + Gunicorn + 4 workers |
| T-048 §4 | Pool tuning | SQLAlchemy `create_engine` kwargs |
| T-048 §5 | `TrustedHostMiddleware` | Middleware add + settings field |
| T-046 §2 | Weight floor 5%→10% | One constant + tests (the first numeric contradiction in the audit) |

**Convert codebase from "single-user dev" to "minimally hardened multi-user-capable".**

### 1.2 Sprint 2 — Close the wiring + cancel gaps

5 items. Total effort: ~2-3 weeks.

| Doc | Item | Description |
|-----|------|-------------|
| T-045 §1 | Wire `SubmissionSweep.tick()` | APScheduler registration |
| T-045 §2 | Wire `IbkrReconciler.tick()` | APScheduler registration |
| T-045 §3 | Worker `cancel_order` wiring | New `cancel_sweep.py` polling `pending_cancellation` |
| T-048 §15 | Ghost-order recovery via Pass A | Derived from §2 — Pass A reconciliation handles connection-lost case |
| T-047 §1 | Case-B `AnthropicTsModelProvider` quarantine | Intent §5 explicit forbid; remove factory branch |

**Close the audit's safety-critical operational gaps** (T-027 stuck-cancel pattern, T-019 ghost-order risk, T-023 Case-B drift). After Sprint 2, the system actually does what users + auditors believe it does.

### 1.3 Sprint 3 — Auth + backups + foundational schema

4 items. Total effort: ~3-4 weeks depending on auth decision.

| Doc | Item | Description |
|-----|------|-------------|
| T-048 §1 | Auth topology + auth layer | Topology decision; if non-localhost, full auth |
| T-048 §2 | Backup / DR tooling | AGENTS.md mandate compliance |
| T-045 §7 | `fx_rate_at_fill` schema | Unblocks T-046 §3 + T-044 §3 (annual report) |
| T-046 §3 | Backtest transaction costs | Intent's "not a backtest, it's marketing" rebuttal |

**Establish the production-readiness floor** (deployment topology + data resilience). After Sprint 3, the system can leave its current "localhost paper-trading scope" without becoming a security incident.

### 1.4 Sprint 4 — AI + quant correctness foundation

3 items. Total effort: ~2-3 weeks.

| Doc | Item | Description |
|-----|------|-------------|
| T-047 §2 | System prompt from intent file | Intent §2 Layer 1 — code-as-prompt → prompt-as-data |
| T-047 §5 | Dutch "budget bereikt" fallback rendering | Locked user-facing text exists in intent only |
| T-046 §1 | ADR-0003 ensemble closure (6th re-confirmation) | Wire 6 existing predictor modules into worker — largest single doctrinal gap |

**Close AI + quant doctrine drift.** Item T-046 §1 is the audit's largest cumulative finding (6 re-confirmations); closing it converts the system from "1-predictor 'ensemble'" to actual ensemble.

### 1.5 Sprint 5 — Trading-quality Musts

2 items. Total effort: ~3-5 weeks.

| Doc | Item | Description |
|-----|------|-------------|
| T-044 §5 | Live mid-price for sizing context | Intent §4 — sizing on stale prices = direct trading-error risk |
| T-044 §1 | Performance review screen | User cannot evaluate system effectiveness without it |

**Close the user-facing "Must" features.** After Sprint 5, the audit's 19 Musts are all addressed.

### 1.6 Total Sprint 1-5 estimate

~3-4 months of focused engineering work for a single-engineer team OR ~6-8 weeks with parallel work. Track 1c's 19 Musts are bounded; Phase 2 backlog can absorb them in one quarter.

## 2. Cross-doc most-cited findings — "the audit's main loops"

Several findings surfaced in multiple Track 1a reality docs + Track 1b reviews + Track 1c gap entries. The 5 most-cited:

### 2.1 ADR-0003 1-of-7 predictors — **6 re-confirmations**

T-007 (originating), T-014 §10, T-015 §10 (3rd), T-016 §11 (4th), T-024 §10.12 (5th), T-046 §1 (6th).

Worker runs only `historical_bootstrap_v1`. Portfolio package defines 6 predictor modules. Backtest orchestrator supports 3. The "ensemble" is a single predictor. **Largest cumulative finding in the audit.** Fix: T-046 §1 (Sprint 4).

### 2.2 SubmissionSweep + IbkrReconciler wiring gap — **8 re-surfaces**

T-019 §4 (originating), T-020 §10.1 + §10.2, T-027 §5, T-031 §1.2 + T-032 §6 + T-033 §6 + T-034 + T-035, T-041 §5, T-042 §7, T-045 §1+§2, T-048 §15.

Both backstop infrastructure ticks (~470 + ~378 LOC each) exist + are tested but never instantiated outside tests. **Most safety-critical operational gap.** Fix: T-045 §1 + §2 + T-048 §15 (Sprint 2).

### 2.3 Case-B `AnthropicTsModelProvider` drift — **4 docs**

T-005 (originating Case A miss-classification), T-023 §7.2 + §10.11, T-024 §4.1 (re-classification + production path), T-047 §1.

LLM forecaster wired into production behind 5 feature flags despite intent §5 forbidding it ("LLMs hallucinate numbers; risk is unbounded"). **Most safety-critical AI gap.** Fix: T-047 §1 (Sprint 2).

### 2.4 `fx_rate_at_fill` schema gap — **3 docs**

T-021 §10.8 (originating), T-022 §10.7, T-045 §7, T-046 §3 (transaction costs depend).

Execution-time FX not recorded → realised gain in EUR unimplementable → Belgian tax disposal events + annual report Section 3 + backtest transaction costs all blocked. **Highest-leverage single schema change.** Fix: T-045 §7 (Sprint 3).

### 2.5 Auth + backups (the two Track 1c Criticals) — **3 docs**

T-042 §1 + §8 (originating), T-043 §3, T-048 §1 + §2.

Zero authentication on 179 routes + no backup tooling despite AGENTS.md mandate. **The "category transition" pair** — converts the codebase from localhost POC to production-ready. Fix: T-048 §1 + §2 (Sprint 3).

## 3. Track 1b → Track 1c convergence

Track 1b verdicted 56 architectural choices; Track 1c prescribed 70 gap fixes. Several patterns converged:

| Track 1b verdict (T-043) | Track 1c Must items mapped |
|---------------------------|----------------------------|
| 4 state-of-the-art highlights (Decimal, audit, real-impl tests, migration chain) | **0 Must items** — Track 1c says "preserve these" |
| 17 outdated verdicts | Mostly Should-tier Track 1c items (10 of 17 map) |
| 15 risky verdicts | **11 of 15 map to Track 1c Musts** (auth, backups, single-worker, pool, etc.) |
| 2 Critical Track 1b items (auth + backups) | T-048 §1 + §2 (the two highest-leverage Musts) |

**Convergence pattern**: Track 1b "risky" verdicts → Track 1c "Must" gaps with ~73% direct mapping. The two tracks are independently-derived but agree on what's broken.

## 4. The "category transition" thesis

T-043 §8 framed the codebase as **"exceptionally well-built where it had to be and exceptionally under-built where it could afford to be, with the asymmetry consistent enough to be a deliberate design posture."** Track 1c quantifies the cost of closing that asymmetry.

### 4.1 What the codebase IS

A single-user paper-trading prototype with:
- Rigorous data discipline (Decimal-as-string, append-only audit, hash chains).
- 240-file Python test suite with 1% mock ratio (T-040 §2 — "we know what we're doing" signal).
- 53-migration linear Alembic chain.
- Full backstop infrastructure code (submission sweep + reconciliation passes A/B/C) — that doesn't run.
- Six predictor modules — only one wires in.
- AI explanation surface — with 2-3 sentence Dutch paraphrase instead of intent's 6-element structure.
- Frontend modern stack (Next 15 + React 19 + TS 5.7) + 2018-era state management (no React Query, manual apiClient, inline styles).
- Zero auth, zero backups, single-worker uvicorn.

### 4.2 What Track 1c Sprints 1-5 close

After all 19 Musts:
- **Sprint 1** hardens: multi-worker, pool tuning, TrustedHost, single `place_order` authority, weight floor.
- **Sprint 2** wires the unfinished infrastructure: SubmissionSweep + IbkrReconciler + cancel + Case-B quarantine.
- **Sprint 3** establishes deployment readiness: auth + backups + `fx_rate_at_fill`.
- **Sprint 4** closes AI + quant doctrine drift: prompt-as-data, ADR-0003 ensemble, budget fallback rendering.
- **Sprint 5** ships the trading-quality user features: live mid-price, performance review screen.

### 4.3 The category transition

After all 5 sprints, the system becomes:
- A multi-user-capable production service.
- With auth + backups + observability foundations.
- Running a 7-predictor ensemble per ADR-0003.
- With safety-critical backstop infrastructure actually backing things up (cancel works, reconciliation runs, ghost-order recovery wired).
- AI explanation surfacing the locked Dutch text and intent's 6-element structure.

**That is the category transition the 19 Musts represent.** It is not incremental; it converts the codebase from "POC on my machine" to "service I can let other people use".

### 4.4 What 38 Shoulds add

Beyond the category transition, the 38 Shoulds add:
- Tax stack: annual report PDF, Reynders, foreign-source income, speculative classification awareness.
- Voice rules: Layer 2 + Layer 3 deterministic filters.
- Per-lot storage + FIFO display options.
- Observability: structured logging, OpenTelemetry, /metrics, coverage tooling.
- Predictor lifecycle: shadow mode, 3-month observation, 6-month retirement.
- Caching layer + background queue.
- Settings infrastructure for Categories 1 + 3 + 4 + 5.

These complete the v1 vision. The 12 Coulds are nice-to-haves on top.

## 5. What Track 1c did NOT prescribe

T-049 is the synthesis; not the implementation plan. Specifically out of scope for Track 1c, in scope for Phase 2 planning:

- **Concrete code-level implementation plans** for any of the 19 Musts. Track 1c says WHAT; Phase 2 designs HOW.
- **Per-Must acceptance criteria** for "done".
- **Test plans** for each item.
- **Rollback plans** for any item that touches production storage.
- **Migration strategies** for items that require schema changes (e.g., T-045 §7 `fx_rate_at_fill`).
- **Operator runbooks** for the operational items (auth, backups, deployment topology).

Phase 2 backlog will produce these per-item.

## 6. The 12 Coulds — what we deferred

12 items earned `Could` priority. Mostly:
- Doctrine naming hygiene (T-047 §9 `StubTsModelProvider` re-classification).
- Process polish (T-046 §10 CI backtest-gate, T-046 §11 monthly rebacktest, T-046 §12 on-demand UI button).
- Frontend Edge / CDN (T-048 §13).
- AI Depth-C "Explain more" surface (T-044 §6).
- AI per-purpose budget split (T-047 §8 — contingent on item T-047 §1).
- Display method setting (T-044 §8 — FIFO / weighted-avg).
- Multi-provider AI fallback (T-044 §10).
- Cost-basis display method (T-044 §8).
- 4-tier B/C/D/E reconciliation classification (T-046 §14).

The Coulds can wait. None block the category transition.

## 7. Track 1c by the numbers

- **5 docs.**
- **70 gap entries.**
- **19 Must items** (27% of total).
- **38 Should items** (54%).
- **12 Could items** (17%).
- **1 Won't-v1 item** (1% — €1M securities tax).
- **~3-4 months of focused engineering work** to close all 19 Musts (single-engineer team).
- **~6-8 weeks with parallel work** (2-3 engineers).

## 8. References to all Track 1c docs

- `docs/gap-analysis/01-missing-features.md` (T-044 — 15 entries)
- `docs/gap-analysis/02-incomplete-implementations.md` (T-045 — 15 entries)
- `docs/gap-analysis/03-quant-and-forecasting-gaps.md` (T-046 — 13 entries)
- `docs/gap-analysis/04-ai-integration-gaps.md` (T-047 — 12 entries)
- `docs/gap-analysis/05-operational-gaps.md` (T-048 — 15 entries)
- `docs/gap-analysis/README.md` (the track scope)

## 9. Closes Track 1c — Phase 1 audit status

T-049 closes the 6-doc Track 1c Gap Analysis (T-044-T-049). With Track 1c complete:

- **Track 1a (Reality)**: 24 docs across 6 component clusters + 11 workflow docs (T-001-T-024 reality functionality, T-025-T-035 workflows).
- **Track 1b (Architecture Review)**: 8 docs verdicting 56 architectural choices (T-036-T-043).
- **Track 1c (Gap Analysis)**: 6 docs identifying 70 concrete gaps (T-044-T-049).

**Phase 1 audit core complete.** 38 docs produced. Plus 11 code-health docs (T-050-T-060) earlier in Phase 1.

Remaining Phase 1 tasks: **5 functional-review additions** (T-011b, T-011c, T-012b, T-016b, T-021b — carry-forward from 2026-05-26 functional review). After those, Phase 1 is fully complete + Phase 2 backlog can begin from the 19 Musts as initial scope.

## 10. Final synthesis

The Phase 1 audit produced:
- **Track 1a** answered "what IS the system?". Answer: a rigorously-disciplined single-user paper-trading prototype.
- **Track 1b** answered "is what IS good?". Answer: yes at the domain layer; no at the infrastructure layer. Asymmetric discipline.
- **Track 1c** answered "what do we fix?". Answer: 19 Must items, grouped into 5 sprints, totalling ~3-4 months. After which the category transition completes.

The audit's **most impactful single recommendation**: close the 19 Musts in the proposed sprint order. The codebase is honest about its current state; the 19 fixes are bounded; Phase 2 has a clear scope.

Track 1c's verdict: **the gap between the codebase's two halves (rigorous domain layer + sparse infrastructure layer) is closable in one quarter of focused work**.
