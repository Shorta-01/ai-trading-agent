"use client";

/**
 * V1.2 §AV / CLAUDE.md §7.2 — Macro-regime info-strip.
 *
 * Smal bovenaan-dashboard banner met de meest recente macro-staat
 * van de orchestrator. Geen blokkade — alleen informatie. Drie
 * niveaus, één per kleur:
 *
 *   - rustig (info, groen)      — markt staat oké voor BUYs
 *   - verhoogd (warning, geel)  — VIX of S&P-trend schreeuwt
 *   - stress (critical, rood)   — beide signalen tegelijk
 *   - onbekend (info, grijs)    — nog geen orchestrator batch
 *
 * Bij ``rustig`` is de strip subtiel; bij stress wordt-ie luidruchtig
 * zodat de operator niet door gewoonte op "Goedkeuren" drukt.
 */

import { useQuery } from "@tanstack/react-query";

import { apiClient, type MacroSnapshotResponse } from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function severityStyle(severity: MacroSnapshotResponse["severity"]) {
  switch (severity) {
    case "critical":
      return { bg: "#fee2e2", fg: "#7f1d1d", border: "#fecaca" };
    case "warning":
      return { bg: "#fef3c7", fg: "#92400e", border: "#fde68a" };
    default:
      return { bg: "#f0fdf4", fg: "#166534", border: "#bbf7d0" };
  }
}

function stateLabel(state: MacroSnapshotResponse["state"]): string {
  switch (state) {
    case "rustig":
      return "Rustig";
    case "verhoogd":
      return "Verhoogd";
    case "stress":
      return "Stress";
    default:
      return "Onbekend";
  }
}

export function MacroRegimeStrip() {
  const query = useQuery({
    queryKey: ["macro-snapshot"],
    queryFn: async (): Promise<MacroSnapshotResponse | null> => {
      const result = await apiClient.getMacroSnapshot();
      return result.ok ? result.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const data = query.data ?? null;
  // Even before the first fetch we render the banner shell so the
  // layout doesn't jump — fall back to "onbekend".
  const state = data?.state ?? "onbekend";
  const severity = data?.severity ?? "info";
  const headline =
    data?.headline_nl ??
    "Macro-regime laden — orchestrator-snapshot wordt opgehaald.";
  const style = severityStyle(severity);
  return (
    <section
      data-testid="macro-regime-strip"
      data-state={state}
      data-severity={severity}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "8px 12px",
        marginBottom: 12,
        background: style.bg,
        color: style.fg,
        border: `1px solid ${style.border}`,
        borderRadius: 6,
        fontSize: 13,
      }}
    >
      <span
        data-testid="macro-regime-badge"
        style={{
          padding: "2px 8px",
          background: style.fg,
          color: style.bg,
          borderRadius: 10,
          fontWeight: 700,
          fontSize: 11,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
        }}
      >
        {stateLabel(state)}
      </span>
      <span
        data-testid="macro-regime-headline"
        style={{ flex: 1 }}
      >
        {headline}
      </span>
      {data?.vix_level != null ? (
        <span
          data-testid="macro-regime-vix"
          style={{ fontSize: 12, opacity: 0.8 }}
        >
          VIX {data.vix_level.toFixed(1).replace(".", ",")}
        </span>
      ) : null}
    </section>
  );
}
