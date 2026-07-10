import { describe, expect, it, vi } from "vitest";

import { TraceGateApiClient, TraceGateApiError } from "../src/index";

const connection = {
  baseUrl: "/api/v1/",
  token: "test-token-not-a-real-secret",
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("TraceGateApiClient", () => {
  it("sends the in-memory bearer token and parses status", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse({
        status: "degraded",
        components: {
          api: { state: "ready", configured: true, message: "API 正常" },
          database: { state: "ready", configured: true, message: "SQLite 正常" },
          github: { state: "not_configured", configured: false, message: "GitHub 尚未连接" },
          model: { state: "not_configured", configured: false, message: "模型尚未配置" },
          eval: { state: "ready", configured: true, message: "Eval 可用" },
        },
        checked_at: "2026-07-10T10:00:00+08:00",
      }),
    );
    const client = new TraceGateApiClient(connection, fetchMock);

    const result = await client.getSystemStatus();

    expect(result.components.github.state).toBe("not_configured");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/system/status",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test-token-not-a-real-secret" }),
      }),
    );
  });

  it("surfaces structured HTTP errors", async () => {
    const client = new TraceGateApiClient(
      connection,
      vi.fn<typeof fetch>().mockResolvedValue(
        jsonResponse({ error: { code: "unauthorized", message: "本地 API Token 无效" } }, 401),
      ),
    );

    await expect(client.health()).rejects.toMatchObject({
      kind: "http",
      status: 401,
      code: "unauthorized",
      message: "本地 API Token 无效",
    });
  });

  it("does not replace a network failure with fallback data", async () => {
    const client = new TraceGateApiClient(
      connection,
      vi.fn<typeof fetch>().mockRejectedValue(new TypeError("connection refused")),
    );

    await expect(client.getSettings()).rejects.toMatchObject({
      kind: "network",
    });
  });

  it("rejects a response that violates the API schema", async () => {
    const client = new TraceGateApiClient(
      connection,
      vi.fn<typeof fetch>().mockResolvedValue(jsonResponse({ status: "ok" })),
    );

    await expect(client.health()).rejects.toMatchObject({
      kind: "invalid_response",
    });
  });

  it("fails before fetching when the token is missing", () => {
    expect(() => new TraceGateApiClient({ baseUrl: "/api/v1", token: "" })).toThrow(
      TraceGateApiError,
    );
  });
});
