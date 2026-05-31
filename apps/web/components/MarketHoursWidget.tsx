"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiClient, type MarketHoursEntry } from "@/lib/apiClient";

/**
 * Dashboard widget: live open/close per followed market.
 *
 * Polls ``GET /markets/hours-now`` once per minute and renders one
 * row per market the operator selected in /instellingen. The endpoint
 * exposes UTC ISO timestamps for the next event so this component can
 * render a relative countdown (e.g. "sluit over 2 u 13 min") without
 * the API having to know the operator's timezone.
 *
 * State → dot colour mapping:
 *   open       → green
 *   pre_open   → amber
 *   post_close → grey
 *   weekend    → grey
 *
 * The widget never blocks the dashboard: when the endpoint is
 * unreachable the card surfaces a single Dutch error line instead of
 * disappearing.
 */

const POLL_INTERVAL_MS = 60_000;

function dotColour(state: MarketHoursEntry["state"]): string {
  switch (state) {
    case "open":
      return "#16a34a";
    case "pre_open":
      return "#f59e0b";
    case "post_close":
    case "weekend":
    default:
      return "#9ca3af";
  }
}

function formatLocalHHMM(iso: string): string {
  // Render in the operator's local timezone (the browser's tz). The
  // widget shows the next event in the operator's perspective so they
  // don't have to map "16:00 EDT" → their own clock manually.
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatCountdown(targetIso: string, nowMs: number): string {
  const targetMs = new Date(targetIso).getTime();
  if (Number.isNaN(targetMs)) return "—";
  const diffMs = targetMs - nowMs;
  if (diffMs <= 0) return "nu";
  const totalMinutes = Math.floor(diffMs / 60_000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  const days = Math.floor(hours / 24);
  if (days >= 1) {
    return `${days} d ${hours % 24} u`;
  }
  if (hours >= 1) {
    return `${hours} u ${minutes} min`;
  }
  return `${minutes} min`;
}

function nextEventLabel_nl(entry: MarketHoursEntry, nowMs: number): string {
  if (!entry.next_event_at_utc || !entry.next_event_kind) {
    return entry.state_nl;
  }
  const verb = entry.next_event_kind === "open" ? "opent" : "sluit";
  const time = formatLocalHHMM(entry.next_event_at_utc);
  const eta = formatCountdown(entry.next_event_at_utc, nowMs);
  return `${verb} om ${time} (over ${eta})`;
}

export function MarketHoursWidget() {
  const query = useQuery({
    queryKey: ["market-hours-now"],
    queryFn: async () => {
      const r = await apiClient.getMarketHoursNow();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  // Re-render every 30s so the countdowns tick without waiting for the
  // next API poll. Cheap: only this component re-renders, and only the
  // text inside each row changes.
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNowMs(Date.now()), 30_000);
    return () => clearInterval(id);
  }, []);

  const data = query.data ?? null;
  const markets = data?.markets ?? [];

  return (
    <section
      data-testid="market-hours-widget"
      aria-label="Markt-uren overzicht"
      style={{
        background: "white",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: "12px 16px",
        boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
        fontSize: 13,
        fontFamily:
          "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      <h3
        style={{
          margin: "0 0 8px 0",
          fontSize: 14,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span aria-hidden>🕒</span>
        <span>Markt-uren vandaag</span>
      </h3>

      {query.isLoading && (
        <p data-testid="market-hours-loading" style={{ color: "#6b7280" }}>
          Markten ophalen…
        </p>
      )}

      {!query.isLoading && data === null && (
        <p
          data-testid="market-hours-error"
          style={{ color: "#b91c1c", margin: 0 }}
        >
          Markt-status niet bereikbaar. Controleer of de API draait.
        </p>
      )}

      {!query.isLoading && data !== null && markets.length === 0 && (
        <p
          data-testid="market-hours-empty"
          style={{ color: "#6b7280", margin: 0 }}
        >
          Geen markten gekozen. Selecteer een universe in{" "}
          <a href="/instellingen">Instellingen</a>.
        </p>
      )}

      {markets.length > 0 && (
        <ul
          data-testid="market-hours-list"
          style={{
            listStyle: "none",
            padding: 0,
            margin: 0,
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          {markets.map((m) => (
            <li
              key={m.market_code}
              data-testid={`market-hours-row-${m.market_code}`}
              data-market-state={m.state}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                paddingBottom: 6,
                borderBottom: "1px solid #f3f4f6",
              }}
            >
              <span
                aria-hidden
                style={{
                  display: "inline-block",
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: dotColour(m.state),
                  flexShrink: 0,
                }}
              />
              <div style={{ flexGrow: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500 }}>{m.market_label_nl}</div>
                <div style={{ color: "#6b7280", fontSize: 12 }}>
                  {m.open_local_hhmm}–{m.close_local_hhmm} ({m.timezone})
                </div>
              </div>
              <div
                style={{
                  textAlign: "right",
                  fontSize: 12,
                  color: "#374151",
                  flexShrink: 0,
                }}
              >
                {nextEventLabel_nl(m, nowMs)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
