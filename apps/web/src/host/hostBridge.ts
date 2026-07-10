import {
  apiConnectionSchema,
  credentialStatusSchema,
  type ApiConnection,
  type CredentialKind,
  type CredentialStatus,
} from "@tracegate/shared-types";

export type HostKind = "browser" | "tauri" | "ue-webview" | "maya-webview";

export interface HostBridge {
  readonly kind: HostKind;
  readonly displayName: string;
  getApiConnection(): Promise<ApiConnection>;
  getCredentialStatus?(kind: CredentialKind): Promise<CredentialStatus>;
  storeCredential?(kind: CredentialKind, secret: string): Promise<CredentialStatus>;
  deleteCredential?(kind: CredentialKind): Promise<CredentialStatus>;
}

export class HostBridgeError extends Error {
  readonly code: "missing_api_token" | "host_command_failed" | "unsupported_host";

  constructor(
    code: HostBridgeError["code"],
    message: string,
    options?: ErrorOptions,
  ) {
    super(message, options);
    this.name = "HostBridgeError";
    this.code = code;
  }
}

export class BrowserHost implements HostBridge {
  readonly kind = "browser" as const;
  readonly displayName = "浏览器开发模式";
  readonly #baseUrl: string;
  readonly #token: string | undefined;

  constructor(environment: Pick<ImportMetaEnv, "VITE_TRACEGATE_API_BASE_URL" | "VITE_TRACEGATE_API_TOKEN">) {
    this.#baseUrl = environment.VITE_TRACEGATE_API_BASE_URL ?? "/api/v1";
    this.#token = environment.VITE_TRACEGATE_API_TOKEN;
  }

  async getApiConnection(): Promise<ApiConnection> {
    if (this.#token === undefined || this.#token.trim() === "") {
      throw new HostBridgeError(
        "missing_api_token",
        "浏览器开发模式尚未配置本地 API Token。请显式设置 VITE_TRACEGATE_API_TOKEN 后重新启动前端。",
      );
    }
    return apiConnectionSchema.parse({ baseUrl: this.#baseUrl, token: this.#token });
  }
}

export class TauriHost implements HostBridge {
  readonly kind = "tauri" as const;
  readonly displayName = "Tauri 桌面端";

  async getApiConnection(): Promise<ApiConnection> {
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      const connection = await invoke<unknown>("get_api_connection");
      return apiConnectionSchema.parse(connection);
    } catch (error) {
      throw new HostBridgeError(
        "host_command_failed",
        "桌面端未能取得本地后端连接信息。Token 不会写入浏览器存储。",
        { cause: error },
      );
    }
  }

  async getCredentialStatus(kind: CredentialKind): Promise<CredentialStatus> {
    const { invoke } = await import("@tauri-apps/api/core");
    return credentialStatusSchema.parse(await invoke<unknown>("get_credential_status", { kind }));
  }

  async storeCredential(kind: CredentialKind, secret: string): Promise<CredentialStatus> {
    const { invoke } = await import("@tauri-apps/api/core");
    return credentialStatusSchema.parse(await invoke<unknown>("store_credential", { kind, secret }));
  }

  async deleteCredential(kind: CredentialKind): Promise<CredentialStatus> {
    const { invoke } = await import("@tauri-apps/api/core");
    return credentialStatusSchema.parse(await invoke<unknown>("delete_credential", { kind }));
  }
}

export interface ReservedWebViewHostAdapter {
  readonly kind: "ue-webview" | "maya-webview";
  readonly supported: false;
  readonly note: string;
}

export const reservedWebViewHosts: readonly ReservedWebViewHostAdapter[] = [
  {
    kind: "ue-webview",
    supported: false,
    note: "仅预留 UE WebView Host Adapter 接口，当前未支持。",
  },
  {
    kind: "maya-webview",
    supported: false,
    note: "仅预留 Maya WebView Host Adapter 接口，当前未支持。",
  },
];

function isTauriRuntime(): boolean {
  return "__TAURI_INTERNALS__" in window;
}

export function createHostBridge(): HostBridge {
  return isTauriRuntime() ? new TauriHost() : new BrowserHost(import.meta.env);
}
