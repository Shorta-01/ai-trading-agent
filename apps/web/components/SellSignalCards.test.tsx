import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type {
  SellSignalCardResponse,
  SellSignalListResponse,
  SellSignalSweepResponse,
} from "@/lib/apiClient";

const getSellSignals = vi.fn();
const dismissSellSignal = vi.fn();
const triggerSellSignalSweep = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getSellSignals: (...a: unknown[]) => getSellSignals(...a),
    dismissSellSignal: (...a: unknown[]) => dismissSellSignal(...a),
    triggerSellSignalSweep: (...a: unknown[]) => triggerSellSignalSweep(...a),
  },
}));

import { SellSignalCards } from "./SellSignalCards";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function makeCard(
  overrides: Partial<SellSignalCardResponse> = {},
): SellSignalCardResponse {
  return {
    card_id: "sscv_abc123",
    ibkr_account_ref: "paper",
    symbol: "AAPL",
    currency: "USD",
    signal_kind: "take_profit",
    action: "suggest_sell",
    entry_price: "100.00",
    current_price: "104.50",
    quantity: 100,
    current_pct_return: "4.50",
    target_pct: "4.00",
    target_reached: true,
    days_held: null,
    forecast_id: "fc_x",
    forecaster_above_target: null,
    position_in_loss: null,
    short_term_p50: "110.00",
    short_term_horizon_days: 90,
    short_term_prob_above_pct: "60.00",
    expected_net_proceeds_eur: "1488.00",
    headline_nl: "VERKOOP — AAPL staat op +4,5%, neem je winst",
    detail_nl: "+4,5% target geraakt. Operator beslist.",
    first_generated_at: "2026-06-14T10:30:00Z",
    last_evaluated_at: "2026-06-14T10:30:00Z",
    dismissed_at: null,
    dismissed_reason: null,
    ...overrides,
  };
}

function makeList(
  cards: SellSignalCardResponse[],
): SellSignalListResponse {
  return {
    title_nl: "SELL-suggesties",
    help_nl: "Operator beslist altijd.",
    cards,
  };
}

beforeEach(() => {
  getSellSignals.mockReset();
  dismissSellSignal.mockReset();
  triggerSellSignalSweep.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("SellSignalCards", () => {
  it("toont loading-state initieel", () => {
    getSellSignals.mockImplementation(
      () => new Promise<never>(() => {}),
    );
    render(<SellSignalCards />);
    expect(screen.getByTestId("sell-signal-cards-loading")).toBeTruthy();
  });

  it("toont empty-state met patience-tekst wanneer geen kaartjes", async () => {
    getSellSignals.mockResolvedValue({ ok: true, data: makeList([]) });
    render(<SellSignalCards />);
    await waitFor(() => {
      expect(screen.getByTestId("sell-signal-cards-empty")).toBeTruthy();
    });
    expect(screen.getByTestId("sell-signal-cards-empty").textContent).toMatch(
      /Geen actieve SELL-suggesties/i,
    );
  });

  it("rendert een take-profit kaartje met alle velden", async () => {
    const card = makeCard();
    getSellSignals.mockResolvedValue({ ok: true, data: makeList([card]) });
    render(<SellSignalCards />);
    await waitFor(() => {
      expect(screen.getByTestId(`sell-signal-card-${card.card_id}`)).toBeTruthy();
    });
    // Headline
    expect(
      screen.getByTestId(`sell-signal-card-headline-${card.card_id}`).textContent,
    ).toMatch(/VERKOOP/);
    // Kind badge
    expect(
      screen.getByTestId("sell-signal-card-kind-badge").textContent,
    ).toMatch(/Take-profit/i);
    // Return badge
    expect(
      screen.getByTestId(`sell-signal-card-return-${card.card_id}`).textContent,
    ).toMatch(/\+4,50%/);
    // Forecast context
    expect(
      screen.getByTestId(`sell-signal-card-forecast-${card.card_id}`).textContent,
    ).toMatch(/p50/);
    // Detail text
    expect(
      screen.getByTestId(`sell-signal-card-detail-${card.card_id}`).textContent,
    ).toMatch(/target geraakt/);
  });

  it("rendert hold_review kaartje met hold-review badge", async () => {
    const card = makeCard({
      signal_kind: "hold_review",
      headline_nl: "REVIEW — MSFT: outlook verslechterd",
      days_held: 200,
      forecaster_above_target: false,
      position_in_loss: true,
    });
    getSellSignals.mockResolvedValue({ ok: true, data: makeList([card]) });
    render(<SellSignalCards />);
    await waitFor(() => {
      expect(
        screen.getByTestId("sell-signal-card-kind-badge").textContent,
      ).toMatch(/hold-review/i);
    });
  });

  it("dismiss-knop roept dismissSellSignal aan met reason", async () => {
    const card = makeCard();
    getSellSignals.mockResolvedValue({ ok: true, data: makeList([card]) });
    dismissSellSignal.mockResolvedValue({ ok: true, data: card });
    render(<SellSignalCards />);
    await waitFor(() => {
      expect(screen.getByTestId(`sell-signal-card-${card.card_id}`)).toBeTruthy();
    });
    const reasonInput = screen.getByTestId(
      `sell-signal-card-dismiss-reason-${card.card_id}`,
    ) as HTMLInputElement;
    fireEvent.change(reasonInput, {
      target: { value: "ik wacht op verder rijzen" },
    });
    fireEvent.click(
      screen.getByTestId(`sell-signal-card-dismiss-${card.card_id}`),
    );
    await waitFor(() => {
      expect(dismissSellSignal).toHaveBeenCalledWith(
        card.card_id,
        "ik wacht op verder rijzen",
      );
    });
  });

  it("dismiss-knop met lege reason stuurt undefined", async () => {
    const card = makeCard();
    getSellSignals.mockResolvedValue({ ok: true, data: makeList([card]) });
    dismissSellSignal.mockResolvedValue({ ok: true, data: card });
    render(<SellSignalCards />);
    await waitFor(() => {
      expect(screen.getByTestId(`sell-signal-card-${card.card_id}`)).toBeTruthy();
    });
    fireEvent.click(
      screen.getByTestId(`sell-signal-card-dismiss-${card.card_id}`),
    );
    await waitFor(() => {
      expect(dismissSellSignal).toHaveBeenCalledWith(card.card_id, undefined);
    });
  });

  it("herevalueer-knop roept sweep aan", async () => {
    getSellSignals.mockResolvedValue({ ok: true, data: makeList([]) });
    const sweepResponse: SellSignalSweepResponse = {
      started_at: "2026-06-14T10:30:00Z",
      completed_at: "2026-06-14T10:30:01Z",
      positions_evaluated: 1,
      take_profit_cards_upserted: 1,
      hold_review_cards_upserted: 1,
      skipped_no_forecast: 0,
      skipped_no_position: 0,
      error_text: null,
    };
    triggerSellSignalSweep.mockResolvedValue({ ok: true, data: sweepResponse });
    render(<SellSignalCards />);
    await waitFor(() => {
      expect(screen.getByTestId("sell-signal-cards-empty")).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId("sell-signal-cards-sweep-button"));
    await waitFor(() => {
      expect(triggerSellSignalSweep).toHaveBeenCalledTimes(1);
    });
  });

  it("toont error-state wanneer getSellSignals faalt", async () => {
    getSellSignals.mockResolvedValue({
      ok: false,
      reason: "not_reachable",
    });
    render(<SellSignalCards />);
    await waitFor(() => {
      expect(screen.getByTestId("sell-signal-cards-error")).toBeTruthy();
    });
  });
});
