# Task 125F — FX snapshot contract inventory (read-only)

## Scope
Task 125F inventariseert alleen bestaande opslag/API-contracten voor FX-readiness en koppelt die read-only aan `GET /portfolio/valuation/readiness`.

Niet toegevoegd in Task 125F:
- geen FX runtime fetch
- geen market-data runtime
- geen suggesties/action drafts/orders/execution
- geen fake FX-rates
- geen fake converted totals

## Inventoryresultaat
Doorzoeking van `packages/storage/src`, `packages/storage/tests`, `apps/api/src`, `apps/api/tests`, `packages/domain/src`, `packages/portfolio/src` en productdocs toont:

- Er bestaat **geen** specifieke FX-rate snapshot tabel in storage.
- Er bestaat **geen** FX-rate record/dataclass in storage public contracten.
- Er bestaat **geen** FX-rate repository-methode voor opgeslagen valutaparen.
- De bestaande market-data snapshot contracten zijn conid-gebaseerd (instrumentprijzen) en modelleren geen valuta-paar FX-rates.
- Er bestaat dus geen bruikbaar read-only opslagcontract dat valuation readiness veilig kan lezen voor FX pair rates.

## Gevolg voor readiness
Task 125F rapporteert nu expliciet:
- `fx_snapshot_contract_status=fx_snapshot_contract_missing`
- `fx_snapshot_contract_available=false`
- `fx_snapshot_data_available=false`

Hiermee blijft FX-required waardering eerlijk geblokkeerd (`Geblokkeerd` / `Controle nodig`) zonder runtime fetch of verzonnen waarden.

## Volgende veilige slice na Task 125F
Task 125G (aanbevolen): document-first contractslice voor een duurzame FX snapshot storage-contractdefinitie (schema/repository/API-read contract), nog steeds zonder runtime provider-fetch.
