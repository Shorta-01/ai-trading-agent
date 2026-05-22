# Next Task

## Task 125D-CI — GitHub main CI-verificatie en herstel (focus task)

### Waarom deze task eerst
Voor Task 125D (read-only valuation preparation) moet de `main` branch aantoonbaar groen zijn op alle zes CI-jobs:
- domain
- storage
- portfolio
- api
- worker
- web

In de huidige sessie kon deze status niet betrouwbaar worden vastgesteld vanuit de execution-omgeving. Daardoor is Task 125D nog niet veilig startbaar volgens de CI-discipline.

### Doel
Voer een gerichte CI-gate controle en herstel uit op `main` vóór nieuwe functionele implementatie.

### Scope
1. Bevestig de laatste `main` workflow-run en jobstatussen voor alle zes jobs.
2. Als één job rood is: repareer alleen de oorzaak van die CI-fout.
3. Laat de pipeline opnieuw draaien en bevestig dat alle zes jobs groen zijn.
4. Pas alleen noodzakelijke code/tests/docs aan voor CI-herstel.

### Expliciet niet in deze task
- Geen Task 125D waarderingsimplementatie.
- Geen market-data runtime.
- Geen suggesties.
- Geen action drafts.
- Geen orders/execution.
- Geen fake prijzen of fake brokerdata.

### Acceptatie
- Laatste `main` CI-run aantoonbaar groen op: domain, storage, portfolio, api, worker, web.
- Alleen gefocuste CI-herstelwijzigingen.
- Producttrackingdocs bijgewerkt met de uitkomst.
