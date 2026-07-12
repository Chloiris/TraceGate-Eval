import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";

const token = "tracegate-playwright-token-0123456789-abcdef";
const databasePath = resolve("build/e2e/studio.db");
const workspacePath = resolve("build/e2e/workspace");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    {
      name: "chrome",
      use: { ...devices["Desktop Chrome"], channel: "chrome" },
    },
  ],
  webServer: [
    {
      command: [
        `.venv/bin/python scripts/prepare_studio_e2e.py --database '${databasePath}' --workspace '${workspacePath}'`,
        `TRACEGATE_LOCAL_API_TOKEN='${token}' TRACEGATE_DATABASE_URL='sqlite+pysqlite:///${databasePath}' TRACEGATE_DATA_DIR='${resolve("build/e2e/data")}' .venv/bin/python -m tracegate.studio.cli serve --port 8876 --log-level warning`,
      ].join(" && "),
      url: "http://127.0.0.1:8876/api/v1/health",
      timeout: 30_000,
      reuseExistingServer: false,
    },
    {
      command: `VITE_TRACEGATE_API_TOKEN='${token}' TRACEGATE_DEV_API_TARGET='http://127.0.0.1:8876' pnpm --filter @tracegate/web dev`,
      url: "http://127.0.0.1:5173",
      timeout: 30_000,
      reuseExistingServer: false,
    },
  ],
});
