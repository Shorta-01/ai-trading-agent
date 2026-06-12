"use client";

/**
 * V1.2 §AE — Profit-harvest cyclus widget.
 *
 * Per held position: entry price (from snapshot), current market
 * price (from snapshot), unrealized return %, and a progress bar
 * toward the +4% Belgian tax-aware profit-take target (TOB round-trip
 * ≈ 0.70%; +4% nets ~+3.30% after taxes).
 *
 * Numbers come straight from the valuation readiness endpoint —
 * nothing is computed in the browser beyond the deterministic
 * distance-to-target arithmetic. Read-only; never promotes to an
 * order.
 */

import { useQuery } from "@tanstack/react-query";

import { EmptyState } from "@/components/EmptyState";
import {
  apiClient,
  type PortfolioValuationReadinessResponse,
  type PortfolioValuationReadinessRow,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;
const PROFIT_TARGET_PCT = 4.0;

function parsePct(value: string | null): number | null {
  if (value === null || value === undefined) return null;
  const cleaned = value.replace("%", "").replace(",", ".").trim();
  const num = Number.parseFloat(cleaned);
  return Number.isFinite(num) ? num : null;
}

function formatPct(num: number): string {
  const sign = num >= 0 ? "+" : "";
  return `${sign}${num.toFixed(2).replace(".", ",")} %`;
}

function progressColor(pct: number): string {
  if (pct >= PROFIT_TARGET_PCT) return "#16a34a";
  if (pct >= PROFIT_TARGET_PCT * 0.75) return "#65a30d";
  if (pct >= 0) return "#0ea5e9";
  if (pct >= -2) return "#f59e0b";
  return "#dc2626";
}

function PositionRow({ row }: { row: PortfolioValuationReadinessRow }) {
  const symbol = row.symbol ?? "—";
  const currency = row.currency ?? "";
  const entry = row.cost_basis ?? row.average_cost ?? null;
  const current = row.market_price ?? null;
  const pct = parsePct(row.unrealized_pl_percent);

  const hasTargetData = pct !== null;
  const distance = hasTargetData ? PROFIT_TARGET_PCT - pct : null;
  const progressRatio = hasTargetData ? Math.max(0, Math.min(1, pct / PROFIT_TARGET_PCT)) : 0;

  return (
    <div
      data-testid={`profit-harvest-row-${symbol}`}
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 12,
        marginBottom: 8,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 12,
          marginBottom: 6,
        }}
      >
        <span style={{ fontWeight: 700, fontSize: 14 }}>{symbol}</span>
        <span style={{ fontSize: 12, color: "#6b7280" }}>
          {row.quantity} stuks {currency}
        </span>
        {hasTargetData && pct !== null ? (
          <span
            data-testid={`profit-harvest-row-${symbol}-pct`}
            style={{
              marginLeft: "auto",
              fontWeight: 700,
              fontSize: 14,
              color: progressColor(pct),
            }}
          >
            {formatPct(pct)}
          </span>
        ) : (
          <span style={{ marginLeft: "auto", fontSize: 12, color: "#6b7280" }}>
            Niet beschikbaar
          </span>
        )}
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 8,
          fontSize: 12,
          color: "#374151",
          marginBottom: 8,
        }}
      >
        <div>
          <div style={{ color: "#6b7280", fontSize: 11 }}>Entry</div>
          <div>{entry ?? "—"}</div>
        </div>
        <div>
          <div style={{ color: "#6b7280", fontSize: 11 }}>Huidige prijs</div>
          <div>{current ?? "—"}</div>
        </div>
        <div>
          <div style={{ color: "#6b7280", fontSize: 11 }}>Tot +4% doel</div>
          <div
            data-testid={`profit-harvest-row-${symbol}-distance`}
            style={{
              color: distance !== null && distance <= 0 ? "#16a34a" : "#374151",
              fontWeight: distance !== null && distance <= 0 ? 700 : 400,
            }}
          >
            {distance === null
              ? "—"
              : distance <= 0
                ? "Doel bereikt"
                : `${distance.toFixed(2).replace(".", ",")} pp`}
          </div>
        </div>
      </div>
      {hasTargetData && pct !== null ? (
        <div
          data-testid={`profit-harvest-row-${symbol}-progress`}
          style={{
            position: "relative",
            background: "#f3f4f6",
            borderRadius: 4,
            height: 8,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              width: `${progressRatio * 100}%`,
              background: progressColor(pct),
              transition: "width 200ms",
            }}
          />
        </div>
      ) : null}
    </div>
  );
}

export function ProfitHarvestCycleWidget() {
  const query = useQuery({
    queryKey: ["profit-harvest-cycle"],
    queryFn: async (): Promise<PortfolioValuationReadinessResponse | null> => {
      const result = await apiClient.getPortfolioValuationReadiness();
      return result.ok ? result.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const data = query.data ?? null;

  const positionRows = (data?.rows ?? []).filter((row) => {
    const qty = Number.parseFloat(row.quantity);
    return Number.isFinite(qty) && qty !== 0;
  });
  const sorted = [...positionRows].sort((a, b) => {
    const pa = parsePct(a.unrealized_pl_percent) ?? -Infinity;
    const pb = parsePct(b.unrealized_pl_percent) ?? -Infinity;
    return pb - pa;
  });

  return (
    <section
      data-testid="profit-harvest-cycle-widget"
      className="dashboard-panel"
    >
      <div className="panel-head">
        <h2>Profit-harvest cyclus</h2>
        <span
          style={{
            fontSize: 11,
            color: "#6b7280",
            background: "#f3f4f6",
            padding: "2px 8px",
            borderRadius: 10,
          }}
        >
          Doel: +4% (na TOB ≈ +3,30%)
        </span>
      </div>
      <p className="top-sub">
        Per positie: instapprijs, huidige prijs en afstand tot het +4%
        winstdoel (Belgisch belastingbewust, TOB 0,35% × 2 ≈ 0,70%
        round-trip). Read-only — geen orderpromotie.
      </p>
      {sorted.length === 0 ? (
        <EmptyState
          title="Nog geen posities in cyclus"
          message="Synchroniseer eerst IBKR-snapshots zodat de waardering beschikbaar is."
        />
      ) : (
        <div data-testid="profit-harvest-cycle-list">
          {sorted.map((row) => (
            <PositionRow
              key={`${row.conid ?? row.symbol ?? "row"}-${row.symbol}`}
              row={row}
            />
          ))}
        </div>
      )}
    </section>
  );
}
