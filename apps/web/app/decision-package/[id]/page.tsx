"use client";

/**
 * Task 132: Decision Package detail page.
 *
 * Client component that fetches the package by ID and delegates to
 * ``DecisionPackageDetail`` for rendering. Three states: loading,
 * not-found (Dutch fallback), and rendered.
 *
 * Uses ``useParams()`` rather than the ``use(params)`` Promise-unwrap
 * pattern — ``use()`` suspends and requires a Suspense boundary,
 * which the parent layout doesn't provide, leaving the page blank in
 * production builds (caught by the Task 132 e2e suite, fixed in the
 * Task 132 hot-fix).
 *
 * Kept thin on purpose — the rendering logic lives in the component
 * for testability.
 */

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { DecisionPackageDetail } from "@/components/DecisionPackageDetail";
import {
  apiClient,
  type DecisionPackageResponse,
} from "@/lib/apiClient";

export default function Page() {
  const params = useParams<{ id: string }>();
  const query = useQuery({
    queryKey: ["decision-package", params?.id],
    enabled: Boolean(params?.id),
    queryFn: async (): Promise<DecisionPackageResponse> => {
      const result = await apiClient.getDecisionPackage(params.id);
      // apiClient.getJson collapses all non-OK responses (404 + 503)
      // to ``not_reachable`` — surface a single Dutch fallback rather
      // than guessing which one happened.
      if (!result.ok) throw new Error("not_reachable");
      return result.data;
    },
  });

  const pkg = query.data ?? null;

  if (query.isError) {
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
