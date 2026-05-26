```yaml
id: T-006
title: Write reality doc for the API infrastructure + AI explanation cluster
phase: P1
status: locked
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Goal

Produce one reality doc covering API infrastructure (entry point, config, health, status, scheduler, system events, release readiness) and the AI explanation surface (Anthropic Claude integration + monthly budget).

## Context

`depends_on:` —. AI policy intent lives in `docs/ai-policy.md`; release-readiness intent in the V1.1 blocker code list inside `release_readiness.py`.

## Touch scope

Create:
- `docs/reality/components/api-infrastructure-and-ai.md`

Read: `main`, `config`, `health`, `status_*`, `scheduler*`, `system_event_*`, `storage_status`, `online_storage_status`, `release_readiness`, `request_audit`, `portfolio_valuation_readiness`, `anthropic_explanation_provider`, `ai_explanation_*`, `claude_ai_budget`. Plus `docs/ai-policy.md`.

## Acceptance criteria

- [ ] Output file exists.
- [ ] FastAPI app construction documented (`main.py` router registrations, middleware chain) with refs.
- [ ] All settings classes documented (`config.py`, `pydantic-settings` env var mapping).
- [ ] Anthropic Claude provider: documented call shape, prompt-cache invariants, budget cap enforcement, gating conditions (all with refs).
- [ ] Release readiness scorecard blockers enumerated with refs.
- [ ] No source modification.

## Out of scope

- Other API clusters (T-004, T-005).
- Worker AI usage (T-007).

## Verification

- File exists.
- `grep -E 'include_router' apps/api/src/portfolio_outlook_api/main.py` count matches the route catalogue in the file.

## Notes

Existing intent references: `docs/ai-policy.md`. The blocker codes in `release_readiness.py` map 1:1 to readiness pre-conditions and should be documented as such.
