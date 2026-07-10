import { useState, type FormEvent } from "react";
import type { Settings } from "@tracegate/shared-types";

import { StatusCard } from "../components/StatusCard";
import { ErrorState, LoadingState } from "../components/RequestState";
import { useSettings, useSystemStatus, useUpdateSettings } from "../api/queries";
import { reservedWebViewHosts, type HostBridge } from "../host/hostBridge";
import { errorMessage } from "../lib/errors";

interface SettingsPageProps {
  host: HostBridge;
}

export function SettingsPage({ host }: SettingsPageProps) {
  const settingsQuery = useSettings();
  const statusQuery = useSystemStatus();

  if (settingsQuery.isPending) {
    return <LoadingState label="正在读取设置…" />;
  }
  if (settingsQuery.isError) {
    return (
      <ErrorState
        title="无法读取设置"
        message={errorMessage(settingsQuery.error)}
        onRetry={() => void settingsQuery.refetch()}
      />
    );
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <span className="eyebrow">本地偏好</span>
        <h2>设置</h2>
        <p>设置通过受鉴权的本地 API 保存。API Token 不会出现在表单、日志或浏览器存储中。</p>
      </header>

      <SettingsEditor key={settingsQuery.data.updated_at} settings={settingsQuery.data} />

      <section aria-labelledby="provider-settings-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">只读连接状态</span>
            <h2 id="provider-settings-title">Provider</h2>
          </div>
        </div>
        {statusQuery.isPending ? <LoadingState label="正在检查 Provider…" /> : null}
        {statusQuery.isError ? (
          <ErrorState title="Provider 状态不可用" message={errorMessage(statusQuery.error)} />
        ) : null}
        {statusQuery.data ? (
          <div className="status-grid status-grid-two">
            <StatusCard eyebrow="GITHUB" title="代码托管连接" status={statusQuery.data.components.github} />
            <StatusCard eyebrow="MODEL" title="语义模型连接" status={statusQuery.data.components.model} />
          </div>
        ) : null}
        <p className="field-note">
          P0 API 尚未提供凭据写入端点，因此本页面不会展示不可用的“连接”按钮，也不会把 Token
          保存进普通设置。
        </p>
      </section>

      <section className="settings-panel" aria-labelledby="host-title">
        <span className="eyebrow">HOST BRIDGE</span>
        <h2 id="host-title">当前宿主：{host.displayName}</h2>
        <p>BrowserHost 从显式环境变量读取开发 Token；TauriHost 通过原生命令取得临时连接信息。</p>
        <ul className="plain-list">
          {reservedWebViewHosts.map((adapter) => (
            <li key={adapter.kind}>{adapter.note}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function SettingsEditor({ settings }: { settings: Settings }) {
  const updateSettings = useUpdateSettings();
  const [theme, setTheme] = useState(settings.theme);
  const [language, setLanguage] = useState(settings.language);
  const [backgroundMonitoring, setBackgroundMonitoring] = useState(settings.background_monitoring);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateSettings.mutate({
      theme,
      language,
      background_monitoring: backgroundMonitoring,
      launch_at_startup: settings.launch_at_startup,
    });
  }

  return (
    <form className="settings-panel" onSubmit={submit}>
      <div className="form-grid">
        <label className="field">
          <span>主题</span>
          <select value={theme} onChange={(event) => setTheme(event.target.value as Settings["theme"])}>
            <option value="system">跟随系统</option>
            <option value="light">浅色</option>
            <option value="dark">深色</option>
          </select>
        </label>
        <label className="field">
          <span>语言</span>
          <select value={language} onChange={(event) => setLanguage(event.target.value as Settings["language"])}>
            <option value="zh-CN">简体中文</option>
            <option value="en-US">English（界面翻译待完善）</option>
          </select>
        </label>
      </div>

      <label className="switch-row">
        <span>
          <strong>后台监控偏好</strong>
          <small>控制后端在能力可用时是否启动仓库轮询；当前状态不会被伪造。</small>
        </span>
        <input
          type="checkbox"
          checked={backgroundMonitoring}
          onChange={(event) => setBackgroundMonitoring(event.target.checked)}
        />
      </label>

      <div className="switch-row switch-disabled" aria-disabled="true">
        <span>
          <strong>开机启动</strong>
          <small>桌面原生能力尚未接入，当前仅显示已保存偏好，不能在 Web 中修改。</small>
        </span>
        <input type="checkbox" checked={settings.launch_at_startup} disabled readOnly />
      </div>

      <div className="provider-summary">
        <span>模型配置</span>
        <strong>{settings.model_provider && settings.model_name ? `${settings.model_provider} / ${settings.model_name}` : "模型尚未配置"}</strong>
      </div>

      {updateSettings.isError ? (
        <p className="inline-error" role="alert">保存失败：{errorMessage(updateSettings.error)}</p>
      ) : null}
      {updateSettings.isSuccess ? (
        <p className="inline-success" role="status">设置已由本地后端确认保存。</p>
      ) : null}

      <div className="form-actions">
        <button className="button button-primary" type="submit" disabled={updateSettings.isPending}>
          {updateSettings.isPending ? "保存中…" : "保存设置"}
        </button>
      </div>
    </form>
  );
}
