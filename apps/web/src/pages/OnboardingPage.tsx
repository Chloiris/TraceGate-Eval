import { useState } from "react";
import {
  isComponentReady,
  type OnboardingState,
  type OnboardingStep,
} from "@tracegate/shared-types";

import { useOnboarding, useUpdateOnboarding } from "../api/queries";
import { ErrorState, LoadingState } from "../components/RequestState";
import { StatusCard } from "../components/StatusCard";
import { errorMessage } from "../lib/errors";

const steps: readonly { id: OnboardingStep; label: string }[] = [
  { id: "welcome", label: "欢迎" },
  { id: "appearance", label: "外观" },
  { id: "github", label: "GitHub" },
  { id: "model", label: "模型" },
  { id: "repository", label: "仓库" },
  { id: "background", label: "后台" },
  { id: "complete", label: "完成" },
];

export function OnboardingPage() {
  const onboardingQuery = useOnboarding();

  if (onboardingQuery.isPending) {
    return <LoadingState label="正在读取首次引导进度…" />;
  }
  if (onboardingQuery.isError) {
    return (
      <ErrorState
        title="无法读取首次引导"
        message={errorMessage(onboardingQuery.error)}
        onRetry={() => void onboardingQuery.refetch()}
      />
    );
  }

  return <OnboardingFlow key={onboardingQuery.data.updated_at} onboarding={onboardingQuery.data} />;
}

function OnboardingFlow({ onboarding }: { onboarding: OnboardingState }) {
  const updateOnboarding = useUpdateOnboarding();
  const [backgroundMonitoring, setBackgroundMonitoring] = useState(onboarding.background_monitoring);
  const [launchAtStartup, setLaunchAtStartup] = useState(onboarding.launch_at_startup);
  const currentIndex = Math.max(0, steps.findIndex((step) => step.id === onboarding.current_step));
  const nextStep = steps[currentIndex + 1]?.id ?? "complete";

  const githubReady = isComponentReady(onboarding.github);
  const modelReady = isComponentReady(onboarding.model);
  const blockedReason =
    onboarding.current_step === "github" && !githubReady
      ? "请先通过后端安全凭据流程连接 GitHub；本页面不会把 Token 写入普通设置。"
      : onboarding.current_step === "repository" && !onboarding.repository_added
        ? "尚未添加真实仓库。仓库 API 完成前，此步骤不会以演示仓库代替。"
        : null;

  const actionLabel =
    onboarding.current_step === "model" && !modelReady
      ? "暂时跳过模型配置"
      : onboarding.current_step === "complete"
        ? onboarding.completed
          ? "引导已完成"
          : "确认完成引导"
        : "保存并继续";

  function advance() {
    const isCompleting = onboarding.current_step === "complete";
    updateOnboarding.mutate({
      completed: isCompleting,
      current_step: isCompleting ? "complete" : nextStep,
      background_monitoring: backgroundMonitoring,
      launch_at_startup: launchAtStartup,
    });
  }

  return (
    <div className="onboarding-layout">
      <aside className="onboarding-steps" aria-label="首次引导步骤">
        <span className="eyebrow">GET STARTED</span>
        <h2>首次引导</h2>
        <ol>
          {steps.map((step, index) => {
            const state = index < currentIndex ? "done" : index === currentIndex ? "current" : "upcoming";
            return (
              <li key={step.id} className={`step-${state}`} aria-current={state === "current" ? "step" : undefined}>
                <span>{index < currentIndex ? "✓" : index + 1}</span>
                {step.label}
              </li>
            );
          })}
        </ol>
      </aside>

      <section className="onboarding-content">
        <span className="eyebrow">当前步骤 · {steps[currentIndex]?.label}</span>
        <h2>{stepTitle(onboarding.current_step)}</h2>
        <p>{stepDescription(onboarding.current_step)}</p>

        <div className="status-grid status-grid-two onboarding-statuses">
          <StatusCard eyebrow="REQUIRED" title="GitHub" status={onboarding.github} />
          <StatusCard eyebrow="OPTIONAL" title="语义模型" status={onboarding.model} />
        </div>

        <div className="preference-stack">
          <label className="switch-row">
            <span>
              <strong>后台监控偏好</strong>
              <small>仅保存真实偏好；监控服务不可用时，Dashboard 会明确显示。</small>
            </span>
            <input
              type="checkbox"
              checked={backgroundMonitoring}
              onChange={(event) => setBackgroundMonitoring(event.target.checked)}
            />
          </label>
          <label className="switch-row">
            <span>
              <strong>开机启动偏好</strong>
              <small>桌面原生能力接入后才会应用；浏览器模式不会声称已启用。</small>
            </span>
            <input
              type="checkbox"
              checked={launchAtStartup}
              onChange={(event) => setLaunchAtStartup(event.target.checked)}
            />
          </label>
        </div>

        {blockedReason ? <p className="blocker-note" role="status">{blockedReason}</p> : null}
        {updateOnboarding.isError ? (
          <p className="inline-error" role="alert">保存失败：{errorMessage(updateOnboarding.error)}</p>
        ) : null}

        <div className="onboarding-actions">
          <span>
            {onboarding.repository_added ? "已添加真实仓库" : "真实仓库尚未添加"}
          </span>
          <button
            type="button"
            className="button button-primary"
            disabled={blockedReason !== null || updateOnboarding.isPending || onboarding.completed}
            onClick={advance}
          >
            {updateOnboarding.isPending ? "保存中…" : actionLabel}
          </button>
        </div>
      </section>
    </div>
  );
}

function stepTitle(step: OnboardingStep): string {
  const titles: Record<OnboardingStep, string> = {
    welcome: "欢迎使用 TraceGate Studio",
    appearance: "选择你的工作台偏好",
    github: "连接真实 GitHub 数据源",
    model: "配置语义分析模型",
    repository: "添加第一个真实仓库",
    background: "决定是否持续监控",
    complete: "核对配置并完成",
  };
  return titles[step];
}

function stepDescription(step: OnboardingStep): string {
  const descriptions: Record<OnboardingStep, string> = {
    welcome: "这里不会生成示例 Finding。所有分析都必须关联真实仓库、提交和 Evidence。",
    appearance: "主题和语言偏好保存在本地后端，可随时在设置中调整。",
    github: "GitHub 尚未连接时，PR 与仓库能力保持不可用，并显示明确原因。",
    model: "允许暂时跳过；跳过后非模型功能继续可用，分析能力明确标记未配置。",
    repository: "只有后端确认真实仓库已添加后才能继续，不使用 fixture 填充页面。",
    background: "后台与开机启动均是用户主动选择，默认不会暗中开启。",
    complete: "完成状态由本地 API 持久化，不代表未验证的平台能力已经可用。",
  };
  return descriptions[step];
}
