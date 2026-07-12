import {
  apiConnectionSchema,
  agentRunListSchema,
  agentRunDetailSchema,
  agentEvidenceGraphSchema,
  agentRunSchema,
  agentDescriptorListSchema,
  agentDescriptorSchema,
  agentStepSchema,
  analyzeResponseSchema,
  evidenceSchema,
  evaluationSummarySchema,
  errorEnvelopeSchema,
  findingSchema,
  fixActionRequestSchema,
  fixApplyRequestSchema,
  fixConfirmationRequestSchema,
  fixPatchResponseSchema,
  fixPlanRequestSchema,
  fixResultSchema,
  fixSessionCreateSchema,
  fixSessionDetailSchema,
  fixSessionEventSchema,
  fixSessionListSchema,
  healthResponseSchema,
  onboardingStateSchema,
  onboardingUpdateSchema,
  notificationRecordSchema,
  indexVersionSchema,
  pullRequestDiffSchema,
  pullRequestListSchema,
  pullRequestSchema,
  reviewMapSchema,
  changeTourSchema,
  checkRunListSchema,
  changedFileDetailListSchema,
  pullRequestCommitListSchema,
  connectionComponentSchema,
  connectionTestResponseSchema,
  diagnosticsSchema,
  diagnosticFixWorkspaceListSchema,
  repositoryCreateSchema,
  repositoryGraphSchema,
  repositoryListSchema,
  repositorySchema,
  repositorySyncSchema,
  repositorySummarySchema,
  repositoryUpdateSchema,
  settingsSchema,
  settingsUpdateSchema,
  systemStatusSchema,
  toolDescriptorListSchema,
  toolDescriptorSchema,
  updateStatusSchema,
  type ApiConnection,
  type AgentRun,
  type AgentRunList,
  type AgentRunDetail,
  type AgentEvidenceGraph,
  type AgentDescriptor,
  type AgentStep,
  type AnalyzeResponse,
  type Evidence,
  type EvaluationSummary,
  type Finding,
  type FixActionRequest,
  type FixApplyRequest,
  type FixConfirmationRequest,
  type FixPatchResponse,
  type FixPlanRequest,
  type FixResult,
  type FixSessionCreate,
  type FixSessionDetail,
  type FixSessionEvent,
  type FixSessionList,
  type HealthResponse,
  type OnboardingState,
  type OnboardingUpdate,
  type NotificationCreate,
  type NotificationRecord,
  type IndexVersion,
  type PullRequest,
  type PullRequestDiff,
  type PullRequestList,
  type ReviewMap,
  type ChangeTour,
  type CheckRunList,
  type ChangedFileDetail,
  type PullRequestCommit,
  type ConnectionComponent,
  type ConnectionTestResponse,
  type Diagnostics,
  type DiagnosticFixWorkspaceList,
  type Repository,
  type RepositoryCreate,
  type RepositoryGraph,
  type RepositoryList,
  type RepositorySync,
  type RepositorySummary,
  type RepositoryUpdate,
  type Settings,
  type SettingsUpdate,
  type SystemStatus,
  type ToolDescriptor,
  type UpdateStatus,
} from "@tracegate/shared-types";
import type { ZodType } from "zod";

export type ApiErrorKind =
  | "configuration"
  | "network"
  | "http"
  | "invalid_response";

interface ApiErrorOptions {
  kind: ApiErrorKind;
  status?: number;
  code?: string;
  cause?: unknown;
}

export class TraceGateApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | undefined;
  readonly code: string | undefined;

  constructor(message: string, options: ApiErrorOptions) {
    super(message, { cause: options.cause });
    this.name = "TraceGateApiError";
    this.kind = options.kind;
    this.status = options.status;
    this.code = options.code;
  }
}

export type FetchImplementation = typeof fetch;

export type RunStreamEvent =
  | { type: "step"; data: AgentStep }
  | { type: "run"; data: AgentRun };

export interface FixSessionListFilters {
  pullRequestId?: string;
  findingId?: string;
  limit?: number;
  offset?: number;
}

export interface FixStreamOptions {
  signal?: AbortSignal;
  lastEventId?: string;
  maxBufferBytes?: number;
  maxSeenEventIds?: number;
}

export interface FixStreamCursor {
  lastEventId: string | null;
}

export interface DownloadArtifact {
  blob: Blob;
  filename: string;
  contentType: string;
  patchHash: string | null;
}

const DEFAULT_SSE_BUFFER_BYTES = 1_000_000;
const DEFAULT_SSE_SEEN_EVENT_IDS = 1_024;

function normalizedBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, "");
}

export class TraceGateApiClient {
  readonly #connection: ApiConnection;
  readonly #fetch: FetchImplementation;

  constructor(connection: ApiConnection, fetchImplementation: FetchImplementation = fetch) {
    const parsed = apiConnectionSchema.safeParse(connection);
    if (!parsed.success) {
      throw new TraceGateApiError(
        "本地 API 连接尚未配置。浏览器开发模式需要显式设置 API Token。",
        { kind: "configuration", cause: parsed.error },
      );
    }
    this.#connection = {
      baseUrl: normalizedBaseUrl(parsed.data.baseUrl),
      token: parsed.data.token,
    };
    // WebKit and some embedded Chromium builds require fetch to retain its
    // global receiver. Keeping a bound function also makes the client safe to
    // store and invoke from class fields.
    this.#fetch = fetchImplementation.bind(globalThis);
  }

  async health(signal?: AbortSignal): Promise<HealthResponse> {
    return this.#request("/health", healthResponseSchema, requestSignal(signal));
  }

  async getSystemStatus(signal?: AbortSignal): Promise<SystemStatus> {
    return this.#request("/system/status", systemStatusSchema, requestSignal(signal));
  }

  async testConnection(
    component: ConnectionComponent,
    signal?: AbortSignal,
  ): Promise<ConnectionTestResponse> {
    return this.#request("/connections/test", connectionTestResponseSchema, {
      method: "POST",
      body: JSON.stringify({ component: connectionComponentSchema.parse(component) }),
      ...requestSignal(signal),
    });
  }

  async getSettings(signal?: AbortSignal): Promise<Settings> {
    return this.#request("/settings", settingsSchema, requestSignal(signal));
  }

  async updateSettings(update: SettingsUpdate, signal?: AbortSignal): Promise<Settings> {
    const body = settingsUpdateSchema.parse(update);
    return this.#request("/settings", settingsSchema, {
      method: "PUT",
      body: JSON.stringify(body),
      ...requestSignal(signal),
    });
  }

  async getOnboarding(signal?: AbortSignal): Promise<OnboardingState> {
    return this.#request("/onboarding", onboardingStateSchema, requestSignal(signal));
  }

  async updateOnboarding(update: OnboardingUpdate, signal?: AbortSignal): Promise<OnboardingState> {
    const body = onboardingUpdateSchema.parse(update);
    return this.#request("/onboarding", onboardingStateSchema, {
      method: "PUT",
      body: JSON.stringify(body),
      ...requestSignal(signal),
    });
  }

  async listRepositories(signal?: AbortSignal): Promise<RepositoryList> {
    return this.#request("/repositories", repositoryListSchema, requestSignal(signal));
  }

  async createRepository(input: RepositoryCreate, signal?: AbortSignal): Promise<Repository> {
    const body = repositoryCreateSchema.parse(input);
    return this.#request("/repositories", repositorySchema, {
      method: "POST",
      body: JSON.stringify(body),
      ...requestSignal(signal),
    });
  }

  async deleteRepository(repositoryId: string, signal?: AbortSignal): Promise<void> {
    await this.#requestVoid(`/repositories/${encodeURIComponent(repositoryId)}`, {
      method: "DELETE",
      ...requestSignal(signal),
    });
  }

  async clearRepositoryCache(repositoryId: string, signal?: AbortSignal): Promise<void> {
    await this.#requestVoid(`/repositories/${encodeURIComponent(repositoryId)}/cache`, {
      method: "DELETE",
      ...requestSignal(signal),
    });
  }

  async getRepositorySummary(repositoryId: string, signal?: AbortSignal): Promise<RepositorySummary> {
    return this.#request(
      `/repositories/${encodeURIComponent(repositoryId)}/summary`,
      repositorySummarySchema,
      requestSignal(signal),
    );
  }

  async updateRepository(
    repositoryId: string,
    update: RepositoryUpdate,
    signal?: AbortSignal,
  ): Promise<Repository> {
    const body = repositoryUpdateSchema.parse(update);
    return this.#request(`/repositories/${encodeURIComponent(repositoryId)}`, repositorySchema, {
      method: "PUT",
      body: JSON.stringify(body),
      ...requestSignal(signal),
    });
  }

  async syncRepository(repositoryId: string, signal?: AbortSignal): Promise<RepositorySync> {
    return this.#request(
      `/repositories/${encodeURIComponent(repositoryId)}/sync`,
      repositorySyncSchema,
      { method: "POST", ...requestSignal(signal) },
    );
  }

  async indexRepository(repositoryId: string, signal?: AbortSignal): Promise<IndexVersion> {
    return this.#request(
      `/repositories/${encodeURIComponent(repositoryId)}/index`,
      indexVersionSchema,
      { method: "POST", ...requestSignal(signal) },
    );
  }

  async getRepositoryGraph(repositoryId: string, signal?: AbortSignal): Promise<RepositoryGraph> {
    return this.#request(
      `/repositories/${encodeURIComponent(repositoryId)}/graph`,
      repositoryGraphSchema,
      requestSignal(signal),
    );
  }

  async listPullRequests(repositoryId?: string, signal?: AbortSignal): Promise<PullRequestList> {
    const query = repositoryId ? `?repository_id=${encodeURIComponent(repositoryId)}` : "";
    return this.#request(`/pull-requests${query}`, pullRequestListSchema, requestSignal(signal));
  }

  async getPullRequest(pullRequestId: string, signal?: AbortSignal): Promise<PullRequest> {
    return this.#request(
      `/pull-requests/${encodeURIComponent(pullRequestId)}`,
      pullRequestSchema,
      requestSignal(signal),
    );
  }

  async listCheckRuns(pullRequestId: string, signal?: AbortSignal): Promise<CheckRunList> {
    return this.#request(
      `/pull-requests/${encodeURIComponent(pullRequestId)}/checks`,
      checkRunListSchema,
      requestSignal(signal),
    );
  }

  async listPullRequestCommits(
    pullRequestId: string,
    signal?: AbortSignal,
  ): Promise<PullRequestCommit[]> {
    return this.#request(
      `/pull-requests/${encodeURIComponent(pullRequestId)}/commits`,
      pullRequestCommitListSchema,
      requestSignal(signal),
    );
  }

  async listPullRequestFiles(
    pullRequestId: string,
    signal?: AbortSignal,
  ): Promise<ChangedFileDetail[]> {
    return this.#request(
      `/pull-requests/${encodeURIComponent(pullRequestId)}/files`,
      changedFileDetailListSchema,
      requestSignal(signal),
    );
  }

  async getPullRequestDiff(
    pullRequestId: string,
    path?: string,
    signal?: AbortSignal,
  ): Promise<PullRequestDiff> {
    const query = path ? `?path=${encodeURIComponent(path)}` : "";
    return this.#request(
      `/pull-requests/${encodeURIComponent(pullRequestId)}/diff${query}`,
      pullRequestDiffSchema,
      requestSignal(signal),
    );
  }

  async getPullRequestGraph(pullRequestId: string, signal?: AbortSignal): Promise<ReviewMap> {
    return this.#request(
      `/pull-requests/${encodeURIComponent(pullRequestId)}/graph`,
      reviewMapSchema,
      requestSignal(signal),
    );
  }

  async getPullRequestTour(pullRequestId: string, signal?: AbortSignal): Promise<ChangeTour> {
    return this.#request(
      `/pull-requests/${encodeURIComponent(pullRequestId)}/tour`,
      changeTourSchema,
      requestSignal(signal),
    );
  }

  async analyzePullRequest(
    pullRequestId: string,
    force = false,
    signal?: AbortSignal,
  ): Promise<AnalyzeResponse> {
    return this.#request(
      `/pull-requests/${encodeURIComponent(pullRequestId)}/analyze?force=${String(force)}`,
      analyzeResponseSchema,
      { method: "POST", ...requestSignal(signal) },
    );
  }

  async listRuns(pullRequestId?: string, signal?: AbortSignal): Promise<AgentRunList> {
    const query = pullRequestId ? `?pull_request_id=${encodeURIComponent(pullRequestId)}` : "";
    return this.#request(`/runs${query}`, agentRunListSchema, requestSignal(signal));
  }

  async getRun(runId: string, signal?: AbortSignal): Promise<AgentRunDetail> {
    return this.#request(`/runs/${encodeURIComponent(runId)}`, agentRunDetailSchema, requestSignal(signal));
  }

  async getRunEvidenceGraph(runId: string, signal?: AbortSignal): Promise<AgentEvidenceGraph> {
    return this.#request(
      `/runs/${encodeURIComponent(runId)}/graph`,
      agentEvidenceGraphSchema,
      requestSignal(signal),
    );
  }

  async cancelRun(runId: string, signal?: AbortSignal): Promise<AgentRun> {
    return this.#request(`/runs/${encodeURIComponent(runId)}/cancel`, agentRunSchema, {
      method: "POST",
      ...requestSignal(signal),
    });
  }

  async retryRun(runId: string, signal?: AbortSignal): Promise<AnalyzeResponse> {
    return this.#request(`/runs/${encodeURIComponent(runId)}/retry`, analyzeResponseSchema, {
      method: "POST",
      ...requestSignal(signal),
    });
  }

  async listFindings(runId?: string, signal?: AbortSignal): Promise<Finding[]> {
    const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
    return this.#request(`/findings${query}`, findingSchema.array(), requestSignal(signal));
  }

  async listEvidence(runId?: string, signal?: AbortSignal): Promise<Evidence[]> {
    const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
    return this.#request(`/evidence${query}`, evidenceSchema.array(), requestSignal(signal));
  }

  async createFixSession(
    input: FixSessionCreate,
    signal?: AbortSignal,
    idempotencyKey?: string,
  ): Promise<FixSessionDetail> {
    const body = fixSessionCreateSchema.parse(input);
    return this.#request("/fix-sessions", fixSessionDetailSchema, {
      method: "POST",
      headers: idempotencyHeaders(idempotencyKey),
      body: JSON.stringify(body),
      ...requestSignal(signal),
    });
  }

  async listFixSessions(
    filters: FixSessionListFilters = {},
    signal?: AbortSignal,
  ): Promise<FixSessionList> {
    const query = new URLSearchParams();
    if (filters.pullRequestId) query.set("pull_request_id", filters.pullRequestId);
    if (filters.findingId) query.set("finding_id", filters.findingId);
    if (filters.limit !== undefined) query.set("limit", String(filters.limit));
    if (filters.offset !== undefined) query.set("offset", String(filters.offset));
    const suffix = query.size > 0 ? `?${query.toString()}` : "";
    return this.#request(`/fix-sessions${suffix}`, fixSessionListSchema, requestSignal(signal));
  }

  async listFixWorkspaces(signal?: AbortSignal): Promise<DiagnosticFixWorkspaceList> {
    return this.#request(
      "/fix-workspaces",
      diagnosticFixWorkspaceListSchema,
      requestSignal(signal),
    );
  }

  async cleanupFixWorkspace(
    fixSessionId: string,
    signal?: AbortSignal,
    idempotencyKey?: string,
  ): Promise<void> {
    await this.#requestVoid(`/fix-workspaces/${encodeURIComponent(fixSessionId)}`, {
      method: "DELETE",
      headers: idempotencyHeaders(idempotencyKey),
      ...requestSignal(signal),
    });
  }

  async getFixSession(fixSessionId: string, signal?: AbortSignal): Promise<FixSessionDetail> {
    return this.#request(
      `/fix-sessions/${encodeURIComponent(fixSessionId)}`,
      fixSessionDetailSchema,
      requestSignal(signal),
    );
  }

  async planFixSession(
    fixSessionId: string,
    input: FixPlanRequest,
    signal?: AbortSignal,
    idempotencyKey?: string,
  ): Promise<FixSessionDetail> {
    return this.#fixAction(fixSessionId, "plan", fixPlanRequestSchema.parse(input), signal, idempotencyKey);
  }

  async generateFixPatch(
    fixSessionId: string,
    input: FixActionRequest,
    signal?: AbortSignal,
    idempotencyKey?: string,
  ): Promise<FixSessionDetail> {
    return this.#fixAction(fixSessionId, "generate", fixActionRequestSchema.parse(input), signal, idempotencyKey);
  }

  async confirmFixSession(
    fixSessionId: string,
    input: FixConfirmationRequest,
    signal?: AbortSignal,
    idempotencyKey?: string,
  ): Promise<FixSessionDetail> {
    return this.#fixAction(fixSessionId, "confirm", fixConfirmationRequestSchema.parse(input), signal, idempotencyKey);
  }

  async applyFixSession(
    fixSessionId: string,
    input: FixApplyRequest,
    signal?: AbortSignal,
    idempotencyKey?: string,
  ): Promise<FixSessionDetail> {
    return this.#fixAction(fixSessionId, "apply", fixApplyRequestSchema.parse(input), signal, idempotencyKey);
  }

  async validateFixSession(
    fixSessionId: string,
    input: FixActionRequest,
    signal?: AbortSignal,
    idempotencyKey?: string,
  ): Promise<FixSessionDetail> {
    return this.#fixAction(fixSessionId, "validate", fixActionRequestSchema.parse(input), signal, idempotencyKey);
  }

  async rereviewFixSession(
    fixSessionId: string,
    input: FixActionRequest,
    signal?: AbortSignal,
    idempotencyKey?: string,
  ): Promise<FixSessionDetail> {
    return this.#fixAction(fixSessionId, "re-review", fixActionRequestSchema.parse(input), signal, idempotencyKey);
  }

  async cancelFixSession(
    fixSessionId: string,
    input: FixActionRequest,
    signal?: AbortSignal,
    idempotencyKey?: string,
  ): Promise<FixSessionDetail> {
    return this.#fixAction(fixSessionId, "cancel", fixActionRequestSchema.parse(input), signal, idempotencyKey);
  }

  async rollbackFixSession(
    fixSessionId: string,
    input: FixActionRequest,
    signal?: AbortSignal,
    idempotencyKey?: string,
  ): Promise<FixSessionDetail> {
    return this.#fixAction(fixSessionId, "rollback", fixActionRequestSchema.parse(input), signal, idempotencyKey);
  }

  async deleteFixWorkspace(
    fixSessionId: string,
    expectedLockVersion: number,
    signal?: AbortSignal,
    idempotencyKey?: string,
  ): Promise<void> {
    const body = fixActionRequestSchema.parse({ expected_lock_version: expectedLockVersion });
    await this.#requestVoid(`/fix-sessions/${encodeURIComponent(fixSessionId)}/workspace`, {
      method: "DELETE",
      headers: idempotencyHeaders(idempotencyKey),
      body: JSON.stringify(body),
      ...requestSignal(signal),
    });
  }

  async getFixPatch(
    fixSessionId: string,
    path?: string,
    signal?: AbortSignal,
  ): Promise<FixPatchResponse> {
    const query = path ? `?path=${encodeURIComponent(path)}` : "";
    return this.#request(
      `/fix-sessions/${encodeURIComponent(fixSessionId)}/patch${query}`,
      fixPatchResponseSchema,
      requestSignal(signal),
    );
  }

  async getFixReport(fixSessionId: string, signal?: AbortSignal): Promise<FixResult> {
    return this.#request(
      `/fix-sessions/${encodeURIComponent(fixSessionId)}/report`,
      fixResultSchema,
      requestSignal(signal),
    );
  }

  async downloadFixPatch(fixSessionId: string, signal?: AbortSignal): Promise<DownloadArtifact> {
    return this.#requestArtifact(
      `/fix-sessions/${encodeURIComponent(fixSessionId)}/patch?download=true`,
      "text/x-diff, text/plain;q=0.9",
      `tracegate-fix-${fixSessionId}.patch`,
      signal,
    );
  }

  async downloadFixReport(fixSessionId: string, signal?: AbortSignal): Promise<DownloadArtifact> {
    return this.#requestArtifact(
      `/fix-sessions/${encodeURIComponent(fixSessionId)}/report?download=true`,
      "application/json",
      `tracegate-fix-${fixSessionId}-report.json`,
      signal,
    );
  }

  async recordNotification(input: NotificationCreate, signal?: AbortSignal): Promise<NotificationRecord> {
    return this.#request("/notifications", notificationRecordSchema, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      ...requestSignal(signal),
    });
  }

  async getEvaluations(signal?: AbortSignal): Promise<EvaluationSummary> {
    return this.#request("/evaluations", evaluationSummarySchema, requestSignal(signal));
  }

  async listAgents(signal?: AbortSignal): Promise<AgentDescriptor[]> {
    return this.#request("/agents", agentDescriptorListSchema, requestSignal(signal));
  }

  async setAgentEnabled(name: string, enabled: boolean, signal?: AbortSignal): Promise<AgentDescriptor> {
    return this.#request(`/agents/${encodeURIComponent(name)}`, agentDescriptorSchema, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
      ...requestSignal(signal),
    });
  }

  async listTools(signal?: AbortSignal): Promise<ToolDescriptor[]> {
    return this.#request("/tools", toolDescriptorListSchema, requestSignal(signal));
  }

  async setToolEnabled(name: string, enabled: boolean, signal?: AbortSignal): Promise<ToolDescriptor> {
    return this.#request(`/tools/${encodeURIComponent(name)}`, toolDescriptorSchema, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
      ...requestSignal(signal),
    });
  }

  async getDiagnostics(signal?: AbortSignal): Promise<Diagnostics> {
    return this.#request("/diagnostics", diagnosticsSchema, requestSignal(signal));
  }

  async getUpdateStatus(signal?: AbortSignal): Promise<UpdateStatus> {
    return this.#request("/system/update", updateStatusSchema, requestSignal(signal));
  }

  async streamRunEvents(
    runId: string,
    onEvent: (event: RunStreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    let response: Response;
    try {
      response = await this.#fetch(
        `${this.#connection.baseUrl}/runs/${encodeURIComponent(runId)}/events`,
        {
          headers: {
            Accept: "text/event-stream",
            Authorization: `Bearer ${this.#connection.token}`,
          },
          ...requestSignal(signal),
        },
      );
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") throw error;
      throw new TraceGateApiError("Agent Trace 流连接失败。", { kind: "network", cause: error });
    }
    if (!response.ok || !response.body) {
      throw new TraceGateApiError(`Agent Trace 流请求失败（HTTP ${response.status}）。`, {
        kind: "http",
        status: response.status,
      });
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const eventName = block.match(/^event:\s*(.+)$/m)?.[1];
        const data = block.match(/^data:\s*(.+)$/m)?.[1];
        if (eventName === "step" && data) {
          onEvent({ type: "step", data: agentStepSchema.parse(JSON.parse(data)) });
        } else if (eventName === "run" && data) {
          onEvent({ type: "run", data: agentRunSchema.parse(JSON.parse(data)) });
        }
        boundary = buffer.indexOf("\n\n");
      }
      if (done) break;
    }
  }

  async streamFixSessionEvents(
    fixSessionId: string,
    onEvent: (event: FixSessionEvent) => void,
    options: FixStreamOptions = {},
  ): Promise<FixStreamCursor> {
    const maxBufferBytes = options.maxBufferBytes ?? DEFAULT_SSE_BUFFER_BYTES;
    const maxSeenEventIds = options.maxSeenEventIds ?? DEFAULT_SSE_SEEN_EVENT_IDS;
    if (!Number.isSafeInteger(maxBufferBytes) || maxBufferBytes < 1_024 || maxBufferBytes > 10_000_000) {
      throw new TraceGateApiError("Fix SSE 缓冲区限制无效。", { kind: "configuration" });
    }
    if (!Number.isSafeInteger(maxSeenEventIds) || maxSeenEventIds < 1 || maxSeenEventIds > 10_000) {
      throw new TraceGateApiError("Fix SSE 去重窗口限制无效。", { kind: "configuration" });
    }

    const headers: Record<string, string> = {
      Accept: "text/event-stream",
      Authorization: `Bearer ${this.#connection.token}`,
      "Cache-Control": "no-cache",
    };
    if (options.lastEventId) headers["Last-Event-ID"] = options.lastEventId;

    let response: Response;
    try {
      response = await this.#fetch(
        `${this.#connection.baseUrl}/fix-sessions/${encodeURIComponent(fixSessionId)}/events`,
        { headers, ...requestSignal(options.signal) },
      );
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") throw error;
      throw new TraceGateApiError("Fix Session 事件流连接失败。", { kind: "network", cause: error });
    }
    if (!response.ok) {
      throw await structuredHttpError(response, "Fix Session 事件流请求失败");
    }
    if (!response.body) {
      throw new TraceGateApiError("Fix Session 事件流响应没有可读取的正文。", {
        kind: "invalid_response",
        status: response.status,
      });
    }
    const contentType = response.headers.get("Content-Type")?.toLowerCase() ?? "";
    if (!contentType.includes("text/event-stream")) {
      throw new TraceGateApiError("Fix Session 事件流返回了错误的 Content-Type。", {
        kind: "invalid_response",
        status: response.status,
      });
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const seen = new Set<string>();
    const seenOrder: string[] = [];
    let buffer = "";
    let lastEventId = options.lastEventId ?? null;
    if (options.lastEventId) {
      seen.add(options.lastEventId);
      seenOrder.push(options.lastEventId);
    }

    const consumeBlock = (block: string): void => {
      const parsed = parseSseBlock(block);
      if (!parsed || parsed.data === "") return;
      if (parsed.id !== null) lastEventId = parsed.id;
      const dedupeId = parsed.id;
      if (dedupeId !== null && seen.has(dedupeId)) return;

      let event: FixSessionEvent;
      try {
        event = fixSessionEventSchema.parse(JSON.parse(parsed.data));
      } catch (error) {
        throw new TraceGateApiError("Fix Session 事件流包含无法识别的数据。", {
          kind: "invalid_response",
          status: response.status,
          cause: error,
        });
      }
      if (parsed.event !== null && parsed.event !== event.type) {
        throw new TraceGateApiError("Fix Session SSE 事件名与载荷类型不一致。", {
          kind: "invalid_response",
          status: response.status,
        });
      }
      if (parsed.id !== null && parsed.id !== event.event_id) {
        throw new TraceGateApiError("Fix Session SSE 事件 ID 与载荷不一致。", {
          kind: "invalid_response",
          status: response.status,
        });
      }
      if (dedupeId !== null) {
        seen.add(dedupeId);
        seenOrder.push(dedupeId);
        if (seenOrder.length > maxSeenEventIds) {
          const expired = seenOrder.shift();
          if (expired !== undefined) seen.delete(expired);
        }
      }
      onEvent(event);
    };

    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let boundary = findSseBoundary(buffer);
      while (boundary !== null) {
        const block = buffer.slice(0, boundary.index);
        buffer = buffer.slice(boundary.index + boundary.length);
        if (utf8Length(block) > maxBufferBytes) {
          await reader.cancel();
          throw new TraceGateApiError("Fix Session SSE 单事件超过安全上限。", {
            kind: "invalid_response",
            status: response.status,
          });
        }
        consumeBlock(block);
        boundary = findSseBoundary(buffer);
      }
      if (utf8Length(buffer) > maxBufferBytes) {
        await reader.cancel();
        throw new TraceGateApiError("Fix Session SSE 缓冲区超过安全上限。", {
          kind: "invalid_response",
          status: response.status,
        });
      }
      if (done) {
        if (buffer.trim() !== "") consumeBlock(buffer);
        break;
      }
    }
    return { lastEventId };
  }

  async #fixAction(
    fixSessionId: string,
    action: "plan" | "generate" | "confirm" | "apply" | "validate" | "re-review" | "cancel" | "rollback",
    body: FixActionRequest | FixPlanRequest | FixConfirmationRequest | FixApplyRequest,
    signal?: AbortSignal,
    idempotencyKey?: string,
  ): Promise<FixSessionDetail> {
    return this.#request(
      `/fix-sessions/${encodeURIComponent(fixSessionId)}/${action}`,
      fixSessionDetailSchema,
      {
        method: "POST",
        headers: idempotencyHeaders(idempotencyKey),
        body: JSON.stringify(body),
        ...requestSignal(signal),
      },
    );
  }

  async #requestArtifact(
    path: string,
    accept: string,
    fallbackFilename: string,
    signal?: AbortSignal,
  ): Promise<DownloadArtifact> {
    let response: Response;
    try {
      response = await this.#fetch(`${this.#connection.baseUrl}${path}`, {
        headers: {
          Accept: accept,
          Authorization: `Bearer ${this.#connection.token}`,
        },
        ...requestSignal(signal),
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") throw error;
      throw new TraceGateApiError("无法下载 TraceGate 修复产物。", { kind: "network", cause: error });
    }
    if (!response.ok) {
      throw await structuredHttpError(response, "修复产物下载失败");
    }
    const filename = safeDownloadFilename(response.headers.get("Content-Disposition"), fallbackFilename);
    const patchHash = response.headers.get("X-TraceGate-Patch-Hash");
    if (patchHash !== null && !/^[0-9a-f]{64}$/.test(patchHash)) {
      throw new TraceGateApiError("修复产物返回了无效的 Patch Hash。", {
        kind: "invalid_response",
        status: response.status,
      });
    }
    return {
      blob: await response.blob(),
      filename,
      contentType: response.headers.get("Content-Type") ?? "application/octet-stream",
      patchHash,
    };
  }

  async #request<T>(
    path: string,
    schema: ZodType<T>,
    init: RequestInit,
  ): Promise<T> {
    let response: Response;
    try {
      response = await this.#fetch(`${this.#connection.baseUrl}${path}`, {
        ...init,
        headers: mergeRequestHeaders(init.headers, this.#connection.token, init.body !== undefined),
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        throw error;
      }
      const detail = error instanceof Error && error.message.trim() !== ""
        ? `：${error.message}`
        : "";
      throw new TraceGateApiError(`无法连接 TraceGate 本地后端${detail}。`, {
        kind: "network",
        cause: error,
      });
    }

    const payload = await parseJson(response);
    if (!response.ok) {
      const envelope = errorEnvelopeSchema.safeParse(payload);
      const errorOptions: ApiErrorOptions = {
        kind: "http",
        status: response.status,
      };
      if (envelope.success) {
        errorOptions.code = envelope.data.error.code;
      }
      throw new TraceGateApiError(
        envelope.success ? envelope.data.error.message : `本地 API 请求失败（HTTP ${response.status}）。`,
        errorOptions,
      );
    }

    const parsed = schema.safeParse(payload);
    if (!parsed.success) {
      throw new TraceGateApiError("本地 API 返回了无法识别的数据格式。", {
        kind: "invalid_response",
        status: response.status,
        cause: parsed.error,
      });
    }
    return parsed.data;
  }

  async #requestVoid(path: string, init: RequestInit): Promise<void> {
    let response: Response;
    try {
      response = await this.#fetch(`${this.#connection.baseUrl}${path}`, {
        ...init,
        headers: mergeRequestHeaders(init.headers, this.#connection.token, init.body !== undefined),
      });
    } catch (error) {
      throw new TraceGateApiError("无法连接 TraceGate 本地后端。", { kind: "network", cause: error });
    }
    if (!response.ok) {
      throw await structuredHttpError(response, "本地 API 请求失败");
    }
  }
}

function requestSignal(signal?: AbortSignal): Pick<RequestInit, "signal"> {
  return signal === undefined ? {} : { signal };
}

async function parseJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch (error) {
    throw new TraceGateApiError("本地 API 返回了非 JSON 响应。", {
      kind: "invalid_response",
      status: response.status,
      cause: error,
    });
  }
}

async function structuredHttpError(response: Response, fallback: string): Promise<TraceGateApiError> {
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    // Some infrastructure errors are intentionally bodyless. Preserve the
    // real HTTP status instead of replacing it with an invalid-JSON error.
  }
  const envelope = errorEnvelopeSchema.safeParse(payload);
  return new TraceGateApiError(
    envelope.success ? envelope.data.error.message : `${fallback}（HTTP ${response.status}）。`,
    {
      kind: "http",
      status: response.status,
      ...(envelope.success ? { code: envelope.data.error.code } : {}),
    },
  );
}

function idempotencyHeaders(value?: string): Record<string, string> {
  const key = value?.trim() || globalThis.crypto.randomUUID();
  if (key.length < 8 || key.length > 200 || /[\r\n]/.test(key)) {
    throw new TraceGateApiError("Idempotency-Key 格式无效。", { kind: "configuration" });
  }
  return { "Idempotency-Key": key };
}

function mergeRequestHeaders(
  initial: HeadersInit | undefined,
  token: string,
  hasBody: boolean,
): Record<string, string> {
  const headers = new Headers(initial);
  headers.set("Accept", "application/json");
  headers.set("Authorization", `Bearer ${token}`);
  if (hasBody && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  return Object.fromEntries(headers.entries());
}

function findSseBoundary(value: string): { index: number; length: number } | null {
  const match = /\r?\n\r?\n/.exec(value);
  return match ? { index: match.index, length: match[0].length } : null;
}

function utf8Length(value: string): number {
  return new TextEncoder().encode(value).byteLength;
}

function parseSseBlock(block: string): { event: string | null; id: string | null; data: string } | null {
  let event: string | null = null;
  let id: string | null = null;
  const data: string[] = [];
  for (const rawLine of block.replaceAll("\r\n", "\n").split("\n")) {
    if (rawLine === "" || rawLine.startsWith(":")) continue;
    const separator = rawLine.indexOf(":");
    const field = separator < 0 ? rawLine : rawLine.slice(0, separator);
    let value = separator < 0 ? "" : rawLine.slice(separator + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value;
    else if (field === "id" && !value.includes("\0")) id = value;
    else if (field === "data") data.push(value);
  }
  if (event === null && id === null && data.length === 0) return null;
  return { event, id, data: data.join("\n") };
}

function safeDownloadFilename(contentDisposition: string | null, fallback: string): string {
  let candidate: string | null = null;
  const encoded = contentDisposition?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  if (encoded) {
    try {
      candidate = decodeURIComponent(encoded.replace(/^"|"$/g, ""));
    } catch {
      candidate = null;
    }
  }
  candidate ??= contentDisposition?.match(/filename="?([^";]+)"?/i)?.[1] ?? null;
  const normalized = candidate?.trim();
  const hasControlCharacter = normalized
    ? [...normalized].some((character) => {
      const codePoint = character.codePointAt(0) ?? 0;
      return codePoint <= 31 || codePoint === 127;
    })
    : false;
  if (!normalized || normalized.includes("/") || normalized.includes("\\") || hasControlCharacter) {
    return fallback;
  }
  return normalized;
}
