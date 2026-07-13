# TraceGate site content and evidence boundaries

The marketing site is designed to look strong because the underlying product,
architecture, and evidence are inspectable—not because uncertainty is hidden.

## Canonical sources

- Product counts and verification identifiers: `docs/project-facts.yaml`
- Product behavior and limits: `README.md`, `docs/README_CN.md`,
  `docs/implementation-status.md`, and architecture/security records
- Screenshot provenance: `apps/site/src/data/gallery.ts`
- Source-bound verification: `docs/verification/`

The site build generates its selected facts from the canonical YAML-compatible
JSON source. Tests fail when the generated copy drifts.

## Screenshot scopes

| Scope | Meaning |
| --- | --- |
| Real local run | Product UI connected to a real local application runtime; it does not imply every provider is configured. |
| Playwright repository fixture | Running product UI against an isolated deterministic repository fixture; not a public-PR or live-model accuracy result. |
| Controlled benchmark | Checked-in Eval/ClaimBench output; not customer telemetry or an Autofix success rate. |

The gallery currently uses all three scopes. Each card and lightbox repeats the
scope label and records the repository-relative source. Generated assets never
contain local absolute paths.

## Claims intentionally withheld

- No user, customer, revenue, accuracy, or automatic-fix success metrics
- No claim that public-PR Autofix E2E is verified
- No claim that Windows CI packaging equals Windows GUI manual acceptance
- No claim of a complete semantic JS, TS, or Java call graph
- No claim that validation commands run inside an OS/container sandbox
- No expiring GitHub Actions artifact presented as a permanent download

Real DeepSeek Autofix evidence is labelled as a synthetic temporary Git
repository. Fixture screenshots remain fixture evidence even when they show a
successful deterministic state.

## Secret and privacy boundary

The site contains no credential input, analytics, database, or upload feature.
API keys, GitHub tokens, credential-store values, local paths, server addresses,
SSH configuration, private logs, and local databases are prohibited content.
The Settings screenshot may show only `configured`/`missing` state.
