```yaml
id: T-023
title: Write reality doc for AI explanation generation + per-provider budget
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/ai-usage.md
decision_ref: docs/decisions/0013-ai-usage-architecture.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/468
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/ai-explanation-and-budget.md` does not exist (verified). Pure synthesis — every code site is cited in T-002 + T-005 + T-006 + T-061 reality docs or being inventoried via the background exploration agent:
  - T-006 `api-infrastructure-and-ai.md` — Anthropic Claude provider call shape + monthly EUR budget cap + Case C AI classification documented.
  - T-005 `api-actions-suggestions-and-watchlists.md` — `anthropic_ts_provider` Case B + `ai_ts_provider` stub Case A documented.
  - T-061 `settings-and-credentials-infrastructure.md` §3 — Anthropic SDK auto-reads `ANTHROPIC_API_KEY` from OS env, NOT from the Pydantic `claude_ai_api_key` field; the Pydantic field is a presence-gate only.
  - `docs/intent/ai-usage.md` — depth B/C, 3-layer voice enforcement, hard cap at budget, 80%/100% threshold warnings, multi-provider fallback, AI-in-forecasting Case A/B/C framework.
  - `docs/intent/ai-explanation-prompt.md` + `docs/intent/voice-rules.md` (intent layer 1 + 2 source).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the end-to-end AI explanation + budget workflow doc.
  - `ai-explanation-and-budget.md` — explanation icon click → API route → cache read (idempotent) on `decision_package_id` → budget check → Anthropic provider call (system prompt + Depth B 6 elements schema) → voice-rule post-generation filter (3 layers per intent §2) → schema validation → cache write → response → Dutch render; budget tracking with per-provider monthly EUR cap + 80%/100% warning thresholds + audit chain for grace extensions; AI-in-forecasting Case A/B/C re-confirmation surfacing the existing 3 provider call sites.
- **Step 3 (one-line change):** write one cited workflow reality doc tracing AI explanation generation end-to-end + the per-provider budget gate.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; explanation provider documented (`anthropic_explanation_provider.py` — `Anthropic()` SDK + `messages.create` + system prompt source); explanation API route documented; lazy generation + cache table documented (cache PK = `decision_package_id`); budget tracking documented (monthly EUR cap + 80%/100% thresholds + audit chain); voice-rule layers documented (which of the 3 intent-§2 layers exist in code vs are gaps); AI-in-forecasting Case A/B/C re-surfaced (3 provider sites); ≥ 10 Phase 1c findings; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — predictor backtest + leaderboard (T-024 future), action-draft composition (T-018 already merged sibling).

## Goal

Produce one workflow reality doc tracing AI explanation end-to-end — from explanation-icon click (UI) → API route → idempotent cache read against `decision_package_id` → per-provider budget gate → Anthropic provider call (system prompt loaded from intent file? or hard-coded?) → schema validation + voice-rule post-generation filter (3-layer intent vs reality) → cache write → Dutch-rendered response. The doc also documents the per-provider monthly EUR budget tracking (intent §4: hard stop at cap; 80% yellow, 100% red), the AI-in-forecasting Case A/B/C re-confirmation across the 3 known provider sites, and the major intent-vs-reality drift on multi-provider fallback (OpenAI second-provider) + the dynamic banned-phrases file-vs-code source.

## Context

`depends_on:` T-002 (portfolio module — unrelated but listed in queue), T-006 (API infrastructure + AI). T-006 covered the Anthropic Claude provider at module level + monthly EUR budget cap + Case C classification; T-023 stitches them into the end-to-end "from explanation-icon click to Dutch-rendered text" story and surfaces the multi-provider fallback gap + voice-rule layer status.

## Touch scope

Create:
- `docs/reality/workflows/ai-explanation-and-budget.md`

Read: T-006 + T-005 + T-061 reality docs + the AI usage intent doc + the voice-rules intent doc + the explanation provider modules + the budget tracking modules + the frontend explanation component.

## Acceptance criteria

- [ ] Output file exists at the locked filename.
- [ ] Explanation provider documented (`Anthropic()` SDK instantiation + `messages.create` call + how the system prompt is constructed — from file or hard-coded).
- [ ] Explanation API route documented (route path + HTTP method + cache-key resolution path).
- [ ] Cache table + lazy generation documented (idempotency key on `decision_package_id`; cache hit path skips the LLM call entirely).
- [ ] Budget tracking documented — monthly EUR cap field + per-call usage increment + hard-stop gate + 80% / 100% warning thresholds (intent §4 mandate vs reality).
- [ ] Voice-rule layer status documented — Layer 1 system prompt source, Layer 2 deterministic post-generation filter (banned-phrases dynamic vs hard-coded), Layer 3 schema validation pass.
- [ ] AI-in-forecasting Case A/B/C re-surfaced — the 3 known provider sites (`anthropic_explanation_provider` Case C, `anthropic_ts_provider` Case B, `ai_ts_provider` stub Case A).
- [ ] ≥ 10 Phase 1c findings.
- [ ] No source modification.

## Out of scope

- Predictor backtest + leaderboard (T-024 future).
- Action draft composition (T-018 — merged sibling).
- Forecast generation deep dive (T-015 — merged sibling; T-023 only cross-references the Case-B/C distinctions).
- Settings configuration UI for Category 1 provider config (T-061 — merged sibling).

## Verification

- File exists.
- All 3 AI provider sites cited with file:line.
- Cache table + migration cited (if present); or absence noted as Phase 1c gap.
- Budget tracking module + thresholds cited.
- Voice-rules file presence + runtime-load path documented (or absence noted as Phase 1c gap).
- ≥ 10 Phase 1c findings.

## Notes

T-023 is unusual because intent §5 explicitly says "T-023 will surface which case the existing code falls into" — the Case A/B/C framework was authored with this reality doc in mind. The explanation surface is the **only** intent-sanctioned LLM use case (Case C with all 3 guardrails); Cases A + B are quarantines for code that needs to be either renamed (Case A) or removed (Case B). T-005's Case-B `anthropic_ts_provider` finding is the most safety-critical re-surface — it's a forecast-emitting LLM that intent forbids. T-023 documents whether it's wired into the production ensemble or only stub-routed.
