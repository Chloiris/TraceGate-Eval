import {
  apiConnectionSchema,
  errorEnvelopeSchema,
  healthResponseSchema,
  onboardingStateSchema,
  onboardingUpdateSchema,
  settingsSchema,
  settingsUpdateSchema,
  systemStatusSchema,
  type ApiConnection,
  type HealthResponse,
  type OnboardingState,
  type OnboardingUpdate,
  type Settings,
  type SettingsUpdate,
  type SystemStatus,
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
