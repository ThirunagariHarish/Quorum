import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: process.env.PW_BASE_URL ?? "http://localhost:8000",
    extraHTTPHeaders: {
      Accept: "application/json",
    },
  },
  reporter: [["list"], ["html", { open: "never", outputFolder: "docs/qa/playwright-report" }]],
});
