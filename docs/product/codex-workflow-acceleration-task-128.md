# Task 128 — Codex workflow acceleration (process-only)

## Waarom deze pivot
De repository stapte in een patroon met veel kleine micro-audits. Dat maakte prompts lang, verhoogde copy-pastewerk en leidde sneller tot trackingdrift en herhaalde CI-repairloops.

Task 128 verplaatst de focus naar herbruikbare workflowdocumentatie en lichte lokale checks, zodat volgende Codex-taken korter, consistenter en veiliger blijven.

## Relatie met Task 125W
Task 125W (micro-audit voor aanvullende valuation readiness helpteksten) wordt met deze taak **bewust gedeferreerd/vervangen** als directe volgende stap.

Deze pivot betekent:
- eerst workflowdiscipline en taakbundeling verbeteren;
- daarna vervolgstappen kiezen vanuit een milestone-queue i.p.v. losse micro-taken.

## Scope van Task 128
Task 128 is strikt **proces/documentatie**:
- geen runtimewijzigingen;
- geen API-behaviorwijzigingen;
- geen storage/migraties;
- geen runtime fetch;
- geen financiële berekeningen;
- geen suggesties, action drafts of orders.

## Nieuwe red/green CI-werkwijze
- **Groene CI**: review + merge is toegestaan.
- **Rode CI**: niet mergen; fix in dezelfde PR; CI opnieuw draaien tot groen.
- **Per ongeluk rood op main gemerged**: featurewerk stoppen; exact één gerichte repair-PR; alleen mergen als alle zes jobs groen zijn.

## Human-in-the-loop blijft verplicht
- Review door mens blijft verplicht.
- Handmatige merge blijft verplicht.
- Codex mag **niet** auto-mergen.

## Branch protection
Repository-owner moet GitHub branch protection actief houden/inschakelen (indien nog niet actief), zodat vereiste CI-checks afdwingbaar blijven.

## Herbruikbaarheid voor volgende taken
Volgende taken moeten korter worden door standaardgebruik van:
- `docs/product/codex-task-template.md`
- `docs/product/task-queue.md`
- `docs/product/codex-red-green-ci-workflow.md`

## Safety blijft leidend
Workflowautomatisering is ondersteunend en mag nooit product safety regels verzwakken:
- geen live trading;
- geen automatische orders;
- geen brokeractie zonder expliciete user approval;
- geen fake data;
- geen runtime-uitbreiding buiten expliciete scope.
