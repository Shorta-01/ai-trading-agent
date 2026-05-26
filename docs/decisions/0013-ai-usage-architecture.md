# 0013 — Adopt the AI-usage architecture

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** Doctrine §13 phrasing prior to 2026-05-26 (the prior "Python calculates, AI explains" formulation is now extended to the nuanced version locked in `docs/intent/_trading-system-doctrine.md` §13)
- **Superseded by:** —
- **References:** `docs/intent/ai-usage.md`, `docs/intent/voice-rules.md`, `docs/intent/ai-explanation-prompt.md`, doctrine §13 and §15.

## Context

T-023 (`ai-explanation-and-budget.md` reality) needed to land a coherent answer to four coupled questions surfaced during the review:

1. What does the AI explanation actually contain? Free-form prose, or structured output?
2. How is voice and tone enforced (so the project's voice survives every LLM update)?
3. What is the budget behaviour at the cap?
4. What is the precise boundary between "AI explains" (allowed) and "AI predicts" (not allowed)? The functional review surfaced a third case — AI produces features that a deterministic forecaster consumes — that was not previously locked.

## Decision

Adopt the architecture defined in `docs/intent/ai-usage.md`:

- **Two explanation depths.** Depth B (default; six structured elements; lazy + cached). Depth C (on-demand "Explain more"; adds alternatives considered and historical comparison; separately cached). Both count toward per-provider monthly cap.
- **Voice enforcement in three layers.** Layer 1: system prompt in `docs/intent/ai-explanation-prompt.md`. Layer 2: deterministic post-generation filter reading `docs/intent/voice-rules.md`. Layer 3: voice-validation schema check. Fallback on validation failure: try fallback provider; if both fail, show raw decision-package data with localized message.
- **Initial banned-patterns list** in `docs/intent/voice-rules.md` (Dutch + English, versioned).
- **Budget behaviour: hard stop at cap.** No grace by default. Explanation surface shows "AI-uitleg budget bereikt voor deze maand" + raw data + settings link. Grace extension via Category 1 settings (audit-logged with user reason). Yellow at 80%, red at 100%. Per-provider.
- **AI-in-forecasting three-case framework.** A (classical ML labelled "AI") → rename + clarify doctrine §13. B (LLM-as-forecaster) → not permitted in v1. C (LLM produces features, deterministic forecaster consumes) → permitted with three guardrails: cached/snapshotted, treated as feature not forecast, never sole or dominant input.

## Alternatives considered

- **Single depth (everything every time).** Rejected: most clicks read only headline reasons; depth C is power-user material.
- **No voice filter (trust the LLM).** Rejected: every LLM update can drift voice. Three layers protects voice from regression without each new model needing a code change.
- **Soft cap with auto-grace.** Rejected: budget is a real cost the user pays. Hard stop with explicit user-approved grace respects the user's financial control.
- **Permit case-B (LLM-as-forecaster) in v1.** Rejected: LLMs hallucinate numbers; calibration is unreliable; this is not a mainstream-safe pattern for retail real-money trading.
- **Forbid case-C (LLM-derived features) entirely.** Rejected: it's the genuinely useful pattern, provided the three guardrails are enforced.

## Consequences

- T-023 reality describes existing AI explanation code against this intent.
- T-015 reality describes the forecast engine and may surface case-A (rename) or case-C (permit with guardrails) instances.
- The voice-rules file becomes a runtime-loaded asset; voice updates do not require code changes.
- AI budget caps move to Category 1 of settings (per-provider, with fallback toggle).
