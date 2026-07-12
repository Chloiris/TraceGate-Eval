import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TraceGateApiClient } from "@tracegate/api-client";
import type { OnboardingState, Settings } from "@tracegate/shared-types";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClientProvider } from "../api/clientContext";
import type { HostBridge } from "../host/hostBridge";
import { I18nProvider } from "../i18n";
import { OnboardingPage } from "./OnboardingPage";

const settings: Settings = {
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
  updated_at: "2026-07-12T10:00:00Z",
};

function onboarding(github: OnboardingState["github"]): OnboardingState {
  return {
    completed: false,
    current_step: "github",
    background_monitoring: false,
    launch_at_startup: false,
    repository_added: false,
    github,
    model: { state: "not_configured", configured: false, message: "模型尚未配置" },
    webhook_relay: { state: "not_configured", configured: false, message: "Webhook Relay 尚未配置" },
    completed_at: null,
    updated_at: "2026-07-12T10:00:00Z",
  };
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderOnboarding(
  state: OnboardingState,
  connectionResponse?: Response,
  hostOverrides: Partial<HostBridge> = {},
) {
  vi.stubGlobal("fetch", vi.fn<typeof fetch>(async (input) => {
    const url = String(input);
    if (url.endsWith("/onboarding")) return jsonResponse(state);
    if (url.endsWith("/settings")) return jsonResponse(settings);
    if (url.endsWith("/connections/test") && connectionResponse) return connectionResponse;
    return jsonResponse({ error: { code: "not_found", message: "Unknown test path" } }, 404);
  }));

  const client = new TraceGateApiClient({ baseUrl: "/api/v1", token: "test-token" });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const host: HostBridge = {
    kind: "tauri",
    displayName: "Tauri 测试宿主",
    getApiConnection: async () => ({ baseUrl: "/api/v1", token: "test-token" }),
    openExternal: async () => undefined,
    storeCredential: async (kind) => ({
      kind,
      configured: true,
      storage: "macOS Keychain",
      restartRequiredAfterChange: false,
    }),
    ...hostOverrides,
  };

  return render(
    <QueryClientProvider client={queryClient}>
      <ApiClientProvider client={client}>
        <I18nProvider locale="zh-CN">
          <OnboardingPage host={host} />
        </I18nProvider>
      </ApiClientProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("GitHub onboarding guidance", () => {
  it("labels the access token and opens GitHub's prefilled creation page through the host", async () => {
    const openExternal = vi.fn(async (_url: string) => undefined);
    renderOnboarding(
      onboarding({
        state: "not_configured",
        configured: false,
        message: "GitHub 尚未连接",
      }),
      undefined,
      { openExternal },
    );

    const field = await screen.findByLabelText("GitHub 访问令牌（Fine-grained PAT）");
    expect(field).toHaveAttribute("placeholder", expect.stringContaining("github_pat_"));
    expect(screen.queryByText(/不是仓库链接/)).not.toBeInTheDocument();
    expect(screen.getByText(/仓库名称在下一步填写/)).toBeInTheDocument();
    expect(screen.getByText("Pull requests · Read-only")).toBeInTheDocument();
    expect(screen.getByText("Checks · Read-only")).toBeInTheDocument();
    expect(screen.getByText("Metadata · GitHub 自动附带")).toBeInTheDocument();

    const openButton = screen.getByRole("button", { name: "在 GitHub 创建令牌 ↗" });
    await userEvent.click(openButton);
    expect(openExternal).toHaveBeenCalledOnce();
    const url = new URL(openExternal.mock.calls[0]?.[0] ?? "");
    expect(`${url.origin}${url.pathname}`).toBe("https://github.com/settings/personal-access-tokens/new");
    expect(url.searchParams.get("pull_requests")).toBe("read");
    expect(url.searchParams.get("checks")).toBe("read");
  });

  it("shows a saved token as unverified instead of green and ready", async () => {
    renderOnboarding(onboarding({
      state: "ready",
      configured: true,
      message: "GitHub credentials are configured.",
      detail: "The credential has not yet been verified by a GitHub connection test.",
    }));

    expect(await screen.findByText("已保存 · 待验证")).toBeInTheDocument();
    expect(screen.queryByText("正常")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "验证令牌身份" })).toBeEnabled();
  });

  it("turns a real HTTP 401 into an actionable token error", async () => {
    renderOnboarding(
      onboarding({
        state: "ready",
        configured: true,
        message: "GitHub credentials are configured.",
      }),
      jsonResponse({
        error: {
          code: "github_connection_failed",
          message: "GitHub connection test failed: GitHub API returned HTTP 401",
        },
      }, 502),
    );

    await userEvent.click(await screen.findByRole("button", { name: "验证令牌身份" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("HTTP 401");
    expect(alert).toHaveTextContent("完整令牌");
    expect(alert).toHaveTextContent("过期或被撤销");
    expect(alert).toHaveTextContent("重新创建、保存后再试");
  });

  it("requires verification again after replacing a verified token", async () => {
    renderOnboarding(
      onboarding({
        state: "ready",
        configured: true,
        message: "GitHub credentials are configured.",
      }),
      jsonResponse({
        component: "github",
        status: "ready",
        message: "GitHub authentication succeeded.",
        detail: "Authenticated user confirmed.",
        latency_ms: 42,
      }),
    );

    await userEvent.click(await screen.findByRole("button", { name: "验证令牌身份" }));
    expect(await screen.findByText("身份已验证")).toBeInTheDocument();

    const field = screen.getByLabelText("GitHub 访问令牌（Fine-grained PAT）");
    await userEvent.type(field, "replacement-credential-material-12345");
    await userEvent.click(screen.getByRole("button", { name: "安全保存令牌" }));

    expect(await screen.findByText("已保存 · 待验证")).toBeInTheDocument();
    expect(screen.getByText("请执行一次真实 GitHub 令牌身份验证。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存并继续" })).toBeDisabled();
  });
});
