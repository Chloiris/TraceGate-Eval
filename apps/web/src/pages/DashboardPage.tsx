import { StatusCard } from "../components/StatusCard";
import { ErrorState, LoadingState } from "../components/RequestState";
import { useSystemStatus } from "../api/queries";
import { errorMessage } from "../lib/errors";

function formatCheckedAt(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("zh-CN", {
        dateStyle: "medium",
        timeStyle: "medium",
      }).format(date);
}

export function DashboardPage() {
  const statusQuery = useSystemStatus();

  if (statusQuery.isPending) {
    return <LoadingState />;
  }
  if (statusQuery.isError) {
    return (
      <ErrorState
        title="无法读取系统状态"
        message={errorMessage(statusQuery.error)}
        onRetry={() => void statusQuery.refetch()}
      />
    );
  }

  const { components, status, checked_at: checkedAt } = statusQuery.data;
  const summary =
    status === "ready"
      ? "基础服务已就绪"
      : status === "degraded"
        ? "部分能力尚未配置"
        : "系统需要处理错误";

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <span className="eyebrow">实时系统状态</span>
          <h2>{summary}</h2>
          <p>
            TraceGate Studio 只展示后端返回的真实状态。未配置的连接不会被替换为演示数据。
          </p>
        </div>
        <div className={`system-verdict verdict-${status}`}>
          <span>当前状态</span>
          <strong>{status === "ready" ? "READY" : status.toUpperCase()}</strong>
          <small>检查于 {formatCheckedAt(checkedAt)}</small>
        </div>
      </section>

      <section aria-labelledby="services-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">连接与运行环境</span>
            <h2 id="services-title">核心服务</h2>
          </div>
          <button
            className="button button-secondary button-small"
            type="button"
            onClick={() => void statusQuery.refetch()}
            disabled={statusQuery.isFetching}
          >
            {statusQuery.isFetching ? "刷新中…" : "刷新状态"}
          </button>
        </div>
        <div className="status-grid">
          <StatusCard eyebrow="LOCAL" title="本地后端" status={components.api} />
          <StatusCard eyebrow="PROVIDER" title="GitHub" status={components.github} />
          <StatusCard eyebrow="PROVIDER" title="模型" status={components.model} />
          <StatusCard eyebrow="STORAGE" title="数据库" status={components.database} />
          <StatusCard eyebrow="TRACEGATE" title="Eval 核心" status={components.eval} />
        </div>
      </section>

      <section className="honest-empty-state" aria-labelledby="workspace-title">
        <div className="empty-mark" aria-hidden="true">TG</div>
        <div>
          <span className="eyebrow">P0 产品边界</span>
          <h2 id="workspace-title">仓库与 PR 数据尚未接入此页面</h2>
          <p>
            当前 `/api/v1` 只提供系统、设置与首次引导状态。仓库、Pull Request、Finding
            和 Agent Run 接口完成前，这里不会显示估算数字、占位风险或虚构活动。
          </p>
        </div>
      </section>
    </div>
  );
}
