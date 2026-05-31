"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/apiClient";

/**
 * Bottom-right floating status widget.
 *
 * Polls the same five status endpoints the cold-start smoke test
 * reads (`/health`, `/storage/status/online`, `/scheduler/v127/status`,
 * `/ibkr/sync/status`, `/system/events/active`) and renders a compact
 * card with a dot per concern. Click the card to expand and see the
 * Dutch detail line per check. The widget never blocks the operator —
 * a failed health probe degrades gracefully to a grey dot rather than
 * crashing the layout.
 *
 * The collapsed state is meant to live always-on in the corner so the
 * operator notices a red dot from the corner of their eye instead of
 * having to open the systeemmeldingen tab.
 */

const POLL_INTERVAL_MS = 30_000;

type DotLevel = "ok" | "warn" | "fail" | "loading";

type CheckSummary = {
  key: string;
  label_nl: string;
  level: DotLevel;
  detail_nl: string;
};

function _level(
  query: { isLoading: boolean; isError: boolean },
  resolveLevel: () => DotLevel,
): DotLevel {
  if (query.isLoading) return "loading";
  if (query.isError) return "fail";
  return resolveLevel();
}

function dotColour(level: DotLevel): string {
  switch (level) {
    case "ok":
      return "#16a34a"; // green-600
    case "warn":
      return "#f59e0b"; // amber-500
    case "fail":
      return "#dc2626"; // red-600
    case "loading":
    default:
      return "#9ca3af"; // grey-400
  }
}

function worstLevel(levels: DotLevel[]): DotLevel {
  const rank = { ok: 0, loading: 0, warn: 1, fail: 2 };
  return levels.reduce<DotLevel>((worst, current) => {
    return rank[current] > rank[worst] ? current : worst;
  }, "ok");
}

export function SystemMonitorWidget() {
  const [expanded, setExpanded] = useState(false);

  const apiQuery = useQuery({
    queryKey: ["monitor", "api-health"],
    queryFn: async () => {
      const r = await apiClient.getApiHealth();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const storageQuery = useQuery({
    queryKey: ["monitor", "storage-online"],
    queryFn: async () => {
      const r = await apiClient.getStorageStatusOnline();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const schedulerQuery = useQuery({
    queryKey: ["monitor", "scheduler-v127"],
    queryFn: async () => {
      const r = await apiClient.getSchedulerV127Status();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const ibkrQuery = useQuery({
    queryKey: ["monitor", "ibkr-sync"],
    queryFn: async () => {
      const r = await apiClient.getIbkrSyncStatus();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const eventsQuery = useQuery({
    queryKey: ["monitor", "system-events"],
    queryFn: async () => {
      const r = await apiClient.getActiveSystemEvents();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  // ---- compute per-check verdicts ----------------------------------
  const apiCheck: CheckSummary = {
    key: "api",
    label_nl: "API",
    level: _level(apiQuery, () =>
      apiQuery.data?.status === "ok" ? "ok" : "fail",
    ),
    detail_nl:
      apiQuery.data?.status === "ok"
        ? "API antwoordt op /health."
        : "API niet bereikbaar.",
  };

  const storageCheck: CheckSummary = {
    key: "storage",
    label_nl: "Opslag",
    level: _level(storageQuery, () => {
      const d = storageQuery.data;
      if (!d) return "fail";
      if (!d.configured) return "warn";
      if (!d.connected) return "fail";
      return d.safe_to_write ? "ok" : "fail";
    }),
    detail_nl:
      storageQuery.data?.writes_status_nl ?? "Status onbekend.",
  };

  const schedulerCheck: CheckSummary = {
    key: "scheduler",
    label_nl: "Scheduler",
    level: _level(schedulerQuery, () => {
      const d = schedulerQuery.data;
      if (!d) return "fail";
      if (!d.enabled) return "warn";
      if (d.last_outcome === "error") return "fail";
      return "ok";
    }),
    detail_nl: schedulerQuery.data?.enabled
      ? `Volgende fires: ${
          (schedulerQuery.data?.next_runs ?? []).join(", ") || "—"
        }`
      : "Worker-scheduler heeft nog geen heartbeat.",
  };

  const ibkrCheck: CheckSummary = {
    key: "ibkr",
    label_nl: "IBKR",
    level: _level(ibkrQuery, () => {
      const d = ibkrQuery.data;
      if (!d) return "warn";
      if (!d.configured) return "warn";
      // ``actions_allowed`` is the API's downstream-safe boolean — true
      // when the latest sync completed cleanly and the operator's
      // actions are permitted. Falls back to ``configured`` when the
      // newer field is absent so older API builds still surface OK.
      const ready = d.actions_allowed ?? true;
      return ready ? "ok" : "warn";
    }),
    detail_nl: ibkrQuery.data?.status_nl ?? "IBKR-sync status onbekend.",
  };

  const activeCount = eventsQuery.data?.events?.length ?? 0;
  const hasBlocking = (eventsQuery.data?.events ?? []).some(
    (e) =>
      e.blocks_suggestions || e.blocks_writes || e.blocks_ai_explanation,
  );
  const eventsCheck: CheckSummary = {
    key: "events",
    label_nl: "Meldingen",
    level: _level(eventsQuery, () => {
      if (!eventsQuery.data) return "warn";
      if (activeCount === 0) return "ok";
      return hasBlocking ? "fail" : "warn";
    }),
    detail_nl:
      activeCount === 0
        ? "Geen actieve systeemmeldingen."
        : `${activeCount} actieve melding(en)${
            hasBlocking ? " (blokkerend)" : ""
          }.`,
  };

  const checks = [apiCheck, storageCheck, schedulerCheck, ibkrCheck, eventsCheck];
  const overall = worstLevel(checks.map((c) => c.level));

  return (
    <div
      data-testid="system-monitor-widget"
      data-overall-level={overall}
      className="system-monitor-widget"
      style={{
        position: "fixed",
        bottom: 16,
        right: 16,
        zIndex: 50,
        background: "white",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.08)",
        padding: expanded ? "12px 16px" : "8px 12px",
        minWidth: expanded ? 280 : "auto",
        fontSize: 13,
        fontFamily:
          "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
        cursor: "pointer",
      }}
      onClick={() => setExpanded((prev) => !prev)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setExpanded((prev) => !prev);
        }
      }}
      role="button"
      tabIndex={0}
      aria-expanded={expanded}
      aria-label={
        expanded
          ? "Systeem-monitor inklappen"
          : `Systeem-monitor uitklappen (status: ${overall})`
      }
      title="Systeemmonitor — klik voor detail."
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span
          data-testid="system-monitor-overall-dot"
          aria-hidden
          style={{
            display: "inline-block",
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: dotColour(overall),
            boxShadow:
              overall === "fail"
                ? "0 0 6px rgba(220, 38, 38, 0.6)"
                : "none",
          }}
        />
        <span style={{ fontWeight: 600 }}>Systeemmonitor</span>
        {!expanded && (
          <span
            data-testid="system-monitor-dot-row"
            style={{
              display: "inline-flex",
              gap: 4,
              marginLeft: 6,
            }}
          >
            {checks.map((c) => (
              <span
                key={c.key}
                aria-hidden
                title={`${c.label_nl}: ${c.detail_nl}`}
                style={{
                  display: "inline-block",
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: dotColour(c.level),
                }}
              />
            ))}
          </span>
        )}
      </div>
      {expanded && (
        <ul
          data-testid="system-monitor-detail-list"
          style={{
            listStyle: "none",
            padding: 0,
            margin: "10px 0 0 0",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {checks.map((c) => (
            <li
              key={c.key}
              data-testid={`system-monitor-check-${c.key}`}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 8,
              }}
            >
              <span
                aria-hidden
                style={{
                  display: "inline-block",
                  width: 8,
                  height: 8,
                  marginTop: 6,
                  borderRadius: "50%",
                  background: dotColour(c.level),
                  flexShrink: 0,
                }}
              />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 500 }}>{c.label_nl}</div>
                <div
                  style={{
                    color: "#6b7280",
                    fontSize: 12,
                    wordBreak: "break-word",
                  }}
                >
                  {c.detail_nl}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
