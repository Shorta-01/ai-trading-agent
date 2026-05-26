# AI explanation prompt — template

**Status:** stub (locked structurally; prompt body developed during Phase 4 execution)
**Locked on:** 2026-05-26
**Version:** 0.1 (stub)
**Parent:** `docs/intent/ai-usage.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§13)

## Purpose

This file holds the **system prompt template** used to generate AI explanations for order rows on the dashboard. It is consumed by the explanation pipeline (Phase 4 task to be queued) and corresponds to **Layer 1** of the three-layer voice enforcement model in `docs/intent/ai-usage.md` §2.

This file is **versioned**; the version field is part of the snapshot recorded with each AI-derived feature (per doctrine §13.2 "cached / snapshotted output" guardrail).

## Status

The prompt **body** is intentionally a stub in v1. The structural commitments below are locked; the literal text will be developed and tuned during the Phase 4 task that builds the explanation pipeline. The stub form below is what ships until that task lands.

## Structural commitments

The final prompt must:

1. **Establish voice.** Reference `docs/intent/voice-rules.md` and instruct the model to avoid the banned patterns. The post-generation filter (Layer 2) catches what the model misses; the prompt is the first line of defence.
2. **Enforce the depth-B template.** Six elements in this order: (i) why this action; (ii) which predictors said what; (iii) ensemble confidence + calibration; (iv) which sizing layer was binding; (v) limit price logic; (vi) risk context. The model must produce all six; missing elements fail schema validation.
3. **Enforce the depth-C extras when requested.** Two additional elements: alternatives considered + rejected; historical comparison from prediction diary.
4. **Schema-output requirement.** The model returns a JSON object with named fields per element. The output is parsed; no free-form paragraph at the top level. Schema validation (existing infrastructure) rejects malformed responses.
5. **Provider-agnostic.** The same prompt body works for Anthropic Claude and OpenAI GPT (doctrine §13.1 multi-provider). Provider-specific formatting (Anthropic XML tags vs OpenAI JSON mode) is added at the provider-adapter layer, not in this prompt body.
6. **Language directive.** Outputs in Dutch by default; configurable per `docs/intent/settings-and-credentials.md` Category 2 UI language.
7. **Decision-package data injection.** The prompt accepts a structured decision-package payload (per `docs/intent/decision-package.md` §1) and must reference only that data. Hard rule: no original speculation. Every claim in the explanation must trace back to a field in the decision-package payload.

## Stub body (v0.1)

The text below is a **placeholder**. It establishes the structural commitments above without final wording.

```
You generate explanations for trading suggestions in a system that places real orders against a real Interactive Brokers account.

Voice rules:
- Read the project voice rules in docs/intent/voice-rules.md.
- No em-dashes. No filler phrases. No LLM-tell vocabulary (delve, unpack, leverage, crucial, key insight, it's worth noting).
- Direct, concrete, citing the data, not editorial.
- Output in Dutch by default.

Output format: a JSON object with one field per element of the requested depth.

Depth B (six fields, all required):
- why_this_action
- which_predictors
- ensemble_confidence
- binding_sizing_layer
- limit_price_logic
- risk_context

Depth C (depth-B fields plus two more):
- alternatives_considered
- historical_comparison

Hard rule: every claim must reference a value present in the decision-package payload provided. No speculation. No original numbers.

[Decision package payload follows…]
```

## Open questions

- Final wording and tuning, to be developed during Phase 4.
- Provider-adapter layer detail: how to translate the same body into Anthropic XML vs OpenAI JSON mode.
- Per-asset-class tone variations (if any).

## Cross-references

- `docs/intent/ai-usage.md` (parent — three-layer enforcement model)
- `docs/intent/voice-rules.md` (the banned-patterns list)
- `docs/intent/decision-package.md` (the data that feeds the prompt)
- Doctrine §13 (AI scope)
