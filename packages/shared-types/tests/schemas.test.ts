import { describe, expect, it } from "vitest";

import {
  componentStatusSchema,
  credentialStatusSchema,
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

  it("accepts credential presence without a secret field", () => {
    const status = credentialStatusSchema.parse({
      kind: "github",
      configured: true,
      storage: "macOS Keychain",
      restartRequiredAfterChange: true,
    });
    expect(status.configured).toBe(true);
    expect("secret" in status).toBe(false);
  });
});
