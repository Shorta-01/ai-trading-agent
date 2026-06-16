# Live-TWS Smoke-Test Runbook (V1.2 §BZ)

Operator-checklist voor het overschakelen van een paper-IBKR-sessie
(`DU*` / `DF*`) naar een live-IBKR-sessie (`U*`).

> **Veiligheid eerst** — Per CLAUDE.md §2 is en blijft de
> operator-approval workflow (klik → modaal → klik) de enige
> veiligheidsgarantie tegen ongewenste live trades. De software is
> ADVISEUR. Geen automatische orderplaatsing, geen automatische
> cancel, geen automatische wijzigingen.

> **Doctrine-referentie** — CLAUDE.md §15 (V1.2 §BZ) en
> `docs/go-live-runbook.md` §2. Per §BZ bepaalt **de IBKR account-id
> prefix** of orders naar paper of live worden geplaatst — er is geen
> `paper_only_mode` env-flag meer. Het in productie nemen van een
> live-account is daarmee een **deploy-time configuratie**, niet een
> code-change.

---

## 1. Voorwaarden — wat is er klaar?

Voordat je een live-account aansluit, MOET het volgende geverifieerd
zijn (laat de paper-flow al ≥ 1 week draaien):

- [ ] Paper-go-live runbook (`docs/go-live-runbook.md`) helemaal groen
      sinds minstens 7 kalenderdagen.
- [ ] `GET /runbook` geeft `ready_for_paper_go_live=true`.
- [ ] Minstens één volledige morning-chain cyclus succesvol (alle 8
      legs `succeeded` of `skipped`, geen `failed`).
- [ ] Minstens één SELL-loop sweep succesvol uitgevoerd tijdens
      market-hours.
- [ ] Minstens één paper-order succesvol door de hele flow:
      `proposed → user_approved → submitted → working → filled` met
      een `permId` van de IBKR paper-server, plus een gerealiseerd
      P&L cijfer op `/portefeuille`.
- [ ] Reconciliation-sweep heeft minstens één keer een fill
      gematched (V1.2 §AT).
- [ ] `/belasting jaaroverzicht` toont een gerealiseerde trade incl.
      TOB-aankoop, TOB-verkoop, en RV-tekort waar van toepassing.

Als één van bovenstaande vinkjes ontbreekt → **NIET DOORGAAN** naar §2.

---

## 2. §CA paper-only blockers verwijderd (2026-06-16 — REEDS GEFIXED)

Per **2026-06-16** zijn de hardcoded `paper_only_required` gates die
contradictorisch waren met de §BZ doctrine ("software werkt VOLLEDIG
in beide modi") **verwijderd**:

| Locatie | Voor 2026-06-16 | Na audit-cleanup |
|---|---|---|
| `action_draft_submission.approve_action_draft` | Blokkeerde `account_mode != "paper"` met `paper_only_required` | Gate verwijderd — `dry_run_status == "passed"` blijft de enige check |
| `action_draft_submission.approve_action_draft` | Blokkeerde `expected_account_mode != "paper"` met `expected_account_mode_not_paper` | Gate verwijderd |
| `action_draft_submission.submit_action_draft_to_paper` | Blokkeerde live drafts met `paper_only_required` | Gate verwijderd — `dry_run` + approval-freshness blijven |
| `action_draft_sync.generate_action_drafts` | `account_mode="paper"` hardcoded | `account_mode=expected_account_mode` (operator-keuze) |
| `ibkr_session_adapter_factory` | Diagnostic string `paper_only_required` | String verwijderd |

**De §2 operator-approval workflow (klik → modaal → klik) is de
enige veiligheidsgarantie tegen ongewenste live trades** — per
CLAUDE.md §2 + §15.

Wat NIET wijzigde (bewust):

- `paper_setup` onboarding-wizard heeft nog steeds een
  `paper_only_required=True` default; dat is correct voor first-time
  setup en blokkeert geen running software-functionaliteit.
- Worker `safety_recheck.py` gateway-mode-match check blijft: een
  draft met DU-prefix tegen een live-gateway connectie geeft
  `mode_mismatch` (en omgekeerd). Dat is doctrine-correct want het
  detecteert een echte misconfiguratie, geen mode-veroorlof.
- `safe_for_*` flags blijven op `False` op alle persisted records.

**De software is dus per 2026-06-16 doctrine-compleet voor live
trading.** Deze smoke-test kan rechtstreeks tegen een live-account
worden uitgevoerd.

---

## 3. Smoke-test procedure (live-cutover simulatie)

### 3.1 Env-config voorbereiden

In `.env` (of via `runtime_config`):

```bash
# Voor de cutover: vervang de paper credentials door je live credentials.
IBKR_ACCOUNT_ID_HINT=U1234567   # je verwachte live account-id
IBKR_HOST=127.0.0.1
IBKR_PORT=4001                  # 4001 = live TWS, 4002 = paper TWS, 7497 = live IBG, 7496 = paper IBG
IBKR_CLIENT_ID=42

# De §AH live-account warning blijft op `warning`, niet `blocking`.
# De operator-approval workflow (§2) is de safety-laag.
```

> **TWS-config**: in TWS → Settings → API → Settings, zet de Read-Only
> API OFF voor de order-sessie (de sync-sessie blijft Read-Only ON).
> Twee aparte API-client-id's per CLAUDE.md (zie ADR-0009).

### 3.2 Stack restart + connectie-verificatie

```bash
docker compose down
docker compose up -d
sleep 30  # geef TWS de tijd om de API-sessie te accepteren
curl -s http://localhost:8000/ibkr/connection/status | jq
```

Verwacht antwoord:
```json
{
  "connection_health": "connected",
  "account_id": "U1234567",
  "account_mode": "live",
  "is_read_only_session": true,
  "last_handshake_at": "2026-06-16T12:30:00Z"
}
```

Als `account_mode != "live"` → controleer TWS poort + account.
Als de account-id verschilt van de hint → `SystemEvent` rij
`category="ibkr_config_mismatch"` verschijnt op `/systeemmeldingen`
en de mismatch-banner op `/portefeuille`. Dat is correct gedrag.

### 3.3 PAPER/LIVE-pill verificatie

- [ ] Open `/portefeuille` in de browser.
- [ ] Bovenaan dashboard: pill toont **"LIVE"** in oranje/rood.
- [ ] Klik op de pill → `/admin/audit/ibkr-config` opent met de
      mismatch-events. Verifieer dat de `live_account_open` rij is
      geschreven.
- [ ] `/instellingen` toont de "Worker laatst herladen" status-strip
      met een recente timestamp.

### 3.4 Position-snapshot smoke-test

```bash
curl -X POST http://localhost:8000/ibkr/sync 2>&1 | jq
```

Verwacht: een rij in `ibkr_position_snapshots` met het echte
live-account-id. Verifieer:

```bash
curl -s http://localhost:8000/portfolio/valuation | jq '.summary'
```

De totale portfolio-waarde moet overeenstemmen met wat TWS toont in
het Account-venster.

### 3.5 BUY-flow smoke-test — kleinste positie

> ⚠️ **Dit is je eerste echte trade met echt geld.** Doe deze test
> met de kleinste mogelijke positie (€5.000 minimum per CLAUDE.md §3,
> idealiter een liquide large-cap met €100/share zodat je 50 shares
> hebt en geen partial-fill issues).

**3.5.1** Trigger morning-chain:
```bash
curl -X POST http://localhost:8000/scheduler/runs/morning-chain | jq '.summary'
```

**3.5.2** Open `/suggesties` in de browser. Zoek een kandidaat met:
- Bedrijfsnaam je kent
- Liquide aandeel (>1M volume/dag)
- Sector waar je comfortabel mee bent
- Confidence ≥ 80%

**3.5.3** Klik **"Goedkeuren"** → modaal → bevestig.
**3.5.4** Ga naar stage 2 ("Te verzenden naar IBKR"):
- Verifieer aantal en limit-prijs
- Klik **"Verzend alle X orders naar IBKR"** → modaal toont:
  > ⚠️ Je staat op een LIVE-account (U1234567). Dit zijn echte
  > orders met echt geld. Bevestig?
- Klik **"Ja, verzend"**.

**3.5.5** Verifieer op stage 3:
- Order status = `submitted`
- `permId` is een 8-9 cijferig getal (geen paper-prefix)
- Open TWS → bevestig dat de order in TWS verschijnt
- Status updates van `working` → `filled` worden live opgepikt

**3.5.6** Na fill, verifieer:
- `/portefeuille` toont de positie met aankoopprijs
- `ibkr_executions` heeft een rij met de echte fill-prijs
- TOB-bedrag (€aantal × prijs × 0.0035, max €1600) is correct berekend
- Reconciliation-sweep matcht de fill binnen 30 sec

### 3.6 SELL-flow smoke-test — +4% target

> **Geen geforceerde verkoop.** Wacht tot de positie organisch +4%
> raakt, of tot je manueel besluit te verkopen.

Wanneer de SELL-suggestie verschijnt:

- [ ] SELL-kaartje toont forecast-context + EUR-equivalent
- [ ] "Verkopen nu" knop opent modaal met:
      > ⚠️ Je verkoopt op een LIVE-account. Bevestig dat je %€X.XX
      > netto winst wilt nemen?
- [ ] Klik bevestig → MKT SELL order naar TWS
- [ ] Fill landt in `ibkr_executions`
- [ ] Gerealiseerde winst verschijnt op `/belasting` jaaroverzicht
- [ ] TOB-verkoop is correct berekend
- [ ] RV-tekort wordt niet getoond op SELL (alleen bij dividenden)

### 3.7 Audit-trail verificatie

Voor elke live-trade MOET de audit-trail compleet zijn:

```bash
curl -s "http://localhost:8000/belasting/jaaroverzicht?year=2026" | \
  jq '.audit_trail[] | select(.account_mode=="live")'
```

Velden die aanwezig moeten zijn:
- `orchestrator_confidence_at_buy`
- `drivers_at_buy`
- `ai_explanation_nl_at_buy`
- `operator_adjustments` (aantal/prijs wijzigingen)
- `decision_time_ms`
- `account_mode == "live"`
- `ibkr_account_id` (gemaskeerd: `U***4567`)

### 3.8 Pauze + Hervat tijdens live

- [ ] Klik "Pauzeer de software" op `/portefeuille`
- [ ] Oranje statusbalk verschijnt
- [ ] BUY-leg wordt geskipt bij volgende morning-chain
- [ ] SELL-monitoring blijft draaien (CLAUDE.md §11)
- [ ] Klik "Hervat" → BUY-leg start weer

---

## 4. Failure-modes en wat te doen

| Symptoom | Oorzaak | Actie |
|---|---|---|
| `account_mode_detected="paper"` op een U-account | TWS draait op poort 4002 i.p.v. 4001 | Check TWS API-config: live = 4001, paper = 4002 |
| `is_read_only_session=true` blokkeert orderplaatsing | Order-sessie is read-only | TWS → API → uncheck "Read-Only API" voor de order-client-id |
| `paper_only_required` block bij approval | §2 doctrine-gap (zie §2 hierboven) | §CA.1-4 nodig — zie sectie 2 |
| Order accepted door API maar niet in TWS | Mogelijk client-id collision | Stop alle workers, check `IBKR_CLIENT_ID` is uniek per worker |
| `pacing_violation` errorCode 162/100/420 | Te veel requests in korte tijd | Worker scheduler `_compute_backoff_seconds` wacht nu 60s — geen actie nodig, herstelt automatisch |
| `IBKR_CONNECTION_LOST` errorCode 1100 | TWS herstart of netwerk-flap | Backoff is exponential (2s/4s/8s) — herstelt automatisch zodra TWS terug is |
| Reconciliation mismatch tussen IBKR + DB | Mid-run failure tussen `placeOrder` en commit | Manueel uitvoeren: `POST /reconciliation/sweep`; bekijk audit-rij voor root cause |
| Onverwachte fill-prijs >2% van limit | Markt is volatiel of LMT was te ruim | Niet panikeren — V1 plaatst LMT orders, geen MKT; fill > LMT kan niet |

---

## 5. Doctrine-locks die LIVE niet mag overrulen

Per CLAUDE.md §15 blijven onaangetast:

- `safe_for_*` flags op decision-records: hard `False` via dataclass
  `__post_init__` validatie.
- Claude/LLM is NIET een forecaster: alleen NL-uitleg, nooit een
  getalwaarde.
- Belgian TOB (0,35% × 2 round-trip voor standard_stock) blijft in
  alle berekeningen.
- Earnings-gate blokkeert BUY-suggesties binnen het earnings-window.
- §2 operator-approval workflow: ZONDER klik → GEEN order.

---

## 6. Quick-rollback procedure

Als er iets fout gaat en je terug wil naar paper-only:

```bash
# 1. Software pauzeren
curl -X POST http://localhost:8000/pauze

# 2. Env-config terugzetten
sed -i 's/IBKR_PORT=4001/IBKR_PORT=4002/' .env
sed -i 's/IBKR_ACCOUNT_ID_HINT=U.*/IBKR_ACCOUNT_ID_HINT=DU1234567/' .env

# 3. Stack restart
docker compose restart api worker

# 4. Verifieer paper-mode terug
curl -s http://localhost:8000/ibkr/connection/status | jq '.account_mode'
# Verwacht: "paper"

# 5. Hervat software
curl -X POST http://localhost:8000/pauze/hervat
```

Bestaande live-orders **bij IBKR** worden hierdoor NIET geannuleerd —
de operator moet manueel via TWS de open live-orders cancelen.

---

## 7. Acceptatie-criterium — wanneer mag je live blijven?

Pas wanneer alle onderstaande punten **één maand achter elkaar** groen
zijn op een live-account mag de €50.000 ramp naar €100.000 (CLAUDE.md
§1) overwogen worden:

- [ ] ≥ 3 succesvolle BUY+SELL cycli zonder operator-tussenkomst
      buiten approval-clicks
- [ ] 0 onverwachte fills (`fill_price` outside `limit_price` ±0.5%)
- [ ] 0 reconciliation mismatches die manuele tussenkomst vereisen
- [ ] 0 IBKR pacing-violations
- [ ] Gerealiseerde winsten matchen IBKR statement tot op de cent
- [ ] `/belasting jaaroverzicht` cijfers matchen een externe
      boekhoudkundige tweede mening

---

## 8. Verwijzingen

- CLAUDE.md §2 — Operator beslissingsmacht
- CLAUDE.md §15 — Doctrine-locks (mode-detectie via account-id)
- `docs/go-live-runbook.md` — Paper-go-live checklist (vereiste vóór
  deze runbook)
- `docs/decisions/0009-order-lifecycle-architecture.md` — Order
  lifecycle (paper én live)
- `docs/decisions/0010-reconciliation-architecture.md` — Reconciliation
- `/runbook` endpoint — Live runbook-status in JSON
- `/admin/audit/ibkr-config` — Audit-page voor mode-transitions

---

*Vastgelegd Tue 2026-06-16 als onderdeel van §BZ audit-cleanup
(PR #688 vervolg). Voorgesteld als doctrine-PR §CA wanneer de
operator klaar is voor live-cutover.*
