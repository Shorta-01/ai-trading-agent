"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/apiClient";

/**
 * Top-of-dashboard triage strip.
 *
 * Three small inline widgets that answer the operator's first
 * questions at 07:00, in order:
 *
 *   1. *Did last night go OK?*  → MorningChainBanner (red/green/amber)
 *   2. *What's coming next?*    → NextEventCountdown
 *   3. *Is the AI still usable?* → ClaudeBudgetPill
 *
 * Each piece degrades gracefully on a transport failure (loading
 * spinner first, then a Dutch "niet bereikbaar" line) so the strip
 * never blocks the rest of the page from rendering.
 *
 * The widgets co-locate because they share the same audience and
 * the same "glance before deciding what to click" intent — splitting
 * them into separate sections would force the operator to scan three
 * different regions of the page for one orientation read.
 */

const SCHEDULER_POLL_MS = 60_000;
const BUDGET_POLL_MS = 5 * 60_000;
const CLOCK_TICK_MS = 30_000;

// ---- shared helpers -----------------------------------------------------

function formatCountdown(targetIso: string, nowMs: number): string {
  const targetMs = new Date(targetIso).getTime();
  if (Number.isNaN(targetMs)) return "—";
  const diffMs = targetMs - nowMs;
  if (diffMs <= 0) return "nu";
  const totalMinutes = Math.floor(diffMs / 60_000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  const days = Math.floor(hours / 24);
  if (days >= 1) return `${days} d ${hours % 24} u`;
  if (hours >= 1) return `${hours} u ${minutes} min`;
  return `${minutes} min`;
}

function formatLocalHHMM(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function pillStyle(colour: string): React.CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    padding: "6px 12px",
    borderRadius: 999,
    background: "white",
    border: `1px solid ${colour}`,
    color: "#111827",
    fontSize: 13,
    fontFamily:
      "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
    boxShadow: "0 1px 2px rgba(0, 0, 0, 0.04)",
  };
}

function dotSpan(colour: string): React.CSSProperties {
  return {
    display: "inline-block",
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: colour,
    flexShrink: 0,
  };
}

// ---- 1. Morning chain banner -------------------------------------------

type MorningChainLevel = "ok" | "warn" | "fail" | "loading";

function morningChainColour(level: MorningChainLevel): string {
  switch (level) {
    case "ok":
      return "#16a34a";
    case "warn":
      return "#f59e0b";
    case "fail":
      return "#dc2626";
    case "loading":
    default:
      return "#9ca3af";
  }
}

function MorningChainBanner() {
  const query = useQuery({
    queryKey: ["triage", "scheduler-v127"],
    queryFn: async () => {
      const r = await apiClient.getSchedulerV127Status();
      return r.ok ? r.data : null;
    },
    refetchInterval: SCHEDULER_POLL_MS,
  });

  const level: MorningChainLevel = (() => {
    if (query.isLoading) return "loading";
    if (query.isError) return "fail";
    const d = query.data;
    if (!d) return "fail";
    if (!d.enabled) return "warn";
    if (d.last_outcome === "error") return "fail";
    if (d.last_outcome === "succeeded" || d.last_outcome === "success")
      return "ok";
    // Any other outcome (e.g. "partial", "pending") → amber so the
    // operator clicks through to see what's actually going on.
    return "warn";
  })();

  const labelText = (() => {
    const d = query.data;
    if (!d) return "Morning chain — status onbekend";
    const when = d.last_run_at
      ? formatLocalHHMM(d.last_run_at)
      : "—";
    const verdict =
      level === "ok"
        ? "OK"
        : level === "fail"
          ? "ERROR"
          : level === "warn"
            ? "WARN"
            : "—";
    return `Morning chain ${when} — ${verdict}`;
  })();

  return (
    <div
      data-testid="triage-morning-chain-banner"
      data-level={level}
      style={pillStyle(morningChainColour(level))}
      title="Status van de laatste scheduler-fire."
    >
      <span aria-hidden style={dotSpan(morningChainColour(level))} />
      <span style={{ fontWeight: 500 }}>{labelText}</span>
    </div>
  );
}

// ---- 2. Next-event countdown -------------------------------------------

function NextEventCountdown() {
  const query = useQuery({
    queryKey: ["triage", "scheduler-v127-next"],
    queryFn: async () => {
      const r = await apiClient.getSchedulerV127Status();
      return r.ok ? r.data : null;
    },
    refetchInterval: SCHEDULER_POLL_MS,
  });

  // Tick the relative countdown without waiting for the next API
  // poll — only this component re-renders.
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNowMs(Date.now()), CLOCK_TICK_MS);
    return () => clearInterval(id);
  }, []);

  const nextIso = (query.data?.next_runs ?? [])
    .filter((s): s is string => typeof s === "string" && s.length > 0)
    .sort()[0];

  if (query.isLoading) {
    return (
      <div
        data-testid="triage-next-event-loading"
        style={pillStyle("#e5e7eb")}
      >
        <span aria-hidden>⏭️</span>
        <span style={{ color: "#6b7280" }}>Volgende: laden…</span>
      </div>
    );
  }
  if (!nextIso) {
    return (
      <div
        data-testid="triage-next-event-empty"
        style={pillStyle("#e5e7eb")}
      >
        <span aria-hidden>⏭️</span>
        <span style={{ color: "#6b7280" }}>
          Geen volgende fire gepland.
        </span>
      </div>
    );
  }

  return (
    <div
      data-testid="triage-next-event"
      data-next-iso={nextIso}
      style={pillStyle("#cbd5e1")}
    >
      <span aria-hidden>⏭️</span>
      <span>
        Volgende: {formatLocalHHMM(nextIso)} (over{" "}
        {formatCountdown(nextIso, nowMs)})
      </span>
    </div>
  );
}

// ---- 3. Claude budget pill ---------------------------------------------

type BudgetLevel = "ok" | "warn" | "fail" | "loading" | "unconfigured";

function budgetColour(level: BudgetLevel): string {
  switch (level) {
    case "ok":
      return "#16a34a";
    case "warn":
      return "#f59e0b";
    case "fail":
      return "#dc2626";
    case "unconfigured":
    case "loading":
    default:
      return "#9ca3af";
  }
}

function ClaudeBudgetPill() {
  const query = useQuery({
    queryKey: ["triage", "claude-budget"],
    queryFn: async () => {
      const r = await apiClient.getClaudeBudgetStatus();
      return r.ok ? r.data : null;
    },
    refetchInterval: BUDGET_POLL_MS,
  });

  if (query.isLoading) {
    return (
      <div data-testid="triage-budget-loading" style={pillStyle("#e5e7eb")}>
        <span aria-hidden>💸</span>
        <span style={{ color: "#6b7280" }}>Claude budget — laden…</span>
      </div>
    );
  }

  const d = query.data;
  if (!d || d.status === "not_configured") {
    return (
      <div
        data-testid="triage-budget-unconfigured"
        data-level="unconfigured"
        style={pillStyle(budgetColour("unconfigured"))}
      >
        <span aria-hidden style={dotSpan(budgetColour("unconfigured"))} />
        <span>Claude budget — niet geconfigureerd.</span>
      </div>
    );
  }

  const cap = Number.parseFloat(d.monthly_cap_eur);
  const used = d.monthly_total_eur
    ? Number.parseFloat(d.monthly_total_eur)
    : 0;
  const pct = cap > 0 ? Math.min(100, (used / cap) * 100) : 0;

  const level: BudgetLevel = (() => {
    if (d.exceeded) return "fail";
    if (pct >= 80) return "warn";
    return "ok";
  })();

  return (
    <div
      data-testid="triage-budget-pill"
      data-level={level}
      style={pillStyle(budgetColour(level))}
      title="Claude maandbudget — gedeeld tussen uitleg- en TS-providers."
    >
      <span aria-hidden style={dotSpan(budgetColour(level))} />
      <span>
        Claude budget: €{used.toFixed(2)} / €{cap.toFixed(2)} (
        {pct.toFixed(0)}%)
      </span>
    </div>
  );
}

// ---- assembled strip ----------------------------------------------------

export function TriageStrip() {
  return (
    <section
      data-testid="dashboard-triage-strip"
      aria-label="Dashboard triage strip"
      style={{
        display: "flex",
        gap: 12,
        flexWrap: "wrap",
        marginBottom: "0.75rem",
      }}
    >
      <MorningChainBanner />
      <NextEventCountdown />
      <ClaudeBudgetPill />
    </section>
  );
}
