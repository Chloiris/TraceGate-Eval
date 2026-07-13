import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { ThemeContext } from "./theme-context";
import { applyTheme, isTheme, readStoredTheme, THEME_STORAGE_KEY } from "./theme-core";
import type { Theme } from "./theme-core";

function initialTheme(): Theme {
  const initialized = document.documentElement.dataset.theme;
  return isTheme(initialized) ? initialized : readStoredTheme();
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    applyTheme(theme);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // The theme still works for this session when storage is unavailable.
    }
    document.documentElement.classList.add("theme-ready");
  }, [theme]);

  const value = useMemo(() => ({
    theme,
    setTheme,
    toggleTheme: () => setTheme((current) => current === "light" ? "dark" : "light"),
  }), [theme]);

  return <ThemeContext value={value}>{children}</ThemeContext>;
}
