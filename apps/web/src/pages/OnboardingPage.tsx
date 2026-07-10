import { useEffect, useState } from "react";
import {
  isComponentReady,
  type ConnectionComponent,
  type ConnectionTestResponse,
  type CredentialKind,
  type OnboardingState,
  type OnboardingStep,
  type Settings,
} from "@tracegate/shared-types";

import {
  useCreateRepository,
  useOnboarding,
  useSettings,
  useUpdateOnboarding,
  useUpdateSettings,
} from "../api/queries";
import { useApiClient } from "../api/clientContext";
import { ErrorState, LoadingState } from "../components/RequestState";
import { StatusCard } from "../components/StatusCard";
import { errorMessage } from "../lib/errors";
import { useI18n } from "../i18n";
import type { HostBridge } from "../host/hostBridge";

const steps: readonly { id: OnboardingStep; zh: string; en: string }[] = [
  { id: "welcome", zh: "欢迎", en: "Welcome" },
  { id: "appearance", zh: "外观", en: "Appearance" },
  { id: "github", zh: "GitHub", en: "GitHub" },
  { id: "model", zh: "模型", en: "Model" },
  { id: "repository", zh: "仓库", en: "Repository" },
  { id: "background", zh: "后台", en: "Background" },
  { id: "complete", zh: "完成", en: "Complete" },
];

export function OnboardingPage({ host }: { host: HostBridge }) {
  const { text } = useI18n();
  const onboardingQuery = useOnboarding();
  const settingsQuery = useSettings();

  if (onboardingQuery.isPending || settingsQuery.isPending) {
    return <LoadingState label={text("正在读取首次引导进度…", "Reading onboarding progress…")} />;
  }
  if (onboardingQuery.isError || settingsQuery.isError) {
    const failure = onboardingQuery.error ?? settingsQuery.error;
    return (
      <ErrorState
        title={text("无法读取首次引导", "Unable to read onboarding")}
        message={errorMessage(failure)}
        onRetry={() => {
          void onboardingQuery.refetch();
          void settingsQuery.refetch();
        }}
      />
    );
  }

  return (
    <OnboardingFlow
      key={`${onboardingQuery.data.updated_at}:${onboardingQuery.data.current_step}`}
      onboarding={onboardingQuery.data}
      settings={settingsQuery.data}
      host={host}
    />
  );
}

function OnboardingFlow({ onboarding, settings, host }: { onboarding: OnboardingState; settings: Settings; host: HostBridge }) {
  const { text } = useI18n();
  const client = useApiClient();
  const updateOnboarding = useUpdateOnboarding();
  const updateSettings = useUpdateSettings();
  const createRepository = useCreateRepository();
  const [backgroundMonitoring, setBackgroundMonitoring] = useState(onboarding.background_monitoring);
  const [launchAtStartup, setLaunchAtStartup] = useState(onboarding.launch_at_startup);
  const [theme, setTheme] = useState(settings.theme);
  const [language, setLanguage] = useState(settings.language);
  const [githubToken, setGithubToken] = useState("");
  const [modelKey, setModelKey] = useState("");
  const [modelProvider, setModelProvider] = useState(settings.model_provider ?? "deepseek");
  const [modelBaseUrl, setModelBaseUrl] = useState(settings.model_base_url ?? "");
  const [modelName, setModelName] = useState(settings.model_name ?? "");
  const [modelContextScope, setModelContextScope] = useState(settings.model_context_scope);
  const [repositoryName, setRepositoryName] = useState("");
  const [repositoryPath, setRepositoryPath] = useState("");
  const [connectionTests, setConnectionTests] = useState<Partial<Record<ConnectionComponent, ConnectionTestResponse>>>({});
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [nativeMessage, setNativeMessage] = useState<string | null>(null);
  const [nativeError, setNativeError] = useState<string | null>(null);
  const currentIndex = Math.max(0, steps.findIndex((step) => step.id === onboarding.current_step));
  const nextStep = steps[currentIndex + 1]?.id ?? "complete";
  const githubReady = isComponentReady(onboarding.github);
  const modelReady = isComponentReady(onboarding.model);

  useEffect(() => {
    const readAutostart = host.getAutostartEnabled?.bind(host);
    if (!readAutostart) return;
    let active = true;
    void readAutostart()
      .then((enabled) => {
        if (active) setLaunchAtStartup(enabled);
      })
      .catch((error: unknown) => {
        if (active) setNativeError(errorMessage(error));
      });
    return () => {
      active = false;
    };
  }, [host]);

  async function storeSecret(kind: CredentialKind, value: string) {
    if (!host.storeCredential) {
      setNativeError(text("浏览器模式请通过后端环境变量配置凭据。", "In browser mode, configure credentials through backend environment variables."));
      return;
    }
    setBusyAction(`credential:${kind}`);
    setNativeError(null);
    setNativeMessage(null);
    try {
      const status = await host.storeCredential(kind, value);
      if (kind === "github") setGithubToken("");
      else setModelKey("");
      setNativeMessage(text(`凭据已写入 ${status.storage}。请重启 TraceGate，让 Sidecar 读取新凭据后再执行连接测试。`, `Credential saved to ${status.storage}. Restart TraceGate so the Sidecar can read it before testing the connection.`));
    } catch (error) {
      setNativeError(errorMessage(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function runConnectionTest(component: ConnectionComponent): Promise<ConnectionTestResponse | null> {
    setBusyAction(`test:${component}`);
    setNativeError(null);
    try {
      const result = await client.testConnection(component);
      setConnectionTests((current) => ({ ...current, [component]: result }));
      return result;
    } catch (error) {
      setConnectionTests((current) => {
        return Object.fromEntries(
          Object.entries(current).filter(([key]) => key !== component),
        ) as Partial<Record<ConnectionComponent, ConnectionTestResponse>>;
      });
      setNativeError(errorMessage(error));
      return null;
    } finally {
      setBusyAction(null);
    }
  }

  async function addRepository() {
    setNativeError(null);
    try {
      await createRepository.mutateAsync({
        full_name: repositoryName.trim(),
        local_path: repositoryPath.trim() || null,
        monitoring_enabled: backgroundMonitoring,
      });
      setNativeMessage(text("真实仓库记录已由后端创建。", "The real repository record was created by the backend."));
    } catch (error) {
      setNativeError(errorMessage(error));
    }
  }

  async function advance() {
    const isCompleting = onboarding.current_step === "complete";
    setNativeError(null);
    setNativeMessage(null);
    try {
      if (onboarding.current_step === "appearance") {
        await updateSettings.mutateAsync({ theme, language });
      }
      if (onboarding.current_step === "model") {
        await updateSettings.mutateAsync({
          model_provider: modelProvider.trim() || null,
          model_base_url: modelBaseUrl.trim() || null,
          model_name: modelName.trim() || null,
          model_context_scope: modelContextScope,
        });
      }
      let confirmedAutostart = launchAtStartup;
      if (onboarding.current_step === "background" || isCompleting) {
        confirmedAutostart = host.setAutostartEnabled
          ? await host.setAutostartEnabled(launchAtStartup)
          : onboarding.launch_at_startup;
        setLaunchAtStartup(confirmedAutostart);
      }
      if (isCompleting) {
        if (!await runConnectionTest("backend")) return;
        if (!await runConnectionTest("github")) return;
        if (modelReady && !await runConnectionTest("model")) return;
      }
      await updateOnboarding.mutateAsync({
        completed: isCompleting,
        current_step: isCompleting ? "complete" : nextStep,
        background_monitoring: backgroundMonitoring,
        launch_at_startup: confirmedAutostart,
      });
    } catch (error) {
      setNativeError(errorMessage(error));
    }
  }

  const blockedReason =
    onboarding.current_step === "github" && !githubReady
      ? text("GitHub 凭据尚未由当前 Sidecar 读取。保存凭据并重启 TraceGate 后继续。", "The current Sidecar has not loaded a GitHub credential. Save it and restart TraceGate before continuing.")
      : onboarding.current_step === "github" && !connectionTests.github
        ? text("请执行一次真实 GitHub 连接测试。", "Run a real GitHub connection test.")
        : onboarding.current_step === "model" && modelReady && modelName.trim() && !connectionTests.model
          ? text("已配置模型时，请先执行真实连接测试；也可以清空模型名称后跳过。", "When a model is configured, run a real connection test first; alternatively clear the model name to skip it.")
          : onboarding.current_step === "repository" && !onboarding.repository_added
            ? text("请先创建一个真实仓库记录。", "Create a real repository record first.")
            : null;

  const actionLabel =
    onboarding.current_step === "model" && !modelReady
      ? text("保存配置或跳过", "Save configuration or skip")
      : onboarding.current_step === "complete"
        ? onboarding.completed
          ? text("引导已完成", "Onboarding complete")
          : text("运行最终测试并完成", "Run final tests and complete")
        : text("保存并继续", "Save and continue");

  return (
    <div className="onboarding-layout">
      <aside className="onboarding-steps" aria-label={text("首次引导步骤", "Onboarding steps")}>
        <span className="eyebrow">GET STARTED</span>
        <h2>{text("首次引导", "Onboarding")}</h2>
        <ol>{steps.map((step, index) => {
          const state = index < currentIndex ? "done" : index === currentIndex ? "current" : "upcoming";
          return <li key={step.id} className={`step-${state}`} aria-current={state === "current" ? "step" : undefined}><span>{index < currentIndex ? "✓" : index + 1}</span>{text(step.zh, step.en)}</li>;
        })}</ol>
      </aside>

      <section className="onboarding-content">
        <span className="eyebrow">{text("当前步骤", "Current step")} · {steps[currentIndex] ? text(steps[currentIndex].zh, steps[currentIndex].en) : ""}</span>
        <h2>{stepTitle(onboarding.current_step, text)}</h2>
        <p>{stepDescription(onboarding.current_step, text)}</p>

        <StepContent
          step={onboarding.current_step}
          text={text}
          host={host}
          onboarding={onboarding}
          settings={{ theme, language, modelProvider, modelBaseUrl, modelName, modelContextScope }}
          setters={{ setTheme, setLanguage, setModelProvider, setModelBaseUrl, setModelName, setModelContextScope }}
          credentials={{ githubToken, modelKey, setGithubToken, setModelKey, storeSecret }}
          repository={{ repositoryName, repositoryPath, setRepositoryName, setRepositoryPath, addRepository, pending: createRepository.isPending }}
          preferences={{ backgroundMonitoring, launchAtStartup, setBackgroundMonitoring, setLaunchAtStartup }}
          tests={{ values: connectionTests, run: runConnectionTest, busyAction }}
        />

        {blockedReason ? <p className="blocker-note" role="status">{blockedReason}</p> : null}
        {updateOnboarding.isError || updateSettings.isError || createRepository.isError ? <p className="inline-error" role="alert">{text("保存失败", "Save failed")}: {errorMessage(updateOnboarding.error ?? updateSettings.error ?? createRepository.error)}</p> : null}
        {nativeMessage ? <p className="inline-success" role="status">{nativeMessage}</p> : null}
        {nativeError ? <p className="inline-error" role="alert">{text("操作失败", "Operation failed")}: {nativeError}</p> : null}

        <div className="onboarding-actions">
          <span>{onboarding.repository_added ? text("已添加真实仓库", "Real repository added") : text("真实仓库尚未添加", "No real repository added")}</span>
          <button type="button" className="button button-primary" disabled={blockedReason !== null || updateOnboarding.isPending || updateSettings.isPending || busyAction !== null || onboarding.completed} onClick={() => void advance()}>{updateOnboarding.isPending || updateSettings.isPending || busyAction !== null ? text("处理中…", "Working…") : actionLabel}</button>
        </div>
      </section>
    </div>
  );
}

type Translate = (zh: string, en: string) => string;

interface StepContentProps {
  step: OnboardingStep;
  text: Translate;
  host: HostBridge;
  onboarding: OnboardingState;
  settings: { theme: Settings["theme"]; language: Settings["language"]; modelProvider: string; modelBaseUrl: string; modelName: string; modelContextScope: Settings["model_context_scope"] };
  setters: { setTheme: (value: Settings["theme"]) => void; setLanguage: (value: Settings["language"]) => void; setModelProvider: (value: string) => void; setModelBaseUrl: (value: string) => void; setModelName: (value: string) => void; setModelContextScope: (value: Settings["model_context_scope"]) => void };
  credentials: { githubToken: string; modelKey: string; setGithubToken: (value: string) => void; setModelKey: (value: string) => void; storeSecret: (kind: CredentialKind, value: string) => Promise<void> };
  repository: { repositoryName: string; repositoryPath: string; setRepositoryName: (value: string) => void; setRepositoryPath: (value: string) => void; addRepository: () => Promise<void>; pending: boolean };
  preferences: { backgroundMonitoring: boolean; launchAtStartup: boolean; setBackgroundMonitoring: (value: boolean) => void; setLaunchAtStartup: (value: boolean) => void };
  tests: { values: Partial<Record<ConnectionComponent, ConnectionTestResponse>>; run: (component: ConnectionComponent) => Promise<ConnectionTestResponse | null>; busyAction: string | null };
}

function StepContent({ step, text, host, onboarding, settings, setters, credentials, repository, preferences, tests }: StepContentProps) {
  if (step === "welcome") return <div className="onboarding-capabilities"><article><strong>{text("真实 PR 证据", "Real PR evidence")}</strong><p>{text("同步 GitHub 元数据、Diff、Checks 与提交 SHA。", "Synchronize GitHub metadata, diffs, Checks, and commit SHAs.")}</p></article><article><strong>{text("可追溯 Agent", "Traceable agent")}</strong><p>{text("每个节点、工具、Finding 和 Evidence 都持久化。", "Every node, tool, Finding, and Evidence item is persisted.")}</p></article><article><strong>{text("本地优先", "Local first")}</strong><p>{text("索引和数据库默认留在本机；只有选中的上下文发送给模型。", "Indexes and the database stay local by default; only selected context is sent to the model.")}</p></article></div>;
  if (step === "appearance") return <div className="form-grid"><label className="field"><span>{text("主题", "Theme")}</span><select value={settings.theme} onChange={(event) => setters.setTheme(event.target.value as Settings["theme"])}><option value="system">{text("跟随系统", "System")}</option><option value="light">{text("浅色", "Light")}</option><option value="dark">{text("深色", "Dark")}</option></select></label><label className="field"><span>{text("语言", "Language")}</span><select value={settings.language} onChange={(event) => setters.setLanguage(event.target.value as Settings["language"])}><option value="zh-CN">简体中文</option><option value="en-US">English</option></select></label></div>;
  if (step === "github") return <div className="setup-stack"><StatusCard eyebrow="GITHUB" title={text("当前连接", "Current connection")} status={onboarding.github} /><label className="field"><span>Fine-grained PAT</span><input type="password" autoComplete="new-password" value={credentials.githubToken} onChange={(event) => credentials.setGithubToken(event.target.value)} placeholder={text("只写入系统凭据库", "Stored only in the system credential store")} /></label><div className="action-row"><button className="button button-secondary" type="button" disabled={!host.storeCredential || credentials.githubToken.length < 20 || tests.busyAction !== null} onClick={() => void credentials.storeSecret("github", credentials.githubToken)}>{text("安全保存", "Save securely")}</button><button className="button button-primary" type="button" disabled={!isComponentReady(onboarding.github) || tests.busyAction !== null} onClick={() => void tests.run("github")}>{text("测试 GitHub 连接", "Test GitHub connection")}</button></div><ConnectionResult value={tests.values.github} /></div>;
  if (step === "model") return <div className="setup-stack"><StatusCard eyebrow="OPTIONAL" title={text("语义模型", "Semantic model")} status={onboarding.model} /><div className="form-grid"><label className="field"><span>Provider</span><input value={settings.modelProvider} onChange={(event) => setters.setModelProvider(event.target.value)} placeholder="deepseek" /></label><label className="field"><span>Base URL</span><input type="url" value={settings.modelBaseUrl} onChange={(event) => setters.setModelBaseUrl(event.target.value)} placeholder="https://api.deepseek.com" /></label><label className="field"><span>Model Name</span><input value={settings.modelName} onChange={(event) => setters.setModelName(event.target.value)} placeholder="deepseek-chat" /></label><label className="field"><span>API Key</span><input type="password" autoComplete="new-password" value={credentials.modelKey} onChange={(event) => credentials.setModelKey(event.target.value)} placeholder={text("只写入系统凭据库", "Stored only in the system credential store")} /></label><label className="field"><span>{text("发送给模型的代码范围", "Code scope sent to the model")}</span><select value={settings.modelContextScope} onChange={(event) => setters.setModelContextScope(event.target.value as Settings["model_context_scope"])}><option value="changed_files">{text("仅 PR 变更文件中的提交绑定片段（推荐）", "Commit-bound snippets from changed PR files only (recommended)")}</option><option value="retrieved_context">{text("变更文件与检索命中的提交绑定上下文", "Changed files plus commit-bound retrieved context")}</option></select></label></div><p className="privacy-note">{settings.modelContextScope === "changed_files" ? text("模型只接收当前 PR 变更文件中、与 Head SHA 索引绑定的片段。", "The model receives only snippets from changed PR files bound to the Head SHA index.") : text("模型还可接收检索命中的提交绑定代码/符号上下文。", "The model may also receive commit-bound code and symbol context returned by retrieval.")} {text("敏感文件规则始终先于模型调用。", "Sensitive-file rules always run before model calls.")}</p><div className="action-row"><button className="button button-secondary" type="button" disabled={!host.storeCredential || credentials.modelKey.length < 20 || tests.busyAction !== null} onClick={() => void credentials.storeSecret("model", credentials.modelKey)}>{text("安全保存密钥", "Save key securely")}</button><button className="button button-primary" type="button" disabled={!isComponentReady(onboarding.model) || tests.busyAction !== null} onClick={() => void tests.run("model")}>{text("测试真实模型", "Test real model")}</button></div><ConnectionResult value={tests.values.model} /></div>;
  if (step === "repository") return <div className="setup-stack"><div className="form-grid"><label className="field"><span>{text("GitHub 仓库", "GitHub repository")}</span><input value={repository.repositoryName} onChange={(event) => repository.setRepositoryName(event.target.value)} placeholder="owner/repository" /></label><label className="field"><span>{text("本地工作区（可选）", "Local workspace (optional)")}</span><input value={repository.repositoryPath} onChange={(event) => repository.setRepositoryPath(event.target.value)} placeholder="/absolute/path/to/repository" /></label></div><button className="button button-primary" type="button" disabled={repository.pending || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository.repositoryName.trim())} onClick={() => void repository.addRepository()}>{repository.pending ? text("添加中…", "Adding…") : text("添加真实仓库", "Add real repository")}</button></div>;
  if (step === "background") return <div className="preference-stack"><label className="switch-row"><span><strong>{text("后台监控", "Background monitoring")}</strong><small>{text("按设置的间隔使用 ETag 轮询已启用仓库。", "Poll enabled repositories with ETags at the configured interval.")}</small></span><input type="checkbox" checked={preferences.backgroundMonitoring} onChange={(event) => preferences.setBackgroundMonitoring(event.target.checked)} /></label><label className="switch-row"><span><strong>{text("开机启动", "Launch at startup")}</strong><small>{host.setAutostartEnabled ? text("由操作系统原生启动服务管理。", "Managed by the native operating-system startup service.") : text("浏览器宿主不支持此能力。", "This capability is unavailable in the browser host.")}</small></span><input type="checkbox" checked={preferences.launchAtStartup} disabled={!host.setAutostartEnabled} onChange={(event) => preferences.setLaunchAtStartup(event.target.checked)} /></label></div>;
  return <div className="setup-stack"><div className="status-grid status-grid-two"><StatusCard eyebrow="GITHUB" title="GitHub" status={onboarding.github} /><StatusCard eyebrow="MODEL" title={text("语义模型（可选）", "Semantic model (optional)")} status={onboarding.model} /></div><div className="connection-test-grid">{(["backend", "github", ...(isComponentReady(onboarding.model) ? ["model"] : [])] as ConnectionComponent[]).map((component) => <div key={component}><button className="button button-secondary" type="button" disabled={tests.busyAction !== null} onClick={() => void tests.run(component)}>{text(`测试 ${component}`, `Test ${component}`)}</button><ConnectionResult value={tests.values[component]} /></div>)}</div></div>;
}

function ConnectionResult({ value }: { value: ConnectionTestResponse | undefined }) {
  if (!value) return null;
  return <p className="inline-success" role="status"><strong>{value.message}</strong>{value.detail ? ` ${value.detail}` : ""} · {value.latency_ms} ms</p>;
}

function stepTitle(step: OnboardingStep, text: Translate): string {
  const titles: Record<OnboardingStep, [string, string]> = { welcome: ["欢迎使用 TraceGate Studio", "Welcome to TraceGate Studio"], appearance: ["选择工作台偏好", "Choose workspace preferences"], github: ["连接真实 GitHub 数据源", "Connect a real GitHub source"], model: ["配置语义分析模型", "Configure a semantic model"], repository: ["添加第一个真实仓库", "Add the first real repository"], background: ["决定是否持续监控", "Choose continuous monitoring"], complete: ["运行连接测试并完成", "Run connection tests and finish"] };
  return text(...titles[step]);
}

function stepDescription(step: OnboardingStep, text: Translate): string {
  const descriptions: Record<OnboardingStep, [string, string]> = { welcome: ["所有分析都必须关联真实仓库、提交和 Evidence。", "Every analysis must reference a real repository, commit, and Evidence."], appearance: ["主题和语言保存在本地数据库，可随时修改。", "Theme and language are stored locally and can be changed later."], github: ["凭据进入系统安全存储；连接测试调用真实 GitHub API。", "Credentials go to secure system storage; the test calls the real GitHub API."], model: ["可以跳过；未配置时分析会明确失败，不生成替代报告。", "You may skip this; without a model, analysis fails explicitly and never creates a substitute report."], repository: ["记录 GitHub 身份；提供本地路径后可建立真实索引与 Diff。", "Record the GitHub identity; a local path enables real indexing and diffs."], background: ["后台监控和开机启动均为主动选择，默认关闭。", "Background monitoring and autostart are opt-in and off by default."], complete: ["完成前重新验证本地后端、GitHub，以及已配置的模型。", "Before completion, revalidate the local backend, GitHub, and any configured model."] };
  return text(...descriptions[step]);
}
