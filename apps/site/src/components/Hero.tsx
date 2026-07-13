import type { CSSProperties } from "react";
import { useEffect, useRef, useState } from "react";

import { copy, useLanguage } from "../i18n";
import { ArrowIcon, GithubIcon, ProductPicture, StatusDot } from "./Primitives";

const nodes = [
  { id: "repo", label: "Repository", x: 12, y: 18, tone: "neutral" },
  { id: "pr", label: "PR #17", x: 39, y: 9, tone: "blue" },
  { id: "evidence", label: "Evidence", x: 63, y: 22, tone: "teal" },
  { id: "finding", label: "Finding", x: 75, y: 47, tone: "amber" },
  { id: "patch", label: "Patch Hash", x: 53, y: 68, tone: "violet" },
  { id: "validation", label: "Validation", x: 25, y: 75, tone: "blue" },
  { id: "resolved", label: "RESOLVED", x: 12, y: 48, tone: "teal" },
] as const;

const paths = [
  "M90 120 C170 30 260 45 330 78",
  "M360 78 C430 75 455 125 500 150",
  "M525 165 C590 190 600 245 610 285",
  "M600 310 C570 370 510 405 455 430",
  "M430 445 C340 490 265 485 210 465",
  "M180 455 C105 415 82 350 92 310",
  "M100 275 C80 220 72 170 90 120",
] as const;

function usePageVisible() {
  const [visible, setVisible] = useState(!document.hidden);
  useEffect(() => {
    const update = () => setVisible(!document.hidden);
    document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);
  return visible;
}

function usePrefersReducedMotion() {
  const query = "(prefers-reduced-motion: reduce)";
  const [reduced, setReduced] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const media = window.matchMedia(query);
    const update = () => setReduced(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return reduced;
}

export function HeroGraph() {
  const reduced = usePrefersReducedMotion();
  const visible = usePageVisible();
  const graphRef = useRef<HTMLDivElement>(null);

  return (
    <div
      ref={graphRef}
      className="hero-graph"
      data-reduced-motion={reduced ? "true" : "false"}
      data-paused={!visible ? "true" : "false"}
      onPointerMove={(event) => {
        if (reduced || window.innerWidth < 760) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        const x = (event.clientX - bounds.left) / bounds.width - 0.5;
        const y = (event.clientY - bounds.top) / bounds.height - 0.5;
        event.currentTarget.style.setProperty("--graph-x", `${x * 8}deg`);
        event.currentTarget.style.setProperty("--graph-y", `${y * -7}deg`);
      }}
      onPointerLeave={(event) => {
        event.currentTarget.style.setProperty("--graph-x", "0deg");
        event.currentTarget.style.setProperty("--graph-y", "0deg");
      }}
    >
      <div className="hero-graph__chrome">
        <span><StatusDot /> Live trace</span>
        <span className="mono">HEAD 74e4577</span>
      </div>
      <div className="hero-graph__field">
        <svg viewBox="0 0 700 540" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="path-gradient" x1="0" y1="0" x2="1" y2="1">
              <stop stopColor="var(--color-accent)" />
              <stop offset=".55" stopColor="var(--color-secondary-accent)" />
              <stop offset="1" stopColor="var(--color-violet)" />
            </linearGradient>
            <filter id="line-glow"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
          </defs>
          {paths.map((path, index) => (
            <g key={path}>
              <path className="graph-path graph-path--ghost" d={path} />
              <path className="graph-path graph-path--pulse" d={path} style={{ animationDelay: `${index * -0.55}s` }} />
            </g>
          ))}
        </svg>
        {nodes.map((node, index) => (
          <div
            key={node.id}
            className={`graph-node graph-node--${node.tone}`}
            style={{
              left: `${node.x}%`,
              top: `${node.y}%`,
              "--float-offset": `${index % 2 === 0 ? -5 : 5}px`,
              "--float-duration": `${5 + index * 0.25}s`,
            } as CSSProperties}
          >
            <span className="graph-node__index">0{index + 1}</span>
            <strong>{node.label}</strong>
            {node.id === "finding" && <span className="graph-node__signal">risk</span>}
          </div>
        ))}
        <div className="graph-event graph-event--tool"><small>TOOL CALL</small><strong>read_file</strong><span>42 ms</span></div>
        <div className="graph-event graph-event--hash"><small>PATCH</small><strong>sha256:e009…</strong><span>confirmed</span></div>
      </div>
      <div className="hero-graph__footer">
        <span className="mono">Evidence → Finding → Fix → Verify</span>
        <span className="graph-live"><StatusDot /> observable</span>
      </div>
    </div>
  );
}

export function Hero() {
  const { language } = useLanguage();
  const text = copy[language].hero;

  return (
    <section id="top" className="hero" aria-labelledby="hero-title">
      <div className="hero__ambient" aria-hidden="true" />
      <div className="hero__grid shell">
        <div className="hero__copy">
          <p className="eyebrow hero-rise hero-rise--1">{text.eyebrow}</p>
          <h1 id="hero-title">
            <span className="hero-rise hero-rise--2">{text.titleA}</span>
            <span className="accent-text hero-rise hero-rise--3">{text.titleB}</span>
          </h1>
          <p className="hero__body hero-rise hero-rise--4">{text.body}</p>
          <div className="hero__actions hero-rise hero-rise--5">
            <a className="button button--primary" href="#product"><span>{text.primary}</span><ArrowIcon /></a>
            <a className="button button--secondary" href="https://github.com/Chloiris/TraceGate-Eval" target="_blank" rel="noreferrer"><GithubIcon /><span>{text.secondary}</span></a>
            <a className="text-link" href="#architecture">{text.architecture}<ArrowIcon /></a>
          </div>
          <div className="hero__meta hero-rise hero-rise--6">
            <span><StatusDot /> {text.preview}</span>
            <span className="mono">{text.status}</span>
          </div>
        </div>
        <div className="hero__visual hero-visual-enter" aria-label={text.graphLabel}>
          <HeroGraph />
        </div>
      </div>
      <div className="hero__product-peek shell" aria-label="TraceGate Studio PR Diff preview">
        <div className="product-window product-window--hero">
          <div className="product-window__bar"><span /><span /><span /><small>TraceGate Studio · PR #17 · Files & Diff</small></div>
          <ProductPicture id="pr-diff" alt="TraceGate Studio PR Diff running in a Playwright repository fixture" priority sizes="(max-width: 760px) 96vw, 1100px" />
        </div>
      </div>
    </section>
  );
}
