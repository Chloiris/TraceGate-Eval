import type { ComponentStatus } from "@tracegate/shared-types";

import { StatusBadge } from "./StatusBadge";

interface StatusCardProps {
  eyebrow: string;
  title: string;
  status: ComponentStatus;
}

export function StatusCard({ eyebrow, title, status }: StatusCardProps) {
  return (
    <article className={`status-card status-card-${status.state}`}>
      <div className="status-card-heading">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h3>{title}</h3>
        </div>
        <StatusBadge status={status} />
      </div>
      <p>{status.message}</p>
      {status.detail ? <p className="status-detail">{status.detail}</p> : null}
    </article>
  );
}
