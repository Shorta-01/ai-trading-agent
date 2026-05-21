# Next Task

## CI status

CI is nu hersteld en groen. Na de repository visibility change van private naar public is de eerdere GitHub Actions execution/logging blokkade opgelost.

- CI run **#358** is succesvol afgerond.
- Alle 6 normale CI-jobs zijn groen: `domain`, `storage`, `portfolio`, `api`, `worker`, `web`.
- GitHub Actions logs en step-details zijn opnieuw zichtbaar.
- Normale regel blijft gelden: nieuwe featuretaken vereisen groene CI.

## Next implementation task

Task 89 — Conservatieve API-readiness contract hardening: kleine vervolgstap met extra response-contract regressietests en expliciete typed coverage voor snapshot-detailvarianten (read-only, geen runtime).

Task 89 wordt **niet** in deze documentatie-taak geïmplementeerd.
