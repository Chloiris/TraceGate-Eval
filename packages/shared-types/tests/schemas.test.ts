import { describe, expect, it } from "vitest";

import {
  componentStatusSchema,
  isComponentReady,
  systemStatusSchema,
} from "../src/index";

describe("shared API schemas", () => {
  it("accepts an explicit not-configured component", () => {
    const status = componentStatusSchema.parse({
      state: "not_configured",
      configured: false,
      message: "GitHub 尚未连接",
      detail: null,
    });

    expect(isComponentReady(status)).toBe(false);
  });

  it("rejects undocumented component states", () => {
    expect(() =>
      componentStatusSchema.parse({
        state: "success",
        configured: true,
        message: "ok",
      }),
    ).toThrow();
  });

  it("requires every core system component", () => {
    expect(() =>
      systemStatusSchema.parse({
        status: "ready",
        components: {},
        checked_at: "2026-07-10T10:00:00+08:00",
      }),
    ).toThrow();
  });
});
