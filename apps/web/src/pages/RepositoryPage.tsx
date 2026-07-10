import { useState, type FormEvent } from "react";
import type { Repository } from "@tracegate/shared-types";

import {
  useCreateRepository,
  useDeleteRepository,
  useIndexRepository,
  useRepositories,
  useSyncRepository,
  useUpdateRepository,
} from "../api/queries";
import { ErrorState, LoadingState } from "../components/RequestState";
import { errorMessage } from "../lib/errors";
import { useUiStore } from "../store/uiStore";

function shortSha(value: string | null): string {
  return value ? value.slice(0, 10) : "尚未索引";
}

function formatDate(value: string | null): string {
  if (!value) return "尚未同步";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("zh-CN");
}

export function RepositoryPage() {
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
        <h2>受控仓库</h2>
        <p>只有显式添加的本地目录会被索引。路径越界、符号链接逃逸和敏感文件读取会被后端拒绝。</p>
      </header>

      <form className="settings-panel repository-form" onSubmit={submit}>
        <div className="form-grid">
          <label className="field">
            <span>GitHub 仓库（owner/name）</span>
            <input
              required
              pattern="[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="openai/openai-python"
            />
          </label>
          <label className="field">
            <span>本地工作区绝对路径（可选）</span>
            <input
              value={localPath}
              onChange={(event) => setLocalPath(event.target.value)}
              placeholder="/Users/name/projects/repository"
            />
          </label>
        </div>
        <label className="switch-row">
          <span><strong>后台监控</strong><small>启用后仓库会进入真实 PR 轮询范围。</small></span>
          <input type="checkbox" checked={monitoring} onChange={(event) => setMonitoring(event.target.checked)} />
        </label>
        {createRepository.isError ? (
          <p className="inline-error" role="alert">添加失败：{errorMessage(createRepository.error)}</p>
        ) : null}
        <div className="form-actions">
          <button className="button button-primary" type="submit" disabled={createRepository.isPending}>
            {createRepository.isPending ? "添加中…" : "添加仓库"}
          </button>
        </div>
      </form>

      <section aria-labelledby="repository-list-title">
        <div className="section-heading">
          <div><span className="eyebrow">ENROLLED</span><h2 id="repository-list-title">仓库列表</h2></div>
          <span className="count-label">{repositories.data?.total ?? 0} 个仓库</span>
        </div>
        {repositories.isPending ? <LoadingState label="正在读取仓库…" /> : null}
        {repositories.isError ? (
          <ErrorState title="仓库读取失败" message={errorMessage(repositories.error)} onRetry={() => void repositories.refetch()} />
        ) : null}
        {repositories.data?.items.length === 0 ? (
          <div className="honest-empty-state">
            <div className="empty-mark">REPO</div>
            <div><h2>还没有受控仓库</h2><p>填写真实 GitHub 仓库名；需要索引、Diff 和代码图时，同时提供本地 Git 工作区。</p></div>
          </div>
        ) : null}
        <div className="repository-grid">
          {repositories.data?.items.map((repository) => (
            <RepositoryCard key={repository.id} repository={repository} />
          ))}
        </div>
      </section>
    </div>
  );
}

function RepositoryCard({ repository }: { repository: Repository }) {
  const syncRepository = useSyncRepository();
  const indexRepository = useIndexRepository();
  const updateRepository = useUpdateRepository();
  const deleteRepository = useDeleteRepository();
  const selectRepository = useUiStore((state) => state.selectRepository);
  const operationError = syncRepository.error ?? indexRepository.error ?? updateRepository.error ?? deleteRepository.error;
  const busy = syncRepository.isPending || indexRepository.isPending || updateRepository.isPending || deleteRepository.isPending;

  function remove() {
    if (window.confirm(`从 TraceGate 删除 ${repository.full_name}？本地仓库文件不会被删除。`)) {
      deleteRepository.mutate(repository.id);
    }
  }

  return (
    <article className="repository-card">
      <div className="repository-card-heading">
        <div><span className="eyebrow">{repository.connection_status}</span><h3>{repository.full_name}</h3></div>
        <span className={`pill pill-${repository.monitoring_enabled ? "active" : "muted"}`}>
          {repository.monitoring_enabled ? "监控中" : "已暂停"}
        </span>
      </div>
      <dl className="metadata-grid">
        <div><dt>本地目录</dt><dd title={repository.local_path ?? undefined}>{repository.local_path ?? "未绑定"}</dd></div>
        <div><dt>默认分支</dt><dd>{repository.default_branch ?? "未同步"}</dd></div>
        <div><dt>HEAD</dt><dd className="mono">{shortSha(repository.current_commit_sha)}</dd></div>
        <div><dt>索引版本</dt><dd className="mono">{shortSha(repository.current_index_version)}</dd></div>
        <div><dt>最近同步</dt><dd>{formatDate(repository.last_synced_at)}</dd></div>
        <div><dt>Rate Limit</dt><dd>{repository.github_rate_remaining ?? "未知"}</dd></div>
      </dl>
      {repository.last_error ? <p className="inline-error" role="alert">{repository.last_error}</p> : null}
      {operationError ? <p className="inline-error" role="alert">操作失败：{errorMessage(operationError)}</p> : null}
      <div className="action-row">
        <button className="button button-primary button-small" type="button" disabled={busy} onClick={() => syncRepository.mutate(repository.id)}>立即同步</button>
        <button className="button button-secondary button-small" type="button" disabled={busy || !repository.local_path} onClick={() => indexRepository.mutate(repository.id)}>重新索引</button>
        <button className="button button-secondary button-small" type="button" disabled={busy} onClick={() => updateRepository.mutate({ repositoryId: repository.id, update: { monitoring_enabled: !repository.monitoring_enabled } })}>
          {repository.monitoring_enabled ? "暂停监控" : "恢复监控"}
        </button>
        <button className="button button-secondary button-small" type="button" disabled={!repository.current_index_version} onClick={() => selectRepository(repository.id, "repository-map")}>Repository Map</button>
        <a className="button button-secondary button-small" href={`https://github.com/${repository.full_name}`} target="_blank" rel="noreferrer">GitHub</a>
        {repository.local_path ? <a className="button button-secondary button-small" href={`vscode://file/${encodeURI(repository.local_path)}`}>VS Code</a> : null}
        <button className="button button-danger button-small" type="button" disabled={busy} onClick={remove}>删除</button>
      </div>
    </article>
  );
}
