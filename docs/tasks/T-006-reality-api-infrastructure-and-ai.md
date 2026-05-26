```yaml
id: T-006
title: Write reality doc for the API infrastructure + AI explanation cluster
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the touch scope is one new file under `docs/reality/components/`; it does not exist. The 20 in-scope modules in `apps/api/src/portfolio_outlook_api/` (~8958 lines) plus the `docs/ai-policy.md` intent reference (95 lines) are read in parallel by three subagents:
  - Agent A — infra core: `main.py` (130), `config.py` (261), `health.py` (12), `status_builders.py` (299), `status_models.py` (109), `status_routes.py` (4014), `scheduler.py` (296), `scheduler_routes.py` (189) ≈ 5310 lines.
  - Agent B — system events + readiness: `system_event_mutations.py` (153), `system_event_reader.py` (147), `system_event_recorder.py` (154), `storage_status.py` (142), `online_storage_status.py` (105), `release_readiness.py` (497), `request_audit.py` (504), `portfolio_valuation_readiness.py` (916) ≈ 2618 lines.
  - Agent C — AI cluster + intent: `anthropic_explanation_provider.py` (280), `ai_explanation_provider.py` (210), `ai_explanation_sync.py` (354), `claude_ai_budget.py` (186), `docs/ai-policy.md` (95) ≈ 1125 lines.
- **Step 2 (one-line per touched file):** the one target file does not exist; it will hold the reality doc for the infrastructure + AI cluster:
  - `api-infrastructure-and-ai.md` — entry point + middleware + 8 infrastructure routers; settings classes; scheduler ticks + admin routes; system_event ring-buffer reader / writer / mutations; storage + online + release-readiness scorecards; request audit middleware; portfolio_valuation_readiness; Anthropic Claude provider call shape + prompt-cache + monthly budget cap + Case A / Case B gating; `docs/ai-policy.md` intent linkage.
- **Step 3 (one-line change):** write one cited reality doc covering FastAPI app construction, settings, infra routes (status / scheduler / system-event), the three readiness scorecards, request audit, and the Anthropic explanation surface — all from the 20 in-scope `apps/api` modules, no source modified.
- **Step 4 (criteria measurable):** yes — six acceptance criteria: file exists; `main.py` router registrations enumerated with refs; all settings classes documented; Anthropic provider call shape + prompt-cache + budget cap + gating documented with refs; release-readiness blocker code list enumerated with refs; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — other API clusters (T-004 / T-005) are not in scope, and worker AI usage (T-007) is not in scope. Note: `status_routes.py` (4014 lines) contains many routes that belong to T-004 (IBKR status) or T-005 (forecast status / market data status); the subagent groups them by responsibility and only the infrastructure-flavoured routes (health, system-event, release-readiness, request-audit, AI explanation status) are documented in detail here — the rest are listed with a forward-reference and route count only.

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
