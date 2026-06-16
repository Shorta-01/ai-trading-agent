# CLAUDE.md — AI Trading Agent Operator Doctrine

**Version**: V1.2 §BZ.1 — vastgelegd Tue 2026-06-16 (§BZ audit-trail infrastructuur expliciet vastgelegd als doctrine-lock; concrete implementatie geshipped in PRs #662-#686). Initial §BZ vastgelegd Mon 2026-06-15 (paper_only_mode flag geschrapt als doctrine-lock; mode-detectie loopt nu uitsluitend via de IBKR account-prefix). Initial V1.2 §AO vastgelegd Sat 2026-06-13.

**Doel van dit document**: Bij elke nieuwe Claude Code sessie kan deze file als naslagwerk worden ingelezen zodat de doctrine niet opnieuw moet worden uitgelegd. De doctrine bepaalt **wat de software moet doen**; de bestaande `docs/intent/_trading-system-doctrine.md` blijft de technische uitwerking.

---

## 1. Operator context

| Item | Waarde |
|---|---|
| Operator | Belgische gepensioneerde |
| Totaal vermogen | €6.000.000 |
| Veilige basis | €5.000.000 op termijnrekening (~€7.300/maand netto baseline) |
| Trading-budget | **€1.000.000 maximum**, geleidelijk op te bouwen |
| Trading start | **€50.000** clean cash, ramp naar **€100.000** wanneer de operator comfortabel is |
| Mode | **IBKR-account bepaalt mode** — paper-account (`DU*`/`DF*`) of live-account (`U*`). De software werkt VOLLEDIG in beide modi; geen software-side flag bepaalt of er live geld kan bewegen, alleen het account waar IBKR de software op laat verbinden |
| Income behoefte | +4% per trade vormt de operator's maandelijkse income — niet herinvesteren |

---

## 2. Fundamenteel principe — beslissingsmacht

> **De software is ADVISEUR. De operator beslist altijd. De software plaatst NOOIT zelfstandig een order, cancelt geen order, en wijzigt niks zonder expliciete klik van de operator.**

Dit principe is bovengeschikt aan alle andere doctrine-regels. Het overrulet alle gates, alle suggesties, alle automatiseringen. Concreet:

- Buy-orders: operator klikt "Goedkeuren" → action draft krijgt status `user_approved` → operator klikt "Verzend alle naar IBKR" → orders gaan naar IBKR (paper of live; de gekoppelde account bepaalt het)
- Sell-orders bij +4%: software toont **SELL-suggestie kaartje** op dashboard, operator beslist
- Sell-orders bij 6m+ trigger: software toont SELL-suggestie, operator beslist
- Position averaging / re-entry: software stelt voor, operator beslist
- Pauze van de software: operator-getriggerd

**De V1.2 §M auto-take-profit LMT order pair wordt VERWIJDERD.** Alleen de BUY-LMT wordt naar IBKR gestuurd; de exit gebeurt na manuele bevestiging.

---

## 3. Position sizing — confidence-weighted

Software bepaalt de positiegrootte volgens de orchestrator-confidence-score:

| Confidence orchestrator | % van trading-portfolio | Op €50k portfolio | Op €100k |
|---|---|---|---|
| ≥90% (zeer zeker) | **50%** | €25.000 | €50.000 |
| 80-90% (zeker) | **30%** | €15.000 | €30.000 |
| 70-80% (redelijk) | **15%** | €7.500 | €15.000 |
| <70% | **skip** | — | — |

**Constraints:**
- **Maximum 50% per asset** (harde cap voor risico-diversificatie)
- **Minimum €5.000 per positie** (TOB-efficient — kleinere posities worden weggevreten door 0,70% round-trip kost)
- Software stelt aantal voor, operator mag aantal/limit-prijs aanpassen voor approval

---

## 4. Universum

**Default trading-universum:**
- US (NASDAQ + NYSE) — al ondersteund
- Euronext (Brussel + Parijs + Amsterdam) — toe te voegen aan exchange-mapping
- **Alleen aandelen** — geen ETFs, geen obligaties, geen opties

**In `/instellingen` configureerbaar:**
- Per beurs aan/uit-vinkje
- ETFs toelaten (default uit; let op accumulating-ETF TOB = 1,32% per kant)
- Obligaties toelaten (default uit)

**Geen sector-uitsluitingen** — alle sectoren (incl. tabak, wapens, gokken, olie/gas) zijn toegestaan. Maar zie §5 voor de hybride watchlist met manuele uitsluitingen.

---

## 5. Watchlist — hybride model

Software werkt met **drie bronnen tegelijk**:

1. **Universum-scan (autonoom)**: orchestrator scant elke ochtend het volledige US + Euronext large-cap universum (~3.500 namen totaal). Niet vereist dat operator iets manueel inputst.
2. **Favorieten-lijst (operator-onderhouden)**: operator kan symbolen toevoegen waar hij iets in ziet (bv. *AAPL, ASML.AS, KBC.BR*). Deze worden in een **apart dashboard-blok** getoond met live confidence-score — **ook als ze niet door de gates komen** (zo ziet de operator waarom).
3. **Uitsluitingen-lijst (operator-onderhouden)**: symbolen die altijd geblokkeerd zijn (bv. *TSLA, of een specifieke sector waar operator een aversie tegen heeft*). Software stelt deze nooit voor.

**Settings UI**: `/instellingen` heeft een Watchlist-sectie met drie tabbladen.

---

## 6. Profit-harvest doctrine — aangepast

### 6.1 Target

**+4% gross capital gain per trade**, gemeten in de **lokale munt** van het aandeel (USD voor AAPL, EUR voor ASML.AS).

EUR-equivalent wordt **als transparency** getoond bij elke suggestie en bij elke SELL-suggestie:
> *"AAPL +4% USD = €1.488 netto na TOB en bij huidige EUR/USD = 0,92. Indien EUR/USD verzwakt naar 0,90 wordt dit €1.260."*

**Optioneel in settings**: max-USD-exposure-cap (b.v. max 60% van portfolio in USD-namen). Default uit.

### 6.2 Horizon — aangepast (V1.2 §M wijziging)

- **Maand 0-6**: positie wordt **vastgehouden ongeacht prijsverloop**. Geen stop-loss. Geen geforceerde verkoop. Software monitort intraday tegen +4% target.
- **Vanaf maand 6**: software re-evalueert maandelijks met **combo-trigger**:
  - **Conditie 1**: forecaster (baseline GBM + ensemble) zegt p50 geen +4% upside meer geeft
  - **Conditie 2**: positie staat ≥ -5% onder instapprijs
  - **Beide condities moeten waar zijn** → software toont SELL-suggestie kaartje "Outlook verslechterd, overweeg te verkopen"
  - **Anders**: blijven houden (geen geforceerde verkoop)

### 6.3 +4% take-profit als SELL-suggestie

Wanneer een positie intraday +4% raakt:
- Software toont **SELL-suggestie kaartje** op dashboard met:
  - "VERKOOP — AAPL staat op +4,X%, neem je winst"
  - **Forecast-context**: "Voorspelling komende 3 dagen: p50 +6,2%, kans op verdere stijging 72%" (zodat operator kan beslissen om langer te wachten)
  - **EUR-equivalent**: "Netto +€1.485 in EUR bij huidige FX"
  - **Knop "Verkopen nu"** of **knop "Houden — ik wacht op verder rijzen"**

Operator beslist. Geen automatische verkoop.

### 6.4 Re-entry / averaging

Software heeft **geen automatische blokkade** voor heraankoop of bijkopen:
- Asset onlangs verkocht? → mag opnieuw worden voorgesteld
- Asset al in portfolio? → bijkopen mag worden voorgesteld (averaging down OK indien confidence hoog)
- Operator beslist of hij re-entry / averaging wil

---

## 7. Confidence en macro

### 7.1 Confidence-drempel

**Strikt <70% = skip.** Software toont enkel kandidaten die door alle gates komen met confidence ≥70%.

**Geen automatische drempel-verlaging.** Bij weken zonder kandidaten zegt het dashboard *"Geen kandidaten vandaag — software wacht op betere setups."* Geduldig wachten. Operator heeft €5M termijnrekening als basis-inkomen.

### 7.2 Macro regime

**Geen harde blokkade.** Macro-stress (VIX >25, S&P trending down, etc.) levert een **info-strip** bovenaan dashboard:
> *"Macro-stress: VIX 28, S&P -6% deze week. Wees voorzichtig."*

Maar de software laat alle voorstellen door. Operator beslist of hij in deze omgeving wil kopen. (Crashes zijn vaak goede BUY-momenten — een hard blok zou dat missen.)

### 7.3 Sector-concentratie

**Geen harde cap.** Software ranking puur op confidence — als de top 3 kandidaten allemaal tech zijn, dan wordt dat voorgesteld.

**Sector-verdeling wordt INFO**, niet blokkade:
- Per voorstel: "*NVDA — tech — als je dit + MSFT neemt zit je 80% in tech*"
- Sector-pie-chart op dashboard toont live portfolio-spreiding
- Operator beslist of hij concentratie wil

### 7.4 Daglimiet

**Geen limiet.** Orchestrator stelt alles voor wat door de gates komt. Per kandidaat **volledig beslissingsdossier** (zie §9).

---

## 8. Workflow — drie stages

| Stage | Status (DB) | UI label | Acties |
|---|---|---|---|
| 1 | `proposed` / `edited` | **"Voorstellen vandaag"** | Per voorstel: **Goedkeuren** / **Aanpassen** (aantal + limit-prijs) / **Afwijzen** |
| 2 | `user_approved` | **"Te verzenden naar IBKR"** (operator's to-do) | Nog bewerkbaar (aantal/prijs). Per regel **"Verwijder uit lijst"** knop. Eén grote knop bovenaan: **"Verzend alle X orders naar IBKR"** met modal-bevestiging |
| 3 | `submitted` → `working` / `filled` | **"Verzonden naar IBKR"** | Read-only, live updates van IBKR. Reconciliation pikt fills automatisch op |

**Approval-mechaniek (geen typen meer):**
- "Goedkeuren" knop → modal *"Weet je zeker?"* → Ja/Nee knop
- "Verzend alle naar IBKR" knop → modal met totaal-overzicht → Ja/Nee knop
- Edit-velden ZICHTBAAR (niet verstopt achter een toggle) voor aantal + limit-prijs in beide stages

**Vervangt de huidige JA/VERZEND typing prompts.**

---

## 9. Per-kandidaat beslissingsdossier

Elke BUY-suggestie moet op het dashboard een **vergelijkings-tabel-regel** krijgen en bij click een **volledig kaartje** met:

| Categorie | Veld |
|---|---|
| **Identiteit** | Symbool, bedrijfsnaam, sector, beurs, valuta, ISIN |
| **Prijs** | Huidige prijs, freshness, laatste sluit |
| **Forecast** | p10/p50/p90 voor 3-6m, kans op +4%, horizon |
| **Conviction** | Orchestrator confidence-score + waarom (drivers) |
| **Risico** | Drivers tegen positie (blockers die net niet trigger'den) |
| **Order** | Voorgesteld aantal, limit-prijs, totaal EUR, TOB-kost |
| **Portfolio impact** | Cash voor/na, sector-blootstelling voor/na, % portfolio |
| **Earnings** | Volgende earnings-datum |
| **Fundamentals** | Sector, market-cap, P/E, momentum 6m/12m |
| **Dividenden** | Verwachte dividenden tijdens hold-periode (lokaal + EUR netto na bronbelasting) |
| **AI uitleg** | Claude-NL paraphrase |

---

## 10. Notificaties

**Geen.** Operator checkt het dashboard op zijn eigen ritme (ochtend + paar keer per dag). Geen email, geen SMS. Alles via dashboard.

---

## 11. Pauze-modus

**Eén knop op dashboard**: *"Pauzeer de software"*.

Bij activatie:
- Morning chain stopt (geen nieuwe BUY-voorstellen)
- **SELL-monitoring blijft draaien** (operator wil geen +4% hits missen tijdens pauze)
- Bestaande posities onaangeroerd
- **Oranje statusbalk** bovenaan dashboard: *"Software gepauzeerd sinds DD/MM/YYYY"*
- Knop "Hervat" herstart alles

Geen panic-knop. Voor uitzonderlijke situaties sluit operator individueel elke positie via SELL-suggesties.

---

## 12. Belastingrapportering — `/belasting` pagina

Per **kalenderjaar selecteerbaar** (huidig + alle vorige jaren beschikbaar).

**Secties van het overzicht:**

| Sectie | Inhoud |
|---|---|
| Gerealiseerde kapitaalwinsten | Per trade: symbol/bedrijfsnaam/ISIN, beurs, valuta, aankoop (datum/prijs/aantal/lokaal+EUR met FX-koers van die dag), verkoop (idem), bruto resultaat, TOB-aankoop, TOB-verkoop, netto resultaat EUR, hold-dagen |
| Ontvangen dividenden | Per dividend: datum, symbol/ISIN, bruto (lokaal+EUR), bronbelasting ingehouden (US 15% / NL 15% / FR 12,8%), netto ontvangen, nog te regulariseren 30% RV via aangifte |
| TOB-jaartotaal | Per security class (standard_stock / distributing_etf / accumulating_etf / bond). Integratie met bestaande §AH widget |
| Audit-trail per trade | Orchestrator confidence op moment van aankoop, drivers, AI-uitleg, eventuele operator-aanpassingen, beslissingstijd |
| Jaartotalen | Bruto winst, totaal TOB, netto winst, bruto dividenden, bronbelasting reeds afgehouden, nog te betalen 30% RV, aantal trades, gem. hold, hit-rate +4% |
| "Goed huisvader"-bewijs | Auto-berekend: trades/jaar, gem. hold, trading-kapitaal/totaal vermogen, geen leverage, geen shorts |
| Maandgrafiek | Cumulatieve netto winst lijn-grafiek |
| Exports | **"Download PDF voor accountant"** (overzichtelijk, met disclaimer) + **"Download CSV"** voor Excel-bewerking |

**Belastingrechtelijk standpunt**: software helpt met overzicht maar geeft GEEN aangifte-advies. Geen auto-invullen van aangiftevakken (te risicovol; regels veranderen).

---

## 13. Maandelijks rapport — `/rapporten` pagina + auto-PDF archief

**Live dashboard-pagina** met maand-selector (kies bv. "juni 2026") toont:

| Sectie | Inhoud |
|---|---|
| Executive summary | Grote netto-winst cijfer, vergelijking vorige maand, vergelijking met termijnrekening-baseline (€1.458/maand op €50k), one-line takeaway |
| Open posities | Tabel + sector-pie + cash beschikbaar |
| Maand-activiteit | Alle BUYs + SELLs van die maand met full audit |
| Income | Capital gains + dividenden + TOB, cumulatief jaartotaal |
| Software-prestatie | Hit-rate +4%, gem. hold-tijd, confidence-distributie, voorstellen vs goedgekeurd |
| Events | Pauze-momenten, macro alerts, vermeden earnings, settings wijzigingen |
| Audit-trail per gesloten trade | Forensisch detail voor "goed huisvader"-bewijs |

**Auto-PDF**: elke 1e van de maand wordt een PDF gegenereerd en opgeslagen in `/rapporten/archief`. Operator kan oude PDFs downloaden. Geen e-mail (consistent met §10).

---

## 14. Settings UI (`/instellingen`)

Bestaande pagina krijgt extra secties voor de doctrine:

| Sectie | Inhoud |
|---|---|
| **Universum** | Per-beurs vinkjes (NASDAQ, NYSE, Brussel, Parijs, Amsterdam), "ETFs toelaten", "Obligaties toelaten" |
| **Watchlist** | Drie tabbladen: Favorieten / Uitsluitingen / Hybride mode |
| **Position sizing** | Confidence→% tabel (read-only, doctrine-fixed) + min-positie €5.000 (configureerbaar) |
| **FX** | Optionele max-USD-exposure cap |
| **Pauze-modus** | Knop "Pauzeer" + statusveld |

---

## 15. Bestaande locks die intact blijven

Alle bestaande doctrine-locks blijven:
- **Mode-detectie via IBKR-account, NIET via software-flag** — een paper-account (`DU*`/`DF*`) bepaalt dat orders naar paper-IBKR gaan, een live-account (`U*`) dat ze naar live-IBKR gaan. **De software werkt fully en correctly in beide modi.** Er is geen `paper_only_mode` flag meer die functionaliteit blokkeert. Het §2 fundamentele principe (operator moet ALTIJD klikken; software plaatst NOOIT zelfstandig een order) is de veiligheidsgarantie tegen ongewenste live trades — niet een software-side mode-lock.
- **§BZ audit-trail infrastructuur** — vastgelegd in PRs #662-#686. Mode-detectie loopt via één canonieke helper (`detect_account_mode_from_id` voor API, `_mode_from_account_id` voor worker) op basis van de account-id prefix. Elke mode-relevante event (mismatch, account-id wijziging, live-account open, runtime_config reload, reload-failed) wordt als `SystemEvent` gelogd in `system_events` met category `ibkr_config_mismatch` of `ibkr_config_change`. Operator-zichtbaarheid via:
  - PAPER/LIVE pill bovenaan dashboard (klikbaar → `/admin/audit/ibkr-config`)
  - Hint↔actual mismatch banner op /portefeuille (met dismiss-met-reden)
  - Live-confirmation modal op bulk-submit knop
  - Paper↔live save-confirmation modal op /instellingen
  - "Worker laatst herladen" status-strip op /instellingen
  - `/admin/audit/ibkr-config` dedicated audit-page (filters + CSV export + timeline)
  - IBKR-config audit sectie in `/belasting` jaaroverzicht (PDF + CSV)
  - Worker auto-pickup van runtime_config wijzigingen (SIGHUP + DB-poll heartbeat)
- **`safe_for_*` flags** blijven op False voor decision-makers (orchestrator, suggestion, action-draft, etc.)
- **AI verboden als forecaster** — Claude/LLM mag alleen NL uitleggen, nooit getallen origineren
- **Belgian TOB-aware** — 0,35% × 2 = 0,70% round-trip blijft in alle berekeningen
- **Earnings-gate** — confirmed en estimated earnings binnen het blok-venster geven `skip_earnings_window` verdict
- **SMTP password write-only via API** (smtp_password_set: bool returned)
- **claude_ai_api_key never returned in any response**

---

## 16. Implementation roadmap

De doctrine vraagt 8-12 PRs verspreid over meerdere sessies. Geplande volgorde (van meest fundamenteel naar meest cosmetisch):

| PR | Inhoud | Impact |
|---|---|---|
| **§AO** | Confidence-weighted position sizing + max 50% cap | Kern-engine |
| **§AP** | Sector hard cap → info-only, macro hard gate → info-strip | Kern-engine |
| **§AQ** | Soft horizon + 6m combo-trigger SELL-suggestie | Kern-engine |
| **§AR** | Auto-LMT weg, SELL-suggestie intraday monitor + kaartjes | Kern-engine |
| **§AS** | Euronext exchange mapping + ETF-toggle in settings | Universum |
| **§AT** | 3-stage workflow UI + button+modal approval + edit-in-place + bulk-submit | UI overhaul |
| **§AU** | Favorieten + uitsluitingen widget + dashboard favorieten-blok met live confidence | Watchlist |
| **§AV** | EUR-equivalent transparency + dividenden-info per kandidaat + macro info-strip + sector-spread widget | Info-widgets |
| **§AW** | `/belasting` pagina met volledige tabellen + PDF/CSV export | Reporting |
| **§AX** | `/rapporten` pagina maand-overzicht + auto-PDF maand-archief | Reporting |
| **§AY** | Pauze-modus knop + oranje statusbalk + patience inactivity-text | Operationeel |

Elke PR komt met:
- Volledige test-coverage (unit + integration + UI)
- mypy + ruff + eslint + tsc clean
- Doctrine constraints behouden
- Geen wijziging aan `safe_for_*` flags
- Software werkt voor beide IBKR account-modes (paper én live); geen pad mag alleen draaien onder een paper-account-aanname

---

## 17. Hoe deze file gebruiken

Bij elke nieuwe Claude Code sessie:
1. **Lees CLAUDE.md eerst** — geen doctrine-discussie opnieuw nodig
2. Wijzigingen aan de doctrine? → werk eerst CLAUDE.md bij in een aparte PR, dan code in volgende PRs
3. Bij conflict tussen CLAUDE.md en code: CLAUDE.md is de bron van waarheid voor doctrine; code moet aangepast worden om CLAUDE.md te volgen

---

*Vastgelegd in design-discussie met operator, Sat 2026-06-13. Volgende PR: §AO (confidence-weighted position sizing).*
