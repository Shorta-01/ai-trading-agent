import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  test: {
    environment: "jsdom",
    globals: false,
    include: [
      "components/**/*.test.tsx",
      "lib/**/*.test.ts",
      "app/**/*.test.tsx",
    ],
    exclude: ["tests/e2e/**", "node_modules/**", ".next/**"],
    setupFiles: ["./vitest.setup.ts"],
  },
});
