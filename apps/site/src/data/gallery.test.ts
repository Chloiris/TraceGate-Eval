import { describe, expect, test } from "vitest";

import { galleryItems, imageSources } from "./gallery";

describe("product screenshot metadata", () => {
  test("covers the required gallery surfaces with explicit provenance", () => {
    expect(galleryItems.length).toBeGreaterThanOrEqual(13);
    const required = ["dashboard", "pr-inbox", "pr-diff", "findings-evidence", "repository-map", "review-map", "agent-trace", "eval-center", "fix-plan", "patch-proposal", "validation", "final-report", "settings"];
    expect(required.every((id) => galleryItems.some((item) => item.id === id))).toBe(true);
    for (const item of galleryItems) {
      expect(["real-local", "test-fixture", "controlled-benchmark"]).toContain(item.scope);
      expect(item.source).not.toMatch(/^\//);
      expect(item.source).not.toContain("/Users/");
      expect(item.scopeLabel.zh.length).toBeGreaterThan(0);
      expect(item.scopeLabel.en.length).toBeGreaterThan(0);
      expect(imageSources(item.id).fallback).toMatch(/^\/media\/product\//);
    }
  });
});
