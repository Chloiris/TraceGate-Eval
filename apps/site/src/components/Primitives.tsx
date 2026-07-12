import type { CSSProperties, ReactNode } from "react";

import { imageSources } from "../data/gallery";

export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <span className={`brand ${compact ? "brand--compact" : ""}`} aria-label="TraceGate Studio">
      <svg className="brand__mark" viewBox="0 0 64 64" aria-hidden="true">
        <defs>
          <linearGradient id="brand-gradient" x1="8" y1="4" x2="56" y2="60">
            <stop stopColor="#67f6c4" />
            <stop offset="1" stopColor="#84b8ff" />
          </linearGradient>
        </defs>
        <path d="M32 5 56 18v28L32 59 8 46V18L32 5Z" fill="url(#brand-gradient)" />
        <path d="M19 20h26v9h-9v24h-8V29h-9v-9Z" fill="#07100f" />
      </svg>
      <span className="brand__type">
        <strong>TraceGate</strong>
        {!compact && <small>STUDIO · LOCAL</small>}
      </span>
    </span>
  );
}

export function ArrowIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="M4 10h11M11 6l4 4-4 4" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function GithubIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path fill="currentColor" d="M12 2C6.48 2 2 6.6 2 12.27c0 4.53 2.87 8.37 6.84 9.73.5.1.68-.22.68-.49 0-.24-.01-1.05-.01-1.9-2.78.62-3.37-1.21-3.37-1.21-.45-1.18-1.11-1.49-1.11-1.49-.91-.64.07-.63.07-.63 1 .07 1.53 1.06 1.53 1.06.9 1.57 2.34 1.12 2.91.86.09-.66.35-1.12.64-1.37-2.22-.26-4.56-1.14-4.56-5.08 0-1.12.39-2.04 1.03-2.76-.1-.26-.45-1.3.1-2.72 0 0 .84-.27 2.75 1.05A9.38 9.38 0 0 1 12 7.01a9.4 9.4 0 0 1 2.5.34c1.91-1.32 2.75-1.05 2.75-1.05.55 1.42.2 2.46.1 2.72.64.72 1.03 1.64 1.03 2.76 0 3.95-2.35 4.82-4.58 5.08.36.32.68.95.68 1.92 0 1.38-.01 2.49-.01 2.83 0 .27.18.59.69.49A10.26 10.26 0 0 0 22 12.27C22 6.6 17.52 2 12 2Z" />
    </svg>
  );
}

export function Reveal({ children, className = "", delay = 0 }: { children: ReactNode; className?: string; delay?: number }) {
  return (
    <div className={`reveal ${className}`} style={{ "--reveal-delay": `${delay}s` } as CSSProperties}>
      {children}
    </div>
  );
}

export function SectionHeader({ eyebrow, title, body, align = "left" }: { eyebrow: string; title: string; body: string; align?: "left" | "center" }) {
  return (
    <Reveal className={`section-header section-header--${align}`}>
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      <p>{body}</p>
    </Reveal>
  );
}

export function ProductPicture({ id, alt, priority = false, sizes = "(max-width: 760px) 94vw, 700px", className = "" }: { id: string; alt: string; priority?: boolean; sizes?: string; className?: string }) {
  const sources = imageSources(id);
  return (
    <picture className={className}>
      <source type="image/avif" srcSet={sources.avif} sizes={sizes} />
      <source type="image/webp" srcSet={sources.webp} sizes={sizes} />
      <img src={sources.fallback} alt={alt} loading={priority ? "eager" : "lazy"} decoding="async" fetchPriority={priority ? "high" : "auto"} />
    </picture>
  );
}

export function GlowCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  const style = { "--pointer-x": "50%", "--pointer-y": "50%" } as CSSProperties;
  return (
    <div
      className={`glow-card ${className}`}
      style={style}
      onPointerMove={(event) => {
        const bounds = event.currentTarget.getBoundingClientRect();
        event.currentTarget.style.setProperty("--pointer-x", `${event.clientX - bounds.left}px`);
        event.currentTarget.style.setProperty("--pointer-y", `${event.clientY - bounds.top}px`);
      }}
    >
      {children}
    </div>
  );
}

export function StatusDot({ tone = "success" }: { tone?: "success" | "warning" | "danger" }) {
  return <span className={`status-dot status-dot--${tone}`} aria-hidden="true" />;
}
