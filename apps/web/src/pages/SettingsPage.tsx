import { useEffect, useState, type FormEvent } from "react";
import type { CredentialKind, CredentialStatus, Settings } from "@tracegate/shared-types";

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
          密钥不经过 FastAPI 设置端点，也不写入 SQLite。桌面端使用系统安全凭据存储；浏览器开发模式
          继续要求显式环境变量。
        </p>
        <CredentialPanel host={host} />
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

const credentialLabels: Record<CredentialKind, { title: string; placeholder: string }> = {
  github: { title: "GitHub Fine-grained PAT", placeholder: "输入 GitHub Token" },
  model: { title: "模型 API Key", placeholder: "输入模型 Provider 密钥" },
};

function CredentialPanel({ host }: { host: HostBridge }) {
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
    return <p className="field-note">浏览器宿主不提供密钥写入。请通过后端进程环境变量配置真实凭据。</p>;
  }

  async function save(kind: CredentialKind) {
    if (!storeCredential) {
      setFailure("当前宿主不支持系统安全凭据存储。");
      return;
    }
    setBusy(kind);
    setFailure(null);
    setMessage(null);
    try {
      const status = await storeCredential(kind, values[kind]);
      setStatuses((current) => ({ ...current, [kind]: status }));
      setValues((current) => ({ ...current, [kind]: "" }));
      setMessage(`${credentialLabels[kind].title} 已写入 ${status.storage}。重启 TraceGate 后后端连接状态生效。`);
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setBusy(null);
    }
  }

  async function remove(kind: CredentialKind) {
    if (!deleteCredential) {
      setFailure("当前宿主不支持系统安全凭据存储。");
      return;
    }
    setBusy(kind);
    setFailure(null);
    setMessage(null);
    try {
      const status = await deleteCredential(kind);
      setStatuses((current) => ({ ...current, [kind]: status }));
      setMessage(`${credentialLabels[kind].title} 已从 ${status.storage} 删除。重启 TraceGate 后后端连接状态生效。`);
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
              <span>{credentialLabels[kind].title}</span>
              <input
                type="password"
                autoComplete="new-password"
                value={values[kind]}
                placeholder={credentialLabels[kind].placeholder}
                onChange={(event) => setValues((current) => ({ ...current, [kind]: event.target.value }))}
              />
            </label>
            <p className="field-note">
              {status ? `${status.configured ? "已配置" : "未配置"} · ${status.storage}` : "正在读取安全存储状态…"}
            </p>
            <div className="form-actions">
              <button
                className="button button-primary"
                type="button"
                disabled={busy !== null || values[kind].length < 20}
                onClick={() => void save(kind)}
              >
                保存到系统凭据库
              </button>
              <button
                className="button button-secondary"
                type="button"
                disabled={busy !== null || !status?.configured}
                onClick={() => void remove(kind)}
              >
                删除
              </button>
            </div>
          </div>
        );
      })}
      {message ? <p className="inline-success" role="status">{message}</p> : null}
      {failure ? <p className="inline-error" role="alert">安全凭据操作失败：{failure}</p> : null}
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
