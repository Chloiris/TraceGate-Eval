import { useEffect, useMemo, useState, type KeyboardEvent } from "react";

import { usePullRequests, useRepositories, useRuns } from "../api/queries";
import { useI18n } from "../i18n";
import { useUiStore, type StudioView } from "../store/uiStore";

interface PaletteItem {
  id: string;
  label: string;
  detail: string;
  keywords: string;
  run: () => void;
}

const viewCommands: readonly [StudioView, string, string][] = [
  ["dashboard", "概览", "Overview"],
  ["repositories", "仓库", "Repositories"],
  ["pull-requests", "PR Inbox", "PR Inbox"],
  ["repository-map", "代码地图", "Code Map"],
  ["runs", "Agent Runs", "Agent Runs"],
  ["eval", "Eval Center", "Eval Center"],
  ["registry", "Registry", "Registry"],
  ["diagnostics", "诊断", "Diagnostics"],
  ["settings", "设置", "Settings"],
];

export function CommandPalette({ onClose }: { onClose: () => void }) {
  const { text } = useI18n();
  const repositories = useRepositories();
  const pullRequests = usePullRequests();
  const runs = useRuns();
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  const items = useMemo<PaletteItem[]>(() => {
    const store = useUiStore.getState();
    const commands = viewCommands.map(([view, zh, en]) => ({
      id: `view:${view}`,
      label: text(zh, en),
      detail: text("打开页面", "Open view"),
      keywords: `${view} ${zh} ${en}`,
      run: () => store.setActiveView(view),
    }));
    const repositoryItems = (repositories.data?.items ?? []).map((repository) => ({
      id: `repository:${repository.id}`,
      label: repository.full_name,
      detail: text("打开仓库", "Open repository"),
      keywords: `${repository.full_name} repository repo`,
      run: () => store.selectRepository(repository.id),
    }));
    const pullRequestItems = (pullRequests.data?.items ?? []).map((pullRequest) => ({
      id: `pr:${pullRequest.id}`,
      label: `#${pullRequest.number} · ${pullRequest.title}`,
      detail: text("打开 Pull Request", "Open Pull Request"),
      keywords: `${pullRequest.title} ${pullRequest.author ?? ""} pr pull request`,
      run: () => store.selectPullRequest(pullRequest.id, pullRequest.repository_id),
    }));
    const runItems = (runs.data?.items ?? []).map((run) => ({
      id: `run:${run.id}`,
      label: run.current_node ?? run.workflow_version ?? run.id,
      detail: `${text("打开 Agent Run", "Open Agent Run")} · ${run.status}`,
      keywords: `${run.id} ${run.status} ${run.model_profile ?? ""} agent run`,
      run: () => store.selectRun(run.id),
    }));
    return [...commands, ...repositoryItems, ...pullRequestItems, ...runItems];
  }, [pullRequests.data?.items, repositories.data?.items, runs.data?.items, text]);

  const visible = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return items.filter((item) => !needle || `${item.label} ${item.keywords}`.toLocaleLowerCase().includes(needle)).slice(0, 40);
  }, [items, query]);

  useEffect(() => setActiveIndex(0), [query]);

  function choose(item: PaletteItem | undefined) {
    if (!item) return;
    item.run();
    onClose();
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => Math.min(index + 1, Math.max(visible.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(visible[activeIndex]);
    } else if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    }
  }

  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="command-palette" role="dialog" aria-modal="true" aria-label={text("命令面板", "Command palette")}><div className="command-search"><span aria-hidden="true">⌘K</span><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={onKeyDown} placeholder={text("搜索页面、仓库、PR 或 Run…", "Search views, repositories, PRs, or runs…")} aria-controls="command-palette-results" /></div><div id="command-palette-results" className="command-results" role="listbox">{visible.map((item, index) => <button key={item.id} type="button" role="option" aria-selected={index === activeIndex} className={index === activeIndex ? "command-result command-result-active" : "command-result"} onMouseEnter={() => setActiveIndex(index)} onClick={() => choose(item)}><strong>{item.label}</strong><small>{item.detail}</small></button>)}{visible.length === 0 ? <p className="field-note">{text("没有匹配结果。", "No matching results.")}</p> : null}</div><footer><span>↑↓ {text("选择", "select")}</span><span>↵ {text("打开", "open")}</span><span>Esc {text("关闭", "close")}</span></footer></section></div>;
}
