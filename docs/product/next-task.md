## Task 71: Asset master identity foundation (recommended)

Doel: een stabiele asset-identiteitslaag toevoegen zodat bronkoppeling, market data, portfolio/watchlist, freshness en probabilistische outlook-functies correct op één consistente asset-identiteit kunnen bouwen.

### Waarom nu

- Task 70 source conflict detection foundation is geïmplementeerd als storage/API foundation.
- Task 70B repair is afgerond en CI staat groen.
- Research/evidence/gate/conflict foundations bestaan nu, maar missen nog een stabiele asset-identiteit als verbindende basis.
- Zonder asset master identity ontstaan later fouten in source-to-asset linking, data freshness en probabilistische outlook traceability.

### In scope (Task 71)

- Asset master identity foundation (canonieke asset-identiteit, mapping-basis en audit-traceability foundation).
- Geen suggestion runtime unlock.
- Geen AI/watchlist/IBKR/order runtimegedrag.

### Alternatieve latere taken (niet aanbevolen als eerstvolgende)

- Market calendar/freshness runtime foundation.
- Source-to-asset linking foundation.
- Asset detection foundation.
\n\n- Task 71: asset master identity foundation toegevoegd; identity is alleen referentie/status data, geen watchlist/portfolio/suggestie/IBKR/order/AI/market-data/forecast runtime.
