import type { ComponentState, ComponentStatus } from "@tracegate/shared-types";
import { useI18n } from "../i18n";

const stateLabels: Record<ComponentState, { zh: string; en: string }> = {
  ready: { zh: "正常", en: "Ready" },
  not_configured: { zh: "未配置", en: "Not configured" },
  error: { zh: "错误", en: "Error" },
  unavailable: { zh: "不可用", en: "Unavailable" },
};

interface StatusBadgeProps {
  status: ComponentStatus;
  compact?: boolean;
}

export function StatusBadge({ status, compact = false }: StatusBadgeProps) {
  const { text } = useI18n();
  const label = text(stateLabels[status.state].zh, stateLabels[status.state].en);
  return (
    <span
      className={`status-badge status-${status.state}${compact ? " status-compact" : ""}`}
      aria-label={`${label}: ${status.message}`}
      title={status.detail ?? status.message}
    >
      <span className="status-dot" aria-hidden="true" />
      {label}
    </span>
  );
}

export function PendingStatusBadge() {
  const { text } = useI18n();
  return (
    <span className="status-badge status-pending" aria-label={text("正在检查状态", "Checking status")}>
      <span className="status-dot" aria-hidden="true" />
      {text("检查中", "Checking")}
    </span>
  );
}
