# Task 125P — Portfolio valuation cost-basis and unrealized P/L display preflight (document-first, read-only)

## 1) Purpose and boundary
Task 125P definieert een document-first/design preflight voor toekomstige read-only weergave van kostbasis en ongerealiseerde winst/verlies in portfolio valuation.

Expliciete boundary voor Task 125P:
- geen berekeningen nu;
- geen API-behavior changes;
- geen UI-behavior changes;
- geen runtime market-data fetching;
- geen FX/provider fetch;
- geen suggesties, action drafts of orders;
- geen fake kostbasis;
- geen fake ongerealiseerde winst/verlies;
- geen unavailable waarde tonen als `0`.

## 2) Source-of-truth en data ownership
- IBKR is source of truth voor posities, quantity, average cost (indien beschikbaar), account state en broker snapshots.
- Opgeslagen market snapshots zijn de enige toegestane bron voor current price/market value inputs.
- Opgeslagen FX snapshots zijn de enige toegestane bron voor currency conversion inputs.
- Python/portfolio code moet eigenaar zijn van toekomstige kostbasis- en P/L-berekeningen.
- UI mag alleen API-aangeleverde waarden tonen.
- UI mag kostbasis of ongerealiseerde winst/verlies niet in de browser berekenen.
- AI mag kostbasis, market value, FX-rate, P/L-bedrag, P/L-percentage of actie-label niet creëren, wijzigen of afleiden.

## 3) Vereiste toekomstige opgeslagen inputs
Voordat ongerealiseerde P/L getoond mag worden, zijn minimaal deze opgeslagen inputs nodig:
- latest durable IBKR sync run;
- opgeslagen position snapshot;
- position quantity;
- position currency;
- opgeslagen average cost of broker-provided cost-basis field;
- opgeslagen latest market-data snapshot voor die positie;
- market-data freshness/validation status;
- opgeslagen FX snapshot als market/cost/base currencies verschillen;
- FX freshness/validation status;
- base currency wanneer conversie vereist is;
- trace-id's voor alle gebruikte inputs.

Als een vereiste input ontbreekt, stale is, ongeldig is of ambigu is, blijft P/L unavailable.

## 4) Kostbasisregels
Toekomstige regels:
- Kostbasis mag alleen uit opgeslagen IBKR position data komen of uit een later expliciet gedocumenteerd broker cost-basis field.
- Geen kostbasis verzinnen vanuit current market value.
- Geen kostbasis afleiden vanuit portfolio value.
- Geen `0` als fallback-kostbasis gebruiken.
- Missing average cost mag nooit als `0` behandeld worden.
- Average cost currency niet stilzwijgend converteren.
- Average cost-semantiek niet aannemen als brokerfield ambigu is.
- Als average cost bestaat maar unit-semantiek onduidelijk is: markeer `Controle nodig`.
- Als quantity ontbreekt of ongeldig is: blokkeer kostbasis en P/L.
- Als position quantity `0` is: P/L alleen als `0` of unavailable na expliciet toekomstig contract.
- Shortposities vallen buiten scope voor Version 1; bij detectie nu markeren als `Geblokkeerd`.

## 5) Ongerealiseerde P/L-regels
- Ongerealiseerde P/L mag alleen berekend worden als veilige current market value minus veilige kostbasis.
- Ongerealiseerde P/L-percentage mag alleen berekend worden als kostbasis positief en veilig is.
- Als kostbasis `0`, missing, negatief, ambigu of onveilig is, blijft P/L-percentage unavailable.
- P/L mag niet berekend worden als market data missing, stale of invalid is.
- P/L mag niet berekend worden als FX vereist is maar missing, stale of invalid is.
- P/L mag geen actie-label impliceren.
- P/L mag geen `Kopen`, `Verkopen`, `Houden`, `Verminderen`, `Vermijden` of andere adviesimplicatie bevatten.

## 6) Currency- en FX-regels
- Native-currency P/L mag alleen getoond worden als native market value en native kostbasis dezelfde bekende valuta hebben.
- Converted P/L mag alleen getoond worden als base currency bekend is en alle vereiste opgeslagen FX snapshots fresh/valid zijn.
- Geen impliciete EUR/USD-default.
- Geen inverse FX pair-synthese.
- Geen browser-side conversie.
- Missing FX blokkeert converted P/L.
- Stale FX leidt tot `Controle nodig` of blokkeert.
- Invalid FX blokkeert converted P/L.

## 7) Candidate future API fields (design-only)
Mogelijke toekomstige responsevelden (niet implementeren in Task 125P):
- `cost_basis_available`
- `cost_basis`
- `cost_basis_currency`
- `cost_basis_status`
- `cost_basis_status_nl`
- `cost_basis_help_nl`
- `unrealized_pl_available`
- `unrealized_pl`
- `unrealized_pl_currency`
- `unrealized_pl_percent_available`
- `unrealized_pl_percent`
- `converted_unrealized_pl_available`
- `converted_unrealized_pl`
- `base_currency`
- `missing_cost_basis_inputs`
- `missing_pl_inputs`
- `missing_pl_market_data_conids`
- `missing_pl_fx_pairs`
- `stale_pl_fx_pairs`
- `invalid_pl_fx_pairs`
- `cost_basis_input_trace`
- `unrealized_pl_input_trace`

Belangrijk: dit zijn kandidaatvelden voor latere taken; Task 125P wijzigt geen API-modellen.

## 8) Candidate statuscodes en eenvoudige Nederlandse labels
Candidate statuscodes:
- `cost_basis_ready`
- `cost_basis_missing`
- `cost_basis_ambiguous`
- `cost_basis_blocked_invalid_quantity`
- `cost_basis_blocked_short_position`
- `pl_ready`
- `pl_blocked_missing_cost_basis`
- `pl_blocked_missing_market_data`
- `pl_blocked_missing_fx`
- `pl_control_needed_stale_market_data`
- `pl_control_needed_stale_fx`
- `pl_blocked_invalid_fx`
- `pl_blocked_incomplete_inputs`

Eenvoudige Nederlandse labels:
- Kostbasis klaar
- Kostbasis ontbreekt
- Kostbasis onduidelijk
- Aantal ongeldig
- Shortpositie niet ondersteund
- Ongerealiseerde winst/verlies klaar
- Marktdata ontbreekt
- Wisselkoers ontbreekt
- Wisselkoers verouderd
- Wisselkoers ongeldig
- Controle nodig
- Geblokkeerd
- Geen veilige winst/verlieswaarde beschikbaar

## 9) Displayregels voor toekomstige UI
- Toon kostbasis alleen wanneer `cost_basis_available=true`.
- Toon ongerealiseerde P/L alleen wanneer `unrealized_pl_available=true`.
- Toon ongerealiseerde P/L-percentage alleen wanneer `unrealized_pl_percent_available=true`.
- Als unavailable: toon API status/helptekst, niet `0` en geen fake placeholder.
- Negatieve P/L alleen tonen als negatief wanneer backend die veilig heeft berekend.
- Geen kleurcodering of label gebruiken dat advies impliceert.
- Geen koop/verkoop/houden-woordgebruik naast P/L-totalen.
- Hoofd-UI blijft simpel Nederlands.
- Detailtrace hoort in advanced detailsectie.

## 10) Traceability- en auditregels
- Geen kostbasis zonder trace naar opgeslagen IBKR snapshot.
- Geen current market value zonder trace naar opgeslagen market snapshot.
- Geen conversie zonder trace naar opgeslagen FX snapshot.
- Geen P/L zonder trace naar alle vereiste inputs.
- Trace bevat minimaal: latest sync run id, position snapshot-identiteit, market snapshot-identiteit, FX snapshot-identiteit (indien gebruikt), en kostbasis source-field.
- Toekomstige UI mag trace alleen in advanced view tonen.

## 11) Safety en non-implication wording
Expliciet verboden:
- P/L `live` noemen zonder runtime freshness-gates;
- latest real-time price impliceren;
- investment advice impliceren;
- order readiness impliceren;
- action-draft readiness impliceren;
- brokeractie-mogelijkheid impliceren;
- impliceren dat missing kostbasis `0` is;
- impliceren dat FX live is opgehaald;
- impliceren dat stale data veilig is.

## 12) Future implementation sequence
Aanbevolen volgende smalle veilige slice:

**Task 125Q — Implement a pure Decimal-only cost-basis and unrealized P/L calculator module with unit tests, based only on caller-provided stored inputs, without API wiring, without UI changes, without runtime market-data/FX fetch, without suggestions, without action drafts and without orders.**

Waarom:
- houdt risico klein;
- test Decimal-only berekeningen vóór API/UI wiring;
- voorkomt runtime-implicaties;
- volgt het Task 125K-patroon.

## 13) Expliciete non-goals
Task 125P implementeert niet:
- calculation runtime;
- API model changes;
- endpoint changes;
- UI changes;
- storage changes;
- FX/provider fetch;
- market-data runtime;
- latest-price fetching;
- suggesties;
- action drafts;
- orders;
- fake data.
