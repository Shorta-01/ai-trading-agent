"use client";

/**
 * Task 132: Decision Package detail view.
 *
 * Renders the seven locked Dutch sections defined in the brief.
 * Pure presentational — receives a fully-formed
 * ``DecisionPackageResponse`` from the parent (page or test). The
 * audit hash truncates by default; clicking expands it. All values
 * come straight from the API — no client-side rendering of forecast
 * math, no client-side translation.
 */

import { useState } from "react";

import type {
  DecisionPackageResponse,
  ForecastConfidenceLevel,
} from "@/lib/apiClient";

const LABEL_COLOR: Record<
  DecisionPackageResponse["suggested_action_label"],
  { bg: string; fg: string }
> = {
  Kopen: { bg: "#dcfce7", fg: "#166534" },
  Verminderen: { bg: "#fed7aa", fg: "#9a3412" },
  Verkopen: { bg: "#fecaca", fg: "#7f1d1d" },
  Houden: { bg: "#dbeafe", fg: "#1e3a8a" },
  Bekijken: { bg: "#fef3c7", fg: "#854d0e" },
};

const CONFIDENCE_LABEL: Record<ForecastConfidenceLevel, string> = {
  Hoog: "Hoog",
  Gemiddeld: "Gemiddeld",
  Laag: "Laag",
};

const FRESHNESS_LABEL: Record<
  DecisionPackageResponse["freshness_state"],
  string
> = {
  fresh: "Vers",
  stale: "Verouderd",
  unavailable: "Niet beschikbaar",
};

function fmtTs(value: string): string {
  // The API returns ISO 8601 already; just slice the wall-time without
  // converting to local TZ — the package is timezone-aware (UTC) and
  // surfacing it as UTC keeps the audit chain readable.
  return value.replace("T", " ").replace(/\+00:00$/, " UTC");
}

function fmtEUR(value: string): string {
  // Keep two decimals; the wire string is the column-precision form
  // (e.g. "640.12345600"). Don't reformat money beyond rounding —
  // doctrine: never re-render financial numbers on the client.
  return `€${Number(value).toFixed(2).replace(".", ",")}`;
}

function fmtPct(value: string, decimals = 0): string {
  const pct = Number(value) * 100;
  return `${pct.toFixed(decimals).replace(".", ",")}%`;
}


export function DecisionPackageDetail({
  package: pkg,
}: {
  package: DecisionPackageResponse;
}) {
  const [hashExpanded, setHashExpanded] = useState(false);
  const labelColor = LABEL_COLOR[pkg.suggested_action_label];
  const shortHash = pkg.audit_trail_hash.slice(0, 12);

  return (
    <article
      data-testid="decision-package-detail"
      style={{ maxWidth: 900, margin: "0 auto", padding: 24 }}
    >
      {/* 1. Header */}
      <header
        data-testid="dp-section-header"
        style={{
          borderBottom: "1px solid #e5e7eb",
          paddingBottom: 12,
          marginBottom: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h1 style={{ margin: 0, fontSize: 22 }}>{pkg.symbol}</h1>
          <span
            data-testid="dp-label-badge"
            style={{
              background: labelColor.bg,
              color: labelColor.fg,
              padding: "4px 12px",
              borderRadius: 999,
              fontSize: 14,
              fontWeight: 700,
            }}
          >
            {pkg.suggested_action_label}
          </span>
          <span
            data-testid="dp-confidence-badge"
            style={{
              color: "#374151",
              fontSize: 13,
              padding: "2px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 4,
            }}
          >
            Betrouwbaarheid: {CONFIDENCE_LABEL[pkg.forecast_confidence_level]}
          </span>
        </div>
        <p
          data-testid="dp-header-timing"
          style={{ margin: "8px 0 0", fontSize: 12, color: "#6b7280" }}
        >
          Samengesteld op {fmtTs(pkg.composed_at)} — geldig tot{" "}
          {fmtTs(pkg.valid_until)}
        </p>
      </header>

      {/* 2. Voorspelling */}
      <section
        data-testid="dp-section-forecast"
        style={{ marginBottom: 24 }}
      >
        <h2 style={{ fontSize: 16, margin: "0 0 8px" }}>Voorspelling</h2>
        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "max-content 1fr",
            gap: "4px 16px",
            margin: 0,
            fontSize: 14,
          }}
        >
          <dt style={{ fontWeight: 600 }}>Bandbreedte (EUR)</dt>
          <dd
            data-testid="dp-field-band"
            style={{ margin: 0 }}
          >
            {fmtEUR(pkg.p10_price_eur)} (p10) — {fmtEUR(pkg.p50_price_eur)}{" "}
            (mediaan) — {fmtEUR(pkg.p90_price_eur)} (p90)
          </dd>
          <dt style={{ fontWeight: 600 }}>Kans op stijging</dt>
          <dd
            data-testid="dp-field-prob-positive"
            style={{ margin: 0 }}
          >
            {fmtPct(pkg.prob_positive)}
          </dd>
          <dt style={{ fontWeight: 600 }}>Kans op verlies (&gt;5%)</dt>
          <dd
            data-testid="dp-field-prob-loss"
            style={{ margin: 0 }}
          >
            {fmtPct(pkg.prob_loss_gt_5pct)}
          </dd>
          <dt style={{ fontWeight: 600 }}>Verwachte volatiliteit</dt>
          <dd
            data-testid="dp-field-volatility"
            style={{ margin: 0 }}
          >
            {fmtPct(pkg.expected_volatility_annualized, 1)} per jaar
          </dd>
        </dl>
      </section>

      {/* 3. Huidige situatie */}
      <section
        data-testid="dp-section-current"
        style={{ marginBottom: 24 }}
      >
        <h2 style={{ fontSize: 16, margin: "0 0 8px" }}>Huidige situatie</h2>
        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "max-content 1fr",
            gap: "4px 16px",
            margin: 0,
            fontSize: 14,
          }}
        >
          <dt style={{ fontWeight: 600 }}>Huidige prijs</dt>
          <dd
            data-testid="dp-field-current-price"
            style={{ margin: 0 }}
          >
            {pkg.current_price_local} {pkg.currency_local} (
            {fmtEUR(pkg.current_price_eur)})
          </dd>
          <dt style={{ fontWeight: 600 }}>Marktdata</dt>
          <dd
            data-testid="dp-field-freshness"
            style={{ margin: 0 }}
          >
            {FRESHNESS_LABEL[pkg.freshness_state]} —{" "}
            {pkg.data_age_trading_days} dagen oud
          </dd>
          <dt style={{ fontWeight: 600 }}>Positie</dt>
          <dd data-testid="dp-field-position" style={{ margin: 0 }}>
            {pkg.user_holds_position && pkg.held_quantity !== null
              ? `${pkg.held_quantity} stuks (gemiddelde kostprijs: ${pkg.held_avg_cost_local} ${pkg.currency_local})`
              : "Niet in portefeuille."}
          </dd>
        </dl>
      </section>

      {/* 4. Gate-uitkomsten */}
      <section data-testid="dp-section-gates" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, margin: "0 0 8px" }}>Gate-uitkomsten</h2>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 13,
          }}
        >
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: 6 }}>Gate</th>
              <th style={{ textAlign: "left", padding: 6 }}>Status</th>
              <th style={{ textAlign: "left", padding: 6 }}>Reden</th>
            </tr>
          </thead>
          <tbody>
            {pkg.gate_outcomes.map((gate) => (
              <tr
                key={gate.gate_name}
                data-testid={`dp-gate-row-${gate.gate_name}`}
                style={{ borderTop: "1px solid #f3f4f6" }}
              >
                <td style={{ padding: 6 }}>{gate.gate_name}</td>
                <td
                  style={{
                    padding: 6,
                    color: gate.passed ? "#166534" : "#7f1d1d",
                    fontWeight: 600,
                  }}
                >
                  {gate.passed ? "Geslaagd" : "Gefaald"}
                </td>
                <td style={{ padding: 6, color: "#6b7280" }}>
                  {gate.reason_nl || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* 5. Bewijsbronnen */}
      <section
        data-testid="dp-section-evidence"
        style={{ marginBottom: 24 }}
      >
        <h2 style={{ fontSize: 16, margin: "0 0 8px" }}>Bewijsbronnen</h2>
        <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13 }}>
          {pkg.evidence_references.map((ev) => (
            <li
              key={ev.source_id}
              data-testid={`dp-evidence-${ev.source_type}`}
            >
              <strong>{ev.source_type}:</strong> {ev.claim_summary}
            </li>
          ))}
        </ul>
      </section>

      {/* 6. Onderbouwing */}
      <section
        data-testid="dp-section-explanation"
        style={{ marginBottom: 24 }}
      >
        <h2 style={{ fontSize: 16, margin: "0 0 8px" }}>Onderbouwing</h2>
        <p
          data-testid="dp-explanation-text"
          style={{
            margin: 0,
            fontSize: 14,
            lineHeight: 1.5,
            color: "#1f2937",
          }}
        >
          {pkg.deterministic_dutch_explanation}
        </p>
      </section>

      {/* 7. Audit */}
      <section data-testid="dp-section-audit">
        <h2 style={{ fontSize: 16, margin: "0 0 8px" }}>Audit</h2>
        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "max-content 1fr",
            gap: "4px 16px",
            margin: 0,
            fontSize: 13,
          }}
        >
          <dt style={{ fontWeight: 600 }}>Samengesteld op</dt>
          <dd style={{ margin: 0 }}>{fmtTs(pkg.composed_at)}</dd>
          <dt style={{ fontWeight: 600 }}>Audit-hash</dt>
          <dd
            data-testid="dp-audit-hash"
            style={{
              margin: 0,
              fontFamily: "monospace",
              wordBreak: "break-all",
            }}
          >
            {hashExpanded ? pkg.audit_trail_hash : `${shortHash}…`}{" "}
            <button
              type="button"
              data-testid="dp-audit-hash-toggle"
              onClick={() => setHashExpanded((v) => !v)}
              style={{
                fontSize: 11,
                marginLeft: 4,
                cursor: "pointer",
              }}
            >
              {hashExpanded ? "Inkorten" : "Toon volledig"}
            </button>
          </dd>
          {pkg.previous_package_hash !== null ? (
            <>
              <dt style={{ fontWeight: 600 }}>Vorige package</dt>
              <dd
                data-testid="dp-previous-hash"
                style={{
                  margin: 0,
                  fontFamily: "monospace",
                  wordBreak: "break-all",
                  color: "#6b7280",
                  fontSize: 11,
                }}
              >
                {pkg.previous_package_hash.slice(0, 12)}…
              </dd>
            </>
          ) : (
            <>
              <dt style={{ fontWeight: 600 }}>Vorige package</dt>
              <dd
                data-testid="dp-previous-hash-none"
                style={{ margin: 0, color: "#6b7280" }}
              >
                Eerste Decision Package voor dit asset.
              </dd>
            </>
          )}
        </dl>
      </section>
    </article>
  );
}
