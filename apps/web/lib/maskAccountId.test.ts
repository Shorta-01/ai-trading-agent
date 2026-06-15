import { describe, expect, it } from "vitest";

import { maskAccountId } from "./maskAccountId";

describe("maskAccountId", () => {
  it("masks a typical paper IBKR account-id with DU prefix", () => {
    expect(maskAccountId("DU1234567")).toBe("DU•••4567");
  });

  it("masks a typical live IBKR account-id with U prefix", () => {
    expect(maskAccountId("U7654321")).toBe("U7•••4321");
  });

  it("returns null for null input", () => {
    expect(maskAccountId(null)).toBeNull();
  });

  it("returns null for undefined input", () => {
    expect(maskAccountId(undefined)).toBeNull();
  });

  it("returns null for empty string", () => {
    expect(maskAccountId("")).toBeNull();
  });

  it("returns null for whitespace-only input", () => {
    expect(maskAccountId("   ")).toBeNull();
  });

  it("leaves short IDs (<= 6 chars) unchanged", () => {
    expect(maskAccountId("DU1234")).toBe("DU1234");
    expect(maskAccountId("ABC")).toBe("ABC");
  });

  it("matches API-side mask_account_id semantics for prefix + suffix", () => {
    // Same algorithm as apps/api/.../ibkr_connection_read_model.py
    // mask_account_id — keeps 2-char prefix + 4-char suffix.
    expect(maskAccountId("DF9876543")).toBe("DF•••6543");
  });
});
