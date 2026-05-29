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

import type { ErrorLogItem } from "@/lib/apiClient";

const getErrors = vi.fn();
const resolveError = vi.fn();
const deleteError = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getErrors: (...a: unknown[]) => getErrors(...a),
    resolveError: (...a: unknown[]) => resolveError(...a),
    deleteError: (...a: unknown[]) => deleteError(...a),
  },
}));

import { toClaudeCodeText } from "@/lib/errorCopy";

import ErrorsPage from "./page";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const _ITEM: ErrorLogItem = {
  system_event_id: "err-1",
  created_at: "2026-05-28T10:00:00+00:00",
  severity: "error",
  category: "runtime_error",
  source_service: "api",
  source_component: "/action-draft",
  event_code: "unhandled_exception",
  title_nl: "Onverwachte serverfout",
  message_nl: "ValueError: boom",
  technical_summary: "ValueError: boom",
  stack_trace_redacted: "Traceback (most recent call last): ... ValueError: boom",
  redacted_details_json: { path: "/action-draft" },
  status: "open",
};

function ok<T>(data: T) {
  return Promise.resolve({ ok: true as const, data });
}

beforeEach(() => {
  getErrors.mockReset();
  resolveError.mockReset();
  deleteError.mockReset();
  Object.assign(navigator, {
    clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

afterEach(() => cleanup());

describe("toClaudeCodeText", () => {
  it("includes the message, stacktrace and context", () => {
    const text = toClaudeCodeText(_ITEM);
    expect(text).toContain("ValueError: boom");
    expect(text).toContain("stacktrace:");
    expect(text).toContain("Traceback");
    expect(text).toContain('"path": "/action-draft"');
  });
});

describe("ErrorsPage", () => {
  it("lists open errors with detail", async () => {
    getErrors.mockReturnValue(ok({ open_count: 1, errors: [_ITEM] }));
    render(<ErrorsPage />);
    expect(await screen.findByText("Onverwachte serverfout")).toBeInTheDocument();
    expect(screen.getByText(/Openstaande fouten: 1/)).toBeInTheDocument();
  });

  it("copies the full error description to the clipboard", async () => {
    getErrors.mockReturnValue(ok({ open_count: 1, errors: [_ITEM] }));
    render(<ErrorsPage />);
    await screen.findByText("Onverwachte serverfout");
    await userEvent.click(screen.getByText("Kopieer voor Claude Code"));
    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        toClaudeCodeText(_ITEM),
      ),
    );
    expect(screen.getByTestId("error-action-status")).toHaveTextContent(
      "gekopieerd",
    );
  });

  it("resolves an error and reloads", async () => {
    getErrors.mockReturnValue(ok({ open_count: 1, errors: [_ITEM] }));
    resolveError.mockReturnValue(ok({ message_nl: "ok" }));
    render(<ErrorsPage />);
    await screen.findByText("Onverwachte serverfout");
    await userEvent.click(screen.getByText("Oplossen"));
    await waitFor(() => expect(resolveError).toHaveBeenCalledWith("err-1"));
    expect(getErrors).toHaveBeenCalledTimes(2); // initial + reload
  });

  it("deletes an error and reloads", async () => {
    getErrors.mockReturnValue(ok({ open_count: 1, errors: [_ITEM] }));
    deleteError.mockReturnValue(ok({ message_nl: "ok" }));
    render(<ErrorsPage />);
    await screen.findByText("Onverwachte serverfout");
    await userEvent.click(screen.getByText("Verwijderen"));
    await waitFor(() => expect(deleteError).toHaveBeenCalledWith("err-1"));
  });
});
