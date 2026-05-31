/**
 * V1 Suggesties grid — the daily TODO screen the operator opens at 7am.
 *
 * Renders the response from ``GET /suggestions/grid``: sections in
 * locked safety order (Verkopen first, Geblokkeerd last), each row
 * showing label badge + confidence + top driver + NIEUW/Gewijzigd diff
 * tag + click-to-expand details + link to the Decision Package.
 *
 * The page never auto-promotes anything. Suggestions are
 * advice-grade; the operator clicks through to a Decision Package to
 * trigger any actual action.
 */

"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { useQuery } from "@tanstack/react-query";

import { apiClient, type SuggestionsGridItem } from "@/lib/apiClient";

const SUGGESTIONS_GRID_KEY = ["suggesties", "grid"] as const;

const GRID_QUERY_OPTIONS = {
  staleTime: 60_000, // 1 min — page is refreshed manually
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
} as const;

// Color tokens per action label. The Dutch label is the lookup key so
// the API can change the English code without breaking the palette.
const LABEL_PALETTE: Record<
  string,
  { background: string; border: string; text: string }
> = {
  Verkopen: { background: "#fee2e2", border: "#fca5a5", text: "#991b1b" },
  Verminderen: { background: "#fed7aa", border: "#fdba74", text: "#9a3412" },
  Kopen: { background: "#dcfce7", border: "#86efac", text: "#15803d" },
  "Langzaam bijkopen": {
    background: "#d1fae5",
    border: "#6ee7b7",
    text: "#047857",
  },
  Houden: { background: "#e0f2fe", border: "#7dd3fc", text: "#075985" },
  Bekijken: { background: "#fef3c7", border: "#fcd34d", text: "#92400e" },
  "Cash houden": { background: "#f3f4f6", border: "#d1d5db", text: "#374151" },
  "Geen actie": { background: "#f3f4f6", border: "#d1d5db", text: "#6b7280" },
  Vermijden: { background: "#fce7f3", border: "#f9a8d4", text: "#9d174d" },
  Geblokkeerd: { background: "#e5e7eb", border: "#9ca3af", text: "#374151" },
};

const NEUTRAL_PALETTE = {
  background: "#f3f4f6",
  border: "#d1d5db",
  text: "#374151",
};

const CONFIDENCE_PALETTE: Record<string, string> = {
  Hoog: "#15803d",
  Middel: "#a16207",
  Laag: "#9ca3af",
};

function paletteFor(label: string) {
  return LABEL_PALETTE[label] ?? NEUTRAL_PALETTE;
}

function formatExpiresIn(minutes: number): string {
  if (minutes < 0) return "Verlopen";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}u`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

function downloadCsv(filename: string, rows: string[][]) {
  const csv = rows
    .map((row) =>
      row
        .map((cell) => {
          if (cell == null) return "";
          const escaped = String(cell).replace(/"/g, '""');
          return `"${escaped}"`;
        })
        .join(","),
    )
    .join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

type DiffFilter = "all" | "nieuw" | "gewijzigd";
type ConfidenceFilter = "all" | "Hoog" | "Middel" | "Laag";

const SECTION_STYLE: React.CSSProperties = {
  border: "1px solid #e5e7eb",
  borderRadius: 8,
  padding: 16,
  marginTop: 16,
  background: "#ffffff",
};

const HEADER_BTN_STYLE: React.CSSProperties = {
  background: "transparent",
  border: "none",
  cursor: "pointer",
  fontSize: 18,
  fontWeight: 600,
  display: "flex",
  alignItems: "center",
  gap: 8,
  padding: 0,
  color: "#111827",
};

function DiffBadge({ diff }: { diff: SuggestionsGridItem["diff_status"] }) {
  if (diff === "nieuw") {
    return (
      <span
        data-testid="suggesties-row-badge-nieuw"
        style={{
          background: "#15803d",
          color: "#ffffff",
          fontSize: 11,
          padding: "2px 8px",
          borderRadius: 999,
          fontWeight: 600,
        }}
      >
        NIEUW
      </span>
    );
  }
  if (diff === "gewijzigd") {
    return (
      <span
        data-testid="suggesties-row-badge-gewijzigd"
        style={{
          background: "#a16207",
          color: "#ffffff",
          fontSize: 11,
          padding: "2px 8px",
          borderRadius: 999,
          fontWeight: 600,
        }}
      >
        GEWIJZIGD
      </span>
    );
  }
  return null;
}

function ConfidenceBadge({
  label,
  score,
}: {
  label: string;
  score: string;
}) {
  const color = CONFIDENCE_PALETTE[label] ?? "#6b7280";
  return (
    <span
      title={`Score: ${score}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        color,
        fontWeight: 600,
        fontSize: 13,
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 8,
          height: 8,
          borderRadius: 999,
          background: color,
          display: "inline-block",
        }}
      />
      {label}
    </span>
  );
}

function LabelBadge({ label }: { label: string }) {
  const palette = paletteFor(label);
  return (
    <span
      data-testid="suggesties-row-label-badge"
      style={{
        background: palette.background,
        border: `1px solid ${palette.border}`,
        color: palette.text,
        fontSize: 13,
        fontWeight: 600,
        padding: "3px 10px",
        borderRadius: 6,
        display: "inline-block",
      }}
    >
      {label}
    </span>
  );
}

function Row({ item }: { item: SuggestionsGridItem }) {
  const [open, setOpen] = useState(false);
  const expiresIn = formatExpiresIn(item.valid_until_age_minutes);
  const expectedReturn =
    item.expected_return_pct != null
      ? `${Number(item.expected_return_pct).toFixed(2)}%`
      : "—";
  const probGain =
    item.prob_gain_pct != null
      ? `${Number(item.prob_gain_pct).toFixed(0)}%`
      : "—";

  return (
    <li
      data-testid={`suggesties-row-${item.symbol}`}
      style={{
        listStyle: "none",
        borderTop: "1px solid #f3f4f6",
        padding: "12px 0",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "120px 1fr 110px 110px 100px 80px auto",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <strong style={{ fontSize: 15 }}>{item.symbol}</strong>
          <DiffBadge diff={item.diff_status} />
        </div>
        <div>
          <LabelBadge label={item.action_label_nl} />
          {item.top_driver_nl ? (
            <div
              data-testid="suggesties-row-top-driver"
              style={{
                fontSize: 13,
                color: "#374151",
                marginTop: 4,
              }}
            >
              {item.top_driver_nl}
            </div>
          ) : null}
        </div>
        <ConfidenceBadge
          label={item.confidence_label_nl}
          score={item.confidence_score}
        />
        <span style={{ fontSize: 13, color: "#111827" }}>
          {expectedReturn}
        </span>
        <span style={{ fontSize: 13, color: "#111827" }}>{probGain}</span>
        <span style={{ fontSize: 12, color: "#6b7280" }} title={item.valid_until}>
          {expiresIn}
        </span>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            data-testid={`suggesties-row-toggle-${item.symbol}`}
            aria-expanded={open}
            style={{
              border: "1px solid #d1d5db",
              background: "#ffffff",
              color: "#374151",
              borderRadius: 4,
              padding: "4px 10px",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            {open ? "Verberg" : "Details"}
          </button>
          {item.forecast_id ? (
            <Link
              href={`/decision-package/${encodeURIComponent(item.forecast_id)}`}
              data-testid={`suggesties-row-decision-package-${item.symbol}`}
              style={{
                border: "1px solid #1f2937",
                background: "#1f2937",
                color: "#ffffff",
                borderRadius: 4,
                padding: "4px 10px",
                fontSize: 12,
                textDecoration: "none",
              }}
            >
              Bekijk Decision Package
            </Link>
          ) : null}
        </div>
      </div>
      {open ? (
        <div
          data-testid={`suggesties-row-details-${item.symbol}`}
          style={{
            marginTop: 12,
            padding: 12,
            background: "#f9fafb",
            borderRadius: 6,
            fontSize: 13,
            color: "#374151",
            lineHeight: 1.5,
          }}
        >
          <div>
            <strong>Volledige redenering:</strong> {item.rationale_nl}
          </div>
          {item.branch_reason_nl ? (
            <div style={{ marginTop: 6 }}>
              <strong>Beslissingstak:</strong> {item.branch_reason_nl}
            </div>
          ) : null}
          {item.downgrade_reason_nl ? (
            <div style={{ marginTop: 6, color: "#92400e" }}>
              <strong>Afschaling:</strong> {item.downgrade_reason_nl}
            </div>
          ) : null}
          {item.blocking_reason_nl ? (
            <div style={{ marginTop: 6, color: "#9d174d" }}>
              <strong>Reden geen advies:</strong> {item.blocking_reason_nl}
            </div>
          ) : null}
          {item.previous_action_label_nl ? (
            <div style={{ marginTop: 6 }}>
              <strong>Gisteren:</strong> {item.previous_action_label_nl} →
              vandaag {item.action_label_nl}
            </div>
          ) : null}
          {item.drivers.length > 0 ? (
            <div style={{ marginTop: 6 }}>
              <strong>Drivers:</strong>{" "}
              <span style={{ fontFamily: "monospace", fontSize: 12 }}>
                {item.drivers.join(" · ")}
              </span>
            </div>
          ) : null}
          {item.blockers.length > 0 ? (
            <div style={{ marginTop: 6 }}>
              <strong>Blockers:</strong> {item.blockers.join(", ")}
            </div>
          ) : null}
          <div style={{ marginTop: 6, color: "#6b7280", fontSize: 12 }}>
            Gegenereerd:{" "}
            {new Date(item.generated_at).toLocaleString("nl-BE")} · Geldig tot:{" "}
            {new Date(item.valid_until).toLocaleString("nl-BE")} ·{" "}
            Risico-profiel: {item.risk_profile} ·{" "}
            {item.has_position ? "In bezit" : "Niet in bezit"}
          </div>
        </div>
      ) : null}
    </li>
  );
}

const LAST_VISIT_STORAGE_KEY = "suggesties:lastVisitAt";

export default function Page() {
  const [diffFilter, setDiffFilter] = useState<DiffFilter>("all");
  const [confidenceFilter, setConfidenceFilter] =
    useState<ConfidenceFilter>("all");
  // Tracks the timestamp the operator last visited this page (read at
  // mount, then updated on the way out). Used to compute the
  // "X nieuw sinds je vorige bezoek" badge so the operator can tell at
  // a glance whether anything changed without scrolling the grid.
  const [lastVisitAt, setLastVisitAt] = useState<number | null>(null);

  const query = useQuery({
    queryKey: SUGGESTIONS_GRID_KEY,
    queryFn: async () => {
      const result = await apiClient.getSuggestionsGrid();
      if (!result.ok) throw new Error("suggestions-grid-unavailable");
      return result.data;
    },
    ...GRID_QUERY_OPTIONS,
  });

  useEffect(() => {
    // Read the previous visit BEFORE writing the new one so the badge
    // can compare grid timestamps against the prior visit window.
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem(LAST_VISIT_STORAGE_KEY);
      const prev = raw ? Number(raw) : null;
      if (prev != null && Number.isFinite(prev)) {
        setLastVisitAt(prev);
      }
      window.localStorage.setItem(
        LAST_VISIT_STORAGE_KEY,
        String(Date.now()),
      );
    } catch {
      // Storage unavailable (e.g. Safari private mode) — silently
      // degrade; the badge just won't render.
    }
  }, []);

  // Count suggestions whose generated_at is newer than the prior visit.
  const sinceLastVisitCount = useMemo(() => {
    if (lastVisitAt == null || !query.data) return 0;
    let count = 0;
    for (const section of query.data.sections) {
      for (const item of section.items) {
        const generatedMs = Date.parse(item.generated_at);
        if (Number.isFinite(generatedMs) && generatedMs > lastVisitAt) {
          count += 1;
        }
      }
    }
    return count;
  }, [lastVisitAt, query.data]);

  const filteredSections = useMemo(() => {
    if (!query.data) return [];
    return query.data.sections
      .map((section) => ({
        ...section,
        items: section.items.filter((item) => {
          if (diffFilter !== "all" && item.diff_status !== diffFilter)
            return false;
          if (
            confidenceFilter !== "all" &&
            item.confidence_label_nl !== confidenceFilter
          )
            return false;
          return true;
        }),
      }))
      .filter((section) => section.items.length > 0);
  }, [query.data, diffFilter, confidenceFilter]);

  function handleExport() {
    if (!query.data) return;
    const header = [
      "symbool",
      "actie",
      "betrouwbaarheid",
      "verwacht_rendement_pct",
      "kans_op_winst_pct",
      "diff_status",
      "voorlaatste_actie",
      "top_driver",
      "redenering",
      "geldig_tot",
    ];
    const rows: string[][] = [header];
    for (const section of query.data.sections) {
      for (const item of section.items) {
        rows.push([
          item.symbol,
          item.action_label_nl,
          item.confidence_label_nl,
          item.expected_return_pct ?? "",
          item.prob_gain_pct ?? "",
          item.diff_status,
          item.previous_action_label_nl ?? "",
          item.top_driver_nl ?? "",
          item.rationale_nl,
          item.valid_until,
        ]);
      }
    }
    const today = new Date().toISOString().slice(0, 10);
    downloadCsv(`suggesties-${today}.csv`, rows);
  }

  if (query.isPending) {
    return (
      <main className="page-wrap" data-testid="suggesties-page">
        <h2>Suggesties — vandaag</h2>
        <p data-testid="suggesties-loading">Laden...</p>
      </main>
    );
  }

  if (query.isError || !query.data) {
    return (
      <main className="page-wrap" data-testid="suggesties-page">
        <h2>Suggesties — vandaag</h2>
        <p data-testid="suggesties-error" style={{ color: "#b91c1c" }}>
          Suggesties konden niet worden opgehaald. Controleer de
          opslag-verbinding en probeer opnieuw.
        </p>
      </main>
    );
  }

  const data = query.data;
  const isEmpty = data.sections.length === 0;

  return (
    <main className="page-wrap" data-testid="suggesties-page">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 12,
        }}
      >
        <div>
          <h2 style={{ margin: 0 }}>Suggesties — vandaag</h2>
          <p
            data-testid="suggesties-status"
            style={{ marginTop: 4, color: "#374151", fontSize: 13 }}
          >
            {data.status_nl}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            type="button"
            onClick={() => void query.refetch()}
            data-testid="suggesties-refresh"
            style={{
              border: "1px solid #d1d5db",
              background: "#ffffff",
              color: "#374151",
              borderRadius: 4,
              padding: "6px 12px",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            Vernieuwen
          </button>
          <button
            type="button"
            onClick={handleExport}
            disabled={isEmpty}
            data-testid="suggesties-export-csv"
            style={{
              border: "1px solid #1f2937",
              background: isEmpty ? "#9ca3af" : "#1f2937",
              color: "#ffffff",
              borderRadius: 4,
              padding: "6px 12px",
              fontSize: 13,
              cursor: isEmpty ? "not-allowed" : "pointer",
            }}
          >
            Export CSV
          </button>
        </div>
      </div>

      <p
        style={{
          marginTop: 8,
          color: "#6b7280",
          fontSize: 13,
          lineHeight: 1.5,
        }}
      >
        {data.help_nl}
      </p>

      {data.generated_at ? (
        <div
          data-testid="suggesties-meta"
          style={{
            marginTop: 12,
            display: "flex",
            gap: 16,
            fontSize: 13,
            color: "#374151",
            flexWrap: "wrap",
          }}
        >
          <span>
            <strong>Gegenereerd:</strong>{" "}
            {new Date(data.generated_at).toLocaleString("nl-BE")}
          </span>
          <span>
            <strong>Totaal:</strong> {data.total_item_count} suggesties
          </span>
          <span style={{ color: "#15803d" }}>
            <strong>Nieuw:</strong> {data.new_count}
          </span>
          <span style={{ color: "#a16207" }}>
            <strong>Gewijzigd:</strong> {data.changed_count}
          </span>
          {lastVisitAt != null && sinceLastVisitCount > 0 ? (
            <span
              data-testid="suggesties-since-last-visit"
              style={{
                background: "#1f2937",
                color: "#ffffff",
                padding: "2px 10px",
                borderRadius: 999,
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              {sinceLastVisitCount} nieuw sinds je vorige bezoek
            </span>
          ) : null}
          <span>
            <strong>Risico-profiel:</strong> {data.risk_profile}
          </span>
        </div>
      ) : null}

      {!isEmpty ? (
        <div
          style={{
            marginTop: 16,
            display: "flex",
            gap: 12,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <label style={{ fontSize: 13, color: "#374151" }}>
            Filter wijzigingen:{" "}
            <select
              value={diffFilter}
              onChange={(e) => setDiffFilter(e.target.value as DiffFilter)}
              data-testid="suggesties-filter-diff"
              style={{ marginLeft: 4 }}
            >
              <option value="all">Alle</option>
              <option value="nieuw">Alleen nieuw</option>
              <option value="gewijzigd">Alleen gewijzigd</option>
            </select>
          </label>
          <label style={{ fontSize: 13, color: "#374151" }}>
            Filter betrouwbaarheid:{" "}
            <select
              value={confidenceFilter}
              onChange={(e) =>
                setConfidenceFilter(e.target.value as ConfidenceFilter)
              }
              data-testid="suggesties-filter-confidence"
              style={{ marginLeft: 4 }}
            >
              <option value="all">Alle</option>
              <option value="Hoog">Hoog</option>
              <option value="Middel">Middel</option>
              <option value="Laag">Laag</option>
            </select>
          </label>
        </div>
      ) : null}

      {isEmpty ? (
        <section style={SECTION_STYLE} data-testid="suggesties-empty">
          <p style={{ margin: 0, color: "#374151" }}>
            Geen suggesties beschikbaar. {data.status_nl}. De grid wordt
            morgenochtend om 07:00 ververst.
          </p>
        </section>
      ) : filteredSections.length === 0 ? (
        <section style={SECTION_STYLE} data-testid="suggesties-no-matches">
          <p style={{ margin: 0, color: "#374151" }}>
            Geen suggesties matchen de huidige filter. Pas de filter aan
            om resultaten te zien.
          </p>
        </section>
      ) : (
        filteredSections.map((section) => (
          <SectionView
            key={section.action_label_nl}
            section={section}
            initiallyOpen={
              section.action_label_nl === "Verkopen" ||
              section.action_label_nl === "Verminderen" ||
              section.action_label_nl === "Kopen"
            }
          />
        ))
      )}
    </main>
  );
}

function SectionView({
  section,
  initiallyOpen,
}: {
  section: { action_label_nl: string; section_title_nl: string; items: SuggestionsGridItem[] };
  initiallyOpen: boolean;
}) {
  const [open, setOpen] = useState(initiallyOpen);
  const palette = paletteFor(section.action_label_nl);
  return (
    <section
      style={{
        ...SECTION_STYLE,
        borderLeft: `4px solid ${palette.border}`,
      }}
      data-testid={`suggesties-section-${section.action_label_nl}`}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        data-testid={`suggesties-section-toggle-${section.action_label_nl}`}
        style={{
          ...HEADER_BTN_STYLE,
          color: palette.text,
        }}
      >
        <span aria-hidden="true">{open ? "▼" : "▶"}</span>
        {section.section_title_nl}{" "}
        <span
          style={{
            fontWeight: 500,
            fontSize: 14,
            color: "#6b7280",
            marginLeft: 6,
          }}
        >
          ({section.items.length})
        </span>
      </button>
      {open ? (
        <ul style={{ marginTop: 12, padding: 0 }}>
          {section.items.map((item) => (
            <Row key={item.suggestion_id} item={item} />
          ))}
        </ul>
      ) : null}
    </section>
  );
}
