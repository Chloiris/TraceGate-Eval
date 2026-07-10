import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ApiConnection } from "@tracegate/shared-types";

import { App } from "./App";
import { HostBridgeError, type HostBridge } from "./host/hostBridge";
import { useUiStore } from "./store/uiStore";

const connection: ApiConnection = {
  baseUrl: "/api/v1",
  token: "test-only-token",
};

function createHost(getApiConnection: () => Promise<ApiConnection>): HostBridge {
  return {
    kind: "browser",
    displayName: "测试浏览器",
    getApiConnection,
  };
}

function renderApp(host: HostBridge) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App host={host} />
    </QueryClientProvider>,
  );
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  useUiStore.setState({ activeView: "dashboard", sidebarOpen: false });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App startup and system state", () => {
  it("keeps a visible loading state while the host connection is pending", () => {
    renderApp(createHost(() => new Promise<ApiConnection>(() => undefined)));

    expect(screen.getByText("正在从宿主取得临时 API 连接信息…")).toBeInTheDocument();
    expect(screen.getAllByText("等待后端", { selector: "dd" })).toHaveLength(2);
  });

  it("shows missing local API configuration without fake provider states", async () => {
    renderApp(
      createHost(() =>
        Promise.reject(
          new HostBridgeError("missing_api_token", "浏览器开发模式尚未配置本地 API Token。"),
        ),
      ),
    );

    expect(await screen.findByText("本地后端尚未连接")).toBeInTheDocument();
    expect(screen.getByText("浏览器开发模式尚未配置本地 API Token。")).toBeInTheDocument();
    expect(screen.getAllByText("无法检查")).toHaveLength(2);
  });

  it("renders explicit GitHub and model not-configured responses", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/system/status")) {
        return jsonResponse({
          status: "degraded",
          components: {
            api: { state: "ready", configured: true, message: "本地 API 正常" },
            database: { state: "ready", configured: true, message: "SQLite 正常" },
            github: { state: "not_configured", configured: false, message: "GitHub 尚未连接" },
            model: { state: "not_configured", configured: false, message: "模型尚未配置" },
            eval: { state: "ready", configured: true, message: "TraceGate Eval 可用" },
          },
          checked_at: "2026-07-10T10:00:00+08:00",
        });
      }
      if (url.endsWith("/settings")) {
        return jsonResponse({
          theme: "system",
          language: "zh-CN",
          background_monitoring: false,
          launch_at_startup: false,
          model_provider: null,
          model_base_url: null,
          model_name: null,
          updated_at: "2026-07-10T10:00:00+08:00",
        });
      }
      return jsonResponse({ error: { code: "not_found", message: "Unknown test path" } }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderApp(createHost(() => Promise.resolve(connection)));

    expect(await screen.findByText("GitHub 尚未连接")).toBeInTheDocument();
    expect(screen.getByText("模型尚未配置")).toBeInTheDocument();
    expect(screen.getByText("仓库与 PR 数据尚未接入此页面")).toBeInTheDocument();
  });

  it("uses the desktop secure-store bridge without returning credential values", async () => {
    useUiStore.setState({ activeView: "settings" });
    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/system/status")) {
        return jsonResponse({
          status: "degraded",
          components: {
            api: { state: "ready", configured: true, message: "API ready" },
            database: { state: "ready", configured: true, message: "SQLite ready" },
            github: { state: "not_configured", configured: false, message: "GitHub 尚未连接" },
            model: { state: "not_configured", configured: false, message: "模型尚未配置" },
            eval: { state: "ready", configured: true, message: "Eval ready" },
          },
          checked_at: "2026-07-10T10:00:00+08:00",
        });
      }
      if (url.endsWith("/settings")) {
        return jsonResponse({
          theme: "system",
          language: "zh-CN",
          background_monitoring: false,
          launch_at_startup: false,
          model_provider: null,
          model_base_url: null,
          model_name: null,
          updated_at: "2026-07-10T10:00:00+08:00",
        });
      }
      return jsonResponse({ error: { code: "not_found", message: "Unknown test path" } }, 404);
    }));

    const storeCredential = vi.fn(async (kind: "github" | "model") => ({
      kind,
      configured: true,
      storage: "macOS Keychain",
      restartRequiredAfterChange: true,
    }));
    const host: HostBridge = {
      kind: "tauri",
      displayName: "Tauri 测试宿主",
      getApiConnection: async () => connection,
      getCredentialStatus: async (kind) => ({
        kind,
        configured: false,
        storage: "macOS Keychain",
        restartRequiredAfterChange: true,
      }),
      storeCredential,
      deleteCredential: async (kind) => ({
        kind,
        configured: false,
        storage: "macOS Keychain",
        restartRequiredAfterChange: true,
      }),
    };

    renderApp(host);
    const field = await screen.findByLabelText("GitHub Fine-grained PAT");
    await userEvent.type(field, "test-credential-material-12345");
    const saveButton = screen.getAllByRole("button", { name: "保存到系统凭据库" })[0];
    if (!saveButton) throw new Error("GitHub secure-store button was not rendered");
    await userEvent.click(saveButton);

    expect(storeCredential).toHaveBeenCalledWith("github", "test-credential-material-12345");
    expect(await screen.findByText(/已写入 macOS Keychain/)).toBeInTheDocument();
    expect(field).toHaveValue("");
  });
});
