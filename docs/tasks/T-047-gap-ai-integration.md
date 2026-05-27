```yaml
id: T-047
title: Write gap analysis doc — 04 AI integration gaps
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/gap-analysis/04-ai-integration-gaps.md` does not exist (verified). T-044 + T-045 + T-046 (siblings, merged) established the 6-part format. T-046 §14 + T-045 §16 + T-044 §16 cross-referenced AI findings as "belongs to T-047". T-047 inherits those.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the gap analysis of AI provider / voice / budget / explanation gaps.
  - `04-ai-integration-gaps.md` — gap-entry-per-gap for AI integration: (1) `AnthropicTsModelProvider` Case-B wired despite intent §5 forbidding it, (2) System prompt hard-coded not loaded from intent file, (3) Voice-rule Layer 3 schema-validation absent, (4) 80%/100% budget threshold warnings absent on system-health line, (5) Dutch "budget bereikt" fallback not rendered, (6) No budget extension table for grace extensions, (7) No idempotent cache-read path, (8) Shared budget across explanation + Case-B forecast, (9) `StubTsModelProvider` Case A/B/C mis-classification, (10) `claude_ai_api_key` Pydantic field is presence-gate only (SDK auto-reads from OS env), (11) TOB-net expected return not implemented (intent §4 mandate), (12) No structured JSON schema for Depth B/C output (AGENTS.md schema-validation mandate).
- **Step 3 (one-line change):** write one gap-analysis doc enumerating AI-specific integration gaps.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; ≥ 12 AI-specific gap entries; each entry uses the 6-part format; MoSCoW spans at least 3 ratings; effort spans at least 2 sizes; each entry cites originating reality doc; cross-reference to T-044/T-045/T-046/T-048; Case-B production-path drift surfaced as the most safety-critical AI gap; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — UI gaps (T-044), schema/incomplete (T-045), quant (T-046), operational/security (T-048), summary (T-049).

## Goal

Produce one gap-analysis doc focused on AI provider / voice rule / budget / explanation gaps. The dominant gap: **the AI-TS forecaster (Case-B) is wired into production behind 5 feature flags despite intent §5 explicitly forbidding it** ("remove from the ensemble. LLMs hallucinate numbers; calibration is unreliable; risk is unbounded.").

## Context

`depends_on:` T-023 (AI explanation + budget — primary source), T-061 (settings + credentials), T-022 (TOB-net expected return cross-ref). T-023's 15 findings map mostly 1:1 to T-047 entries; T-044-T-046 already absorbed a few (Depth-C UI, eager generation, prompt_version, voice-rule Layer 2 partial).

## Touch scope

Create:
- `docs/gap-analysis/04-ai-integration-gaps.md`

Read: T-022 + T-023 + T-061 reality docs + T-044/T-045/T-046 for cross-reference.

## Acceptance criteria

- [ ] Output file exists at `docs/gap-analysis/04-ai-integration-gaps.md`.
- [ ] ≥ 12 AI-specific gap entries.
- [ ] Each entry uses the 6-part format.
- [ ] MoSCoW spans at least 3 ratings.
- [ ] Effort spans at least 2 sizes.
- [ ] Each entry cites originating reality doc.
- [ ] Cross-reference table to T-044/T-045/T-046/T-048.
- [ ] Case-B production-path drift surfaced as the most safety-critical AI gap.
- [ ] No source modification.

## Out of scope

- Missing user features (T-044 — merged; AI Depth-C UI surface lives there).
- Incomplete implementations (T-045 — merged; AI prompt_version, eager generation, AI Depth-B paraphrase live there).
- Quant gaps (T-046 — merged).
- Operational gaps (T-048 — future).
- Summary (T-049 — last).

## Verification

- File exists.
- 6-part format consistent.
- Case-B drift prominent.
- Cross-reference table present.

## Notes

T-047 is the 4th of 6 Track 1c docs. The most safety-critical AI finding is **Case-B drift**: intent §5 of `ai-usage.md` is unambiguous — "remove from the ensemble. This is not a mainstream-safe pattern for retail trading. LLMs hallucinate numbers; calibration is unreliable; risk is unbounded." Reality: `AnthropicTsModelProvider` is wired in via `build_ts_model_provider`, gated behind 5 feature flags whose defaults are safe. Operator flips 3 flags → LLM forecaster in production ensemble. The intent explicitly forbids what the code makes feature-flag-reachable.
