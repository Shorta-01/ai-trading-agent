# Task 127 — Action Draft, Prediction Diary and Alerts Decision Locks

## Purpose
Deze documentatie vergrendelt productbeslissingen uit Task 127 en Task 127R. Dit document wijzigt **geen runtimegedrag**.

## 1. Product identity and account mode
- Portfolio Outlook Manager is een account-mode-aware IBKR portfolio- en watchlist-intelligence/suggestiesysteem.
- GUI toont zichtbaar of de verbonden IBKR-account paper of real-money is.
- Analyse-, suggestie-, action-draft- en approvalworkflow blijft hetzelfde in beide accountmodi.
- Geen brokeractie zonder expliciete usergoedkeuring.
- Geen automatische submit/modify/cancel van brokerorders.
- IBKR is operationele bron van waarheid voor portfolio, cash, posities, orders, executions/fills en accountstatus.
- Lokale app/database is bron van waarheid voor workflow, modeluitkomsten, suggesties, drafts, validatie, audit en Prediction Diary.

## 2. Asset scope
- Version 1 start met aandelen, ETF’s en niet-gehevelde goud-ETF/ETC-blootstelling.
- Niet in initiële scope: opties, futures, leverage, short selling, crypto, CFD’s, complexe derivaten en fractionele aandelen.
- Goudscope: enkel goud-ETF/ETC; geen fysiek goud, futures of leveraged goudproducten.
- Goudanalyse gebruikt trend, volatiliteit, correlatie, reële rente/macro, FX/inflatiecontext en diversificatie-impact.
- Goud wordt niet gewaardeerd alsof het een bedrijf is.

## 3. Suggestion horizon and risk profile
- Primaire horizon: 1–6 maanden.
- Secundaire context: 6–12 maanden.
- Kortere high-conviction kansen mogen alleen bij sterke multi-signaalbevestiging.
- Deze signalen zijn opportunity/review-needed meldingen, geen noisy daytrading-signalen.
- Standaard risicoprofiel: Balanced.
- Userkeuze: Conservative / Balanced / Aggressive.
- Risicoprofiel beïnvloedt cashbuffer, blootstellingslimieten, koop/verkoopdrempels, volatiliteitstolerantie, opportunity-thresholds, positie-sizing en uitlegtekst.

## 4. Suggestions and confidence
- Het systeem toont de beste toegelaten actie op basis van data en gates.
- Suggesties mogen niet kunstmatig afgezwakt worden.
- Elke suggestie bevat action label, confidence label, confidence score, uitkomstkans waar beschikbaar, Nederlandse uitleg, drivers, risico’s en wat het ongeldig kan maken.
- Zowel label als score worden getoond (bijv. Hoog 88/100).
- Confidence betekent sterkte van evidence/model/data/gates; het is geen toekomstgarantie.
- Outcome probability blijft apart en komt uit Python/modelcode, niet uit AI-tekstgeneratie.

## 5. Editable action drafts
- Suggestie en action draft zijn aparte objecten.
- Actionable suggesties kunnen exacte bewerkbare action drafts genereren.
- Drafts zijn gestructureerde IBKR-compatibele dataobjecten, geen vrije tekst.
- Draftvelden bevatten minimaal asset, symbol, IBKR conid, exchange, currency, action, quantity, order type, limit price, time in force, account mode, estimated order value, estimated cash after order, portfolio weight after order, risk-checkstatus, data-freshnessstatus, confidence, linked suggestion, linked Decision Package, explanation en approve/edit/reject controls.
- Draftbewerking gebeurt via een geldige gestructureerde GUI-vorm of grid.

## 6. Order type scope
- Eerste uitvoerbare action-draftversie: whole shares/units, Buy/Sell, Limit, Day.
- Geen fractionele shares.
- Geen market/stop/stop-limit/trailing/bracket/GTC/complexe ordertypes in eerste versie.
- Backend valideert draft opnieuw na edits.
- Geen auto-send.
- Geen directe active-order modification in eerste uitvoerversie.

## 7. Staged, scheduled and triggered drafts
- Staged orders mogen als één plan zichtbaar zijn.
- Elke individuele draft blijft apart bewerkbaar en apart goed te keuren.
- Approve-all kan pas later en alleen als alle drafts slagen en planimpact volledig zichtbaar is.
- Scheduled/price-triggered drafts zijn eerst lokaal.
- Trigger of datum veroorzaakt verplichte revalidatie en nieuwe usergoedkeuring.
- Geen automatische delayed execution.
- Geen automatische price-triggered execution.
- Geen long-lived conditionele IBKR-order in eerste versie.

## 8. Switch plans
- Sell-to-buy switchplannen zijn toegestaan als gelinkte plannen.
- Workflow toont waarom asset A zwakker is en asset B sterker.
- Elke order blijft apart bewerkbaar en apart goed te keuren.
- Geen automatische sell-to-buy uitvoering.

## 9. Manual orders
- Handmatige user-created drafts zijn toegestaan.
- Manual drafts blijven gescheiden van system-generated drafts.
- Aanbevolen tabs in IBKR Action Center:
  - Systeemvoorstellen
  - Mijn eigen orders
  - Actief bij IBKR
  - Historiek
- Manual orders krijgen basisveiligheidschecks.
- Bij conflict met systemsuggestie: waarschuwing + verplichte reden.
- Manual orders tellen mee in audit/outcome history, maar niet in system prediction accuracy.
- Manual orders zonder geldige systemsuggestie zijn toegestaan met extra waarschuwing, extra confirmatie en verplichte userreden.

## 10. Hard blockers and soft blockers
Hard blockers (niet overridebaar):
- ongeldige/ontbrekende IBKR contractidentiteit
- ongeldige quantity
- ongeldige limit price
- buy > beschikbare cash
- sell > beschikbare positie
- ontbrekende IBKR accountstatus
- ontbrekend verplicht orderveld
- niet-ondersteunde route/type
- geen geldig IBKR-orderobject op te bouwen

Soft blockers (override met reden):
- manual order conflicteert met suggestie
- positie wordt groter dan aanbevolen
- concentratierisico stijgt
- volatiliteit hoog
- confidence laag
- geen geldige systemsuggestie
- benchmark ontbreekt voor diepere analyse
- verhoogd nieuwsrisico
- suggestie recent gewijzigd

Critical warnings zijn nooit uitschakelbaar.

## 11. What-if simulation
- Elke draft of plan vereist what-if vóór approval.
- What-if toont cash vóór/na, posities vóór/na, gewichten vóór/na, sector- en valuta-exposure-impact, totaal risico-effect, expected risk-adjusted improvement, downside scenario, partial-fill scenario, prijsbeweging vóór uitvoering en fit met risicoprofiel.
- User mag scenario-aannames aanpassen: quantity, assumed fill price, partial-fill assumption, extra cash contribution, risicoprofielscenario en expected price movement.
- Elke wijziging triggert revalidatie.
- Scheiding blijft hard: what-if-scenario is geen echte order; editable draft bevat de echte ordervelden.

## 12. Dry-run validation
- Dry-run is verplicht vóór een goedgekeurde order naar IBKR kan gaan.
- Backend bouwt exact IBKR-compatibel orderobject zonder verzending.
- Dry-run controleert accountstatus, accountmode, contractidentiteit, action, quantity, order type, limit price, time in force, cash/positie, market status, alignment met laatste suggestie, hard blockers, soft blockers met override-redenen, audit readiness, approval validity en stale state.
- Exact dry-run resultaat wordt opgeslagen met draft-id, suggestion-id, Decision Package-id, account-id/status/mode, assetidentiteit, conid, ordervelden, impactschatting, blockerresultaten, override-redenen, validatietimestamp, exact IBKR-orderobject en pass/fail + failreason.
- Geldigheid: tijdens markthours 60 seconden; buiten markthours tot market-open tenzij relevante data wijzigt.
- Dry-run vervalt bij wijzigingen in draft/cash/positie/prijs/accountstatus/marketstatus/suggestie/orderstatus.

## 13. Final confirmation
- Na geldige dry-run volgt final confirmation.
- Normale knop is voldoende in paper én real-money modus.
- Geen typed confirmation vereist.
- Knopteksten:
  - Definitief verzenden naar IBKR
  - Definitief annuleren bij IBKR
- Final send-knop blijft disabled als data of validatie stale is.

## 14. Cancellation flow
- Eerste versie ondersteunt annuleren van één actieve IBKR-order per keer.
- Geen cancel-all in eerste versie.
- Geen automatische annulatie.
- Annulatie gebruikt aparte draft- en audittrail.
- Annulatie vereist dry-run en final confirmation.
- Dry-run checkt dat order bestaat, bij correcte account hoort, actief en annuleerbaar is, nog niet filled/cancelled is, status vers is, reden is vastgelegd en approval geldig is.

## 15. Partial fills
- Version 1 ondersteunt basis partial-fill tracking.
- Minimaal zichtbaar: approved quantity, filled quantity, remaining quantity, average fill price, cash used/received, huidige IBKR-status, remaining active quantity, of laatste suggestie nog past, en review-needed indicator.
- Na partial fill wordt resterende quantity automatisch herevalueerd.
- Geen automatische modify/cancel.

## 16. Active order revalidation
- Actieve IBKR-orders worden na elke IBKR-sync en later periodiek gerevalideerd.
- Revalidatiecheck omvat IBKR-orderstatus, gevuld/resterend volume, recente positie/cash/marktprijs, laatste suggestie, marktdatafressness, accountstatus, risicoprofiel-fit, oorspronkelijke Decision Package-fit, conflicts met gewijzigde suggestie en prijsdrift t.o.v. originele logica.
- Statuslabels:
  - Nog geldig
  - Controle nodig
  - Verouderd
  - Conflict
  - Niet meer uitvoerbaar

## 17. Prediction Diary
- Prediction Diary is Version 1 scope.
- Referentie voor leren is marktuitkomst, niet userbeslissing als waarheid.
- Userkeuze blijft auditcontext.
- Track minimaal: suggestion timestamp, asset, benchmark, suggested action, proposed draft, horizon, confidence score, expected range/outcome, modelversie, gebruikte data, hoofdredenen, userbeslissing, marktuitkomst op 1 dag/1 week/1 maand/3 maanden/6 maanden, resultaat vs do nothing, benchmark en cash, plus right/wrong/early/late/inconclusive met uitleg.
- Weergaven: globale prestatie, per-asset prestatie, eenvoudige Nederlandse userview en geavanceerde auditview.
- Geen stille zelflerende productie-updates; modelverbetering via gecontroleerde versioning/backtesting/validatie.

## 18. Suggestion versioning and draft invalidation
- Hoofd-UI toont alleen laatste actieve suggestie.
- Historie/detail toont vorige suggesties.
- Suggestiewijziging vereist expliciete diff: wat wijzigde en waarom.
- Oude suggesties worden nooit overschreven.
- Bij suggestiewijziging:
  - unapproved drafts worden stale/blocked tot revalidatie
  - approved maar ongesend drafts pauzeren en vragen re-approval
  - actieve IBKR-orders worden niet automatisch gecanceld of aangepast
  - conflicterende actieve orders worden voor review gemarkeerd
  - systeem mag cancellation/review draft voorstellen
  - brokeractie blijft user-goedkeuring vereisen

## 19. Alerts
- Version 1 bevat in-app alerts in dashboard, notification panel, IBKR Action Center, portfolio/watchlist-rijen, assetdetail en draft/orderdetail.
- Prioriteiten:
  - Kritiek
  - Hoog
  - Normaal
  - Laag
- Kritieke alerts vereisen acknowledgement of resolution en zijn niet uitschakelbaar.
- Voorbeelden: conflict actieve order vs suggestie, stale approved draft, hard blocker, ongeldige accountstatus/assetidentiteit, onvoldoende cash, sell > positie, stale data tijdens approval/send, verlopen Decision Package, partial-fill conflict, dry-run failure.
- Acknowledgements komen in audittrail.
- Acknowledged alerts mogen zichtbaar blijven of terugkomen als het probleem onopgelost blijft.
- Alleen niet-kritieke alerts zijn configureerbaar.
- Geen email/push in eerste versie (architectuur mag later uitbreiden).

## 20. Daily briefing
- Version 1 bevat een in-app daily briefing.
- Briefing wordt gegenereerd bij app-open wanneer briefing van vandaag ontbreekt, via manuele refresh en later via vaste scheduling.
- Focus: wat veranderde sinds vorige briefing.
- Secties: portfolio vandaag, gewijzigde suggesties, orders met reviewbehoefte, cashpositie, belangrijke risico’s, kansen, Prediction Diary-updates, komende events, datakwaliteit.
- Partiële briefing is toegestaan bij ontbrekende/stale data.
- Betroffen secties tonen duidelijke data-quality warnings.
- Geen verzonnen suggesties of advies als data ontbreekt.

## 21. Explicit non-runtime boundary for this task
Task 127R is documentatie-only:
- geen runtime code
- geen tests (behalve docs tooling indien nodig)
- geen migrations
- geen workflows
- geen package metadata
- geen UI code
- geen trading/execution implementatie
- geen suggestieruntime
- geen action-draftruntime
- geen market-dataruntime
- geen AI runtime
- geen scheduler runtime
