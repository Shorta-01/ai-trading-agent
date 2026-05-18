# Web (Next.js)

Moderne, snelle en eenvoudige Nederlandstalige webinterface voor AI-Trading-Agent.

## Dashboard foundation (Task 18)
- Modern Nederlandstalig dashboard met veilige read-only secties.
- Data komt uit read-only endpoints: `/system/status`, `/settings/summary`, `/usage/ai/summary`, `/integrations/summary`.
- Bij backend-uitval toont de UI duidelijk: **API niet bereikbaar**.
- Geen fake portefeuilledata, geen fake prijzen, geen fake actiesuggesties.
- Geen instellingen bewerken in deze stap.
- Geen orderplaatsing, geen live trading, paper-only.

## Lokaal starten

```bash
cd apps/web
npm install
npm run dev
```

## Controles

```bash
cd apps/web
npm run lint
npm run build
```
\n## Storage foundation update\nOpslagreadiness-contracten toegevoegd; opslag is nog niet ingesteld en setup/transacties worden nog niet bewaard. Backup blijft onveilig tot hersteltest slaagt.
