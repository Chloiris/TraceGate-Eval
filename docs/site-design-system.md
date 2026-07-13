# TraceGate site design system

## Brand direction

The site uses a precise developer-tool visual language in two intentionally
designed modes. Light is the first-visit default: cool ivory and mist-green
page fields, ink-green text, white elevated surfaces, structural teal, and
quiet ice-blue depth. Dark preserves the original graphite/green visual with
mint signals, glass panels, glow, and the same violet or amber workflow meaning.
Neither mode is an inversion of the other.

The core visual metaphor is a traceable chain:

`Repository → PR → Evidence → Finding → Patch Hash → Validation → Resolution`

## Tokens

Canonical variables are in `apps/site/src/styles/tokens.css`.

| Group | Purpose |
| --- | --- |
| `--color-page*` | page, secondary field, and deep browser backdrop |
| `--color-surface*` | cards, glass, elevated, muted, media, and code layers |
| `--color-text-*` | primary, secondary, muted, inverse, and accent text |
| `--color-border*`, `--color-divider` | structural boundaries |
| `--color-accent*`, `--color-secondary-accent` | TraceGate teal and ice-blue signals |
| `--color-success`, `--color-warning`, `--color-danger` | status semantics, never the sole signal |
| `--shadow-*`, `--hero-gradient`, `--card-gradient` | theme-specific light and depth |
| `--graph-*` | node, edge, risk, resolution, canvas, and event semantics |
| `--space-*`, `--shell` | spacing rhythm and content width |

System fonts are used so the Chinese and English layouts remain stable without
remote font requests.

Components do not branch into duplicate light/dark DOM. Theme values are
selected by `data-theme` at the root and consumed through semantic variables.
The storage key is `tracegate-site-theme`, with only `light` and `dark` valid.
`public/theme-init.js` applies it before React and CSS; storage errors or invalid
values fall back to light. `ThemeProvider` keeps `theme-color` and native
`color-scheme` synchronized after interaction.

## Components and motion

- Navigation becomes a glass layer after scrolling and collapses to a
  keyboard-accessible drawer on mobile.
- The hero graph is lightweight DOM/SVG with CSS transforms, pulsing paths,
  pointer response, reduced-motion support, and page-visibility pausing.
- Workflow state transitions use Motion; below-fold code is split from the
  critical rendering path.
- Cards use restrained border illumination and do not require hover to reveal
  essential information.
- Gallery images use responsive AVIF/WebP sources, explicit provenance, lazy
  loading, and an Escape-closeable dialog.
- The header theme control is keyboard-operable, exposes the destination theme
  in Chinese or English, and leaves the drawer/dialog state untouched.

`prefers-reduced-motion` disables nonessential movement. Touch layouts simplify
the hero graph and convert dense grids into readable vertical structures.

## Breakpoints checked

The CSS supports 375/390/430px phones, 768px tablets, 1024px notebooks,
1440px desktops, and 1920px wide displays. Playwright asserts the 390px drawer;
browser and screenshot review cover the desktop and mobile compositions.

Run `pnpm site:test`, `pnpm site:test:e2e`, and `pnpm site:lighthouse` after any
token or component change. Capture mode generates paired light/dark desktop,
Autofix, mobile-home, and mobile-drawer evidence in `docs/site-screenshots/`.
