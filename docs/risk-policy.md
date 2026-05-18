# Risk Policy (Paper-only v1)

## Kernregel
Versie 1 is strikt paper-only en risk-first.

## Verplichte risicoregels
- Positielimieten (max positie, max ETF-allocatie, max individuele aandeelallocatie).
- Minimale cashreserve (eerste opbouw en normaal bedrijf).
- Geen leverage.
- Geen opties.
- Geen short selling.
- Geen penny stocks.
- Geen illiquide assets.

## Blokkeerregels
- Geen trade bij datakwaliteitsfalen.
- Geen trade bij risico-overtreding.
- Geblokkeerde suggesties tonen altijd expliciete reden.

## Gedragsregels
- Geen overtrading.
- Niet alles meteen investeren.
- Beslissings-cooldown verplicht.
- “Insufficient evidence”-status totdat er voldoende paperhistoriek is.
- Geen stale advice bij scheduler/data-update falen.

## Capability-handhaving (nieuw)
- De backend moet capabilityregels afdwingen voor opvolgen, onderzoek, actiesuggesties, papieren orders, papieren transacties en portefeuilletoegang.
- UI-instellingen mogen geblokkeerde productregels nooit overrulen.
- Dormante koop/verkoopcode voor geblokkeerde categorieën is niet toegestaan.
