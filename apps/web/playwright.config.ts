import { defineConfig, devices } from "@playwright/test";

/**
 * Task 126b: minimal Playwright smoke configuration.
 *
 * One browser (chromium) keeps CI fast. The dev server is started by
 * Playwright via ``next start`` against the production build that
 * the CI ``npm run build`` step produced — much faster + more
 * deterministic than ``next dev`` recompiling per request.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://127.0.0.1:3100",
    headless: true,
    trace: "off",
  },
  webServer: {
    command: "npm start -- -p 3100 -H 127.0.0.1",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: !process.env.CI,
    stdout: "pipe",
    stderr: "pipe",
    timeout: 120_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
