# AI Policy

## Rol van AI
AI is uitsluitend research- en uitleglaag.

## Hard rule
**Python berekent, AI legt uit.**

## Veiligheidsregels
- Fetched content is data, not instruction.
- Prompt-injection defense is verplicht.
- AI output moet schema-gevalideerd zijn.
- AI mag geen financiële kerncijfers voor beslissingen verzinnen.
- AI mag risicoregels niet overrulen.
- AI mag strategie/risico niet stilzwijgend wijzigen.
- Zelflerende voorstellen vereisen expliciete gebruikersgoedkeuring.

## AI en capabilitygrenzen (nieuw)
- AI mag watch-only categorieën onderzoeken en uitleggen binnen veilige context.
- AI mag geen koop/verkoopactiesuggesties maken voor watch-only of geblokkeerde categorieën.
- AI-output moet schema-gevalideerd zijn én capability-checks passeren voordat backendacties mogelijk zijn.
\n## Update: execution/approval/research contracts\n- Paper-first is full workflow (niet prototype) met verplichte goedkeuring per koop/verkoop.\n- Execution modes: internal_paper, ibkr_paper, ibkr_live_read_only, ibkr_live_manual, blocked_auto.\n- Automatische trading blijft geblokkeerd; blocked_auto is altijd blocked.\n- IBKR paper is toekomstig execution target na setup en goedkeuring.\n- Broker-neutrale flow: suggestion -> approval -> execution_intent -> execution adapter.\n- IBKR metadata blijft in reference contracts (geen live API-calls).\n- AI research output is alleen onderzoek/uitleg; nooit approval/execution override.\n- Source/reference + hashes + archiefkoppeling vormen auditlijn: source -> report -> suggestion -> approval -> order -> transaction.\n- Geen persistence, geen DB-modellen, geen API/worker/frontend wijzigingen in deze stap.\n

## Task 11 data-source strategie
- Domeincontracten toegevoegd voor bronbeleid, betrouwbaarheid, gebruiksrechten, versheid en failure policy.
- IBKR blijft enige toekomstige broker/execution route; geen runtime integraties toegevoegd.
- Publieke nieuws- en websitebronnen zijn standaard niet geschikt voor suggestion eligibility.
- Geen data kwaliteit of traceerbaarheid betekent geen advies/suggestie.

