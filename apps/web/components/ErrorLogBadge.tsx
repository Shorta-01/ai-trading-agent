"use client";

/**
 * Central error-log badge for the dashboard header.
 *
 * Polls ``GET /errors`` every 60s and shows the count of open errors. Red when
 * there are any, neutral grey when clear. Links to the /errors panel.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { apiClient, ErrorLogResponse } from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

export function ErrorLogBadge() {
  const query = useQuery({
    queryKey: ["error-log-count"],
    queryFn: async (): Promise<ErrorLogResponse> => {
      const result = await apiClient.getErrors();
      if (!result.ok) throw new Error("errors_unreachable");
      return result.data;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const count = query.data?.open_count ?? 0;
  const hasErrors = count > 0;

  return (
    <Link
      href="/errors"
      data-testid="error-log-badge"
      data-state={hasErrors ? "errors" : "clear"}
      role="status"
      aria-label={
        hasErrors ? `${count} openstaande fouten` : "Geen openstaande fouten"
      }
      title="Bekijk en beheer fouten"
      style={{
        background: hasErrors ? "#dc2626" : "#6b7280",
        color: "#ffffff",
        padding: "6px 12px",
        borderRadius: "6px",
        fontWeight: 600,
        fontSize: "13px",
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        textDecoration: "none",
      }}
    >
      <span aria-hidden="true">{hasErrors ? "⚠️" : "✓"}</span>
      <span>Fouten</span>
      <span data-testid="error-log-count">{count}</span>
    </Link>
  );
}
