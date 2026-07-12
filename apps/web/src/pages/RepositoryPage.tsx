import { useState, type FormEvent } from "react";
import type { Repository } from "@tracegate/shared-types";

import {
  useCreateRepository,
  useClearRepositoryCache,
  useDeleteRepository,
  useIndexRepository,
  useRepositories,
  useRepositorySummary,
  useSyncRepository,
  useUpdateRepository,
} from "../api/queries";
import { ErrorState, LoadingState } from "../components/RequestState";
import { errorMessage } from "../lib/errors";
import { useUiStore } from "../store/uiStore";
import { useI18n } from "../i18n";
import type { HostBridge } from "../host/hostBridge";

function shortSha(value: string | null, empty: string): string {
  return value ? value.slice(0, 10) : empty;
}

function formatDate(value: string | null, locale: string, empty: string): string {
  if (!value) return empty;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString(locale);
}

export function RepositoryPage({ host }: { host: HostBridge }) {
  const { text } = useI18n();
  const repositories = useRepositories();
  const createRepository = useCreateRepository();
  const [fullName, setFullName] = useState("");
  const [localPath, setLocalPath] = useState("");
  const [monitoring, setMonitoring] = useState(true);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createRepository.mutate({
      full_name: fullName.trim(),
      local_path: localPath.trim() || null,
      monitoring_enabled: monitoring,
    }, {
      onSuccess: () => {
        setFullName("");
        setLocalPath("");
      },
    });
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <span className="eyebrow">REPOSITORY CONTROL</span>
        <h2>{text("受控仓库", "Controlled repositories")}</h2>
        <p>{text("只有显式添加的本地目录会被索引。路径越界、符号链接逃逸和敏感文件读取会被后端拒绝。", "Only explicitly enrolled local directories are indexed. The backend rejects path escapes, symlink escapes, and sensitive-file reads.")}</p>
      </header>

      <form className="settings-panel repository-form" onSubmit={submit}>
        <div className="form-grid">
          <label className="field">
            <span>{text("GitHub 仓库（owner/name）", "GitHub repository (owner/name)")}</span>
            <input
              required
              pattern="[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="openai/openai-python"
            />
          </label>
          <label className="field">
            <span>{text("本地工作区绝对路径（可选）", "Absolute local workspace path (optional)")}</span>
            <input
              value={localPath}
              onChange={(event) => setLocalPath(event.target.value)}
              placeholder="/Users/name/projects/repository"
            />
          </label>
        </div>
        <label className="switch-row">
          <span><strong>{text("后台监控", "Background monitoring")}</strong><small>{text("启用后仓库会进入真实 PR 轮询范围。", "When enabled, the repository enters the real PR polling scope.")}</small></span>
          <input type="checkbox" checked={monitoring} onChange={(event) => setMonitoring(event.target.checked)} />
        </label>
        {createRepository.isError ? (
          <p className="inline-error" role="alert">{text("添加失败", "Add failed")}: {errorMessage(createRepository.error)}</p>
        ) : null}
        <div className="form-actions">
          <button className="button button-primary" type="submit" disabled={createRepository.isPending}>
            {createRepository.isPending ? text("添加中…", "Adding…") : text("添加仓库", "Add repository")}
          </button>
        </div>
      </form>

      <section aria-labelledby="repository-list-title">
        <div className="section-heading">
          <div><span className="eyebrow">ENROLLED</span><h2 id="repository-list-title">{text("仓库列表", "Repository list")}</h2></div>
          <span className="count-label">{repositories.data?.total ?? 0} {text("个仓库", "repositories")}</span>
        </div>
        {repositories.isPending ? <LoadingState label={text("正在读取仓库…", "Reading repositories…")} /> : null}
        {repositories.isError ? (
          <ErrorState title={text("仓库读取失败", "Unable to read repositories")} message={errorMessage(repositories.error)} onRetry={() => void repositories.refetch()} />
        ) : null}
        {repositories.data?.items.length === 0 ? (
          <div className="honest-empty-state">
            <div className="empty-mark">REPO</div>
            <div><h2>{text("还没有受控仓库", "No controlled repositories")}</h2><p>{text("填写真实 GitHub 仓库名；需要索引、Diff 和代码图时，同时提供本地 Git 工作区。", "Enter a real GitHub repository name and provide a local Git workspace when indexing, diffs, and code maps are needed.")}</p></div>
          </div>
        ) : null}
        <div className="repository-grid">
          {repositories.data?.items.map((repository) => (
            <RepositoryCard key={repository.id} repository={repository} host={host} />
          ))}
        </div>
      </section>
    </div>
  );
}

function RepositoryCard({ repository, host }: { repository: Repository; host: HostBridge }) {
  const { locale, text } = useI18n();
  const syncRepository = useSyncRepository();
  const indexRepository = useIndexRepository();
  const updateRepository = useUpdateRepository();
  const deleteRepository = useDeleteRepository();
  const clearCache = useClearRepositoryCache();
  const summary = useRepositorySummary(repository.id);
  const selectRepository = useUiStore((state) => state.selectRepository);
  const operationError = syncRepository.error ?? indexRepository.error ?? updateRepository.error ?? deleteRepository.error ?? clearCache.error ?? summary.error;
  const busy = syncRepository.isPending || indexRepository.isPending || updateRepository.isPending || deleteRepository.isPending || clearCache.isPending;
  const localPath = repository.local_path;

  function remove() {
    if (window.confirm(text(`从 TraceGate 删除 ${repository.full_name}？本地仓库文件不会被删除。`, `Remove ${repository.full_name} from TraceGate? Local repository files will not be deleted.`))) {
      deleteRepository.mutate(repository.id);
    }
  }

  function removeCache() {
    if (window.confirm(text(`清理 ${repository.full_name} 的本地索引缓存？仓库源码与历史分析不会被删除。`, `Clear the local index cache for ${repository.full_name}? Source files and analysis history are preserved.`))) {
      clearCache.mutate(repository.id);
    }
  }

  return (
    <article className="repository-card">
      <div className="repository-card-heading">
        <div><span className="eyebrow">{repository.connection_status}</span><h3>{repository.full_name}</h3></div>
        <span className={`pill pill-${repository.monitoring_enabled ? "active" : "muted"}`}>
          {repository.monitoring_enabled ? text("监控中", "Monitoring") : text("已暂停", "Paused")}
        </span>
      </div>
      <dl className="metadata-grid">
        <div><dt>{text("本地目录", "Local directory")}</dt><dd title={repository.local_path ?? undefined}>{repository.local_path ?? text("未绑定", "Not bound")}</dd></div>
        <div><dt>{text("默认分支", "Default branch")}</dt><dd>{repository.default_branch ?? text("未同步", "Not synchronized")}</dd></div>
        <div><dt>HEAD</dt><dd className="mono">{shortSha(repository.current_commit_sha, text("尚未索引", "Not indexed"))}</dd></div>
        <div><dt>{text("索引版本", "Index version")}</dt><dd className="mono">{shortSha(repository.current_index_version, text("尚未索引", "Not indexed"))}</dd></div>
        <div><dt>{text("最近同步", "Last synchronized")}</dt><dd>{formatDate(repository.last_synced_at, locale, text("尚未同步", "Never synchronized"))}</dd></div>
        <div><dt>Rate Limit</dt><dd>{repository.github_rate_remaining ?? text("未知", "Unknown")}</dd></div>
        <div><dt>{text("文件 / 目录", "Files / directories")}</dt><dd>{summary.data ? `${summary.data.file_count} / ${summary.data.directory_count}` : "…"}</dd></div>
        <div><dt>{text("符号 / 关系边", "Symbols / relation edges")}</dt><dd>{summary.data ? `${summary.data.symbol_count} / ${summary.data.dependency_edge_count}` : "…"}</dd></div>
        <div><dt>{text("语言构成", "Languages")}</dt><dd>{summary.data ? Object.entries(summary.data.language_counts).map(([language, count]) => `${language} ${count}`).join(" · ") || text("尚未索引", "Not indexed") : "…"}</dd></div>
        <div><dt>{text("活跃 PR", "Active PRs")}</dt><dd>{summary.data?.active_pull_requests ?? "…"}</dd></div>
      </dl>
      {repository.last_error ? <p className="inline-error" role="alert">{repository.last_error}</p> : null}
      {operationError ? <p className="inline-error" role="alert">{text("操作失败", "Operation failed")}: {errorMessage(operationError)}</p> : null}
      <div className="action-row">
        <button className="button button-primary button-small" type="button" disabled={busy} onClick={() => syncRepository.mutate(repository.id)}>{text("立即同步", "Synchronize now")}</button>
        <button className="button button-secondary button-small" type="button" disabled={busy || !repository.local_path} onClick={() => indexRepository.mutate(repository.id)}>{text("重新索引", "Reindex")}</button>
        <button className="button button-secondary button-small" type="button" disabled={busy} onClick={() => updateRepository.mutate({ repositoryId: repository.id, update: { monitoring_enabled: !repository.monitoring_enabled } })}>
          {repository.monitoring_enabled ? text("暂停监控", "Pause monitoring") : text("恢复监控", "Resume monitoring")}
        </button>
        <button className="button button-secondary button-small" type="button" disabled={!repository.current_index_version} onClick={() => selectRepository(repository.id, "repository-map")}>Repository Map</button>
        <a className="button button-secondary button-small" href={`https://github.com/${repository.full_name}`} target="_blank" rel="noreferrer">GitHub</a>
        {localPath ? <button className="button button-secondary button-small" type="button" disabled={!host.openWorkspace} onClick={() => void host.openWorkspace?.(localPath, false)}>{text("打开本地目录", "Open local directory")}</button> : null}
        {localPath ? <button className="button button-secondary button-small" type="button" disabled={!host.openWorkspace} onClick={() => void host.openWorkspace?.(localPath, true)}>VS Code</button> : null}
        <button className="button button-secondary button-small" type="button" disabled={busy || !repository.current_index_version} onClick={removeCache}>{text("清理缓存", "Clear cache")}</button>
        <button className="button button-danger button-small" type="button" disabled={busy} onClick={remove}>{text("删除", "Delete")}</button>
      </div>
    </article>
  );
}
