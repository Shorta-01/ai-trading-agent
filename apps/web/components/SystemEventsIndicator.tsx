"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { apiClient } from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

export function SystemEventsIndicator() {
  const query = useQuery({
    queryKey: ["active-system-events-count"],
    queryFn: async (): Promise<number | null> => {
      const response = await apiClient.getActiveSystemEvents();
      return response.ok ? response.data.events.length : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const activeCount = query.data ?? null;

  const hasActive = typeof activeCount === "number" && activeCount > 0;

  return (
    <Link className={`events-indicator ${hasActive ? "events-indicator-active" : ""}`} href="/systeemmeldingen" title="Bekijk actieve systeemmeldingen.">
      <span aria-hidden>🔔</span>
      <span>Systeemmeldingen</span>
      {typeof activeCount === "number" ? <span className="events-indicator-count">{activeCount}</span> : null}
    </Link>
  );
}
