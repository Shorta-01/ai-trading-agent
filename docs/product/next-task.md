# Task 150 — geselecteerde TWS/Gateway client dependency install/import CI preflight zonder runtime-connectiviteit

Geselecteerde volgende taak: **Task 150**.

## Doel
Voer een dependency-only CI preflight uit voor de geselecteerde kandidaat (`ibapi`) met install/import verificatie per verplichte CI job, zonder runtime connectiviteit.

## Scope
- Voeg tijdelijk/controlled dependency-introductie toe in projectmetadata voor CI install/import verificatie.
- Verifieer Python-versie compatibiliteit en Linux x86_64 + arm64/Raspberry Pi geschiktheid in CI/gedocumenteerde checks.
- Documenteer resultaten en rollbackpad.

## Non-goals
- Geen runtime code, geen production connectiestromen, geen sockets/open connecties.
- Geen API/web behavior changes.
- Geen storage schema/migraties.
- Geen account/portfolio sync runtime, market-data runtime, FX runtime.
- Geen suggesties, action drafts, orders of broker execution.
