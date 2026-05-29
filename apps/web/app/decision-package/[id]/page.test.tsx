import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DecisionPackageResponse } from "@/lib/apiClient";

const getDecisionPackage = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getDecisionPackage: (...a: unknown[]) => getDecisionPackage(...a),
  },
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "dp-1" }),
}));

// Stub the heavy presentational child; this page's job is just the
// fetch + state machine around it.
vi.mock("@/components/DecisionPackageDetail", () => ({
  DecisionPackageDetail: ({ package: pkg }: { package: DecisionPackageResponse }) => (
    <div data-testid="dp-detail-stub">{pkg.decision_package_id}</div>
  ),
}));

import Page from "./page";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function ok(id: string) {
  return Promise.resolve({
    ok: true as const,
    data: { decision_package_id: id } as DecisionPackageResponse,
  });
}

beforeEach(() => getDecisionPackage.mockReset());
afterEach(() => cleanup());

describe("DecisionPackage detail page", () => {
  it("shows the loading state before the package arrives", () => {
    // Resolves to valid data, but the loading state is asserted
    // synchronously on first render before the microtask flushes.
    getDecisionPackage.mockReturnValue(ok("dp-1"));
    render(<Page />);
    expect(screen.getByTestId("decision-package-loading")).toBeInTheDocument();
  });

  it("renders the package detail on success", async () => {
    getDecisionPackage.mockReturnValue(ok("dp-1"));
    render(<Page />);
    expect(await screen.findByTestId("dp-detail-stub")).toHaveTextContent(
      "dp-1",
    );
    expect(getDecisionPackage).toHaveBeenCalledWith("dp-1");
  });

  it("renders the Dutch not-found fallback on failure", async () => {
    getDecisionPackage.mockReturnValue(
      Promise.resolve({ ok: false as const, reason: "not_reachable" }),
    );
    render(<Page />);
    expect(
      await screen.findByTestId("decision-package-not-found"),
    ).toBeInTheDocument();
  });
});
