import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";

import type { ActionDraftResponse } from "@/lib/apiClient";

import { ActionDraftGrid } from "./ActionDraftGrid";

// V1.2 §BZ vervolg: ``BulkSubmitBar`` gebruikt React Query; wrap
// alle renders zodat hooks een client vinden.
function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const HAPPY: ActionDraftResponse = {
  action_draft_id: "draft-1",
  decision_package_id: "dp-1",
  forecast_run_id: "fcst-1",
  created_at: "2026-05-26T07:00:00+00:00",
  created_by: "user",
  ibkr_account_id: "DU1234567",
  conid: "ASML.AS",
  symbol: "ASML",
  exchange: "AEB",
  currency_local: "EUR",
  side: "BUY",
  quantity: "6",
  order_type: "LMT",
  limit_price_local: "638.72000000",
  time_in_force: "DAY",
  notional_local: "3832.32000000",
  notional_eur: "3832.32000000",
  fx_rate_at_creation: "1",
  usable_cash_eur_at_creation: "50000",
  held_quantity_at_creation: null,
  status: "proposed",
  last_edited_at: null,
  user_approved_at: null,
  dismissed_at: null,
  deleted_at: null,
  dismissed_reason: null,
  user_note: null,
  superseded_by_decision_package_id: null,
  audit_trail_hash: "h-1",
  previous_draft_hash: null,
  safe_for_submission: false,
  submission_block_reason: null,
  submission_started_at: null,
  terminal_state_at: null,
};

vi.mock("@/lib/apiClient", async () => {
  const actual = (await vi.importActual("@/lib/apiClient")) as Record<string, unknown>;
  return {
    ...actual,
    apiClient: {
      approveActionDraft: vi.fn(),
      dismissActionDraft: vi.fn(),
      deleteActionDraft: vi.fn(),
      patchActionDraft: vi.fn(),
      submitActionDraftToPaper: vi.fn(),
      // V1.2 §BZ vervolg: ``BulkSubmitBar`` queries het IBKR
      // account-mode endpoint zodat de live-confirmation modal kan
      // weten of er extra waarschuwing nodig is. Default paper-mock
      // zodat bestaande tests onveranderd blijven.
      getIbkrAccountMode: vi.fn().mockResolvedValue({
        ok: true,
        data: {
          status: "ok",
          mode: "paper",
          display_label: "PAPER",
          expected_environment: "paper",
          help_nl: "",
          safe_for_orders: false,
          blocks_orders: true,
        },
      }),
    },
  };
});

import { apiClient } from "@/lib/apiClient";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ActionDraftGrid", () => {
  it("renders empty state when no drafts", () => {
    render(<ActionDraftGrid drafts={[]} onChange={() => {}} />);
    expect(screen.getByTestId("action-draft-grid-empty")).toBeTruthy();
  });

  it("renders one row per draft with symbol, side, quantity", () => {
    render(<ActionDraftGrid drafts={[HAPPY]} onChange={() => {}} />);
    expect(screen.getByText("ASML")).toBeTruthy();
    expect(screen.getByTestId("action-draft-side-draft-1").textContent).toBe(
      "BUY",
    );
    expect(screen.getByTestId("action-draft-quantity-draft-1").textContent).toBe(
      "6",
    );
  });

  it("shows superseded badge when superseded_by_decision_package_id is set", () => {
    render(
      <ActionDraftGrid
        drafts={[
          { ...HAPPY, superseded_by_decision_package_id: "dp-newer" },
        ]}
        onChange={() => {}}
      />,
    );
    expect(screen.getByTestId("action-draft-superseded-draft-1")).toBeTruthy();
    expect(
      screen.getByTestId("action-draft-superseded-draft-1").textContent,
    ).toContain("Advies gewijzigd");
  });

  // V1.2 §AT — drafts are grouped into the two operator stages.

  it("groups proposed drafts under Voorstellen and approved under Te verzenden", () => {
    render(
      <ActionDraftGrid
        drafts={[
          HAPPY,
          { ...HAPPY, action_draft_id: "draft-2", status: "user_approved" },
        ]}
        onChange={() => {}}
      />,
    );
    expect(
      screen.getByTestId("action-draft-stage-voorstellen"),
    ).toBeTruthy();
    expect(
      screen.getByTestId("action-draft-stage-te-verzenden"),
    ).toBeTruthy();
  });

  it("renders the approved-stage submit button when status is user_approved", () => {
    render(
      <ActionDraftGrid
        drafts={[{ ...HAPPY, status: "user_approved" }]}
        onChange={() => {}}
      />,
    );
    const banner = screen.getByTestId(
      "action-draft-approved-banner-draft-1",
    );
    expect(banner.textContent).toContain("klaar om te verzenden");
    expect(
      screen.getByTestId("action-draft-submit-to-paper-draft-1"),
    ).toBeTruthy();
  });

  // V1.2 §AT — approval via knop + modal (geen typen).

  it("approves via confirm modal Ja-button (no typing)", async () => {
    const onChange = vi.fn();
    (apiClient.approveActionDraft as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      data: { ...HAPPY, status: "user_approved" },
    });
    render(<ActionDraftGrid drafts={[HAPPY]} onChange={onChange} />);
    // Clicking Goedkeuren opens the modal — does NOT call the API yet.
    fireEvent.click(screen.getByTestId("action-draft-approve-draft-1"));
    expect(apiClient.approveActionDraft).not.toHaveBeenCalled();
    expect(
      screen.getByTestId("action-draft-approve-modal-draft-1"),
    ).toBeTruthy();
    // Confirm in the modal.
    fireEvent.click(
      screen.getByTestId("action-draft-approve-modal-draft-1-confirm"),
    );
    await waitFor(() => {
      expect(apiClient.approveActionDraft).toHaveBeenCalledWith("draft-1");
    });
    expect(onChange).toHaveBeenCalled();
  });

  it("does NOT approve when the modal is cancelled", async () => {
    const onChange = vi.fn();
    render(<ActionDraftGrid drafts={[HAPPY]} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("action-draft-approve-draft-1"));
    fireEvent.click(
      screen.getByTestId("action-draft-approve-modal-draft-1-cancel"),
    );
    expect(apiClient.approveActionDraft).not.toHaveBeenCalled();
    expect(onChange).not.toHaveBeenCalled();
  });

  // V1.2 §AT — submit via knop + modal (geen typen).

  it("submits via confirm modal Ja-button (no typing)", async () => {
    const onChange = vi.fn();
    (apiClient.submitActionDraftToPaper as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        data: {
          status: "submitted",
          status_nl: "Verzonden",
          help_nl: "",
          submission_id: "sub-1",
          state: "submitted",
          ibkr_order_id: 42,
          ibkr_perm_id: null,
          ibkr_status_text: null,
          blocking_reason: null,
          actions_allowed: false,
          order_submission_allowed: false,
          order_modification_allowed: false,
          order_cancellation_allowed: false,
          safe_for_submission: false,
          safe_for_orders: false,
          safe_for_broker_submission: false,
          blocks_orders: true,
        },
      });
    render(
      <ActionDraftGrid
        drafts={[{ ...HAPPY, status: "user_approved" }]}
        onChange={onChange}
      />,
    );
    fireEvent.click(
      screen.getByTestId("action-draft-submit-to-paper-draft-1"),
    );
    expect(apiClient.submitActionDraftToPaper).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByTestId("action-draft-submit-modal-draft-1-confirm"),
    );
    await waitFor(() => {
      expect(apiClient.submitActionDraftToPaper).toHaveBeenCalledWith(
        "draft-1",
      );
    });
    expect(onChange).toHaveBeenCalled();
  });

  it("surfaces blocking_reason from server response as inline error", async () => {
    const onChange = vi.fn();
    (apiClient.submitActionDraftToPaper as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        data: {
          status: "blocked",
          status_nl: "Geblokkeerd",
          help_nl: "Approval verlopen.",
          submission_id: null,
          state: null,
          ibkr_order_id: null,
          ibkr_perm_id: null,
          ibkr_status_text: null,
          blocking_reason: "approval_expired",
          actions_allowed: false,
          order_submission_allowed: false,
          order_modification_allowed: false,
          order_cancellation_allowed: false,
          safe_for_submission: false,
          safe_for_orders: false,
          safe_for_broker_submission: false,
          blocks_orders: true,
        },
      });
    render(
      <ActionDraftGrid
        drafts={[{ ...HAPPY, status: "user_approved" }]}
        onChange={onChange}
      />,
    );
    fireEvent.click(
      screen.getByTestId("action-draft-submit-to-paper-draft-1"),
    );
    fireEvent.click(
      screen.getByTestId("action-draft-submit-modal-draft-1-confirm"),
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("action-draft-error-draft-1").textContent,
      ).toContain("approval_expired");
    });
    expect(onChange).not.toHaveBeenCalled();
  });

  // V1.2 §AT — bulk submit.

  it("bulk-submits all approved drafts via modal", async () => {
    const onChange = vi.fn();
    (apiClient.submitActionDraftToPaper as ReturnType<typeof vi.fn>)
      .mockResolvedValue({
        ok: true,
        data: {
          status: "submitted",
          status_nl: "Verzonden",
          help_nl: "",
          submission_id: "sub",
          state: "submitted",
          ibkr_order_id: 1,
          ibkr_perm_id: null,
          ibkr_status_text: null,
          blocking_reason: null,
          actions_allowed: false,
          order_submission_allowed: false,
          order_modification_allowed: false,
          order_cancellation_allowed: false,
          safe_for_submission: false,
          safe_for_orders: false,
          safe_for_broker_submission: false,
          blocks_orders: true,
        },
      });
    render(
      <ActionDraftGrid
        drafts={[
          { ...HAPPY, action_draft_id: "draft-1", status: "user_approved" },
          { ...HAPPY, action_draft_id: "draft-2", status: "user_approved" },
        ]}
        onChange={onChange}
      />,
    );
    expect(
      screen.getByTestId("action-draft-bulk-submit-bar"),
    ).toBeTruthy();
    fireEvent.click(screen.getByTestId("action-draft-bulk-submit-button"));
    fireEvent.click(
      screen.getByTestId("action-draft-bulk-submit-modal-confirm"),
    );
    await waitFor(() => {
      expect(apiClient.submitActionDraftToPaper).toHaveBeenCalledTimes(2);
    });
    expect(apiClient.submitActionDraftToPaper).toHaveBeenCalledWith("draft-1");
    expect(apiClient.submitActionDraftToPaper).toHaveBeenCalledWith("draft-2");
    expect(onChange).toHaveBeenCalled();
  });

  it("shows extra LIVE warning in bulk-submit modal when account mode is live", async () => {
    // V1.2 §BZ vervolg: bij live-account moet de operator een
    // EXTRA waarschuwing zien voordat orders met echt geld de markt
    // raken. De banner + button label + modal copy passen zich aan.
    (apiClient.getIbkrAccountMode as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      data: {
        status: "ok",
        mode: "live",
        display_label: "LIVE",
        expected_environment: "live",
        detected_source: "connected_session",
        actual_account_id_masked: "U7•••4321",
        hint_account_id_masked: "U7•••4321",
        hint_mismatch: false,
        hint_mismatch_nl: null,
        help_nl: "",
        safe_for_orders: false,
        blocks_orders: true,
      },
    });
    render(
      <ActionDraftGrid
        drafts={[
          { ...HAPPY, action_draft_id: "draft-1", status: "user_approved" },
        ]}
        onChange={() => {}}
      />,
    );

    // Wacht tot de async query is opgelost zodat de UI is bijgewerkt.
    const button = await screen.findByTestId("action-draft-bulk-submit-button");
    await waitFor(() => {
      expect(button.getAttribute("data-account-mode")).toBe("live");
    });
    expect(button.textContent).toContain("LIVE");
    expect(button.textContent).toContain("⚠️");

    // Open de modal.
    fireEvent.click(button);

    // De live-warning block moet zichtbaar zijn met masked account-id
    // zodat de operator ziet TEGEN welk live-account hij gaat handelen.
    const warning = await screen.findByTestId(
      "action-draft-bulk-submit-live-warning",
    );
    expect(warning.textContent).toContain("LIVE");
    expect(warning.textContent).toContain("U7•••4321");
    expect(warning.textContent).toContain("ECHT geld");

    // Confirm-label benoemt LIVE expliciet.
    expect(
      screen.getByTestId("action-draft-bulk-submit-modal-confirm").textContent,
    ).toContain("LIVE");
  });

  it("does NOT show LIVE warning when account mode is paper", async () => {
    // Expliciete paper-mock — vi.clearAllMocks() reset alleen call-
    // history, niet de implementation, dus we zetten 'em hier weer.
    (apiClient.getIbkrAccountMode as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      data: {
        status: "ok",
        mode: "paper",
        display_label: "PAPER",
        expected_environment: "paper",
        help_nl: "",
        safe_for_orders: false,
        blocks_orders: true,
      },
    });
    render(
      <ActionDraftGrid
        drafts={[
          { ...HAPPY, action_draft_id: "draft-1", status: "user_approved" },
        ]}
        onChange={() => {}}
      />,
    );

    const button = await screen.findByTestId("action-draft-bulk-submit-button");
    await waitFor(() => {
      expect(button.getAttribute("data-account-mode")).toBe("paper");
    });
    expect(button.textContent).not.toContain("LIVE");

    fireEvent.click(button);

    // Live-warning block mag NIET aanwezig zijn.
    expect(
      screen.queryByTestId("action-draft-bulk-submit-live-warning"),
    ).toBeNull();
  });

  it("calls dismissActionDraft with reason when user enters one", async () => {
    const onChange = vi.fn();
    const promptSpy = vi
      .spyOn(window, "prompt")
      .mockReturnValue("wacht event");
    (apiClient.dismissActionDraft as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      data: { ...HAPPY, status: "dismissed", dismissed_reason: "wacht event" },
    });
    render(<ActionDraftGrid drafts={[HAPPY]} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("action-draft-dismiss-draft-1"));
    await waitFor(() => {
      expect(apiClient.dismissActionDraft).toHaveBeenCalledWith(
        "draft-1",
        "wacht event",
      );
    });
    promptSpy.mockRestore();
  });

  it("removes an approved draft from the list via Verwijder uit lijst", async () => {
    const onChange = vi.fn();
    (apiClient.deleteActionDraft as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      data: { ...HAPPY, status: "deleted" },
    });
    render(
      <ActionDraftGrid
        drafts={[{ ...HAPPY, status: "user_approved" }]}
        onChange={onChange}
      />,
    );
    fireEvent.click(
      screen.getByTestId("action-draft-remove-from-list-draft-1"),
    );
    await waitFor(() => {
      expect(apiClient.deleteActionDraft).toHaveBeenCalledWith("draft-1");
    });
  });

  it("opens edit form when Aanpassen is clicked", () => {
    render(<ActionDraftGrid drafts={[HAPPY]} onChange={() => {}} />);
    fireEvent.click(screen.getByTestId("action-draft-edit-draft-1"));
    expect(screen.getByTestId("action-draft-edit-form-draft-1")).toBeTruthy();
    expect(
      (screen.getByTestId("action-draft-edit-quantity-draft-1") as HTMLInputElement)
        .value,
    ).toBe("6");
  });

  // V1.2 §AV / CLAUDE.md §6.1 — EUR-equivalent transparency block.

  it("shows EUR-equivalent block on a BUY with notional_eur", () => {
    render(
      <ActionDraftGrid
        drafts={[{ ...HAPPY, notional_eur: "15000" }]}
        onChange={() => {}}
      />,
    );
    const block = screen.getByTestId("action-draft-eur-equivalent-draft-1");
    expect(block.textContent).toContain("+4");
    expect(block.textContent).toContain("TOB");
    // +4% on €15.000 = €600 gross, €495 net after 0,70% TOB.
    expect(
      screen.getByTestId("action-draft-eur-equivalent-net-draft-1").textContent,
    ).toMatch(/Netto €\s*495,00/);
  });

  it("hides the FX sensitivity block when currency_local is EUR", () => {
    render(
      <ActionDraftGrid
        drafts={[{ ...HAPPY, notional_eur: "15000" }]}
        onChange={() => {}}
      />,
    );
    expect(
      screen.queryByTestId("action-draft-fx-sensitivity-draft-1"),
    ).toBeNull();
  });

  it("shows three FX sensitivity rows for a non-EUR position", () => {
    render(
      <ActionDraftGrid
        drafts={[
          {
            ...HAPPY,
            currency_local: "USD",
            fx_rate_at_creation: "0.92",
            notional_eur: "10000",
          },
        ]}
        onChange={() => {}}
      />,
    );
    expect(
      screen.getByTestId("action-draft-fx-sensitivity-draft-1"),
    ).toBeTruthy();
    expect(
      screen.getByTestId("action-draft-fx-row-draft-1-0").textContent,
    ).toContain("Huidige koers");
    expect(
      screen.getByTestId("action-draft-fx-row-draft-1-2").textContent,
    ).toContain("zwakkere EUR");
  });

  it("does not render the EUR-equivalent block on SELL drafts", () => {
    render(
      <ActionDraftGrid
        drafts={[{ ...HAPPY, side: "SELL" }]}
        onChange={() => {}}
      />,
    );
    expect(
      screen.queryByTestId("action-draft-eur-equivalent-draft-1"),
    ).toBeNull();
  });
});
