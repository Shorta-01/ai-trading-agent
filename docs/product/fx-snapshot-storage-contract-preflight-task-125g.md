# Task 125G — FX snapshot storage contract preflight (document-first, read-only)

## 1) Purpose and boundary
Task 125F bevestigde dat er nog geen bruikbaar duurzaam FX snapshot-opslagcontract bestaat voor valuation readiness. Task 125G levert daarom bewust alleen een document-first preflight die het minimale toekomstige storage/repository/API-read contract afbakent.

Deze taak voegt **geen runtimegedrag** toe:
- geen runtime FX fetch;
- geen market-data runtime;
- geen suggesties, action drafts of orders;
- geen fake FX-rates;
- geen fake converted totals.

Doel: valuation readiness moet later benodigde valutaparen lezen uit **opgeslagen** FX snapshots, niet live ophalen tijdens readiness-bepaling.

## 2) Source-of-truth en data ownership
- Toekomstige market-data/FX providers blijven externe bron van FX-rates, maar pas na aparte runtime-provider taken.
- De lokale database wordt de duurzame bron van waarheid voor FX snapshotrecords.
- Valuation readiness mag later alleen opgeslagen FX snapshotdata lezen.
- Python/domain/storage contracten blijven eigenaar van berekeningen en statuslogica.
- AI mag geen FX-rates, converted totals of andere financiële kernwaarden genereren of overschrijven.

## 3) Minimale toekomstige storage-tabel (designvoorstel)
Voorgestelde tabelnaam: `fx_rate_snapshots` (definitieve naam volgt repository naming-conventies).

Kandidaatvelden (minimaal):
- `snapshot_id` (unieke snapshot-id, bijv. UUID/string)
- `provider` (bronprovidernaam)
- `source` (broncontext/canaal)
- `base_currency` (ISO-valutacode)
- `quote_currency` (ISO-valutacode)
- `pair` (genormaliseerd paar, bijv. `EUR/USD`)
- `rate` (**Decimal-safe**, nooit float)
- `rate_type` (bijv. mid/bid/ask/reference)
- `as_of` (provider effective timestamp)
- `received_at` (ontvangsttijd)
- `stored_at` (opslagtijd)
- `freshness_status` (contractstatus)
- `validation_status` (contractstatus)
- `reason_code` (deterministische statusreden)
- `metadata_json` (optionele bron/quality metadata)
- audit-link velden conform bestaande request/source-traceability patronen (optioneel, indien beschikbaar)

Decimal-regel:
- `rate` moet in storage/domain/API-contracten Decimal-safe zijn.
- Python dataclasses/records/protocollen mogen voor `rate` geen `float` toestaan.

## 4) Kandidaat repositorycontract (design-only)
Toekomstige methoden (namen indicatief):
- `save_fx_rate_snapshot(record)`
- `list_latest_fx_rate_snapshots_by_pairs(pairs)`
- `get_latest_fx_rate_snapshot(base_currency, quote_currency)`
- `list_fx_rate_snapshots(...)`
- optioneel: `get_fx_rate_snapshot(snapshot_id)`

Verwachte semantiek:
- Ontbrekend valutapaar retourneert expliciet ontbrekend resultaat (geen fallback/fake rate).
- Verouderde of ongeldige snapshots leiden tot `control_needed`/blocked readiness-uitkomst.
- Alle koerswaarden blijven Decimal-safe.
- Geen repositorymethode mag externe providerdata ophalen.

## 5) Kandidaat API-read contract voor valuation readiness
Toekomstige readinessvelden (designniveau):
- `fx_snapshot_contract_available`
- `fx_snapshot_data_available`
- `fx_snapshot_source`
- `fx_snapshot_count`
- `fx_snapshot_pairs_available`
- `missing_fx_pairs`
- `stale_fx_pairs`
- `invalid_fx_pairs`
- `fx_rates_available`
- `fx_conversion_allowed`
- `converted_totals_available`

Verwachte response-gedrag:
- FX niet vereist: readiness meldt `fx_not_required`; conversie blijft niet nodig.
- FX vereist maar storagecontract ontbreekt: `fx_snapshot_contract_missing` + blocked.
- FX vereist en contract bestaat maar paar ontbreekt: `fx_snapshot_missing` + blocked.
- FX vereist en paar bestaat maar stale: `fx_snapshot_stale` + control-needed/blocked.
- FX vereist en paar bestaat maar invalid: `fx_snapshot_invalid` + control-needed/blocked.
- FX vereist en alle paren valide/vers: `fx_snapshot_available`; pas dan mag `fx_conversion_allowed=true` worden.

## 6) Pair-derivation rules (toekomstig)
Benodigde valutaparen worden later afgeleid uit:
- `valuation_currencies`
- `cash_currencies`
- `portfolio_currencies`
- `base_currency` wanneer beschikbaar

Regels:
- Geen impliciete EUR/USD-default, tenzij expliciet uit opgeslagen account/settingscontext.
- Mixed position/cash currencies vereisen FX voor aggregate valuation.
- Multi-currency cash zonder posities vereist FX voor aggregate cash valuation.
- Single-currency portfolio + cash vereist geen FX-conversie.

## 7) Freshness- en validationstatus (voorstel)
Kandidaat status/reason-codes:
- `fx_not_required`
- `fx_snapshot_contract_missing`
- `fx_snapshot_missing`
- `fx_snapshot_stale`
- `fx_snapshot_invalid`
- `fx_snapshot_available`
- `fx_control_needed`
- `fx_storage_unavailable`

Nederlandse status/helptekstvoorbeelden:
- FX niet nodig
- FX-opslag ontbreekt
- Wisselkoers ontbreekt
- Wisselkoers verouderd
- Wisselkoers ongeldig
- Opgeslagen wisselkoers beschikbaar
- Controle nodig
- Geblokkeerd

## 8) Aanbevolen volgende implementatieslice
Veiligste volgende stap: **Task 125H — implementeer duurzame FX snapshot storage schema/repository contract + tests, zonder runtime provider-fetch en zonder valuation-conversieruntime.**

Niet aanbevelen als volgende slice:
- suggestieruntime;
- action-draft runtime;
- order/execution runtime;
- AI runtime;
- live provider fetch.

## 9) Toekomstige teststrategie (bij implementatie)
Verplicht bij Task 125H en opvolgers:
- storage Decimal round-trip tests voor FX-rates;
- expliciete guard tegen float-gebruik;
- pair-uniqueness/latest lookup gedrag;
- missing-pair gedrag (geen fake rates);
- stale/invalid statusgedrag;
- public exports tests als nieuwe storage records worden toegevoegd;
- migration inventory/readiness tests wanneer migratie wordt toegevoegd;
- API mypy coverage zodra API nieuwe storage records importeert;
- valuation readiness tests zodra API stored FX pairs consumeert;
- regressietests dat geen fake FX-rates of fake converted totals ontstaan.

## 10) Expliciete non-goals
Task 125G doet **niet**:
- geen FX runtime fetch;
- geen providerintegratie;
- geen market-data runtime;
- geen scheduler/background jobs;
- geen valuation conversion implementatie;
- geen suggesties;
- geen action drafts;
- geen orders/execution;
- geen fake FX-rates;
- geen fake converted totals;
- geen fake brokerdata.
