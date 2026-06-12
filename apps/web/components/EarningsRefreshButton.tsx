"use client";

/**
 * V1.2 §AK — Manual earnings refresh button.
 *
 * Klein dashboard-widget dat:
 * 1. De huidige IBKR-posities ophaalt.
 * 2. Symbool+exchange omzet naar EODHD-format (default ``.US`` voor
 *    de V1 universe, vandaar de simpele suffix-map).
 * 3. ``POST /earnings/refresh`` aanroept zodat de
 *    ``earnings_events`` tabel actueel wordt.
 *
 * Geen broker-promotie pad; alleen schrijft naar de
 * earnings-storage. De operator kan dit handmatig draaien naast
 * (of in plaats van) de morning-chain leg.
 */

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  apiClient,
  type EarningsRefreshResponse,
  type IbkrPositionSnapshot,
} from "@/lib/apiClient";

const EXCHANGE_SUFFIX: Record<string, string> = {
  NASDAQ: "US",
  NYSE: "US",
  ARCA: "US",
  AMEX: "US",
  BATS: "US",
  EURONEXT: "PA",
  AEB: "AS",
  XETRA: "XETRA",
};

function toEodhdSymbol(
  position: IbkrPositionSnapshot,
): string | null {
  const exchangeRaw = (position.exchange ?? "").trim().toUpperCase();
  const suffix = EXCHANGE_SUFFIX[exchangeRaw];
  if (!suffix) return null;
  if (!position.symbol) return null;
  return `${position.symbol}.${suffix}`;
}

function uniqueEodhdSymbols(
  positions: IbkrPositionSnapshot[],
): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const position of positions) {
    const qty = Number.parseFloat(position.quantity);
    if (!Number.isFinite(qty) || qty === 0) continue;
    const sym = toEodhdSymbol(position);
    if (sym === null || seen.has(sym)) continue;
    seen.add(sym);
    out.push(sym);
  }
  return out;
}

export function EarningsRefreshButton() {
  const positionsQuery = useQuery({
    queryKey: ["earnings-refresh-button-positions"],
    queryFn: async (): Promise<IbkrPositionSnapshot[]> => {
      const r = await apiClient.getIbkrPositions();
      return r.ok ? (r.data.items ?? []) : [];
    },
  });
  const symbols = uniqueEodhdSymbols(positionsQuery.data ?? []);

  const [result, setResult] = useState<EarningsRefreshResponse | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (): Promise<EarningsRefreshResponse> => {
      const r = await apiClient.refreshEarnings({
        symbols,
        window_days: 21,
      });
      if (!r.ok) throw new Error(r.reason ?? "request_failed");
      return r.data;
    },
    onSuccess: (data) => {
      setResult(data);
      setErrorText(null);
    },
    onError: (err: unknown) => {
      setResult(null);
      setErrorText(
        err instanceof Error ? err.message : "Onbekende fout",
      );
    },
  });

  const disabled = mutation.isPending || symbols.length === 0;
  const label = mutation.isPending
    ? "Verversen…"
    : symbols.length === 0
      ? "Geen posities om te verversen"
      : `Earnings verversen (${symbols.length} symbolen)`;

  return (
    <section
      data-testid="earnings-refresh-button-widget"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: "8px 12px",
        marginBottom: 12,
        fontSize: 13,
      }}
    >
      <strong style={{ color: "#374151" }}>Earnings-feed:</strong>
      <button
        type="button"
        data-testid="earnings-refresh-button"
        onClick={() => mutation.mutate()}
        disabled={disabled}
        style={{
          background: disabled ? "#9ca3af" : "#1d4ed8",
          color: "#ffffff",
          border: "none",
          borderRadius: 6,
          padding: "4px 12px",
          fontSize: 12,
          fontWeight: 600,
          cursor: disabled ? "not-allowed" : "pointer",
        }}
      >
        {label}
      </button>
      {result ? (
        <span
          data-testid="earnings-refresh-button-result"
          style={{
            fontSize: 12,
            color: result.status === "ok" ? "#166534" : "#854d0e",
          }}
        >
          {result.status === "ok"
            ? `OK — ${result.upserted_count} events bijgewerkt`
            : result.status === "skipped"
              ? `Overgeslagen — ${result.error_text ?? "geen reden"}`
              : `Fout — ${result.error_text ?? "onbekend"}`}
        </span>
      ) : null}
      {errorText ? (
        <span
          data-testid="earnings-refresh-button-error"
          style={{ fontSize: 12, color: "#991b1b" }}
        >
          Fout: {errorText}
        </span>
      ) : null}
    </section>
  );
}
