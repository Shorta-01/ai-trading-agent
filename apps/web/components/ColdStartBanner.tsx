"use client";

/**
 * Task 128: cold-start banner.
 *
 * Polls ``/watchlist/confirmation-state`` every 60 seconds. When the
 * server reports ``state="unconfirmed"`` we render a sticky Dutch
 * banner just below the AccountModeBadge with a "Naar Volglijst"
 * router link. When state is ``confirmed`` or
 * ``no_account_configured`` the banner renders ``null`` — no DOM
 * footprint at all so it never crowds the header.
 *
 * Mounted globally in ``app/layout.tsx``.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import {
  apiClient,
  WatchlistConfirmationStateResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;


export function ColdStartBanner() {
  const query = useQuery({
    queryKey: ["watchlist-confirmation-state"],
    queryFn: async (): Promise<WatchlistConfirmationStateResponse> => {
      const result = await apiClient.getWatchlistConfirmationState();
      if (!result.ok) throw new Error("unreachable");
      return result.data;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const state = query.data ?? null;

  if (state === null || state.state !== "unconfirmed") {
    return null;
  }

  return (
    <div
      data-testid="cold-start-banner"
      data-state={state.state}
      role="alert"
      style={{
        background: "#fef3c7",
        color: "#92400e",
        border: "1px solid #fbbf24",
        padding: "10px 14px",
        borderRadius: 6,
        fontSize: 14,
        margin: "6px 0",
        display: "flex",
        gap: 12,
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <span style={{ flex: 1 }}>{state.banner_text}</span>
      <Link
        href="/volglijst"
        data-testid="cold-start-banner-link"
        style={{
          background: "#92400e",
          color: "#fef3c7",
          padding: "6px 12px",
          borderRadius: 4,
          textDecoration: "none",
          fontWeight: 600,
        }}
      >
        Naar Volglijst
      </Link>
    </div>
  );
}
