import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type { OrchestratorVerdictsSummaryResponse } from "@/lib/apiClient";

const getOrchestratorVerdictsSummary = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getOrchestratorVerdictsSummary: (...args: unknown[]) =>
      getOrchestratorVerdictsSummary(...args),
  },
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

import { OrchestratorVerdictsSummary } from "./OrchestratorVerdictsSummary";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const MIXED: OrchestratorVerdictsSummaryResponse = {
  title_nl: "Doctrine output vandaag",
  help_nl: "Per gate.",
  total: 5,
  by_decision: {
    suggest: 2,
    skip_earnings_window: 1,
    skip_risk_universe: 2,
  },
  latest_generated_at: "2026-06-12T09:00:00Z",
};

const EMPTY: OrchestratorVerdictsSummaryResponse = {
  title_nl: "Doctrine output vandaag",
  help_nl: "Per gate.",
  total: 0,
  by_decision: {},
  latest_generated_at: null,
};

beforeEach(() => {
  getOrchestratorVerdictsSummary.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("OrchestratorVerdictsSummary", () => {
  it("renders a chip per decision code with Dutch label and count", async () => {
    getOrchestratorVerdictsSummary.mockResolvedValue({
      ok: true as const,
      data: MIXED,
    });
    render(<OrchestratorVerdictsSummary />);

    const widget = await screen.findByTestId(
      "orchestrator-verdicts-summary-widget",
    );
    expect(widget).toHaveTextContent("Doctrine output vandaag");
    expect(widget).toHaveTextContent("Totaal 5 kandidaten");

    expect(
      screen.getByTestId("orchestrator-verdicts-chip-suggest"),
    ).toHaveTextContent("Voorgesteld: 2");
    expect(
      screen.getByTestId("orchestrator-verdicts-chip-skip_earnings_window"),
    ).toHaveTextContent("Earnings-venster: 1");
    expect(
      screen.getByTestId("orchestrator-verdicts-chip-skip_risk_universe"),
    ).toHaveTextContent("Risico-filter: 2");
  });

  it("renders Dutch empty state when no verdicts today", async () => {
    getOrchestratorVerdictsSummary.mockResolvedValue({
      ok: true as const,
      data: EMPTY,
    });
    render(<OrchestratorVerdictsSummary />);
    const empty = await screen.findByTestId("orchestrator-verdicts-empty");
    expect(empty).toHaveTextContent("Nog geen verdicts vandaag");
    expect(empty).toHaveTextContent("morning chain");
  });

  it("links the widget card to /orchestrator-verdicts", async () => {
    getOrchestratorVerdictsSummary.mockResolvedValue({
      ok: true as const,
      data: MIXED,
    });
    render(<OrchestratorVerdictsSummary />);
    const widget = await screen.findByTestId(
      "orchestrator-verdicts-summary-widget",
    );
    expect(widget.getAttribute("href")).toBe("/orchestrator-verdicts");
  });

  it("renders nothing on API failure", async () => {
    getOrchestratorVerdictsSummary.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    const { container } = render(<OrchestratorVerdictsSummary />);
    await waitFor(() => {
      expect(getOrchestratorVerdictsSummary).toHaveBeenCalledTimes(1);
    });
    expect(
      container.querySelector(
        '[data-testid="orchestrator-verdicts-summary-widget"]',
      ),
    ).toBeNull();
  });
});
