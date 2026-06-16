"use client";

/**
 * V1.2 §BA / CLAUDE.md §12 follow-up — operator-getrackt dividenden.
 *
 * In V1 hebben we geen broker-dividend-feed; de operator voert ze
 * handmatig in. Component biedt:
 *
 *   - Tabel van geregistreerde dividenden voor het gekozen jaar
 *   - Form om een dividend toe te voegen (symbol, datum, bruto,
 *     bronbelasting %, land)
 *   - Per-regel verwijder-knop
 *   - Year-totals per valuta (bruto / bronbelasting / netto)
 *
 * Verdrag-defaults (US 15 %, NL 15 %, FR 12,8 %, BE 0 %) worden in
 * het form geprefilld op basis van het gekozen land — operator
 * kan overrulen.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import {
  apiClient,
  type DividendListResponse,
  type DividendRow,
} from "@/lib/apiClient";

function fmtMoney(raw: string): string {
  const n = Number(raw);
  if (Number.isNaN(n)) return raw;
  return n.toLocaleString("nl-BE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function MoneyByCurrency({
  amounts,
}: {
  amounts: Record<string, string>;
}) {
  const entries = Object.entries(amounts);
  if (entries.length === 0) return <span>—</span>;
  return (
    <span>
      {entries
        .map(([ccy, amount]) => `${fmtMoney(amount)} ${ccy}`)
        .join(" · ")}
    </span>
  );
}

export function DividendenManager({ year }: { year: number }) {
  const queryClient = useQueryClient();
  const [symbol, setSymbol] = useState("");
  const [payDate, setPayDate] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [gross, setGross] = useState("");
  const [country, setCountry] = useState("US");
  const [pctOverride, setPctOverride] = useState("");
  const [error, setError] = useState<string | null>(null);

  const queryKey = ["dividenden", year];
  const query = useQuery({
    queryKey,
    queryFn: async (): Promise<DividendListResponse | null> => {
      const result = await apiClient.listDividenden({ year });
      return result.ok ? result.data : null;
    },
  });
  const data = query.data ?? null;

  // Prefill withholding override based on country treaty default.
  useEffect(() => {
    if (data === null) return;
    const treaty = data.treaty_defaults_pct_by_country[country] ?? "0";
    if (pctOverride === "" || /^\d+(\.\d+)?$/.test(pctOverride)) {
      // Only refill when empty or already numeric — don't clobber
      // mid-typing.
      setPctOverride(treaty);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [country, data]);

  const createMut = useMutation({
    mutationFn: async () => {
      const result = await apiClient.createDividend({
        symbol: symbol.trim(),
        pay_date: payDate.trim(),
        currency_local: currency.trim(),
        gross_local: gross.trim(),
        withholding_pct: pctOverride.trim() === "" ? null : pctOverride.trim(),
        country_code: country.trim() === "" ? null : country.trim(),
      });
      if (!result.ok) {
        throw new Error("Toevoegen mislukt — controleer de velden.");
      }
      return result.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      setSymbol("");
      setGross("");
      setPayDate("");
      setError(null);
    },
    onError: (err) =>
      setError(err instanceof Error ? err.message : "Onbekende fout."),
  });

  const deleteMut = useMutation({
    mutationFn: async (id: string) => {
      const result = await apiClient.deleteDividend(id);
      if (!result.ok) {
        throw new Error("Verwijderen mislukt.");
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });

  const handleAdd = () => {
    setError(null);
    if (
      symbol.trim() === "" ||
      payDate.trim() === "" ||
      gross.trim() === ""
    ) {
      setError("Vul symbool, datum en bruto in.");
      return;
    }
    createMut.mutate();
  };

  const items: DividendRow[] = data?.items ?? [];

  return (
    <section
      data-testid="dividenden-manager"
      style={{
        background: "#f9fafb",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 12,
      }}
    >
      <h3 style={{ marginTop: 0 }}>Dividenden registreren ({year})</h3>
      <p style={{ margin: 0, fontSize: 13, color: "#374151" }}>
        V1 heeft geen dividend-feed; voer hier de dividenden in die je
        op je rekening ontvangt. De bronbelasting wordt automatisch
        afgetrokken volgens de verdrag-tarieven (US 15 %, NL 15 %,
        FR 12,8 %, BE 0 %) — je kan dat per dividend overschrijven.
      </p>

      <div
        data-testid="dividenden-form"
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr",
          gap: 8,
          marginTop: 12,
          alignItems: "flex-end",
        }}
      >
        <div>
          <label style={{ display: "block", fontSize: 11, color: "#6b7280" }}>
            Symbool
          </label>
          <input
            data-testid="dividend-input-symbol"
            type="text"
            value={symbol}
            placeholder="AAPL"
            onChange={(e) => setSymbol(e.target.value)}
            style={{
              width: "100%",
              padding: "6px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 6,
              fontSize: 13,
            }}
          />
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "#6b7280" }}>
            Datum
          </label>
          <input
            data-testid="dividend-input-date"
            type="date"
            value={payDate}
            onChange={(e) => setPayDate(e.target.value)}
            style={{
              width: "100%",
              padding: "6px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 6,
              fontSize: 13,
            }}
          />
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "#6b7280" }}>
            Bruto
          </label>
          <input
            data-testid="dividend-input-gross"
            type="text"
            inputMode="decimal"
            value={gross}
            placeholder="100"
            onChange={(e) => setGross(e.target.value)}
            style={{
              width: "100%",
              padding: "6px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 6,
              fontSize: 13,
            }}
          />
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "#6b7280" }}>
            Valuta
          </label>
          <select
            data-testid="dividend-input-currency"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            style={{
              width: "100%",
              padding: "6px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 6,
              fontSize: 13,
            }}
          >
            {["USD", "EUR", "GBP", "CHF"].map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "#6b7280" }}>
            Land
          </label>
          <select
            data-testid="dividend-input-country"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            style={{
              width: "100%",
              padding: "6px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 6,
              fontSize: 13,
            }}
          >
            {["US", "NL", "FR", "BE", "GB", "DE"].map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ display: "block", fontSize: 11, color: "#6b7280" }}>
            Bronbelasting % (override)
          </label>
          <input
            data-testid="dividend-input-pct"
            type="text"
            inputMode="decimal"
            value={pctOverride}
            placeholder="15"
            onChange={(e) => setPctOverride(e.target.value)}
            style={{
              width: "100%",
              padding: "6px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 6,
              fontSize: 13,
            }}
          />
        </div>
        <button
          type="button"
          data-testid="dividend-add-button"
          onClick={handleAdd}
          disabled={createMut.isPending}
          style={{
            padding: "8px 12px",
            background: createMut.isPending ? "#9ca3af" : "#15803d",
            color: "#ffffff",
            border: "none",
            borderRadius: 6,
            fontWeight: 600,
            cursor: createMut.isPending ? "not-allowed" : "pointer",
            fontSize: 13,
            gridColumn: "span 4",
          }}
        >
          {createMut.isPending ? "Bezig…" : "Voeg dividend toe"}
        </button>
      </div>
      {error ? (
        <p
          data-testid="dividenden-error"
          style={{ marginTop: 8, color: "#b91c1c", fontSize: 12 }}
        >
          {error}
        </p>
      ) : null}

      {items.length > 0 ? (
        <div style={{ overflowX: "auto", marginTop: 12 }}>
          <table
            data-testid="dividenden-table"
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: 12,
            }}
          >
            <thead>
              <tr style={{ background: "#f3f4f6", textAlign: "left" }}>
                <th>Symbool</th>
                <th>Datum</th>
                <th>Land</th>
                <th>Valuta</th>
                <th style={{ textAlign: "right" }}>Bruto</th>
                <th style={{ textAlign: "right" }}>Bronbelasting %</th>
                <th style={{ textAlign: "right" }}>Bronbelasting</th>
                <th style={{ textAlign: "right" }}>Netto</th>
                <th style={{ textAlign: "right" }} title="Belgische 30% RV - reeds afgehouden bronbelasting = nog te declareren via aangifte">
                  RV-tekort (30%)
                </th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((d) => (
                <tr
                  key={d.dividend_event_id}
                  data-testid={`dividend-row-${d.symbol}-${d.pay_date}`}
                >
                  <td>{d.symbol}</td>
                  <td>{d.pay_date}</td>
                  <td>{d.country_code ?? "—"}</td>
                  <td>{d.currency_local}</td>
                  <td style={{ textAlign: "right" }}>
                    {fmtMoney(d.gross_local)}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    {fmtMoney(d.withholding_pct)} %
                  </td>
                  <td style={{ textAlign: "right", color: "#7f1d1d" }}>
                    {fmtMoney(d.withholding_local)}
                  </td>
                  <td
                    style={{
                      textAlign: "right",
                      fontWeight: 700,
                      color: "#166534",
                    }}
                  >
                    {fmtMoney(d.net_local)}
                  </td>
                  <td
                    data-testid={`dividend-rv-shortfall-${d.dividend_event_id}`}
                    style={{
                      textAlign: "right",
                      color: Number(d.rv_shortfall_local) > 0 ? "#92400e" : "#6b7280",
                    }}
                    title={`${fmtMoney(d.rv_shortfall_pct)}% Belgische RV nog te declareren in de aangifte`}
                  >
                    {fmtMoney(d.rv_shortfall_local)}
                  </td>
                  <td>
                    <button
                      type="button"
                      data-testid={`dividend-delete-${d.dividend_event_id}`}
                      onClick={() => deleteMut.mutate(d.dividend_event_id)}
                      disabled={deleteMut.isPending}
                      style={{
                        padding: "4px 8px",
                        background: "#fee2e2",
                        color: "#991b1b",
                        border: "none",
                        borderRadius: 6,
                        fontWeight: 600,
                        fontSize: 11,
                        cursor: deleteMut.isPending ? "not-allowed" : "pointer",
                      }}
                    >
                      Verwijder
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div
            data-testid="dividenden-totals"
            style={{
              marginTop: 8,
              padding: 8,
              background: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: 6,
              fontSize: 12,
              color: "#374151",
            }}
          >
            <strong>Totalen {year}:</strong> Bruto{" "}
            <MoneyByCurrency
              amounts={data?.totals.gross_by_currency ?? {}}
            />{" "}
            · Bronbelasting{" "}
            <MoneyByCurrency
              amounts={data?.totals.withholding_by_currency ?? {}}
            />{" "}
            · Netto{" "}
            <MoneyByCurrency
              amounts={data?.totals.net_by_currency ?? {}}
            />{" "}
            ({data?.totals.count ?? 0} dividend
            {(data?.totals.count ?? 0) === 1 ? "" : "en"})
          </div>
        </div>
      ) : (
        <p
          data-testid="dividenden-empty-state"
          style={{
            margin: "12px 0 0",
            fontStyle: "italic",
            color: "#6b7280",
            fontSize: 13,
          }}
        >
          Geen dividenden geregistreerd voor {year}.
        </p>
      )}
    </section>
  );
}
