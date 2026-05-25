"use client";

/**
 * Task 128: cold-start confirmation flow for the Volglijst page.
 *
 * Rendered by ``app/volglijst/page.tsx`` when
 * ``/watchlist/confirmation-state`` reports ``state="unconfirmed"``.
 * Shows the yellow info card, the seeded starter rows with
 * ``Verwijder`` buttons, the "+ Asset toevoegen" link (to the
 * existing contract-picker), and the BEVESTIG confirmation block at
 * the bottom.
 *
 * The locked confirmation phrase is the uppercase Dutch word
 * ``BEVESTIG``. Lowercase / other input → server returns HTTP 400
 * with a Dutch detail; we surface it inline.
 */

import { useEffect, useState } from "react";

import {
  apiClient,
  ColdStartWatchlistItem,
} from "@/lib/apiClient";


type Props = {
  /** Callback fired after the user confirms — the parent reloads
   *  state and switches to the normal Volglijst view. */
  readonly onConfirmed: () => void;
};


export function VolglijstColdStartFlow({ onConfirmed }: Props) {
  const [items, setItems] = useState<ColdStartWatchlistItem[]>([]);
  const [phrase, setPhrase] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const result = await apiClient.getColdStartWatchlistItems();
      if (cancelled) return;
      if (result.ok) {
        setItems(result.data.items);
      }
      setLoaded(true);
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleArchive(watchlistItemId: string) {
    setError(null);
    const result = await apiClient.deleteColdStartWatchlistItem(
      watchlistItemId,
    );
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setItems((prev) =>
      prev.filter((row) => row.watchlist_item_id !== watchlistItemId),
    );
  }

  async function handleConfirm() {
    setError(null);
    setSubmitting(true);
    try {
      const result = await apiClient.confirmWatchlist(phrase);
      if (!result.ok) {
        setError(result.message);
        return;
      }
      onConfirmed();
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmit = items.length > 0 && phrase.trim().length > 0;

  return (
    <main className="page-wrap" data-testid="volglijst-cold-start-flow">
      <section
        className="dashboard-panel"
        data-testid="cold-start-info-card"
        style={{
          background: "#fef3c7",
          border: "1px solid #fbbf24",
          padding: "12px 16px",
          marginBottom: "1rem",
          color: "#92400e",
        }}
      >
        <strong>Startvoorstel.</strong> Verwijder of voeg toe wat je
        wilt. Klik op &ldquo;Volglijst bevestigen&rdquo; wanneer je
        tevreden bent.
      </section>

      <section className="dashboard-panel">
        <div className="panel-head">
          <h2>Volglijst-startvoorstel</h2>
        </div>
        <div className="panel-body">
          {!loaded ? (
            <p>Bezig met laden…</p>
          ) : items.length === 0 ? (
            <p data-testid="cold-start-empty-list">
              Geen items in het startvoorstel.
            </p>
          ) : (
            <ul
              data-testid="cold-start-items"
              style={{ listStyle: "none", padding: 0, margin: 0 }}
            >
              {items.map((row) => (
                <li
                  key={row.watchlist_item_id}
                  data-testid={`cold-start-row-${row.symbol}`}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "8px 0",
                    borderBottom: "1px solid #e5e7eb",
                  }}
                >
                  <span>
                    <strong>{row.symbol}</strong>
                    {row.name ? ` — ${row.name}` : ""}
                    {row.exchange ? ` (${row.exchange})` : ""}
                  </span>
                  <button
                    type="button"
                    data-testid={`cold-start-verwijder-${row.symbol}`}
                    onClick={() => handleArchive(row.watchlist_item_id)}
                    style={{
                      background: "transparent",
                      border: "1px solid #6b7280",
                      color: "#1f2937",
                      padding: "4px 10px",
                      borderRadius: 4,
                      cursor: "pointer",
                    }}
                  >
                    Verwijder
                  </button>
                </li>
              ))}
            </ul>
          )}

          <p style={{ marginTop: "1rem" }}>
            <a href="#manual-add" data-testid="cold-start-add-link">
              + Asset toevoegen
            </a>
          </p>
        </div>
      </section>

      <section
        className="dashboard-panel"
        data-testid="cold-start-confirm-block"
        style={{ marginTop: "1rem" }}
      >
        <div className="panel-head">
          <h2>Bevestig je Volglijst</h2>
        </div>
        <div className="panel-body">
          <p>
            Typ het woord <code>BEVESTIG</code> (in hoofdletters) om te
            bevestigen. Daarna start het systeem met geplande runs.
          </p>
          <input
            type="text"
            value={phrase}
            data-testid="cold-start-phrase-input"
            onChange={(e) => setPhrase(e.target.value)}
            placeholder="BEVESTIG"
            style={{
              padding: "8px 10px",
              border: "1px solid #d1d5db",
              borderRadius: 4,
              fontSize: 14,
              fontFamily: "monospace",
              marginRight: 12,
              minWidth: 200,
            }}
            aria-label="Bevestigingsfrase"
          />
          <button
            type="button"
            disabled={!canSubmit || submitting}
            data-testid="cold-start-confirm-button"
            onClick={() => void handleConfirm()}
            style={{
              padding: "8px 14px",
              border: "none",
              borderRadius: 4,
              background: canSubmit ? "#15803d" : "#9ca3af",
              color: "#ffffff",
              fontWeight: 600,
              cursor: canSubmit ? "pointer" : "not-allowed",
            }}
          >
            {submitting ? "Bezig met bevestigen…" : "Volglijst bevestigen"}
          </button>
          {error ? (
            <p
              role="alert"
              data-testid="cold-start-error"
              style={{ color: "#b91c1c", marginTop: 12 }}
            >
              {error}
            </p>
          ) : null}
        </div>
      </section>
    </main>
  );
}
