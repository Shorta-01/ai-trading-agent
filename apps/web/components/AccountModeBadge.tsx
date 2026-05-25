"use client";

/**
 * Task 126b: persistent IBKR account-mode indicator.
 *
 * Polls ``/ibkr/connection/status`` every 30 seconds, renders one of
 * three visual states (Paper neutral-blue / Live amber / Disconnected
 * grey). On first mount the strip flashes the full-saturation mode
 * colour for ~500ms, then settles. The account ID arrives masked
 * from the API (``DU•••4567``); the component never receives the
 * full ID.
 */

import { useEffect, useState } from "react";

import { apiClient, IbkrConnectionStatusResponse } from "@/lib/apiClient";

const POLL_INTERVAL_MS = 30_000;
const FLASH_DURATION_MS = 500;

type Mode = "paper" | "live" | "disconnected";

type Visuals = {
  background: string;
  flashBackground: string;
  color: string;
  label: (id: string | null) => string;
  ariaLabel: string;
};

const PAPER_VISUALS: Visuals = {
  background: "#1e40af",
  flashBackground: "#3b82f6",
  color: "#ffffff",
  label: (id) => `Paper-rekening: ${id ?? "onbekend"}`,
  ariaLabel: "IBKR paper-rekening verbonden",
};

const LIVE_VISUALS: Visuals = {
  background: "#f59e0b",
  flashBackground: "#fbbf24",
  color: "#1f2937",
  label: (id) => `Echte rekening: ${id ?? "onbekend"}`,
  ariaLabel: "IBKR live-rekening verbonden",
};

const DISCONNECTED_VISUALS: Visuals = {
  background: "#6b7280",
  flashBackground: "#9ca3af",
  color: "#ffffff",
  label: () => "Geen IBKR-verbinding",
  ariaLabel: "Geen IBKR-verbinding",
};

function deriveMode(
  status: IbkrConnectionStatusResponse | null,
): Mode {
  if (status === null) return "disconnected";
  if (!status.connected) return "disconnected";
  if (status.account_mode === "paper") return "paper";
  if (status.account_mode === "live") return "live";
  return "disconnected";
}

function visualsFor(mode: Mode): Visuals {
  if (mode === "paper") return PAPER_VISUALS;
  if (mode === "live") return LIVE_VISUALS;
  return DISCONNECTED_VISUALS;
}

export function AccountModeBadge() {
  const [status, setStatus] = useState<IbkrConnectionStatusResponse | null>(
    null,
  );
  const [flashing, setFlashing] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const result = await apiClient.getIbkrConnectionStatus();
      if (cancelled) return;
      if (result.ok) {
        setStatus(result.data);
      } else {
        setStatus(null);
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

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFlashing(false);
    }, FLASH_DURATION_MS);
    return () => window.clearTimeout(timer);
  }, []);

  const mode = deriveMode(status);
  const visuals = visualsFor(mode);
  const background = flashing ? visuals.flashBackground : visuals.background;
  const label = visuals.label(status?.account_id ?? null);

  return (
    <div
      data-testid="account-mode-badge"
      data-mode={mode}
      role="status"
      aria-label={visuals.ariaLabel}
      style={{
        background,
        color: visuals.color,
        minHeight: "32px",
        padding: "6px 12px",
        borderRadius: "6px",
        fontWeight: 600,
        fontSize: "14px",
        display: "inline-flex",
        alignItems: "center",
        gap: "8px",
        transition: "background 300ms ease-out",
      }}
    >
      <span aria-hidden="true">
        {mode === "live" ? "●" : mode === "paper" ? "○" : "×"}
      </span>
      <span>{label}</span>
    </div>
  );
}
