# Task 131B — Implement IBKR read-only account/session safety batch using the Task 130 session-status boundary

- Vervangt de eerdere kleine Task 131-route met een veiligere milestone-batch.
- Scope: account-mode mapping, unknown-status veilige wording, en statusmapping voor `connection_failed`, `authentication_required` en `pacing_limited`.
- Vereist: fake-adapter tests plus no-secret/no-fake-data checks.

## Boundaries (locked)
- Geen account/portfolio sync.
- Geen market-data runtime.
- Geen suggesties.
- Geen action drafts.
- Geen Decision Packages runtime.
- Geen orders (submit/modify/cancel/bind).
- Geen broker execution.
- Geen fake brokerdata, fake portfoliodata of fake marktdata.

## CI and merge discipline
- Volg `docs/product/codex-red-green-ci-workflow.md`.
- Alleen handmatige merge na groene CI op alle zes jobs (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`).
- Bij rode CI: fix op dezelfde PR-branch; niet mergen.
