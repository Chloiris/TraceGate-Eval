# TraceGate site design system

## Brand direction

The site uses a precise developer-tool visual language: deep graphite and
navy-black surfaces, restrained teal and ice-blue signals, and violet or amber
only for workflow and risk meaning. It avoids customer-logo walls, invented
metrics, generic SaaS gradients, and decorative effects that compete with the
evidence story.

The core visual metaphor is a traceable chain:

`Repository → PR → Evidence → Finding → Patch Hash → Validation → Resolution`

## Tokens

Canonical variables are in `apps/site/src/styles/tokens.css`.

| Group | Purpose |
| --- | --- |
| `--bg-*` | page, soft, and elevated dark surfaces |
| `--surface*` | glass and card layers |
| `--text-*` | primary, secondary, and muted hierarchy |
| `--border*` | subtle and emphasized structural boundaries |
| `--accent*` | TraceGate teal and ice-blue signals |
| `--success`, `--warning`, `--danger` | status semantics, never the sole signal |
| `--violet` | controlled workflow emphasis |
| `--shadow-*`, `--radius-*` | consistent depth and geometry |
| `--space-*`, `--shell` | spacing rhythm and content width |

System fonts are used so the Chinese and English layouts remain stable without
remote font requests.

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

`prefers-reduced-motion` disables nonessential movement. Touch layouts simplify
the hero graph and convert dense grids into readable vertical structures.

## Breakpoints checked

The CSS supports 375/390/430px phones, 768px tablets, 1024px notebooks,
1440px desktops, and 1920px wide displays. Playwright asserts the 390px drawer;
browser and screenshot review cover the desktop and mobile compositions.
