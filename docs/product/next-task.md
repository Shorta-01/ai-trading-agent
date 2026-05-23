# Task 133B — Implementeer IBKR read-only sync readiness/preflight gate met Task 131B account/session status outputs

- Implementeer een veilige read-only readiness/preflight gate voor handmatige IBKR sync op basis van settings, read-only mode, storage readiness (waar relevant) en Task 131B account/session status outputs.
- Scope: veilige gating/statuswording en testdekking zonder runtime-unlock.
- Vereist: heldere NL statusuitkomsten zoals `Geblokkeerd`, `Controle nodig` en `Klaar voor handmatige read-only sync`.

## Boundaries (locked)
- Geen real TWS/Gateway network runtime.
- Geen account/portfolio sync runtime.
- Geen market-data runtime.
- Geen suggesties.
- Geen action drafts.
- Geen orders (submit/modify/cancel/bind).
- Geen broker execution.
- Geen fake brokerdata, fake portfoliodata of fake marktdata.

## CI and merge discipline
- Volg `docs/product/codex-red-green-ci-workflow.md`.
- Alleen handmatige merge na groene CI op alle zes jobs (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`).
- Bij rode CI: fix op dezelfde PR-branch; niet mergen.
