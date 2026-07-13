import { useEffect, useState } from "react";

import { copy, useLanguage } from "../i18n";
import { useTheme } from "../theme-context";
import { BrandMark, GithubIcon } from "./Primitives";

const sections = ["product", "autofix", "intelligence", "evidence", "architecture", "verification"] as const;

function useActiveSection() {
  const [active, setActive] = useState("product");
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        const first = visible[0];
        if (first?.target.id) setActive(first.target.id);
      },
      { rootMargin: "-20% 0px -60%", threshold: [0.05, 0.25, 0.5] },
    );
    for (const id of sections) {
      const element = document.getElementById(id);
      if (element) observer.observe(element);
    }
    return () => observer.disconnect();
  }, []);
  return active;
}

export function Navigation() {
  const { language, setLanguage } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const text = copy[language].nav;
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const active = useActiveSection();

  useEffect(() => {
    const update = () => setScrolled(window.scrollY > 24);
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  const items = [
    ["product", text.product],
    ["autofix", text.autofix],
    ["intelligence", text.intelligence],
    ["evidence", text.evidence],
    ["architecture", text.architecture],
    ["verification", text.verification],
  ] as const;
  const themeLabel = theme === "light" ? text.switchToDark : text.switchToLight;

  return (
    <header className={`site-nav ${scrolled ? "site-nav--scrolled" : ""}`}>
      <div className="site-nav__inner">
        <a href="#top" className="site-nav__brand" title="TraceGate Studio home" onClick={() => setOpen(false)}>
          <BrandMark />
        </a>
        <nav className={`site-nav__links ${open ? "site-nav__links--open" : ""}`} aria-label="Primary navigation">
          {items.map(([id, label]) => (
            <a key={id} href={`#${id}`} aria-current={active === id ? "location" : undefined} onClick={() => setOpen(false)}>
              <span>{label}</span>
            </a>
          ))}
          <a className="site-nav__github" href="https://github.com/Chloiris/TraceGate-Eval" target="_blank" rel="noreferrer">
            <GithubIcon />
            <span>{text.github}</span>
          </a>
        </nav>
        <div className="site-nav__actions">
          <button
            className="theme-toggle"
            type="button"
            aria-label={themeLabel}
            aria-pressed={theme === "dark"}
            title={themeLabel}
            onClick={toggleTheme}
          >
            <span className="theme-toggle__icon theme-toggle__icon--moon" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path d="M20.3 15.3A8.5 8.5 0 0 1 8.7 3.7 8.5 8.5 0 1 0 20.3 15.3Z" /></svg>
            </span>
            <span className="theme-toggle__icon theme-toggle__icon--sun" aria-hidden="true">
              <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3.4" /><path d="M12 2v2.2M12 19.8V22M4.9 4.9l1.6 1.6M17.5 17.5l1.6 1.6M2 12h2.2M19.8 12H22M4.9 19.1l1.6-1.6M17.5 6.5l1.6-1.6" /></svg>
            </span>
          </button>
          <div className="language-switch" role="group" aria-label="Language">
            <button type="button" aria-pressed={language === "zh"} onClick={() => setLanguage("zh")}>中</button>
            <button type="button" aria-pressed={language === "en"} onClick={() => setLanguage("en")}>EN</button>
          </div>
          <button className="menu-button" type="button" aria-label={open ? text.close : text.menu} aria-expanded={open} onClick={() => setOpen((value) => !value)}>
            <span />
            <span />
          </button>
        </div>
      </div>
    </header>
  );
}
