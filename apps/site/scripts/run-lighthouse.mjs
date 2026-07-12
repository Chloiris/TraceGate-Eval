import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { spawn } from "node:child_process";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { launch } from "chrome-launcher";
import lighthouse from "lighthouse";
import desktopConfig from "lighthouse/core/config/desktop-config.js";

const url = process.env.TRACEGATE_SITE_URL ?? "http://127.0.0.1:4174";
const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = resolve(here, "..");
const repositoryRoot = resolve(siteRoot, "../..");
const reportRoot = resolve(repositoryRoot, "build/site-lighthouse");
await mkdir(reportRoot, { recursive: true });

const preview = url.includes("127.0.0.1:4174")
  ? spawn("pnpm", ["preview"], { cwd: siteRoot, stdio: "ignore", detached: true })
  : null;

async function waitForPage() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // Preview is still starting.
    }
    await new Promise((resolveWait) => setTimeout(resolveWait, 250));
  }
  throw new Error(`Preview did not become ready at ${url}`);
}

let chrome;
try {
  await waitForPage();
  chrome = await launch({ chromeFlags: ["--headless=new", "--no-sandbox"] });
  const result = await lighthouse(url, {
    port: chrome.port,
    output: ["json", "html"],
    onlyCategories: ["performance", "accessibility", "best-practices", "seo"],
  }, desktopConfig);
  if (!result) throw new Error("Lighthouse returned no result");
  const outputs = Array.isArray(result.report) ? result.report : [result.report];
  await writeFile(resolve(reportRoot, "report.json"), outputs[0] ?? "", "utf8");
  await writeFile(resolve(reportRoot, "report.html"), outputs[1] ?? "", "utf8");

  const scores = Object.fromEntries(
    Object.entries(result.lhr.categories).map(([key, value]) => [key, Math.round((value.score ?? 0) * 100)]),
  );
  console.log(JSON.stringify(scores));
  const thresholds = { performance: 90, accessibility: 95, "best-practices": 95, seo: 95 };
  const failures = Object.entries(thresholds).filter(([key, threshold]) => (scores[key] ?? 0) < threshold);
  if (failures.length > 0) {
    throw new Error(`Lighthouse thresholds missed: ${failures.map(([key, threshold]) => `${key}<${threshold}`).join(", ")}`);
  }
} finally {
  await chrome?.kill();
  if (preview?.pid) process.kill(-preview.pid, "SIGTERM");
}
