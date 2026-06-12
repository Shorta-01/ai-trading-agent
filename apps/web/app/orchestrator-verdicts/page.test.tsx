import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { OrchestratorVerdictsListResponse } from "@/lib/apiClient";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const listOrchestratorVerdicts = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    listOrchestratorVerdicts: (...a: unknown[]) =>
      listOrchestratorVerdicts(...a),
  },
}));

import Page from "./page";

const ok = <T,>(data: T) => ({ ok: true as const, data });

const SAMPLE: OrchestratorVerdictsListResponse = {
  title_nl: "Orchestrator verdicts",
  help_nl: "Verdicts van de profit-harvest orchestrator per kandidaat.",
  items: [
    {
      verdict_id: "v1",
      symbol: "AAPL",
      ibkr_conid: 1,
      forecast_id: "fc-AAPL",
      generated_at: "2026-06-12T09:00:00Z",
      decision: "suggest",
      blocking_reason: null,
      summary_nl: "AAPL voldoet aan alle gates.",
      details_json: { macro: { favorable: true } },
    },
    {
      verdict_id: "v2",
      symbol: "EARN",
      ibkr_conid: 2,
      forecast_id: "fc-EARN",
      generated_at: "2026-06-12T09:01:00Z",
      decision: "skip_earnings_window",
      blocking_reason: "earnings_within_block_window",
      summary_nl: "EARN binnen earnings-blokvenster.",
      details_json: { earnings: { in_window: true } },
    },
  ],
};

beforeEach(() => {
  listOrchestratorVerdicts.mockReset();
  listOrchestratorVerdicts.mockReturnValue(ok(SAMPLE));
});

afterEach(() => cleanup());

describe("OrchestratorVerdictsPage", () => {
  it("renders a row per verdict with Dutch decision label", async () => {
    render(<Page />);
    expect(await screen.findByTestId("verdict-row-v1")).toHaveTextContent(
      "AAPL",
    );
    expect(screen.getByTestId("verdict-row-v1")).toHaveTextContent(
      "Voorgesteld",
    );
    expect(screen.getByTestId("verdict-row-v2")).toHaveTextContent(
      "Earnings-venster",
    );
    expect(screen.getByTestId("verdict-row-v2")).toHaveTextContent(
      "earnings_within_block_window",
    );
  });

  it("expands a row to reveal the details_json blob", async () => {
    render(<Page />);
    const toggle = await screen.findByTestId("verdict-row-v1-toggle");
    fireEvent.click(toggle);
    const details = screen.getByTestId("verdict-row-v1-details");
    expect(details).toHaveTextContent("macro");
    expect(details).toHaveTextContent("favorable");
  });

  it("filters rows by decision code via chip", async () => {
    render(<Page />);
    await screen.findByTestId("verdict-row-v1");
    fireEvent.click(screen.getByTestId("verdict-filter-skip_earnings_window"));
    expect(screen.queryByTestId("verdict-row-v1")).toBeNull();
    expect(screen.getByTestId("verdict-row-v2")).toBeInTheDocument();
    // "Alle" restores all rows.
    fireEvent.click(screen.getByTestId("verdict-filter-all"));
    expect(screen.getByTestId("verdict-row-v1")).toBeInTheDocument();
    expect(screen.getByTestId("verdict-row-v2")).toBeInTheDocument();
  });

  it("renders Dutch empty state when no verdicts", async () => {
    listOrchestratorVerdicts.mockReturnValue(
      ok({ ...SAMPLE, items: [] }),
    );
    render(<Page />);
    expect(
      await screen.findByTestId("orchestrator-verdicts-empty"),
    ).toHaveTextContent("Nog geen verdicts geschreven");
  });
});
