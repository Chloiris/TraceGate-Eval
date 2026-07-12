import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = resolve(here, "..");
const repositoryRoot = resolve(siteRoot, "../..");
const sourcePath = resolve(repositoryRoot, "docs/project-facts.yaml");
const source = JSON.parse(await readFile(sourcePath, "utf8"));

const facts = {
  productName: source.canonical_naming.product_name,
  repositoryName: source.canonical_naming.repository_name,
  version: source.version,
  review: {
    nodeCount: source.review_workflow.node_count,
    nodes: source.review_workflow.nodes,
  },
  autofix: {
    nodeCount: source.autofix_workflow.node_count,
    nodes: source.autofix_workflow.nodes,
    resolutions: source.autofix_workflow.resolutions,
  },
  tools: source.tool_registry.tool_count,
  tests: {
    python: source.current_test_counts.python,
    typescript: source.current_test_counts.typescript.total,
    rust: source.current_test_counts.rust.passed,
    rustIgnored: source.current_test_counts.rust.ignored,
    playwright: source.current_test_counts.playwright,
    sourceSha: source.current_test_counts.source_sha,
  },
  benchmark: {
    publicPrCases: source.benchmark_counts.real_pr_cases,
    claimbenchRuns: source.benchmark_counts.claimbench_runs,
  },
  verification: {
    macos: source.platforms.verified.macos_arm64.status,
    windowsCi: source.platforms.verified.windows_x86_64_ci.status,
    windowsManual: source.platforms.verified.windows_x86_64_manual.status,
  },
};

const generatedPath = resolve(siteRoot, "src/generated/projectFacts.ts");
await mkdir(dirname(generatedPath), { recursive: true });
await writeFile(
  generatedPath,
  `/* Generated from docs/project-facts.yaml. Do not edit by hand. */\nexport const projectFacts = ${JSON.stringify(facts, null, 2)} as const;\n`,
  "utf8",
);

await writeFile(resolve(siteRoot, "public/project-facts.json"), `${JSON.stringify(facts, null, 2)}\n`, "utf8");
console.log(`TraceGate site facts generated for ${facts.productName} ${facts.version}`);
