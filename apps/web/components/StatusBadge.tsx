type BadgeType = "actief" | "waarschuwing" | "fout" | "info";

type StatusBadgeProps = {
  text: string;
  type?: BadgeType;
};

const classMap: Record<BadgeType, string> = {
  actief: "status-badge status-badge-actief",
  waarschuwing: "status-badge status-badge-waarschuwing",
  fout: "status-badge status-badge-fout",
  info: "status-badge status-badge-info",
};

export function StatusBadge({ text, type = "info" }: StatusBadgeProps) {
  return <span className={classMap[type]}>{text}</span>;
}
