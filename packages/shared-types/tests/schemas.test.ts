import { describe, expect, it } from "vitest";

import {
  componentStatusSchema,
  credentialStatusSchema,
  diagnosticFixWorkspaceListSchema,
  isComponentReady,
  systemStatusSchema,
  settingsSchema,
  settingsUpdateSchema,
  evaluationSummarySchema,
  fixConfirmationSchema,
  fixConfirmationRequestSchema,
  fixSessionDetailSchema,
  fixSessionEventSchema,
  patchProposalSchema,
  notificationKindSchema,
  postFixReportSchema,
  validationCommandSchema,
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

  it("parses bounded residual Fix workspace diagnostics without secret fields", () => {
    const result = diagnosticFixWorkspaceListSchema.parse({
      items: [{
        fix_session_id: "orphan-session-0001",
        repository_id: "repository-0001",
        path: "/managed/autofix/repository-0001/orphan-session-0001/worktree",
        cleanup_status: "ORPHANED",
        last_active_at: "2026-07-12T10:00:00Z",
        expired: true,
      }],
      total: 1,
      retention_hours: 12,
    });

    expect(result.items[0]?.cleanup_status).toBe("ORPHANED");
    expect(JSON.stringify(result)).not.toMatch(/token|secret|key/i);
    expect(() => diagnosticFixWorkspaceListSchema.parse({
      ...result,
      items: [{ ...result.items[0], api_key: "must-not-appear" }],
    })).toThrow();
  });

  it("rejects evaluation summaries that are not marked as real", () => {
    expect(() => evaluationSummarySchema.parse({ is_real_dataset: false })).toThrow();
  });

  it("parses a strict, head-bound Fix Session detail", () => {
    const detail = fixSessionDetailSchema.parse({
      id: "11111111-1111-4111-8111-111111111111",
      repository_id: "22222222-2222-4222-8222-222222222222",
      pull_request_id: "33333333-3333-4333-8333-333333333333",
      finding_id: "44444444-4444-4444-8444-444444444444",
      source_agent_run_id: "55555555-5555-4555-8555-555555555555",
      base_sha: "a".repeat(40),
      head_sha: "b".repeat(40),
      index_version_id: "66666666-6666-4666-8666-666666666666",
      workspace_index_version_id: null,
      status: "AWAITING_USER_CONFIRMATION",
      current_node: "AWAIT_USER_CONFIRMATION",
      permission_mode: "APPLY_IN_ISOLATED_WORKSPACE",
      workspace_path: null,
      workspace_state_hash: null,
      cleanup_status: "ACTIVE",
      model_profile: "deepseek/deepseek-chat",
      workflow_version: "tracegate-fix-v1",
      eligibility: { status: "ELIGIBLE", reasons: [], warnings: [], force_allowed: false },
      allowed_actions: ["CONFIRM", "CANCEL", "EXPORT_PATCH"],
      lock_version: 7,
      cancellation_requested: false,
      input_tokens: 100,
      output_tokens: 25,
      latency_ms: 250,
      retry_count: 0,
      created_at: "2026-07-12T10:00:00Z",
      started_at: "2026-07-12T10:00:01Z",
      finished_at: null,
      error_code: null,
      error_message: null,
      last_active_at: "2026-07-12T10:00:02Z",
      updated_at: "2026-07-12T10:00:02Z",
      plan: null,
      proposal: null,
      patch_inspection: null,
      confirmation: null,
      validation_plan: null,
      validation_runs: [],
      steps: [],
      re_review: null,
      result: null,
    });

    expect(detail.allowed_actions).toContain("CONFIRM");
    expect(() => fixSessionDetailSchema.parse({ ...detail, unknown_state: true })).toThrow();
  });

  it("rejects unsafe paths in structured Patch Proposals", () => {
    expect(() => patchProposalSchema.parse({
      finding_id: "44444444-4444-4444-8444-444444444444",
      base_sha: "a".repeat(40),
      head_sha: "b".repeat(40),
      patch: "diff --git a/../.env b/../.env",
      changed_files: ["../.env"],
      estimated_changed_lines: 1,
      rationale: "unsafe",
      assumptions: [],
      validation_commands: [],
      residual_risks: [],
      confidence: 0.5,
    })).toThrow();
  });

  it("rejects NUL bytes in validation argv", () => {
    expect(() => validationCommandSchema.parse({
      argv: ["pytest", "bad\0argument"],
      command_purpose: "Run tests",
      required: true,
      timeout: 180,
      expected_result: "exit 0",
      source: "pyproject.toml",
    })).toThrow();
  });

  it("never accepts a raw confirmation nonce in confirmation responses", () => {
    expect(() => fixConfirmationSchema.parse({
      id: "11111111-1111-4111-8111-111111111111",
      fix_session_id: "22222222-2222-4222-8222-222222222222",
      patch_hash: "c".repeat(64),
      expires_at: "2026-07-12T10:05:00Z",
      confirmed_at: "2026-07-12T10:00:00Z",
      consumed_at: null,
      invalidated_at: null,
      created_at: "2026-07-12T10:00:00Z",
      confirmation_nonce: "must-not-leave-the-client",
    })).toThrow();
  });

  it("binds confirmation requests only to lock version and patch hash", () => {
    expect(fixConfirmationRequestSchema.parse({
      expected_lock_version: 4,
      patch_hash: "c".repeat(64),
    })).toEqual({ expected_lock_version: 4, patch_hash: "c".repeat(64) });
    expect(() => fixConfirmationRequestSchema.parse({
      expected_lock_version: 4,
      patch_hash: "c".repeat(64),
      confirmation_nonce: "must-not-leave-the-server",
    })).toThrow();
  });

  it("recognizes every controlled Fix lifecycle notification", () => {
    for (const kind of [
      "fix_proposal_ready",
      "fix_awaiting_confirmation",
      "fix_validation_passed",
      "fix_validation_failed",
      "fix_resolved",
      "fix_needs_human_review",
    ]) expect(notificationKindSchema.parse(kind)).toBe(kind);
  });

  it("defaults legacy settings reads without injecting autofix defaults into partial updates", () => {
    const legacy = settingsSchema.parse({
      theme: "system", language: "zh-CN", background_monitoring: false, launch_at_startup: false,
      close_notice_dismissed: false, notifications_enabled: true, model_provider: null, model_base_url: null,
      model_name: null, model_temperature: 0, model_max_output_tokens: 4096, model_timeout_seconds: 60,
      model_max_retries: 2, model_native_structured_output: false, model_streaming_enabled: false,
      model_native_tool_calling: false, model_context_scope: "changed_files", model_input_cost_per_million: 0,
      model_output_cost_per_million: 0, github_poll_interval_seconds: 60, automatic_analysis_enabled: false,
      automatic_analysis_include_drafts: false, automatic_analysis_require_checks_success: false,
      analysis_paused: false, webhook_relay_url: null, webhook_relay_device_id: null, updated_at: "2026-07-12T10:00:00Z",
    });
    expect(legacy.autofix_max_files).toBe(8);
    expect(settingsUpdateSchema.parse({ theme: "dark" })).toEqual({ theme: "dark" });
  });

  it("requires applied, passed validation before RESOLVED", () => {
    expect(() => postFixReportSchema.parse({
      fix_session_id: "11111111-1111-4111-8111-111111111111",
      finding_id: "22222222-2222-4222-8222-222222222222",
      patch_hash: "d".repeat(64),
      applied: false,
      validation_status: "FAILED",
      commands_run: [],
      passed_commands: [],
      failed_commands: [["pytest"]],
      re_review_status: "completed",
      finding_resolution: "RESOLVED",
      residual_findings: [],
      residual_risks: [],
      final_summary: "not actually resolved",
    })).toThrow();
  });

  it("parses only declared Fix SSE event payloads", () => {
    const event = fixSessionEventSchema.parse({
      event_id: "9",
      sequence: 9,
      fix_session_id: "11111111-1111-4111-8111-111111111111",
      created_at: "2026-07-12T10:00:00Z",
      type: "validation_output",
      data: {
        validation_run_id: "22222222-2222-4222-8222-222222222222",
        stream: "stdout",
        chunk: "1 passed",
        truncated: false,
      },
    });
    expect(event.type).toBe("validation_output");
    expect(() => fixSessionEventSchema.parse({ ...event, secret: "should-be-rejected" })).toThrow();
  });
});
