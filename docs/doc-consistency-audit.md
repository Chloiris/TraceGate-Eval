# TraceGate documentation consistency audit

- Audit opened: 2026-07-12
- Starting code baseline: `a1dcd7d755c25e0f75aac499943a07b759ec30db`
- Active branch: `feat/coding-agent-autofix-loop`
- Product version selected after tag audit: `0.4.0`
- Status: macOS implementation, full local matrix, native package and scoped
  real-model Autofix evidence complete; remote Windows evidence remains pending

## Canonical naming

| Scope | Canonical name | Applied boundary |
| --- | --- | --- |
| Repository | TraceGate-Eval | GitHub/repository identity only |
| Desktop/full-stack product | TraceGate Studio | UI, Sidecar, desktop, review and Autofix product |
| Research/evaluation subsystem | TraceGate Eval | Preserved benchmark/CLI/research scope |
| Controlled claim evaluation | ClaimBench | 160-run controlled artifact set |
| Semantic PR review module | Semantic PR Advisor | PR advisory module, not whole-product name |

## Findings and disposition

| Area | Finding | Correction / remaining gate |
| --- | --- | --- |
| Naming | Older documents alternated between Eval and Studio for the whole product. | Both READMEs now explain repository/product/eval/module names; historical research files keep their original scope. |
| Version | Runtime/package sources were `0.1.0` while historical tags include `v0.2-alpha` and `v0.3-alpha`. | Selected `0.4.0` to avoid semantic regression; package/runtime/build metadata now share one canonical version. |
| Positioning | Python metadata described only process-context routing. | Canonical description now states local-first full-stack review/code intelligence/controlled Autofix/agent evaluation without “production-ready” claims. |
| README parity | English/Chinese structure and Autofix content differed. | Both now use the same required 26-section order and canonical facts. Checker validates order, nodes, resolutions, and safety boundaries. |
| Review/Fix boundary | Existing docs described only a low-level confirmation-gated patch Tool. | Added a separate 11-node Fix workflow, hash/Head confirmation, isolated worktree, validation/re-review/resolution and no-auto-push boundary. |
| Test counts | Current docs copied different totals from different historical commits. | `project-facts.yaml` preserves the 212 Python / 30 TS / 22 Rust + 1 ignored / 4 Playwright pre-Autofix baseline and separately records the completed 269 Python / 60 TS / 22 Rust + 1 ignored / 5 Playwright Autofix matrix. |
| Workflow/Tool count | Seven Review nodes and 19 tools were not centrally checked. | Runtime imports now validate Review nodes/tools plus 11 Fix nodes and five resolutions against project facts. |
| API | Autofix lifecycle/API/SSE/export behavior was absent. | Added and tested 17 method/path facts, including authenticated diagnostic workspace cleanup, plus typed API/SSE/export guide coverage. |
| Capabilities | Some summaries could be read as full polyglot semantics, vector retrieval, or native Tool Calling. | READMEs and checker preserve bounded JS/TS/Java adapters, disabled embeddings, compatibility-mode tool-selection boundary, and no whole-program Java call resolution. |
| Branch/SHA/run | Current-facing files referenced merged feature branches and several noncanonical run snapshots. | Current status uses the active branch/starting main; immutable evidence keeps original values only in documents marked **Historical verification record** or explicit historical/source-bound rows. Final feature SHA/run is pending. |
| Windows | Automated packaging and GUI acceptance were easy to conflate. | All current docs state `VERIFIED_WINDOWS_CI` does not imply `VERIFIED_WINDOWS_MANUAL`; Autofix adds fresh CI and eight GUI checks without claiming completion. |
| Screenshots | Existing P1 images were not always labelled by data source; Autofix images did not exist at baseline. | Gallery now labels P1 and two new Autofix captures as Playwright fixture evidence. No image is called a public-PR/real-model Fix result. |
| Real Autofix E2E | No completed production-path record existed at baseline. | A real DeepSeek run completed the production Review and Fix workflows on an explicitly labelled synthetic temporary Git repository; the public-PR Fix scope remains `BLOCKED`, and no fixture/mock/cache/rule result is presented as that evidence. |
| Security/privacy | Patch replacement, stale Head, worktree and validation-command threats were missing. | Updated security/privacy/policy plus dedicated Autofix safety matrix and troubleshooting. |
| Product/interview/demo | Story ended at read-only review and contained stale counts/runs. | Tour/demo/engineering discussion now show the controlled loop, source workspace proof, failure branch, export/rollback and evidence scope. |
| Resume bullets | Some bullets embedded outdated suite counts/Windows identifiers. | Every current bullet cites code/test/verification evidence and separates implementation from pending real-model/full-suite gates. |
| Links | No repository-wide executable link check existed. | Checker now scans every repository Markdown file (excluding generated/vendor trees) for Markdown and HTML relative targets. |
| Single source of truth | Facts were copied manually across docs. | `docs/project-facts.yaml` plus checker validates naming, versions, runtime nodes/tools/parser/benchmarks, README structure, limitations, links, historical markers and forbidden overclaims. |

## Screenshot inventory

| Image | Data boundary | Current use |
| --- | --- | --- |
| `screenshots/p1-pr-diff-macos.png` | Playwright repository fixture | Hero/product tour; UI behavior only |
| `screenshots/p1-review-map-macos.png` | Playwright repository fixture | Static/evidence map rendering only |
| `screenshots/p1-eval-center-macos.png` | Checked-in 19-case/160-row artifacts | Eval rendering, not live accuracy |
| `screenshots/p1-registry-macos.png` | Running product registry | Seven Review nodes/19 tools at captured code |
| `screenshots/autofix-playwright-fixture-confirmation-macos.png` | Playwright Autofix fixture | Patch/Hash/confirmation UI only |
| `screenshots/autofix-playwright-fixture-result-macos.png` | Playwright Autofix fixture | Validation/re-review/report UI only |

Real-model/public-PR Autofix screenshots remain `PENDING`. Add them only after
the actual run and label the exact scope in the image caption and verification
record.

## Automated policy

`uv run python scripts/check_docs_consistency.py` validates:

- canonical product/repository/subsystem/module names;
- SemVer across Python, Node packages, Tauri/Cargo, lock files, runtime User
  Agents, MCP metadata, and build-info generation;
- seven Review nodes, 11 Fix nodes, five resolutions, 19 Registry tools, parser
  matrix and checked-in benchmark distributions against production/artifacts;
- identical 26-section English/Chinese README structure and required Autofix
  read-only/confirmation/isolation/no-push/real-E2E boundaries;
- required limitations and forbidden unqualified vector/native-tool/full-Java
  claims;
- historical markers and Windows CI/manual separation;
- every Markdown/HTML relative link in every repository Markdown document;
- existence and source-bound fields of the scoped real Autofix E2E record,
  including its explicit synthetic-repository and blocked public-PR boundary.

## Remaining dynamic evidence

- [x] Tested implementation source SHA.
- [ ] Pull Request URL and final remote Windows workflow record.
- [x] Complete current Python/TypeScript/Rust/Playwright counts.
- [x] Migration fresh/upgrade/idempotency/MySQL-offline final result.
- [x] Real-model Autofix scope, provider/model, Fix Session, model/Tool counts,
  tokens/latency, Patch Hash, files/lines, validation commands/codes,
  re-review/resolution, authoritative artifacts, original-workspace proof,
  rollback and cleanup.
- [x] Fresh macOS Sidecar/Tauri package/runtime evidence.
- [ ] Fresh Windows workflow URL, every job status, artifact name/ID/paths and
  hashes.
- [ ] Windows GUI/manual remains blocked unless a real target record is added.

## First-pass checklist

- [x] Canonical names and version sources unified.
- [x] Historical research/evidence scope preserved and labelled.
- [x] English/Chinese README structures and facts aligned.
- [x] Autofix workflow/safety/API/usage/failure boundaries documented.
- [x] Parser/vector/Tool Calling limits remain explicit.
- [x] Windows CI/manual states remain separate.
- [x] Fixture screenshots are labelled and links resolve.
- [x] Repository-wide link and Autofix fact checks implemented.
- [x] Replace completed macOS dynamic fields only from real commands/runs.
- [ ] Replace remote Windows fields only after the source-bound workflow ends.
