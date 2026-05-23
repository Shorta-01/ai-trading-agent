# Codex red/green CI workflow

## Doel
Deze workflow voorkomt merge van rode PR's en vermindert losse handmatige repairtaken.

## Green path
1. Codex opent PR.
2. GitHub CI draait.
3. Alle zes jobs zijn groen (`domain`, `storage`, `portfolio`, `api`, `worker`, `web`).
4. User voert review uit.
5. User merge handmatig.
6. Volgende taak start pas na merge + verificatie.

## Red path
1. CI is rood.
2. **Niet mergen.**
3. Lees failing job logs.
4. Fix op dezelfde PR-branch.
5. Push fix.
6. Rerun CI.
7. Herhaal tot alle zes jobs groen zijn.
8. Pas dan review + merge.

## Accidental red merge path
1. Stop featurewerk.
2. Inspecteer main CI-failures.
3. Schrijf exact één focused repair task.
4. Maak repair-PR alleen voor die fout.
5. Merge alleen als alle zes jobs groen zijn.

## Harde regels
- Rode PR's mogen niet gemerged worden.
- Repair hoort in dezelfde PR waar mogelijk.
- Losse repair-PR is alleen voor al gemergede kapotte main.
- Dit proces ondersteunt discipline, maar vervangt geen GitHub CI.
- Geen auto-merge; human review + manual merge blijven verplicht.
