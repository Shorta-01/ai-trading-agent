import { StatusBadge, UiStatus } from "@/components/StatusBadge";

type StatusCardProps = {
  title: string;
  description: string;
  statusLabel: string;
  status: UiStatus;
};

export function StatusCard({ title, description, statusLabel, status }: StatusCardProps) {
  return (
    <article className="dashboard-card" aria-label={`${title} kaart`}>
      <div className="card-topline">
        <h3>{title}</h3>
        <StatusBadge label={statusLabel} status={status} />
      </div>
      <p>{description}</p>
    </article>
  );
}
