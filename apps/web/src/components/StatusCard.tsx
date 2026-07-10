import type { ComponentStatus } from "@tracegate/shared-types";

import { StatusBadge } from "./StatusBadge";
import { useI18n } from "../i18n";

interface StatusCardProps {
  eyebrow: string;
  title: string;
  status: ComponentStatus;
}

export function StatusCard({ eyebrow, title, status }: StatusCardProps) {
  const { locale } = useI18n();
  const translatedMessage = locale === "en-US"
    ? ({ "GitHub 尚未连接": "GitHub is not connected", "模型尚未配置": "Model is not configured", "Webhook Relay 未配置": "Webhook Relay is not configured" } as Record<string, string>)[status.message] ?? status.message
    : status.message;
  return (
    <article className={`status-card status-card-${status.state}`}>
      <div className="status-card-heading">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h3>{title}</h3>
        </div>
        <StatusBadge status={status} />
      </div>
      <p>{translatedMessage}</p>
      {status.detail ? <p className="status-detail">{status.detail}</p> : null}
    </article>
  );
}
