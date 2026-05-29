import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { IbkrSubmissionLifecycleEvent } from "@/lib/apiClient";

vi.mock("@/lib/apiClient", async () => {
  const actual = (await vi.importActual("@/lib/apiClient")) as Record<
    string,
    unknown
  >;
  return {
    ...actual,
    apiClient: {
      getIbkrSubmissionLifecycle: vi.fn(),
    },
  };
});

import { apiClient } from "@/lib/apiClient";

import { SubmissionLifecycleDrawer } from "./SubmissionLifecycleDrawer";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const SAMPLE_EVENTS: IbkrSubmissionLifecycleEvent[] = [
  {
    id: 1,
    action_draft_id: "draft-1",
    event_at: "2026-05-26T10:00:00+00:00",
    ibkr_perm_id: 100100,
    event_type: "status_change",
    from_status: "submitted",
    to_status: "accepted",
    ibkr_raw_status: "Submitted",
    fill_price_local: null,
    fill_quantity: null,
    commission: null,
    commission_currency: null,
    raw_callback_json: {},
  },
  {
    id: 2,
    action_draft_id: "draft-1",
    event_at: "2026-05-26T10:00:02+00:00",
    ibkr_perm_id: 100100,
    event_type: "status_change",
    from_status: "accepted",
    to_status: "working",
    ibkr_raw_status: "PreSubmitted",
    fill_price_local: null,
    fill_quantity: null,
    commission: null,
    commission_currency: null,
    raw_callback_json: {},
  },
  {
    id: 3,
    action_draft_id: "draft-1",
    event_at: "2026-05-26T10:00:05+00:00",
    ibkr_perm_id: 100100,
    event_type: "fill",
    from_status: "working",
    to_status: "filled",
    ibkr_raw_status: null,
    fill_price_local: "638.72",
    fill_quantity: "6",
    commission: null,
    commission_currency: null,
    raw_callback_json: {},
  },
  {
    id: 4,
    action_draft_id: "draft-1",
    event_at: "2026-05-26T10:00:07+00:00",
    ibkr_perm_id: 100100,
    event_type: "commission_report",
    from_status: null,
    to_status: null,
    ibkr_raw_status: null,
    fill_price_local: null,
    fill_quantity: null,
    commission: "1.50",
    commission_currency: "EUR",
    raw_callback_json: {},
  },
];

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SubmissionLifecycleDrawer", () => {
  it("does not render when closed", () => {
    render(
      <SubmissionLifecycleDrawer
        actionDraftId={null}
        open={false}
        onClose={() => {}}
      />,
    );
    expect(
      screen.queryByTestId("submission-lifecycle-drawer"),
    ).toBeNull();
  });

  it("fetches and renders events in Dutch when opened", async () => {
    (
      apiClient.getIbkrSubmissionLifecycle as ReturnType<typeof vi.fn>
    ).mockResolvedValueOnce({
      ok: true,
      data: { action_draft_id: "draft-1", events: SAMPLE_EVENTS },
    });
    render(
      <SubmissionLifecycleDrawer
        actionDraftId="draft-1"
        open={true}
        onClose={() => {}}
      />,
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("submission-lifecycle-events"),
      ).toBeTruthy();
    });
    // Status change events labeled in Dutch.
    expect(screen.getAllByText("Statuswijziging").length).toBeGreaterThan(
      0,
    );
    expect(screen.getByText("Uitvoering")).toBeTruthy();
    // "Commissie" appears both as the event label and the dt label.
    expect(screen.getAllByText("Commissie").length).toBeGreaterThan(0);
    // Status mapped to Dutch.
    expect(screen.getAllByText("Verstuurd").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Uitgevoerd").length).toBeGreaterThan(0);
    expect(apiClient.getIbkrSubmissionLifecycle).toHaveBeenCalledWith(
      "draft-1",
    );
  });

  it("renders empty state when there are no events yet", async () => {
    (
      apiClient.getIbkrSubmissionLifecycle as ReturnType<typeof vi.fn>
    ).mockResolvedValueOnce({
      ok: true,
      data: { action_draft_id: "draft-1", events: [] },
    });
    render(
      <SubmissionLifecycleDrawer
        actionDraftId="draft-1"
        open={true}
        onClose={() => {}}
      />,
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("submission-lifecycle-empty"),
      ).toBeTruthy();
    });
  });

  it("renders an error banner when fetch fails", async () => {
    (
      apiClient.getIbkrSubmissionLifecycle as ReturnType<typeof vi.fn>
    ).mockResolvedValueOnce({ ok: false, reason: "not_reachable" });
    render(
      <SubmissionLifecycleDrawer
        actionDraftId="draft-1"
        open={true}
        onClose={() => {}}
      />,
    );
    await waitFor(() => {
      expect(
        screen.getByText(/Lifecycle kon niet worden geladen/i),
      ).toBeTruthy();
    });
  });
});
