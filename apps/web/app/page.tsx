import { HelpText } from "@/components/HelpText";
import { StatusCard } from "@/components/StatusCard";
import { uiText } from "@/lib/uiText";

export default function HomePage() {
  return (
    <main className="container">
      <h1>{uiText.projectNaam}</h1>

      <section className="notice">
        <h2>{uiText.paperOnlyTitel}</h2>
        <p>{uiText.paperOnlyMelding}</p>
        <HelpText text="Deze melding bevestigt dat de applicatie alleen met papergeld werkt." />
      </section>

      <section>
        <h2>{uiText.statusTitel}</h2>
        <p>{uiText.statusBeschrijving}</p>
        <HelpText text="Hier zie je of de basisdiensten bereikbaar zijn in de technische skeleton." />
      </section>

      <section className="grid">
        {uiText.kaarten.map((titel) => (
          <StatusCard
            key={titel}
            titel={titel}
            beschrijving="Placeholder: inhoud volgt in een volgende fase."
            hulptekst={`Dit onderdeel toont later details voor ${titel.toLowerCase()}.`}
          />
        ))}
      </section>
    </main>
  );
}
