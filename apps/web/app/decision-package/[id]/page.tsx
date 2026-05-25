"use client";

/**
 * Task 132: Decision Package detail page.
 *
 * Client component that fetches the package by ID and delegates to
 * ``DecisionPackageDetail`` for rendering. Three states: loading,
 * not-found (Dutch fallback), and rendered.
 *
 * Kept thin on purpose — the rendering logic lives in the component
 * for testability.
 */

import { use, useEffect, useState } from "react";

import { DecisionPackageDetail } from "@/components/DecisionPackageDetail";
import {
  apiClient,
  type DecisionPackageResponse,
} from "@/lib/apiClient";

export default function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const [pkg, setPkg] = useState<DecisionPackageResponse | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const result = await apiClient.getDecisionPackage(resolvedParams.id);
      if (cancelled) return;
      if (result.ok) {
        setPkg(result.data);
      } else {
        // apiClient.getJson collapses all non-OK responses (404 + 503)
        // to ``not_reachable`` — surface a single Dutch fallback rather
        // than guessing which one happened.
        setUnavailable(true);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [resolvedParams.id]);

  if (unavailable) {
    return (
      <main className="page-wrap" style={{ padding: 24 }}>
        <p data-testid="decision-package-not-found">
          Decision Package niet gevonden.
        </p>
      </main>
    );
  }
  if (pkg === null) {
    return (
      <main className="page-wrap" style={{ padding: 24 }}>
        <p data-testid="decision-package-loading">Bezig met laden…</p>
      </main>
    );
  }
  return (
    <main className="page-wrap">
      <DecisionPackageDetail package={pkg} />
    </main>
  );
}
