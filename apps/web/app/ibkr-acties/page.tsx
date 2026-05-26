"use client";

/**
 * Task 133: IBKR Acties (Action Center) page.
 *
 * Three tabs locked by the brainstorm decision (2026-05-25):
 *   1. Te keuren — pending + approved drafts (this task).
 *   2. Actief bij IBKR — submitted-and-working orders (Task 134+).
 *   3. Historiek — completed / cancelled orders (Task 135+).
 *
 * For now only Te keuren has real data; the other two render a
 * placeholder ``EmptyState`` so the tab structure is visible from
 * day one without lying about the runtime state.
 */

import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { ActionDraftGrid } from "@/components/ActionDraftGrid";
import {
  apiClient,
  type ActionDraftResponse,
} from "@/lib/apiClient";

type TabKey = "te-keuren" | "actief" | "historiek";

const TABS: { key: TabKey; label_nl: string }[] = [
  { key: "te-keuren", label_nl: "Te keuren" },
  { key: "actief", label_nl: "Actief bij IBKR" },
  { key: "historiek", label_nl: "Historiek" },
];

export default function Page() {
  const [tab, setTab] = useState<TabKey>("te-keuren");
  const [drafts, setDrafts] = useState<ActionDraftResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    const result = await apiClient.getActionDraftsTeKeuren();
    if (!result.ok) {
      setError(
        "Actiedrafts konden niet worden geladen. Controleer of de API draait.",
      );
      setDrafts([]);
      return;
    }
    setDrafts(result.data.drafts);
  }, []);

  useEffect(() => {
    if (tab === "te-keuren") {
      void refresh();
    }
  }, [tab, refresh]);

  return (
    <main className="page-wrap" data-testid="ibkr-acties-page">
      <h2>IBKR Acties</h2>
      <p style={{ color: "#6b7280", marginTop: 4 }}>
        De drie-fase actieflow: <b>Te keuren</b> is jouw to-do laag —
        Decision Packages worden hier voorbereid als IBKR-orders. Pas
        bij goedkeuring gaat er iets naar IBKR; in deze release stopt de
        flow bij <i>Goedgekeurd</i> (echte verzending volgt in een
        toekomstige update).
      </p>

      <nav
        data-testid="ibkr-acties-tabs"
        role="tablist"
        style={{
          display: "flex",
          gap: 4,
          borderBottom: "2px solid #e5e7eb",
          marginTop: 16,
        }}
      >
        {TABS.map((entry) => (
          <button
            key={entry.key}
            type="button"
            role="tab"
            data-testid={`ibkr-acties-tab-${entry.key}`}
            aria-selected={tab === entry.key}
            onClick={() => setTab(entry.key)}
            style={{
              padding: "8px 16px",
              border: "none",
              background: tab === entry.key ? "#1d4ed8" : "transparent",
              color: tab === entry.key ? "#ffffff" : "#1f2937",
              borderRadius: "6px 6px 0 0",
              cursor: "pointer",
              fontWeight: tab === entry.key ? 700 : 500,
            }}
          >
            {entry.label_nl}
          </button>
        ))}
      </nav>

      <section style={{ marginTop: 16 }}>
        {tab === "te-keuren" ? (
          <div data-testid="ibkr-acties-te-keuren">
            {error ? (
              <div
                style={{
                  color: "#7f1d1d",
                  background: "#fee2e2",
                  padding: 12,
                  borderRadius: 6,
                  marginBottom: 12,
                }}
              >
                {error}
              </div>
            ) : null}
            {drafts === null ? (
              <p>Bezig met laden…</p>
            ) : (
              <ActionDraftGrid drafts={drafts} onChange={refresh} />
            )}
          </div>
        ) : null}

        {tab === "actief" ? (
          <EmptyState
            title="Module in opbouw"
            message="De Actief-bij-IBKR weergave verschijnt wanneer de IBKR-orderverzending live staat (toekomstige update)."
          />
        ) : null}

        {tab === "historiek" ? (
          <EmptyState
            title="Module in opbouw"
            message="De Historiek-weergave verschijnt wanneer er echte voltooide/geannuleerde orders binnenkomen."
          />
        ) : null}
      </section>
    </main>
  );
}
