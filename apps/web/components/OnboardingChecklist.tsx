"use client";

/**
 * V1.2 §CA / GAPS.md P2-3 — Cold-start onboarding checklist.
 *
 * Bestaande `ColdStartBanner` dekt alleen het watchlist-confirmation
 * pad. Deze component vult de gap voor een **bredere onboarding**:
 * toont een prominente 3-stappen checklist bovenaan het dashboard
 * wanneer de software op verse-install staat (geen positions, geen
 * favorieten) of wanneer de runbook nog blocking items heeft.
 *
 * Verdwijnt automatisch zodra alle drie stappen done zijn — geen
 * polling-flicker (dankzij staleTime 5min op alle drie queries).
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { apiClient } from "@/lib/apiClient";

const STALE_MS = 5 * 60 * 1000;

export function OnboardingChecklist() {
  const positionsQuery = useQuery({
    queryKey: ["onboarding-positions"],
    queryFn: async () => {
      const result = await apiClient.getIbkrPositions();
      return result.ok ? result.data.items.length : null;
    },
    staleTime: STALE_MS,
  });
  const favoritesQuery = useQuery({
    queryKey: ["onboarding-favorites"],
    queryFn: async () => {
      const result = await apiClient.listFavorieten();
      return result.ok ? (result.data.items?.length ?? 0) : null;
    },
    staleTime: STALE_MS,
  });
  const runbookQuery = useQuery({
    queryKey: ["onboarding-runbook"],
    queryFn: async () => {
      const result = await apiClient.getRunbook();
      return result.ok ? result.data : null;
    },
    staleTime: STALE_MS,
  });

  if (
    positionsQuery.isLoading ||
    favoritesQuery.isLoading ||
    runbookQuery.isLoading
  ) {
    return null;
  }

  const positionsCount = positionsQuery.data ?? 0;
  const favoritesCount = favoritesQuery.data ?? 0;
  const runbook = runbookQuery.data;
  const runbookReady = runbook?.ready_for_paper_go_live ?? false;
  const blockingItems =
    runbook?.items.filter((i) => i.status === "blocking").length ?? 0;

  // Wanneer alle drie stappen done zijn verdwijnt de checklist.
  if (positionsCount > 0 && favoritesCount > 0 && runbookReady) {
    return null;
  }

  const steps = [
    {
      key: "runbook",
      label: "Runbook controleren",
      done: runbookReady,
      desc: runbookReady
        ? "Alle doctrine-locks + provider-configuratie OK."
        : `${blockingItems} blocking-item(s) in de runbook nog te fixen.`,
      href: "/runbook",
      cta: "Open runbook",
    },
    {
      key: "ibkr",
      label: "IBKR-verbinding + sync",
      done: positionsCount > 0,
      desc:
        positionsCount > 0
          ? `${positionsCount} positie(s) bekend in laatste sync.`
          : "Configureer IBKR paper-account in /instellingen → IBKR.",
      href: "/instellingen",
      cta: "Naar instellingen",
    },
    {
      key: "favorites",
      label: "Watchlist favorieten",
      done: favoritesCount > 0,
      desc:
        favoritesCount > 0
          ? `${favoritesCount} favoriet(en) opgeslagen.`
          : "Voeg minstens één favoriet toe zodat het dashboard direct live confidence toont.",
      href: "/instellingen",
      cta: "Beheer watchlist",
    },
  ];

  return (
    <section
      data-testid="onboarding-checklist"
      style={{
        background: "#fef9c3",
        border: "1px solid #facc15",
        borderRadius: 8,
        padding: 16,
        marginBottom: 12,
      }}
    >
      <header style={{ marginBottom: 8 }}>
        <h2 style={{ margin: 0, fontSize: 16, color: "#713f12" }}>
          Eerste keer hier? Drie stappen om de software live te krijgen
        </h2>
        <p
          style={{
            margin: "4px 0 0 0",
            fontSize: 12,
            color: "#854d0e",
          }}
        >
          Het dashboard is nu nog leeg omdat de software op startpositie
          staat. Werk onderstaande stappen één voor één af; deze checklist
          verdwijnt automatisch zodra alles klaar is.
        </p>
      </header>
      <ol
        data-testid="onboarding-checklist-steps"
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {steps.map((step, idx) => (
          <li
            key={step.key}
            data-testid={`onboarding-step-${step.key}`}
            data-done={step.done}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "8px 12px",
              background: step.done ? "#dcfce7" : "#ffffff",
              border: `1px solid ${step.done ? "#86efac" : "#fef3c7"}`,
              borderRadius: 6,
            }}
          >
            <span
              style={{
                width: 24,
                height: 24,
                borderRadius: 12,
                background: step.done ? "#16a34a" : "#facc15",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                fontSize: 13,
              }}
            >
              {step.done ? "✓" : idx + 1}
            </span>
            <div style={{ flex: 1, minWidth: 200 }}>
              <strong
                style={{
                  fontSize: 13,
                  color: step.done ? "#166534" : "#713f12",
                }}
              >
                {step.label}
              </strong>
              <p
                style={{
                  margin: "2px 0 0 0",
                  fontSize: 12,
                  color: "#4b5563",
                }}
              >
                {step.desc}
              </p>
            </div>
            {!step.done && (
              <Link
                data-testid={`onboarding-cta-${step.key}`}
                href={step.href}
                style={{
                  padding: "6px 12px",
                  background: "#0f172a",
                  color: "#ffffff",
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  textDecoration: "none",
                }}
              >
                {step.cta} →
              </Link>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
