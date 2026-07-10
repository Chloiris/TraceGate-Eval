import {
  apiConnectionSchema,
  agentRunListSchema,
  agentRunDetailSchema,
  agentEvidenceGraphSchema,
  agentRunSchema,
  agentDescriptorListSchema,
  agentStepSchema,
  analyzeResponseSchema,
  evidenceSchema,
  evaluationSummarySchema,
  errorEnvelopeSchema,
  findingSchema,
  healthResponseSchema,
  onboardingStateSchema,
  onboardingUpdateSchema,
  indexVersionSchema,
  pullRequestDiffSchema,
  pullRequestListSchema,
  pullRequestSchema,
  reviewMapSchema,
  changeTourSchema,
  diagnosticsSchema,
  repositoryCreateSchema,
  repositoryGraphSchema,
  repositoryListSchema,
  repositorySchema,
  repositorySyncSchema,
  repositoryUpdateSchema,
  settingsSchema,
  settingsUpdateSchema,
  systemStatusSchema,
  toolDescriptorListSchema,
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
  type HealthResponse,
  type OnboardingState,
  type OnboardingUpdate,
  type IndexVersion,
  type PullRequest,
  type PullRequestDiff,
  type PullRequestList,
  type ReviewMap,
  type ChangeTour,
  type Diagnostics,
  type Repository,
  type RepositoryCreate,
  type RepositoryGraph,
  type RepositoryList,
  type RepositorySync,
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

  async getEvaluations(signal?: AbortSignal): Promise<EvaluationSummary> {
    return this.#request("/evaluations", evaluationSummarySchema, requestSignal(signal));
  }

  async listAgents(signal?: AbortSignal): Promise<AgentDescriptor[]> {
    return this.#request("/agents", agentDescriptorListSchema, requestSignal(signal));
  }

  async listTools(signal?: AbortSignal): Promise<ToolDescriptor[]> {
    return this.#request("/tools", toolDescriptorListSchema, requestSignal(signal));
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

  async #request<T>(
    path: string,
    schema: ZodType<T>,
    init: RequestInit,
  ): Promise<T> {
    let response: Response;
    try {
      response = await this.#fetch(`${this.#connection.baseUrl}${path}`, {
        ...init,
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${this.#connection.token}`,
          ...(init.body === undefined ? {} : { "Content-Type": "application/json" }),
        },
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
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${this.#connection.token}`,
        },
      });
    } catch (error) {
      throw new TraceGateApiError("无法连接 TraceGate 本地后端。", { kind: "network", cause: error });
    }
    if (!response.ok) {
      throw new TraceGateApiError(`本地 API 请求失败（HTTP ${response.status}）。`, {
        kind: "http",
        status: response.status,
      });
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
