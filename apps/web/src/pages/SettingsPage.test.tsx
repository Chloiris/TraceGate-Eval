import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TraceGateApiClient } from "@tracegate/api-client";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClientProvider } from "../api/clientContext";
import type { HostBridge } from "../host/hostBridge";
import { I18nProvider } from "../i18n";
import { SettingsPage } from "./SettingsPage";

const settings = {
  theme: "system",
  language: "zh-CN",
  background_monitoring: false,
  launch_at_startup: false,
  close_notice_dismissed: false,
  notifications_enabled: true,
  model_provider: "deepseek",
  model_base_url: "https://api.deepseek.com",
  model_name: "deepseek-chat",
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
  updated_at: "2026-07-11T10:00:00Z",
};

const component = { state: "ready", configured: true, message: "ready" };
const diagnostics = {
  software_version: "0.1.0",
  git_commit: "abcdef1",
  operating_system: "Darwin",
  architecture: "arm64",
  python_version: "3.12.10",
  frontend_version: "0.1.0",
  desktop_version: "0.1.0",
  rust_version_info: "rustc 1.88.0",
  log_level: "INFO",
  database_type: "sqlite",
  database_path: "/tmp/tracegate.db",
  log_path: "/tmp/tracegate.log",
  workspace_paths: ["/tmp/example"],
  sidecar_pid: 1234,
  api_port: 8765,
  github: component,
  model: component,
  webhook_relay: { state: "not_configured", configured: false, message: "not configured" },
  monitor: {
    running: true,
    polling: false,
    queued_repositories: 0,
    last_started_at: null,
    last_finished_at: null,
    last_error: null,
    rate_limited_until: null,
  },
  relay_monitor: {
    running: false,
    connected: false,
    reconnect_count: 0,
    last_connected_at: null,
    last_event_at: null,
    last_repository: null,
    last_error: null,
  },
  agent_queue: 0,
  index_queue: 0,
  last_github_api_request_count: 2,
  last_github_api_duration_ms: 130,
  last_index_duration_ms: 240,
  last_graph_duration_ms: 80,
  last_retrieval_result_count: 4,
  last_model_latency_ms: 900,
  last_model_input_tokens: 120,
  last_model_output_tokens: 40,
  last_model_retry_count: 0,
  delivered_notification_count: 1,
  failed_notification_count: 0,
  telemetry_enabled: false,
};

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), { status: 200, headers: { "Content-Type": "application/json" } });
}

function renderSettings(initialSection: "general" | "diagnostics" = "general") {
  const client = new TraceGateApiClient({ baseUrl: "/api/v1", token: "test-token" });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const host: HostBridge = {
    kind: "browser",
    displayName: "测试浏览器",
    getApiConnection: async () => ({ baseUrl: "/api/v1", token: "test-token" }),
  };
  return render(
    <QueryClientProvider client={queryClient}>
      <ApiClientProvider client={client}>
        <I18nProvider locale="zh-CN">
          <SettingsPage host={host} initialSection={initialSection} />
        </I18nProvider>
      </ApiClientProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Settings secondary navigation", () => {
  it("keeps the full redacted diagnostics view inside Settings and refreshes it", async () => {
    let diagnosticsRequests = 0;
    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/settings")) return jsonResponse(settings);
      if (url.endsWith("/system/status")) {
        return jsonResponse({
          status: "ready",
          components: { api: component, database: component, github: component, model: component, webhook_relay: diagnostics.webhook_relay, eval: component },
          checked_at: "2026-07-11T10:00:00Z",
        });
      }
      if (url.endsWith("/diagnostics")) {
        diagnosticsRequests += 1;
        return jsonResponse(diagnostics);
      }
      if (url.endsWith("/system/update")) {
        return jsonResponse({ current_version: "0.1.0", channel: "stable", configured: false, update_available: false, latest_version: null, manifest_url: null, signature_verification: false, message: "not configured" });
      }
      return new Response(null, { status: 404 });
    }));

    renderSettings();

    const navigation = await screen.findByRole("navigation", { name: "设置目录" });
    const diagnosticsLink = screen.getByRole("link", { name: /诊断/ });
    expect(navigation).toContainElement(diagnosticsLink);
    expect(diagnosticsLink).toHaveAttribute("href", "#settings-diagnostics");
    expect(screen.getByRole("link", { name: /常规/ })).toHaveAttribute("aria-current", "location");

    await userEvent.click(diagnosticsLink);
    expect(diagnosticsLink).toHaveAttribute("aria-current", "location");
    expect(await screen.findByRole("heading", { name: "版本与进程" })).toBeInTheDocument();
    expect(screen.getByText("Darwin / arm64")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "后台队列" })).toBeInTheDocument();

    const beforeRefresh = diagnosticsRequests;
    await userEvent.click(screen.getByRole("button", { name: "刷新" }));
    await waitFor(() => expect(diagnosticsRequests).toBeGreaterThan(beforeRefresh));
  });

  it("marks the diagnostics subsection active for the legacy diagnostics route", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/settings")) return jsonResponse(settings);
      if (url.endsWith("/system/status")) return jsonResponse({ status: "ready", components: { api: component, database: component, github: component, model: component, webhook_relay: diagnostics.webhook_relay, eval: component }, checked_at: "2026-07-11T10:00:00Z" });
      if (url.endsWith("/diagnostics")) return jsonResponse(diagnostics);
      if (url.endsWith("/system/update")) return jsonResponse({ current_version: "0.1.0", channel: "stable", configured: false, update_available: false, latest_version: null, manifest_url: null, signature_verification: false, message: "not configured" });
      return new Response(null, { status: 404 });
    }));

    renderSettings("diagnostics");

    const diagnosticsLink = await screen.findByRole("link", { name: /诊断/ });
    expect(diagnosticsLink).toHaveAttribute("aria-current", "location");
    expect(await screen.findByRole("heading", { name: "最近持久化指标" })).toBeInTheDocument();
  });
});
