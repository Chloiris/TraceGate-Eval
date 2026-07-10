import { lazy, Suspense, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useSettings, useSystemStatus } from "./api/queries";
import { useApiClient } from "./api/clientContext";
import { ErrorState, LoadingState } from "./components/RequestState";
import { PendingStatusBadge, StatusBadge } from "./components/StatusBadge";
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
  const [nativeNotice, setNativeNotice] = useState<{ kind: "success" | "error"; message: string } | null>(null);
  const locale: StudioLocale = settingsQuery.data?.language ?? "zh-CN";
  const text = (zh: string, en: string) => locale === "en-US" ? en : zh;

  useEffect(() => {
    const theme = settingsQuery.data?.theme ?? "system";
    document.documentElement.dataset.theme = theme;
    document.documentElement.lang = settingsQuery.data?.language ?? "zh-CN";
  }, [settingsQuery.data?.language, settingsQuery.data?.theme]);

  useEffect(() => {
    let active = true;
    const unregister: (() => void)[] = [];
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
          report("success", `托盘扫描完成：${repositories.items.length} 个仓库。`);
        } else if (action === "pause_monitoring" || action === "resume_monitoring") {
          const enabled = action === "resume_monitoring";
          await client.updateSettings({ background_monitoring: enabled });
          await queryClient.invalidateQueries({ queryKey: ["settings"] });
          report("success", enabled ? "后台监控已恢复。" : "后台监控已暂停。若有当前轮询，会安全完成当前请求。" );
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
            report("success", "当前持久化 Findings 中没有高风险 Pull Request。" );
          }
        } else if (action === "settings") {
          useUiStore.getState().setActiveView("settings");
        } else if (action === "logs" || action === "diagnostics") {
          useUiStore.getState().setActiveView("diagnostics");
        }
      } catch (error) {
        report("error", `托盘操作失败：${errorMessage(error)}`);
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
        if (!repository) throw new Error("深链仓库尚未添加到 TraceGate。" );
        if (route.kind === "repository") {
          useUiStore.getState().selectRepository(repository.id);
          return;
        }
        const pullRequests = await client.listPullRequests(repository.id);
        const pullRequest = pullRequests.items.find((item) => item.number === route.number);
        if (!pullRequest) throw new Error("深链 Pull Request 尚未同步。" );
        useUiStore.getState().selectPullRequest(pullRequest.id, repository.id);
      } catch (error) {
        report("error", `深链打开失败：${errorMessage(error)}`);
      }
    };
    if (host.onTrayAction) {
      void host.onTrayAction((action) => void handleTrayAction(action)).then((stop) => {
        if (active) unregister.push(stop); else stop();
      }).catch((error: unknown) => report("error", `托盘监听失败：${errorMessage(error)}`));
    }
    if (host.onDeepLink) {
      void host.onDeepLink((route) => void handleDeepLink(route)).then((stop) => {
        if (active) unregister.push(stop); else stop();
      }).catch((error: unknown) => report("error", `深链监听失败：${errorMessage(error)}`));
    }
    return () => {
      active = false;
      unregister.forEach((stop) => stop());
    };
  }, [client, host, queryClient]);

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

        <div className="workspace-content"><Suspense fallback={<LoadingState label="正在加载代码视图…" />}>
          {activeView === "dashboard" ? <DashboardPage /> : null}
          {activeView === "repositories" ? <RepositoryPage /> : null}
          {activeView === "pull-requests" ? <PullRequestInboxPage /> : null}
          {activeView === "pull-request-detail" ? <PullRequestDetailPage /> : null}
          {activeView === "repository-map" ? <RepositoryMapPage /> : null}
          {activeView === "runs" ? <AgentRunsPage /> : null}
          {activeView === "eval" ? <EvalCenterPage /> : null}
          {activeView === "registry" ? <RegistryPage /> : null}
          {activeView === "diagnostics" ? <DiagnosticsPage /> : null}
          {activeView === "onboarding" ? <OnboardingPage /> : null}
          {activeView === "settings" ? <SettingsPage host={host} /> : null}
        </Suspense></div>
      </main>
    </div></I18nProvider>
  );
}
