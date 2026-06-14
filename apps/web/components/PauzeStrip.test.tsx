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

import type { PauzeStatusResponse } from "@/lib/apiClient";

const getPauzeStatus = vi.fn();
const postPauze = vi.fn();
const postHervat = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getPauzeStatus: (...a: unknown[]) => getPauzeStatus(...a),
    postPauze: (...a: unknown[]) => postPauze(...a),
    postHervat: (...a: unknown[]) => postHervat(...a),
  },
}));

import { PauzeStrip } from "./PauzeStrip";

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

function makeStatus(
  overrides: Partial<PauzeStatusResponse> = {},
): PauzeStatusResponse {
  return {
    title_nl: "Pauze-modus",
    help_nl: "help",
    paused: false,
    paused_at: null,
    summary_nl: "Software draait.",
    ...overrides,
  };
}

beforeEach(() => {
  getPauzeStatus.mockReset();
  postPauze.mockReset();
  postHervat.mockReset();
});

afterEach(() => cleanup());

describe("PauzeStrip", () => {
  it("renders a blue 'draaiend' strip when not paused", async () => {
    getPauzeStatus.mockResolvedValue({
      ok: true as const,
      data: makeStatus(),
    });
    render(<PauzeStrip />);
    await waitFor(() => {
      expect(
        screen.getByTestId("pauze-strip").getAttribute("data-paused"),
      ).toBe("false");
    });
    expect(screen.getByTestId("pauze-strip-badge").textContent).toBe(
      "Draaiend",
    );
    expect(screen.getByTestId("pauze-strip-button").textContent).toBe(
      "Pauzeer",
    );
  });

  it("renders an orange 'gepauzeerd' strip with since-timestamp", async () => {
    getPauzeStatus.mockResolvedValue({
      ok: true as const,
      data: makeStatus({
        paused: true,
        paused_at: "2026-06-13T20:00:00+00:00",
        summary_nl: "Software gepauzeerd.",
      }),
    });
    render(<PauzeStrip />);
    await waitFor(() => {
      expect(
        screen.getByTestId("pauze-strip").getAttribute("data-paused"),
      ).toBe("true");
    });
    expect(screen.getByTestId("pauze-strip-badge").textContent).toBe(
      "Gepauzeerd",
    );
    expect(screen.getByTestId("pauze-strip-button").textContent).toBe(
      "Hervat",
    );
    expect(
      screen.getByTestId("pauze-strip-summary").textContent,
    ).toMatch(/13\/06\/2026/);
  });

  it("opens the confirm modal before calling POST /pauze", async () => {
    getPauzeStatus.mockResolvedValue({
      ok: true as const,
      data: makeStatus(),
    });
    render(<PauzeStrip />);
    await screen.findByTestId("pauze-strip-button");
    fireEvent.click(screen.getByTestId("pauze-strip-button"));
    expect(
      await screen.findByTestId("pauze-confirm-modal"),
    ).toBeInTheDocument();
    expect(postPauze).not.toHaveBeenCalled();
  });

  it("calls POST /pauze when the modal's confirm button is clicked", async () => {
    getPauzeStatus.mockResolvedValue({
      ok: true as const,
      data: makeStatus(),
    });
    postPauze.mockResolvedValue({
      ok: true as const,
      data: makeStatus({
        paused: true,
        paused_at: "2026-06-13T20:00:00+00:00",
      }),
    });
    render(<PauzeStrip />);
    await screen.findByTestId("pauze-strip-button");
    fireEvent.click(screen.getByTestId("pauze-strip-button"));
    fireEvent.click(
      await screen.findByTestId("pauze-confirm-modal-confirm"),
    );
    await waitFor(() => {
      expect(postPauze).toHaveBeenCalledTimes(1);
    });
  });

  it("calls POST /pauze/hervat when the modal's confirm button is clicked while paused", async () => {
    getPauzeStatus.mockResolvedValue({
      ok: true as const,
      data: makeStatus({
        paused: true,
        paused_at: "2026-06-13T20:00:00+00:00",
      }),
    });
    postHervat.mockResolvedValue({
      ok: true as const,
      data: makeStatus(),
    });
    render(<PauzeStrip />);
    await waitFor(() => {
      expect(screen.getByTestId("pauze-strip-button").textContent).toBe(
        "Hervat",
      );
    });
    fireEvent.click(screen.getByTestId("pauze-strip-button"));
    fireEvent.click(
      await screen.findByTestId("pauze-confirm-modal-confirm"),
    );
    await waitFor(() => {
      expect(postHervat).toHaveBeenCalledTimes(1);
    });
  });

  it("does not call POST when the modal is cancelled", async () => {
    getPauzeStatus.mockResolvedValue({
      ok: true as const,
      data: makeStatus(),
    });
    render(<PauzeStrip />);
    await screen.findByTestId("pauze-strip-button");
    fireEvent.click(screen.getByTestId("pauze-strip-button"));
    fireEvent.click(
      await screen.findByTestId("pauze-confirm-modal-cancel"),
    );
    expect(postPauze).not.toHaveBeenCalled();
  });

  it("falls back to a draaiend strip when the API errors", async () => {
    getPauzeStatus.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    render(<PauzeStrip />);
    const strip = await screen.findByTestId("pauze-strip");
    expect(strip.getAttribute("data-paused")).toBe("false");
  });
});
