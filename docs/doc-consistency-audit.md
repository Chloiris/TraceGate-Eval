# TraceGate documentation consistency audit

- Audit opened: 2026-07-12
- Code baseline: `a1dcd7d755c25e0f75aac499943a07b759ec30db`
- Status: in progress; this file records evidence before global corrections.

## Canonical naming

| Scope | Canonical name |
| --- | --- |
| Repository | TraceGate-Eval |
| Desktop/full-stack product | TraceGate Studio |
| Research/evaluation subsystem | TraceGate Eval |
| Controlled claim evaluation | ClaimBench |
| Semantic PR review module | Semantic PR Advisor |

## Initial findings

| Area | Baseline evidence | Required correction |
| --- | --- | --- |
| Version | Python, root/web/desktop/shared/api packages, Cargo and Tauri all report `0.1.0`. | Audit release history, then select and synchronize the Autofix release version. |
| Python description | `pyproject.toml` still describes only process-context routing research. | Describe the local-first Studio product while preserving Eval as a subsystem. |
| Current status | `docs/implementation-status.md` is source-bound to the merged Studio feature work. | Move current state to the Autofix branch and retain old SHA/run evidence only as historical records. |
| Test facts | Starting executable baseline is 212 Python, 5 shared, 7 API-client, 18 web and 22 Rust passing. | Replace non-historical current-count copies after Autofix tests are added. |
| Screenshots | Existing P1 screenshots represent fixture-backed browser flows; the Review Map image is not suitable as Autofix evidence. | Generate labelled Autofix screenshots from the new Playwright flow and retire only genuinely stale gallery images. |
| Product boundary | Older research documents correctly describe TraceGate Eval; newer product docs describe Studio. | Add explicit historical/subsystem labels instead of globally renaming research records. |
| Old branches/SHAs | Historical verification files intentionally bind earlier commits/runs; current documents also contain feature-branch references. | Preserve immutable evidence with a `Historical verification record` label; forbid stale branch/SHA claims in current docs. |
| Capability status | Autofix is absent from current code and documentation. | Add only evidence-backed status after each implementation gate. |
| README parity | English and Chinese READMEs are broadly aligned but do not contain the required Autofix workflow/safety/usage sections. | Keep identical section order and canonical facts from `project-facts.yaml`. |
| Link integrity | No repository-wide executable consistency checker exists. | Add relative-link and canonical-fact checks to CI. |

## Audit checklist

- [ ] Project naming is consistent without rewriting historical research scope.
- [ ] Version and metadata have one canonical source and synchronized consumers.
- [ ] Current test/benchmark/tool/node counts come from executable facts.
- [ ] Current docs contain no obsolete feature branch or non-historical SHA.
- [ ] Historical verification records are explicitly labelled and unchanged.
- [ ] English and Chinese README sections and facts match.
- [ ] Every screenshot states fixture/real-local/real-model/public-PR provenance.
- [ ] Parser, vector retrieval and model Tool Calling boundaries remain honest.
- [ ] Windows CI and Windows graphical/manual acceptance remain distinct.
- [ ] Relative links and referenced files pass an automated check.
- [ ] Documentation consistency checks run in CI.
