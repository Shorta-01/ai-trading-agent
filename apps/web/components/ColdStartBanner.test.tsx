import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type { WatchlistConfirmationStateResponse } from "@/lib/apiClient";

const getWatchlistConfirmationState = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getWatchlistConfirmationState: (...args: unknown[]) =>
      getWatchlistConfirmationState(...args),
  },
}));

// Stub next/link so JSDOM doesn't choke on Next's client manifest.
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

import { ColdStartBanner } from "./ColdStartBanner";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function ok(data: WatchlistConfirmationStateResponse) {
  return Promise.resolve({ ok: true as const, data });
}

const UNCONFIRMED: WatchlistConfirmationStateResponse = {
  account_id: "DU1234567",
  state: "unconfirmed",
  banner_text:
    "Welkom. Je IBKR-rekening is gesynchroniseerd. Het systeem heeft een startvoorstel voor je Volglijst klaargezet. Bekijk en bevestig in Volglijst voordat suggesties starten.",
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const CONFIRMED: WatchlistConfirmationStateResponse = {
  account_id: "DU1234567",
  state: "confirmed",
  banner_text: null,
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const NO_ACCOUNT: WatchlistConfirmationStateResponse = {
  account_id: null,
  state: "no_account_configured",
  banner_text: null,
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  getWatchlistConfirmationState.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
  cleanup();
});

describe("ColdStartBanner", () => {
  it("renders the Dutch banner + link when state is unconfirmed", async () => {
    getWatchlistConfirmationState.mockReturnValue(ok(UNCONFIRMED));

    render(<ColdStartBanner />);

    const banner = await screen.findByTestId("cold-start-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveAttribute("data-state", "unconfirmed");
    expect(banner).toHaveTextContent("Welkom.");
    const link = await screen.findByTestId("cold-start-banner-link");
    expect(link).toHaveAttribute("href", "/volglijst");
    expect(link).toHaveTextContent("Naar Volglijst");
  });

  it("renders nothing when state is confirmed", async () => {
    getWatchlistConfirmationState.mockReturnValue(ok(CONFIRMED));

    const { container } = render(<ColdStartBanner />);
    // Wait for the fetch to resolve.
    await waitFor(() => {
      expect(getWatchlistConfirmationState).toHaveBeenCalledTimes(1);
    });
    // No banner in the DOM.
    expect(
      container.querySelector('[data-testid="cold-start-banner"]'),
    ).toBeNull();
  });

  it("renders nothing when no account is configured", async () => {
    getWatchlistConfirmationState.mockReturnValue(ok(NO_ACCOUNT));

    const { container } = render(<ColdStartBanner />);
    await waitFor(() => {
      expect(getWatchlistConfirmationState).toHaveBeenCalledTimes(1);
    });
    expect(
      container.querySelector('[data-testid="cold-start-banner"]'),
    ).toBeNull();
  });

  it("polls /watchlist/confirmation-state on the 60-second interval", async () => {
    getWatchlistConfirmationState.mockReturnValue(ok(CONFIRMED));

    render(<ColdStartBanner />);
    await waitFor(() => {
      expect(getWatchlistConfirmationState).toHaveBeenCalledTimes(1);
    });

    // TanStack Query's refetchInterval; exact count is implementation
    // detail under auto-advancing fake timers, so assert >=.
    await vi.advanceTimersByTimeAsync(60_000);
    expect(
      getWatchlistConfirmationState.mock.calls.length,
    ).toBeGreaterThanOrEqual(2);

    await vi.advanceTimersByTimeAsync(60_000);
    expect(
      getWatchlistConfirmationState.mock.calls.length,
    ).toBeGreaterThanOrEqual(3);
  });

  it("flips from unconfirmed (visible) to confirmed (hidden) on poll", async () => {
    getWatchlistConfirmationState
      .mockReturnValueOnce(ok(UNCONFIRMED))
      .mockReturnValueOnce(ok(CONFIRMED));

    const { container } = render(<ColdStartBanner />);
    await screen.findByTestId("cold-start-banner");
    await vi.advanceTimersByTimeAsync(60_000);
    await waitFor(() => {
      expect(
        container.querySelector('[data-testid="cold-start-banner"]'),
      ).toBeNull();
    });
  });
});
