import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type {
  OrchestratorVerdictRow,
  OrchestratorVerdictsListResponse,
} from "@/lib/apiClient";

const listOrchestratorVerdicts = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    listOrchestratorVerdicts: (...a: unknown[]) =>
      listOrchestratorVerdicts(...a),
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

import { EarningsThisWeekStrip } from "./EarningsThisWeekStrip";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function makeVerdict(
  overrides: Partial<OrchestratorVerdictRow> & {
    verdict_id: string;
    symbol: string;
  },
): OrchestratorVerdictRow {
  return {
    ibkr_conid: 1,
    forecast_id: "fc",
    generated_at: "2026-06-12T07:00:00Z",
    decision: "skip_earnings_window",
    blocking_reason: "earnings_within_block_window",
    summary_nl: "Earnings binnen 5 dagen",
    details_json: {},
    ...overrides,
  };
}

const ok = <T,>(data: T) => ({ ok: true as const, data });

beforeEach(() => {
  listOrchestratorVerdicts.mockReset();
});

afterEach(() => cleanup());

describe("EarningsThisWeekStrip", () => {
  it("renders a chip per unique earnings-blocked symbol", async () => {
    const data: OrchestratorVerdictsListResponse = {
      title_nl: "",
      help_nl: "",
      items: [
        makeVerdict({ verdict_id: "v1", symbol: "AAPL" }),
        makeVerdict({
          verdict_id: "v2",
          symbol: "MSFT",
        }),
        makeVerdict({ verdict_id: "v3", symbol: "OTHER", decision: "suggest" }),
        makeVerdict({ verdict_id: "v4", symbol: "AAPL" }),
      ],
    };
    listOrchestratorVerdicts.mockResolvedValue(ok(data));
    render(<EarningsThisWeekStrip />);
    await screen.findByTestId("earnings-this-week-strip");
    expect(
      screen.getByTestId("earnings-this-week-chip-AAPL"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("earnings-this-week-chip-MSFT"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("earnings-this-week-chip-OTHER"),
    ).toBeNull();
  });

  it("renders nothing when there are no earnings-blocked verdicts", async () => {
    listOrchestratorVerdicts.mockResolvedValue(
      ok({
        title_nl: "",
        help_nl: "",
        items: [
          makeVerdict({
            verdict_id: "v1",
            symbol: "AAPL",
            decision: "suggest",
            blocking_reason: null,
          }),
        ],
      }),
    );
    const { container } = render(<EarningsThisWeekStrip />);
    await waitFor(() => {
      expect(listOrchestratorVerdicts).toHaveBeenCalledTimes(1);
    });
    expect(
      container.querySelector('[data-testid="earnings-this-week-strip"]'),
    ).toBeNull();
  });
});
