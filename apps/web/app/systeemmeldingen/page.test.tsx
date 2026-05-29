import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SystemEventSummary } from "@/lib/apiClient";

const getActiveSystemEvents = vi.fn();
const resolveSystemEvent = vi.fn();
const archiveSystemEvent = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getActiveSystemEvents: (...a: unknown[]) => getActiveSystemEvents(...a),
    resolveSystemEvent: (...a: unknown[]) => resolveSystemEvent(...a),
    archiveSystemEvent: (...a: unknown[]) => archiveSystemEvent(...a),
  },
}));

import SysteemmeldingenPage from "./page";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const _EVENT: SystemEventSummary = {
  system_event_id: "evt-1",
  severity: "warning",
  category: "ingest",
  source_service: "worker",
  source_component: "price-poller",
  event_code: "stale_price",
  title_nl: "Prijzen zijn verouderd",
  message_nl: "De laatste prijsupdate is te oud.",
  help_nl: "Controleer de marktdataverbinding.",
  created_at: "2026-05-28T10:00:00+00:00",
  blocks_suggestions: true,
  blocks_writes: false,
  blocks_ai_explanation: false,
  status: "open",
};

function ok<T>(data: T) {
  return Promise.resolve({ ok: true as const, data });
}

beforeEach(() => {
  getActiveSystemEvents.mockReset();
  resolveSystemEvent.mockReset();
  archiveSystemEvent.mockReset();
  Object.assign(navigator, {
    clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

afterEach(() => cleanup());

describe("SysteemmeldingenPage", () => {
  it("lists active system events with detail", async () => {
    getActiveSystemEvents.mockReturnValue(ok({ events: [_EVENT] }));
    render(<SysteemmeldingenPage />);
    expect(
      await screen.findByText("Prijzen zijn verouderd"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Actief: 1/)).toBeInTheDocument();
  });

  it("shows the empty hint when there are no active events", async () => {
    getActiveSystemEvents.mockReturnValue(ok({ events: [] }));
    render(<SysteemmeldingenPage />);
    expect(
      await screen.findByText("Geen actieve systeemmeldingen."),
    ).toBeInTheDocument();
  });

  it("shows the error hint when the API is unreachable", async () => {
    getActiveSystemEvents.mockReturnValue(
      Promise.resolve({ ok: false as const, reason: "not_reachable" }),
    );
    render(<SysteemmeldingenPage />);
    expect(
      await screen.findByText("Systeemmeldingen konden niet geladen worden."),
    ).toBeInTheDocument();
  });

  it("resolves an event and reloads", async () => {
    getActiveSystemEvents.mockReturnValue(ok({ events: [_EVENT] }));
    resolveSystemEvent.mockReturnValue(ok({ message_nl: "ok" }));
    render(<SysteemmeldingenPage />);
    await screen.findByText("Prijzen zijn verouderd");
    await userEvent.click(screen.getByText("Oplossen"));
    await waitFor(() =>
      expect(resolveSystemEvent).toHaveBeenCalledWith("evt-1", expect.anything()),
    );
    expect(getActiveSystemEvents).toHaveBeenCalledTimes(2); // initial + reload
  });

  it("copies the event details to the clipboard", async () => {
    getActiveSystemEvents.mockReturnValue(ok({ events: [_EVENT] }));
    render(<SysteemmeldingenPage />);
    await screen.findByText("Prijzen zijn verouderd");
    await userEvent.click(screen.getByText("Details kopiëren"));
    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1),
    );
    expect(screen.getByText("Details gekopieerd.")).toBeInTheDocument();
  });
});
