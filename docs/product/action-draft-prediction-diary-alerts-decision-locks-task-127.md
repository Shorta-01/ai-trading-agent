# Task 127 — Action Draft, Prediction Diary and Alerts Decision Locks

## Purpose
Deze documentatie vergrendelt productbeslissingen uit Task 127. Dit document wijzigt **geen runtimegedrag**.

## 1. Product identity and account mode
- Portfolio Outlook Manager is een IBKR portfolio- en watchlist-intelligence/suggestiesysteem.
- IBKR is operationele bron van waarheid voor posities, cash, orders, executies en accountstatus.
- Lokale database is workflow/model/suggestie/draft/audit bron van waarheid.
- GUI moet accountmodus duidelijk tonen: paper of real-money.
- Workflow is account-mode-aware, niet paper-only als productidentiteit.
- Geen brokeractie zonder expliciete usergoedkeuring.

## 2. Asset scope
Version 1 start met: aandelen, ETF’s en niet-gehevelde goud-ETF/ETC blootstelling.
Niet in startscope: opties, futures, leverage, short selling, crypto, CFD’s, complexe derivaten, fractionele aandelen.

## 3. Suggestion horizon and risk profile
- Primaire horizon: 1–6 maanden.
- Secundaire context: 6–12 maanden.
- Korte termijn-signalen alleen als sterke multi-signal bevestiging, als kansmelding/review nodig.
- Standaard risicoprofiel: Balanced; instelbaar: Conservative/Balanced/Aggressive.

## 4. Suggestions and confidence
Suggestie bevat: action label, confidence label + score, uitkomstkans waar beschikbaar, simpele Nederlandse uitleg, drivers, risico’s, en wat fout kan gaan.
Confidence betekent bewijskracht/validatiekwaliteit, niet toekomstzekerheid.

## 5. Editable action drafts
Suggestie (redenatie) en action draft (exact orderobject) zijn gescheiden.
Actionable suggesties moeten exacte bewerkbare drafts kunnen opleveren.

## 6. Order type scope
Eerste draft-scope: whole shares/units, Buy/Sell, Limit, Day, expliciet bewerkbare velden, backend-validatie na edits, geen auto-send.

## 7. Staged, scheduled and triggered drafts
- Staged plannen mogen, maar elke order blijft apart bewerkbaar/goed te keuren.
- Eerste conditional scope: lokale schedule/price-trigger drafts.
- Trigger = opnieuw valideren + opnieuw usergoedkeuring.
- Geen automatische vertraagde of price-triggered uitvoering.

## 8. Switch plans
Sell-to-buy switchplannen mogen als gelinkte redenatie, met losse bewerkbare orders en aparte approvals.

## 9. Manual orders
Handmatige drafts zijn toegestaan, gescheiden van systeemvoorstellen en met waarschuwingen/override-reden/audit.

## 10. Hard blockers and soft blockers
- Hard blockers: niet overridebaar.
- Soft blockers: override met verplichte reden.

## 11. What-if simulation
Elke draft/plan vereist what-if vóór approval (cash, gewicht, risico, scenario’s, partial fill, risk-profile fit).

## 12. Dry-run validation
Verplicht vóór send: backend bouwt exact IBKR-compatibel orderobject zonder verzending, met volledige checkset en auditopslag.

## 13. Final confirmation
Na geldige dry-run volgt expliciete finale knop (geen typed confirm verplicht).

## 14. Cancellation flow
Eerste versie: één-voor-één user-goedgekeurde annulatie, met aparte draft, dry-run en final confirm.

## 15. Partial fills
Basis partial-fill tracking is Version 1 scope, met automatische herevaluatie van resterende hoeveelheid (zonder auto-modify/cancel).

## 16. Active order revalidation
Na IBKR sync en periodiek: actieve orders herbeoordelen met status: Nog geldig / Controle nodig / Verouderd / Conflict / Niet meer uitvoerbaar.

## 17. Prediction Diary
Prediction Diary is Version 1 scope, met outcome-tracking over meerdere horizons en vergelijking met benchmark/do nothing/cash.
Geen stille zelflerende productie-updates.

## 18. Suggestion versioning and draft invalidation
Alleen latest active suggestie in hoofdviews; historie blijft.
Bij suggestiewijziging: oude drafts stale/paused volgens statusregels; geen auto-cancel van actieve IBKR orders.

## 19. Alerts
Sterke in-app alerts zijn Version 1 scope (dashboard, panel, action center, rijen, detail).
Critical alerts zijn niet uitschakelbaar en vereisen acknowledgement/resolutie met audit.

## 20. Daily briefing
In-app daily briefing is Version 1 scope met duidelijke datakwaliteitswaarschuwingen waar data mist/stale is.

## 21. Explicit non-runtime boundary for this task
Task 127 is documentatie-only:
- geen runtime code,
- geen tests,
- geen migrations,
- geen workflows,
- geen package metadata,
- geen UI code,
- geen trading/execution implementatie.
