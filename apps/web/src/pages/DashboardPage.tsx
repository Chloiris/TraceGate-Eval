import { StatusCard } from "../components/StatusCard";
import { ErrorState, LoadingState } from "../components/RequestState";
import { usePullRequests, useRepositories, useRuns, useSystemStatus } from "../api/queries";
import { errorMessage } from "../lib/errors";
import { useI18n } from "../i18n";

function formatCheckedAt(value: string, locale: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        timeStyle: "medium",
      }).format(date);
}

export function DashboardPage() {
  const { locale, text } = useI18n();
  const statusQuery = useSystemStatus();
  const repositories = useRepositories();
  const pullRequests = usePullRequests();
  const runs = useRuns();

  if (statusQuery.isPending) {
    return <LoadingState />;
  }
  if (statusQuery.isError) {
    return (
      <ErrorState
        title={text("无法读取系统状态", "Unable to read system status")}
        message={errorMessage(statusQuery.error)}
        onRetry={() => void statusQuery.refetch()}
      />
    );
  }

  const { components, status, checked_at: checkedAt } = statusQuery.data;
  const summary =
    status === "ready"
      ? text("基础服务已就绪", "Core services are ready")
      : status === "degraded"
        ? text("部分能力尚未配置", "Some capabilities are not configured")
        : text("系统需要处理错误", "System errors require attention");

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <span className="eyebrow">{text("实时系统状态", "LIVE SYSTEM STATUS")}</span>
          <h2>{summary}</h2>
          <p>
            {text("TraceGate Studio 只展示后端返回的真实状态。未配置的连接不会被替换为演示数据。", "TraceGate Studio displays only real backend state. Unconfigured connections are never replaced with demo data.")}
          </p>
        </div>
        <div className={`system-verdict verdict-${status}`}>
          <span>{text("当前状态", "Current status")}</span>
          <strong>{status === "ready" ? "READY" : status.toUpperCase()}</strong>
          <small>{text("检查于", "Checked")} {formatCheckedAt(checkedAt, locale)}</small>
        </div>
      </section>

      <section aria-labelledby="services-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">{text("连接与运行环境", "CONNECTIONS AND RUNTIME")}</span>
            <h2 id="services-title">{text("核心服务", "Core services")}</h2>
          </div>
          <button
            className="button button-secondary button-small"
            type="button"
            onClick={() => void statusQuery.refetch()}
            disabled={statusQuery.isFetching}
          >
            {statusQuery.isFetching ? text("刷新中…", "Refreshing…") : text("刷新状态", "Refresh status")}
          </button>
        </div>
        <div className="status-grid">
          <StatusCard eyebrow="LOCAL" title={text("本地后端", "Local backend")} status={components.api} />
          <StatusCard eyebrow="PROVIDER" title="GitHub" status={components.github} />
          <StatusCard eyebrow="PROVIDER" title={text("模型", "Model")} status={components.model} />
          <StatusCard eyebrow="STORAGE" title={text("数据库", "Database")} status={components.database} />
          <StatusCard eyebrow="TRACEGATE" title={text("Eval 核心", "Eval core")} status={components.eval} />
        </div>
      </section>

      <section aria-labelledby="workspace-title">
        <div className="section-heading"><div><span className="eyebrow">LIVE SQLITE STATE</span><h2 id="workspace-title">{text("工作区活动", "Workspace activity")}</h2></div></div>
        {repositories.isError || pullRequests.isError || runs.isError ? (
          <ErrorState title={text("活动统计读取失败", "Unable to read activity totals")} message={errorMessage(repositories.error ?? pullRequests.error ?? runs.error)} />
        ) : null}
        <div className="metric-cards">
          <div><span>{text("监控仓库", "Monitored repositories")}</span><strong>{repositories.data?.items.filter((item) => item.monitoring_enabled).length ?? "…"}</strong></div>
          <div><span>{text("开放 PR", "Open PRs")}</span><strong>{pullRequests.data?.items.filter((item) => item.state === "open").length ?? "…"}</strong></div>
          <div><span>{text("待分析 PR", "PRs awaiting analysis")}</span><strong>{pullRequests.data?.items.filter((item) => item.analysis_status === "not_analyzed").length ?? "…"}</strong></div>
          <div><span>{text("运行中 Agent", "Active agents")}</span><strong>{runs.data?.items.filter((item) => item.status === "queued" || item.status === "running").length ?? "…"}</strong></div>
          <div><span>{text("最近完成", "Recently completed")}</span><strong>{runs.data?.items.filter((item) => item.status === "completed").length ?? "…"}</strong></div>
          <div><span>{text("最近失败", "Recently failed")}</span><strong>{runs.data?.items.filter((item) => item.status === "failed").length ?? "…"}</strong></div>
          <div><span>{text("已索引仓库", "Indexed repositories")}</span><strong>{repositories.data?.items.filter((item) => item.current_index_version).length ?? "…"}</strong></div>
          <div><span>GitHub Rate Limit</span><strong>{repositories.data?.items.find((item) => item.github_rate_remaining !== null)?.github_rate_remaining ?? text("未知", "Unknown")}</strong></div>
        </div>
        <p className="field-note">{text("以上数字直接聚合当前 API 返回记录。模型成本尚无已配置价格，因此不显示估算值。", "These totals are aggregated directly from current API records. Model cost is omitted because no pricing is configured.")}</p>
      </section>
    </div>
  );
}
