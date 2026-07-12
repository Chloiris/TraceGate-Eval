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

const fixSessionId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const findingId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

function fixSessionDetailPayload() {
  return {
    id: fixSessionId,
    repository_id: "11111111-1111-4111-8111-111111111111",
    pull_request_id: "22222222-2222-4222-8222-222222222222",
    finding_id: findingId,
    source_agent_run_id: "33333333-3333-4333-8333-333333333333",
    base_sha: "a".repeat(40),
    head_sha: "b".repeat(40),
    index_version_id: "44444444-4444-4444-8444-444444444444",
    workspace_index_version_id: null,
    status: "ELIGIBLE",
    current_node: "CHECK_FIX_ELIGIBILITY",
    permission_mode: "APPLY_IN_ISOLATED_WORKSPACE",
    workspace_path: null,
    workspace_state_hash: null,
    cleanup_status: "ACTIVE",
    model_profile: "deepseek/deepseek-chat",
    workflow_version: "tracegate-fix-v1",
    eligibility: { status: "ELIGIBLE", reasons: [], warnings: [], force_allowed: false },
    allowed_actions: ["PLAN", "CANCEL"],
    lock_version: 1,
    cancellation_requested: false,
    input_tokens: 0,
    output_tokens: 0,
    latency_ms: 0,
    retry_count: 0,
    created_at: "2026-07-12T10:00:00Z",
    started_at: "2026-07-12T10:00:01Z",
    finished_at: null,
    error_code: null,
    error_message: null,
    last_active_at: "2026-07-12T10:00:01Z",
    updated_at: "2026-07-12T10:00:01Z",
    plan: null,
    proposal: null,
    patch_inspection: null,
    confirmation: null,
    validation_plan: null,
    validation_runs: [],
    steps: [],
    re_review: null,
    result: null,
  };
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
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/system/status");
    expect(new Headers(fetchMock.mock.calls[0]?.[1]?.headers).get("Authorization"))
      .toBe("Bearer test-token-not-a-real-secret");
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
    expect(fetchMock.mock.calls[0]?.[0]).toBe(`/api/v1/pull-requests/${pullRequestId}/graph`);
    expect(new Headers(fetchMock.mock.calls[0]?.[1]?.headers).get("Authorization"))
      .toBe("Bearer test-token-not-a-real-secret");
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

  it("creates a Fix Session with schema validation, auth, and an idempotency key", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async () => jsonResponse(fixSessionDetailPayload()));
    const client = new TraceGateApiClient(connection, fetchMock);

    const detail = await client.createFixSession(
      { finding_id: findingId, permission_mode: "APPLY_IN_ISOLATED_WORKSPACE" },
      undefined,
      "create-fix-session-0001",
    );

    expect(detail.id).toBe(fixSessionId);
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/fix-sessions");
    expect(init?.method).toBe("POST");
    const headers = new Headers(init?.headers);
    expect(headers.get("Authorization")).toBe("Bearer test-token-not-a-real-secret");
    expect(headers.get("Idempotency-Key")).toBe("create-fix-session-0001");
    expect(JSON.parse(String(init?.body))).toEqual({
      finding_id: findingId,
      permission_mode: "APPLY_IN_ISOLATED_WORKSPACE",
    });
  });

  it("preserves custom headers while preventing callers from replacing auth", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(fixSessionDetailPayload()));
    const client = new TraceGateApiClient(connection, fetchMock);

    await client.planFixSession(
      fixSessionId,
      { expected_lock_version: 1, force_eligibility: false },
      undefined,
      "plan-fix-session-0001",
    );

    const [, init] = fetchMock.mock.calls[0] ?? [];
    const headers = new Headers(init?.headers);
    expect(headers.get("Idempotency-Key")).toBe("plan-fix-session-0001");
    expect(headers.get("Authorization")).toBe("Bearer test-token-not-a-real-secret");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("exposes every controlled Fix Session transition endpoint", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async () => jsonResponse(fixSessionDetailPayload()));
    const client = new TraceGateApiClient(connection, fetchMock);
    const action = { expected_lock_version: 1 };

    await client.generateFixPatch(fixSessionId, action, undefined, "generate-fix-0001");
    await client.confirmFixSession(fixSessionId, {
      ...action,
      patch_hash: "c".repeat(64),
    }, undefined, "confirm-fix-0001");
    await client.applyFixSession(fixSessionId, { ...action, patch_hash: "c".repeat(64) }, undefined, "apply-fix-0001");
    await client.validateFixSession(fixSessionId, action, undefined, "validate-fix-0001");
    await client.rereviewFixSession(fixSessionId, action, undefined, "rereview-fix-0001");
    await client.cancelFixSession(fixSessionId, action, undefined, "cancel-fix-0001");
    await client.rollbackFixSession(fixSessionId, action, undefined, "rollback-fix-0001");

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      `/api/v1/fix-sessions/${fixSessionId}/generate`,
      `/api/v1/fix-sessions/${fixSessionId}/confirm`,
      `/api/v1/fix-sessions/${fixSessionId}/apply`,
      `/api/v1/fix-sessions/${fixSessionId}/validate`,
      `/api/v1/fix-sessions/${fixSessionId}/re-review`,
      `/api/v1/fix-sessions/${fixSessionId}/cancel`,
      `/api/v1/fix-sessions/${fixSessionId}/rollback`,
    ]);
  });

  it("lists and reads Fix Sessions with explicit filters", async () => {
    const detail = fixSessionDetailPayload();
    const summary = { ...detail };
    delete (summary as Partial<typeof detail>).plan;
    delete (summary as Partial<typeof detail>).proposal;
    delete (summary as Partial<typeof detail>).patch_inspection;
    delete (summary as Partial<typeof detail>).confirmation;
    delete (summary as Partial<typeof detail>).validation_plan;
    delete (summary as Partial<typeof detail>).validation_runs;
    delete (summary as Partial<typeof detail>).steps;
    delete (summary as Partial<typeof detail>).re_review;
    delete (summary as Partial<typeof detail>).result;
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ items: [summary], total: 1, limit: 20, offset: 0 }))
      .mockResolvedValueOnce(jsonResponse(detail));
    const client = new TraceGateApiClient(connection, fetchMock);

    const list = await client.listFixSessions({
      pullRequestId: detail.pull_request_id,
      findingId,
      limit: 20,
      offset: 0,
    });
    const fetched = await client.getFixSession(fixSessionId);

    expect(list.total).toBe(1);
    expect(fetched.id).toBe(fixSessionId);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      `/api/v1/fix-sessions?pull_request_id=${detail.pull_request_id}&finding_id=${findingId}&limit=20&offset=0`,
    );
  });

  it("parses authoritative Patch and Fix Result responses", async () => {
    const patchHash = "c".repeat(64);
    const report = {
      fix_session_id: fixSessionId,
      finding_id: findingId,
      patch_hash: patchHash,
      applied: true,
      validation_status: "PASSED",
      commands_run: [["pytest", "-q"]],
      passed_commands: [["pytest", "-q"]],
      failed_commands: [],
      re_review_status: "completed",
      finding_resolution: "RESOLVED",
      residual_findings: [],
      residual_risks: [],
      final_summary: "Resolved with passing validation.",
    };
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({
        fix_session_id: fixSessionId,
        head_sha: "b".repeat(40),
        patch_hash: patchHash,
        unified_diff: "diff --git a/service.py b/service.py",
        changed_files: [{ path: "service.py", status: "modified" }],
        selected_path: "service.py",
        original: "return value * 2",
        modified: "return value",
      }))
      .mockResolvedValueOnce(jsonResponse({
        id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        fix_session_id: fixSessionId,
        resolution: "RESOLVED",
        validation_status: "PASSED",
        re_review_status: "completed",
        residual_findings: [],
        residual_risks: [],
        report,
        created_at: "2026-07-12T10:10:00Z",
      }));
    const client = new TraceGateApiClient(connection, fetchMock);

    expect((await client.getFixPatch(fixSessionId, "service.py")).patch_hash).toBe(patchHash);
    expect((await client.getFixReport(fixSessionId)).resolution).toBe("RESOLVED");
    expect(fetchMock.mock.calls[0]?.[0]).toBe(`/api/v1/fix-sessions/${fixSessionId}/patch?path=service.py`);
  });

  it("downloads authoritative Patch bytes and preserves trusted metadata", async () => {
    const patchHash = "d".repeat(64);
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response("diff --git a/a b/a\n", {
      status: 200,
      headers: {
        "Content-Type": "text/x-diff",
        "Content-Disposition": "attachment; filename=verified.patch",
        "X-TraceGate-Patch-Hash": patchHash,
      },
    }));
    const client = new TraceGateApiClient(connection, fetchMock);

    const artifact = await client.downloadFixPatch(fixSessionId);

    expect(artifact.filename).toBe("verified.patch");
    expect(artifact.patchHash).toBe(patchHash);
    expect(await artifact.blob.text()).toContain("diff --git");
  });

  it("deletes only the addressed Fix workspace and downloads the persisted report", async () => {
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response("{\"resolution\":\"NEEDS_HUMAN_REVIEW\"}", {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Content-Disposition": "attachment; filename=fix-report.json",
        },
      }));
    const client = new TraceGateApiClient(connection, fetchMock);

    await client.deleteFixWorkspace(fixSessionId, 8, undefined, "delete-workspace-0001");
    const artifact = await client.downloadFixReport(fixSessionId);

    expect(fetchMock.mock.calls[0]?.[0]).toBe(`/api/v1/fix-sessions/${fixSessionId}/workspace`);
    expect(fetchMock.mock.calls[0]?.[1]?.method).toBe("DELETE");
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({ expected_lock_version: 8 });
    expect(fetchMock.mock.calls[1]?.[0]).toBe(`/api/v1/fix-sessions/${fixSessionId}/report?download=true`);
    expect(artifact.filename).toBe("fix-report.json");
  });

  it("lists and safely cleans residual Fix workspaces through diagnostics endpoints", async () => {
    const residualId = "orphan-session-0001";
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({
        items: [{
          fix_session_id: residualId,
          repository_id: "repository-0001",
          path: `/managed/autofix/repository-0001/${residualId}/worktree`,
          cleanup_status: "ORPHANED",
          last_active_at: "2026-07-12T10:00:00Z",
          expired: true,
        }],
        total: 1,
        retention_hours: 12,
      }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    const client = new TraceGateApiClient(connection, fetchMock);

    const listed = await client.listFixWorkspaces();
    await client.cleanupFixWorkspace(residualId, undefined, "cleanup-residual-0001");

    expect(listed.items[0]?.cleanup_status).toBe("ORPHANED");
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/fix-workspaces");
    expect(fetchMock.mock.calls[1]?.[0]).toBe(`/api/v1/fix-workspaces/${residualId}`);
    expect(fetchMock.mock.calls[1]?.[1]?.method).toBe("DELETE");
    expect(new Headers(fetchMock.mock.calls[1]?.[1]?.headers).get("Idempotency-Key"))
      .toBe("cleanup-residual-0001");
  });

  it("parses CRLF, multiline Fix SSE, sends Last-Event-ID, and deduplicates bounded IDs", async () => {
    const event = {
      event_id: "12",
      sequence: 12,
      fix_session_id: fixSessionId,
      created_at: "2026-07-12T10:00:00Z",
      type: "validation_output",
      data: {
        validation_run_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        stream: "stdout",
        chunk: "line one\nline two",
        truncated: false,
      },
    };
    const serialized = JSON.stringify(event);
    const midpoint = serialized.indexOf("\"data\"");
    const dataLines = `${serialized.slice(0, midpoint)}\r\ndata: ${serialized.slice(midpoint)}`;
    const wire = `id: 12\r\nevent: validation_output\r\ndata: ${dataLines}\r\n\r\n` +
      `id: 12\r\nevent: validation_output\r\ndata: ${dataLines}\r\n\r\n`;
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(wire.slice(0, 47)));
        controller.enqueue(encoder.encode(wire.slice(47)));
        controller.close();
      },
    });
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream; charset=utf-8" },
    }));
    const client = new TraceGateApiClient(connection, fetchMock);
    const events: string[] = [];

    const cursor = await client.streamFixSessionEvents(
      fixSessionId,
      (item) => events.push(item.event_id),
      { lastEventId: "11", maxBufferBytes: 32_000, maxSeenEventIds: 2 },
    );

    expect(events).toEqual(["12"]);
    expect(cursor.lastEventId).toBe("12");
    const [, init] = fetchMock.mock.calls[0] ?? [];
    expect(new Headers(init?.headers).get("Last-Event-ID")).toBe("11");
  });

  it("fails closed when a Fix SSE event exceeds its configured buffer", async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(`data: ${"x".repeat(2_000)}`));
        controller.close();
      },
    });
    const client = new TraceGateApiClient(connection, vi.fn<typeof fetch>().mockResolvedValue(new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    })));

    await expect(client.streamFixSessionEvents(fixSessionId, () => undefined, { maxBufferBytes: 1_024 }))
      .rejects.toMatchObject({ kind: "invalid_response" });
  });
});
