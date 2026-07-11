import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ApiConnection, CredentialKind } from "@tracegate/shared-types";

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
            webhook_relay: { state: "not_configured", configured: false, message: "Webhook Relay 未配置" },
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
          close_notice_dismissed: false,
          notifications_enabled: true,
          model_provider: null,
          model_base_url: null,
          model_name: null,
          model_temperature: 0,
          model_max_output_tokens: 4096,
          model_timeout_seconds: 60,
          model_max_retries: 2,
          model_native_structured_output: false,
          model_streaming_enabled: false,
          model_native_tool_calling: false,
          model_context_scope: "changed_files",
          model_input_cost_per_million: 0,
          model_output_cost_per_million: 0,
          github_poll_interval_seconds: 60,
          automatic_analysis_enabled: false,
          automatic_analysis_include_drafts: false,
          automatic_analysis_require_checks_success: false,
          analysis_paused: false,
          webhook_relay_url: null,
          webhook_relay_device_id: null,
          updated_at: "2026-07-10T10:00:00+08:00",
        });
      }
      if (url.endsWith("/repositories") || url.endsWith("/pull-requests") || url.endsWith("/runs")) {
        return jsonResponse({ items: [], total: 0, limit: 50, offset: 0 });
      }
      return jsonResponse({ error: { code: "not_found", message: "Unknown test path" } }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderApp(createHost(() => Promise.resolve(connection)));

    expect(await screen.findByText("GitHub 尚未连接")).toBeInTheDocument();
    expect(screen.getByText("模型尚未配置")).toBeInTheDocument();
    expect(screen.getByText("工作区活动")).toBeInTheDocument();
    expect(screen.getByText("配置输入/输出 Token 单价后才显示成本估算。", { exact: false })).toBeInTheDocument();
    const navigation = screen.getByRole("navigation", { name: "主导航" });
    expect(navigation).toHaveTextContent("审查队列");
    expect(navigation).toHaveTextContent("拉取请求审查与分析");
    expect(navigation).toHaveTextContent("运行记录");
    expect(navigation).toHaveTextContent("节点与工具轨迹");
    expect(navigation).toHaveTextContent("评测中心");
    expect(navigation).toHaveTextContent("真实基准与声明评测");
    expect(navigation).toHaveTextContent("组件注册");
    expect(navigation).toHaveTextContent("智能体与工具");
    expect(navigation).not.toHaveTextContent("PR Inbox");
    expect(navigation).not.toHaveTextContent("Agent Runs");
    expect(navigation).not.toHaveTextContent("Eval Center");
    expect(navigation).not.toHaveTextContent("Registry");
    expect(navigation).not.toHaveTextContent("诊断");
    const connectionSummary = screen.getByLabelText("连接摘要");
    expect(connectionSummary).toHaveTextContent("连接状态");
    expect(connectionSummary).toHaveTextContent("本地后端");
    expect(connectionSummary).toHaveTextContent("代码托管");
    expect(connectionSummary).toHaveTextContent("语义模型");
    expect(document.querySelector(".workspace-header")).not.toHaveTextContent("后端");
    expect(screen.queryByRole("button", { name: "打开命令面板" })).not.toBeInTheDocument();
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
            webhook_relay: { state: "not_configured", configured: false, message: "Webhook Relay 未配置" },
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
          close_notice_dismissed: false,
          notifications_enabled: true,
          model_provider: null,
          model_base_url: null,
          model_name: null,
          model_temperature: 0,
          model_max_output_tokens: 4096,
          model_timeout_seconds: 60,
          model_max_retries: 2,
          model_native_structured_output: false,
          model_streaming_enabled: false,
          model_native_tool_calling: false,
          model_context_scope: "changed_files",
          model_input_cost_per_million: 0,
          model_output_cost_per_million: 0,
          github_poll_interval_seconds: 60,
          automatic_analysis_enabled: false,
          automatic_analysis_include_drafts: false,
          automatic_analysis_require_checks_success: false,
          analysis_paused: false,
          webhook_relay_url: null,
          webhook_relay_device_id: null,
          updated_at: "2026-07-10T10:00:00+08:00",
        });
      }
      return jsonResponse({ error: { code: "not_found", message: "Unknown test path" } }, 404);
    }));

    const storeCredential = vi.fn(async (kind: CredentialKind) => ({
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

  it("routes real Tauri tray actions into Studio views", async () => {
    let trayHandler: ((action: "settings" | "diagnostics") => void) | undefined;
    let closeHandler: (() => void) | undefined;
    const hideMainWindow = vi.fn(async () => undefined);
    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/system/status")) {
        return jsonResponse({
          status: "degraded",
          components: {
            api: { state: "ready", configured: true, message: "API ready" },
            database: { state: "ready", configured: true, message: "DB ready" },
            github: { state: "not_configured", configured: false, message: "GitHub 尚未连接" },
            model: { state: "not_configured", configured: false, message: "模型尚未配置" },
            webhook_relay: { state: "not_configured", configured: false, message: "Webhook Relay 未配置" },
            eval: { state: "ready", configured: true, message: "Eval ready" },
          },
          checked_at: "2026-07-10T10:00:00Z",
        });
      }
      if (url.endsWith("/settings")) {
        return jsonResponse({ theme: "system", language: "zh-CN", background_monitoring: false, launch_at_startup: false, close_notice_dismissed: false, notifications_enabled: true, model_provider: null, model_base_url: null, model_name: null, model_temperature: 0, model_max_output_tokens: 4096, model_timeout_seconds: 60, model_max_retries: 2, model_native_structured_output: false, model_streaming_enabled: false, model_native_tool_calling: false, model_context_scope: "changed_files", model_input_cost_per_million: 0, model_output_cost_per_million: 0, github_poll_interval_seconds: 60, automatic_analysis_enabled: false, automatic_analysis_include_drafts: false, automatic_analysis_require_checks_success: false, analysis_paused: false, webhook_relay_url: null, webhook_relay_device_id: null, updated_at: "2026-07-10T10:00:00Z" });
      }
      if (url.endsWith("/repositories") || url.endsWith("/pull-requests") || url.endsWith("/runs")) {
        return jsonResponse({ items: [], total: 0, limit: 50, offset: 0 });
      }
      return jsonResponse({ error: { code: "not_found", message: "Unknown test path" } }, 404);
    }));
    const host: HostBridge = {
      kind: "tauri",
      displayName: "Tauri 测试宿主",
      getApiConnection: async () => connection,
      onTrayAction: async (handler) => {
        trayHandler = handler as (action: "settings" | "diagnostics") => void;
        return () => undefined;
      },
      onCloseRequested: async (handler) => {
        closeHandler = handler;
        return () => undefined;
      },
      hideMainWindow,
    };
    renderApp(host);
    await screen.findByRole("heading", { name: "概览" });
    await waitFor(() => expect(trayHandler).toBeDefined());
    await act(async () => trayHandler?.("settings"));
    expect(await screen.findByRole("heading", { name: "设置", level: 2 })).toBeInTheDocument();
    await act(async () => trayHandler?.("diagnostics"));
    expect(screen.getByRole("button", { name: /设置.*本地偏好与宿主/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /诊断.*版本、指标与队列/ })).toHaveAttribute("aria-current", "location");
    expect(screen.queryByRole("button", { name: /诊断.*版本、日志与队列/ })).not.toBeInTheDocument();
    await act(async () => closeHandler?.());
    expect(screen.getByRole("heading", { name: "TraceGate 将继续在后台监控 PR。" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: /不再提示/ }));
    await userEvent.click(screen.getByRole("button", { name: "继续在后台运行" }));
    expect(hideMainWindow).toHaveBeenCalledOnce();
  });

  it("renders the persisted English shell without the removed command palette", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/system/status")) {
        return jsonResponse({
          status: "degraded",
          components: {
            api: { state: "ready", configured: true, message: "API ready" },
            database: { state: "ready", configured: true, message: "DB ready" },
            github: { state: "not_configured", configured: false, message: "GitHub not connected" },
            model: { state: "not_configured", configured: false, message: "Model not configured" },
            webhook_relay: { state: "not_configured", configured: false, message: "Webhook Relay is not configured" },
            eval: { state: "ready", configured: true, message: "Eval ready" },
          },
          checked_at: "2026-07-10T10:00:00Z",
        });
      }
      if (url.endsWith("/settings")) {
        return jsonResponse({ theme: "system", language: "en-US", background_monitoring: false, launch_at_startup: false, close_notice_dismissed: false, notifications_enabled: true, model_provider: null, model_base_url: null, model_name: null, model_temperature: 0, model_max_output_tokens: 4096, model_timeout_seconds: 60, model_max_retries: 2, model_native_structured_output: false, model_streaming_enabled: false, model_native_tool_calling: false, model_context_scope: "changed_files", model_input_cost_per_million: 0, model_output_cost_per_million: 0, github_poll_interval_seconds: 60, automatic_analysis_enabled: false, automatic_analysis_include_drafts: false, automatic_analysis_require_checks_success: false, analysis_paused: false, webhook_relay_url: null, webhook_relay_device_id: null, updated_at: "2026-07-10T10:00:00Z" });
      }
      if (url.endsWith("/onboarding")) {
        return jsonResponse({ completed: false, current_step: "welcome", background_monitoring: false, launch_at_startup: false, repository_added: false, github: { state: "not_configured", configured: false, message: "GitHub 尚未连接" }, model: { state: "not_configured", configured: false, message: "模型尚未配置" }, webhook_relay: { state: "not_configured", configured: false, message: "Webhook Relay 尚未配置" }, completed_at: null, updated_at: "2026-07-10T10:00:00Z" });
      }
      if (url.endsWith("/repositories") || url.endsWith("/pull-requests") || url.endsWith("/runs")) {
        return jsonResponse({ items: [], total: 0, limit: 50, offset: 0 });
      }
      return jsonResponse({ error: { code: "not_found", message: "Unknown test path" } }, 404);
    }));
    renderApp(createHost(async () => connection));
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    const navigation = screen.getByRole("navigation", { name: "Primary navigation" });
    expect(navigation).toHaveTextContent("Repositories");
    expect(navigation).not.toHaveTextContent("Diagnostics");
    expect(screen.getByRole("heading", { name: "Some capabilities are not configured" })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en-US");
    act(() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true })));
    act(() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true })));
    expect(screen.queryByRole("dialog", { name: "Command palette" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open command palette" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Onboarding.*Complete initial setup/ }));
    expect(await screen.findByRole("heading", { name: "Welcome to TraceGate Studio" })).toBeInTheDocument();
    expect(screen.getByText("Real PR evidence")).toBeInTheDocument();
  });
});
