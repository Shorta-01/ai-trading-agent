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

import type { ProfitTargetResponse } from "@/lib/apiClient";

const getProfitTarget = vi.fn();
const putProfitTarget = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getProfitTarget: (...a: unknown[]) => getProfitTarget(...a),
    putProfitTarget: (...a: unknown[]) => putProfitTarget(...a),
  },
}));

import { ProfitTargetSetting } from "./ProfitTargetSetting";

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

function makeResp(
  overrides: Partial<ProfitTargetResponse> = {},
): ProfitTargetResponse {
  return {
    title_nl: "Winstdoel per trade",
    help_nl: "help",
    profit_target_pct: "4",
    is_doctrine_default: true,
    summary_nl: "Doctrine-default 4 % actief.",
    ...overrides,
  };
}

beforeEach(() => {
  getProfitTarget.mockReset();
  putProfitTarget.mockReset();
});

afterEach(() => cleanup());

describe("ProfitTargetSetting", () => {
  it("renders the current target and summary", async () => {
    getProfitTarget.mockResolvedValue({ ok: true as const, data: makeResp() });
    render(<ProfitTargetSetting />);
    await waitFor(() => {
      expect(
        screen.getByTestId("profit-target-summary").textContent,
      ).toContain("Doctrine-default");
    });
    expect(
      (screen.getByTestId("profit-target-input") as HTMLInputElement).value,
    ).toBe("4");
  });

  it("saves the entered value via PUT", async () => {
    getProfitTarget.mockResolvedValue({ ok: true as const, data: makeResp() });
    putProfitTarget.mockResolvedValue({
      ok: true as const,
      data: makeResp({
        profit_target_pct: "5.5",
        is_doctrine_default: false,
        summary_nl: "Operator-keuze 5.5 %.",
      }),
    });
    render(<ProfitTargetSetting />);
    await waitFor(() => {
      expect(
        (screen.getByTestId("profit-target-input") as HTMLInputElement).value,
      ).toBe("4");
    });
    fireEvent.change(screen.getByTestId("profit-target-input"), {
      target: { value: "5.5" },
    });
    fireEvent.click(screen.getByTestId("profit-target-save"));
    await waitFor(() => {
      expect(putProfitTarget).toHaveBeenCalledWith({
        profit_target_pct: "5.5",
      });
    });
  });

  it("resets to doctrine-default via reset button", async () => {
    getProfitTarget.mockResolvedValue({
      ok: true as const,
      data: makeResp({
        profit_target_pct: "6",
        is_doctrine_default: false,
        summary_nl: "Operator-keuze 6 %.",
      }),
    });
    putProfitTarget.mockResolvedValue({ ok: true as const, data: makeResp() });
    render(<ProfitTargetSetting />);
    await screen.findByTestId("profit-target-summary");
    fireEvent.click(screen.getByTestId("profit-target-reset"));
    await waitFor(() => {
      expect(putProfitTarget).toHaveBeenCalledWith({
        profit_target_pct: null,
      });
    });
  });

  it("shows an error when the mutation fails", async () => {
    getProfitTarget.mockResolvedValue({ ok: true as const, data: makeResp() });
    putProfitTarget.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    render(<ProfitTargetSetting />);
    await screen.findByTestId("profit-target-summary");
    fireEvent.click(screen.getByTestId("profit-target-save"));
    expect(
      await screen.findByTestId("profit-target-error"),
    ).toHaveTextContent("mislukt");
  });
});
