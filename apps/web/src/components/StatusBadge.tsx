import type { ComponentState, ComponentStatus } from "@tracegate/shared-types";

const stateLabels: Record<ComponentState, string> = {
  ready: "正常",
  not_configured: "未配置",
  error: "错误",
  unavailable: "不可用",
};

interface StatusBadgeProps {
  status: ComponentStatus;
  compact?: boolean;
}

export function StatusBadge({ status, compact = false }: StatusBadgeProps) {
  return (
    <span
      className={`status-badge status-${status.state}${compact ? " status-compact" : ""}`}
      aria-label={`${stateLabels[status.state]}：${status.message}`}
      title={status.detail ?? status.message}
    >
      <span className="status-dot" aria-hidden="true" />
      {stateLabels[status.state]}
    </span>
  );
}

export function PendingStatusBadge() {
  return (
    <span className="status-badge status-pending" aria-label="正在检查状态">
      <span className="status-dot" aria-hidden="true" />
      检查中
    </span>
  );
}
