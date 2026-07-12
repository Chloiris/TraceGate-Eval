import { useEffect, useState } from "react";

import { copy, useLanguage } from "../i18n";
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

  return (
    <header className={`site-nav ${scrolled ? "site-nav--scrolled" : ""}`}>
      <div className="site-nav__inner">
        <a href="#top" className="site-nav__brand" aria-label="TraceGate Studio home" onClick={() => setOpen(false)}>
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
