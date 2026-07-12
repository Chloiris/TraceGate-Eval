import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";

const remoteBaseUrl = process.env.TRACEGATE_SITE_BASE_URL;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: resolve("../../build/site-playwright-report") }]],
  use: {
    baseURL: remoteBaseUrl ?? "http://127.0.0.1:4174",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    colorScheme: "dark",
  },
  projects: [
    { name: "desktop-chrome", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
  ],
  ...(remoteBaseUrl ? {} : {
    webServer: {
      command: "pnpm build && pnpm preview",
      url: "http://127.0.0.1:4174",
      timeout: 60_000,
      reuseExistingServer: false,
    },
  }),
});
