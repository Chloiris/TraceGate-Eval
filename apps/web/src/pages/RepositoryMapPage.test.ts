import { describe, expect, it } from "vitest";

import { repositoryMapSvg } from "../lib/repositoryMapExport";

describe("repositoryMapSvg", () => {
  it("exports deterministic standalone SVG without foreignObject", () => {
    const svg = repositoryMapSvg(
      [
        { id: "a", position: { x: 0, y: 0 }, data: { label: "A <root>", kind: "file", path: "a.ts", language: "typescript", symbol: null } },
        { id: "b", position: { x: 260, y: 0 }, data: { label: "B", kind: "symbol", path: "b.ts", language: "typescript", symbol: "B" } },
      ],
      [{ id: "edge", source: "a", target: "b" }],
    );
    expect(svg).toContain("A &lt;root&gt;");
    expect(svg).toContain("<line");
    expect(svg).not.toContain("foreignObject");
    expect(svg).toMatch(/^<svg/);
  });
});
