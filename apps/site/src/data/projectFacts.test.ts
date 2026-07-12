// @vitest-environment node
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, test } from "vitest";

import { projectFacts } from "../generated/projectFacts";

describe("generated project facts", () => {
  test("matches the canonical repository fact source", () => {
    const here = dirname(fileURLToPath(import.meta.url));
    const repositoryRoot = resolve(here, "../../../..");
    const canonical = JSON.parse(readFileSync(resolve(repositoryRoot, "docs/project-facts.yaml"), "utf8"));
    expect(projectFacts.version).toBe(canonical.version);
    expect(projectFacts.review.nodeCount).toBe(canonical.review_workflow.node_count);
    expect(projectFacts.review.nodes).toEqual(canonical.review_workflow.nodes);
    expect(projectFacts.autofix.nodeCount).toBe(canonical.autofix_workflow.node_count);
    expect(projectFacts.autofix.nodes).toEqual(canonical.autofix_workflow.nodes);
    expect(projectFacts.tools).toBe(canonical.tool_registry.tool_count);
    expect(projectFacts.tests.python).toBe(canonical.current_test_counts.python);
    expect(projectFacts.tests.typescript).toBe(canonical.current_test_counts.typescript.total);
    expect(projectFacts.tests.rust).toBe(canonical.current_test_counts.rust.passed);
    expect(projectFacts.tests.playwright).toBe(canonical.current_test_counts.playwright);
  });
});
