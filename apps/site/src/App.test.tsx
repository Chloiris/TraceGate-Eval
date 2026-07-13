import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import App from "./App";
import { HeroGraph } from "./components/Hero";
import { LanguageProvider } from "./i18n";
import { ThemeProvider } from "./theme";

function renderApp() {
  return render(<ThemeProvider><LanguageProvider><App /></LanguageProvider></ThemeProvider>);
}

describe("TraceGate marketing site", () => {
  test("switches languages without a reload and remembers the choice", async () => {
    renderApp();
    expect(screen.getByRole("heading", { name: /审查有证据/ })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "EN" }));
    expect(await screen.findByRole("heading", { name: /Review with evidence/ })).toBeVisible();
    expect(document.documentElement.lang).toBe("en");
    expect(window.localStorage.getItem("tracegate-site-language")).toBe("en");
  });

  test("exposes all primary navigation anchors", async () => {
    renderApp();
    await waitFor(() => {
      for (const href of ["#product", "#autofix", "#intelligence", "#evidence", "#architecture", "#verification"]) {
        expect(document.querySelector(`a[href="${href}"]`)).toBeInTheDocument();
        expect(document.querySelector(href)).toBeInTheDocument();
      }
    });
  });

  test("uses real GitHub links for the primary CTA", () => {
    renderApp();
    const links = screen.getAllByRole("link", { name: /GitHub|TraceGate/ });
    expect(links.some((link) => link.getAttribute("href") === "https://github.com/Chloiris/TraceGate-Eval")).toBe(true);
  });

  test("renders the honest verification boundary", async () => {
    renderApp();
    expect((await screen.findAllByText("VERIFIED IN CI")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("BLOCKED").length).toBe(2);
    expect(screen.getByText(/VERIFIED_WINDOWS_CI 不等于/)).toBeVisible();
  });

  test("opens the mobile navigation through an accessible control", () => {
    renderApp();
    const menu = screen.getByRole("button", { name: "打开导航" });
    expect(menu).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "true");
    expect(document.querySelector(".site-nav__links--open")).toBeInTheDocument();
  });

  test("reduces the animated hero graph when the preference is enabled", () => {
    vi.mocked(window.matchMedia).mockImplementation((query: string) => ({
      matches: query.includes("prefers-reduced-motion"),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    const { container } = render(<HeroGraph />);
    expect(container.querySelector(".hero-graph")).toHaveAttribute("data-reduced-motion", "true");
  });
});
