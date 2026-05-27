```yaml
id: T-061
title: reality-settings-and-credentials
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/settings-and-credentials.md
decision_ref: docs/decisions/0004-settings-and-credentials-structure.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/457
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the new file under `docs/reality/components/` does not exist (verified). Two intent docs read: `docs/intent/settings-and-credentials.md` (127 lines, 5-category model + 7 UX rules + 7 open questions) and `docs/decisions/0004-settings-and-credentials-structure.md` (36 lines — accepted ADR). Settings code inventoried: `apps/api/src/portfolio_outlook_api/config.py` + `apps/worker/src/portfolio_outlook_worker/config.py` already covered by T-006 §2 and T-007 §3 respectively. New files for this task (delegated to subagent): `packages/domain/src/portfolio_outlook_domain/settings.py` (large — flagged at T-055 FIND-RADON-012 as MI=0.00), `packages/storage/src/ai_trading_agent_storage/settings.py`, `packages/domain/src/portfolio_outlook_domain/paper_setup.py`, `apps/api/src/portfolio_outlook_api/paper_setup.py`, `apps/api/src/portfolio_outlook_api/paper_setup_persistence.py`, `apps/api/src/portfolio_outlook_api/claude_ai_budget.py` (already covered T-006 §11e; will re-cite).
- **Step 2 (one-line per touched file):** the one target file does not exist; it will hold the reality doc mapping current code against the five-category intent.
  - `settings-and-credentials-infrastructure.md` — five-category map + secrets-read inventory + UX-rules-vs-reality table + Phase 1c gap surface.
- **Step 3 (one-line change):** write one cited reality doc mapping the existing settings/credentials infrastructure against the locked five-category intent; surface gaps for Phase 1c.
- **Step 4 (measurable):** yes — four acceptance criteria: one file in `docs/reality/components/`; every claim cites `path:line`; mapping each existing settings module to the 5 categories (notes categories with no implementation yet); inventory of every place secrets are read at runtime; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — no settings-code changes; no new-backend design (Doctrine §15 open question stays open).

## Goal

Document the existing settings and credentials infrastructure as it stands in HEAD, and map it against the intent in `docs/intent/settings-and-credentials.md`.

## Context

Surfaced during the functional review of 2026-05-26 (T-011…T-024). The settings/secrets infrastructure already exists in scattered places — `packages/domain/.../settings.py`, `claude_ai_budget.py`, `paper_setup.py`, plus whatever `.env` handling is in `apps/api/src/.../config.py` and `apps/worker/src/.../config.py`. No single doc currently describes which categories exist, which storage backends are used, how secrets are read at runtime, or how to add a new setting. This task delivers that descriptive baseline so Phase 1c can score the gap between the five-category intent and reality.

## Touch scope

- New file under `docs/reality/components/` (location and exact filename chosen during the task — likely `settings-and-credentials-infrastructure.md`).

## Acceptance criteria

- [ ] One file in `docs/reality/components/` describes the current settings/credentials infrastructure.
- [ ] Every claim cites `path:line` per the Phase 1 quality bar.
- [ ] The doc maps each existing settings module to the five intent categories (connections, user preferences, safety limits, monitoring, audit/backup) and notes which categories have no implementation yet.
- [ ] Listed: every place where secrets (API keys, DB URLs, IBKR credentials) are read at runtime.

## Out of scope

- Changes to the settings code. This is reality-documentation only.
- Designing new settings backends (keyring vs encrypted file is a doctrine §15 open question).

## Verification

Reviewer can read the file and locate each cited symbol or line in the repo at HEAD without ambiguity.

## Notes

Pairs with the intent in `docs/intent/settings-and-credentials.md` and decision `0004`.
