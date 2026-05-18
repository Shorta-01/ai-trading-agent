import { HelpText } from "@/components/HelpText";

type StatusCardProps = {
  titel: string;
  beschrijving: string;
  hulptekst: string;
};

export function StatusCard({ titel, beschrijving, hulptekst }: StatusCardProps) {
  return (
    <article className="status-card">
      <h3>{titel}</h3>
      <p>{beschrijving}</p>
      <HelpText text={hulptekst} />
    </article>
  );
}
