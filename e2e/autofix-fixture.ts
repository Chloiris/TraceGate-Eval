import type { Page, Route } from "@playwright/test";
import type { FixPatchResponse, FixSession, FixSessionDetail } from "@tracegate/shared-types";

const fixSessionId = "71000000-0000-4000-8000-000000000001";
const sourceRunId = "71000000-0000-4000-8000-000000000002";
const confirmationId = "71000000-0000-4000-8000-000000000003";
const validationId = "71000000-0000-4000-8000-000000000004";
const resultId = "71000000-0000-4000-8000-000000000005";
const patchHash = "f1".repeat(32);
const timestamp = "2026-07-12T10:00:00Z";

export interface AutofixFixtureContext {
  repositoryId: string;
  pullRequestId: string;
  baseSha: string;
  headSha: string;
}

function summary(detail: FixSessionDetail): FixSession {
  const {
    plan: _plan,
    proposal: _proposal,
    patch_inspection: _inspection,
    confirmation: _confirmation,
    validation_plan: _validationPlan,
    validation_runs: _validationRuns,
    steps: _steps,
    re_review: _reReview,
    result: _result,
    ...session
  } = detail;
  return session;
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

export async function installAutofixUiFixture(page: Page, context: AutofixFixtureContext): Promise<void> {
  let detail: FixSessionDetail | null = null;
  const patch: FixPatchResponse = {
    fix_session_id: fixSessionId,
    head_sha: context.headSha,
    patch_hash: patchHash,
    unified_diff: "diff --git a/service.py b/service.py\n--- a/service.py\n+++ b/service.py\n@@ -1,2 +1,2 @@\n def calculate_total(value: int) -> int:\n-    return value * 2\n+    return value",
    changed_files: [{ path: "service.py", status: "modified" }],
    selected_path: "service.py",
    original: "def calculate_total(value: int) -> int:\n    return value * 2\n",
    modified: "def calculate_total(value: int) -> int:\n    return value\n",
  };

  const transition = (fields: Partial<FixSessionDetail>): FixSessionDetail => {
    if (!detail) throw new Error("Autofix fixture session has not been created");
    detail = { ...detail, ...fields, lock_version: detail.lock_version + 1, updated_at: timestamp, last_active_at: timestamp };
    return detail;
  };

  await page.route("**/api/v1/fix-sessions**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path.endsWith("/fix-sessions") && request.method() === "POST") {
      const input = request.postDataJSON() as { finding_id: string; permission_mode: "APPLY_IN_ISOLATED_WORKSPACE" };
      detail = {
        id: fixSessionId,
        repository_id: context.repositoryId,
        pull_request_id: context.pullRequestId,
        finding_id: input.finding_id,
        source_agent_run_id: sourceRunId,
        base_sha: context.baseSha,
        head_sha: context.headSha,
        index_version_id: null,
        workspace_index_version_id: null,
        status: "CREATED",
        current_node: "LOAD_FINDING",
        permission_mode: input.permission_mode,
        workspace_path: null,
        workspace_state_hash: null,
        cleanup_status: "NOT_CREATED",
        model_profile: "playwright-ui-fixture/not-a-real-model",
        workflow_version: "tracegate-fix-v1",
        eligibility: null,
        allowed_actions: ["PLAN", "CANCEL"],
        lock_version: 0,
        cancellation_requested: false,
        input_tokens: 0,
        output_tokens: 0,
        latency_ms: 0,
        retry_count: 0,
        created_at: timestamp,
        started_at: timestamp,
        finished_at: null,
        error_code: null,
        error_message: null,
        last_active_at: timestamp,
        updated_at: timestamp,
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
      return json(route, detail, 201);
    }

    if (path.endsWith("/fix-sessions") && request.method() === "GET") {
      return json(route, { items: detail ? [summary(detail)] : [], total: detail ? 1 : 0, limit: 50, offset: 0 });
    }

    if (path.endsWith("/events")) {
      return route.fulfill({ status: 200, headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" }, body: "" });
    }

    if (path.endsWith("/patch") && request.method() === "GET") {
      if (url.searchParams.get("download") === "true") {
        return route.fulfill({ status: 200, headers: { "Content-Type": "text/x-diff", "Content-Disposition": `attachment; filename="tracegate-fix-${fixSessionId}.patch"`, "X-TraceGate-Patch-Hash": patchHash }, body: patch.unified_diff });
      }
      return json(route, patch);
    }

    if (path.endsWith("/report") && request.method() === "GET") {
      if (!detail?.result) return json(route, { error: { code: "report_not_ready", message: "Report is not ready" } }, 409);
      if (url.searchParams.get("download") === "true") {
        return route.fulfill({ status: 200, headers: { "Content-Type": "application/json", "Content-Disposition": `attachment; filename="tracegate-fix-${fixSessionId}-report.json"`, "X-TraceGate-Patch-Hash": patchHash }, body: JSON.stringify(detail.result) });
      }
      return json(route, detail.result);
    }

    if (path.endsWith("/workspace") && request.method() === "DELETE") {
      if (detail) detail = { ...detail, cleanup_status: "DELETED", workspace_path: null, workspace_state_hash: null, lock_version: detail.lock_version + 1 };
      return route.fulfill({ status: 204, body: "" });
    }

    if (path.endsWith("/plan") && request.method() === "POST") {
      return json(route, transition({
        status: "PLAN_READY",
        current_node: "PLAN_FIX",
        eligibility: { status: "ELIGIBLE", reasons: ["Fixture Evidence, line range, and Head SHA are internally consistent"], warnings: ["Playwright UI fixture: not public-PR accuracy evidence"], force_allowed: false },
        allowed_actions: ["GENERATE", "CANCEL"],
        input_tokens: 320,
        output_tokens: 180,
        latency_ms: 940,
        plan: {
          finding_id: detail?.finding_id ?? "",
          objective: "Restore the original return-value contract",
          root_cause: "The changed implementation multiplies the returned value while the original contract returned it unchanged.",
          affected_files: ["service.py", "test_service.py"],
          affected_symbols: ["calculate_total", "test_total"],
          constraints: ["Do not commit or push", "Operate only in the isolated worktree"],
          proposed_steps: ["Restore the identity return value", "Update the focused regression expectation"],
          expected_behavior: "calculate_total(2) returns 2",
          validation_strategy: ["Run python -m pytest -q"],
          risk_notes: ["Callers depending on doubled values require human review"],
          confidence: 0.88,
        },
      }));
    }

    if (path.endsWith("/generate") && request.method() === "POST") {
      return json(route, transition({
        status: "AWAITING_USER_CONFIRMATION",
        current_node: "AWAIT_USER_CONFIRMATION",
        allowed_actions: ["CONFIRM", "EXPORT_PATCH", "CANCEL"],
        proposal: {
          finding_id: detail?.finding_id ?? "",
          base_sha: context.baseSha,
          head_sha: context.headSha,
          changed_files: ["service.py"],
          estimated_changed_lines: 2,
          rationale: "Restore the evidence-backed original behavior.",
          assumptions: ["The base implementation is the intended contract"],
          validation_commands: [{ argv: ["python", "-m", "pytest", "-q"], command_purpose: "Focused repository tests", required: true, timeout: 90, expected_result: "exit 0", source: "fixture repository" }],
          residual_risks: ["External callers are outside this fixture"],
          confidence: 0.86,
          patch_hash: patchHash,
          created_at: timestamp,
          stale_at: null,
        },
        patch_inspection: { patch_hash: patchHash, changed_files: ["service.py"], changed_lines: 2, additions: 1, deletions: 1, warnings: ["Behavioral change requires explicit reviewer confirmation", "Playwright UI fixture only"], requires_confirmation: true },
        validation_plan: { commands: [{ argv: ["python", "-m", "pytest", "-q"], command_purpose: "Focused repository tests", required: true, timeout: 90, expected_result: "exit 0", source: "fixture repository" }], notes: ["argv execution only; shell expansion disabled"] },
      }));
    }

    if (path.endsWith("/confirm") && request.method() === "POST") {
      return json(route, transition({
        allowed_actions: ["APPLY", "EXPORT_PATCH", "CANCEL"],
        confirmation: { id: confirmationId, fix_session_id: fixSessionId, patch_hash: patchHash, expires_at: "2099-01-01T00:00:00Z", confirmed_at: timestamp, consumed_at: null, invalidated_at: null, created_at: timestamp },
      }));
    }

    if (path.endsWith("/apply") && request.method() === "POST") {
      return json(route, transition({ status: "PATCH_APPLIED", current_node: "APPLY_PATCH", allowed_actions: ["VALIDATE", "ROLLBACK", "EXPORT_PATCH"], workspace_path: "/tmp/tracegate-playwright-fixture", workspace_state_hash: "a3".repeat(32), cleanup_status: "ACTIVE", confirmation: detail?.confirmation ? { ...detail.confirmation, consumed_at: timestamp } : null }));
    }

    if (path.endsWith("/validate") && request.method() === "POST") {
      return json(route, transition({ status: "VALIDATION_COMPLETE", current_node: "RUN_VALIDATION", allowed_actions: ["RE_REVIEW", "ROLLBACK", "EXPORT_PATCH"], validation_runs: [{ id: validationId, fix_session_id: fixSessionId, sequence: 1, command: ["python", "-m", "pytest", "-q"], purpose: "Focused repository tests", required: true, status: "PASSED", return_code: 0, stdout_summary: "1 passed in 0.04s", stderr_summary: "", output_truncated: false, error_code: null, started_at: timestamp, finished_at: timestamp, duration_ms: 41, created_at: timestamp }] }));
    }

    if (path.endsWith("/re-review") && request.method() === "POST") {
      const result = {
        id: resultId,
        fix_session_id: fixSessionId,
        resolution: "RESOLVED" as const,
        validation_status: "PASSED" as const,
        re_review_status: "completed",
        residual_findings: [],
        residual_risks: ["Public callers were not evaluated by this Playwright fixture"],
        report: {
          fix_session_id: fixSessionId,
          finding_id: detail?.finding_id ?? "",
          patch_hash: patchHash,
          applied: true,
          validation_status: "PASSED" as const,
          commands_run: [["python", "-m", "pytest", "-q"]],
          passed_commands: [["python", "-m", "pytest", "-q"]],
          failed_commands: [],
          re_review_status: "completed",
          finding_resolution: "RESOLVED" as const,
          residual_findings: [],
          residual_risks: ["Public callers were not evaluated by this Playwright fixture"],
          final_summary: "The fixture patch applied in isolation, the fixture command passed, and deterministic fixture re-review resolved the seeded Finding.",
        },
        created_at: timestamp,
      };
      return json(route, transition({ status: "COMPLETED", current_node: "FINALIZE", finished_at: timestamp, allowed_actions: ["EXPORT_PATCH", "EXPORT_REPORT", "ROLLBACK"], re_review: { original_finding_supported: false, residual_findings: [], residual_risks: result.residual_risks, new_high_risk: false, summary: "Fixture re-review no longer supports the seeded Finding.", confidence: 0.9 }, result }));
    }

    if (path.endsWith("/rollback") && request.method() === "POST") {
      return json(route, transition({ status: "ROLLED_BACK", current_node: null, allowed_actions: ["EXPORT_PATCH", "EXPORT_REPORT", "DELETE_WORKSPACE"], workspace_state_hash: "0".repeat(64) }));
    }

    if (path.endsWith(`/fix-sessions/${fixSessionId}`) && request.method() === "GET") {
      if (!detail) return json(route, { error: { code: "not_found", message: "Fixture session not created" } }, 404);
      return json(route, detail);
    }

    return json(route, { error: { code: "fixture_route_missing", message: `${request.method()} ${path}` } }, 404);
  });
}

export async function annotateAutofixFixtureScreenshot(page: Page): Promise<void> {
  await page.evaluate(() => {
    const marker = document.createElement("div");
    marker.dataset.testid = "autofix-fixture-disclosure";
    marker.textContent = "PLAYWRIGHT UI FIXTURE · 非公共 PR 准确率证据 · 非真实模型结果";
    marker.style.cssText = "position:fixed;z-index:9999;left:18px;right:18px;bottom:18px;padding:12px 16px;border:2px solid #ffbe55;border-radius:10px;background:#241a08;color:#ffd98f;font:700 14px ui-monospace,monospace;box-shadow:0 8px 30px #0009;text-align:center";
    document.body.append(marker);
  });
}
