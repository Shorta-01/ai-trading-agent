"use client";

/**
 * V1.2 §BC — Maandrapport-PDF archief.
 *
 * Lijst van geregistreerde maandrapport-PDFs + "Genereer voor deze
 * maand"-knop. Operator downloadt elk archief direct als PDF.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiClient } from "@/lib/apiClient";

const MONTH_LABELS_NL = [
  "Januari", "Februari", "Maart", "April", "Mei", "Juni",
  "Juli", "Augustus", "September", "Oktober", "November", "December",
];

export function ArchivePanel({ defaultYear, defaultMonth }: { defaultYear: number; defaultMonth: number }) {
  const queryClient = useQueryClient();
  const [genYear, setGenYear] = useState(defaultYear);
  const [genMonth, setGenMonth] = useState(defaultMonth);
  const [error, setError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["rapporten-archief"],
    queryFn: async () => {
      const result = await apiClient.listArchive();
      return result.ok ? result.data : null;
    },
  });
  const items = query.data?.items ?? [];

  const generateMut = useMutation({
    mutationFn: async () => {
      const result = await apiClient.generateArchive({
        year: genYear,
        month: genMonth,
      });
      if (!result.ok) {
        throw new Error("PDF genereren mislukt.");
      }
      return result.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rapporten-archief"] });
      setError(null);
    },
    onError: (err) =>
      setError(err instanceof Error ? err.message : "Onbekende fout."),
  });

  return (
    <section
      data-testid="rapport-archive-panel"
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 12,
        marginBottom: 16,
      }}
    >
      <h2 style={{ marginTop: 0 }}>PDF-archief</h2>
      <p style={{ margin: 0, fontSize: 13, color: "#374151" }}>
        Geregistreerde maandrapport-PDFs. CLAUDE.md §13 voorziet auto-
        generatie elke 1e van de maand; voor V1 genereer je ze handmatig
        via de knop hieronder.
      </p>

      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "flex-end",
          margin: "12px 0",
        }}
      >
        <div>
          <label
            style={{ display: "block", fontSize: 11, color: "#6b7280" }}
          >
            Jaar
          </label>
          <input
            data-testid="archive-gen-year"
            type="number"
            value={genYear}
            onChange={(e) => setGenYear(Number(e.target.value))}
            style={{
              width: 100,
              padding: "6px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 6,
            }}
          />
        </div>
        <div>
          <label
            style={{ display: "block", fontSize: 11, color: "#6b7280" }}
          >
            Maand
          </label>
          <select
            data-testid="archive-gen-month"
            value={genMonth}
            onChange={(e) => setGenMonth(Number(e.target.value))}
            style={{
              padding: "6px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 6,
            }}
          >
            {MONTH_LABELS_NL.map((label, idx) => (
              <option key={idx + 1} value={idx + 1}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          data-testid="archive-generate-button"
          onClick={() => generateMut.mutate()}
          disabled={generateMut.isPending}
          style={{
            padding: "8px 14px",
            background: generateMut.isPending ? "#9ca3af" : "#15803d",
            color: "#ffffff",
            border: "none",
            borderRadius: 6,
            fontWeight: 600,
            cursor: generateMut.isPending ? "not-allowed" : "pointer",
            fontSize: 13,
          }}
        >
          {generateMut.isPending ? "Bezig…" : "Genereer PDF"}
        </button>
      </div>
      {error ? (
        <p
          data-testid="archive-error"
          style={{ color: "#b91c1c", fontSize: 12, marginBottom: 8 }}
        >
          {error}
        </p>
      ) : null}

      {items.length === 0 ? (
        <p
          data-testid="archive-empty"
          style={{
            fontStyle: "italic",
            color: "#6b7280",
            fontSize: 13,
          }}
        >
          Nog geen PDFs in het archief — genereer er één hierboven.
        </p>
      ) : (
        <ul
          data-testid="archive-list"
          style={{ margin: 0, padding: 0, listStyle: "none" }}
        >
          {items.map((it) => (
            <li
              key={it.archive_id}
              data-testid={`archive-row-${it.year}-${it.month}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "6px 0",
                borderBottom: "1px solid #f3f4f6",
                fontSize: 13,
              }}
            >
              <span style={{ fontWeight: 600, minWidth: 120 }}>
                {MONTH_LABELS_NL[it.month - 1]} {it.year}
              </span>
              <span style={{ color: "#6b7280", fontSize: 11 }}>
                {Math.round(it.pdf_size_bytes / 1024)} KB · gegenereerd{" "}
                {it.generated_at.slice(0, 10)}
              </span>
              <a
                data-testid={`archive-download-${it.year}-${it.month}`}
                href={apiClient.archivePdfUrl({
                  year: it.year,
                  month: it.month,
                })}
                download
                style={{
                  marginLeft: "auto",
                  padding: "4px 10px",
                  background: "#0f172a",
                  color: "#ffffff",
                  borderRadius: 6,
                  textDecoration: "none",
                  fontWeight: 600,
                  fontSize: 11,
                }}
              >
                Download
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
