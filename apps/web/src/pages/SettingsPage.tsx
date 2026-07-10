import { useEffect, useState, type FormEvent } from "react";
import type { CredentialKind, CredentialStatus, Settings } from "@tracegate/shared-types";

import { StatusCard } from "../components/StatusCard";
import { ErrorState, LoadingState } from "../components/RequestState";
import { useSettings, useSystemStatus, useUpdateSettings } from "../api/queries";
import { reservedWebViewHosts, type HostBridge } from "../host/hostBridge";
import { errorMessage } from "../lib/errors";
import { useI18n } from "../i18n";

interface SettingsPageProps {
  host: HostBridge;
}

export function SettingsPage({ host }: SettingsPageProps) {
  const { text } = useI18n();
  const settingsQuery = useSettings();
  const statusQuery = useSystemStatus();

  if (settingsQuery.isPending) {
    return <LoadingState label={text("正在读取设置…", "Reading settings…")} />;
  }
  if (settingsQuery.isError) {
    return (
      <ErrorState
        title={text("无法读取设置", "Unable to read settings")}
        message={errorMessage(settingsQuery.error)}
        onRetry={() => void settingsQuery.refetch()}
      />
    );
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <span className="eyebrow">{text("本地偏好", "LOCAL PREFERENCES")}</span>
        <h2>{text("设置", "Settings")}</h2>
        <p>{text("设置通过受鉴权的本地 API 保存。API Token 不会出现在表单、日志或浏览器存储中。", "Settings are saved through the authenticated local API. API tokens never appear in forms, logs, or browser storage.")}</p>
      </header>

      <SettingsEditor key={settingsQuery.data.updated_at} settings={settingsQuery.data} host={host} />

      <section aria-labelledby="provider-settings-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">{text("只读连接状态", "READ-ONLY CONNECTION STATUS")}</span>
            <h2 id="provider-settings-title">Provider</h2>
          </div>
        </div>
        {statusQuery.isPending ? <LoadingState label={text("正在检查 Provider…", "Checking providers…")} /> : null}
        {statusQuery.isError ? (
          <ErrorState title={text("Provider 状态不可用", "Provider status unavailable")} message={errorMessage(statusQuery.error)} />
        ) : null}
        {statusQuery.data ? (
          <div className="status-grid status-grid-two">
            <StatusCard eyebrow="GITHUB" title={text("代码托管连接", "Code hosting connection")} status={statusQuery.data.components.github} />
            <StatusCard eyebrow="MODEL" title={text("语义模型连接", "Semantic model connection")} status={statusQuery.data.components.model} />
          </div>
        ) : null}
        <p className="field-note">
          {text("密钥不经过 FastAPI 设置端点，也不写入 SQLite。桌面端使用系统安全凭据存储；浏览器开发模式继续要求显式环境变量。", "Secrets never pass through the FastAPI settings endpoint or SQLite. Desktop uses the operating-system credential store; browser development mode still requires explicit environment variables.")}
        </p>
        <CredentialPanel host={host} />
      </section>

      <section className="settings-panel" aria-labelledby="host-title">
        <span className="eyebrow">HOST BRIDGE</span>
        <h2 id="host-title">{text("当前宿主", "Current host")}: {host.displayName}</h2>
        <p>{text("BrowserHost 从显式环境变量读取开发 Token；TauriHost 通过原生命令取得临时连接信息。", "BrowserHost reads a development token from explicit environment variables; TauriHost obtains temporary connection details through native commands.")}</p>
        <ul className="plain-list">
          {reservedWebViewHosts.map((adapter) => (
            <li key={adapter.kind}>{adapter.note}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

const credentialLabels: Record<CredentialKind, { titleZh: string; titleEn: string; placeholderZh: string; placeholderEn: string }> = {
  github: { titleZh: "GitHub Fine-grained PAT", titleEn: "GitHub fine-grained PAT", placeholderZh: "输入 GitHub Token", placeholderEn: "Enter GitHub token" },
  model: { titleZh: "模型 API Key", titleEn: "Model API key", placeholderZh: "输入模型 Provider 密钥", placeholderEn: "Enter model provider key" },
};

function CredentialPanel({ host }: { host: HostBridge }) {
  const { text } = useI18n();
  const readCredentialStatus = host.getCredentialStatus?.bind(host);
  const storeCredential = host.storeCredential?.bind(host);
  const deleteCredential = host.deleteCredential?.bind(host);
  const [statuses, setStatuses] = useState<Partial<Record<CredentialKind, CredentialStatus>>>({});
  const [values, setValues] = useState<Record<CredentialKind, string>>({ github: "", model: "" });
  const [busy, setBusy] = useState<CredentialKind | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    const readStatus = host.getCredentialStatus?.bind(host);
    if (!readStatus) return;
    let active = true;
    void Promise.all([readStatus("github"), readStatus("model")])
      .then(([github, model]) => {
        if (active) setStatuses({ github, model });
      })
      .catch((error: unknown) => {
        if (active) setFailure(errorMessage(error));
      });
    return () => {
      active = false;
    };
  }, [host]);

  if (!storeCredential || !deleteCredential || !readCredentialStatus) {
    return <p className="field-note">{text("浏览器宿主不提供密钥写入。请通过后端进程环境变量配置真实凭据。", "The browser host cannot write secrets. Configure real credentials through backend process environment variables.")}</p>;
  }

  async function save(kind: CredentialKind) {
    if (!storeCredential) {
      setFailure(text("当前宿主不支持系统安全凭据存储。", "The current host does not support secure credential storage."));
      return;
    }
    setBusy(kind);
    setFailure(null);
    setMessage(null);
    try {
      const status = await storeCredential(kind, values[kind]);
      setStatuses((current) => ({ ...current, [kind]: status }));
      setValues((current) => ({ ...current, [kind]: "" }));
      setMessage(text(`${credentialLabels[kind].titleZh} 已写入 ${status.storage}。重启 TraceGate 后后端连接状态生效。`, `${credentialLabels[kind].titleEn} was written to ${status.storage}. Restart TraceGate to apply the backend connection.`));
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setBusy(null);
    }
  }

  async function remove(kind: CredentialKind) {
    if (!deleteCredential) {
      setFailure(text("当前宿主不支持系统安全凭据存储。", "The current host does not support secure credential storage."));
      return;
    }
    setBusy(kind);
    setFailure(null);
    setMessage(null);
    try {
      const status = await deleteCredential(kind);
      setStatuses((current) => ({ ...current, [kind]: status }));
      setMessage(text(`${credentialLabels[kind].titleZh} 已从 ${status.storage} 删除。重启 TraceGate 后后端连接状态生效。`, `${credentialLabels[kind].titleEn} was removed from ${status.storage}. Restart TraceGate to apply the backend connection.`));
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="credential-grid">
      {(["github", "model"] as const).map((kind) => {
        const status = statuses[kind];
        return (
          <div className="credential-card" key={kind}>
            <label className="field">
              <span>{text(credentialLabels[kind].titleZh, credentialLabels[kind].titleEn)}</span>
              <input
                type="password"
                autoComplete="new-password"
                value={values[kind]}
                placeholder={text(credentialLabels[kind].placeholderZh, credentialLabels[kind].placeholderEn)}
                onChange={(event) => setValues((current) => ({ ...current, [kind]: event.target.value }))}
              />
            </label>
            <p className="field-note">
              {status ? `${status.configured ? text("已配置", "Configured") : text("未配置", "Not configured")} · ${status.storage}` : text("正在读取安全存储状态…", "Reading secure storage status…")}
            </p>
            <div className="form-actions">
              <button
                className="button button-primary"
                type="button"
                disabled={busy !== null || values[kind].length < 20}
                onClick={() => void save(kind)}
              >
                {text("保存到系统凭据库", "Save to system credential store")}
              </button>
              <button
                className="button button-secondary"
                type="button"
                disabled={busy !== null || !status?.configured}
                onClick={() => void remove(kind)}
              >
                {text("删除", "Delete")}
              </button>
            </div>
          </div>
        );
      })}
      {message ? <p className="inline-success" role="status">{message}</p> : null}
      {failure ? <p className="inline-error" role="alert">{text("安全凭据操作失败", "Secure credential operation failed")}: {failure}</p> : null}
    </div>
  );
}

function SettingsEditor({ settings, host }: { settings: Settings; host: HostBridge }) {
  const { text } = useI18n();
  const updateSettings = useUpdateSettings();
  const [theme, setTheme] = useState(settings.theme);
  const [language, setLanguage] = useState(settings.language);
  const [backgroundMonitoring, setBackgroundMonitoring] = useState(settings.background_monitoring);
  const [launchAtStartup, setLaunchAtStartup] = useState(settings.launch_at_startup);
  const [nativeAutostartAvailable, setNativeAutostartAvailable] = useState(Boolean(host.getAutostartEnabled));
  const [nativeBusy, setNativeBusy] = useState(false);
  const [nativeMessage, setNativeMessage] = useState<string | null>(null);
  const [nativeFailure, setNativeFailure] = useState<string | null>(null);

  useEffect(() => {
    const readAutostart = host.getAutostartEnabled?.bind(host);
    if (!readAutostart) return;
    let active = true;
    void readAutostart()
      .then((enabled) => {
        if (active) {
          setLaunchAtStartup(enabled);
          setNativeAutostartAvailable(true);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setNativeAutostartAvailable(false);
          setNativeFailure(`${text("无法读取系统开机启动状态", "Unable to read system autostart state")}: ${errorMessage(error)}`);
        }
      });
    return () => {
      active = false;
    };
  }, [host, text]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNativeBusy(true);
    setNativeFailure(null);
    setNativeMessage(null);
    try {
      const confirmedAutostart = host.setAutostartEnabled
        ? await host.setAutostartEnabled(launchAtStartup)
        : settings.launch_at_startup;
      setLaunchAtStartup(confirmedAutostart);
      await updateSettings.mutateAsync({
        theme,
        language,
        background_monitoring: backgroundMonitoring,
        launch_at_startup: confirmedAutostart,
      });
    } catch (error) {
      setNativeFailure(errorMessage(error));
    } finally {
      setNativeBusy(false);
    }
  }

  async function testNotification() {
    if (!host.showReviewNotification) return;
    setNativeBusy(true);
    setNativeFailure(null);
    setNativeMessage(null);
    try {
      await host.showReviewNotification("TraceGate Studio", text("原生审查通知已连接。", "Native review notifications are connected."));
      setNativeMessage(text("通知已交给操作系统；是否展示取决于系统通知权限与勿扰设置。", "The notification was handed to the operating system; display depends on notification permission and focus settings."));
    } catch (error) {
      setNativeFailure(errorMessage(error));
    } finally {
      setNativeBusy(false);
    }
  }

  return (
    <form className="settings-panel" onSubmit={submit}>
      <div className="form-grid">
        <label className="field">
          <span>{text("主题", "Theme")}</span>
          <select value={theme} onChange={(event) => setTheme(event.target.value as Settings["theme"])}>
            <option value="system">{text("跟随系统", "System")}</option>
            <option value="light">{text("浅色", "Light")}</option>
            <option value="dark">{text("深色", "Dark")}</option>
          </select>
        </label>
        <label className="field">
          <span>{text("语言", "Language")}</span>
          <select value={language} onChange={(event) => setLanguage(event.target.value as Settings["language"])}>
            <option value="zh-CN">简体中文</option>
            <option value="en-US">English</option>
          </select>
        </label>
      </div>

      <label className="switch-row">
        <span>
          <strong>{text("后台监控偏好", "Background monitoring")}</strong>
          <small>{text("控制后端在能力可用时是否启动仓库轮询；当前状态不会被伪造。", "Controls repository polling when the capability is available; current state is never fabricated.")}</small>
        </span>
        <input
          type="checkbox"
          checked={backgroundMonitoring}
          onChange={(event) => setBackgroundMonitoring(event.target.checked)}
        />
      </label>

      <label className={nativeAutostartAvailable ? "switch-row" : "switch-row switch-disabled"}>
        <span>
          <strong>{text("开机启动", "Launch at startup")}</strong>
          <small>{nativeAutostartAvailable ? text("由操作系统原生启动项管理；保存后再次读取系统状态确认。", "Managed by the operating-system startup service and verified after saving.") : text("当前宿主不提供原生开机启动能力。", "The current host does not provide native autostart.")}</small>
        </span>
        <input
          type="checkbox"
          checked={launchAtStartup}
          disabled={!nativeAutostartAvailable || nativeBusy}
          onChange={(event) => setLaunchAtStartup(event.target.checked)}
        />
      </label>

      <div className="provider-summary">
        <span>{text("原生通知", "Native notifications")}</span>
        <button
          className="button button-secondary button-small"
          type="button"
          disabled={!host.showReviewNotification || nativeBusy}
          onClick={() => void testNotification()}
        >
          {text("发送测试通知", "Send test notification")}
        </button>
      </div>

      <div className="provider-summary">
        <span>{text("模型配置", "Model configuration")}</span>
        <strong>{settings.model_provider && settings.model_name ? `${settings.model_provider} / ${settings.model_name}` : text("模型尚未配置", "Model not configured")}</strong>
      </div>

      {updateSettings.isError ? (
        <p className="inline-error" role="alert">{text("保存失败", "Save failed")}: {errorMessage(updateSettings.error)}</p>
      ) : null}
      {updateSettings.isSuccess ? (
        <p className="inline-success" role="status">{text("设置已由本地后端确认保存。", "Settings were confirmed by the local backend.")}</p>
      ) : null}
      {nativeMessage ? <p className="inline-success" role="status">{nativeMessage}</p> : null}
      {nativeFailure ? <p className="inline-error" role="alert">{text("原生设置失败", "Native setting failed")}: {nativeFailure}</p> : null}

      <div className="form-actions">
        <button className="button button-primary" type="submit" disabled={updateSettings.isPending || nativeBusy}>
          {updateSettings.isPending || nativeBusy ? text("保存中…", "Saving…") : text("保存设置", "Save settings")}
        </button>
      </div>
    </form>
  );
}
