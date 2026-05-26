"use client";

/**
 * Task 133 + 134c: IBKR Acties (Action Center) page.
 *
 * Three tabs locked by the brainstorm decision (2026-05-25):
 *   1. Te keuren — pending + approved drafts (Task 133).
 *   2. Actief bij IBKR — submitted/accepted/working/partially_filled/
 *      pending_cancellation drafts (Task 134c).
 *   3. Historiek — filled/cancelled/rejected/dismissed/deleted/
 *      superseded/awaiting_reply_timeout drafts (Task 134c).
 *
 * All three tabs now show real data. The lifecycle drawer opens on
 * any row click in Actief or Historiek.
 */

import { useCallback, useEffect, useState } from "react";

import { ActionDraftGrid } from "@/components/ActionDraftGrid";
import {
  ActiefBijIbkrGrid,
  HistoriekGrid,
} from "@/components/IbkrSubmissionGrids";
import { SubmissionLifecycleDrawer } from "@/components/SubmissionLifecycleDrawer";
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

  // Te keuren tab data.
  const [teKeurenDrafts, setTeKeurenDrafts] = useState<
    ActionDraftResponse[] | null
  >(null);
  const [teKeurenError, setTeKeurenError] = useState<string | null>(null);

  // Actief bij IBKR tab data.
  const [actiefDrafts, setActiefDrafts] = useState<
    ActionDraftResponse[] | null
  >(null);
  const [actiefError, setActiefError] = useState<string | null>(null);

  // Historiek tab data.
  const [historiekDrafts, setHistoriekDrafts] = useState<
    ActionDraftResponse[] | null
  >(null);
  const [historiekError, setHistoriekError] = useState<string | null>(null);

  // Drawer.
  const [drawerDraftId, setDrawerDraftId] = useState<string | null>(null);

  const refreshTeKeuren = useCallback(async () => {
    setTeKeurenError(null);
    const result = await apiClient.getActionDraftsTeKeuren();
    if (!result.ok) {
      setTeKeurenError(
        "Actiedrafts konden niet worden geladen. Controleer of de API draait.",
      );
      setTeKeurenDrafts([]);
      return;
    }
    setTeKeurenDrafts(result.data.drafts);
  }, []);

  const refreshActief = useCallback(async () => {
    setActiefError(null);
    const result = await apiClient.getIbkrSubmissionActive();
    if (!result.ok) {
      setActiefError(
        "Actieve orders konden niet worden geladen. Controleer of de API draait.",
      );
      setActiefDrafts([]);
      return;
    }
    setActiefDrafts(result.data.drafts);
  }, []);

  const refreshHistoriek = useCallback(async () => {
    setHistoriekError(null);
    const result = await apiClient.getIbkrSubmissionHistoriek();
    if (!result.ok) {
      setHistoriekError(
        "Historiek kon niet worden geladen. Controleer of de API draait.",
      );
      setHistoriekDrafts([]);
      return;
    }
    setHistoriekDrafts(result.data.drafts);
  }, []);

  useEffect(() => {
    if (tab === "te-keuren") {
      void refreshTeKeuren();
    } else if (tab === "actief") {
      void refreshActief();
    } else if (tab === "historiek") {
      void refreshHistoriek();
    }
  }, [tab, refreshTeKeuren, refreshActief, refreshHistoriek]);

  return (
    <main className="page-wrap" data-testid="ibkr-acties-page">
      <h2>IBKR Acties</h2>
      <p style={{ color: "#6b7280", marginTop: 4 }}>
        De drie-fase actieflow: <b>Te keuren</b> is jouw to-do laag —
        Decision Packages worden hier voorbereid als IBKR-orders.{" "}
        <b>Actief bij IBKR</b> toont lopende orders en{" "}
        <b>Historiek</b> de afgeronde orders.
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
            {teKeurenError ? (
              <div
                style={{
                  color: "#7f1d1d",
                  background: "#fee2e2",
                  padding: 12,
                  borderRadius: 6,
                  marginBottom: 12,
                }}
              >
                {teKeurenError}
              </div>
            ) : null}
            {teKeurenDrafts === null ? (
              <p>Bezig met laden…</p>
            ) : (
              <ActionDraftGrid
                drafts={teKeurenDrafts}
                onChange={refreshTeKeuren}
              />
            )}
          </div>
        ) : null}

        {tab === "actief" ? (
          <div data-testid="ibkr-acties-actief">
            {actiefError ? (
              <div
                style={{
                  color: "#7f1d1d",
                  background: "#fee2e2",
                  padding: 12,
                  borderRadius: 6,
                  marginBottom: 12,
                }}
              >
                {actiefError}
              </div>
            ) : null}
            {actiefDrafts === null ? (
              <p>Bezig met laden…</p>
            ) : (
              <ActiefBijIbkrGrid
                drafts={actiefDrafts}
                onChange={refreshActief}
                onOpenLifecycle={setDrawerDraftId}
              />
            )}
          </div>
        ) : null}

        {tab === "historiek" ? (
          <div data-testid="ibkr-acties-historiek">
            {historiekError ? (
              <div
                style={{
                  color: "#7f1d1d",
                  background: "#fee2e2",
                  padding: 12,
                  borderRadius: 6,
                  marginBottom: 12,
                }}
              >
                {historiekError}
              </div>
            ) : null}
            {historiekDrafts === null ? (
              <p>Bezig met laden…</p>
            ) : (
              <HistoriekGrid
                drafts={historiekDrafts}
                onOpenLifecycle={setDrawerDraftId}
              />
            )}
          </div>
        ) : null}
      </section>

      <SubmissionLifecycleDrawer
        actionDraftId={drawerDraftId}
        open={drawerDraftId !== null}
        onClose={() => setDrawerDraftId(null)}
      />
    </main>
  );
}
