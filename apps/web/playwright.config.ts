import { defineConfig, devices } from "@playwright/test";

/**
 * Task 126b: minimal Playwright smoke configuration.
 *
 * One browser (chromium) keeps CI fast. The dev server is started by
 * Playwright; the test mocks every API call via ``page.route()`` so
 * no live API is required.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:3100",
    headless: true,
    trace: "off",
  },
  webServer: {
    command: "npm run dev -- --port 3100",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: !process.env.CI,
    stdout: "ignore",
    stderr: "pipe",
    timeout: 60_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
