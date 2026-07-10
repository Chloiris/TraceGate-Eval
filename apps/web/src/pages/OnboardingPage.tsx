import { useEffect, useState } from "react";
import {
  isComponentReady,
  type OnboardingState,
  type OnboardingStep,
} from "@tracegate/shared-types";

import { useOnboarding, useUpdateOnboarding } from "../api/queries";
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

  if (onboardingQuery.isPending) {
    return <LoadingState label={text("正在读取首次引导进度…", "Reading onboarding progress…")} />;
  }
  if (onboardingQuery.isError) {
    return (
      <ErrorState
        title={text("无法读取首次引导", "Unable to read onboarding")}
        message={errorMessage(onboardingQuery.error)}
        onRetry={() => void onboardingQuery.refetch()}
      />
    );
  }

  return <OnboardingFlow key={onboardingQuery.data.updated_at} onboarding={onboardingQuery.data} host={host} />;
}

function OnboardingFlow({ onboarding, host }: { onboarding: OnboardingState; host: HostBridge }) {
  const { text } = useI18n();
  const updateOnboarding = useUpdateOnboarding();
  const [backgroundMonitoring, setBackgroundMonitoring] = useState(onboarding.background_monitoring);
  const [launchAtStartup, setLaunchAtStartup] = useState(onboarding.launch_at_startup);
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
  const blockedReason =
    onboarding.current_step === "github" && !githubReady
      ? text("请先通过后端安全凭据流程连接 GitHub；本页面不会把 Token 写入普通设置。", "Connect GitHub through the secure credential flow first; this page never writes a token to ordinary settings.")
      : onboarding.current_step === "repository" && !onboarding.repository_added
        ? text("尚未添加真实仓库。此步骤不会以演示仓库代替。", "No real repository has been added. This step never substitutes a demo repository.")
        : null;

  const actionLabel =
    onboarding.current_step === "model" && !modelReady
      ? text("暂时跳过模型配置", "Skip model configuration for now")
      : onboarding.current_step === "complete"
        ? onboarding.completed
          ? text("引导已完成", "Onboarding complete")
          : text("确认完成引导", "Complete onboarding")
        : text("保存并继续", "Save and continue");

  async function advance() {
    const isCompleting = onboarding.current_step === "complete";
    setNativeError(null);
    try {
      const confirmedAutostart = host.setAutostartEnabled
        ? await host.setAutostartEnabled(launchAtStartup)
        : onboarding.launch_at_startup;
      setLaunchAtStartup(confirmedAutostart);
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

  return (
    <div className="onboarding-layout">
      <aside className="onboarding-steps" aria-label={text("首次引导步骤", "Onboarding steps")}>
        <span className="eyebrow">GET STARTED</span>
        <h2>{text("首次引导", "Onboarding")}</h2>
        <ol>
          {steps.map((step, index) => {
            const state = index < currentIndex ? "done" : index === currentIndex ? "current" : "upcoming";
            return (
              <li key={step.id} className={`step-${state}`} aria-current={state === "current" ? "step" : undefined}>
                <span>{index < currentIndex ? "✓" : index + 1}</span>
                {text(step.zh, step.en)}
              </li>
            );
          })}
        </ol>
      </aside>

      <section className="onboarding-content">
        <span className="eyebrow">{text("当前步骤", "Current step")} · {steps[currentIndex] ? text(steps[currentIndex].zh, steps[currentIndex].en) : ""}</span>
        <h2>{stepTitle(onboarding.current_step, text)}</h2>
        <p>{stepDescription(onboarding.current_step, text)}</p>

        <div className="status-grid status-grid-two onboarding-statuses">
          <StatusCard eyebrow="REQUIRED" title="GitHub" status={onboarding.github} />
          <StatusCard eyebrow="OPTIONAL" title={text("语义模型", "Semantic model")} status={onboarding.model} />
        </div>

        <div className="preference-stack">
          <label className="switch-row">
            <span>
              <strong>{text("后台监控偏好", "Background monitoring")}</strong>
              <small>{text("仅保存真实偏好；监控服务不可用时，Dashboard 会明确显示。", "Saves the real preference; Dashboard reports when monitoring is unavailable.")}</small>
            </span>
            <input
              type="checkbox"
              checked={backgroundMonitoring}
              onChange={(event) => setBackgroundMonitoring(event.target.checked)}
            />
          </label>
          <label className="switch-row">
            <span>
              <strong>{text("开机启动偏好", "Launch at startup")}</strong>
              <small>{host.setAutostartEnabled ? text("保存时调用操作系统原生启动服务并读取确认结果。", "Saving calls the operating-system startup service and reads back the confirmed result.") : text("浏览器宿主不提供开机启动，此开关不可用。", "The browser host does not provide autostart, so this switch is unavailable.")}</small>
            </span>
            <input
              type="checkbox"
              checked={launchAtStartup}
              disabled={!host.setAutostartEnabled}
              onChange={(event) => setLaunchAtStartup(event.target.checked)}
            />
          </label>
        </div>

        {blockedReason ? <p className="blocker-note" role="status">{blockedReason}</p> : null}
        {updateOnboarding.isError ? (
          <p className="inline-error" role="alert">{text("保存失败", "Save failed")}: {errorMessage(updateOnboarding.error)}</p>
        ) : null}
        {nativeError ? <p className="inline-error" role="alert">{text("原生设置失败", "Native setting failed")}: {nativeError}</p> : null}

        <div className="onboarding-actions">
          <span>
            {onboarding.repository_added ? text("已添加真实仓库", "Real repository added") : text("真实仓库尚未添加", "No real repository added")}
          </span>
          <button
            type="button"
            className="button button-primary"
            disabled={blockedReason !== null || updateOnboarding.isPending || onboarding.completed}
            onClick={() => void advance()}
          >
            {updateOnboarding.isPending ? text("保存中…", "Saving…") : actionLabel}
          </button>
        </div>
      </section>
    </div>
  );
}

type Translate = (zh: string, en: string) => string;

function stepTitle(step: OnboardingStep, text: Translate): string {
  const titles: Record<OnboardingStep, [string, string]> = {
    welcome: ["欢迎使用 TraceGate Studio", "Welcome to TraceGate Studio"],
    appearance: ["选择你的工作台偏好", "Choose workspace preferences"],
    github: ["连接真实 GitHub 数据源", "Connect a real GitHub source"],
    model: ["配置语义分析模型", "Configure a semantic model"],
    repository: ["添加第一个真实仓库", "Add the first real repository"],
    background: ["决定是否持续监控", "Choose continuous monitoring"],
    complete: ["核对配置并完成", "Review and complete setup"],
  };
  return text(...titles[step]);
}

function stepDescription(step: OnboardingStep, text: Translate): string {
  const descriptions: Record<OnboardingStep, [string, string]> = {
    welcome: ["这里不会生成示例 Finding。所有分析都必须关联真实仓库、提交和 Evidence。", "No example Findings are generated. Every analysis must reference a real repository, commit, and Evidence."],
    appearance: ["主题和语言偏好保存在本地后端，可随时在设置中调整。", "Theme and language are stored by the local backend and can be changed in Settings."],
    github: ["GitHub 尚未连接时，PR 与仓库能力保持不可用，并显示明确原因。", "When GitHub is not connected, PR and repository capabilities stay unavailable with an explicit reason."],
    model: ["允许暂时跳过；跳过后非模型功能继续可用，分析能力明确标记未配置。", "This may be skipped; non-model features remain available and analysis is explicitly marked unconfigured."],
    repository: ["只有后端确认真实仓库已添加后才能继续，不使用 fixture 填充页面。", "Continue only after the backend confirms a real repository; fixtures never fill the product page."],
    background: ["后台与开机启动均是用户主动选择，默认不会暗中开启。", "Background monitoring and autostart are opt-in and never enabled silently."],
    complete: ["完成状态由本地 API 持久化，不代表未验证的平台能力已经可用。", "Completion is persisted by the local API and does not claim unverified platform capabilities."],
  };
  return text(...descriptions[step]);
}
