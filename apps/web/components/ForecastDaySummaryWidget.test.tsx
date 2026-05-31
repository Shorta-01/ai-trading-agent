import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type { ForecastDaySummaryResponse } from "@/lib/apiClient";

const getForecastDaySummary = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getForecastDaySummary: (...args: unknown[]) =>
      getForecastDaySummary(...args),
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

import { ForecastDaySummaryWidget } from "./ForecastDaySummaryWidget";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const MIXED: ForecastDaySummaryResponse = {
  account_id: "DU1234567",
  as_of_date: "2026-05-25",
  total_forecasts: 12,
  total_blocked: 2,
  label_counts: {
    Kopen: 3,
    Bekijken: 5,
    Houden: 2,
    Geblokkeerd: 2,
  },
  block_reasons: { insufficient_history: 2 },
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const EMPTY: ForecastDaySummaryResponse = {
  account_id: "DU1234567",
  as_of_date: "2026-05-25",
  total_forecasts: 0,
  total_blocked: 0,
  label_counts: {},
  block_reasons: {},
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

beforeEach(() => {
  getForecastDaySummary.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("ForecastDaySummaryWidget", () => {
  it("renders all non-zero label pills with counts", async () => {
    getForecastDaySummary.mockResolvedValue({
      ok: true as const,
      data: MIXED,
    });
    render(<ForecastDaySummaryWidget />);

    expect(await screen.findByTestId("forecast-day-summary-total"))
      .toHaveTextContent("12 voorspellingen, 2 geblokkeerd.");

    const kopen = screen.getByTestId("forecast-day-summary-pill-Kopen");
    expect(kopen).toHaveTextContent("3 Kopen");
    expect(screen.getByTestId("forecast-day-summary-pill-Bekijken"))
      .toHaveTextContent("5 Bekijken");
    expect(screen.getByTestId("forecast-day-summary-pill-Houden"))
      .toHaveTextContent("2 Houden");
    expect(screen.getByTestId("forecast-day-summary-pill-Geblokkeerd"))
      .toHaveTextContent("2 Geblokkeerd");
  });

  it("omits zero-count labels", async () => {
    getForecastDaySummary.mockResolvedValue({
      ok: true as const,
      data: MIXED,
    });
    const { container } = render(<ForecastDaySummaryWidget />);
    await screen.findByTestId("forecast-day-summary-total");
    expect(
      container.querySelector('[data-testid="forecast-day-summary-pill-Verkopen"]'),
    ).toBeNull();
    expect(
      container.querySelector('[data-testid="forecast-day-summary-pill-Verminderen"]'),
    ).toBeNull();
  });

  it("renders the Dutch empty state when no forecasts today", async () => {
    getForecastDaySummary.mockResolvedValue({
      ok: true as const,
      data: EMPTY,
    });
    render(<ForecastDaySummaryWidget />);
    const empty = await screen.findByTestId("forecast-day-summary-empty");
    expect(empty).toHaveTextContent("Geen voorspellingen vandaag");
    expect(empty).toHaveTextContent("07:00");
  });

  it("each pill links to /suggesties (Volglijst-cleanup PR)", async () => {
    getForecastDaySummary.mockResolvedValue({
      ok: true as const,
      data: MIXED,
    });
    render(<ForecastDaySummaryWidget />);
    // Suggestions are the actionable surface; the widget pills now
    // route there instead of the legacy ?filter=<label> on Volglijst.
    const kopen = await screen.findByTestId("forecast-day-summary-pill-Kopen");
    expect(kopen.getAttribute("href")).toBe("/suggesties");
    const bekijken = screen.getByTestId("forecast-day-summary-pill-Bekijken");
    expect(bekijken.getAttribute("href")).toBe("/suggesties");
  });

  it("renders nothing on API failure", async () => {
    getForecastDaySummary.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    const { container } = render(<ForecastDaySummaryWidget />);
    await waitFor(() => {
      expect(getForecastDaySummary).toHaveBeenCalledTimes(1);
    });
    expect(
      container.querySelector('[data-testid="forecast-day-summary-widget"]'),
    ).toBeNull();
  });

  it("does not call the endpoint with account_id when none supplied", async () => {
    getForecastDaySummary.mockResolvedValue({
      ok: true as const,
      data: EMPTY,
    });
    render(<ForecastDaySummaryWidget />);
    await waitFor(() => {
      expect(getForecastDaySummary).toHaveBeenCalledTimes(1);
    });
    // Widget calls with no args (defaults to today/config-driven account).
    expect(getForecastDaySummary).toHaveBeenCalledWith();
  });
});
