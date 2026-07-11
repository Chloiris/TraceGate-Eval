import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { settingsUpdateSchema, type CredentialKind, type CredentialStatus, type Settings } from "@tracegate/shared-types";

import { StatusCard } from "../components/StatusCard";
import { ErrorState, LoadingState } from "../components/RequestState";
import { queryKeys, useDiagnostics, useSettings, useSystemStatus, useUpdateSettings } from "../api/queries";
import { reservedWebViewHosts, type GitHubDeviceAuthorization, type HostBridge } from "../host/hostBridge";
import { errorMessage } from "../lib/errors";
import { useI18n } from "../i18n";
import { DiagnosticsContent } from "./DiagnosticsPage";

export type SettingsSection = "general" | "model" | "automation" | "connections" | "host" | "data" | "diagnostics";

interface SettingsPageProps {
  host: HostBridge;
  initialSection?: SettingsSection;
}

const settingsSections: readonly {
  id: SettingsSection;
  target: string;
  zh: string;
  en: string;
  descriptionZh: string;
  descriptionEn: string;
}[] = [
  { id: "general", target: "settings-general", zh: "常规", en: "General", descriptionZh: "外观与本地偏好", descriptionEn: "Appearance and local preferences" },
  { id: "model", target: "settings-model", zh: "模型", en: "Model", descriptionZh: "Provider 与运行参数", descriptionEn: "Provider and runtime" },
  { id: "automation", target: "settings-automation", zh: "自动化", en: "Automation", descriptionZh: "轮询、Relay 与分析", descriptionEn: "Polling, relay, and analysis" },
  { id: "connections", target: "settings-connections", zh: "连接与凭据", en: "Connections", descriptionZh: "安全存储与连接状态", descriptionEn: "Secure storage and status" },
  { id: "host", target: "settings-host", zh: "当前宿主", en: "Current host", descriptionZh: "桌面与浏览器能力", descriptionEn: "Desktop and browser capabilities" },
  { id: "data", target: "settings-data", zh: "安全与数据", en: "Security and data", descriptionZh: "策略、路径与存储", descriptionEn: "Policies, paths, and storage" },
  { id: "diagnostics", target: "settings-diagnostics", zh: "诊断", en: "Diagnostics", descriptionZh: "版本、指标与队列", descriptionEn: "Versions, metrics, and queues" },
];

export function SettingsPage({ host, initialSection = "general" }: SettingsPageProps) {
  const { text } = useI18n();
  const settingsQuery = useSettings();
  const statusQuery = useSystemStatus();
  const diagnosticsQuery = useDiagnostics();
  const [activeSection, setActiveSection] = useState<SettingsSection>(initialSection);

  useEffect(() => {
    setActiveSection(initialSection);
  }, [initialSection]);

  useEffect(() => {
    if (!settingsQuery.isSuccess || initialSection === "general") return;
    const section = settingsSections.find((item) => item.id === initialSection);
    const element = section ? document.getElementById(section.target) : null;
    if (element && typeof element.scrollIntoView === "function") {
      element.scrollIntoView({ block: "start" });
    }
  }, [initialSection, settingsQuery.isSuccess]);

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

      <div className="settings-layout">
        <nav className="settings-navigation" aria-label={text("设置目录", "Settings sections")}>
          <span className="eyebrow">{text("设置目录", "SETTINGS")}</span>
          {settingsSections.map((section) => (
            <a
              key={section.id}
              className={activeSection === section.id ? "settings-navigation-item settings-navigation-item-active" : "settings-navigation-item"}
              href={`#${section.target}`}
              aria-current={activeSection === section.id ? "location" : undefined}
              onClick={() => setActiveSection(section.id)}
            >
              <strong>{text(section.zh, section.en)}</strong>
              <small>{text(section.descriptionZh, section.descriptionEn)}</small>
            </a>
          ))}
        </nav>

        <div className="settings-content">
      <SettingsEditor key={settingsQuery.data.updated_at} settings={settingsQuery.data} host={host} />

      <section id="settings-connections" className="settings-anchor" aria-labelledby="provider-settings-title">
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
          <div className="status-grid">
            <StatusCard eyebrow="GITHUB" title={text("代码托管连接", "Code hosting connection")} status={statusQuery.data.components.github} />
            <StatusCard eyebrow="MODEL" title={text("语义模型连接", "Semantic model connection")} status={statusQuery.data.components.model} />
            <StatusCard eyebrow="RELAY" title="Webhook Relay" status={statusQuery.data.components.webhook_relay} />
          </div>
        ) : null}
        <p className="field-note">
          {text("密钥不经过 FastAPI 设置端点，也不写入 SQLite。桌面端使用系统安全凭据存储；浏览器开发模式继续要求显式环境变量。", "Secrets never pass through the FastAPI settings endpoint or SQLite. Desktop uses the operating-system credential store; browser development mode still requires explicit environment variables.")}
        </p>
        <CredentialPanel host={host} />
      </section>

      <section id="settings-host" className="settings-panel settings-anchor" aria-labelledby="host-title">
        <span className="eyebrow">HOST BRIDGE</span>
        <h2 id="host-title">{text("当前宿主", "Current host")}: {host.displayName}</h2>
        <p>{text("BrowserHost 从显式环境变量读取开发 Token；TauriHost 通过原生命令取得临时连接信息。", "BrowserHost reads a development token from explicit environment variables; TauriHost obtains temporary connection details through native commands.")}</p>
        <ul className="plain-list">
          {reservedWebViewHosts.map((adapter) => (
            <li key={adapter.kind}>{adapter.note}</li>
          ))}
        </ul>
      </section>

      <section id="settings-data" className="settings-panel settings-anchor" aria-labelledby="policy-title">
        <span className="eyebrow">POLICY · STORAGE · ABOUT</span>
        <h2 id="policy-title">{text("安全策略与本地数据", "Security policy and local data")}</h2>
        <dl className="metadata-grid">
          <div><dt>{text("命令执行策略", "Command execution policy")}</dt><dd>{text("只读默认；受限命令仅允许固定参数列表；写入需显式确认", "Read-only by default; restricted commands use fixed argument allowlists; writes require explicit confirmation")}</dd></div>
          <div><dt>{text("敏感文件规则", "Sensitive-file rules")}</dt><dd className="mono">.env* · .ssh · .aws · .azure · .kube · gcloud · id_rsa/id_ed25519 · credentials*</dd></div>
          <div><dt>{text("托盘模式", "Tray mode")}</dt><dd>{host.kind === "tauri" ? text("原生托盘驻留；只有退出命令终止 Sidecar", "Native tray residency; only Quit terminates the Sidecar") : text("浏览器宿主无原生托盘", "No native tray in the browser host")}</dd></div>
          <div><dt>{text("应用版本", "Application version")}</dt><dd>{diagnosticsQuery.data?.software_version ?? text("正在读取…", "Reading…")}</dd></div>
          <div><dt>{text("数据库模式", "Database mode")}</dt><dd>{diagnosticsQuery.data?.database_type ?? text("正在读取…", "Reading…")}</dd></div>
          <div><dt>{text("日志路径", "Log path")}</dt><dd className="mono">{diagnosticsQuery.data?.log_path ?? text("正在读取…", "Reading…")}</dd></div>
        </dl>
        {diagnosticsQuery.data ? <details><summary>{text("已授权工作区路径", "Authorized workspace paths")}</summary><ul className="plain-list">{diagnosticsQuery.data.workspace_paths.length ? diagnosticsQuery.data.workspace_paths.map((path) => <li className="mono" key={path}>{path}</li>) : <li>{text("尚无本地工作区", "No local workspaces")}</li>}</ul></details> : null}
        {diagnosticsQuery.isError ? <p className="inline-error">{text("诊断读取失败", "Unable to read diagnostics")}: {errorMessage(diagnosticsQuery.error)}</p> : null}
      </section>

      <section id="settings-diagnostics" className="settings-anchor" aria-label={text("诊断", "Diagnostics")}>
        <DiagnosticsContent embedded />
      </section>
        </div>
      </div>
    </div>
  );
}

const credentialLabels: Record<CredentialKind, { titleZh: string; titleEn: string; placeholderZh: string; placeholderEn: string }> = {
  github: { titleZh: "GitHub Fine-grained PAT", titleEn: "GitHub fine-grained PAT", placeholderZh: "输入 GitHub Token", placeholderEn: "Enter GitHub token" },
  model: { titleZh: "模型 API Key", titleEn: "Model API key", placeholderZh: "输入模型 Provider 密钥", placeholderEn: "Enter model provider key" },
  relay: { titleZh: "Webhook Relay 设备 Token", titleEn: "Webhook Relay device token", placeholderZh: "输入配对后返回的设备 Token", placeholderEn: "Enter the device token returned by pairing" },
};

function CredentialPanel({ host }: { host: HostBridge }) {
  const { text } = useI18n();
  const queryClient = useQueryClient();
  const readCredentialStatus = host.getCredentialStatus?.bind(host);
  const storeCredential = host.storeCredential?.bind(host);
  const deleteCredential = host.deleteCredential?.bind(host);
  const [statuses, setStatuses] = useState<Partial<Record<CredentialKind, CredentialStatus>>>({});
  const [values, setValues] = useState<Record<CredentialKind, string>>({ github: "", model: "", relay: "" });
  const [busy, setBusy] = useState<CredentialKind | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [oauthClientId, setOauthClientId] = useState("");
  const [oauthAuthorization, setOauthAuthorization] = useState<GitHubDeviceAuthorization | null>(null);
  const [oauthBusy, setOauthBusy] = useState(false);

  useEffect(() => {
    const readStatus = host.getCredentialStatus?.bind(host);
    if (!readStatus) return;
    let active = true;
    void Promise.all([readStatus("github"), readStatus("model"), readStatus("relay")])
      .then(([github, model, relay]) => {
        if (active) setStatuses({ github, model, relay });
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

  async function refreshConnectionState() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus }),
      queryClient.invalidateQueries({ queryKey: queryKeys.onboarding }),
    ]);
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
      await refreshConnectionState();
      setMessage(text(`${credentialLabels[kind].titleZh} 已写入 ${status.storage}，后端已重新加载凭据，连接状态已刷新。`, `${credentialLabels[kind].titleEn} was written to ${status.storage}. The backend reloaded the credential and refreshed the connection state.`));
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
      await refreshConnectionState();
      setMessage(text(`${credentialLabels[kind].titleZh} 已从 ${status.storage} 删除，后端已重新加载凭据，连接状态已刷新。`, `${credentialLabels[kind].titleEn} was removed from ${status.storage}. The backend reloaded credentials and refreshed the connection state.`));
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setBusy(null);
    }
  }

  async function beginDeviceFlow() {
    if (!host.beginGithubDeviceFlow) return;
    setOauthBusy(true);
    setFailure(null);
    setMessage(null);
    try {
      setOauthAuthorization(await host.beginGithubDeviceFlow(oauthClientId.trim()));
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setOauthBusy(false);
    }
  }

  async function pollDeviceFlow() {
    if (!host.pollGithubDeviceFlow) return;
    setOauthBusy(true);
    setFailure(null);
    try {
      const result = await host.pollGithubDeviceFlow();
      const credential = result.credential;
      if (result.status === "authorized" && credential) {
        setStatuses((current) => ({ ...current, github: credential }));
        setOauthAuthorization(null);
        await refreshConnectionState();
        setMessage(text(`GitHub OAuth Token 已写入 ${credential.storage}，后端已重新加载凭据，连接状态已刷新。`, `The GitHub OAuth token was stored in ${credential.storage}. The backend reloaded it and refreshed the connection state.`));
      } else {
        setMessage(text(`GitHub 仍在等待授权；请至少间隔 ${result.intervalSeconds} 秒再检查。`, `GitHub is still waiting for authorization; check again after at least ${result.intervalSeconds} seconds.`));
      }
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setOauthBusy(false);
    }
  }

  return (
    <div className="credential-grid">
      {(["github", "model", "relay"] as const).map((kind) => {
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
      {host.beginGithubDeviceFlow && host.pollGithubDeviceFlow ? <div className="credential-card oauth-card"><span className="eyebrow">GITHUB OAUTH DEVICE FLOW</span><h3>{text("不用粘贴 Token 连接 GitHub", "Connect GitHub without pasting a token")}</h3><label className="field"><span>OAuth App Client ID</span><input value={oauthClientId} onChange={(event) => setOauthClientId(event.target.value)} placeholder="Iv1…" /></label><button className="button button-secondary" type="button" disabled={oauthBusy || oauthClientId.trim().length < 8} onClick={() => void beginDeviceFlow()}>{text("开始设备授权", "Start device authorization")}</button>{oauthAuthorization ? <div className="oauth-code"><p>{text("在 GitHub 输入代码", "Enter this code on GitHub")}</p><strong className="mono">{oauthAuthorization.userCode}</strong><a className="button button-primary button-small" href={oauthAuthorization.verificationUri} target="_blank" rel="noreferrer">{text("打开 GitHub 授权页", "Open GitHub authorization")}</a><small>{text("过期时间", "Expires")}: {new Date(oauthAuthorization.expiresAtEpochMs).toLocaleString()}</small><button className="button button-secondary button-small" type="button" disabled={oauthBusy} onClick={() => void pollDeviceFlow()}>{text("我已授权，检查状态", "I authorized, check status")}</button></div> : null}<p className="field-note">{text("Client ID 不是密钥；Device Code 只保存在桌面进程内存中，Access Token 直接写入 Keychain/Credential Manager，永不返回 WebView。", "The client ID is not a secret. The device code stays in desktop process memory, and the access token is written directly to Keychain/Credential Manager without being returned to the WebView.")}</p></div> : null}
      {message ? <p className="inline-success" role="status">{message}</p> : null}
      {failure ? <p className="inline-error" role="alert">{text("安全凭据操作失败", "Secure credential operation failed")}: {failure}</p> : null}
    </div>
  );
}

function SettingsEditor({ settings, host }: { settings: Settings; host: HostBridge }) {
  const { text } = useI18n();
  const queryClient = useQueryClient();
  const updateSettings = useUpdateSettings();
  const [theme, setTheme] = useState(settings.theme);
  const [language, setLanguage] = useState(settings.language);
  const [backgroundMonitoring, setBackgroundMonitoring] = useState(settings.background_monitoring);
  const [notificationsEnabled, setNotificationsEnabled] = useState(settings.notifications_enabled);
  const [launchAtStartup, setLaunchAtStartup] = useState(settings.launch_at_startup);
  const [modelProvider, setModelProvider] = useState(settings.model_provider ?? "");
  const [modelBaseUrl, setModelBaseUrl] = useState(settings.model_base_url ?? "");
  const [modelName, setModelName] = useState(settings.model_name ?? "");
  const [modelTemperature, setModelTemperature] = useState(settings.model_temperature);
  const [modelMaxOutputTokens, setModelMaxOutputTokens] = useState(settings.model_max_output_tokens);
  const [modelTimeoutSeconds, setModelTimeoutSeconds] = useState(settings.model_timeout_seconds);
  const [modelMaxRetries, setModelMaxRetries] = useState(settings.model_max_retries);
  const [modelNativeStructuredOutput, setModelNativeStructuredOutput] = useState(settings.model_native_structured_output);
  const [modelStreamingEnabled, setModelStreamingEnabled] = useState(settings.model_streaming_enabled);
  const [modelNativeToolCalling, setModelNativeToolCalling] = useState(settings.model_native_tool_calling);
  const [modelContextScope, setModelContextScope] = useState(settings.model_context_scope);
  const [modelInputCostPerMillion, setModelInputCostPerMillion] = useState(settings.model_input_cost_per_million);
  const [modelOutputCostPerMillion, setModelOutputCostPerMillion] = useState(settings.model_output_cost_per_million);
  const [githubPollIntervalSeconds, setGithubPollIntervalSeconds] = useState(settings.github_poll_interval_seconds);
  const [automaticAnalysisEnabled, setAutomaticAnalysisEnabled] = useState(settings.automatic_analysis_enabled);
  const [automaticAnalysisIncludeDrafts, setAutomaticAnalysisIncludeDrafts] = useState(settings.automatic_analysis_include_drafts);
  const [automaticAnalysisRequireChecksSuccess, setAutomaticAnalysisRequireChecksSuccess] = useState(settings.automatic_analysis_require_checks_success);
  const [webhookRelayUrl, setWebhookRelayUrl] = useState(settings.webhook_relay_url ?? "");
  const [webhookRelayDeviceId, setWebhookRelayDeviceId] = useState(settings.webhook_relay_device_id ?? "");
  const [relayPairingCode, setRelayPairingCode] = useState("");
  const [relayPairingBusy, setRelayPairingBusy] = useState(false);
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
        notifications_enabled: notificationsEnabled,
        model_provider: modelProvider.trim() || null,
        model_base_url: modelBaseUrl.trim() || null,
        model_name: modelName.trim() || null,
        model_temperature: modelTemperature,
        model_max_output_tokens: modelMaxOutputTokens,
        model_timeout_seconds: modelTimeoutSeconds,
        model_max_retries: modelMaxRetries,
        model_native_structured_output: modelNativeStructuredOutput,
        model_streaming_enabled: modelStreamingEnabled,
        model_native_tool_calling: modelNativeToolCalling,
        model_context_scope: modelContextScope,
        model_input_cost_per_million: modelInputCostPerMillion,
        model_output_cost_per_million: modelOutputCostPerMillion,
        github_poll_interval_seconds: githubPollIntervalSeconds,
        automatic_analysis_enabled: automaticAnalysisEnabled,
        automatic_analysis_include_drafts: automaticAnalysisIncludeDrafts,
        automatic_analysis_require_checks_success: automaticAnalysisRequireChecksSuccess,
        webhook_relay_url: webhookRelayUrl.trim() || null,
        webhook_relay_device_id: webhookRelayDeviceId.trim() || null,
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

  async function pairRelay() {
    if (!host.pairWebhookRelay) return;
    setRelayPairingBusy(true);
    setNativeFailure(null);
    setNativeMessage(null);
    try {
      const result = await host.pairWebhookRelay(
        webhookRelayUrl.trim(),
        relayPairingCode.trim(),
        webhookRelayDeviceId.trim(),
      );
      await updateSettings.mutateAsync({
        webhook_relay_url: webhookRelayUrl.trim(),
        webhook_relay_device_id: webhookRelayDeviceId.trim(),
      });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus }),
        queryClient.invalidateQueries({ queryKey: queryKeys.onboarding }),
      ]);
      setRelayPairingCode("");
      setNativeMessage(text(
        `Webhook Relay 已安全配对，授权仓库：${result.repositories.join("、")}。后端已重新加载设备 Token，连接状态已刷新。`,
        `Webhook Relay paired securely for: ${result.repositories.join(", ")}. The backend reloaded the device token and refreshed the connection state.`,
      ));
    } catch (error) {
      setNativeFailure(errorMessage(error));
    } finally {
      setRelayPairingBusy(false);
    }
  }

  function exportSettings() {
    const blob = new Blob([JSON.stringify(settings, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "tracegate-settings.json";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function importSettings(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setNativeFailure(null);
    try {
      const parsed = settingsUpdateSchema.parse(JSON.parse(await file.text()));
      await updateSettings.mutateAsync(parsed);
      setNativeMessage(text("非敏感设置已从 JSON 导入并由后端验证保存。", "Non-secret settings were imported from JSON and validated by the backend."));
    } catch (error) {
      setNativeFailure(errorMessage(error));
    }
  }

  return (
    <form id="settings-general" className="settings-panel settings-anchor" onSubmit={submit}>
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

      <div id="settings-model" className="settings-subsection settings-anchor">
        <div>
          <span className="eyebrow">MODEL PROVIDER</span>
          <h3>{text("模型运行参数", "Model runtime")}</h3>
          <p className="field-note">{text("这些参数会直接用于下一次真实模型请求。密钥仍仅存放在系统凭据库中。", "These values are passed directly to the next real model request. The secret remains only in the system credential store.")}</p>
        </div>
        <div className="form-grid">
          <label className="field">
            <span>{text("模型 Provider", "Model provider")}</span>
            <input value={modelProvider} placeholder="deepseek" onChange={(event) => setModelProvider(event.target.value)} />
          </label>
          <label className="field">
            <span>Base URL</span>
            <input type="url" value={modelBaseUrl} placeholder="https://api.deepseek.com" onChange={(event) => setModelBaseUrl(event.target.value)} />
          </label>
          <label className="field">
            <span>Model Name</span>
            <input value={modelName} placeholder="deepseek-chat" onChange={(event) => setModelName(event.target.value)} />
          </label>
          <label className="field">
            <span>Temperature</span>
            <input type="number" min="0" max="2" step="0.1" value={modelTemperature} onChange={(event) => setModelTemperature(event.target.valueAsNumber)} />
          </label>
          <label className="field">
            <span>{text("最大输出 Token", "Max output tokens")}</span>
            <input type="number" min="256" max="32768" step="256" value={modelMaxOutputTokens} onChange={(event) => setModelMaxOutputTokens(event.target.valueAsNumber)} />
          </label>
          <label className="field">
            <span>{text("超时（秒）", "Timeout (seconds)")}</span>
            <input type="number" min="5" max="300" value={modelTimeoutSeconds} onChange={(event) => setModelTimeoutSeconds(event.target.valueAsNumber)} />
          </label>
          <label className="field">
            <span>{text("有限重试次数", "Bounded retries")}</span>
            <input type="number" min="0" max="3" value={modelMaxRetries} onChange={(event) => setModelMaxRetries(event.target.valueAsNumber)} />
          </label>
        </div>
        <label className="switch-row">
          <span>
            <strong>{text("原生结构化输出", "Native structured output")}</strong>
            <small>{text("仅当 Provider 原生支持 JSON Schema 时开启；关闭时明确使用 JSON 兼容模式。", "Enable only when the provider natively supports JSON Schema; when off, TraceGate explicitly uses JSON compatibility mode.")}</small>
          </span>
          <input type="checkbox" checked={modelNativeStructuredOutput} onChange={(event) => setModelNativeStructuredOutput(event.target.checked)} />
        </label>
        <label className="switch-row">
          <span><strong>{text("流式结构化响应", "Stream structured responses")}</strong><small>{text("启用后通过真实 SSE 增量接收模型输出，完成后再做同一份 Pydantic Schema 校验；错误不会回退到非模型结果。", "When enabled, model output is received over real SSE and then validated against the same Pydantic schema. Failures never fall back to non-model results.")}</small></span>
          <input type="checkbox" checked={modelStreamingEnabled} onChange={(event) => setModelStreamingEnabled(event.target.checked)} />
        </label>
        <label className="switch-row">
          <span><strong>{text("Provider 原生 Tool Calling 能力", "Provider-native tool calling capability")}</strong><small>{modelNativeToolCalling ? text("Provider 适配器会使用原生 function tools；生产工作流仍由本地 Registry 执行权限检查。", "The provider adapter uses native function tools; the production workflow still enforces permissions in the local Registry.") : text("明确使用 JSON 兼容选择模式，不会显示为原生 Tool Calling；生产工作流仍由本地 Registry 执行。", "Explicit JSON compatibility selection mode; it is never labelled native tool calling. The local Registry still executes production tools.")}</small></span>
          <input type="checkbox" checked={modelNativeToolCalling} onChange={(event) => setModelNativeToolCalling(event.target.checked)} />
        </label>
        <div className="form-grid">
          <label className="field"><span>{text("发送给模型的代码范围", "Code scope sent to the model")}</span><select value={modelContextScope} onChange={(event) => setModelContextScope(event.target.value as Settings["model_context_scope"])}><option value="changed_files">{text("仅 PR 变更文件中的提交绑定片段（推荐）", "Commit-bound snippets from changed PR files only (recommended)")}</option><option value="retrieved_context">{text("变更文件与检索命中的提交绑定上下文", "Changed files plus commit-bound retrieved context")}</option></select><small>{text("敏感文件规则在两种模式下都先执行；更改范围会使分析去重键失效并生成新的 Run。", "Sensitive-file rules run first in both modes. Changing scope invalidates the analysis deduplication key and creates a new Run.")}</small></label>
          <label className="field"><span>{text("输入价格 / 百万 Token（USD）", "Input price / 1M tokens (USD)")}</span><input type="number" min="0" max="10000" step="0.01" value={modelInputCostPerMillion} onChange={(event) => setModelInputCostPerMillion(event.target.valueAsNumber)} /></label>
          <label className="field"><span>{text("输出价格 / 百万 Token（USD）", "Output price / 1M tokens (USD)")}</span><input type="number" min="0" max="10000" step="0.01" value={modelOutputCostPerMillion} onChange={(event) => setModelOutputCostPerMillion(event.target.valueAsNumber)} /></label>
        </div>
      </div>

      <div id="settings-automation" className="settings-anchor settings-automation-section">
      <label className="field">
        <span>{text("GitHub 轮询频率（秒）", "GitHub polling interval (seconds)")}</span>
        <input type="number" min="30" max="3600" step="30" value={githubPollIntervalSeconds} onChange={(event) => setGithubPollIntervalSeconds(event.target.valueAsNumber)} />
        <small>{text("保存后后台监控器会立即唤醒，并在下一轮使用新的间隔。", "Saving wakes the background monitor immediately; the next wait uses this interval.")}</small>
      </label>

      <div className="settings-subsection">
        <div>
          <span className="eyebrow">OPTIONAL WEBHOOK RELAY</span>
          <h3>{text("实时事件配对", "Realtime event pairing")}</h3>
          <p className="field-note">{text("Relay 只接收配对时授权的仓库事件；设备 Token 直接写入系统凭据库，不返回 WebView。未配置时继续使用 GitHub ETag 轮询。", "The Relay receives events only for repositories scoped at pairing. Its device token is written directly to the system credential store and never returned to the WebView. GitHub ETag polling remains the fallback when unconfigured.")}</p>
        </div>
        <div className="form-grid">
          <label className="field">
            <span>Relay URL</span>
            <input type="url" value={webhookRelayUrl} placeholder="https://relay.example.com" onChange={(event) => setWebhookRelayUrl(event.target.value)} />
          </label>
          <label className="field">
            <span>{text("设备 ID", "Device ID")}</span>
            <input value={webhookRelayDeviceId} placeholder="tracegate-mac-1" onChange={(event) => setWebhookRelayDeviceId(event.target.value)} />
          </label>
          {host.pairWebhookRelay ? <label className="field">
            <span>{text("一次性配对码", "One-time pairing code")}</span>
            <input type="password" autoComplete="one-time-code" value={relayPairingCode} onChange={(event) => setRelayPairingCode(event.target.value)} />
          </label> : null}
        </div>
        {host.pairWebhookRelay ? <button className="button button-secondary" type="button" disabled={relayPairingBusy || webhookRelayUrl.trim().length < 8 || webhookRelayDeviceId.trim().length < 1 || relayPairingCode.trim().length < 20} onClick={() => void pairRelay()}>{relayPairingBusy ? text("配对中…", "Pairing…") : text("安全配对 Relay", "Pair Relay securely")}</button> : <p className="field-note">{text("浏览器宿主只保存非敏感 URL 与设备 ID；设备 Token 必须通过后端环境变量提供。", "The browser host saves only the non-secret URL and device ID; provide the device token through the backend environment.")}</p>}
      </div>

      <div className="settings-subsection">
        <div>
          <span className="eyebrow">AUTOMATIC ANALYSIS</span>
          <h3>{text("自动分析规则", "Automatic analysis rules")}</h3>
          <p className="field-note">{text("后台同步后仅对本地索引已精确匹配 PR Head SHA 的记录入队；缺少模型或匹配索引会显示明确原因。", "After synchronization, only PRs whose local index exactly matches the Head SHA are queued. Missing models or indexes are reported explicitly.")}</p>
        </div>
        <label className="switch-row"><span><strong>{text("启用自动分析", "Enable automatic analysis")}</strong><small>{text("默认关闭；相同 Head SHA、索引、Prompt 和模型不会重复入队。", "Off by default; the same Head SHA, index, prompt, and model are never queued twice.")}</small></span><input type="checkbox" checked={automaticAnalysisEnabled} onChange={(event) => setAutomaticAnalysisEnabled(event.target.checked)} /></label>
        <label className="switch-row"><span><strong>{text("包含 Draft PR", "Include draft PRs")}</strong><small>{text("关闭时只处理非草稿的开放 PR。", "When off, only non-draft open PRs are eligible.")}</small></span><input type="checkbox" checked={automaticAnalysisIncludeDrafts} disabled={!automaticAnalysisEnabled} onChange={(event) => setAutomaticAnalysisIncludeDrafts(event.target.checked)} /></label>
        <label className="switch-row"><span><strong>{text("要求 Checks 通过", "Require successful Checks")}</strong><small>{text("开启后，只有聚合 Check Run 状态为 success 的 PR 才会入队。", "When enabled, only PRs with an aggregate Check Run status of success are queued.")}</small></span><input type="checkbox" checked={automaticAnalysisRequireChecksSuccess} disabled={!automaticAnalysisEnabled} onChange={(event) => setAutomaticAnalysisRequireChecksSuccess(event.target.checked)} /></label>
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

      <label className="switch-row">
        <span>
          <strong>{text("系统通知", "System notifications")}</strong>
          <small>{host.showReviewNotification ? text("启用新 PR、提交、分析状态和高风险 Finding 的原生通知。", "Enable native notifications for new PRs, commits, analysis state, and high-risk Findings.") : text("当前宿主不提供系统通知；设置会保存但不会声称已经展示通知。", "The current host has no system notifications; the preference is saved without claiming delivery.")}</small>
        </span>
        <input type="checkbox" checked={notificationsEnabled} onChange={(event) => setNotificationsEnabled(event.target.checked)} />
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
      </div>

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
        <span>{text("数据导入导出", "Data import/export")}</span>
        <div className="action-row compact">
          <button className="button button-secondary button-small" type="button" onClick={exportSettings}>{text("导出非敏感设置", "Export non-secret settings")}</button>
          <label className="button button-secondary button-small file-button">{text("导入设置 JSON", "Import settings JSON")}<input type="file" accept="application/json,.json" onChange={(event) => void importSettings(event)} /></label>
        </div>
      </div>

      <div className="provider-summary">
        <span>{text("模型配置", "Model configuration")}</span>
        <strong>{modelProvider && modelName ? `${modelProvider} / ${modelName}` : text("模型尚未配置", "Model not configured")}</strong>
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
