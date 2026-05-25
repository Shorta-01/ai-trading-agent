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

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  apiClient,
  WatchlistConfirmationStateResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;


export function ColdStartBanner() {
  const [state, setState] =
    useState<WatchlistConfirmationStateResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const result = await apiClient.getWatchlistConfirmationState();
      if (cancelled) return;
      if (result.ok) {
        setState(result.data);
      }
    }

    void load();
    const handle = window.setInterval(() => {
      void load();
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

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
