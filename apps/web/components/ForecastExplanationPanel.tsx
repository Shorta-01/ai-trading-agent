"use client";

/**
 * Task 130: Forecast explanation modal ("Waarom?" panel).
 *
 * Reads ``/forecast/latest?conid=…`` and renders nine locked Dutch
 * fields. Pure presentation: it never calls any other endpoint, and
 * the rendered numbers come straight from the persisted forecast row
 * (Decimal-as-string). Nothing here can originate or alter an order.
 *
 * Locked fields (per the §Q4 forecast-explanation spec):
 *
 * 1. Verwachte richting (label)
 * 2. Kans op stijging (prob_positive)
 * 3. Kans op verlies (>5%) (prob_loss_gt_5pct)
 * 4. Verwachte bandbreedte (p10..p90 in local + EUR)
 * 5. Risico (verwachte volatiliteit) (expected_volatility_annualized)
 * 6. Betrouwbaarheid (confidence_level)
 * 7. Onderbouwing (history + horizon summary)
 * 8. Methode ("Historische bootstrap, 252 dagen, blok-resampling")
 * 9. Geldig tot (forecast_valid_until)
 */

import { useEffect, useState } from "react";

import {
  apiClient,
  ForecastLatestResponse,
} from "@/lib/apiClient";

type Props = {
  readonly conid: string;
  readonly open: boolean;
  readonly onClose: () => void;
};

const METHOD_LABEL_NL = "Historische bootstrap, 252 dagen, blok-resampling";

function pct(value: string): string {
  const num = Number(value);
  if (Number.isNaN(num)) return value;
  return `${(num * 100).toFixed(1)}%`;
}

function fmtDate(iso: string): string {
  // Render as YYYY-MM-DD to avoid locale-driven test flakiness; the
  // exact field is locked + comes straight from the server.
  return iso.slice(0, 10);
}


export function ForecastExplanationPanel({ conid, open, onClose }: Props) {
  const [data, setData] = useState<ForecastLatestResponse | null>(null);
  const [errorReason, setErrorReason] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    let cancelled = false;
    setData(null);
    setErrorReason(null);

    async function load() {
      const result = await apiClient.getForecastLatest(conid);
      if (cancelled) return;
      if (result.ok) {
        setData(result.data);
      } else {
        setErrorReason(result.reason ?? "not_reachable");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [open, conid]);

  if (!open) {
    return null;
  }

  return (
    <div
      data-testid="forecast-explanation-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="forecast-explanation-title"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        data-testid="forecast-explanation-panel"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#ffffff",
          color: "#111827",
          padding: 24,
          borderRadius: 8,
          maxWidth: 560,
          width: "calc(100% - 32px)",
          maxHeight: "calc(100vh - 64px)",
          overflowY: "auto",
          boxShadow: "0 8px 24px rgba(0,0,0,0.2)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 12,
          }}
        >
          <h2
            id="forecast-explanation-title"
            style={{ margin: 0, fontSize: 18, fontWeight: 700 }}
          >
            Waarom deze voorspelling?
          </h2>
          <button
            type="button"
            data-testid="forecast-explanation-close"
            onClick={onClose}
            aria-label="Sluiten"
            style={{
              background: "transparent",
              border: "none",
              fontSize: 20,
              cursor: "pointer",
              color: "#6b7280",
            }}
          >
            ×
          </button>
        </div>

        {errorReason !== null && (
          <p data-testid="forecast-explanation-error" style={{ color: "#b91c1c" }}>
            Voorspelling is op dit moment niet beschikbaar.
          </p>
        )}

        {data === null && errorReason === null && (
          <p data-testid="forecast-explanation-loading">Bezig met laden…</p>
        )}

        {data !== null && (
          <dl
            data-testid="forecast-explanation-fields"
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(160px, 1fr) 2fr",
              gap: "8px 16px",
              margin: 0,
            }}
          >
            <dt style={{ fontWeight: 600 }}>Verwachte richting</dt>
            <dd data-testid="forecast-field-direction" style={{ margin: 0 }}>
              {data.label}
              {data.block_reason !== null && (
                <span style={{ marginLeft: 8, color: "#92400e" }}>
                  ({data.block_reason})
                </span>
              )}
            </dd>

            <dt style={{ fontWeight: 600 }}>Kans op stijging</dt>
            <dd data-testid="forecast-field-prob-positive" style={{ margin: 0 }}>
              {pct(data.prob_positive)}
            </dd>

            <dt style={{ fontWeight: 600 }}>Kans op verlies (&gt;5%)</dt>
            <dd data-testid="forecast-field-prob-loss" style={{ margin: 0 }}>
              {pct(data.prob_loss_gt_5pct)}
            </dd>

            <dt style={{ fontWeight: 600 }}>Verwachte bandbreedte</dt>
            <dd data-testid="forecast-field-band" style={{ margin: 0 }}>
              {data.p10_price_local} – {data.p90_price_local} {data.currency_local}
              {data.p10_price_eur !== null && data.p90_price_eur !== null && data.currency_local !== "EUR" && (
                <span style={{ marginLeft: 6, color: "#6b7280" }}>
                  ({data.p10_price_eur} – {data.p90_price_eur} EUR)
                </span>
              )}
            </dd>

            <dt style={{ fontWeight: 600 }}>Risico (verwachte volatiliteit)</dt>
            <dd data-testid="forecast-field-volatility" style={{ margin: 0 }}>
              {pct(data.expected_volatility_annualized)} per jaar
            </dd>

            <dt style={{ fontWeight: 600 }}>Betrouwbaarheid</dt>
            <dd data-testid="forecast-field-confidence" style={{ margin: 0 }}>
              {data.confidence_level}
            </dd>

            <dt style={{ fontWeight: 600 }}>Onderbouwing</dt>
            <dd data-testid="forecast-field-rationale" style={{ margin: 0 }}>
              Gebaseerd op {data.horizon_trading_days} handelsdagen vooruit; mediaan log-rendement{" "}
              {data.p50_log_return}.
            </dd>

            <dt style={{ fontWeight: 600 }}>Methode</dt>
            <dd data-testid="forecast-field-method" style={{ margin: 0 }}>
              {METHOD_LABEL_NL}
            </dd>

            <dt style={{ fontWeight: 600 }}>Geldig tot</dt>
            <dd data-testid="forecast-field-valid-until" style={{ margin: 0 }}>
              {fmtDate(data.forecast_valid_until)}
            </dd>
          </dl>
        )}

        <p
          style={{
            marginTop: 16,
            fontSize: 12,
            color: "#6b7280",
          }}
        >
          Informatief — geen handelsadvies. Orders worden alleen na expliciete
          bevestiging in de approval-gate ingelegd.
        </p>
      </div>
    </div>
  );
}
