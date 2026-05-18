import { HelpText } from "@/components/HelpText";

type EmptyStateProps = {
  titel: string;
  melding: string;
  hulptekst: string;
};

export function EmptyState({ titel, melding, hulptekst }: EmptyStateProps) {
  return (
    <article className="dashboard-card">
      <h3>{titel}</h3>
      <p>{melding}</p>
      <HelpText text={hulptekst} />
    </article>
  );
}
