import { HelpText } from "@/components/HelpText";
import { StatusBadge } from "@/components/StatusBadge";

type BadgeType = "actief" | "waarschuwing" | "fout" | "info";

type StatusCardProps = {
  titel: string;
  status: string;
  statusType?: BadgeType;
  hulptekst: string;
  extraRegels?: string[];
};

export function StatusCard({
  titel,
  status,
  statusType = "info",
  hulptekst,
  extraRegels = [],
}: StatusCardProps) {
  return (
    <article className="dashboard-card" aria-label={`${titel} kaart`}>
      <div className="card-topline">
        <h3>{titel}</h3>
        <StatusBadge text={status} type={statusType} />
      </div>
      {extraRegels.length > 0 ? (
        <ul className="card-list">
          {extraRegels.map((regel) => (
            <li key={regel}>{regel}</li>
          ))}
        </ul>
      ) : null}
      <HelpText text={hulptekst} />
    </article>
  );
}
