"use client";

/**
 * V1.2 §AF — Portfolio KPI tiles.
 *
 * Four tiles at-a-glance: total portfolio value, day result, cash
 * available, position count. Values come straight from the valuation
 * readiness endpoint plus IBKR cash snapshot. The day-result tile
 * uses the NAV history (latest vs previous point) — read-only,
 * deterministic.
 */

import { useQuery } from "@tanstack/react-query";

import {
  apiClient,
  type IbkrCashSnapshot,
  type NavHistoryResponse,
  type PortfolioValuationReadinessResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function Tile({
  label,
  value,
  help,
  tone,
  testid,
}: {
  label: string;
  value: string;
  help: string;
  tone: "ok" | "info" | "wacht" | "aandacht";
  testid: string;
}) {
  const colors = (() => {
    switch (tone) {
      case "ok":
        return { fg: "#166534" };
      case "wacht":
        return { fg: "#854d0e" };
      case "aandacht":
        return { fg: "#9a3412" };
      default:
        return { fg: "#1f2937" };
    }
  })();
  return (
    <div
      data-testid={testid}
      title={help}
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 12,
      }}
    >
      <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 18, fontWeight: 700, color: colors.fg }}>
        {value}
      </div>
    </div>
  );
}

function navDelta(history: NavHistoryResponse | null): {
  label: string;
  tone: "ok" | "info" | "aandacht";
} {
  if (!history || history.points.length < 2)
    return { label: "Niet beschikbaar", tone: "info" };
  const sorted = [...history.points].sort((a, b) =>
    a.recorded_at_utc.localeCompare(b.recorded_at_utc),
  );
  const last = Number.parseFloat(sorted[sorted.length - 1].nav_value);
  const prev = Number.parseFloat(sorted[sorted.length - 2].nav_value);
  if (!Number.isFinite(last) || !Number.isFinite(prev) || prev === 0)
    return { label: "Niet beschikbaar", tone: "info" };
  const delta = last - prev;
  const pct = (delta / prev) * 100;
  const sign = delta >= 0 ? "+" : "";
  const ccy = history.base_currency ?? "";
  const tone: "ok" | "info" | "aandacht" = delta > 0 ? "ok" : delta < 0 ? "aandacht" : "info";
  return {
    label: `${sign}${delta.toFixed(2)} ${ccy} (${sign}${pct.toFixed(2)} %)`,
    tone,
  };
}

export function PortfolioKpiTiles() {
  const valuationQuery = useQuery({
    queryKey: ["kpi-tiles-valuation"],
    queryFn: async (): Promise<PortfolioValuationReadinessResponse | null> => {
      const r = await apiClient.getPortfolioValuationReadiness();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const cashQuery = useQuery({
    queryKey: ["kpi-tiles-cash"],
    queryFn: async (): Promise<IbkrCashSnapshot[]> => {
      const r = await apiClient.getIbkrCash();
      return r.ok ? (r.data.items ?? []) : [];
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const navQuery = useQuery({
    queryKey: ["kpi-tiles-nav-history"],
    queryFn: async (): Promise<NavHistoryResponse | null> => {
      const r = await apiClient.getNavHistory(7);
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const valuation = valuationQuery.data ?? null;
  const cash = (cashQuery.data ?? [])[0] ?? null;
  const nav = navDelta(navQuery.data ?? null);

  const totalValue =
    valuation?.total_portfolio_value_available && valuation.total_portfolio_value
      ? `${valuation.base_currency ?? ""} ${valuation.total_portfolio_value}`.trim()
      : "Niet beschikbaar";
  const cashAvailable = cash?.available_funds
    ? `${cash.base_currency} ${cash.available_funds}`
    : cash?.cash
      ? `${cash.base_currency} ${cash.cash}`
      : "Niet beschikbaar";
  const positionCount = valuation?.rows
    ? valuation.rows.filter((r) => {
        const q = Number.parseFloat(r.quantity);
        return Number.isFinite(q) && q !== 0;
      }).length
    : 0;

  return (
    <section
      data-testid="portfolio-kpi-tiles"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
        gap: 10,
        marginBottom: 12,
      }}
    >
      <Tile
        label="Totale portefeuillewaarde"
        value={totalValue}
        help="Som van veilige marktwaarde + cash; geen browserberekening."
        tone={
          valuation?.total_portfolio_value_available ? "ok" : "wacht"
        }
        testid="kpi-tile-total-value"
      />
      <Tile
        label="Dagresultaat (NAV)"
        value={nav.label}
        help="Laatste NAV-punt vs vorig punt uit nav-history; deterministische delta."
        tone={nav.tone === "aandacht" ? "aandacht" : nav.tone}
        testid="kpi-tile-day-result"
      />
      <Tile
        label="Cash beschikbaar"
        value={cashAvailable}
        help="Available funds uit IBKR cash-snapshot, valt terug op cashwaarde."
        tone={cash?.available_funds ? "ok" : "wacht"}
        testid="kpi-tile-cash"
      />
      <Tile
        label="Aantal posities"
        value={`${positionCount}`}
        help="Aantal posities met niet-nul aantal in laatste valuation."
        tone={positionCount > 0 ? "ok" : "info"}
        testid="kpi-tile-position-count"
      />
    </section>
  );
}
