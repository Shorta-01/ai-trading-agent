import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { ConfirmModal } from "./ConfirmModal";

afterEach(() => cleanup());

describe("ConfirmModal", () => {
  it("renders nothing when open is false", () => {
    const { container } = render(
      <ConfirmModal
        open={false}
        title="X"
        body="Y"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders title + body when open", () => {
    render(
      <ConfirmModal
        open
        title="Order goedkeuren?"
        body="Detail tekst"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(screen.getByTestId("confirm-modal").textContent).toContain(
      "Order goedkeuren?",
    );
    expect(screen.getByTestId("confirm-modal").textContent).toContain(
      "Detail tekst",
    );
  });

  it("calls onConfirm when the confirm button is clicked", () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmModal
        open
        title="X"
        body="Y"
        onConfirm={onConfirm}
        onCancel={() => {}}
      />,
    );
    fireEvent.click(screen.getByTestId("confirm-modal-confirm"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when the cancel button is clicked", () => {
    const onCancel = vi.fn();
    render(
      <ConfirmModal
        open
        title="X"
        body="Y"
        onConfirm={() => {}}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByTestId("confirm-modal-cancel"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when the overlay is clicked", () => {
    const onCancel = vi.fn();
    render(
      <ConfirmModal
        open
        title="X"
        body="Y"
        onConfirm={() => {}}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByTestId("confirm-modal-overlay"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("does not call onCancel when the dialog body is clicked", () => {
    const onCancel = vi.fn();
    render(
      <ConfirmModal
        open
        title="X"
        body="Y"
        onConfirm={() => {}}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByTestId("confirm-modal"));
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("disables buttons and shows Bezig when busy", () => {
    render(
      <ConfirmModal
        open
        busy
        title="X"
        body="Y"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    const confirm = screen.getByTestId(
      "confirm-modal-confirm",
    ) as HTMLButtonElement;
    expect(confirm.disabled).toBe(true);
    expect(confirm.textContent).toContain("Bezig");
  });

  it("supports a custom testId for multiple modals on one page", () => {
    render(
      <ConfirmModal
        open
        testId="my-modal"
        title="X"
        body="Y"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(screen.getByTestId("my-modal")).toBeTruthy();
    expect(screen.getByTestId("my-modal-confirm")).toBeTruthy();
  });
});
