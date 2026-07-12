import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useAnalyzePullRequest, usePullRequests, useRepositories, useRuns, useSettings, useSyncRepository, useUpdateSettings } from "../api/queries";
import { useApiClient } from "../api/clientContext";
import { ErrorState, LoadingState } from "../components/RequestState";
import { errorMessage } from "../lib/errors";
import { useUiStore } from "../store/uiStore";
import { useI18n } from "../i18n";

const statusOptions = [
  ["all", "全部", "All"],
  ["not_analyzed", "未分析", "Not analyzed"],
  ["queued", "排队中", "Queued"],
  ["running", "分析中", "Running"],
  ["completed", "已完成", "Completed"],
  ["failed", "失败", "Failed"],
  ["cancelled", "已取消", "Cancelled"],
] as const;

export function PullRequestInboxPage() {
  const { locale, text } = useI18n();
  const client = useApiClient();
  const queryClient = useQueryClient();
  const repositories = useRepositories();
  const selectedRepositoryId = useUiStore((state) => state.selectedRepositoryId);
  const selectRepository = useUiStore((state) => state.selectRepository);
  const selectPullRequest = useUiStore((state) => state.selectPullRequest);
  const [analysisFilter, setAnalysisFilter] = useState("all");
  const [stateFilter, setStateFilter] = useState("all");
  const [checksFilter, setChecksFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [modelFilter, setModelFilter] = useState("all");
  const [updatedSince, setUpdatedSince] = useState("");
  const [search, setSearch] = useState("");
  const pullRequests = usePullRequests(selectedRepositoryId ?? undefined);
  const syncRepository = useSyncRepository();
  const analyze = useAnalyzePullRequest();
  const runs = useRuns();
  const settings = useSettings();
  const updateSettings = useUpdateSettings();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkError, setBulkError] = useState<string | null>(null);

  const visible = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return (pullRequests.data?.items ?? []).filter((pullRequest) => {
      if (analysisFilter !== "all" && pullRequest.analysis_status !== analysisFilter) return false;
      if (stateFilter !== "all" && pullRequest.state !== stateFilter) return false;
      if (checksFilter !== "all" && pullRequest.checks_status !== checksFilter) return false;
      if (riskFilter !== "all" && pullRequest.risk_level !== riskFilter) return false;
      if (modelFilter !== "all" && pullRequest.latest_model_profile !== modelFilter) return false;
      if (updatedSince && (!pullRequest.updated_at_github || new Date(pullRequest.updated_at_github) < new Date(`${updatedSince}T00:00:00`))) return false;
      return !query || `${pullRequest.title} ${pullRequest.author ?? ""} #${pullRequest.number}`.toLocaleLowerCase().includes(query);
    });
  }, [analysisFilter, checksFilter, modelFilter, pullRequests.data?.items, riskFilter, search, stateFilter, updatedSince]);
  const modelOptions = useMemo(() => [...new Set((pullRequests.data?.items ?? []).map((item) => item.latest_model_profile).filter((item): item is string => Boolean(item)))].sort(), [pullRequests.data?.items]);

  function toggleSelection(id: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function runBulk(action: "analyze" | "cancel" | "retry") {
    setBulkBusy(true);
    setBulkError(null);
    try {
      if (action === "analyze") {
        for (const pullRequestId of selectedIds) await client.analyzePullRequest(pullRequestId);
      } else {
        const candidates = (runs.data?.items ?? []).filter((run) => run.pull_request_id && selectedIds.has(run.pull_request_id));
        if (action === "cancel") {
          for (const run of candidates.filter((item) => item.status === "queued" || item.status === "running")) await client.cancelRun(run.id);
        } else {
          const latestByPullRequest = new Map<string, (typeof candidates)[number]>();
          for (const run of candidates.filter((item) => item.status === "failed" || item.status === "cancelled")) {
            if (run.pull_request_id && !latestByPullRequest.has(run.pull_request_id)) latestByPullRequest.set(run.pull_request_id, run);
          }
          for (const run of latestByPullRequest.values()) await client.retryRun(run.id);
        }
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["pull-requests"] }),
        queryClient.invalidateQueries({ queryKey: ["runs"] }),
      ]);
    } catch (error) {
      setBulkError(errorMessage(error));
    } finally {
      setBulkBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <span className="eyebrow">PULL REQUEST INBOX</span>
        <h2>{text("审查队列", "Review queue")}</h2>
        <p>{text("列表来自 GitHub 同步快照；没有同步记录时保持空状态，不生成示例 PR。", "The list comes from synchronized GitHub snapshots. It stays empty without synchronized records and never generates example PRs.")}</p>
      </header>

      <section className="filter-bar" aria-label={text("PR 筛选", "PR filters")}>
        <label className="field"><span>{text("仓库", "Repository")}</span>
          <select value={selectedRepositoryId ?? "all"} onChange={(event) => {
            const value = event.target.value;
            if (value === "all") useUiStore.setState({ selectedRepositoryId: null });
            else selectRepository(value, "pull-requests");
          }}>
            <option value="all">{text("全部仓库", "All repositories")}</option>
            {repositories.data?.items.map((repository) => <option key={repository.id} value={repository.id}>{repository.full_name}</option>)}
          </select>
        </label>
        <label className="field"><span>{text("分析状态", "Analysis status")}</span><select value={analysisFilter} onChange={(event) => setAnalysisFilter(event.target.value)}>{statusOptions.map(([value, zh, en]) => <option key={value} value={value}>{text(zh, en)}</option>)}</select></label>
        <label className="field"><span>{text("PR 状态", "PR status")}</span><select value={stateFilter} onChange={(event) => setStateFilter(event.target.value)}><option value="all">{text("全部", "All")}</option><option value="open">{text("开放", "Open")}</option><option value="closed">{text("关闭", "Closed")}</option><option value="merged">{text("已合并", "Merged")}</option></select></label>
        <label className="field"><span>Checks</span><select value={checksFilter} onChange={(event) => setChecksFilter(event.target.value)}><option value="all">{text("全部", "All")}</option><option value="pending">{text("进行中", "Pending")}</option><option value="success">{text("通过", "Success")}</option><option value="failure">{text("失败", "Failure")}</option><option value="neutral">Neutral</option><option value="not_available">{text("无快照", "No snapshot")}</option></select></label>
        <label className="field"><span>{text("风险级别", "Risk level")}</span><select value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)}><option value="all">{text("全部", "All")}</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option><option value="info">Info</option></select></label>
        <label className="field"><span>{text("模型", "Model")}</span><select value={modelFilter} onChange={(event) => setModelFilter(event.target.value)}><option value="all">{text("全部", "All")}</option>{modelOptions.map((model) => <option key={model} value={model}>{model}</option>)}</select></label>
        <label className="field"><span>{text("更新日期不早于", "Updated since")}</span><input type="date" value={updatedSince} onChange={(event) => setUpdatedSince(event.target.value)} /></label>
        <label className="field"><span>{text("标题或作者", "Title or author")}</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={text("搜索真实同步记录", "Search synchronized records")} /></label>
        <button className="button button-secondary" type="button" disabled={!selectedRepositoryId || syncRepository.isPending} onClick={() => selectedRepositoryId && syncRepository.mutate(selectedRepositoryId)}>
          {syncRepository.isPending ? text("扫描中…", "Scanning…") : text("手动扫描", "Scan now")}
        </button>
      </section>
      <section className="bulk-toolbar" aria-label={text("批量分析操作", "Bulk analysis actions")}>
        <span>{selectedIds.size} {text("项已选择", "selected")}</span>
        <button className="button button-primary button-small" type="button" disabled={!selectedIds.size || bulkBusy || settings.data?.analysis_paused} onClick={() => void runBulk("analyze")}>{text("批量分析", "Analyze selected")}</button>
        <button className="button button-secondary button-small" type="button" disabled={!selectedIds.size || bulkBusy} onClick={() => void runBulk("cancel")}>{text("取消任务", "Cancel runs")}</button>
        <button className="button button-secondary button-small" type="button" disabled={!selectedIds.size || bulkBusy} onClick={() => void runBulk("retry")}>{text("重试失败任务", "Retry failed runs")}</button>
        <button className="button button-secondary button-small" type="button" disabled={updateSettings.isPending || !settings.data} onClick={() => settings.data && updateSettings.mutate({ analysis_paused: !settings.data.analysis_paused })}>{settings.data?.analysis_paused ? text("恢复分析", "Resume analysis") : text("暂停分析", "Pause analysis")}</button>
      </section>
      {bulkError ? <p className="inline-error" role="alert">{text("批量操作失败", "Bulk operation failed")}: {bulkError}</p> : null}
      {settings.data?.analysis_paused ? <p className="blocker-note">{text("新分析已暂停；正在运行的任务可单独取消。", "New analysis is paused; active runs can still be cancelled individually.")}</p> : null}
      {syncRepository.isError ? <p className="inline-error" role="alert">{text("同步失败", "Synchronization failed")}: {errorMessage(syncRepository.error)}</p> : null}
      {analyze.isError ? <p className="inline-error" role="alert">{text("分析未启动", "Analysis did not start")}: {errorMessage(analyze.error)}</p> : null}

      {pullRequests.isPending ? <LoadingState label={text("正在读取 PR 快照…", "Reading PR snapshots…")} /> : null}
      {pullRequests.isError ? <ErrorState title={text("PR Inbox 读取失败", "Unable to read PR Inbox")} message={errorMessage(pullRequests.error)} onRetry={() => void pullRequests.refetch()} /> : null}
      {pullRequests.data && visible.length === 0 ? (
        <div className="honest-empty-state"><div className="empty-mark">PR</div><div><h2>{text("当前筛选没有 PR", "No PRs match the current filters")}</h2><p>{text("选择一个已添加仓库并执行手动扫描。未配置 GitHub 时，后端会明确返回“GitHub 尚未连接”。", "Select an enrolled repository and scan it. If GitHub is unconfigured, the backend explicitly reports that GitHub is not connected.")}</p></div></div>
      ) : null}
      <div className="data-table-wrap">
        {visible.length ? (
          <table className="data-table">
            <thead><tr><th><input type="checkbox" aria-label={text("选择当前列表", "Select visible Pull Requests")} checked={visible.length > 0 && visible.every((item) => selectedIds.has(item.id))} onChange={(event) => setSelectedIds((current) => { const next = new Set(current); for (const item of visible) { if (event.target.checked) next.add(item.id); else next.delete(item.id); } return next; })} /></th><th>PR</th><th>{text("作者", "Author")}</th><th>{text("变更", "Changes")}</th><th>{text("风险", "Risk")}</th><th>{text("分析", "Analysis")}</th><th>Checks</th><th>{text("更新时间", "Updated")}</th><th>{text("操作", "Actions")}</th></tr></thead>
            <tbody>{visible.map((pullRequest) => (
              <tr key={pullRequest.id}>
                <td><input type="checkbox" aria-label={text(`选择 PR #${pullRequest.number}`, `Select PR #${pullRequest.number}`)} checked={selectedIds.has(pullRequest.id)} onChange={() => toggleSelection(pullRequest.id)} /></td>
                <td><button className="table-link" type="button" onClick={() => selectPullRequest(pullRequest.id, pullRequest.repository_id)}>#{pullRequest.number} · {pullRequest.title}</button></td>
                <td>{pullRequest.author ?? text("未知", "Unknown")}</td>
                <td><span className="positive">+{pullRequest.additions}</span> <span className="negative">−{pullRequest.deletions}</span> · {pullRequest.changed_files} files</td>
                <td><span className={`pill severity-${pullRequest.risk_level ?? "none"}`}>{pullRequest.risk_level ?? text("未分析", "Not analyzed")}{pullRequest.risk_score !== null ? ` · ${pullRequest.risk_score}` : ""}</span></td>
                <td><span className={`pill pill-${pullRequest.analysis_status}`}>{pullRequest.analysis_status}</span></td>
                <td><span className={`pill pill-${pullRequest.checks_status}`}>{pullRequest.checks_status}</span></td>
                <td>{pullRequest.updated_at_github ? new Date(pullRequest.updated_at_github).toLocaleString(locale) : text("未记录", "Not recorded")}</td>
                <td><div className="action-row compact"><button className="button button-secondary button-small" type="button" onClick={() => selectPullRequest(pullRequest.id, pullRequest.repository_id)}>{text("详情", "Details")}</button><button className="button button-primary button-small" type="button" disabled={analyze.isPending || pullRequest.analysis_status === "running" || settings.data?.analysis_paused} onClick={() => analyze.mutate({ pullRequestId: pullRequest.id })}>{text("分析", "Analyze")}</button></div></td>
              </tr>
            ))}</tbody>
          </table>
        ) : null}
      </div>
    </div>
  );
}
