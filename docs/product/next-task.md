## Task 73: Docs — lock Release 1 functional workflow blueprint (recommended)

Doel: eerst repository-truth vastzetten voor de volledige Release 1 functionele workflow vóór nieuwe implementatietaken starten.

### Waarom nu

- Na Task 72C is de repository nog foundation-heavy en ontbreken suggestion/IBKR/AI/market-data/forecast runtimes.
- De bredere Release 1 ontwerpbeslissingen zijn nu vergrendeld en moeten eerst als documentatiebron worden vastgelegd.
- Zonder deze blueprint is er risico op versnipperde implementatie en scope-drift.

### Task 73 output (docs-only)

- Voeg `docs/product/release-1-functional-workflow-blueprint.md` toe als leidende bron voor end-to-end Release 1 workflow.
- Synchroniseer verwijzingen in handover, final vision, locked decisions, backlog, scope register en task history.
- Bevestig expliciet dat geen runtimecode, migraties, API’s, UI, tests of tradinggedrag worden toegevoegd.

### Niet doen in Task 73

- Geen asset detection implementeren.
- Geen IBKR sync runtime bouwen.
- Geen suggestions/Decision Packages/action grids bouwen.
- Geen market-data of AI runtime toevoegen.

### Na merge van deze docs-task (toekomstige volgende stap)

Als deze blueprint gemerged is en CI groen is, start dan pas een conservatieve eerste runtime-implementatietaak, bijvoorbeeld:
- “Task 74: IBKR portfolio sync engine foundation (read-only, audit-first, geen orderflow)”

Die toekomstige taak blijft buiten deze PR.
