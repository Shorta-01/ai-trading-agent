import { StatusBadge, UiStatus } from "@/components/StatusBadge";

type SyncStatusBadgeProps = {
  label: string;
  status: UiStatus;
  help: string;
};

export function SyncStatusBadge({ label, status, help }: SyncStatusBadgeProps) {
  return <StatusBadge label={label} status={status} title={help} />;
}
