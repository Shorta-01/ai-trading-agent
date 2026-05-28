import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

vi.mock("@/lib/apiClient", () => ({
  decisionPackagesExportUrl: () =>
    "http://api.test/decision-packages/export",
}));

import { ExportSuggestionsButton } from "./ExportSuggestionsButton";

afterEach(() => cleanup());

describe("ExportSuggestionsButton", () => {
  it("renders a download anchor pointing at the export endpoint", () => {
    render(<ExportSuggestionsButton />);
    const link = screen.getByTestId("export-suggestions-button");
    expect(link.tagName).toBe("A");
    expect(link.getAttribute("href")).toBe(
      "http://api.test/decision-packages/export",
    );
    // The download attribute hints the browser to save rather than navigate.
    expect(link.hasAttribute("download")).toBe(true);
    expect(link.textContent).toContain("Exporteer suggesties");
  });
});
