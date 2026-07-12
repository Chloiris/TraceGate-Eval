import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TraceGateApiClient } from "@tracegate/api-client";
import type { FixPatchResponse, FixResult, FixSessionDetail, FixSessionEvent } from "@tracegate/shared-types";
import { describe, expect, it, vi } from "vitest";

import { ApiClientProvider } from "../api/clientContext";
import { I18nProvider } from "../i18n";
import {
  canApplyFix,
  commandText,
  FixConfirmationDialog,
  FixSessionView,
  isFixStale,
  localizedFixStatus,
  fixStreamRetryDelay,
  streamFixEventsWithRetry,
} from "./FixExperience";

const sessionId = "11111111-1111-4111-8111-111111111111";
const repositoryId = "22222222-2222-4222-8222-222222222222";
const pullRequestId = "33333333-3333-4333-8333-333333333333";
const findingId = "44444444-4444-4444-8444-444444444444";
const runId = "55555555-5555-4555-8555-555555555555";
const proposalId = "66666666-6666-4666-8666-666666666666";
const headSha = "a".repeat(40);
const patchHash = "b".repeat(64);
const now = "2026-07-12T10:00:00Z";

function fixSession(overrides: Partial<FixSessionDetail> = {}): FixSessionDetail {
  return {
    id: sessionId,
    repository_id: repositoryId,
    pull_request_id: pullRequestId,
    finding_id: findingId,
    source_agent_run_id: runId,
    base_sha: "c".repeat(40),
    head_sha: headSha,
    index_version_id: null,
    workspace_index_version_id: null,
    status: "AWAITING_USER_CONFIRMATION",
    current_node: "AWAIT_USER_CONFIRMATION",
    permission_mode: "APPLY_IN_ISOLATED_WORKSPACE",
    workspace_path: "/tmp/tracegate/fix-safe",
    workspace_state_hash: "d".repeat(64),
    cleanup_status: "ACTIVE",
    model_profile: "deepseek/deepseek-chat",
    workflow_version: "tracegate-fix-v1",
    eligibility: { status: "ELIGIBLE", reasons: ["Evidence and exact source range verified"], warnings: [], force_allowed: false },
    allowed_actions: ["CONFIRM", "EXPORT_PATCH", "CANCEL"],
    lock_version: 4,
    cancellation_requested: false,
    input_tokens: 512,
    output_tokens: 230,
    latency_ms: 1840,
    retry_count: 0,
    created_at: now,
    started_at: now,
    finished_at: null,
    error_code: null,
    error_message: null,
    last_active_at: now,
    updated_at: now,
    plan: {
      finding_id: findingId,
      objective: "Prevent a zero divisor",
      root_cause: "The divisor is used before a boundary check.",
      affected_files: ["src/calculate.py"],
      affected_symbols: ["calculate_ratio"],
      constraints: ["Preserve the public API"],
      proposed_steps: ["Guard zero before division", "Exercise the boundary in tests"],
      expected_behavior: "Zero input returns a typed error.",
      validation_strategy: ["Run focused pytest"],
      risk_notes: ["Error behavior changes for invalid input"],
      confidence: 0.91,
    },
    proposal: {
      finding_id: findingId,
      base_sha: "c".repeat(40),
      head_sha: headSha,
      changed_files: ["src/calculate.py"],
      estimated_changed_lines: 3,
      rationale: "Check the boundary before division.",
      assumptions: [],
      validation_commands: [{ argv: ["python", "-m", "pytest", "tests/test_calculate.py", "-q"], command_purpose: "Focused regression", required: true, timeout: 90, expected_result: "exit 0", source: "pyproject.toml" }],
      residual_risks: ["Caller error handling needs human review"],
      confidence: 0.9,
      patch_hash: patchHash,
      created_at: now,
      stale_at: null,
    },
    patch_inspection: { patch_hash: patchHash, changed_files: ["src/calculate.py"], changed_lines: 3, additions: 2, deletions: 1, warnings: ["Authentication-adjacent code: review manually"], requires_confirmation: true },
    confirmation: null,
    validation_plan: { commands: [{ argv: ["python", "-m", "pytest", "tests/test_calculate.py", "-q"], command_purpose: "Focused regression", required: true, timeout: 90, expected_result: "exit 0", source: "pyproject.toml" }], notes: ["No shell expansion is used"] },
    validation_runs: [],
    steps: [],
    re_review: null,
    result: null,
    ...overrides,
  };
}

const patch: FixPatchResponse = {
  fix_session_id: sessionId,
  head_sha: headSha,
  patch_hash: patchHash,
  unified_diff: "diff --git a/src/calculate.py b/src/calculate.py\n--- a/src/calculate.py\n+++ b/src/calculate.py\n@@ -1 +1,2 @@\n+if divisor == 0:\n+    raise ValueError('zero')",
  changed_files: [{ path: "src/calculate.py", status: "modified" }],
  selected_path: "src/calculate.py",
  original: "return total / divisor\n",
  modified: "if divisor == 0:\n    raise ValueError('zero')\nreturn total / divisor\n",
};

function failedResult(): FixResult {
  return {
    id: proposalId,
    fix_session_id: sessionId,
    resolution: "VERIFICATION_FAILED",
    validation_status: "FAILED",
    re_review_status: "not_started",
    residual_findings: ["Division guard regression remains unverified"],
    residual_risks: ["Focused test exited 1"],
    report: {
      fix_session_id: sessionId,
      finding_id: findingId,
      patch_hash: patchHash,
      applied: true,
      validation_status: "FAILED",
      commands_run: [["python", "-m", "pytest"]],
      passed_commands: [],
      failed_commands: [["python", "-m", "pytest"]],
      re_review_status: "not_started",
      finding_resolution: "VERIFICATION_FAILED",
      residual_findings: ["Division guard regression remains unverified"],
      residual_risks: ["Focused test exited 1"],
      final_summary: "The isolated patch was applied, but required validation failed.",
    },
    created_at: now,
  };
}

function client(fetchImpl: typeof fetch = vi.fn<typeof fetch>()): TraceGateApiClient {
  return new TraceGateApiClient({ baseUrl: "http://127.0.0.1:9876/api/v1", token: "test-token-not-secret" }, fetchImpl);
}

function renderView(session: FixSessionDetail, options: { currentHead?: string | null; result?: FixResult | null; apiClient?: TraceGateApiClient } = {}) {
  const apiClient = options.apiClient ?? client();
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><ApiClientProvider client={apiClient}><I18nProvider locale="zh-CN"><FixSessionView session={session} finding={null} evidence={[]} currentHead={options.currentHead === undefined ? headSha : options.currentHead} patch={patch} patchError={null} report={options.result ?? session.result} events={[]} streamError={null} onOpenDiff={() => undefined} onRefresh={() => undefined} client={apiClient} /></I18nProvider></ApiClientProvider></QueryClientProvider>);
}

describe("FixExperience safety UX", () => {
  it("localizes states and renders the authoritative diff with its full hash", () => {
    renderView(fixSession());
    expect(screen.getByRole("heading", { name: "等待用户确认" })).toBeInTheDocument();
    expect(screen.getAllByText(patchHash).length).toBeGreaterThan(0);
    expect(screen.getByText("完整补丁与文件预览")).toBeInTheDocument();
    expect(screen.getAllByText("return total / divisor", { exact: false }).length).toBeGreaterThanOrEqual(2);
    expect(localizedFixStatus("RE_REVIEWING", "en-US")).toBe("Re-reviewing");
    expect(commandText(["python", "-m", "pytest", "tests/a file.py"])).toBe('python -m pytest "tests/a file.py"');
  });

  it("requires an explicit acknowledgement before binding confirmation to the exact hash", async () => {
    const onConfirm = vi.fn();
    render(<I18nProvider locale="zh-CN"><FixConfirmationDialog session={fixSession()} onCancel={() => undefined} onConfirm={onConfirm} busy={false} /></I18nProvider>);
    expect(screen.getByText(patchHash)).toBeInTheDocument();
    expect(screen.getByText("Authentication-adjacent code: review manually")).toBeInTheDocument();
    expect(screen.getByText("python -m pytest tests/test_calculate.py -q", { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/不会 commit、push 或修改原工作区/)).toBeInTheDocument();
    const confirm = screen.getByRole("button", { name: "确认该 Hash 并授权隔离应用" });
    expect(confirm).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox"));
    expect(confirm).toBeEnabled();
    await userEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("blocks apply for a stale Head even when an old confirmation exists", () => {
    const stale = fixSession({ status: "STALE", allowed_actions: ["APPLY"], confirmation: { id: proposalId, fix_session_id: sessionId, patch_hash: patchHash, expires_at: "2099-01-01T00:00:00Z", confirmed_at: now, consumed_at: null, invalidated_at: null, created_at: now } });
    expect(isFixStale(stale, "e".repeat(40))).toBe(true);
    expect(canApplyFix(stale, "e".repeat(40))).toBe(false);
    renderView(stale, { currentHead: "e".repeat(40) });
    expect(screen.getByRole("alert")).toHaveTextContent("Head SHA 已变化");
    expect(screen.getByRole("button", { name: "应用到隔离工作区" })).toBeDisabled();
  });

  it("enables apply only for an unconsumed matching confirmation", () => {
    const confirmed = fixSession({ allowed_actions: ["APPLY"], confirmation: { id: proposalId, fix_session_id: sessionId, patch_hash: patchHash, expires_at: "2099-01-01T00:00:00Z", confirmed_at: now, consumed_at: null, invalidated_at: null, created_at: now } });
    expect(canApplyFix(confirmed, headSha)).toBe(true);
    renderView(confirmed);
    expect(screen.getByRole("button", { name: "应用到隔离工作区" })).toBeEnabled();
  });

  it("shows validation failure, deterministic resolution and residual work without calling it resolved", () => {
    const result = failedResult();
    const failed = fixSession({ status: "FAILED", current_node: "RUN_VALIDATION", allowed_actions: ["ROLLBACK", "DELETE_WORKSPACE", "EXPORT_REPORT"], validation_runs: [{ id: proposalId, fix_session_id: sessionId, sequence: 1, command: ["python", "-m", "pytest"], purpose: "Required suite", required: true, status: "FAILED", return_code: 1, stdout_summary: "1 failed", stderr_summary: "AssertionError", output_truncated: false, error_code: "VALIDATION_FAILED", started_at: now, finished_at: now, duration_ms: 220, created_at: now }], result });
    renderView(failed, { result });
    expect(screen.getAllByText("FAILED").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "VERIFICATION_FAILED" })).toBeInTheDocument();
    expect(screen.getByText("Division guard regression remains unverified")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "RESOLVED" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "回滚隔离工作区" })).toBeEnabled();
  });

  it("surfaces structured API action errors instead of silently advancing state", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify({ error: { code: "lock_conflict", message: "Fix Session lock version is stale" } }), { status: 409, headers: { "Content-Type": "application/json" } }));
    renderView(fixSession({ allowed_actions: ["ROLLBACK"] }), { apiClient: client(fetchMock) });
    await userEvent.click(screen.getByRole("button", { name: "回滚隔离工作区" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Fix Session lock version is stale");
  });

  it("reconnects Fix SSE with Last-Event-ID and aborts without leaking another retry", async () => {
    const controller = new AbortController();
    const event: FixSessionEvent = { event_id: "event-7", sequence: 7, fix_session_id: sessionId, created_at: now, type: "workflow_step", data: { status: "RUNNING_VALIDATION", current_node: "RUN_VALIDATION", message: "running pytest" } };
    let calls = 0;
    const stream: TraceGateApiClient["streamFixSessionEvents"] = async (_id, onEvent, options) => {
      calls += 1;
      if (calls === 1) {
        onEvent(event);
        throw new Error("socket reset");
      }
      expect(options?.lastEventId).toBe("event-7");
      controller.abort();
      return { lastEventId: "event-7" };
    };
    const terminalError = vi.fn();
    await streamFixEventsWithRetry(stream, sessionId, vi.fn(), terminalError, controller.signal, { wait: async () => undefined });
    expect(calls).toBe(2);
    expect(terminalError).not.toHaveBeenCalled();
    expect(fixStreamRetryDelay(0)).toBe(250);
    expect(fixStreamRetryDelay(20)).toBe(4_000);
  });

  it("stops after the bounded number of consecutive SSE reconnect failures", async () => {
    const stream: TraceGateApiClient["streamFixSessionEvents"] = async () => { throw new Error("offline"); };
    const terminalError = vi.fn();
    await streamFixEventsWithRetry(stream, sessionId, vi.fn(), terminalError, new AbortController().signal, { maxAttempts: 3, wait: async () => undefined });
    expect(terminalError).toHaveBeenCalledOnce();
    expect(terminalError.mock.calls[0]?.[0]).toBeInstanceOf(Error);
  });

  it("never forces eligibility silently and requires a separate explicit risk acknowledgement", async () => {
    const risky = fixSession({
      status: "ELIGIBLE",
      current_node: "CHECK_FIX_ELIGIBILITY",
      eligibility: { status: "NEEDS_CONFIRMATION", reasons: ["Verifier confidence is below the automatic threshold"], warnings: ["Human judgement is required"], force_allowed: true },
      allowed_actions: ["PLAN"],
    });
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(JSON.stringify(risky), { status: 200, headers: { "Content-Type": "application/json" } }));
    renderView(risky, { apiClient: client(fetchMock) });

    await userEvent.click(screen.getByRole("button", { name: "检查资格并规划" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const defaultBody = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body)) as { force_eligibility: boolean };
    expect(defaultBody.force_eligibility).toBe(false);

    const forcedButton = screen.getByRole("button", { name: "承担风险，继续规划" });
    expect(forcedButton).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox", { name: /我已理解资格警告/ }));
    expect(forcedButton).toBeEnabled();
    await userEvent.click(forcedButton);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const forcedBody = JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body)) as { force_eligibility: boolean };
    expect(forcedBody.force_eligibility).toBe(true);
  });
});
