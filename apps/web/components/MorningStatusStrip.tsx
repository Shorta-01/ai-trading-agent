"use client";

/**
 * V1.2 §AF — Morning status strip.
 *
 * Single sticky line at the top of the dashboard with everything the
 * operator needs to glance at first thing: date, market state, last
 * IBKR sync, scheduler/briefing status, alert count. If anything here
 * shows red, the operator knows to investigate before clicking
 * anywhere else. Read-only; all data sourced from existing endpoints.
 */

import { useQuery } from "@tanstack/react-query";

import {
  apiClient,
  type ActiveSystemEventsResponse,
  type IbkrSyncStatusResponse,
  type MarketHoursNowResponse,
  type SchedulerJobsResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function formatBrusselsTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("nl-BE", {
      timeZone: "Europe/Brussels",
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
    });
  } catch {
    return iso;
  }
}

function marketSummary(markets: MarketHoursNowResponse | null): {
  label: string;
  tone: "ok" | "wacht" | "info";
} {
  if (!markets || markets.markets.length === 0) {
    return { label: "Markt onbekend", tone: "info" };
  }
  const anyOpen = markets.markets.some((m) => m.state === "open");
  const anyPre = markets.markets.some((m) => m.state === "pre_open");
  if (anyOpen) return { label: "Markt open", tone: "ok" };
  if (anyPre) return { label: "Pre-market", tone: "wacht" };
  return { label: "Markt gesloten", tone: "info" };
}

function toneColor(tone: "ok" | "wacht" | "info" | "aandacht" | "geblokkeerd"): {
  bg: string;
  fg: string;
} {
  switch (tone) {
    case "ok":
      return { bg: "#dcfce7", fg: "#166534" };
    case "wacht":
      return { bg: "#fef3c7", fg: "#854d0e" };
    case "aandacht":
      return { bg: "#fed7aa", fg: "#9a3412" };
    case "geblokkeerd":
      return { bg: "#fee2e2", fg: "#991b1b" };
    default:
      return { bg: "#e0e7ff", fg: "#3730a3" };
  }
}

function Chip({
  label,
  tone,
  testid,
}: {
  label: string;
  tone: "ok" | "wacht" | "info" | "aandacht" | "geblokkeerd";
  testid: string;
}) {
  const colors = toneColor(tone);
  return (
    <span
      data-testid={testid}
      style={{
        background: colors.bg,
        color: colors.fg,
        padding: "3px 10px",
        borderRadius: 10,
        fontSize: 12,
        fontWeight: 600,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </span>
  );
}

export function MorningStatusStrip() {
  const marketQuery = useQuery({
    queryKey: ["morning-strip-market-hours"],
    queryFn: async (): Promise<MarketHoursNowResponse | null> => {
      const r = await apiClient.getMarketHoursNow();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const syncQuery = useQuery({
    queryKey: ["morning-strip-sync"],
    queryFn: async (): Promise<IbkrSyncStatusResponse | null> => {
      const r = await apiClient.getIbkrSyncStatus();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const schedulerQuery = useQuery({
    queryKey: ["morning-strip-scheduler"],
    queryFn: async (): Promise<SchedulerJobsResponse | null> => {
      const r = await apiClient.getSchedulerJobs();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const eventsQuery = useQuery({
    queryKey: ["morning-strip-events"],
    queryFn: async (): Promise<ActiveSystemEventsResponse | null> => {
      const r = await apiClient.getActiveSystemEvents();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const market = marketSummary(marketQuery.data ?? null);
  const sync = syncQuery.data ?? null;
  const scheduler = schedulerQuery.data ?? null;
  const events = eventsQuery.data ?? null;
  const alertCount = events?.events?.length ?? 0;

  const today = new Date().toLocaleDateString("nl-BE", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  const syncTone: "ok" | "wacht" | "aandacht" =
    sync?.configured && sync.last_sync_at ? "ok" : sync?.configured ? "wacht" : "aandacht";
  const syncLabel = sync?.last_sync_at
    ? `IBKR-sync ${formatBrusselsTime(sync.last_sync_at)}`
    : "IBKR-sync ontbreekt";

  const briefingTone: "ok" | "wacht" | "info" = scheduler?.status === "ok" ? "ok" : "info";
  const briefingLabel = scheduler?.items?.[0]?.next_run_at
    ? `Volgende briefing ${formatBrusselsTime(scheduler.items[0].next_run_at)}`
    : "Briefing-tijd onbekend";

  const alertsTone: "ok" | "aandacht" | "geblokkeerd" =
    alertCount === 0 ? "ok" : alertCount >= 3 ? "geblokkeerd" : "aandacht";
  const alertsLabel =
    alertCount === 0 ? "Geen actieve meldingen" : `${alertCount} actieve meldingen`;

  return (
    <section
      data-testid="morning-status-strip"
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: 10,
        background: "#f9fafb",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: "8px 12px",
        marginBottom: 12,
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}
    >
      <span
        data-testid="morning-status-strip-date"
        style={{ fontWeight: 700, fontSize: 13, color: "#111827" }}
      >
        {today}
      </span>
      <Chip label={market.label} tone={market.tone} testid="morning-status-strip-market" />
      <Chip label={syncLabel} tone={syncTone} testid="morning-status-strip-sync" />
      <Chip
        label={briefingLabel}
        tone={briefingTone}
        testid="morning-status-strip-briefing"
      />
      <Chip label={alertsLabel} tone={alertsTone} testid="morning-status-strip-alerts" />
    </section>
  );
}
