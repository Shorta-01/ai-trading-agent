# Task 132B — Select and document the next IBKR read-only sync foundation batch after Task 131B

- Gebruik de Task 131B account/session status outputs als startpunt voor een veilige vervolgselectie.
- Scope: document-first selectie + afbakening van de eerstvolgende sync-foundation batch zonder runtime-unlock.
- Vereist: duidelijke no-network/no-order/no-suggestion/no-action-draft/no-market-data grenzen.

## Boundaries (locked)
- Geen echte TWS/Gateway netwerk runtime.
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
