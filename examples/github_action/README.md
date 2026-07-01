# TraceGate GitHub Action Example

This example shows the warning-only Pull Request advisory path.

1. Add `tracegate.yml` to the repository root.
2. Enable `.github/workflows/tracegate-advisory.yml`.
3. Open a Pull Request touching files matched by a configured claim.
4. Read the advisory in the GitHub Actions job summary.

The action reads real PR changed files from GitHub context and repo-local claim configuration. It does not run a mock dataset and does not block merges by default.
