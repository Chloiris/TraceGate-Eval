import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const screenshotRoot = resolve("../../docs/site-screenshots");
const capture = process.env.TRACEGATE_SITE_CAPTURE === "1";

test.beforeAll(async () => {
  if (capture) await mkdir(screenshotRoot, { recursive: true });
});

test("renders the Chinese desktop home", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("TraceGate Studio — Evidence-grounded AI Coding Agent");
  await expect(page.getByRole("heading", { name: /审查有证据/ })).toBeVisible();
  await expect(page.getByText("Windows preview verified in CI")).toBeVisible();
  if (capture) {
    await page.waitForTimeout(900);
    await page.screenshot({ path: resolve(screenshotRoot, "desktop-1440-home.png") });
  }
});

test("switches to English without refreshing", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "EN", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Review with evidence/ })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  expect(await page.evaluate(() => localStorage.getItem("tracegate-site-language"))).toBe("en");
});

test("opens a keyboard-accessible mobile navigation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const menu = page.locator(".menu-button");
  await expect(menu).toHaveAccessibleName("打开导航");
  if (capture) {
    await page.waitForTimeout(900);
    await page.screenshot({ path: resolve(screenshotRoot, "mobile-390-home.png") });
  }
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("link", { name: "受控修复" })).toBeVisible();
  if (capture) {
    await page.waitForTimeout(300);
    await page.screenshot({ path: resolve(screenshotRoot, "mobile-navigation.png") });
  }
  await page.keyboard.press("Escape");
  await expect(menu).toHaveAttribute("aria-expanded", "false");
});

test("keeps every required responsive breakpoint within the viewport", async ({ page }) => {
  for (const viewport of [
    { width: 375, height: 812 },
    { width: 430, height: 932 },
    { width: 768, height: 1024 },
    { width: 1024, height: 768 },
    { width: 1440, height: 900 },
    { width: 1920, height: 1080 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /审查有证据/ })).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
  }
});

test("exposes all eleven Autofix nodes and captures the transaction", async ({ page }) => {
  await page.goto("/#autofix");
  const section = page.locator("#autofix");
  await expect(section.getByRole("tab")).toHaveCount(11);
  await expect(section.getByText("AWAIT_USER_CONFIRMATION", { exact: true })).toBeVisible();
  await section.getByRole("tab", { name: /06.*AWAIT_USER_CONFIRMATION/ }).click();
  await expect(section.getByText("User Confirmation", { exact: true })).toBeVisible();
  if (capture) {
    await page.waitForTimeout(350);
    await section.screenshot({ path: resolve(screenshotRoot, "desktop-autofix.png") });
  }
});

test("opens and closes the gallery lightbox", async ({ page }) => {
  await page.goto("/#evidence");
  const gallery = page.locator("#evidence");
  await gallery.getByRole("button", { name: /放大查看: 系统概览/ }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog").getByText("真实本地运行")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  if (capture) {
    await page.waitForTimeout(400);
    await page.screenshot({ path: resolve(screenshotRoot, "desktop-gallery.png") });
  }
});

test("uses the real GitHub repository for every primary CTA", async ({ page }) => {
  await page.goto("/");
  const links = page.locator('a[href="https://github.com/Chloiris/TraceGate-Eval"]');
  await expect(links).toHaveCount(3);
  for (const link of await links.all()) await expect(link).toHaveAttribute("target", "_blank");
});

test("resolves every internal anchor", async ({ page }) => {
  await page.goto("/");
  const hrefs = await page.locator('a[href^="#"]').evaluateAll((links) => [...new Set(links.map((link) => link.getAttribute("href")).filter(Boolean))] as string[]);
  expect(hrefs.length).toBeGreaterThanOrEqual(7);
  for (const href of hrefs) await expect(page.locator(href)).toHaveCount(1);
});

test("loads without console errors or missing static resources", async ({ page }) => {
  const errors: string[] = [];
  const failed: string[] = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => { if (response.status() >= 400 && new URL(response.url()).origin === new URL(page.url()).origin) failed.push(`${response.status()} ${response.url()}`); });
  await page.goto("/");
  await page.locator("#verification").scrollIntoViewIfNeeded();
  const galleryImages = page.locator("#evidence img");
  await expect(galleryImages).toHaveCount(15);
  for (let index = 0; index < await galleryImages.count(); index += 1) {
    const current = galleryImages.nth(index);
    await current.scrollIntoViewIfNeeded();
    await expect(current).toHaveJSProperty("complete", true);
    expect(await current.evaluate((image) => (image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  }
  expect(errors).toEqual([]);
  expect(failed).toEqual([]);
});
