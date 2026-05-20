export type UiStatus =
  | "ok"
  | "aandacht"
  | "geblokkeerd"
  | "wacht"
  | "niet-beschikbaar"
  | "sync"
  | "vergrendeld"
  | "info";

type StatusBadgeProps = {
  label: string;
  status?: UiStatus;
  title?: string;
};

const classMap: Record<UiStatus, string> = {
  ok: "status-badge status-badge-ok",
  aandacht: "status-badge status-badge-aandacht",
  geblokkeerd: "status-badge status-badge-geblokkeerd",
  wacht: "status-badge status-badge-wacht",
  "niet-beschikbaar": "status-badge status-badge-niet-beschikbaar",
  sync: "status-badge status-badge-sync",
  vergrendeld: "status-badge status-badge-vergrendeld",
  info: "status-badge status-badge-info",
};

export function StatusBadge({ label, status = "info", title }: StatusBadgeProps) {
  return (
    <span className={classMap[status]} title={title}>
      {label}
    </span>
  );
}
