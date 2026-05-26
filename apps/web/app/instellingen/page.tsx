"use client";

/**
 * Task 133: Instellingen page.
 *
 * Surfaces the persisted trading settings (allowed universe + user
 * strategy). For Task 133 the only editable field added here is
 * ``user_buffer_eur`` — the EUR headroom subtracted from
 * available_funds when sizing BUY drafts. Other fields (portfolio
 * goal, risk level, sector preferences) live in the same JSON column
 * and can be wired through later UI work; the page currently shows
 * the buffer + a read-only summary of the other user-strategy
 * settings.
 */

import { useCallback, useEffect, useState } from "react";

import {
  apiClient,
  type TradingSettingsResponse,
} from "@/lib/apiClient";

export default function Page() {
  const [data, setData] = useState<TradingSettingsResponse | null>(null);
  const [buffer, setBuffer] = useState<string>("0");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    const result = await apiClient.getTradingSettings();
    setLoading(false);
    if (!result.ok) {
      setError("Instellingen konden niet worden geladen.");
      return;
    }
    setData(result.data);
    const raw = result.data.user_strategy?.user_buffer_eur;
    if (raw !== undefined && raw !== null) {
      setBuffer(String(raw));
    } else {
      setBuffer("0");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleSave() {
    if (data === null) return;
    const numeric = Number(buffer);
    if (Number.isNaN(numeric) || numeric < 0) {
      setError("Cashbuffer moet ≥ 0 zijn.");
      return;
    }
    setSaving(true);
    setError(null);
    setSavedMessage(null);
    const next_user_strategy = {
      ...(data.user_strategy as Record<string, unknown>),
      user_buffer_eur: buffer,
    };
    const result = await apiClient.updateTradingSettings({
      allowed_universe: data.allowed_universe,
      user_strategy: next_user_strategy,
      reason_nl: "Cashbuffer voor actiedrafts aangepast.",
    });
    setSaving(false);
    if (!result.ok) {
      setError("Opslaan mislukt. Controleer of de API beschikbaar is.");
      return;
    }
    setSavedMessage("Instellingen opgeslagen.");
    await refresh();
  }

  return (
    <main className="page-wrap" data-testid="instellingen-page">
      <h2>Instellingen</h2>

      {loading ? (
        <p>Bezig met laden…</p>
      ) : data === null ? (
        <p>Geen instellingen beschikbaar.</p>
      ) : (
        <>
          <section
            style={{
              marginTop: 16,
              padding: 16,
              border: "1px solid #d1d5db",
              borderRadius: 8,
            }}
          >
            <h3 style={{ marginTop: 0 }}>Actie-instellingen</h3>
            <p style={{ color: "#6b7280", fontSize: 13 }}>
              De cashbuffer wordt afgetrokken van je beschikbare cash voordat
              de voorgestelde aankoophoeveelheid wordt berekend. Standaard €0.
            </p>
            <label
              style={{ display: "grid", gap: 4, maxWidth: 320 }}
              htmlFor="user-buffer-eur-input"
            >
              <span style={{ fontWeight: 600, fontSize: 13 }}>
                Cashbuffer (EUR)
              </span>
              <input
                id="user-buffer-eur-input"
                data-testid="instellingen-user-buffer-input"
                type="number"
                min="0"
                step="1"
                value={buffer}
                onChange={(event) => setBuffer(event.target.value)}
              />
            </label>
            <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
              <button
                type="button"
                data-testid="instellingen-save-button"
                onClick={handleSave}
                disabled={saving}
                style={{
                  padding: "8px 16px",
                  background: "#1d4ed8",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: 6,
                  cursor: saving ? "wait" : "pointer",
                  fontWeight: 600,
                }}
              >
                {saving ? "Bezig…" : "Opslaan"}
              </button>
              {savedMessage ? (
                <span
                  data-testid="instellingen-saved-message"
                  style={{
                    alignSelf: "center",
                    color: "#15803d",
                    fontSize: 13,
                  }}
                >
                  {savedMessage}
                </span>
              ) : null}
            </div>
            {error ? (
              <div
                data-testid="instellingen-error"
                style={{
                  marginTop: 12,
                  background: "#fee2e2",
                  color: "#7f1d1d",
                  padding: 8,
                  borderRadius: 4,
                  fontSize: 13,
                }}
              >
                {error}
              </div>
            ) : null}
          </section>
        </>
      )}
    </main>
  );
}
