import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const screenshotRoot = resolve("../../docs/site-screenshots");
const capture = process.env.TRACEGATE_SITE_CAPTURE === "1";

test.beforeAll(async () => {
  if (capture) await mkdir(screenshotRoot, { recursive: true });
});

async function setTheme(page: Page, theme: "light" | "dark") {
  const current = await page.locator("html").getAttribute("data-theme");
  if (current !== theme) {
    const label = theme === "dark" ? "切换到夜间模式" : "切换到日间模式";
    await page.getByRole("button", { name: label }).click();
  }
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
}

test("defaults to light even when the OS preference is dark and captures both desktop homes", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("TraceGate Studio — Evidence-grounded AI Coding Agent");
  await expect(page.getByRole("heading", { name: /审查有证据/ })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(page.getByRole("button", { name: "切换到夜间模式" })).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByText("Windows preview verified in CI")).toBeVisible();
  if (capture) {
    await page.waitForTimeout(700);
    await page.screenshot({ path: resolve(screenshotRoot, "light-desktop-1440-home.png") });
  }

  await setTheme(page, "dark");
  await expect(page.getByRole("button", { name: "切换到日间模式" })).toHaveAttribute("aria-pressed", "true");
  if (capture) {
    await page.waitForTimeout(300);
    await page.screenshot({ path: resolve(screenshotRoot, "dark-desktop-1440-home.png") });
  }
});

test("persists both explicit theme choices across reloads", async ({ page }) => {
  await page.goto("/");
  await setTheme(page, "dark");
  expect(await page.evaluate(() => localStorage.getItem("tracegate-site-theme"))).toBe("dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  await setTheme(page, "light");
  expect(await page.evaluate(() => localStorage.getItem("tracegate-site-theme"))).toBe("light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("keeps language and theme choices independent", async ({ page }) => {
  await page.goto("/");
  await setTheme(page, "dark");
  await page.getByRole("button", { name: "EN", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Review with evidence/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Switch to light mode" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  expect(await page.evaluate(() => localStorage.getItem("tracegate-site-language"))).toBe("en");
});

test("captures both Autofix themes with all eleven observable states", async ({ page }) => {
  await page.goto("/#autofix");
  const section = page.locator("#autofix");
  await expect(section.getByRole("tab")).toHaveCount(11);
  await section.getByRole("tab", { name: /06.*AWAIT_USER_CONFIRMATION/ }).click();
  await expect(section.getByText("User Confirmation", { exact: true })).toBeVisible();
  await section.locator(".autofix__transaction").scrollIntoViewIfNeeded();
  await page.evaluate(() => {
    (document.activeElement as HTMLElement | null)?.blur();
    window.scrollBy(0, -88);
  });
  if (capture) {
    await page.waitForTimeout(350);
    await page.screenshot({ path: resolve(screenshotRoot, "light-desktop-autofix.png") });
  }
  await setTheme(page, "dark");
  if (capture) {
    await page.waitForTimeout(250);
    await page.screenshot({ path: resolve(screenshotRoot, "dark-desktop-autofix.png") });
  }
});

test("keeps the mobile menu open while switching and captures both mobile themes", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  if (capture) {
    await page.waitForTimeout(600);
    await page.screenshot({ path: resolve(screenshotRoot, "light-mobile-390-home.png") });
  }

  const menu = page.locator(".menu-button");
  await expect(menu).toHaveAccessibleName("打开导航");
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("link", { name: "受控修复" })).toBeVisible();
  if (capture) {
    await page.waitForTimeout(300);
    await page.screenshot({ path: resolve(screenshotRoot, "light-mobile-navigation.png") });
  }

  await setTheme(page, "dark");
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  if (capture) {
    await page.waitForTimeout(300);
    await page.screenshot({ path: resolve(screenshotRoot, "dark-mobile-navigation.png") });
  }
  await page.keyboard.press("Escape");
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  if (capture) {
    await page.waitForTimeout(250);
    await page.screenshot({ path: resolve(screenshotRoot, "dark-mobile-390-home.png") });
  }
});

test("keeps the gallery lightbox open and readable across both themes", async ({ page }) => {
  await page.goto("/#evidence");
  const gallery = page.locator("#evidence");
  await gallery.getByRole("button", { name: /系统概览/ }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("真实本地运行")).toBeVisible();
  await page.getByRole("button", { name: "切换到夜间模式" }).evaluate((button) => (button as HTMLButtonElement).click());
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(dialog).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
});

test("keeps every required breakpoint within the viewport in both themes", async ({ page }) => {
  for (const viewport of [
    { width: 375, height: 812 },
    { width: 390, height: 844 },
    { width: 430, height: 932 },
    { width: 768, height: 1024 },
    { width: 1024, height: 768 },
    { width: 1440, height: 900 },
    { width: 1920, height: 1080 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /审查有证据/ })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await setTheme(page, "dark");
    await expectNoHorizontalOverflow(page);
    await page.evaluate(() => localStorage.removeItem("tracegate-site-theme"));
  }
});

test("reduces theme and graph motion when the user requests it", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const durationSeconds = await page.locator(".theme-toggle").evaluate((button) => Number.parseFloat(getComputedStyle(button).transitionDuration));
  expect(durationSeconds).toBeLessThanOrEqual(0.00001);
  await setTheme(page, "dark");
  await expect(page.locator(".hero-graph")).toHaveAttribute("data-reduced-motion", "true");
});

test("uses real GitHub links and resolves every internal anchor", async ({ page }) => {
  await page.goto("/");
  const links = page.locator('a[href="https://github.com/Chloiris/TraceGate-Eval"]');
  await expect(links).toHaveCount(3);
  for (const link of await links.all()) await expect(link).toHaveAttribute("target", "_blank");

  const hrefs = await page.locator('a[href^="#"]').evaluateAll((anchors) => [...new Set(anchors.map((anchor) => anchor.getAttribute("href")).filter(Boolean))] as string[]);
  expect(hrefs.length).toBeGreaterThanOrEqual(7);
  for (const href of hrefs) await expect(page.locator(href)).toHaveCount(1);
});

test("loads both themes without console errors or missing static resources", async ({ page }) => {
  const errors: string[] = [];
  const failed: string[] = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => {
    if (response.status() >= 400 && new URL(response.url()).origin === new URL(page.url()).origin) failed.push(`${response.status()} ${response.url()}`);
  });
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
  await setTheme(page, "dark");
  await page.locator("#top").scrollIntoViewIfNeeded();
  expect(errors).toEqual([]);
  expect(failed).toEqual([]);
});
