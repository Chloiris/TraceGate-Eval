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
          webhook_relay: { state: "not_configured", configured: false, message: "Webhook Relay 未配置" },
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

  it("parses a commit-bound Review Map and preserves bearer authentication", async () => {
    const pullRequestId = "11111111-1111-4111-8111-111111111111";
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse({
      pull_request_id: pullRequestId,
      base_sha: "a".repeat(40),
      head_sha: "b".repeat(40),
      index_version: "22222222-2222-4222-8222-222222222222",
      source: "git_diff+static_index+agent_evidence",
      nodes: [{
        id: "file:main",
        kind: "file",
        label: "main.py",
        path: "main.py",
        symbol: null,
        language: "python",
        impact_depth: 0,
        change_status: "modified",
        risk: null,
        finding_ids: [],
        evidence_ids: [],
      }],
      edges: [],
      truncated: false,
      message: "Derived from real static evidence.",
    }));
    const client = new TraceGateApiClient(connection, fetchMock);

    const graph = await client.getPullRequestGraph(pullRequestId);

    expect(graph.nodes[0]?.path).toBe("main.py");
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/pull-requests/${pullRequestId}/graph`,
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test-token-not-a-real-secret" }),
      }),
    );
  });

  it("parses authenticated SSE Agent Trace events", async () => {
    const runId = "11111111-1111-4111-8111-111111111111";
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(`event: run\ndata: ${JSON.stringify({
          id: runId,
          repository_id: "22222222-2222-4222-8222-222222222222",
          pull_request_id: null,
          status: "completed",
          current_node: "Report Composer",
          head_sha: "a".repeat(40),
          prompt_version: "v1",
          index_version: "33333333-3333-4333-8333-333333333333",
          workflow_version: "v1",
          model_profile: "deepseek/test",
          context_scope: "changed_files",
          input_tokens: 10,
          output_tokens: 5,
          latency_ms: 12,
          retry_count: 0,
          retrieval_hit_count: 0,
          cancellation_requested: false,
          error_code: null,
          error_message: null,
          started_at: "2026-07-10T10:00:00Z",
          finished_at: "2026-07-10T10:00:01Z",
          created_at: "2026-07-10T10:00:00Z",
          updated_at: "2026-07-10T10:00:01Z",
        })}\n\n`));
        controller.close();
      },
    });
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    }));
    const client = new TraceGateApiClient(connection, fetchMock);
    const events: string[] = [];

    await client.streamRunEvents(runId, (event) => events.push(event.type));

    expect(events).toEqual(["run"]);
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/runs/${runId}/events`,
      expect.objectContaining({ headers: expect.objectContaining({ Accept: "text/event-stream" }) }),
    );
  });
});
