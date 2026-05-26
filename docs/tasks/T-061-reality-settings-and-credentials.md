```yaml
id: T-061
title: reality-settings-and-credentials
phase: P1
status: locked
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/settings-and-credentials.md
decision_ref: docs/decisions/0004-settings-and-credentials-structure.md
pr_url:
```

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
