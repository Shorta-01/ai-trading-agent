import { HelpTooltip } from "@/components/HelpTooltip";
import { StatusBadge, UiStatus } from "@/components/StatusBadge";

type MetricCardProps = {
  title: string;
  value: string;
  status: UiStatus;
  help: string;
};

export function MetricCard({ title, value, status, help }: MetricCardProps) {
  return (
    <article className="metric-card">
      <div className="metric-head">
        <p>{title}</p>
        <HelpTooltip text={help} />
      </div>
      <h3>{value}</h3>
      <StatusBadge label={value} status={status} title={help} />
    </article>
  );
}
