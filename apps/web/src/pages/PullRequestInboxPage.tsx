import { useMemo, useState } from "react";

import { useAnalyzePullRequest, usePullRequests, useRepositories, useSyncRepository } from "../api/queries";
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
] as const;

export function PullRequestInboxPage() {
  const { locale, text } = useI18n();
  const repositories = useRepositories();
  const selectedRepositoryId = useUiStore((state) => state.selectedRepositoryId);
  const selectRepository = useUiStore((state) => state.selectRepository);
  const selectPullRequest = useUiStore((state) => state.selectPullRequest);
  const [analysisFilter, setAnalysisFilter] = useState("all");
  const [stateFilter, setStateFilter] = useState("all");
  const [search, setSearch] = useState("");
  const pullRequests = usePullRequests(selectedRepositoryId ?? undefined);
  const syncRepository = useSyncRepository();
  const analyze = useAnalyzePullRequest();

  const visible = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return (pullRequests.data?.items ?? []).filter((pullRequest) => {
      if (analysisFilter !== "all" && pullRequest.analysis_status !== analysisFilter) return false;
      if (stateFilter !== "all" && pullRequest.state !== stateFilter) return false;
      return !query || `${pullRequest.title} ${pullRequest.author ?? ""} #${pullRequest.number}`.toLocaleLowerCase().includes(query);
    });
  }, [analysisFilter, pullRequests.data?.items, search, stateFilter]);

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
        <label className="field"><span>{text("标题或作者", "Title or author")}</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={text("搜索真实同步记录", "Search synchronized records")} /></label>
        <button className="button button-secondary" type="button" disabled={!selectedRepositoryId || syncRepository.isPending} onClick={() => selectedRepositoryId && syncRepository.mutate(selectedRepositoryId)}>
          {syncRepository.isPending ? text("扫描中…", "Scanning…") : text("手动扫描", "Scan now")}
        </button>
      </section>
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
            <thead><tr><th>PR</th><th>{text("作者", "Author")}</th><th>{text("变更", "Changes")}</th><th>{text("状态", "Status")}</th><th>{text("更新时间", "Updated")}</th><th>{text("操作", "Actions")}</th></tr></thead>
            <tbody>{visible.map((pullRequest) => (
              <tr key={pullRequest.id}>
                <td><button className="table-link" type="button" onClick={() => selectPullRequest(pullRequest.id, pullRequest.repository_id)}>#{pullRequest.number} · {pullRequest.title}</button></td>
                <td>{pullRequest.author ?? text("未知", "Unknown")}</td>
                <td><span className="positive">+{pullRequest.additions}</span> <span className="negative">−{pullRequest.deletions}</span> · {pullRequest.changed_files} files</td>
                <td><span className={`pill pill-${pullRequest.analysis_status}`}>{pullRequest.analysis_status}</span></td>
                <td>{pullRequest.updated_at_github ? new Date(pullRequest.updated_at_github).toLocaleString(locale) : text("未记录", "Not recorded")}</td>
                <td><div className="action-row compact"><button className="button button-secondary button-small" type="button" onClick={() => selectPullRequest(pullRequest.id, pullRequest.repository_id)}>{text("详情", "Details")}</button><button className="button button-primary button-small" type="button" disabled={analyze.isPending || pullRequest.analysis_status === "running"} onClick={() => analyze.mutate({ pullRequestId: pullRequest.id })}>{text("分析", "Analyze")}</button></div></td>
              </tr>
            ))}</tbody>
          </table>
        ) : null}
      </div>
    </div>
  );
}
