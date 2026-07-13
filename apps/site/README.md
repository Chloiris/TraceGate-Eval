# TraceGate Studio marketing site

`apps/site` is the bilingual, static product site for TraceGate Studio. It is
separate from the Studio application in `apps/web` and does not alter the
desktop product or FastAPI Sidecar.

## Stack

- React 19 and strict TypeScript
- Vite static build
- Motion for workflow state transitions; CSS/SVG for the lightweight hero graph
- Vitest and React Testing Library
- Playwright for desktop, language, mobile navigation, Autofix, gallery, links,
  resources, both themes, persistence, and screenshot acceptance
- Sharp for AVIF/WebP asset variants
- Lighthouse desktop CI-style thresholds

## Theme system

The first visit always starts in the independently designed light theme; it
does not follow the operating-system preference. The header toggle switches
between `light` and `dark` without navigation, preserves the current language,
scroll position, mobile drawer, and gallery state, and stores only one of those
two values under `tracegate-site-theme`.

`public/theme-init.js` runs synchronously in the document head before the React
entry and its imported CSS. It safely reads the stored value, falls back to
`light`, and sets `document.documentElement.dataset.theme` plus
`color-scheme`, preventing a light-to-dark or dark-to-light first-paint flash.
It is a same-origin external script, so the production CSP remains
`script-src 'self'` without `unsafe-inline`. React then owns changes through
`ThemeProvider`, including the matching `theme-color` meta value.

Canonical semantic tokens live in `src/styles/tokens.css`. New components must
use the `--color-*`, `--shadow-*`, gradient, and graph tokens rather than
hard-coded dark surfaces. Theme transitions are limited to color, background,
border, shadow, opacity, and the small icon transform; reduced-motion users get
near-instant changes through the global media query.

## Commands

From the repository root:

```bash
pnpm install --frozen-lockfile
pnpm site:dev
pnpm site:lint
pnpm site:typecheck
pnpm site:test
pnpm site:assets
pnpm site:build
pnpm site:preview
pnpm site:test:e2e
pnpm site:lighthouse
```

The production output is `apps/site/dist`. `pnpm site:deploy` uploads that
directory only after the local build and remote preflight checks succeed.

## Content and assets

Project counts are generated at build time from `docs/project-facts.yaml` by
`scripts/generate-project-facts.mjs`. Do not edit the generated TypeScript or
JSON copies. Product screenshot metadata and provenance live in
`src/data/gallery.ts`; generated AVIF/WebP files live under
`public/media/product`.

When product UI changes:

1. Run the existing Studio Playwright suite with
   `TRACEGATE_CAPTURE_SITE_PRODUCT=1` to refresh local fixture captures.
2. Run `pnpm site:assets` to regenerate bounded responsive images.
3. Review every crop and its evidence label.
4. Run the complete site validation commands above.

See [design system](../../docs/site-design-system.md),
[content boundaries](../../docs/site-content-boundaries.md), and
[deployment](../../docs/site-deployment.md).
