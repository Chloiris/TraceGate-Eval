import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import App from "./App";
import { LanguageProvider } from "./i18n";
import { ThemeProvider } from "./theme";
import { THEME_STORAGE_KEY } from "./theme-core";

function renderThemedApp() {
  return render(
    <ThemeProvider>
      <LanguageProvider>
        <App />
      </LanguageProvider>
    </ThemeProvider>,
  );
}

function resetInitializedTheme() {
  delete document.documentElement.dataset.theme;
  document.documentElement.style.colorScheme = "";
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("TraceGate site themes", () => {
  test("defaults a new visitor to light without consulting the OS theme", async () => {
    resetInitializedTheme();
    vi.mocked(window.matchMedia).mockImplementation((query: string) => ({
      matches: query.includes("prefers-color-scheme: dark"),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    renderThemedApp();
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
    expect(screen.getByRole("button", { name: "切换到夜间模式" })).toHaveAttribute("aria-pressed", "false");
  });

  test.each(["light", "dark"] as const)("loads a stored %s theme", async (theme) => {
    resetInitializedTheme();
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    renderThemedApp();
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe(theme));
  });

  test("falls back to light for an invalid stored value", async () => {
    resetInitializedTheme();
    window.localStorage.setItem(THEME_STORAGE_KEY, "system");
    renderThemedApp();
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
  });

  test("switches in both directions, updates browser chrome, and persists", async () => {
    resetInitializedTheme();
    const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]') ?? document.head.appendChild(document.createElement("meta"));
    meta.setAttribute("name", "theme-color");
    renderThemedApp();

    fireEvent.click(screen.getByRole("button", { name: "切换到夜间模式" }));
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("dark"));
    expect(document.documentElement.style.colorScheme).toBe("dark");
    expect(meta.content).toBe("#07100f");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(screen.getByRole("button", { name: "切换到日间模式" })).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(screen.getByRole("button", { name: "切换到日间模式" }));
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
    expect(document.documentElement.style.colorScheme).toBe("light");
    expect(meta.content).toBe("#f2f7f4");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
  });

  test("uses the correct English accessible labels", async () => {
    renderThemedApp();
    fireEvent.click(screen.getByRole("button", { name: "EN" }));
    expect(await screen.findByRole("button", { name: "Switch to dark mode" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Switch to dark mode" }));
    expect(await screen.findByRole("button", { name: "Switch to light mode" })).toBeVisible();
  });

  test("keeps the mobile navigation open while the theme changes", () => {
    renderThemedApp();
    const menu = screen.getByRole("button", { name: "打开导航" });
    fireEvent.click(menu);
    fireEvent.click(screen.getByRole("button", { name: "切换到夜间模式" }));
    expect(menu).toHaveAttribute("aria-expanded", "true");
    expect(document.querySelector(".site-nav__links--open")).toBeInTheDocument();
  });

  test("continues rendering when localStorage access throws", async () => {
    resetInitializedTheme();
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new DOMException("blocked"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new DOMException("blocked"); });
    renderThemedApp();
    expect(screen.getByRole("heading", { name: /审查有证据/ })).toBeVisible();
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
  });
});
