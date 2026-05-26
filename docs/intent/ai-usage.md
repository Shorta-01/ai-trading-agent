# AI usage — intent

**Status:** locked
**Locked on:** 2026-05-26
**Decision record:** `docs/decisions/0013-ai-usage-architecture.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§13, §15)

## Scope

This document specifies how AI (LLM) is used in the system: explanation depth, voice and tone enforcement, budget behaviour, and the boundary on AI-in-forecasting. It is the source for `docs/intent/voice-rules.md` and `docs/intent/ai-explanation-prompt.md`.

## 1. Explanation depth — two levels

The explanation icon on every order row (doctrine §10) opens an explanation. There are two depth levels:

### Depth B (default, lazy-generated, cached)

Six elements, always present:

1. **Why this action** — what the system is suggesting and the headline reason.
2. **Which predictors said what** — per-predictor contribution to the ensemble (predictor name + raw direction + weight).
3. **Ensemble confidence** — the combined confidence + calibration status (green / yellow / red).
4. **Which sizing layer was binding** — Kelly base / conviction scaling / hard caps (doctrine §5.1).
5. **Limit price logic** — patient liquidity (with discount/premium) or forecast override (doctrine §5.3).
6. **Risk context** — current exposure of this position, sector, asset class; distance to caps; available cash.

Depth B is **lazy-generated** (on first explanation-icon click — see `docs/intent/decision-package.md` §5) and **cached** against `decision_package_id` until the package is rebuilt.

### Depth C (on-demand via "Explain more")

Two additional sections:

7. **Alternatives considered and rejected** — the other top-scoring actions the system evaluated and why they didn't win.
8. **Historical comparison from prediction diary** — how similar setups for similar assets have performed historically.

Depth C is **separately cached** against `decision_package_id`. Both depths count toward the per-provider monthly cap (§3).

## 2. Voice and tone — three enforcement layers

Voice rules apply to every AI-generated output. Three layers ensure compliance.

### Layer 1: system prompt

The system prompt lives in `docs/intent/ai-explanation-prompt.md`. It carries the voice rules summary, the structural template (the six elements of Depth B, the two extra of Depth C), and the schema requirements.

### Layer 2: deterministic post-generation filter

After the LLM returns, a deterministic filter applies:

- **Em-dashes** (any) are converted to standard punctuation.
- **Banned phrases** are stripped or rephrased.
- **Length and paragraph bounds** are enforced.

The filter reads `docs/intent/voice-rules.md` at runtime. No code-level baked-in rules; the file is the source.

### Layer 3: voice-validation schema check

The schema validator (already in scope via "Every AI output must be schema-validated" from AGENTS.md) includes a voice-validation pass: any output still containing a banned pattern after Layer 2 fails validation.

### Fallback on validation failure

On voice-validation failure (or any schema-invalid output):

1. **Try the fallback provider** (per doctrine §13.1).
2. **If both fail**, show the raw decision package data with a localized Dutch message: `"Een uitleg in jouw stijl kon niet gegenereerd worden."`

The order row's trust signal does not change on AI fallback — AI is non-critical (`docs/intent/decision-package.md` §6).

## 3. Initial banned-patterns list

Dutch and English. The full list is in `docs/intent/voice-rules.md`. Initial entries:

- Em-dashes (any character variant)
- "let me explain"
- "it's important to note"
- "in essence"
- "fundamentally"
- "not just X but Y" construction
- "unpack"
- "delve"
- "navigate" (in non-literal sense)
- "leverage" (verb)
- "crucial"
- "key insight"
- "it's worth noting"
- Excessive bolding (more than two bolded spans per paragraph)
- Gedachtestreepje (Dutch em-dash equivalent)

The list is **versioned** in `docs/intent/voice-rules.md` (file-level version field). New patterns discovered from real output are added with the rationale; never silently removed.

## 4. Budget behaviour

Per-provider monthly cap. Behaviour:

- **Hard stop at cap.** No grace period in the soft sense — once the per-provider budget is exhausted in a month, no more requests go to that provider.
- **When cap reached on the explanation surface:** the explanation icon shows `"AI-uitleg budget bereikt voor deze maand"` + the raw decision-package data (Depth B's six elements rendered from the structured fields, without LLM rewrite) + a link to Category 1 of settings to enable / increase the budget.
- **Grace extension via Category 1 settings.** The user can add a supplemental amount mid-month. The supplemental addition is **audit-logged with the user's reason** (free-text note).
- **Approaching-cap warnings:** yellow on the dashboard system-health line at **80%** of monthly cap consumed. Red at **100%**.

Budget caps are **per provider**: hitting the Anthropic cap can still allow fallback to OpenAI if its cap is unspent (per doctrine §13.1 multi-provider fallback). The fallback enabled toggle in settings controls this.

## 5. AI-in-forecasting boundary — three-case framework

Three cases, pre-decided. T-023 (`ai-explanation-and-budget.md` reality) and T-015 (`forecast-generation-and-labelling.md` reality) will surface which case the existing code falls into. Pre-decided responses:

### Case A — classical ML model labelled "AI"

A traditional ML model (e.g. gradient-boosted trees) that someone has labelled "AI" in code.

**Response:** rename. Update doctrine §13 to clarify "AI" means **LLM specifically**. A classical ML predictor remains a Predictor — see `docs/intent/forecast-engine.md`.

### Case B — LLM directly producing forecasts

The LLM is asked to emit a price prediction or probability distribution that feeds the ensemble directly.

**Response:** **remove from the ensemble.** This is not a mainstream-safe pattern for retail trading. LLMs hallucinate numbers; calibration is unreliable; risk is unbounded.

### Case C — LLM produces features that a deterministic forecaster consumes

The LLM produces a structured feature (e.g. "company is in turnaround: yes/no", "guidance sentiment: positive/neutral/negative") which a deterministic forecaster reads as one input among many.

**Response:** **permit with three guardrails** (doctrine §13.2):

1. **Cached / snapshotted output.** The feature value is stored with its timestamp and the prompt version that produced it. Reproducibility is guaranteed.
2. **Treated as a feature, not as a forecast.** The deterministic forecaster owns the prediction; the LLM's output is one input among many.
3. **Never the sole or dominant input.** If the LLM-derived feature would be the strongest contributor in a given forecast, the forecast is generated **without** the LLM feature for that asset.

## 6. Open questions

- Initial banned-patterns list (final form, after observing real output) — doctrine §15
- Per-provider AI budget defaults — doctrine §13.1, §15
- Multi-provider AI scope expansion (whether to permit OpenAI for non-explanation use cases) — doctrine §15, pending T-015 / T-023 findings
- Permitted vs prohibited patterns for AI in forecasting (full formalization) — doctrine §15

## 7. Cross-references

- Doctrine §13 (AI scope: explanation primary, features permitted with guardrails)
- Doctrine §15 (open questions)
- `docs/intent/voice-rules.md` (the actual banned-patterns list)
- `docs/intent/ai-explanation-prompt.md` (the system prompt template)
- `docs/intent/decision-package.md` (lazy generation + caching)
- `docs/intent/dashboard-and-order-flow.md` (explanation icon UX)
- `docs/intent/forecast-engine.md` (case-C predictor lives here)
- `docs/intent/settings-and-credentials.md` (Category 1: provider config, per-provider budget caps)
