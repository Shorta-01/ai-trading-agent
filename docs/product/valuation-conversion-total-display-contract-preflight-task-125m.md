# Task 125M — Valuation conversion total display contract preflight (document-first, read-only)

## 1) Purpose and boundary
Task 125M definieert een document-first/design preflight voor toekomstige read-only UI/API-weergave van valuation conversion totals die al berekend en readiness-gated worden aangeleverd.

Deze taak verandert **geen runtimegedrag**:
- geen web UI-behavior wijzigingen;
- geen API-behavior wijzigingen;
- geen nieuwe berekeningen;
- geen runtime fetch;
- geen suggesties/action drafts/orders;
- geen fake totals;
- geen weergave van unavailable totals als `0`.

## 2) Source-of-truth and data ownership
- Python/portfolio calculator blijft eigenaar van financiële berekeningen.
- De API readiness endpoint exposeert alleen veilige resultaatsvelden.
- UI toont alleen API-aangeleverde waarden.
- UI berekent geen financiële totals.
- UI verzint geen missende waarden.
- AI mag financiële totals niet creëren, overschrijven of “uitleggen alsof ze bestaan”.

## 3) Existing API fields to be consumed later
Toekomstige read-only display mag (zonder contractwijziging in deze taak) minimaal deze velden uit `GET /portfolio/valuation/readiness` consumeren:
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
- `converted_totals_available`
- `converted_position_values_available`
- `converted_cash_values_available`
- `missing_total_value_inputs`
- `missing_market_data_conids`
- `missing_cash_inputs`
- `missing_fx_pairs`
- `stale_fx_pairs`
- `invalid_fx_pairs`
- `valuation_input_trace`

Belangrijk: Task 125M beschrijft alleen display-contractgebruik en wijzigt het API-model niet.

## 4) Simple Dutch UI labels
Aanbevolen simpele NL labels voor latere UI-implementatie:
- Totale marktwaarde
- Cashwaarde
- Totale portefeuillewaarde
- Basismunt
- Omrekening
- Omrekening klaar
- Omrekening niet nodig
- Controle nodig
- Geblokkeerd
- Marktdata ontbreekt
- Cashsnapshot ontbreekt
- Wisselkoers ontbreekt
- Wisselkoers verouderd
- Wisselkoers ongeldig
- Geen veilige totaalwaarde beschikbaar

## 5) Display rules for safe totals
Toekomstige UI-regels:
- Toon totals alleen wanneer corresponderende `*_available` boolean `true` is.
- Toon `total_portfolio_value` alleen bij `total_portfolio_value_available=true`.
- Toon `total_market_value` alleen bij `total_market_value_available=true`.
- Toon `total_cash_value` alleen bij `total_cash_value_available=true`.
- Als waarde unavailable is: toon API status/helptekst; nooit `0`, kale `N/A` zonder uitleg, of fake placeholder.
- Houd statustekst conservatief: `Controle nodig` of `Geblokkeerd` bij incomplete/onveilige inputs.
- Toon conversion totals niet als suggestie, aanbeveling, signaal of actie-label.
- Impliceer geen `Kopen`, `Verkopen`, `Houden` of ander advies vanuit valuation totals.

## 6) Formatting and rounding boundary
- API financiële waarden blijven Decimal-veilige strings.
- Toekomstige UI mag voor leesbaarheid formatteren, maar onderliggende waarde niet wijzigen.
- Display-rounding hoort in UI-weergave, niet in core-calculatie.
- Als rounding later wordt toegevoegd, moet ruwe API-waarde beschikbaar blijven voor audit/debug.
- Converteer financiële strings nooit via JavaScript floating-point arithmetic voor nieuwe berekeningen.
- Bereken geen totals in de browser.

## 7) Status and blocker display
Toekomstige UI moet blockers zo tonen:
- Missing market data: toon betrokken conids indien beschikbaar.
- Missing cash input: toon simpele Nederlandse uitleg.
- Missing FX: toon vereiste missende pair(s).
- Stale FX: toon dat wisselkoers verouderd is en controle vereist.
- Invalid FX: toon dat wisselkoers ongeldig is en totals geblokkeerd blijven.
- Missing base currency: toon dat basismunt ontbreekt.
- Unknown/incomplete input: toon conservatieve blocked/control-needed wording.

## 8) Audit/trace display
- `valuation_input_trace` is bedoeld voor audit/debug/detailweergaven, niet per se voor het hoofd-dashboard.
- Toekomstige detailweergave mag trace-id’s tonen voor:
  - latest sync run id;
  - position trace ids;
  - cash snapshot ids;
  - market snapshot ids;
  - FX snapshot ids.
- Geen totaal mag als betrouwbaar worden getoond zonder traceability.
- Hoofd-UI blijft simpel NL; diepere trace-info hoort in expanded/advanced details.

## 9) Future UI placement proposal
Aanbevolen toekomstige plaatsing (niet implementeren in Task 125M):
- Portfolio/valuation readiness-sectie of Portefeuille-detailpaneel.
- Compacte statuskaart voor totale portefeuillewaarde.
- Aparte rijen/kaarten voor marktwaarde en cashwaarde.
- Kleine status-chip voor conversion status.
- Uitklapbare `Waarom?` of `Controle` detail met blocker- en trace-info.

Task 125M implementeert deze UI niet.

## 10) Safety and non-implication wording
Verboden implicaties in toekomstige UI/API-copy:
- noem totals niet “live” zonder echte runtime freshness-gates;
- impliceer geen latest real-time price;
- impliceer geen advies/suggestie/aanbeveling/actie-readiness/order-readiness;
- impliceer niet dat FX live wordt opgehaald;
- impliceer geen compleetheid als een availability-boolean `false` is;
- impliceer niet dat brokeractie mogelijk is.

## 11) Future implementation follow-up
Aanbevolen volgende smalle slice:

**Task 125N — Implement read-only web/API-client display support for valuation conversion totals using the existing `GET /portfolio/valuation/readiness` response and the Task 125M display contract, with simple Dutch labels, no new calculations, no API behavior changes, no runtime fetch, no suggestions, no action drafts, and no orders.**
