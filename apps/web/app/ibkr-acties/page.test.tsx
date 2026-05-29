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

import type { ActionDraftResponse } from "@/lib/apiClient";

const getActionDraftsTeKeuren = vi.fn();
const getIbkrSubmissionActive = vi.fn();
const getIbkrSubmissionHistoriek = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getActionDraftsTeKeuren: (...a: unknown[]) => getActionDraftsTeKeuren(...a),
    getIbkrSubmissionActive: (...a: unknown[]) => getIbkrSubmissionActive(...a),
    getIbkrSubmissionHistoriek: (...a: unknown[]) =>
      getIbkrSubmissionHistoriek(...a),
  },
}));

vi.mock("@/components/ActionDraftGrid", () => ({
  ActionDraftGrid: ({ drafts }: { drafts: ActionDraftResponse[] }) => (
    <div data-testid="te-keuren-grid">te-keuren:{drafts.length}</div>
  ),
}));
vi.mock("@/components/IbkrSubmissionGrids", () => ({
  ActiefBijIbkrGrid: ({ drafts }: { drafts: ActionDraftResponse[] }) => (
    <div data-testid="actief-grid">actief:{drafts.length}</div>
  ),
  HistoriekGrid: ({ drafts }: { drafts: ActionDraftResponse[] }) => (
    <div data-testid="historiek-grid">historiek:{drafts.length}</div>
  ),
}));
vi.mock("@/components/SubmissionLifecycleDrawer", () => ({
  SubmissionLifecycleDrawer: () => null,
}));
vi.mock("@/components/ExportSuggestionsButton", () => ({
  ExportSuggestionsButton: () => null,
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

function ok(n: number) {
  return Promise.resolve({
    ok: true as const,
    data: {
      drafts: Array.from(
        { length: n },
        (_, i) => ({ action_draft_id: `d${i}` }) as ActionDraftResponse,
      ),
    },
  });
}
function fail() {
  return Promise.resolve({ ok: false as const, reason: "not_reachable" });
}

beforeEach(() => {
  getActionDraftsTeKeuren.mockReset();
  getIbkrSubmissionActive.mockReset();
  getIbkrSubmissionHistoriek.mockReset();
});
afterEach(() => cleanup());

describe("IBKR Acties page", () => {
  it("loads the Te keuren tab by default", async () => {
    getActionDraftsTeKeuren.mockReturnValue(ok(2));
    render(<Page />);
    expect(await screen.findByTestId("te-keuren-grid")).toHaveTextContent(
      "te-keuren:2",
    );
    expect(getActionDraftsTeKeuren).toHaveBeenCalledTimes(1);
    expect(getIbkrSubmissionActive).not.toHaveBeenCalled();
  });

  it("loads the Actief tab only when selected", async () => {
    getActionDraftsTeKeuren.mockReturnValue(ok(0));
    getIbkrSubmissionActive.mockReturnValue(ok(3));
    render(<Page />);
    await screen.findByTestId("te-keuren-grid");
    await userEvent.click(screen.getByTestId("ibkr-acties-tab-actief"));
    expect(await screen.findByTestId("actief-grid")).toHaveTextContent(
      "actief:3",
    );
  });

  it("shows the error banner when a tab's load fails", async () => {
    getActionDraftsTeKeuren.mockReturnValue(fail());
    render(<Page />);
    expect(
      await screen.findByText(/Actiedrafts konden niet worden geladen/),
    ).toBeInTheDocument();
  });

  it("shows the loading hint before data arrives", async () => {
    getActionDraftsTeKeuren.mockReturnValue(ok(1));
    render(<Page />);
    expect(screen.getByText("Bezig met laden…")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId("te-keuren-grid")).toBeInTheDocument(),
    );
  });
});
