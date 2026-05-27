# AI Explanation + Per-Provider Budget — From Intent to a 2-Sentence Paraphrase

**Scope.** End-to-end trace of the LLM explanation surface — from the Anthropic Claude provider call, through the per-month EUR budget gate (`assert_budget_available` → `messages.create` → `persist_call_cost`), to the `decision_package_explanations` cache table, the validation guards, and the Dutch-rendered output. Plus the AI-in-forecasting Case A/B/C re-classification: the explanation provider is Case C-shaped but not Case-C-compliant; `anthropic_ts_provider` is wired in as a feature-flagged Case-B LLM forecaster (which intent §5 explicitly forbids).

**Intent**: `docs/intent/ai-usage.md` (locked 2026-05-26). **Decision**: `docs/decisions/0013-ai-usage-architecture.md`. **Component reality**: T-006 `docs/reality/components/api-infrastructure-and-ai.md` (the Anthropic provider + monthly EUR budget cap), T-005 `docs/reality/components/api-actions-suggestions-and-watchlists.md` (the `anthropic_ts_provider` Case-B finding + `ai_ts_provider` stub), T-061 `docs/reality/components/settings-and-credentials-infrastructure.md` §3 (the `ANTHROPIC_API_KEY` auto-read pathway). **Sibling**: T-015 `docs/reality/workflows/forecast-generation-and-labelling.md` (where Case-B would feed if enabled).

## 0. TL;DR

| Intent locked behaviour | Reality | Status |
|-------------------------|---------|--------|
| Depth B = 6 structured elements | Hard-coded prompt asks for "twee tot drie zinnen" (2-3 sentences) Dutch paraphrase | **Gap §10.1** |
| Depth C = 2 extra elements ("Explain more") | Not implemented — no second prompt | **Gap §10.2** |
| Lazy-generated on first explanation-icon click | Eager-generated during Decision Package composition (no standalone explanation route) | **Gap §10.3** |
| Cached against `decision_package_id` | Cache table `decision_package_explanations` exists (migration `0034`); UNIQUE on `(decision_package_id, content_hash)` | **Shipped** |
| System prompt loaded from `docs/intent/ai-explanation-prompt.md` (intent §2 Layer 1) | Hard-coded inline at `anthropic_explanation_provider.py:55-62` | **Gap §10.4** |
| Voice-rule deterministic filter (intent §2 Layer 2) | Not implemented — `docs/intent/voice-rules.md` exists but no runtime reader | **Gap §10.5** |
| Voice-rule schema-validation pass (intent §2 Layer 3) | Not implemented — existing validator checks hallucinated numbers + disclaimer + length only | **Gap §10.6** |
| Per-provider monthly EUR cap | `claude_ai_budget_monthly_eur = €50` default; `assert_budget_available` hard-stop | **Shipped** |
| 80% yellow / 100% red on system-health line | Not implemented | **Gap §10.7** |
| Multi-provider fallback (Anthropic → OpenAI) | Not implemented — single provider only | **Gap §10.8** |
| `"AI-uitleg budget bereikt voor deze maand"` Dutch fallback | Not implemented — string exists only in intent doc | **Gap §10.9** |
| Grace-extension audit log | Not implemented — no `budget_extension` table | **Gap §10.10** |
| AI-in-forecasting Case B "remove from ensemble" | `anthropic_ts_provider` wired into production behind 5 feature flags (defaults safe) | **Active drift §10.11** |
| Case C guardrail: prompt-version stored on cache | Cache row has `generated_at` but NO `prompt_version` column | **Gap §10.12** |

**Net summary**: the budget gate is shipped and rigorous; the cache is shipped; the explanation **content** is a stripped-down paraphrase that does not match the intent's 6-element structure; the voice-rule layers 2 + 3 are absent; the Case-B LLM forecaster has a code path despite being intent-forbidden.

## 1. The single LLM explanation provider — `AnthropicExplanationProvider`

**Module**: `apps/api/src/portfolio_outlook_api/anthropic_explanation_provider.py`. Class `AnthropicExplanationProvider` at `:182`. The only LLM call site for the explanation surface.

### 1.1 SDK instantiation (`:219`)

```python
from anthropic import Anthropic
return cast(_AnthropicClientProtocol, Anthropic())
```

`Anthropic()` reads `ANTHROPIC_API_KEY` directly from the OS environment — **not** from the Pydantic `claude_ai_api_key` field. T-061 §3 already documented this: the Pydantic field is a presence-gate only. If `claude_ai_api_key` is set in the Pydantic config but the OS env `ANTHROPIC_API_KEY` is not exported, the call would fail at runtime even though the readiness gate reports green.

### 1.2 The hard-coded Dutch system prompt (`:55-62`)

```python
SYSTEM_PROMPT_NL = (
    "Je bent een paraphrase-assistent voor een Nederlandstalig "
    "trading-dashboard. Vat het Decision Package samen in twee tot drie "
    "zinnen. Bevat de samenvatting geen nieuwe getallen die niet in de "
    "input voorkomen. Geen advies. Geen oordeel over koersrichting. "
    "Sluit altijd af met de wettelijke disclaimer die in de input wordt "
    "meegegeven."
)
```

(Translation: "You are a paraphrase-assistant for a Dutch-language trading dashboard. Summarize the Decision Package in two to three sentences. The summary contains no new numbers that aren't in the input. No advice. No judgment on price direction. Always end with the legal disclaimer provided in the input.")

**Note the gap**: the prompt asks for a 2-3 sentence paraphrase, NOT the 6-element structured output mandated by intent §1 Depth B (why this action, predictor contributions, ensemble confidence, sizing layer, limit price logic, risk context). What ships is a much narrower "rewrite the DP fields into Dutch prose" rather than the intent's "structured explanation with 6 sections". §10.1.

### 1.3 Default model

`DEFAULT_MODEL_NAME = "claude-haiku-4-5-20251001"` (`:52`). Configurable via `claude_ai_explanation_model` Pydantic field (default same; `config.py:187`).

### 1.4 The `messages.create` call (`:238`)

```python
message = client.messages.create(**payload)
```

`payload` is built earlier in `generate(...)` with the system prompt at `:55-62`, the model name, max_tokens, and the user message (the Decision Package fields).

### 1.5 Output extraction (`:122-130`)

Free-form text concatenation from the message content blocks:

```python
def _extract_output_text(message: _AnthropicMessageProtocol) -> str:
    parts: list[str] = []
    for block in message.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts)
```

**The output is unstructured Dutch text — not a Pydantic-validated JSON schema with the 6+2 Depth-B/C fields**. AGENTS.md "Every AI output must be schema-validated" doctrine is not satisfied for the explanation surface (the existing validator §3 checks free-form properties, not the 6-element structure). §10.6.

## 2. The orchestrator — `generate_explanation` in `ai_explanation_sync.py`

**Module**: `apps/api/src/portfolio_outlook_api/ai_explanation_sync.py`. Function `generate_explanation(...)` at `:188`.

### 2.1 No standalone API route

Grep across `apps/api/src/portfolio_outlook_api/` for `@router.get|@router.post` paths matching `/ai/explanation`, `/explanation/generate`, `/decision-package/.*/explanation` returns **zero matches**. The explanation surface has no dedicated endpoint.

`generate_explanation` is invoked **during Decision Package composition** — i.e., the explanation is written at DP-compose time, not lazily on user-click. Intent §1 says:

> "Depth B is lazy-generated (on first explanation-icon click — see `docs/intent/decision-package.md` §5) and cached against `decision_package_id`."

Reality is **eager** generation. This means every composed Decision Package eats budget at compose time, regardless of whether the user ever clicks the icon. §10.3.

### 2.2 Cache write (`:278`)

```python
repo.save_decision_package_explanation(explanation)
```

Repository: `SqlAlchemyDecisionPackageExplanationRepository` at `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:2712`. Writes one row per (DP id, content hash) pair to the `decision_package_explanations` table.

### 2.3 No idempotent cache-read path

Per the agent's inventory: there is no production code path that calls `repo.get_decision_package_explanation(decision_package_id)` to short-circuit before generating. The cache is **write-only on first generation**. A second access — if there were a route — would re-generate and conflict with the UNIQUE constraint on `(decision_package_id, content_hash)`. The pattern protects against duplicate writes but not against duplicate cost. §10.13.

## 3. Validation guards — what's checked vs intent §2 Layer 3

`validate_explanation_output(...)` lives in `ai_explanation_guards.py` (lines 112-159 per the agent's inventory). The current checks:

| Check | Implemented? | Maps to intent? |
|-------|--------------|------------------|
| Hallucinated numbers (digits not in source DP) | **Yes** | Doctrine §13 — schema-validated output |
| Disclaimer present | **Yes** | Intent §2 Layer 1 (system prompt mandate) |
| Length bounds | **Yes** | Intent §2 Layer 2 ("Length and paragraph bounds enforced") |
| Banned phrases stripped (em-dashes, "in essence", "let me explain", etc.) | **No** — intent §2 Layer 2 mandate but no implementation | §10.5 |
| Voice-validation schema pass (intent §2 Layer 3) | **No** — only the three checks above run | §10.6 |
| Em-dash normalisation (intent §3 banned-pattern table) | **No** — `voice-rules.md` is not read at runtime | §10.5 |

The length-bound check overlaps with intent §2 Layer 2 but doesn't satisfy the rest of it. The banned-phrase list in `docs/intent/voice-rules.md` (153 lines, version 1, locked 2026-05-26) is referenced by intent but has no runtime reader. The file is there; the code is not.

## 4. The budget gate — `claude_ai_budget.py`

**Module**: `apps/api/src/portfolio_outlook_api/claude_ai_budget.py` (187 LOC). Standalone — same module used by both the explanation provider and `anthropic_ts_provider` (§7.2).

### 4.1 Storage — `claude_ai_budget_usage` table (migration `0043`)

`packages/storage/alembic/versions/0043_claude_ai_budget_usage.py:22-48`. Columns:

| Column | Type | Notes |
|--------|------|-------|
| `usage_id` | PK | autoincrement |
| `budget_month` | Text | `YYYY-MM` string for monthly bucket |
| `provider_code` | Text | always `"anthropic_claude"` today |
| `model_name` | Text | `claude-haiku-4-5-...` etc. |
| `called_at` | DateTime tz | wall-clock call timestamp |
| `input_units` | Numeric | input tokens charged at full rate |
| `cached_input_units` | Numeric | input tokens read from cache (cheaper) |
| `output_units` | Numeric | output tokens |
| `cost_eur` | Numeric | computed EUR cost for this call |
| `call_kind` | Text | `"explanation"` or `"ts_forecast"` |
| `explanation_nl` | Text | optional excerpt of the output for audit |

### 4.2 Hard-stop gate — `assert_budget_available` (`:122`)

```python
def assert_budget_available(...):
    status = monthly_budget_status(...)
    if status.remaining_eur <= Decimal("0"):
        raise ClaudeAiBudgetExceededError(...)
```

Called from `anthropic_explanation_provider.py:228` (the agent confirmed) **before** each `messages.create`. A `ClaudeAiBudgetExceededError` raised here aborts the call before any token cost is incurred.

### 4.3 Per-call cost recording — `persist_call_cost` (`:142`)

Called from `anthropic_explanation_provider.py:252` (the agent confirmed) **after** a successful response. Computes EUR from `input_tokens / cached_input_tokens / output_tokens` × the model's per-token rates (locked in the module).

### 4.4 The default cap — €50/month

`config.py:182`: `claude_ai_budget_monthly_eur: Decimal = Decimal("50")`. This is the **per-provider** cap per intent §4 — but since the only configured provider is Anthropic and `claude_ai_budget_usage.call_kind` lumps `"explanation"` + `"ts_forecast"` into the same monthly total, the cap is in practice **per-purpose-shared**, not per-provider. A spike in Case-B forecast usage would block explanation generation. §10.14.

### 4.5 What's NOT there — the 80% / 100% surface

Intent §4 mandates:

> "Approaching-cap warnings: yellow on the dashboard system-health line at 80% of monthly cap consumed. Red at 100%."

`monthly_budget_status(...)` (`:101`) returns a `BudgetStatus` dataclass with `remaining_eur` — but no code path reads this and posts it to `status_routes.py:/system/status` (the system-health surface, per T-006). The thresholds are not wired. §10.7.

Also missing: the Dutch "AI-uitleg budget bereikt voor deze maand" text intent §4 mandates. The string exists only in the intent doc (line 96) and the decision record (line 26); no module renders it as a fallback when `ClaudeAiBudgetExceededError` is caught. §10.9.

## 5. The cache table — `decision_package_explanations`

**Migration**: `packages/storage/alembic/versions/0034_decision_package_explanations.py:18-64`. Created 2026-05-29.

### 5.1 Columns

| Column | Notes |
|--------|-------|
| `explanation_id` | PK |
| `decision_package_id` | FK to `decision_packages` |
| `decision_package_content_hash` | SHA-256 of the source DP — part of UNIQUE constraint |
| `explanation_nl` | the generated Dutch text |
| `output_text_hash` | content-addressed hash of the output for audit |
| `status` | enum: `generated` / `blocked` / `failed` (per `ai_explanation_guards.py:32-35`) |
| `generated_at` | DateTime tz |
| `provider_code` | `"anthropic_claude"` etc. |
| `model_name` | the SDK model identifier |
| `input_tokens / output_tokens / cached_input_tokens` | per-call usage breakout |
| `cost_eur` | per-call EUR cost (duplicated from `claude_ai_budget_usage` for join-free reads) |

### 5.2 UNIQUE constraint

`(decision_package_id, decision_package_content_hash)` (line 59 of the migration). Idempotency: if the DP is rebuilt (content hash changes), a new explanation row may be inserted; if the DP is unchanged, re-generation conflicts with the constraint and the duplicate write fails.

### 5.3 The missing `prompt_version`

Intent §5 Case C guardrail #1 mandates:

> "Cached / snapshotted output. The feature value is stored with its timestamp and the prompt version that produced it. Reproducibility is guaranteed."

The cache row has `generated_at` but **no `prompt_version` column**. A future prompt-text change cannot be distinguished from earlier rows by reading the row. To reproduce the call, the operator would need to git-blame `anthropic_explanation_provider.py:55-62` at the row's `generated_at`. §10.12.

## 6. The frontend explanation surface

`apps/web/components/ForecastExplanationPanel.tsx:1` — the component that renders explanation text. Per the agent's findings:

- `apiClient.getForecastLatest(conid)` at `:69` — reads the latest forecast (not the explanation directly).
- `apiClient.getLatestDecisionPackage({ conid })` at `:80` — reads the latest DP, which carries the explanation inline (eager-generated; §2.1).
- The Dutch "AI-uitleg budget bereikt voor deze maand" fallback text from intent §4 is **NOT rendered** anywhere in the component or `apiClient.ts`. Budget exhaustion would surface as an empty explanation field, not the locked Dutch error string. §10.9.

No second prompt for Depth C ("Explain more") exists. The intent-§1 Depth-C surface is absent in the UI. §10.2.

## 7. The AI-in-forecasting Case A/B/C re-classification

Intent §5 mandates three pre-decided responses for AI in forecasting:

> "**Case A** — classical ML model labelled 'AI' → **rename**.
> **Case B** — LLM directly producing forecasts → **remove from the ensemble.**
> **Case C** — LLM produces features that a deterministic forecaster consumes → **permit with three guardrails.**"

### 7.1 The three known AI provider sites

| Site | File | Intent classification | Reality status |
|------|------|------------------------|----------------|
| `AnthropicExplanationProvider` | `anthropic_explanation_provider.py:182` | Case C-shaped (LLM produces output consumed by user, not by forecast ensemble) | Case-C guardrail #1 violated (no `prompt_version`); Case C guardrail #2 satisfied (not a forecast); §10.12 |
| `AnthropicTsModelProvider` | `anthropic_ts_provider.py:214` | **Case B** — LLM directly producing forecasts (p10/p50/p90 quantiles + `prob_gain` + `confidence_score`) | **Wired in behind 5 feature flags, defaults safe but code path exists** — §10.11 |
| `StubTsModelProvider` | `ai_ts_provider.py:58` | T-005 flagged as Case A; agent re-classifies as pure-Python empirical-quantile drift model (NOT classical ML) | **Re-classification needed** — neither Case A nor case B/C; pure deterministic math labelled as "AI". §10.15 |

### 7.2 The Case-B production path — `anthropic_ts_provider.py`

`ai_ts_provider.py:168-256` is the factory `build_ts_model_provider`. The decision tree:

```text
not ai_ts_predictor_enabled                          → TsModelProviderUnavailable("ai_ts_predictor_disabled")
ai_ts_predictor_provider_code == "stub"              → StubTsModelProvider (pure-Python; §7.1)
not ai_ts_predictor_real_client_enabled              → TsModelProviderUnavailable("real_client_not_enabled")
provider_code == "anthropic_claude" AND ALL 4:
  - claude_ai_api_key present (:215)
  - budget_repo supplied (:225)
  - ai_ts_predictor_daily_only=False OR invoked_from_scheduler=True (:234-237)
→ AnthropicTsModelProvider (LLM forecast — Case B)
```

**The defaults** (`config.py:169-176`):
- `ai_ts_predictor_enabled = False`
- `ai_ts_predictor_real_client_enabled = False`
- `ai_ts_predictor_provider_code = "stub"`
- `ai_ts_predictor_daily_only = True`

So in a fresh deploy, the Case-B path is unreachable. **But the path exists.** Intent §5 Case B is unambiguous: "remove from the ensemble. This is not a mainstream-safe pattern for retail trading. LLMs hallucinate numbers; calibration is unreliable; risk is unbounded."

T-023 surfaces this as a doctrine drift: an operator who flips three settings (`ai_ts_predictor_enabled=true`, `ai_ts_predictor_real_client_enabled=true`, `ai_ts_predictor_provider_code=anthropic_claude`) gets a working LLM forecaster wired into the ensemble. The daily-only flag (`ai_ts_predictor_daily_only=True` default) reduces the surface to once-per-day from the scheduler — but does not remove the path. §10.11.

### 7.3 Shared budget across explanation + Case-B forecast

Both `AnthropicExplanationProvider` (§1) and `AnthropicTsModelProvider` (§7.2) call into the same `claude_ai_budget` module (§4). `call_kind` differentiates them in the audit table — `"explanation"` vs `"ts_forecast"` — but the **monthly cap is shared**. A budget exhaustion caused by Case-B forecast calls would block all subsequent explanation calls in the same month, with no graceful degradation. §10.14.

## 8. End-to-end timeline — eager explanation generation

| t | Site | Event |
|---|------|-------|
| 0 | worker decision-package composer | DP composed with all 5 gates passed (T-017) |
| 0+ε | composer calls API route or directly invokes `generate_explanation` | (this transit is intra-process if same Python interpreter; HTTP if cross-process; not yet documented end-to-end) |
| 0+ε | `ai_explanation_sync.py:188` `generate_explanation` | orchestrator entered |
| 0+ε | `claude_ai_budget.assert_budget_available` (called from `:228` of explanation provider) | budget check; raises `ClaudeAiBudgetExceededError` if exhausted |
| 0+ε | `anthropic_explanation_provider.py:182` `AnthropicExplanationProvider.generate` | provider invoked |
| 0+ε | `Anthropic()` SDK instantiated (`:219`) | reads `ANTHROPIC_API_KEY` from OS env |
| 0+ε | `messages.create(...)` (`:238`) | LLM call; SYSTEM_PROMPT_NL + DP user message |
| 0+ε | `_extract_output_text` (`:122`) | free-form Dutch text extracted |
| 0+ε | `validate_explanation_output` (`ai_explanation_guards.py:112`) | 3 checks (hallucinated numbers / disclaimer / length); voice not checked |
| 0+ε | `persist_call_cost` (`claude_ai_budget.py:142`) | `claude_ai_budget_usage` row written |
| 0+ε | `repo.save_decision_package_explanation` (`ai_explanation_sync.py:278`) | `decision_package_explanations` row written |
| 0+ε | DP composer continues with `explanation_nl` field populated | DP row persisted |
| later | user clicks explanation icon on `/portefeuille` | `<ForecastExplanationPanel>` reads DP; renders `explanation_nl` directly (no second LLM call) |

There is **no Depth-C "Explain more"** path. The user sees only the pre-generated Depth-B (actually 2-3 sentence paraphrase) text.

## 9. Failure paths

1. **Budget exhausted** → `ClaudeAiBudgetExceededError` from `assert_budget_available`. DP composition catches it; the DP is persisted with `explanation_nl=NULL` or a placeholder. **No Dutch "AI-uitleg budget bereikt" string is rendered** (§10.9).
2. **`ANTHROPIC_API_KEY` env-var missing despite Pydantic field set** → the `Anthropic()` constructor raises at `:219`. The error surface is the SDK's exception, not a localized Dutch message.
3. **Provider returns banned phrase** → no detection; the banned phrase is rendered to the user. §10.5.
4. **Provider hallucinates a number** → `validate_explanation_output` catches it (one of the 3 checks); the explanation is rejected with status `"blocked"`; cached as such. The user sees the placeholder.
5. **Provider returns over the length bound** → caught by the length check; same treatment as #4.
6. **`AnthropicTsModelProvider` produces a calibration-bad p50** → no detection; the LLM forecast is fed into the ensemble. (Defaults make this unreachable; §7.2.)

## 10. Phase 1c surface (15 findings)

1. **Depth B ≠ 6 structured elements** — intent §1 mandates 6 sections (why, predictors, ensemble confidence, sizing layer, limit price, risk context). Reality: the SYSTEM_PROMPT_NL at `anthropic_explanation_provider.py:55-62` asks for a "twee tot drie zinnen" (2-3 sentences) paraphrase. The output is free-form Dutch text, not a 6-element structured response.
2. **Depth C "Explain more" surface absent** — intent §1 mandates 2 extra sections (alternatives considered, historical comparison from prediction diary). Neither a second prompt nor a second cache row type exists.
3. **Eager generation instead of lazy** — intent §1 mandates "lazy-generated on first explanation-icon click". Reality: generation happens during DP composition, regardless of whether the user clicks the icon. Each composed DP eats budget upfront.
4. **System prompt hard-coded, not loaded from intent file** — intent §2 Layer 1 mandates the prompt live in `docs/intent/ai-explanation-prompt.md` (which exists). Reality: hard-coded in `anthropic_explanation_provider.py:55-62`. The intent file is a stub that doesn't drive production.
5. **Voice-rule deterministic filter (intent §2 Layer 2) not implemented** — em-dash normalisation, banned-phrase stripping, paragraph-bound enforcement: none of the three runtime substitutions exists. `docs/intent/voice-rules.md` (153 LOC, version 1) is never loaded at runtime.
6. **Voice-validation schema pass (intent §2 Layer 3) not implemented** — `validate_explanation_output` checks hallucinated numbers + disclaimer + length only, not voice patterns. AGENTS.md "Every AI output must be schema-validated" doctrine is at best partially satisfied; the schema validates content correctness, not voice compliance.
7. **80% / 100% budget warnings on system-health line absent** — intent §4 mandates yellow at 80%, red at 100% on the doctrine-§10 system-health line. `monthly_budget_status` returns the data but no surface consumes it. Operators cannot see budget pressure until the hard stop fires.
8. **Multi-provider fallback (Anthropic → OpenAI) not implemented** — intent §2 + doctrine §13.1 mandate fallback to a second provider on validation failure or exhaustion. Reality: single Anthropic provider, no OpenAI integration anywhere in the API codebase.
9. **`"AI-uitleg budget bereikt voor deze maand"` Dutch fallback not rendered** — string exists only in intent (line 96) + decision record (line 26). No frontend component or backend response renders it on budget exhaustion. Users would see an empty or generic error.
10. **No budget extension table / no audit log for grace extensions** — intent §4 mandates "Grace extension via Category 1 settings... audit-logged with the user's reason (free-text note)". No `budget_extension` table, no settings field, no audit row format exists.
11. **Case-B LLM forecaster code path exists despite intent §5 forbidding it** — `anthropic_ts_provider.py:214` `AnthropicTsModelProvider` is wired in via `build_ts_model_provider` at `ai_ts_provider.py:168`. Defaults are safe (`ai_ts_predictor_enabled=False`), but three flag flips activate a Case-B LLM forecaster. Intent §5 Case B is unambiguous: "remove from the ensemble".
12. **No `prompt_version` column on `decision_package_explanations`** — intent §5 Case C guardrail #1 mandates "stored with its timestamp and the prompt version that produced it". Cache row has `generated_at` but not the version. Reproducibility relies on git-blame of `anthropic_explanation_provider.py:55-62` at the row's timestamp — operationally brittle.
13. **No idempotent cache-read path** — second access to the same DP re-generates instead of short-circuiting on the cache. The UNIQUE constraint catches duplicates at write time but doesn't prevent the LLM cost.
14. **Shared budget across explanation + Case-B forecast** — both call into `claude_ai_budget_usage` with the same monthly cap. A spike in Case-B forecast usage (if enabled) would silently exhaust the explanation budget. Intent §4 says "per provider"; reality is "per Anthropic Claude API account, lumped".
15. **`StubTsModelProvider` mis-classified as Case A** — T-005 flagged it as classical-ML-labelled-as-AI (Case A → rename). Per direct read of `ai_ts_provider.py:58-165`, it's a pure-Python empirical-quantile drift model using log-returns + lognormal distribution — not classical ML at all. **It's neither Case A, B, nor C**: deterministic math wearing an "AI" name tag.

## 11. Out of scope (re-confirmed)

- **Predictor backtest + leaderboard** (T-024 future).
- **Action draft composition** (T-018 — merged sibling).
- **Forecast generation deep dive** (T-015 — merged sibling; only cross-referenced for the Case-A vs Case-B distinction).
- **Settings configuration UI for Category 1 provider config** (T-061 — merged sibling).
- **Voice-rules file content review** — T-023 documents the file's existence and the absence of a runtime reader, not its specific banned-pattern list.

## 12. References

- `apps/api/src/portfolio_outlook_api/anthropic_explanation_provider.py:1-...` (LLM explanation provider — class at `:182`; SDK init at `:219`; system prompt at `:55-62`; `messages.create` at `:238`)
- `apps/api/src/portfolio_outlook_api/ai_explanation_sync.py:188, :278` (`generate_explanation` orchestrator + cache write)
- `apps/api/src/portfolio_outlook_api/ai_explanation_guards.py:32-35, :112-159` (status enum + validation guard)
- `apps/api/src/portfolio_outlook_api/claude_ai_budget.py:101, :122, :142` (`monthly_budget_status`, `assert_budget_available`, `persist_call_cost`)
- `apps/api/src/portfolio_outlook_api/ai_ts_provider.py:58, :168-256` (`StubTsModelProvider` + factory)
- `apps/api/src/portfolio_outlook_api/anthropic_ts_provider.py:214` (`AnthropicTsModelProvider` — Case-B)
- `apps/api/src/portfolio_outlook_api/config.py:158-188` (Settings — provider gates + budget cap + model name + daily-only flag)
- `packages/storage/alembic/versions/0034_decision_package_explanations.py:1-64` (cache table migration)
- `packages/storage/alembic/versions/0043_claude_ai_budget_usage.py:1-48` (budget usage table migration)
- `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:2712` (`SqlAlchemyDecisionPackageExplanationRepository`)
- `packages/storage/src/ai_trading_agent_storage/repository_contracts.py:2657` (`DecisionPackageExplanationRecord.generated_at`)
- `apps/web/components/ForecastExplanationPanel.tsx:1, :69, :80` (frontend consumer)
- `docs/intent/ai-usage.md` (locked 2026-05-26)
- `docs/intent/ai-explanation-prompt.md` (stub v0.1 — never loaded at runtime)
- `docs/intent/voice-rules.md` (version 1, 153 LOC — never loaded at runtime)
- `docs/decisions/0013-ai-usage-architecture.md`
- `docs/reality/components/api-infrastructure-and-ai.md` (T-006 — Anthropic provider + monthly EUR cap)
- `docs/reality/components/api-actions-suggestions-and-watchlists.md` (T-005 — Case B + Case A stub originating findings)
- `docs/reality/components/settings-and-credentials-infrastructure.md` (T-061 §3 — `ANTHROPIC_API_KEY` auto-read pathway)
- `docs/reality/workflows/forecast-generation-and-labelling.md` (T-015 — sibling that would consume Case-B if enabled)
