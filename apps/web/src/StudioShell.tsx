import { useEffect } from "react";

import { useSettings, useSystemStatus } from "./api/queries";
import { ErrorState } from "./components/RequestState";
import { PendingStatusBadge, StatusBadge } from "./components/StatusBadge";
import type { HostBridge } from "./host/hostBridge";
import { errorMessage } from "./lib/errors";
import { DashboardPage } from "./pages/DashboardPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { SettingsPage } from "./pages/SettingsPage";
import { useUiStore, type StudioView } from "./store/uiStore";

const navigation: readonly { id: StudioView; label: string; description: string; glyph: string }[] = [
  { id: "dashboard", label: "概览", description: "系统与连接状态", glyph: "01" },
  { id: "onboarding", label: "首次引导", description: "完成基础配置", glyph: "02" },
  { id: "settings", label: "设置", description: "本地偏好与宿主", glyph: "03" },
];

export function StudioShell({ host }: { host: HostBridge }) {
  const activeView = useUiStore((state) => state.activeView);
  const sidebarOpen = useUiStore((state) => state.sidebarOpen);
  const setActiveView = useUiStore((state) => state.setActiveView);
  const setSidebarOpen = useUiStore((state) => state.setSidebarOpen);
  const statusQuery = useSystemStatus();
  const settingsQuery = useSettings();

  useEffect(() => {
    const theme = settingsQuery.data?.theme ?? "system";
    document.documentElement.dataset.theme = theme;
    document.documentElement.lang = settingsQuery.data?.language ?? "zh-CN";
  }, [settingsQuery.data?.language, settingsQuery.data?.theme]);

  const activeLabel = navigation.find((item) => item.id === activeView)?.label ?? "概览";

  return (
    <div className="studio-shell">
      <aside className={`sidebar${sidebarOpen ? " sidebar-open" : ""}`}>
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true"><i />TG</span>
          <div>
            <strong>TraceGate</strong>
            <span>STUDIO · LOCAL</span>
          </div>
        </div>

        <nav className="primary-nav" aria-label="主导航">
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
                <strong>{item.label}</strong>
                <small>{item.description}</small>
              </span>
            </button>
          ))}
        </nav>

        <div className="sidebar-status" aria-label="连接摘要">
          <span className="eyebrow">CONNECTIONS</span>
          <div>
            <span>本地后端</span>
            {statusQuery.data ? <StatusBadge compact status={statusQuery.data.components.api} /> : <PendingStatusBadge />}
          </div>
          <div>
            <span>GitHub</span>
            {statusQuery.data ? <StatusBadge compact status={statusQuery.data.components.github} /> : <PendingStatusBadge />}
          </div>
          <div>
            <span>模型</span>
            {statusQuery.data ? <StatusBadge compact status={statusQuery.data.components.model} /> : <PendingStatusBadge />}
          </div>
        </div>

        <div className="host-caption">
          <span>{host.displayName}</span>
          <small>API Token 仅驻留内存</small>
        </div>
      </aside>

      {sidebarOpen ? (
        <button className="sidebar-scrim" type="button" aria-label="关闭导航" onClick={() => setSidebarOpen(false)} />
      ) : null}

      <main className="workspace">
        <header className="workspace-header">
          <button className="mobile-menu" type="button" aria-label="打开导航" onClick={() => setSidebarOpen(true)}>
            <span /><span /><span />
          </button>
          <div>
            <span className="eyebrow">TRACEGATE STUDIO</span>
            <h1>{activeLabel}</h1>
          </div>
          <div className="header-status">
            <span>后端</span>
            {statusQuery.data ? <StatusBadge status={statusQuery.data.components.api} /> : <PendingStatusBadge />}
          </div>
        </header>

        {statusQuery.isError ? (
          <div className="global-error">
            <ErrorState
              title="系统状态检查失败"
              message={errorMessage(statusQuery.error)}
              onRetry={() => void statusQuery.refetch()}
            />
          </div>
        ) : null}

        <div className="workspace-content">
          {activeView === "dashboard" ? <DashboardPage /> : null}
          {activeView === "onboarding" ? <OnboardingPage /> : null}
          {activeView === "settings" ? <SettingsPage host={host} /> : null}
        </div>
      </main>
    </div>
  );
}
