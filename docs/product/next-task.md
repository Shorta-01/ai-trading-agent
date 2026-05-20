# Next Recommended Task

## Task 63: Add extraction UI trigger and extracted-text status display

### Why this is next

- De API kan nu deterministische extractie voor TXT/MD/CSV.
- De gebruiker heeft een veilige Nederlandse UI-flow nodig om extractie te starten vanuit de Onderzoeksbibliotheek.
- De UI moet extracted metadata/status tonen en expliciet maken dat de bron nog geblokkeerd blijft voor suggesties.
- Deze stap blijft binnen foundation-progressie zonder AI/classificatie/suggestie-runtime.

### Scope summary (kort)

- Voeg in de Onderzoeksbibliotheek een duidelijke extractie-actie toe.
- Toon extractiestatus en kernmetadata per bron.
- Houd veiligheidsboodschap zichtbaar: geen suggesties uit deze bron tot latere validatiegates.

### Alternative if team skips UI-trigger

- **Task 64:** Add deterministic document classification contracts/runtime foundation.
