# Gap Analysis 01 — Missing Features

**Scope.** User-facing features mandated by intent docs but absent from the shipped code. Each entry uses the Track 1c 6-part gap format: **name + why it matters (plain English) + where it would live + effort estimate (S/M/L) + dependency + MoSCoW priority**.

**Opens Track 1c.** Track 1a verdicted reality, Track 1b verdicted choices, Track 1c prescribes fixes. T-044 is the first of 6 gap-analysis docs (T-044-T-049).

**Distinct from siblings**:
- T-045 (incomplete implementations): features that exist but are partial.
- T-046 (quant + forecasting): predictor/backtest/calibration-specific gaps.
- T-047 (AI integration): provider/budget/voice-rule gaps.
- T-048 (operational): auth/backup/observability gaps.
- T-049 (summary).

T-044 specifically covers **user-visible features that don't exist at all**.

## 0. Gap matrix at a glance

15 user-facing missing features.

| # | Feature | Effort | MoSCoW |
|---|---------|--------|--------|
| 1 | Performance review screen | L | **Must** |
| 2 | Currency exposure dimension | M | Should |
| 3 | Annual Belgian tax report PDF | L | Should |
| 4 | Predictor leaderboard UI | M | Should |
| 5 | Live mid-price for sizing context | M | **Must** |
| 6 | AI Depth-C "Explain more" surface | M | Could |
| 7 | User-initiated reconciliation trigger | S | Should |
| 8 | Display method setting (FIFO / weighted-avg / specific-lot) | M | Could |
| 9 | Voice-rule deterministic filter (Layer 2) | M | Should |
| 10 | Multi-provider AI fallback (Anthropic → OpenAI) | L | Could |
| 11 | Reynders bond-component recording | M | Should |
| 12 | Speculative classification awareness | L | Should |
| 13 | Foreign-source income summary | M | Should |
| 14 | €1M securities account tax data | S | Won't (v1) |
| 15 | Trading settings full surface (10 of 11 fields) | M | Should |

**Distribution**: 2 Must + 8 Should + 4 Could + 1 Won't. Effort: 1 S + 8 M + 6 L.

## 1. Performance review screen

- **Name**: Portfolio performance review screen (time-weighted return vs benchmark, drawdown, volatility, exposure breakdown, weekly/monthly views).
- **Why it matters**: The user has no way to evaluate "how is my system actually doing over time?". Intent §5 of `portfolio-valuation.md` + doctrine §11 explicitly mandate this screen. Without it, the user makes per-order decisions without performance context. The dashboard surfaces current state; this surfaces history + trend.
- **Where it would live**: New page `apps/web/app/performance/page.tsx` + supporting `apps/web/components/PerformanceReview*.tsx` components + new API surface for time-series aggregates.
- **Effort**: **Large** — requires (a) new aggregation API, (b) charting library adoption (probably Recharts or Chart.js), (c) time-series query patterns over existing `ibkr_position_snapshots` + `ibkr_executions` + `fx_rate_snapshots`.
- **Dependency**: T-021b functional-review reality doc (queued; not started). Per-lot storage (item 15 below) would enable lot-level performance attribution.
- **MoSCoW**: **Must**. The user cannot evaluate the system without it.
- **Originating reality**: T-021 §10.5 (gap surfaced) + T-008 (frontend page inventory — confirmed absent).

## 2. Currency exposure dimension

- **Name**: Per-currency exposure tracking (intent §5 portfolio-valuation: "currency exposure tracked separately and shown on the performance review screen as a first-class dimension").
- **Why it matters**: A portfolio split across EUR + USD + JPY has implicit FX risk. The user has no surface to see "how much of my portfolio is in non-base currency". Belgian Euro-base users can be silently up/down 5-10% on FX drift alone. Intent + doctrine §11 mandate visibility.
- **Where it would live**: Performance review screen (item 1) as a primary dimension, OR a dedicated section on the dashboard portfolio area. New aggregation: SUM(position_value × fx_rate) GROUP BY currency.
- **Effort**: **Medium** — aggregation query is straightforward; UI rendering is a chart + table; FX-rate provenance via existing `fx_rate_snapshots`.
- **Dependency**: Item 1 (performance review screen) likely hosts this dimension.
- **MoSCoW**: Should.
- **Originating reality**: T-021 §10.6.

## 3. Annual Belgian tax report PDF

- **Name**: Annual Belgian tax report (PDF with 7 sections + CSV pack per intent §3 belgian-tax.md).
- **Why it matters**: The user's accountant needs an annual report for filing. Without one, the user manually reconstructs from broker statements + emails. Intent §3 specifies 8 sections (transactions+TOB, dividends+withholding, realised gains, capital gains classification, Reynders disposals, year-end position, foreign-source income, CSV exports). This is the deliverable that converts "the system tracks data" into "the system supports filing tax".
- **Where it would live**: New worker job + API route `POST /reports/annual-tax/{year}/generate` + new `tax_reports` storage table for retained versions. PDF generation requires a new dependency (reportlab or weasyprint per T-022 §8.1 inventory).
- **Effort**: **Large** — PDF generation infra (new dep), 7-section template, CSV pack, retention policy (T-022 §3.5: "previous reports are retained in the audit log, never overwritten"). Section 3 (realised gains) blocked on item 12 below + fx_rate_at_fill (T-021 §10.8).
- **Dependency**: `fx_rate_at_fill` column on `ibkr_executions` (T-021 §10.8 — not in T-044 because it's a schema gap, lives in T-045). Item 11 (Reynders). Item 12 (speculative classification). Item 13 (foreign-source). All five entangled.
- **MoSCoW**: Should — yearly deliverable; high-value for user but seasonal.
- **Originating reality**: T-022 §8 (zero infrastructure documented).

## 4. Predictor leaderboard UI

- **Name**: Predictor leaderboard read-only screen (7 columns: hit rate, average return, Sharpe, max drawdown, calibration status, current ensemble weight, last-backtest score per intent §3 predictor-lifecycle.md).
- **Why it matters**: The user has no way to see "which predictors are actually working?". The backtest API exists (4 routes per T-024 §3); the leaderboard data is computed (inverse-Brier auto-weights). Only the UI is missing. Without it, the operator-facing 4 API routes are inaccessible from the dashboard.
- **Where it would live**: New page `apps/web/app/admin/predictors/page.tsx` (admin-area like reconciliation per T-028) + `apps/web/components/PredictorLeaderboardTable.tsx`. Backend ready: `GET /predictor/leaderboard` exists at `status_routes.py:3704`.
- **Effort**: **Medium** — sortable table with 7 columns + a 3-month / 6-month / 12-month / all-time toggle (intent §3 default 6-month). Drill-down (per intent §3: by asset class / sector / horizon) adds complexity.
- **Dependency**: None for the basic table. Drill-downs would need more API aggregations.
- **MoSCoW**: Should.
- **Originating reality**: T-024 §3 (API exists) + T-024 §10.7 (UI absent).

## 5. Live mid-price for sizing context

- **Name**: Live IBKR mid-price fetch at decision-package composition + action-draft sizing time (intent §4 portfolio-valuation: "Live mid-price (IBKR on-demand)").
- **Why it matters**: Without live mid-price, the system sizes BUY orders using yesterday's close (or older). On a fast-moving market day, the proposed quantity is computed against a stale price; the limit price the order builder writes may be far from the actual mid. The user sees "buy 6 shares of ASML @ €638.72" when ASML actually trades at €655.00 — sizing math is wrong by ~3%.
- **Where it would live**: Worker `apps/worker/src/portfolio_outlook_worker/decision_package/composer.py` would gain an `ibkr_quote_fetcher` injection. API needs a new `GET /ibkr/quote/live/{conid}` route (worker proxy). The IBKR adapter (T-004) supports `reqMktData` already.
- **Effort**: **Medium** — adapter is in place; the wiring through composer + new API route + frontend display is medium. The IBKR-side rate limits + tick-by-tick subscription cost need consideration.
- **Dependency**: None. The IBKR adapter is operational.
- **MoSCoW**: **Must**. Sizing on stale prices is a direct trading-error risk.
- **Originating reality**: T-017 §4 + T-021 §10.9 + T-022 §9.

## 6. AI Depth-C "Explain more" surface

- **Name**: Depth-C AI explanation surface — 2 extra sections beyond Depth-B (intent §1 ai-usage.md: "Alternatives considered and rejected" + "Historical comparison from prediction diary").
- **Why it matters**: Depth-B is the always-on summary; Depth-C is the "tell me more" expansion when the user wants to understand why this action vs alternatives. Without it, the user gets the conclusion but no reasoning depth. Intent §1 mandates both.
- **Where it would live**: New API route `POST /decision-packages/{id}/explain-more` + new prompt template + cache extension to `decision_package_explanations.depth_c_nl`. Frontend: expansion section in `<DecisionPackageDetail>` or `<ForecastExplanationPanel>`.
- **Effort**: **Medium** — second LLM call + cache extension + prompt design + UI section. The infra (AnthropicExplanationProvider) is reusable.
- **Dependency**: Item 9 (voice-rule filter) — if added, applies to Depth-C too. Prediction diary read for the "historical comparison" section already exists (T-016).
- **MoSCoW**: Could.
- **Originating reality**: T-023 §10.2.

## 7. User-initiated reconciliation trigger

- **Name**: On-demand reconciliation trigger button (intent §6 reconciliation.md: "User-initiated reconciliation trigger" in Category 5 settings).
- **Why it matters**: The user has no way to manually trigger a reconciliation run when they suspect drift. Combined with T-035 §1.2 (reconciliation is not APScheduler-wired so it never runs automatically), the only path to ever run Pass A/B/C is via a manual button — which doesn't exist.
- **Where it would live**: New API route `POST /reconciliation/run` invoking `IbkrReconciler.tick()` once. Frontend button on `/admin/reconciliation` page (T-028).
- **Effort**: **Small** — adapter from a synchronous API call to one tick invocation. The `IbkrReconciler` class is already implemented per T-020.
- **Dependency**: This unblocks Pass A/B/C running at all in current production (T-035 §5.2). Companion to T-048's operational fix of wiring the tick to APScheduler.
- **MoSCoW**: Should — partially mitigates the APScheduler-wiring gap.
- **Originating reality**: T-020 §7.7 + T-035 §5.2 (intent §6 trigger missing).

## 8. Display method setting (FIFO / weighted-avg / specific-lot)

- **Name**: Configurable cost-basis display method per intent §2 portfolio-valuation.md (default: weighted average cost; alternatives: FIFO, Specific Lot ID).
- **Why it matters**: The user has no way to choose how cost basis is displayed in the UI. Intent §2 specifies the choice is "a reporting choice, independent of how taxes are computed". Without the setting, the user is locked into whatever the codebase ships (currently aggregate `average_cost`, which is closest to weighted-avg).
- **Where it would live**: Settings UI extension (new field on `/instellingen`) + `UserStrategySettings.cost_basis_display_method` Pydantic field + display logic in `<PortefeuilleRealtimeSection>` / `<PositionPlTraceDetails>`.
- **Effort**: **Medium** — settings field is trivial; FIFO + specific-lot display logic requires the per-lot data (item 15-companion, T-045 territory).
- **Dependency**: Per-lot storage (T-045 territory). Without it, FIFO + specific-lot can't be displayed. Weighted-avg is the only reachable option until per-lot lands.
- **MoSCoW**: Could.
- **Originating reality**: T-021 §10.4.

## 9. Voice-rule deterministic post-generation filter (Layer 2)

- **Name**: Voice-rule Layer 2 — deterministic filter that strips banned phrases (em-dashes, "let me explain", "in essence", etc.) from LLM output (intent §2 ai-usage.md).
- **Why it matters**: Intent §2 mandates 3 voice-rule enforcement layers. Layer 1 (system prompt) is partial (T-023 §1.2 — hard-coded prompt). **Layer 2 + Layer 3 are entirely absent** (T-023 §3 + §10.5). The user's AI explanation gets whatever the LLM produces, including any banned phrase. The reference `docs/intent/voice-rules.md` exists (153 LOC, version 1) but no code reads it at runtime.
- **Where it would live**: New module `apps/api/src/portfolio_outlook_api/voice_filter.py` reading `docs/intent/voice-rules.md` at startup + applying substitutions/strips after `messages.create` returns. Plus Layer 3 schema-validation pass for any remaining patterns.
- **Effort**: **Medium** — file read + regex substitution is small; ensuring the filter catches all locked patterns + integrates with the existing `validate_explanation_output` (T-023 §3) is medium.
- **Dependency**: None. The infra is ready.
- **MoSCoW**: Should — intent §2 is explicit on 3 layers, the codebase implements 1.
- **Originating reality**: T-023 §10.5 + §10.6.

## 10. Multi-provider AI fallback (Anthropic → OpenAI)

- **Name**: Fallback to a second AI provider on Anthropic failure or budget exhaustion (intent §2 ai-usage.md: "Try the fallback provider per doctrine §13.1").
- **Why it matters**: When Anthropic returns an error OR the monthly EUR cap is hit, the user currently sees an empty explanation field (T-023 §10.9 — no Dutch fallback rendered either). With OpenAI as fallback: the explanation surface degrades gracefully. Without fallback: every Anthropic-side hiccup loses AI features for the rest of the month.
- **Where it would live**: New `OpenAIExplanationProvider` symmetric to `AnthropicExplanationProvider` (T-023 §1) + factory logic in `build_explanation_provider` (T-023 §1.1) for fallback chain. `apps/api/pyproject.toml` adds `openai` dependency.
- **Effort**: **Large** — provider implementation, prompt translation (OpenAI takes slightly different system-message shape), separate budget tracking (per intent §4: "per provider"), test coverage with new mock surfaces.
- **Dependency**: Item 9 (voice-rule filter) — applies to whichever provider returns. Independent budget per provider needs schema extension (`claude_ai_budget_usage` is Anthropic-specific; needs `ai_budget_usage` generalisation).
- **MoSCoW**: Could.
- **Originating reality**: T-023 §10.8.

## 11. Reynders bond-component recording

- **Name**: Reynders bond-component recording on every disposal (intent §1 belgian-tax.md: "Reynders bond-component data per disposal").
- **Why it matters**: Belgian Reynders law requires bond-funds + bond-ETFs report their bond-component value on disposal for tax purposes. The accountant needs this data; the system today records nothing about Reynders. Annual report Section 5 (item 3 above) depends on this.
- **Where it would live**: New `reynders_disposals` storage table + ingestion logic on each `ibkr_executions` insert where the instrument is classified as bond-fund/ETF + UI surface in annual report Section 5.
- **Effort**: **Medium** — new table + ingestion + classification logic (which instruments are Reynders-applicable). The classification source itself is doctrine §15 open per intent §7.
- **Dependency**: Instrument classification source (intent §7 open). Without resolving who decides "is this Reynders?", the system can record placeholder + leave determination to the accountant per intent §1 record discipline.
- **MoSCoW**: Should.
- **Originating reality**: T-022 §10.8.

## 12. Speculative classification awareness

- **Name**: Live trade-count + turnover tracking with system-decision item when approaching speculative-classification pattern thresholds (intent §4 belgian-tax.md).
- **Why it matters**: Belgian tax law classifies frequent traders as "speculative" — moving capital gains from tax-free to taxable. The user must know when their activity approaches that threshold. Intent §4 mandates a system-decision item in the actions area: "Activity approaching speculative-classification pattern. Review with accountant."
- **Where it would live**: New worker job aggregating `ibkr_executions` into rolling trade-count + turnover metrics → comparing against thresholds in `trading_settings` (Category 3 — not yet implemented per T-029 §8). System-decision generator → dashboard actions area.
- **Effort**: **Large** — rolling-aggregation infrastructure + thresholds + actions-area UI + system-decision item type. Doctrine §15 open on threshold defaults (intent §7).
- **Dependency**: Category 3 settings infrastructure (T-029 §8). System-decision item generator (none exists in current production per T-028 §8 / T-018).
- **MoSCoW**: Should — single-user low-volume user may never approach the threshold; but the system has no detection so it can't warn.
- **Originating reality**: T-022 §10.9.

## 13. Foreign-source income summary

- **Name**: Annual report Section 7 — per-source-country breakdown of dividends + withholding with treaty-rate notes (intent §3 §7 belgian-tax.md).
- **Why it matters**: Belgian tax residents with foreign-source income can sometimes reclaim foreign withholding via tax treaties. Without per-source-country data, the accountant cannot file the reclaim. Intent §3 §7 mandates the section.
- **Where it would live**: Annual report Section 7 (item 3) + new schema: `dividend_events.source_country`, `dividend_events.treaty_rate`, `dividend_events.withheld_rate`. **The `dividend_events` table itself does not exist** (T-022 §5).
- **Effort**: **Medium** — schema + ingestion + report section. Per T-022 §5 the dividend-event-ingestion path is also absent — adding this feature requires adding dividend events first.
- **Dependency**: Item 3 (annual report PDF infra). Dividend events table (T-045 / T-046 territory — incomplete-implementation gap). `compute_dividend_withholding` exists but is stranded (T-022 §5).
- **MoSCoW**: Should — yearly seasonal value.
- **Originating reality**: T-022 §10.10.

## 14. €1M securities account tax data

- **Name**: Annual securities-account-tax data capture (intent §1 belgian-tax.md record list: "Only relevant if portfolio crosses €1M average; the data is captured regardless so the threshold check is deterministic").
- **Why it matters**: The Belgian "Wertpapiersteuer" (securities account tax) kicks in at €1M average portfolio value. Single-user v1 scope unlikely to cross this. The intent mandates capture regardless for forward-compatibility.
- **Where it would live**: New annual aggregation of average daily portfolio value over the tax year + persistence in `tax_period_snapshots`.
- **Effort**: **Small** — single annual computation + one row per year + one report line. Low LOC.
- **Dependency**: Year-end position snapshot (intent §3 §6 — also absent; T-022 territory).
- **MoSCoW**: **Won't (v1)** — single-user scope unlikely to cross €1M. Intent says "captured regardless" but the trade-off vs other Must items is unfavourable for v1.
- **Originating reality**: T-022 §10.11.

## 15. Trading settings full surface (10 of 11 fields)

- **Name**: Expose the 10 missing `UserStrategySettings` fields in `/instellingen` UI (intent + T-029 §3 listing).
- **Why it matters**: Domain defines 11 user-strategy fields (portfolio_goal, risk_level, asset_mix_preference, preferred_regions, preferred_sectors, avoided_sectors, max_position_pct, min_cash_reserve_pct, currency_preference, prefer_simple_belgian_tax_admin, user_buffer_eur). UI exposes 1 (cashbuffer). The other 10 are locked at domain defaults unless out-of-band SQL changes them. The user has no path to express portfolio risk preference, sector preferences, or position-size caps.
- **Where it would live**: Existing `apps/web/app/instellingen/page.tsx` extension. Backend already supports — `UserStrategySettings` Pydantic + PUT route accept the full payload (T-029 §3).
- **Effort**: **Medium** — 10 new input fields + validation + per-field Dutch help text + frontend form composition. Backend is ready.
- **Dependency**: None. The Pydantic + PUT path are validated end-to-end already.
- **MoSCoW**: Should.
- **Originating reality**: T-029 §3 + §10.2.

## 16. Cross-reference: gap-coverage across Track 1c siblings

Some entries naturally span multiple Track 1c categories. Mapping:

| Gap | Covered fully in T-044 | Cross-ref to | Reason |
|-----|------------------------|--------------|---------|
| Per-lot storage (T-021 §10.1) | No | T-045 | Schema gap, not user-feature gap |
| ADR-0003 7-of-7 predictors (T-024 §10.12) | No | T-046 | Quant infrastructure |
| Shadow-mode infrastructure (T-024 §10.9) | No | T-046 | Quant infrastructure |
| Authentication (T-042 §1) | No | T-048 | Operational/security |
| Backup tooling (T-042 §8) | No | T-048 | Operational/security |
| `fx_rate_at_fill` (T-021 §10.8) | No | T-045 | Schema gap (incomplete) |
| AI Depth-B 6-element structure (T-023 §10.1) | No | T-047 | AI-specific |
| Voice-rule Layers 2 + 3 (T-023 §10.5-§10.6) | Partial (item 9) | T-047 | AI-specific deep dive in T-047 |
| `claude_ai_budget_usage` shared budget (T-023 §10.14) | No | T-047 | AI budget infrastructure |

T-044 stays focused on **user-visible features that aren't there**. The infrastructure / partial / quant / AI / ops gaps belong to T-045-T-048.

## 17. Summary

15 user-facing missing features. Distribution: **2 Must (performance review, live mid-price) + 8 Should + 4 Could + 1 Won't (€1M tax data — v1 scope)**.

The 2 Must items both address direct trading-quality issues:
- **Performance review screen** (item 1): the user cannot evaluate system effectiveness without it.
- **Live mid-price for sizing** (item 5): sizing on stale prices creates direct trading-error risk.

The 8 Should items are intent-mandated features that improve the user's experience without being critical to v1 trading correctness. Most cluster around tax reporting (items 3 + 11 + 12 + 13 — the Belgian tax stack) and operational gaps (items 7 + 9 + 15 — settings + reconciliation + voice).

The 4 Could items are nice-to-haves (Depth-C explanation, display method choice, multi-provider fallback, fine-grained predictor leaderboard).

The 1 Won't is honest about v1 scope (€1M securities tax).

Phase 2 backlog planning should prioritise the 2 Must items first, then cluster the 8 Should items by theme (tax stack vs settings vs reconciliation), then defer Could items.

## 18. References

- T-008 `web-pages.md`, `web-components-status-and-shared.md`, `web-components-feature-grids.md` (frontend page inventory — confirms which features have no UI)
- T-017 `decision-package-composition.md` (live mid-price gap)
- T-018 `action-draft-composition-and-approval.md` (system-decision item generator absence)
- T-020 `ibkr-reconciliation-passes-a-b-c.md` §7.7 (user trigger absent)
- T-021 `portfolio-valuation-and-cost-basis.md` §10.4, §10.5, §10.6, §10.9 (display method, perf review, currency exposure, live mid)
- T-022 `belgian-tax-computation.md` §8, §10.8, §10.9, §10.10, §10.11 (annual report, Reynders, speculative, foreign-source, €1M)
- T-023 `ai-explanation-and-budget.md` §10.2, §10.5, §10.6, §10.8 (Depth-C, voice rules, multi-provider)
- T-024 `predictor-backtest-and-leaderboard.md` §3, §10.7 (backtest API + leaderboard UI gap)
- T-028 `user-acknowledge-manual-review.md` §8 (actions-area gap)
- T-029 `user-edit-trading-settings.md` §3, §10.2 (10-of-11 invisible fields)
- T-035 `system-ibkr-reconciliation-tick.md` §5.2 (user trigger absent)
- T-043 `00-summary.md` (Track 1b synthesis informing Track 1c priorities)
- `docs/intent/ai-usage.md`, `belgian-tax.md`, `portfolio-valuation.md`, `predictor-lifecycle.md`, `reconciliation.md` (locked intents)
- `docs/intent/voice-rules.md` (the unread runtime config — item 9)
