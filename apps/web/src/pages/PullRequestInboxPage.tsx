import { useMemo, useState } from "react";

import { useAnalyzePullRequest, usePullRequests, useRepositories, useSyncRepository } from "../api/queries";
import { ErrorState, LoadingState } from "../components/RequestState";
import { errorMessage } from "../lib/errors";
import { useUiStore } from "../store/uiStore";

const statusOptions = [
  ["all", "全部"],
  ["not_analyzed", "未分析"],
  ["queued", "排队中"],
  ["running", "分析中"],
  ["completed", "已完成"],
  ["failed", "失败"],
] as const;

export function PullRequestInboxPage() {
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
        <h2>审查队列</h2>
        <p>列表来自 GitHub 同步快照；没有同步记录时保持空状态，不生成示例 PR。</p>
      </header>

      <section className="filter-bar" aria-label="PR 筛选">
        <label className="field"><span>仓库</span>
          <select value={selectedRepositoryId ?? "all"} onChange={(event) => {
            const value = event.target.value;
            if (value === "all") useUiStore.setState({ selectedRepositoryId: null });
            else selectRepository(value, "pull-requests");
          }}>
            <option value="all">全部仓库</option>
            {repositories.data?.items.map((repository) => <option key={repository.id} value={repository.id}>{repository.full_name}</option>)}
          </select>
        </label>
        <label className="field"><span>分析状态</span><select value={analysisFilter} onChange={(event) => setAnalysisFilter(event.target.value)}>{statusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="field"><span>PR 状态</span><select value={stateFilter} onChange={(event) => setStateFilter(event.target.value)}><option value="all">全部</option><option value="open">开放</option><option value="closed">关闭</option><option value="merged">已合并</option></select></label>
        <label className="field"><span>标题或作者</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索真实同步记录" /></label>
        <button className="button button-secondary" type="button" disabled={!selectedRepositoryId || syncRepository.isPending} onClick={() => selectedRepositoryId && syncRepository.mutate(selectedRepositoryId)}>
          {syncRepository.isPending ? "扫描中…" : "手动扫描"}
        </button>
      </section>
      {syncRepository.isError ? <p className="inline-error" role="alert">同步失败：{errorMessage(syncRepository.error)}</p> : null}
      {analyze.isError ? <p className="inline-error" role="alert">分析未启动：{errorMessage(analyze.error)}</p> : null}

      {pullRequests.isPending ? <LoadingState label="正在读取 PR 快照…" /> : null}
      {pullRequests.isError ? <ErrorState title="PR Inbox 读取失败" message={errorMessage(pullRequests.error)} onRetry={() => void pullRequests.refetch()} /> : null}
      {pullRequests.data && visible.length === 0 ? (
        <div className="honest-empty-state"><div className="empty-mark">PR</div><div><h2>当前筛选没有 PR</h2><p>选择一个已添加仓库并执行手动扫描。未配置 GitHub 时，后端会明确返回“GitHub 尚未连接”。</p></div></div>
      ) : null}
      <div className="data-table-wrap">
        {visible.length ? (
          <table className="data-table">
            <thead><tr><th>PR</th><th>作者</th><th>变更</th><th>状态</th><th>更新时间</th><th>操作</th></tr></thead>
            <tbody>{visible.map((pullRequest) => (
              <tr key={pullRequest.id}>
                <td><button className="table-link" type="button" onClick={() => selectPullRequest(pullRequest.id, pullRequest.repository_id)}>#{pullRequest.number} · {pullRequest.title}</button></td>
                <td>{pullRequest.author ?? "未知"}</td>
                <td><span className="positive">+{pullRequest.additions}</span> <span className="negative">−{pullRequest.deletions}</span> · {pullRequest.changed_files} files</td>
                <td><span className={`pill pill-${pullRequest.analysis_status}`}>{pullRequest.analysis_status}</span></td>
                <td>{pullRequest.updated_at_github ? new Date(pullRequest.updated_at_github).toLocaleString("zh-CN") : "未记录"}</td>
                <td><div className="action-row compact"><button className="button button-secondary button-small" type="button" onClick={() => selectPullRequest(pullRequest.id, pullRequest.repository_id)}>详情</button><button className="button button-primary button-small" type="button" disabled={analyze.isPending || pullRequest.analysis_status === "running"} onClick={() => analyze.mutate({ pullRequestId: pullRequest.id })}>分析</button></div></td>
              </tr>
            ))}</tbody>
          </table>
        ) : null}
      </div>
    </div>
  );
}
