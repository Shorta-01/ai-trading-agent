# Task 125J — Valuation conversion-total preflight (document-first, read-only)

## 1) Purpose and boundary
Task 125J definieert de minimale, veilige ontwerpgrenzen voor toekomstige geconverteerde valuation totals in basismunt.

Waarom nodig:
- Na Task 125I/125I-R kan readiness aangeven of opgeslagen FX-paren beschikbaar, missing, stale of invalid zijn.
- Het systeem berekent nog **geen** geconverteerde totaalsommen.
- Zonder expliciete criteria zou runtime later risico lopen op silent defaults, onveilige conversie of onduidelijke audit-trace.

Boundaries van Task 125J:
- Alleen design/preflight, geen runtime-implementatie.
- Alleen reeds opgeslagen inputbronnen zijn toegestaan.
- Geen runtime FX/provider fetch.
- Geen fake FX-rates, fake cash values, fake prijzen of fake converted totals.
- Geen suggesties, action drafts of orders.

## 2) Source-of-truth and data ownership
Toekomstige converted totals mogen alleen worden afgeleid uit duurzame, lokaal opgeslagen records:
- Duurzame IBKR snapshots (positie/cash) zijn bron voor portfolio- en cash-inputs.
- Opgeslagen market-data latest snapshots zijn bron voor native market-prijzen.
- Opgeslagen FX snapshots zijn bron voor wisselkoersconversie.
- Lokale database is bron van waarheid voor readiness/workflow/valuation-inputs.
- Python + Decimal berekent financieel resultaat.
- AI mag geen financiële waarden, prijzen, rates of totals creëren/overschrijven.

## 3) Required stored inputs for future converted totals
Future conversion totals zijn alleen toegestaan als de minimale inputset compleet en valide is:
- latest durable IBKR sync run aanwezig (`latest_sync_run_id`).
- position snapshots voor die run.
- cash/account snapshots voor die run.
- valide opgeslagen latest market snapshots voor alle posities die market value vereisen.
- valide opgeslagen FX snapshots voor alle vereiste valutaparen.
- bekende base currency.
- timestamps per input (sync, market, FX, cash).
- freshness/validation status voor market data en FX.
- Decimal-veilige hoeveelheden, prijzen, rates en cashwaarden.

## 4) Base currency rules
Voor toekomstige totaalsommen gelden strikte basismuntregels:
- Geen impliciete EUR/USD-default.
- Base currency mag alleen uit opgeslagen accountdata komen, expliciete settings, of een toekomstige gevalideerde gebruikersinstelling.
- Als base currency ontbreekt: converted totals blijven unavailable.
- Multi-currency cash zonder bekende base currency => control-needed/blocked.
- Gemengde positie- en cash-valuta vereisen base currency vóór aggregatie.
- Single-currency portfolio/cash mag native totaalcurrency gebruiken, maar alleen als alle inputs exact dezelfde valuta delen.

## 5) FX pair rules
Vereiste FX-paren moeten deterministisch afleidbaar zijn uit inputvaluta + base currency:
- Required pair-derivatie is deterministisch en testbaar.
- Geen automatische inverse pair-synthese tenzij expliciet in een latere taak ontworpen.
- Als opgeslagen pair-richting niet matcht met required pair, niet stilzwijgend inverteren.
- Missing pair blokkeert converted totals.
- Stale pair blokkeert of markeert control-needed (conservatief).
- Invalid pair blokkeert of markeert control-needed (conservatief).
- Unknown freshness/validation status moet conservatief als onveilig behandeld worden.

## 6) Calculation boundaries
Alleen wanneer alle veilige criteria gehaald zijn, mag toekomstige runtime berekenen:
- per-position native market value;
- per-position base-currency market value;
- native cash values;
- base-currency cash values;
- total market value in base currency;
- total cash value in base currency;
- total portfolio value in base currency;
- optioneel unrealized P/L in base currency, alleen met veilige cost-basis + FX-inputs.

Moet unavailable blijven zodra input incompleet/onveilig is:
- elk totaal met ontbrekende prijsinput;
- elk totaal met ontbrekende cashinput;
- elk totaal met ontbrekende FX-input;
- elke conversie met stale/invalid FX;
- elk totaal met onbekende base currency;
- elk P/L-resultaat zonder average cost/cost basis.

## 7) Decimal and rounding rules
Toekomstige financiële conversie volgt strikte Decimal-veiligheid:
- Geen float-berekeningen in financiële totals.
- API-serialisatie van financiële outputs als Decimal-veilige strings.
- Geen silent rounding in core-berekening.
- Ruwe precision blijft apart van UI-display formatting.
- Display rounding hoort later in UI-laag, niet in core-waarderingsberekening.
- Tests moeten Decimal round-trip en exact calculation cases bewijzen.

## 8) Readiness/status contract proposal
Task 125J stelt een candidate contract voor toekomstige valuation conversion readiness.

Candidate velden:
- `conversion_total_status`
- `conversion_total_status_nl`
- `conversion_total_help_nl`
- `base_currency`
- `total_market_value_available`
- `total_market_value`
- `total_cash_value_available`
- `total_cash_value`
- `total_portfolio_value_available`
- `total_portfolio_value`
- `missing_total_value_inputs`
- `missing_market_data_conids`
- `missing_cash_inputs`
- `missing_fx_pairs`
- `stale_fx_pairs`
- `invalid_fx_pairs`
- `converted_position_values_available`
- `converted_cash_values_available`
- `valuation_input_trace`

Candidate statuscodes:
- `conversion_not_required`
- `conversion_ready`
- `conversion_blocked_missing_base_currency`
- `conversion_blocked_missing_market_data`
- `conversion_blocked_missing_cash`
- `conversion_blocked_missing_fx`
- `conversion_control_needed_stale_market_data`
- `conversion_control_needed_stale_fx`
- `conversion_blocked_invalid_fx`
- `conversion_blocked_incomplete_inputs`

Voorbeeld NL status/help labels (eenvoudig):
- Omrekening niet nodig
- Totaalwaarde klaar
- Basismunt ontbreekt
- Marktdata ontbreekt
- Cashsnapshot ontbreekt
- Wisselkoers ontbreekt
- Wisselkoers verouderd
- Wisselkoers ongeldig
- Controle nodig
- Geblokkeerd

## 9) Audit/traceability rules
Geen totaal zonder herleidbare bronketen.

Minimale trace-eisen:
- Elk totaal traceerbaar naar `latest_sync_run_id`.
- Elke position value traceerbaar naar position snapshot-id of stabiele row-identiteit.
- Elke market value traceerbaar naar market snapshot-id.
- Elke FX-conversie traceerbaar naar FX snapshot-id.
- Elke cash value traceerbaar naar cash snapshot-id of duurzame record-identiteit.
- Responsecontract moet voldoende tracemetadata bevatten voor audit/debug.
- Geen opaque totaalsommen.

## 10) Future test strategy
Verplichte toekomstige testgroepen vóór runtime-unlock:
- Decimal-only calculation tests.
- Single-currency totals zonder FX-behoefte.
- Multi-currency positions met valide opgeslagen FX.
- Multi-currency cash met valide opgeslagen FX.
- Missing market data blokkeert totals.
- Stale market data blokkeert of markeert control-needed.
- Missing FX blokkeert totals.
- Stale FX blokkeert of markeert control-needed.
- Invalid FX blokkeert totals.
- Missing base currency blokkeert totals.
- Geen inverse pair synthese.
- Geen zero-fallback.
- Geen fake totals.
- API-serialisatie als strings.
- Safety booleans blijven false/blocked wanneer criteria niet gehaald zijn.
- Regressietests voor bestaand Task 125D/125E/125F/125I-readiness gedrag.

## 11) Recommended future implementation sequence
Aanbevolen volgende smalle slice:

**Task 125K — implementeer een Decimal-only conversion-total calculator module met unit tests, zonder API wiring en zonder runtime fetch/providerintegratie.**

Reden:
- Houdt risico klein en toetsbaar (pure berekenmodule + tests).
- Valideert eerst contract- en Decimal-criteria voordat API-responses uitgebreid worden.
- Vermijdt vroegtijdige runtime implicaties.

Niet aanbevelen in Task 125K:
- runtime FX/provider fetch;
- market-data runtime;
- suggesties;
- Decision Packages runtime;
- action drafts;
- broker execution.

## 12) Explicit non-goals (Task 125J)
Task 125J doet expliciet **niet**:
- geen converted-total runtime;
- geen API calculation implementation;
- geen storage migration;
- geen FX runtime fetch;
- geen providerintegratie;
- geen market-data runtime;
- geen scheduler/background jobs;
- geen suggesties;
- geen action drafts;
- geen orders/execution;
- geen fake FX-rates;
- geen fake converted totals;
- geen fake brokerdata.
