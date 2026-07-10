import {
  apiConnectionSchema,
  credentialStatusSchema,
  type ApiConnection,
  type CredentialKind,
  type CredentialStatus,
} from "@tracegate/shared-types";

export type HostKind = "browser" | "tauri" | "ue-webview" | "maya-webview";
export type TrayAction =
  | "scan_all"
  | "pause_monitoring"
  | "resume_monitoring"
  | "recent_pull_requests"
  | "high_risk_pull_requests"
  | "settings"
  | "logs"
  | "diagnostics";

export type DeepLinkRoute =
  | { kind: "repository"; owner: string; repository: string }
  | { kind: "pull_request"; owner: string; repository: string; number: number }
  | { kind: "run"; run_id: string };

export interface GitHubDeviceAuthorization {
  userCode: string;
  verificationUri: "https://github.com/login/device";
  expiresAtEpochMs: number;
  intervalSeconds: number;
}

export interface GitHubDevicePollResult {
  status: "pending" | "authorized";
  intervalSeconds: number;
  credential: CredentialStatus | null;
}

export interface RelayPairingResult {
  repositories: string[];
  credential: CredentialStatus;
}

export interface HostBridge {
  readonly kind: HostKind;
  readonly displayName: string;
  getApiConnection(): Promise<ApiConnection>;
  getCredentialStatus?(kind: CredentialKind): Promise<CredentialStatus>;
  storeCredential?(kind: CredentialKind, secret: string): Promise<CredentialStatus>;
  deleteCredential?(kind: CredentialKind): Promise<CredentialStatus>;
  getAutostartEnabled?(): Promise<boolean>;
  setAutostartEnabled?(enabled: boolean): Promise<boolean>;
  showReviewNotification?(title: string, body: string, deepLink?: string): Promise<void>;
  hideMainWindow?(): Promise<void>;
  openWorkspace?(path: string, editor?: boolean): Promise<void>;
  openWorkspaceFile?(workspace: string, path: string, line?: number): Promise<void>;
  beginGithubDeviceFlow?(clientId: string): Promise<GitHubDeviceAuthorization>;
  pollGithubDeviceFlow?(): Promise<GitHubDevicePollResult>;
  pairWebhookRelay?(baseUrl: string, pairingCode: string, deviceId: string): Promise<RelayPairingResult>;
  onTrayAction?(handler: (action: TrayAction) => void): Promise<() => void>;
  onDeepLink?(handler: (route: DeepLinkRoute) => void): Promise<() => void>;
  onCloseRequested?(handler: () => void): Promise<() => void>;
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

  async getAutostartEnabled(): Promise<boolean> {
    const { invoke } = await import("@tauri-apps/api/core");
    return invoke<boolean>("get_autostart_enabled");
  }

  async setAutostartEnabled(enabled: boolean): Promise<boolean> {
    const { invoke } = await import("@tauri-apps/api/core");
    return invoke<boolean>("set_autostart_enabled", { enabled });
  }

  async showReviewNotification(title: string, body: string, deepLink?: string): Promise<void> {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("show_review_notification", { title, body, deepLink });
  }

  async hideMainWindow(): Promise<void> {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("hide_main_window");
  }

  async openWorkspace(path: string, editor = false): Promise<void> {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("open_workspace", { path, editor });
  }

  async openWorkspaceFile(workspace: string, path: string, line?: number): Promise<void> {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("open_workspace_file", { workspace, path, line });
  }

  async beginGithubDeviceFlow(clientId: string): Promise<GitHubDeviceAuthorization> {
    const { invoke } = await import("@tauri-apps/api/core");
    const value = await invoke<GitHubDeviceAuthorization>("begin_github_device_flow", { clientId });
    if (value.verificationUri !== "https://github.com/login/device" || !value.userCode || value.intervalSeconds < 1) {
      throw new HostBridgeError("host_command_failed", "GitHub Device Flow 返回了无效的公开授权信息。");
    }
    return value;
  }

  async pollGithubDeviceFlow(): Promise<GitHubDevicePollResult> {
    const { invoke } = await import("@tauri-apps/api/core");
    const value = await invoke<GitHubDevicePollResult>("poll_github_device_flow");
    if (!(["pending", "authorized"] as const).includes(value.status) || value.intervalSeconds < 1) {
      throw new HostBridgeError("host_command_failed", "GitHub Device Flow 返回了无效的轮询结果。");
    }
    if (value.credential) credentialStatusSchema.parse(value.credential);
    return value;
  }

  async pairWebhookRelay(baseUrl: string, pairingCode: string, deviceId: string): Promise<RelayPairingResult> {
    const { invoke } = await import("@tauri-apps/api/core");
    const value = await invoke<RelayPairingResult>("pair_webhook_relay", { baseUrl, pairingCode, deviceId });
    return {
      repositories: value.repositories.filter((item) => /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(item)),
      credential: credentialStatusSchema.parse(value.credential),
    };
  }

  async onTrayAction(handler: (action: TrayAction) => void): Promise<() => void> {
    const { listen } = await import("@tauri-apps/api/event");
    return listen<TrayAction>("tracegate-tray-action", (event) => handler(event.payload));
  }

  async onDeepLink(handler: (route: DeepLinkRoute) => void): Promise<() => void> {
    const { listen } = await import("@tauri-apps/api/event");
    const stop = await listen<{ route: DeepLinkRoute }>("tracegate-deep-link", (event) => handler(event.payload.route));
    const { invoke } = await import("@tauri-apps/api/core");
    const pending = await invoke<DeepLinkRoute | null>("take_pending_deep_link");
    if (pending) handler(pending);
    return stop;
  }

  async onCloseRequested(handler: () => void): Promise<() => void> {
    const { listen } = await import("@tauri-apps/api/event");
    return listen("tracegate-close-requested", handler);
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
