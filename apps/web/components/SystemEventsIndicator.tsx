"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiClient } from "@/lib/apiClient";

export function SystemEventsIndicator() {
  const [activeCount, setActiveCount] = useState<number | null>(null);

  useEffect(() => {
    async function loadCount() {
      const response = await apiClient.getActiveSystemEvents();
      if (!response.ok) {
        setActiveCount(null);
        return;
      }
      setActiveCount(response.data.events.length);
    }

    void loadCount();
  }, []);

  const hasActive = typeof activeCount === "number" && activeCount > 0;

  return (
    <Link className={`events-indicator ${hasActive ? "events-indicator-active" : ""}`} href="/systeemmeldingen" title="Bekijk actieve systeemmeldingen.">
      <span aria-hidden>🔔</span>
      <span>Systeemmeldingen</span>
      {typeof activeCount === "number" ? <span className="events-indicator-count">{activeCount}</span> : null}
    </Link>
  );
}
