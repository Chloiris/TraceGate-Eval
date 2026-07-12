# ADR-002: bounded deterministic graph layout

- Status: Accepted
- Date: 2026-07-10
- Decision owners: TraceGate maintainers

## Context

The original Studio architecture selected React Flow with ELK.js for automatic
layout. The first production build put ELK in a lazy Repository Map chunk that
was 1,445.36 kB minified (441.12 kB gzip). The persisted graph currently has
only `contains`, `import`, and `call` relationships and the UI already limits a
single view to 800 nodes. Shipping a general-purpose layout engine was not
proportionate to that graph model.

## Decision

Repository Map keeps React Flow but uses a deterministic layered layout owned
by `RepositoryMapPage.tsx`:

1. compute in-degree and outgoing relationships from the filtered graph;
2. assign the longest predecessor layer for acyclic nodes;
3. place cycles and unresolved nodes in the first layer;
4. sort every lane by stable node ID;
5. cap one rendered view at 800 nodes and require filters above that limit.

The algorithm runs only on the commit-bound API graph. It does not infer or
invent relationships. Users retain pan, zoom, drag, selection, MiniMap,
re-layout, search, filters, JSON export, and SVG export.

## Evidence

After removing ELK, the lazy Repository Map JavaScript chunk fell from
1,445.36 kB to 6.32 kB minified (2.67 kB gzip). The main application chunk
remained 179.13 kB (58.69 kB gzip). `pnpm typecheck`, ESLint, Vitest, the Vite
production build, and the real-browser Playwright flow passed on macOS arm64.

Monaco remains a larger separately loaded chunk because local/offline loading
is a security and reliability requirement. It is not part of the initial
Dashboard download.

## Consequences

The layout is intentionally less sophisticated than ELK for dense cyclic
graphs. The 800-node cap and filters make that limitation explicit. If future
graph capabilities add inheritance, route, database, test, or clustered
directory hyperedges, ELK or a worker-based layout may be reconsidered with a
new measured build comparison.
