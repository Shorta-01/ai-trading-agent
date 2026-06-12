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
  EarningsUpcomingResponse,
  OrchestratorVerdictRow,
  OrchestratorVerdictsListResponse,
} from "@/lib/apiClient";

const listOrchestratorVerdicts = vi.fn();
const getUpcomingEarnings = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    listOrchestratorVerdicts: (...a: unknown[]) =>
      listOrchestratorVerdicts(...a),
    getUpcomingEarnings: (...a: unknown[]) => getUpcomingEarnings(...a),
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

const EMPTY_FEED: EarningsUpcomingResponse = {
  title_nl: "Aankomende earnings",
  help_nl: "",
  window_days: 7,
  items: [],
};

const FEED_SAMPLE: EarningsUpcomingResponse = {
  title_nl: "Aankomende earnings",
  help_nl: "",
  window_days: 7,
  items: [
    {
      earnings_event_id: "ev-1",
      symbol: "AAPL",
      ibkr_conid: "1",
      event_date: "2026-06-15",
      status: "confirmed",
      source: "eodhd",
      fetched_at: "2026-06-12T06:00:00Z",
    },
    {
      earnings_event_id: "ev-2",
      symbol: "MSFT",
      ibkr_conid: "2",
      event_date: "2026-06-17",
      status: "estimated",
      source: "eodhd",
      fetched_at: "2026-06-12T06:00:00Z",
    },
  ],
};

beforeEach(() => {
  listOrchestratorVerdicts.mockReset();
  getUpcomingEarnings.mockReset();
});

afterEach(() => cleanup());

describe("EarningsThisWeekStrip", () => {
  it("uses the real earnings feed when /earnings/upcoming returns rows", async () => {
    getUpcomingEarnings.mockResolvedValue(ok(FEED_SAMPLE));
    listOrchestratorVerdicts.mockResolvedValue(
      ok({ title_nl: "", help_nl: "", items: [] } as OrchestratorVerdictsListResponse),
    );
    render(<EarningsThisWeekStrip />);
    await waitFor(() => {
      expect(
        screen.getByTestId("earnings-this-week-strip"),
      ).toHaveAttribute("data-mode", "feed");
    });
    expect(
      screen.getByTestId("earnings-this-week-chip-AAPL"),
    ).toHaveTextContent("AAPL");
    expect(
      screen.getByTestId("earnings-this-week-chip-MSFT"),
    ).toHaveTextContent("MSFT");
  });

  it("falls back to skip_earnings_window verdicts when feed is empty", async () => {
    getUpcomingEarnings.mockResolvedValue(ok(EMPTY_FEED));
    const verdicts: OrchestratorVerdictsListResponse = {
      title_nl: "",
      help_nl: "",
      items: [
        makeVerdict({ verdict_id: "v1", symbol: "AAPL" }),
        makeVerdict({
          verdict_id: "v2",
          symbol: "NOT_BLOCKED",
          decision: "suggest",
          blocking_reason: null,
        }),
      ],
    };
    listOrchestratorVerdicts.mockResolvedValue(ok(verdicts));
    render(<EarningsThisWeekStrip />);
    await waitFor(() => {
      expect(
        screen.getByTestId("earnings-this-week-strip"),
      ).toHaveAttribute("data-mode", "fallback");
    });
    expect(
      screen.getByTestId("earnings-this-week-chip-AAPL"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("earnings-this-week-chip-NOT_BLOCKED"),
    ).toBeNull();
  });

  it("renders nothing when both feed and verdict-fallback are empty", async () => {
    getUpcomingEarnings.mockResolvedValue(ok(EMPTY_FEED));
    listOrchestratorVerdicts.mockResolvedValue(
      ok({ title_nl: "", help_nl: "", items: [] } as OrchestratorVerdictsListResponse),
    );
    const { container } = render(<EarningsThisWeekStrip />);
    await waitFor(() => {
      expect(getUpcomingEarnings).toHaveBeenCalledTimes(1);
      expect(listOrchestratorVerdicts).toHaveBeenCalledTimes(1);
    });
    expect(
      container.querySelector('[data-testid="earnings-this-week-strip"]'),
    ).toBeNull();
  });
});
