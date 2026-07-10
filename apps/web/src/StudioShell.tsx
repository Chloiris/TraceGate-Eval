import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { usePullRequests, useRepositories, useRuns, useSettings, useSystemStatus } from "./api/queries";
import { useApiClient } from "./api/clientContext";
import { ErrorState, LoadingState } from "./components/RequestState";
import { PendingStatusBadge, StatusBadge } from "./components/StatusBadge";
import { CommandPalette } from "./components/CommandPalette";
import type { DeepLinkRoute, HostBridge, TrayAction } from "./host/hostBridge";
import { errorMessage } from "./lib/errors";
import { I18nProvider, type StudioLocale } from "./i18n";
import { DashboardPage } from "./pages/DashboardPage";
import { RepositoryPage } from "./pages/RepositoryPage";
import { PullRequestInboxPage } from "./pages/PullRequestInboxPage";
import { AgentRunsPage } from "./pages/AgentRunsPage";
import { EvalCenterPage } from "./pages/EvalCenterPage";
import { RegistryPage } from "./pages/RegistryPage";
import { DiagnosticsPage } from "./pages/DiagnosticsPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { SettingsPage } from "./pages/SettingsPage";
import { useUiStore, type StudioView } from "./store/uiStore";
import type { NotificationCreate } from "@tracegate/shared-types";

const PullRequestDetailPage = lazy(async () => {
  const module = await import("./pages/PullRequestDetailPage");
  return { default: module.PullRequestDetailPage };
});
const RepositoryMapPage = lazy(async () => {
  const module = await import("./pages/RepositoryMapPage");
  return { default: module.RepositoryMapPage };
});

const navigation: readonly { id: StudioView; zh: string; en: string; descriptionZh: string; descriptionEn: string; glyph: string }[] = [
  { id: "dashboard", zh: "概览", en: "Overview", descriptionZh: "系统与连接状态", descriptionEn: "System and connections", glyph: "01" },
  { id: "repositories", zh: "仓库", en: "Repositories", descriptionZh: "同步与增量索引", descriptionEn: "Sync and incremental index", glyph: "02" },
  { id: "pull-requests", zh: "PR Inbox", en: "PR Inbox", descriptionZh: "审查与分析队列", descriptionEn: "Review and analysis queue", glyph: "03" },
  { id: "repository-map", zh: "代码地图", en: "Code Map", descriptionZh: "静态关系与影响", descriptionEn: "Static relations and impact", glyph: "04" },
  { id: "runs", zh: "Agent Runs", en: "Agent Runs", descriptionZh: "节点与工具 Trace", descriptionEn: "Node and tool trace", glyph: "05" },
  { id: "eval", zh: "Eval Center", en: "Eval Center", descriptionZh: "真实基准与 ClaimBench", descriptionEn: "Real benchmarks and ClaimBench", glyph: "06" },
  { id: "registry", zh: "Registry", en: "Registry", descriptionZh: "Agent 与 Tool", descriptionEn: "Agents and tools", glyph: "07" },
  { id: "diagnostics", zh: "诊断", en: "Diagnostics", descriptionZh: "版本、日志与队列", descriptionEn: "Versions, logs and queues", glyph: "08" },
  { id: "onboarding", zh: "首次引导", en: "Onboarding", descriptionZh: "完成基础配置", descriptionEn: "Complete initial setup", glyph: "09" },
  { id: "settings", zh: "设置", en: "Settings", descriptionZh: "本地偏好与宿主", descriptionEn: "Local preferences and host", glyph: "10" },
];

export function StudioShell({ host }: { host: HostBridge }) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  const activeView = useUiStore((state) => state.activeView);
  const sidebarOpen = useUiStore((state) => state.sidebarOpen);
  const setActiveView = useUiStore((state) => state.setActiveView);
  const setSidebarOpen = useUiStore((state) => state.setSidebarOpen);
  const statusQuery = useSystemStatus();
  const settingsQuery = useSettings();
  const notificationPullRequests = usePullRequests();
  const notificationRepositories = useRepositories();
  const notificationRuns = useRuns();
  const [nativeNotice, setNativeNotice] = useState<{ kind: "success" | "error"; message: string } | null>(null);
  const [closePromptOpen, setClosePromptOpen] = useState(false);
  const [dismissClosePrompt, setDismissClosePrompt] = useState(false);
  const [closeBusy, setCloseBusy] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const previousPullRequests = useRef<Map<string, string | null> | null>(null);
  const previousRuns = useRef<Map<string, string> | null>(null);
  const previousGithubState = useRef<string | null>(null);
  const locale: StudioLocale = settingsQuery.data?.language ?? "zh-CN";
  const text = useCallback((zh: string, en: string) => locale === "en-US" ? en : zh, [locale]);
  const deliverNotification = useCallback(async (
    input: Omit<NotificationCreate, "status" | "error_message">,
  ): Promise<void> => {
    const notify = host.showReviewNotification;
    if (!notify) return;
    try {
      await notify(input.title, input.body, input.deep_link ?? undefined);
    } catch (error) {
      const message = errorMessage(error);
      try {
        await client.recordNotification({ ...input, status: "failed", error_message: message });
      } catch (recordError) {
        setNativeNotice({ kind: "error", message: `${text("通知和记录均失败", "Notification and audit record failed")}: ${message}; ${errorMessage(recordError)}` });
      }
      throw error;
    }
    try {
      await client.recordNotification({ ...input, status: "delivered", error_message: null });
    } catch (recordError) {
      setNativeNotice({ kind: "error", message: `${text("通知已交给操作系统，但记录失败", "Notification was handed to the OS, but its audit record failed")}: ${errorMessage(recordError)}` });
    }
  }, [client, host.showReviewNotification, text]);

  useEffect(() => {
    const theme = settingsQuery.data?.theme ?? "system";
    document.documentElement.dataset.theme = theme;
    document.documentElement.lang = settingsQuery.data?.language ?? "zh-CN";
  }, [settingsQuery.data?.language, settingsQuery.data?.theme]);

  useEffect(() => {
    const handleKeyboard = (event: globalThis.KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLocaleLowerCase() === "k") {
        event.preventDefault();
        setCommandPaletteOpen((open) => !open);
      } else if (event.key === "Escape") {
        setCommandPaletteOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, []);

  useEffect(() => {
    const items = notificationPullRequests.data?.items;
    if (!items) return;
    const current = new Map(items.map((item) => [item.id, item.head_sha]));
    const previous = previousPullRequests.current;
    previousPullRequests.current = current;
    if (!previous || !settingsQuery.data?.notifications_enabled || !host.showReviewNotification) return;
    for (const item of items) {
      const oldHead = previous.get(item.id);
      const repository = notificationRepositories.data?.items.find((candidate) => candidate.id === item.repository_id);
      const deepLink = repository ? `tracegate://pr/${repository.full_name}/${item.number}` : undefined;
      if (!previous.has(item.id)) {
        void deliverNotification({ kind: "new_pull_request", title: "TraceGate · New Pull Request", body: `#${item.number} ${item.title}`, deep_link: deepLink, repository_id: item.repository_id, pull_request_id: item.id }).catch((error: unknown) => setNativeNotice({ kind: "error", message: `${text("通知失败", "Notification failed")}: ${errorMessage(error)}` }));
      } else if (oldHead && item.head_sha && oldHead !== item.head_sha) {
        void deliverNotification({ kind: "new_pull_request_commit", title: "TraceGate · New PR commit", body: `#${item.number} ${item.title}`, deep_link: deepLink, repository_id: item.repository_id, pull_request_id: item.id }).catch((error: unknown) => setNativeNotice({ kind: "error", message: `${text("通知失败", "Notification failed")}: ${errorMessage(error)}` }));
      }
    }
  }, [deliverNotification, host.showReviewNotification, notificationPullRequests.data, notificationRepositories.data?.items, settingsQuery.data?.notifications_enabled, text]);

  useEffect(() => {
    const items = notificationRuns.data?.items;
    if (!items) return;
    const current = new Map(items.map((item) => [item.id, item.status]));
    const previous = previousRuns.current;
    previousRuns.current = current;
    if (!previous || !settingsQuery.data?.notifications_enabled || !host.showReviewNotification) return;
    for (const run of items) {
      const oldStatus = previous.get(run.id);
      if (oldStatus === run.status) continue;
      const deepLink = `tracegate://run/${run.id}`;
      if (run.status === "running") {
        void deliverNotification({ kind: "analysis_started", title: "TraceGate · Analysis started", body: run.current_node ?? run.workflow_version ?? run.id, deep_link: deepLink, repository_id: run.repository_id, pull_request_id: run.pull_request_id, agent_run_id: run.id }).catch((error: unknown) => setNativeNotice({ kind: "error", message: `${text("通知失败", "Notification failed")}: ${errorMessage(error)}` }));
      } else if (run.status === "completed") {
        void client.listFindings(run.id).then(async (findings) => {
          const highRisk = findings.find((finding) => finding.severity === "critical" || finding.severity === "high");
          const notifications: Promise<void>[] = [];
          if (highRisk) notifications.push(deliverNotification({ kind: "high_risk_finding", title: "TraceGate · High-risk Finding", body: highRisk.title, deep_link: deepLink, repository_id: run.repository_id, pull_request_id: run.pull_request_id, agent_run_id: run.id }));
          notifications.push(deliverNotification({ kind: "analysis_completed", title: "TraceGate · Analysis completed", body: run.model_profile ?? run.id, deep_link: deepLink, repository_id: run.repository_id, pull_request_id: run.pull_request_id, agent_run_id: run.id }));
          await Promise.all(notifications);
        }).catch((error: unknown) => setNativeNotice({ kind: "error", message: `${text("通知准备失败", "Could not prepare notification")}: ${errorMessage(error)}` }));
      } else if (run.status === "failed") {
        void deliverNotification({ kind: "analysis_failed", title: "TraceGate · Analysis failed", body: run.error_code ?? run.id, deep_link: deepLink, repository_id: run.repository_id, pull_request_id: run.pull_request_id, agent_run_id: run.id }).catch((error: unknown) => setNativeNotice({ kind: "error", message: `${text("通知失败", "Notification failed")}: ${errorMessage(error)}` }));
      }
    }
  }, [client, deliverNotification, host.showReviewNotification, notificationRuns.data, settingsQuery.data?.notifications_enabled, text]);

  useEffect(() => {
    const state = statusQuery.data?.components.github.state;
    if (!state) return;
    const previous = previousGithubState.current;
    previousGithubState.current = state;
    if (previous === "ready" && state !== "ready" && settingsQuery.data?.notifications_enabled && host.showReviewNotification) {
      void deliverNotification({ kind: "github_authentication_failed", title: "TraceGate · GitHub authentication", body: text("GitHub 连接已失效。", "The GitHub connection is no longer valid.") }).catch((error: unknown) => setNativeNotice({ kind: "error", message: `${text("通知失败", "Notification failed")}: ${errorMessage(error)}` }));
    }
  }, [deliverNotification, host.showReviewNotification, settingsQuery.data?.notifications_enabled, statusQuery.data?.components.github.state, text]);

  useEffect(() => {
    let active = true;
    const unregister: (() => void)[] = [];
    const localized = (zh: string, en: string) => locale === "en-US" ? en : zh;
    const report = (kind: "success" | "error", message: string) => {
      if (active) setNativeNotice({ kind, message });
    };
    const handleTrayAction = async (action: TrayAction) => {
      try {
        if (action === "scan_all") {
          const repositories = await client.listRepositories();
          for (const repository of repositories.items) await client.syncRepository(repository.id);
          await queryClient.invalidateQueries({ queryKey: ["repositories"] });
          await queryClient.invalidateQueries({ queryKey: ["pull-requests"] });
          report("success", localized(`托盘扫描完成：${repositories.items.length} 个仓库。`, `Tray scan completed for ${repositories.items.length} repositories.`));
        } else if (action === "pause_monitoring" || action === "resume_monitoring") {
          const enabled = action === "resume_monitoring";
          await client.updateSettings({ background_monitoring: enabled });
          await queryClient.invalidateQueries({ queryKey: ["settings"] });
          report("success", enabled ? localized("后台监控已恢复。", "Background monitoring resumed.") : localized("后台监控已暂停。若有当前轮询，会安全完成当前请求。", "Background monitoring paused; an active poll will finish safely."));
        } else if (action === "recent_pull_requests") {
          useUiStore.getState().setActiveView("pull-requests");
        } else if (action === "high_risk_pull_requests") {
          const [pullRequests, runs] = await Promise.all([client.listPullRequests(), client.listRuns()]);
          let selected: { id: string; repository_id: string } | null = null;
          for (const run of runs.items) {
            if (!run.pull_request_id) continue;
            const findings = await client.listFindings(run.id);
            if (findings.some((finding) => finding.severity === "high" || finding.severity === "critical")) {
              const pullRequest = pullRequests.items.find((item) => item.id === run.pull_request_id);
              if (pullRequest) selected = pullRequest;
              break;
            }
          }
          if (selected) useUiStore.getState().selectPullRequest(selected.id, selected.repository_id);
          else {
            useUiStore.getState().setActiveView("pull-requests");
            report("success", localized("当前持久化 Findings 中没有高风险 Pull Request。", "No high-risk Pull Request exists in persisted Findings."));
          }
        } else if (action === "settings") {
          useUiStore.getState().setActiveView("settings");
        } else if (action === "logs" || action === "diagnostics") {
          useUiStore.getState().setActiveView("diagnostics");
        }
      } catch (error) {
        report("error", `${localized("托盘操作失败", "Tray operation failed")}: ${errorMessage(error)}`);
      }
    };
    const handleDeepLink = async (route: DeepLinkRoute) => {
      try {
        if (route.kind === "run") {
          await client.getRun(route.run_id);
          useUiStore.getState().selectRun(route.run_id);
          return;
        }
        const repositories = await client.listRepositories();
        const repository = repositories.items.find((item) => item.full_name === `${route.owner}/${route.repository}`);
        if (!repository) throw new Error(localized("深链仓库尚未添加到 TraceGate。", "The deep-linked repository is not enrolled in TraceGate."));
        if (route.kind === "repository") {
          useUiStore.getState().selectRepository(repository.id);
          return;
        }
        const pullRequests = await client.listPullRequests(repository.id);
        const pullRequest = pullRequests.items.find((item) => item.number === route.number);
        if (!pullRequest) throw new Error(localized("深链 Pull Request 尚未同步。", "The deep-linked Pull Request is not synchronized."));
        useUiStore.getState().selectPullRequest(pullRequest.id, repository.id);
      } catch (error) {
        report("error", `${localized("深链打开失败", "Deep link failed")}: ${errorMessage(error)}`);
      }
    };
    if (host.onTrayAction) {
      void host.onTrayAction((action) => void handleTrayAction(action)).then((stop) => {
        if (active) unregister.push(stop); else stop();
      }).catch((error: unknown) => report("error", `${localized("托盘监听失败", "Tray listener failed")}: ${errorMessage(error)}`));
    }
    if (host.onDeepLink) {
      void host.onDeepLink((route) => void handleDeepLink(route)).then((stop) => {
        if (active) unregister.push(stop); else stop();
      }).catch((error: unknown) => report("error", `${localized("深链监听失败", "Deep-link listener failed")}: ${errorMessage(error)}`));
    }
    if (host.onCloseRequested) {
      void host.onCloseRequested(() => {
        if (settingsQuery.data?.close_notice_dismissed && host.hideMainWindow) {
          void host.hideMainWindow().catch((error: unknown) => report("error", `${localized("隐藏窗口失败", "Could not hide window")}: ${errorMessage(error)}`));
        } else {
          setDismissClosePrompt(false);
          setClosePromptOpen(true);
        }
      }).then((stop) => {
        if (active) unregister.push(stop); else stop();
      }).catch((error: unknown) => report("error", `${localized("关闭事件监听失败", "Close listener failed")}: ${errorMessage(error)}`));
    }
    return () => {
      active = false;
      unregister.forEach((stop) => stop());
    };
  }, [client, host, locale, queryClient, settingsQuery.data?.close_notice_dismissed]);

  async function continueInBackground() {
    if (!host.hideMainWindow) return;
    setCloseBusy(true);
    try {
      if (dismissClosePrompt) {
        await client.updateSettings({ close_notice_dismissed: true });
        await queryClient.invalidateQueries({ queryKey: ["settings"] });
      }
      await host.hideMainWindow();
      setClosePromptOpen(false);
    } catch (error) {
      setNativeNotice({ kind: "error", message: `${text("隐藏窗口失败", "Could not hide window")}: ${errorMessage(error)}` });
    } finally {
      setCloseBusy(false);
    }
  }

  const activeLabel = activeView === "pull-request-detail"
    ? text("PR 详情", "PR Details")
    : (() => { const item = navigation.find((entry) => entry.id === activeView); return item ? text(item.zh, item.en) : text("概览", "Overview"); })();

  return (
    <I18nProvider locale={locale}><div className="studio-shell">
      <aside className={`sidebar${sidebarOpen ? " sidebar-open" : ""}`}>
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true"><i />TG</span>
          <div>
            <strong>TraceGate</strong>
            <span>STUDIO · LOCAL</span>
          </div>
        </div>

        <nav className="primary-nav" aria-label={text("主导航", "Primary navigation")}>
          {navigation.map((item) => (
            <button
              key={item.id}
              type="button"
              className={activeView === item.id ? "nav-item nav-item-active" : "nav-item"}
              aria-current={activeView === item.id ? "page" : undefined}
              onClick={() => setActiveView(item.id)}
            >
              <span className="nav-glyph">{item.glyph}</span>
              <span>
                <strong>{text(item.zh, item.en)}</strong>
                <small>{text(item.descriptionZh, item.descriptionEn)}</small>
              </span>
            </button>
          ))}
        </nav>

        <div className="sidebar-status" aria-label={text("连接摘要", "Connection summary")}>
          <span className="eyebrow">CONNECTIONS</span>
          <div>
            <span>{text("本地后端", "Local backend")}</span>
            {statusQuery.data ? <StatusBadge compact status={statusQuery.data.components.api} /> : <PendingStatusBadge />}
          </div>
          <div>
            <span>GitHub</span>
            {statusQuery.data ? <StatusBadge compact status={statusQuery.data.components.github} /> : <PendingStatusBadge />}
          </div>
          <div>
            <span>{text("模型", "Model")}</span>
            {statusQuery.data ? <StatusBadge compact status={statusQuery.data.components.model} /> : <PendingStatusBadge />}
          </div>
        </div>

        <div className="host-caption">
          <span>{host.displayName}</span>
          <small>{text("API Token 仅驻留内存", "API token stays in memory")}</small>
        </div>
      </aside>

      {sidebarOpen ? (
        <button className="sidebar-scrim" type="button" aria-label={text("关闭导航", "Close navigation")} onClick={() => setSidebarOpen(false)} />
      ) : null}

      <main className="workspace">
        <header className="workspace-header">
          <button className="mobile-menu" type="button" aria-label={text("打开导航", "Open navigation")} onClick={() => setSidebarOpen(true)}>
            <span /><span /><span />
          </button>
          <div>
            <span className="eyebrow">TRACEGATE STUDIO</span>
            <h1>{activeLabel}</h1>
          </div>
          <div className="header-status">
            <button className="command-trigger" type="button" onClick={() => setCommandPaletteOpen(true)} aria-label={text("打开命令面板", "Open command palette")}><span>{text("搜索", "Search")}</span><kbd>⌘K</kbd></button>
            <span>{text("后端", "Backend")}</span>
            {statusQuery.data ? <StatusBadge status={statusQuery.data.components.api} /> : <PendingStatusBadge />}
          </div>
        </header>

        {statusQuery.isError ? (
          <div className="global-error">
            <ErrorState
              title={text("系统状态检查失败", "System status check failed")}
              message={errorMessage(statusQuery.error)}
              onRetry={() => void statusQuery.refetch()}
            />
          </div>
        ) : null}

        {nativeNotice ? <div className={nativeNotice.kind === "error" ? "global-error inline-error" : "global-error inline-success"} role={nativeNotice.kind === "error" ? "alert" : "status"}>{nativeNotice.message}<button className="text-button" type="button" onClick={() => setNativeNotice(null)}>{text("关闭", "Close")}</button></div> : null}

        {closePromptOpen ? <div className="modal-backdrop" role="presentation"><section className="confirmation-modal" role="dialog" aria-modal="true" aria-labelledby="close-background-title"><span className="eyebrow">BACKGROUND MONITORING</span><h2 id="close-background-title">{text("TraceGate 将继续在后台监控 PR。", "TraceGate will continue monitoring PRs in the background.")}</h2><p>{text("关闭主窗口不会结束 Sidecar 或当前监控；只有“退出 TraceGate”会终止所有子进程。", "Closing the main window does not stop the Sidecar or monitoring. Only Quit TraceGate terminates all child processes.")}</p><label className="switch-row"><span><strong>{text("不再提示", "Do not show again")}</strong><small>{text("以后关闭窗口时直接隐藏。", "Hide the window immediately on future close requests.")}</small></span><input type="checkbox" checked={dismissClosePrompt} onChange={(event) => setDismissClosePrompt(event.target.checked)} /></label><div className="form-actions"><button className="button button-secondary" type="button" disabled={closeBusy} onClick={() => setClosePromptOpen(false)}>{text("取消", "Cancel")}</button><button className="button button-primary" type="button" disabled={closeBusy} onClick={() => void continueInBackground()}>{closeBusy ? text("处理中…", "Working…") : text("继续在后台运行", "Continue in background")}</button></div></section></div> : null}
        {commandPaletteOpen ? <CommandPalette onClose={() => setCommandPaletteOpen(false)} /> : null}

        <div className="workspace-content"><Suspense fallback={<LoadingState label={text("正在加载代码视图…", "Loading code view…")} />}>
          {activeView === "dashboard" ? <DashboardPage /> : null}
          {activeView === "repositories" ? <RepositoryPage host={host} /> : null}
          {activeView === "pull-requests" ? <PullRequestInboxPage /> : null}
          {activeView === "pull-request-detail" ? <PullRequestDetailPage host={host} /> : null}
          {activeView === "repository-map" ? <RepositoryMapPage host={host} /> : null}
          {activeView === "runs" ? <AgentRunsPage /> : null}
          {activeView === "eval" ? <EvalCenterPage /> : null}
          {activeView === "registry" ? <RegistryPage /> : null}
          {activeView === "diagnostics" ? <DiagnosticsPage /> : null}
          {activeView === "onboarding" ? <OnboardingPage host={host} /> : null}
          {activeView === "settings" ? <SettingsPage host={host} /> : null}
        </Suspense></div>
      </main>
    </div></I18nProvider>
  );
}
