# Go-Live Runbook (V1.2 §BH)

Operator-checklist voor het in productie zetten van de AI-Trading-Agent
op paper-mode. Iedere stap heeft een tegenhanger in de
`GET /runbook` endpoint zodat de operator de status kan zien in de UI
zonder dit document opnieuw te lezen.

> **Belangrijk**: CLAUDE.md §1 + §15 vergrendelen `paper_only_mode=True`.
> Deze runbook is uitsluitend voor paper-mode go-live. Live trading is
> niet ondersteund en mag NOOIT worden ingeschakeld in V1.

## 1. Stack draait

- [ ] `docker compose up` zonder fouten.
- [ ] API health endpoint geeft 200: `curl http://localhost:8000/health`
- [ ] Worker health endpoint geeft 200: `curl http://localhost:8100/health`
- [ ] Web build draait: `curl http://localhost:3000` geeft 200.

## 2. Doctrine-locks (hard vereist)

- [ ] `paper_only_mode=True` (`GET /runbook` → groep `doctrine_locks`).
      Mag nooit op `False` staan.
- [ ] `safe_for_*` booleans staan op `False` op alle decision-records
      (orchestrator, suggestion, action-draft, etc.). Dit is doctrine
      via dataclass `__post_init__` validatie — kan niet per ongeluk
      omklappen.
- [ ] `claude_ai_api_key` mag wel ontbreken (Claude alleen voor
      NL-uitleg, nooit als forecaster — CLAUDE.md §15).

## 3. Provider-configuratie (warning indien niet ingesteld)

- [ ] `STORAGE__ENABLED=true`, `STORAGE__DATABASE_URL=postgresql://...`,
      `STORAGE__WRITES_ENABLED=true`. Hard vereist — zonder schrijfbare
      opslag werkt geen audit-rij.
- [ ] `EODHD_API_KEY=...` ingesteld. Zonder key vallen forecasts +
      earnings refresh weg; SELL-loop blijft draaien.
- [ ] `IBKR_ENABLED=true`, `IBKR_HOST=...`, `IBKR_PORT=4002` (paper),
      `IBKR_CLIENT_ID=...`. IBKR-paper-account is vereist voor live
      positie-sync.
- [ ] `CLAUDE_AI_API_KEY=...` optioneel (NL-uitleg kaartjes).

## 4. Doctrine-features inschakelen

In `runtime_config` (via UI of API) één voor één aanzetten:

- [ ] `MARKET_DATA_SYNC_ENABLED=true` — EODHD market-data
- [ ] `FORECAST_SYNC_ENABLED=true` — GBM + ensemble forecasts
- [ ] `SUGGESTION_SYNC_ENABLED=true` — asset suggestions
- [ ] `DECISION_PACKAGE_SYNC_ENABLED=true` — decision packages
- [ ] `ACTION_DRAFT_SYNC_ENABLED=true` — action drafts
- [ ] `EARNINGS_CALENDAR_SYNC_ENABLED=true` — V1.2 §AK earnings
      refresh leg (PR §BG laat deze nu ook in HTTP-trigger pad lopen)
- [ ] `ORCHESTRATOR_SCORING_ENABLED=true` — V1.2 §Y profit-harvest
      scoring (PR §BG laat deze ook in HTTP-trigger pad lopen)
- [ ] `DAILY_BRIEFING_SYNC_ENABLED=true` — daily briefing samenvatting

## 5. Scheduler + worker

- [ ] Worker scheduler draait (`scheduler_state` rij wordt elke
      ``heartbeat_interval_seconds`` opgefrist).
- [ ] `POST /scheduler/runs/morning-chain` werkt (manueel trigger;
      morning-chain audit row landt in `scheduler_runs`).
- [ ] `POST /sell-signals/sweep` werkt (SELL-loop sweep, V1.2 §BF).
- [ ] Worker triggert SELL-sweep elke 15 min tijdens market-hours.

## 6. Operator-flows

- [ ] **Pauze-modus**: `POST /pauze` → `software_paused=True`. BUY-leg
      skipped, SELL-monitoring blijft draaien (CLAUDE.md §11).
- [ ] **Watchlist**: `/instellingen` → Watchlist → favorites toevoegen.
- [ ] **Profit-target**: `/instellingen` → Profit target = 4 (default
      per CLAUDE.md §6.1).
- [ ] **Belasting**: `/belasting` toont jaartotaal incl. TOB +
      bronbelasting.
- [ ] **Maandrapport**: `/rapporten` toont vorige-maand PDF in archief.

## 7. Smoke-test cyclus

1. Trigger handmatig: `POST /scheduler/runs/morning-chain`.
2. Controleer dat alle 8 legs status `succeeded` of `skipped` hebben
   (geen `failed`).
3. Controleer `GET /forecasts` heeft minstens één rij.
4. Controleer `GET /suggestions/grid` heeft kandidaten (of een
   informatieve "geen kandidaten vandaag" boodschap per CLAUDE.md
   §7.1).
5. Trigger handmatig: `POST /sell-signals/sweep`.
6. Controleer `GET /sell-signals` reageert (mogelijk leeg als geen
   positie de +4 % target raakt).

## 8. Beveiligings-checklist

- [ ] `.env` files bevatten geen secrets in git history
      (`git log --all --full-history -p .env*` mag niets tonen).
- [ ] Backup-scripts geconfigureerd: `BACKUP_DIR`,
      `BACKUP_GPG_PASSPHRASE_FILE` op chmod 600.
- [ ] Recente restore-test geslaagd (per backup-strategie in
      `deployment.md`).

## 9. Wat ALS er iets misgaat

- **Morning-chain leg gefaald**: lees `error_text` in `scheduler_runs`.
  De meeste failures herstellen vanzelf met een retry; alleen
  persistent gefaald → ticket aanmaken.
- **EODHD-quota uitgeput**: forecast + market-data legs skippen
  silentlijk; SELL-loop blijft draaien op laatste forecasts.
- **IBKR-connectie weg**: `ibkr_sync` job re-tried; `safe_for_*`
  flags voorkomen dat oude state als nieuw wordt geïnterpreteerd.
- **Software in pauze maar SELL gewenst**: SELL-loop draait sowieso
  (CLAUDE.md §11). Operator kan kaartjes blijven dismissen.
- **Onverwachte SELL-suggestie**: dismissal-knop in UI; signaal
  blijft sticky tot het materieel verandert (V1.2 §BF stickiness).

## 10. Quick reference — runbook endpoint

```bash
curl -s http://localhost:8000/runbook | jq '.ready_for_paper_go_live,
.summary_nl, .items[] | {code, status}'
```

Output: één rij per check met `ok / info / warning / blocking`. De
samenvatting boven is "klaar voor paper-go-live: ja/nee" met de
reden in NL.
