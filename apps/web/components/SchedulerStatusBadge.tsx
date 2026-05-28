"use client";

/**
 * Task 127: scheduler status indicator for the Dashboard page.
 *
 * Polls ``/scheduler/v127/status`` every 60 seconds and renders one
 * of three visual states:
 *
 * * ``Actief`` (green) — scheduler reports enabled + at least one
 *   worker has heartbeat data. Shows the next fire time in
 *   ``Volgende run om HH:MM`` Dutch.
 * * ``Uitgeschakeld`` (grey) — scheduler reports disabled (storage
 *   off OR no worker heartbeat).
 * * ``Fout`` (amber) — last run had ``outcome="error"`` OR the
 *   API call failed.
 *
 * Mounted on the Dashboard only — not the global layout.
 */

import { useQuery } from "@tanstack/react-query";

import { apiClient, SchedulerV127StatusResponse } from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

type BadgeState = "actief" | "uitgeschakeld" | "fout";

const STATE_VISUALS: Record<BadgeState, { background: string; color: string }> = {
  actief: { background: "#15803d", color: "#ffffff" },
  uitgeschakeld: { background: "#6b7280", color: "#ffffff" },
  fout: { background: "#f59e0b", color: "#1f2937" },
};

function deriveState(
  status: SchedulerV127StatusResponse | null,
  apiError: boolean,
): BadgeState {
  if (apiError) return "fout";
  if (status === null) return "uitgeschakeld";
  if (!status.enabled) return "uitgeschakeld";
  if (status.last_outcome === "error") return "fout";
  return "actief";
}

function formatNextRun(iso: string | null | undefined): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleTimeString("nl-BE", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

function labelFor(
  state: BadgeState,
  status: SchedulerV127StatusResponse | null,
): string {
  if (state === "uitgeschakeld") return "Uitgeschakeld";
  if (state === "fout") {
    const errorRunType = status?.last_run_type;
    return errorRunType
      ? `Fout in laatste ${errorRunType}`
      : "Fout in laatste run";
  }
  const next = status?.next_runs?.[0];
  const time = formatNextRun(next);
  return time ? `Actief — volgende run om ${time}` : "Actief";
}

export function SchedulerStatusBadge() {
  const query = useQuery({
    queryKey: ["scheduler-v127-status"],
    queryFn: async (): Promise<SchedulerV127StatusResponse> => {
      const result = await apiClient.getSchedulerV127Status();
      if (!result.ok) throw new Error("scheduler_status_unreachable");
      return result.data;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const status = query.data ?? null;
  const apiError = query.isError;

  const state = deriveState(status, apiError);
  const visuals = STATE_VISUALS[state];
  const label = labelFor(state, status);

  return (
    <div
      data-testid="scheduler-status-badge"
      data-state={state}
      role="status"
      aria-label={`Scheduler-status: ${label}`}
      style={{
        background: visuals.background,
        color: visuals.color,
        padding: "6px 12px",
        borderRadius: "6px",
        fontWeight: 600,
        fontSize: "13px",
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
      }}
    >
      <span aria-hidden="true">●</span>
      <span>{label}</span>
    </div>
  );
}
