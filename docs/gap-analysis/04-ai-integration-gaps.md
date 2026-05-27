# Gap Analysis 04 — AI Integration Gaps

**Scope.** AI provider / voice rules / budget / explanation surface gaps. Distinct from T-044 (missing AI user surfaces — Depth-C, multi-provider, voice Layer 2), T-045 (incomplete AI implementation — Depth-B paraphrase, eager generation, prompt_version), T-046 (quant gaps), T-048 (operational gaps). Each entry uses the Track 1c 6-part format.

**Dominant gap**: **Case-B `AnthropicTsModelProvider` is wired in production behind 5 feature flags despite intent §5 forbidding it**. Intent: "remove from the ensemble. This is not a mainstream-safe pattern for retail trading. LLMs hallucinate numbers; calibration is unreliable; risk is unbounded."

## 0. Gap matrix at a glance

12 AI-specific gap entries.

| # | Gap | Effort | MoSCoW |
|---|-----|--------|--------|
| 1 | Case-B `AnthropicTsModelProvider` production-path drift | M | **Must** |
| 2 | System prompt hard-coded, not loaded from intent file | S | **Must** |
| 3 | Voice-rule Layer 3 schema-validation absent | M | Should |
| 4 | 80% / 100% budget threshold warnings on system-health line | M | Should |
| 5 | Dutch "AI-uitleg budget bereikt" fallback not rendered | S | **Must** |
| 6 | No budget extension table for grace extensions | S | Should |
| 7 | No idempotent cache-read path (racy re-generation) | S | Should |
| 8 | Shared budget across explanation + Case-B forecast | M | Should |
| 9 | `StubTsModelProvider` Case A/B/C mis-classification | S | Could |
| 10 | `claude_ai_api_key` Pydantic field is presence-gate only (SDK auto-reads from OS env) | S | Should |
| 11 | TOB-net expected return not implemented in suggestion gate | M | Should |
| 12 | No structured JSON schema for Depth-B/C output (AGENTS.md mandate) | M | Should |

**Distribution**: 3 Must + 8 Should + 1 Could. **Effort**: 7 S + 5 M + 0 L. All 3 effort sizes... actually 2 sizes (S + M) — no Large items in T-047 (AI gaps are mostly bounded scope).

## 1. Case-B `AnthropicTsModelProvider` production-path drift

- **Name**: Remove `AnthropicTsModelProvider` from the ts-model factory, OR document the feature-flag-locked Case-C-equivalent rationale.
- **Why it matters**: T-023 §10.11 + T-023 §7.2 documented the most safety-critical AI gap. Intent §5 of `ai-usage.md` is unambiguous: **"Case B — LLM directly producing forecasts. Response: remove from the ensemble. This is not a mainstream-safe pattern for retail trading. LLMs hallucinate numbers; calibration is unreliable; risk is unbounded."** Reality: `apps/api/src/portfolio_outlook_api/anthropic_ts_provider.py:214` `AnthropicTsModelProvider` is wired in via `apps/api/src/portfolio_outlook_api/ai_ts_provider.py:168-256` `build_ts_model_provider`. **Five feature flags** gate it (per T-023 §7.2 default-safe config). Three flag flips activate a Case-B LLM forecaster in production.
- **Why this isn't T-046**: this is AI-specific. T-046 covered the predictor-side ADR-0003 1-of-7 (worker forecasting). T-047 covers the AI-provider quarantine.
- **Where it would live**: `apps/api/src/portfolio_outlook_api/ai_ts_provider.py:214-256` — replace the `if code == "anthropic_claude"` branch with a `TsModelProviderUnavailable(reason="case_b_forbidden")` return. Plus delete `anthropic_ts_provider.py` (or move to `quarantine/` if there's a defensible Phase-4 reactivation path).
- **Effort**: **Medium** — code deletion is small; the surrounding tests + the documentation rationale + the V1.1 Slice 30 lock revisit is medium.
- **Dependency**: None code-wise. Requires intent §5 re-confirmation OR explicit decision to revise intent (e.g., "Case-B permitted with Case-C guardrails: cached output, version-stamped").
- **MoSCoW**: **Must**. Intent §5 is the strongest doctrinal language in the audit ("LLMs hallucinate numbers; risk is unbounded"). Code making the path reachable behind defaults is a latent vulnerability.
- **Originating reality**: T-023 §7.2 + §10.11.

## 2. System prompt hard-coded, not loaded from intent file

- **Name**: Load `SYSTEM_PROMPT_NL` from `docs/intent/ai-explanation-prompt.md` at startup.
- **Why it matters**: Intent §2 Layer 1 of `ai-usage.md`: "The system prompt lives in `docs/intent/ai-explanation-prompt.md`. It carries the voice rules summary, the structural template (the six elements of Depth B, the two extra of Depth C), and the schema requirements." T-023 §1.2 documented the prompt is hard-coded at `anthropic_explanation_provider.py:55-62` — a 6-line Dutch paraphrase request. The intent file (`docs/intent/ai-explanation-prompt.md` — exists, stub v0.1) is **never loaded at runtime**. Operators changing the intent doc cannot affect production behavior.
- **Why this isn't T-045**: T-045 §8 covered "Depth-B is paraphrase not 6-element structure". T-047 §2 covers the orthogonal issue: the prompt source. Both compound but are distinct fixes.
- **Where it would live**: `anthropic_explanation_provider.py:55` — replace the hard-coded constant with `_load_system_prompt()` that reads + caches `docs/intent/ai-explanation-prompt.md` at module load. Plus a startup-time check that the file exists + is non-empty + ends with the expected schema-anchor pattern.
- **Effort**: **Small** — file read + caching + fail-fast startup check.
- **Dependency**: Requires the intent file to be fleshed out to production quality (currently stub v0.1 per T-023 §1.2).
- **MoSCoW**: **Must**. Intent §2 Layer 1 is the prompt-as-data mandate; code-as-prompt makes intent-vs-reality unmaintainable.
- **Originating reality**: T-023 §10.4.

## 3. Voice-rule Layer 3 schema-validation absent

- **Name**: Add Layer 3 schema-validation pass over LLM output for residual banned-pattern detection.
- **Why it matters**: Intent §2 of `ai-usage.md` mandates **three** voice-rule layers: Layer 1 (system prompt — partial per item 2), Layer 2 (deterministic filter — covered in T-044 §9), Layer 3 (schema validator that catches any pattern still present after Layer 2). T-023 §10.6 documented Layer 3 is absent. The existing `validate_explanation_output` (`ai_explanation_guards.py:112-159`) checks hallucinated numbers + disclaimer + length — none of which are voice patterns. Without Layer 3, any banned phrase that survives Layer 2 (or that Layer 2 doesn't recognise) lands in the user-visible output.
- **Why this isn't T-044**: T-044 §9 covered Layer 2 (the deterministic filter). T-047 §3 covers Layer 3 (the final validator). Both layers needed.
- **Where it would live**: `apps/api/src/portfolio_outlook_api/ai_explanation_guards.py` — extend `validate_explanation_output` with a Layer 3 pass that re-applies the voice-rule pattern list + fails the output if any pattern matches. Output drives the fallback-provider path (T-044 §10).
- **Effort**: **Medium** — pattern matcher + schema-validation integration + tests + Dutch error rendering.
- **Dependency**: T-044 §9 (Layer 2 deterministic filter must exist first). T-044 §10 (multi-provider fallback) — Layer 3 failure drives fallback.
- **MoSCoW**: Should.
- **Originating reality**: T-023 §10.6.

## 4. 80% / 100% budget threshold warnings on system-health line

- **Name**: Surface AI budget threshold warnings to the dashboard system-health line.
- **Why it matters**: Intent §4 of `ai-usage.md`: "Approaching-cap warnings: yellow on the dashboard system-health line at 80% of monthly cap consumed. Red at 100%." T-023 §10.7 documented `monthly_budget_status` returns the data (a `BudgetStatus` dataclass with `remaining_eur`) but **no code path reads it and posts to `status_routes.py:/system/status`**. The thresholds are not wired. Operators see budget pressure only via direct SQL query of `claude_ai_budget_usage`.
- **Why this isn't T-048**: this is AI-specific observability, not generic ops observability (which is T-048 territory).
- **Where it would live**: `apps/api/src/portfolio_outlook_api/status_routes.py` — extend `/system/status` response with `ai_budget_status: {percent_consumed, warning_level, dutch_message}`. Plus dashboard system-health rendering with yellow at 80% / red at 100%.
- **Effort**: **Medium** — server-side aggregation + response extension + frontend rendering + Dutch text.
- **Dependency**: None.
- **MoSCoW**: Should — intent §4 is explicit on the threshold values.
- **Originating reality**: T-023 §10.7.

## 5. Dutch "AI-uitleg budget bereikt" fallback not rendered

- **Name**: Render the locked Dutch fallback text when budget is exhausted.
- **Why it matters**: Intent §4 of `ai-usage.md` mandates the exact text: `"AI-uitleg budget bereikt voor deze maand"` + the raw decision-package data (Depth-B's six elements rendered from the structured fields, without LLM rewrite) + a link to Category 1 settings. T-023 §10.9 documented: the string exists ONLY in the intent doc and decision record. **No code path renders it.** Today, when budget is exhausted, the user sees an empty explanation field. The locked Dutch text is the documented graceful-degradation surface; it doesn't exist.
- **Why this isn't T-044**: this is a code-rendering gap, not a missing UI feature (the explanation panel exists; only the budget-exhausted state is missing).
- **Where it would live**: `apps/web/components/ForecastExplanationPanel.tsx` — handle the `result.error === "budget_exceeded"` branch with the locked Dutch text + structured-field fallback rendering. Or: server-side return the fallback already-rendered.
- **Effort**: **Small** — branch on the existing budget-exhausted error + render the locked text + structured fallback. Most of the data (structured DP fields) already flows.
- **Dependency**: None.
- **MoSCoW**: **Must**. The locked Dutch text is part of the user-facing contract; absence means silent failure.
- **Originating reality**: T-023 §10.9.

## 6. No budget extension table for grace extensions

- **Name**: Add `ai_budget_extensions` storage table for grace-extension audit.
- **Why it matters**: Intent §4 of `ai-usage.md`: "Grace extension via Category 1 settings. The user can add a supplemental amount mid-month. The supplemental addition is audit-logged with the user's reason (free-text note)." T-023 §10.10 documented: no `budget_extension` table, no settings field, no audit row format exists.
- **Why this isn't T-044**: T-044 §15 covered settings UI breadth (1 of 11 fields); this is a specific AI-budget audit table that needs to exist before any settings UI can write to it.
- **Where it would live**: New Alembic migration adding `ai_budget_extensions` table with columns: `extension_id, provider_code, budget_month, supplemental_eur, user_reason_nl, applied_at, applied_by`. Plus new API route `POST /settings/ai-budget/extend` with reason validation.
- **Effort**: **Small** — schema + route + tests.
- **Dependency**: T-044 §15 (Trading settings full surface) — natural co-location with Category 1 settings extension.
- **MoSCoW**: Should — audit-discipline matches the codebase's strength elsewhere (T-042 §5 audit-table standard).
- **Originating reality**: T-023 §10.10.

## 7. No idempotent cache-read path

- **Name**: Add idempotent cache-read shortcut to `generate_explanation`.
- **Why it matters**: T-023 §2.3 documented the cache is **write-only on first generation**. Second access to the same DP re-generates instead of short-circuiting. The UNIQUE constraint on `(decision_package_id, content_hash)` catches duplicate writes BUT doesn't prevent the LLM cost — the duplicate write fails AFTER the LLM call already happened. Racy: two concurrent reads of the same DP both call the LLM, both attempt insert, one wins, one wastes a paid LLM call.
- **Why this isn't T-045**: T-045 §9 covered "eager-not-lazy" generation. T-047 §7 covers the cache-read-shortcut for any lazy path. Both compound.
- **Where it would live**: `ai_explanation_sync.py` — wrap `generate_explanation` with a cache-read attempt first: `if repo.get_decision_package_explanation(dp_id, content_hash) is not None: return cached`. Only proceed to LLM call on cache miss.
- **Effort**: **Small** — cache-read lookup + branch.
- **Dependency**: T-045 §9 (lazy generation) — both items compound. Either alone is partial; both together eliminate redundant LLM cost.
- **MoSCoW**: Should — operational cost optimisation.
- **Originating reality**: T-023 §10.13.

## 8. Shared budget across explanation + Case-B forecast

- **Name**: Split `claude_ai_budget_usage` into per-purpose budgets (explanation vs ts_forecast).
- **Why it matters**: T-023 §10.14 documented: `claude_ai_budget_usage` lumps both explanation calls and `anthropic_ts_provider` forecast calls into the same monthly cap. Intent §4 says "per provider"; reality is "per Anthropic Claude API account, lumped across purposes". A Case-B forecast spike (item 1) would silently exhaust the explanation budget. Per-purpose split is cleaner accounting.
- **Why this isn't T-046**: this is AI-budget infrastructure, not quant.
- **Where it would live**: `claude_ai_budget_usage.call_kind` column already exists; the budget gate at `claude_ai_budget.py:122` `assert_budget_available` just needs to filter by `call_kind` and apply per-purpose caps. New `claude_ai_budget_monthly_eur_explanation` + `claude_ai_budget_monthly_eur_ts_forecast` settings.
- **Effort**: **Medium** — settings extension + gate-filter update + tests.
- **Dependency**: Item 1 (Case-B removal) would moot this — if `anthropic_ts_provider` is removed per intent §5, there's only explanation usage to budget. If Case-B is kept feature-flagged: this becomes important.
- **MoSCoW**: Should — depends on item 1 decision.
- **Originating reality**: T-023 §10.14.

## 9. `StubTsModelProvider` Case A/B/C mis-classification

- **Name**: Re-classify `StubTsModelProvider` per intent §5 framework (neither Case A nor B nor C).
- **Why it matters**: T-023 §10.15 documented: T-005 originally classified `StubTsModelProvider` (`apps/api/src/portfolio_outlook_api/ai_ts_provider.py:58-165`) as Case A ("classical ML model labelled 'AI'"). T-023 §7.1 re-classification revealed it's actually a **pure-Python empirical-quantile drift model** using log-returns + lognormal distribution. Not classical ML. Not LLM. Not Case A, B, or C. The "AI" naming is misleading.
- **Why this isn't T-046**: this is an AI-naming/doctrine gap, not a predictor-functionality gap.
- **Where it would live**: Rename `ai_ts_provider.py` + `StubTsModelProvider` to remove the "AI" suffix. Update intent §5 to either (a) add a Case A.1 for "pure-math predictor named AI" or (b) confirm Case A rename per intent §5 ("Response: rename.").
- **Effort**: **Small** — module rename + class rename + grep-and-replace + tests + intent §5 clarification.
- **Dependency**: Intent §5 clarification.
- **MoSCoW**: Could — naming hygiene; doesn't affect runtime.
- **Originating reality**: T-023 §10.15.

## 10. `claude_ai_api_key` Pydantic field is presence-gate only

- **Name**: Migrate Anthropic SDK initialisation to consume the Pydantic `claude_ai_api_key` field directly.
- **Why it matters**: T-023 §1.1 + T-061 §3 documented the divergence: `Anthropic()` SDK at `anthropic_explanation_provider.py:219` reads `ANTHROPIC_API_KEY` from the OS env directly. The Pydantic `claude_ai_api_key` field at `config.py:188` is a **presence-gate only** — it confirms the env var was set, but the SDK separately reads the raw env. If a future refactor wraps the field in `SecretStr` for masking (T-048 §4 territory), the SDK still sees the raw env. The Pydantic typed config is decorative.
- **Why this isn't T-048**: this is AI-provider-specific (Anthropic SDK behavior). T-048 §4 covers the broader SecretStr migration.
- **Where it would live**: `anthropic_explanation_provider.py:219` — instead of `Anthropic()`, use `Anthropic(api_key=settings.claude_ai_api_key)` explicitly. Same for `anthropic_ts_provider.py:215` if Case B is retained per item 1.
- **Effort**: **Small** — single line change per provider + tests.
- **Dependency**: T-048 §4 (SecretStr) — both touch the same config field. Order: do this first, then SecretStr-wrap.
- **MoSCoW**: Should — closes the typed-config-vs-raw-env-divergence.
- **Originating reality**: T-023 §1.1 + T-061 §3.

## 11. TOB-net expected return not implemented

- **Name**: Subtract `estimated_belgian_tob` from `ensemble_expected_return_pct` in the suggestion gate.
- **Why it matters**: Intent §4 of `belgian-tax.md`: "TOB-aware suggestions. The expected return from a suggestion is computed **net of expected TOB**. A trade with a negative net expected return after TOB is not suggested." T-022 §9.3 documented this is NOT implemented. The `repository_contracts.py:2199-2200` comment is explicit: "Informational on the draft; the TOB does not change order sizing." Per-trade TOB is computed (`compute_tob` at `belgian_tax.py:91`) + displayed (T-022 §4.2) but never subtracted from expected return.
- **Why this isn't T-046**: this is the tax↔AI/predictor integration boundary. The suggestion gate uses ensemble forecasts (T-046 territory) and tax (T-022 territory); the missing integration is the gate logic.
- **Where it would live**: `packages/portfolio/src/portfolio_outlook_portfolio/action_draft_safety.py:438` — extend `compute_orderimpact` to compute `net_expected_return_pct = ensemble_expected_return_pct - (estimated_belgian_tob / order_value)`. Then the suggestion gate filters on `net_expected_return_pct > threshold`.
- **Effort**: **Medium** — math integration + threshold definition (intent doesn't specify; needs decision) + test cases for negative-net-return scenarios.
- **Dependency**: T-046 §1 (ADR-0003 ensemble closure) — the multi-predictor ensemble produces more sensitive expected returns; with single-predictor reality, this gap is dormant. Item is more impactful post-ADR-0003.
- **MoSCoW**: Should — intent §4 explicit; gate-level fix.
- **Originating reality**: T-022 §9.3.

## 12. No structured JSON schema for Depth-B/C output

- **Name**: Define + enforce a Pydantic schema for LLM-generated explanation output.
- **Why it matters**: AGENTS.md mandates: "Every AI output must be schema-validated." Today, the LLM output is **free-form Dutch text** (per T-023 §1.5: `_extract_output_text` concatenates content blocks into a single string). The `validate_explanation_output` function checks 3 free-form properties (hallucinated numbers, disclaimer presence, length) but not structure. There's no Pydantic model for "the LLM should produce 6 named sections corresponding to Depth-B intent §1". AGENTS.md mandate is at best partially satisfied.
- **Why this isn't T-045**: T-045 §8 covered "Depth-B prompt asks for 2-3 sentences not 6 elements". T-047 §12 covers the schema-as-data structure. Fix order: first restructure prompt (T-045 §8), then define schema (T-047 §12).
- **Where it would live**: New Pydantic model `ExplanationDepthB` (6 fields per intent §1) + `ExplanationDepthC` (8 fields). Anthropic SDK tool-use mode (already used by `anthropic_ts_provider.py:214` for structured forecasts) can drive structured output. Schema validation runs in `validate_explanation_output`.
- **Effort**: **Medium** — schema design + prompt update to request JSON shape + tool-use integration + tests. Couples with prompt-restructuring (T-045 §8).
- **Dependency**: T-045 §8 (Depth-B prompt restructure) is the prerequisite. Sequencing: prompt → schema → validation.
- **MoSCoW**: Should — AGENTS.md mandate compliance.
- **Originating reality**: T-023 §1.5 + AGENTS.md mandate cross-ref.

## 13. Cross-reference: gap coverage across Track 1c siblings

| Gap | Covered in T-047 | Cross-ref to | Reason |
|-----|------------------|--------------|--------|
| AI Depth-B 6-element structure (T-023 §10.1) | No | T-045 §8 | Incomplete-implementation |
| AI Depth-C "Explain more" UI (T-023 §10.2) | No | T-044 §6 | Missing user feature |
| Eager AI explanation generation (T-023 §10.3) | No | T-045 §9 | Incomplete-implementation |
| `prompt_version` on cache (T-023 §10.12) | No | T-045 §10 | Schema gap |
| Voice-rule Layer 2 deterministic filter (T-023 §10.5) | No | T-044 §9 | Missing user-facing feature surface |
| Multi-provider AI fallback (T-023 §10.8) | No | T-044 §10 | Missing user feature |
| Authentication on AI routes (no specific finding but implicit) | No | T-048 | Operational |
| AI explanation budget hard-stop visibility (T-023 §4.2) | Item 4 (partially) | T-048 | Observability overlap |
| `AnthropicTsModelProvider` quarantine (T-023 §7.2) | **Item 1 — covered fully** | (none) | Core T-047 territory |
| Hard-coded prompt source (T-023 §10.4) | **Item 2 — covered fully** | (none) | Core T-047 territory |

## 14. Summary

12 AI-specific gap entries. **Distribution**: 3 Must + 8 Should + 1 Could. Items: 7 Small + 5 Medium + 0 Large — AI gaps are mostly bounded in scope (single provider + finite intent surface).

The 3 Musts:

- **Item 1**: Case-B `AnthropicTsModelProvider` quarantine. Intent §5 is unambiguous ("LLMs hallucinate numbers; risk is unbounded"); code makes the path reachable behind 3-flag flips. The most safety-critical AI gap.
- **Item 2**: System prompt from intent file. Code-as-prompt makes intent-vs-reality unmaintainable; intent §2 Layer 1 mandates file-based source.
- **Item 5**: Dutch "budget bereikt" fallback. Locked user-facing text not rendered means silent failure on budget exhaustion. Small effort, locked-text-mandate compliance.

The 8 Shoulds cluster around AI observability + voice-rule completion + budget infrastructure. Item 8 (per-purpose budget) is contingent on item 1's decision.

The 1 Could is naming hygiene (item 9 — `StubTsModelProvider` Case A/B/C re-classification).

**Total AI-integration work bounded**: no Large items. Item 1 (the safety-critical one) is Medium effort. Items 2 + 5 are Small. Combined Must-work: ~M+S+S = manageable single-PR scope. Phase 2 sequencing: items 2 + 5 (low-effort wins) → item 1 (safety-critical decision required) → 3-12 in MoSCoW order.

## 15. References

- T-022 `belgian-tax-computation.md` §9.3 (TOB-net expected return — item 11)
- T-023 `ai-explanation-and-budget.md` (T-047's primary source — 15 findings; 12 map to T-047, 3 cross-referenced to T-044/T-045)
- T-029 `user-edit-trading-settings.md` (Category 1 settings UI for item 6)
- T-040 `05-testing-and-ci.md` §2 (1% mock ratio; AI provider tests are appropriately mock-driven)
- T-042 `07-security-observability-ops.md` §4 (SecretStr cross-ref for item 10)
- T-044 §6, §9, §10 (cross-references)
- T-045 §8-§10 (cross-references)
- T-046 §14 (cross-reference)
- T-061 `settings-and-credentials-infrastructure.md` §3 (Anthropic SDK auto-read — item 10)
- `docs/intent/ai-usage.md` (the primary intent — §1 Depth B/C, §2 voice layers, §4 budget thresholds, §5 Case A/B/C)
- `docs/intent/ai-explanation-prompt.md` (the un-loaded prompt source — item 2)
- `docs/intent/voice-rules.md` (the un-loaded patterns — items 3 + T-044 §9 cross-ref)
- AGENTS.md (schema-validation mandate — item 12)
- `apps/api/src/portfolio_outlook_api/anthropic_ts_provider.py:214` (Case-B provider — item 1)
- `apps/api/src/portfolio_outlook_api/ai_ts_provider.py:168-256` (the factory that wires Case-B — item 1)
- `apps/api/src/portfolio_outlook_api/anthropic_explanation_provider.py:55-62, :219` (hard-coded prompt + SDK init — items 2 + 10)
- `apps/api/src/portfolio_outlook_api/claude_ai_budget.py:101-187` (budget module + threshold data — items 4 + 8)
