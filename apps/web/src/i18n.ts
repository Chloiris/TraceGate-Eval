import { createContext, createElement, useCallback, useContext, type ReactNode } from "react";

export type StudioLocale = "zh-CN" | "en-US";

const LocaleContext = createContext<StudioLocale>("zh-CN");

export function I18nProvider({ locale, children }: { locale: StudioLocale; children: ReactNode }) {
  return createElement(LocaleContext.Provider, { value: locale }, children);
}

export function useI18n() {
  const locale = useContext(LocaleContext);
  const text = useCallback((zhCN: string, enUS: string): string => (
    locale === "en-US" ? enUS : zhCN
  ), [locale]);
  return {
    locale,
    text,
  };
}
