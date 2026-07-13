import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

class IntersectionObserverMock implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "0px";
  readonly thresholds = [0];
  disconnect = vi.fn();
  observe = vi.fn();
  takeRecords = vi.fn(() => []);
  unobserve = vi.fn();
}

beforeEach(() => {
  if (typeof window === "undefined") return;
  window.localStorage.clear();
  document.documentElement.dataset.theme = "light";
  document.documentElement.style.colorScheme = "light";
  document.documentElement.classList.remove("theme-ready");
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  vi.stubGlobal("IntersectionObserver", IntersectionObserverMock);
});

afterEach(() => {
  if (typeof window !== "undefined") cleanup();
  vi.unstubAllGlobals();
});
