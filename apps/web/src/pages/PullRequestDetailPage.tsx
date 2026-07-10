import { useState } from "react";
import { DiffEditor, loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api.js";
import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import "monaco-editor/esm/vs/basic-languages/javascript/javascript.contribution";
import "monaco-editor/esm/vs/basic-languages/java/java.contribution";
import "monaco-editor/esm/vs/basic-languages/markdown/markdown.contribution";
import "monaco-editor/esm/vs/basic-languages/python/python.contribution";
import "monaco-editor/esm/vs/basic-languages/rust/rust.contribution";
import "monaco-editor/esm/vs/basic-languages/typescript/typescript.contribution";
import "monaco-editor/esm/vs/basic-languages/yaml/yaml.contribution";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";

import {
  useAnalyzePullRequest,
  useEvidence,
  useFindings,
  usePullRequest,
  usePullRequestDiff,
  usePullRequestGraph,
  usePullRequestTour,
  useRun,
  useRuns,
} from "../api/queries";
import { ErrorState, LoadingState } from "../components/RequestState";
import { errorMessage } from "../lib/errors";
import { useUiStore } from "../store/uiStore";
import { useI18n } from "../i18n";

self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
loader.config({ monaco });

type DetailTab = "overview" | "files" | "map" | "tour" | "findings" | "evidence" | "trace" | "checks" | "history";
const tabs: readonly [DetailTab, string][] = [
  ["overview", "Overview"], ["files", "Files & Diff"], ["map", "Review Map"], ["tour", "Change Tour"],
  ["findings", "Findings"], ["evidence", "Evidence"], ["trace", "Agent Trace"], ["checks", "Checks"], ["history", "History"],
];

function languageFor(path: string | null): string {
  const extension = path?.split(".").pop()?.toLocaleLowerCase();
  return ({ py: "python", ts: "typescript", tsx: "typescript", js: "javascript", jsx: "javascript", rs: "rust", java: "java", json: "json", md: "markdown", yml: "yaml", yaml: "yaml" } as Record<string, string>)[extension ?? ""] ?? "plaintext";
}

export function PullRequestDetailPage() {
  const { text } = useI18n();
  const pullRequestId = useUiStore((state) => state.selectedPullRequestId);
  const selectedDiffPath = useUiStore((state) => state.selectedDiffPath);
  const selectedRunId = useUiStore((state) => state.selectedRunId);
  const selectDiffPath = useUiStore((state) => state.selectDiffPath);
  const selectRun = useUiStore((state) => state.selectRun);
  const setActiveView = useUiStore((state) => state.setActiveView);
  const [tab, setTab] = useState<DetailTab>("overview");
  const pullRequest = usePullRequest(pullRequestId ?? undefined);
  const diff = usePullRequestDiff(pullRequestId ?? undefined, selectedDiffPath ?? undefined);
  const reviewMap = usePullRequestGraph(pullRequestId ?? undefined);
  const tour = usePullRequestTour(pullRequestId ?? undefined);
  const runs = useRuns(pullRequestId ?? undefined);
  const effectiveRunId = selectedRunId ?? runs.data?.items[0]?.id;
  const run = useRun(effectiveRunId);
  const findings = useFindings(effectiveRunId);
  const evidence = useEvidence(effectiveRunId);
  const analyze = useAnalyzePullRequest();

  function jumpToPath(path: string | null) {
    if (!path) return;
    selectDiffPath(path);
    setTab("files");
  }

  if (!pullRequestId) {
    return <div className="honest-empty-state"><div className="empty-mark">PR</div><div><h2>{text("未选择 Pull Request", "No Pull Request selected")}</h2><p>{text("从 PR Inbox 选择一条真实同步记录。", "Select a real synchronized record from PR Inbox.")}</p></div></div>;
  }
  if (pullRequest.isPending) return <LoadingState label={text("正在读取 PR 详情…", "Reading PR details…")} />;
  if (pullRequest.isError) return <ErrorState title={text("PR 详情不可用", "PR details unavailable")} message={errorMessage(pullRequest.error)} onRetry={() => void pullRequest.refetch()} />;

  const current = pullRequest.data;
  return (
    <div className="page-stack pr-detail-page">
      <header className="detail-hero">
        <div><button className="text-button" type="button" onClick={() => setActiveView("pull-requests")}>← {text("返回 Inbox", "Back to Inbox")}</button><span className="eyebrow">PR #{current.number} · {current.state}</span><h2>{current.title}</h2><p>{current.author ?? text("未知作者", "Unknown author")} · {current.changed_files} files · <span className="positive">+{current.additions}</span> / <span className="negative">−{current.deletions}</span></p></div>
        <div className="detail-actions"><a className="button button-secondary" href={current.url} target="_blank" rel="noreferrer">{text("在 GitHub 打开", "Open on GitHub")}</a><button className="button button-primary" type="button" disabled={analyze.isPending} onClick={() => analyze.mutate({ pullRequestId: current.id })}>{analyze.isPending ? text("启动中…", "Starting…") : text("启动 Agent 分析", "Start Agent analysis")}</button></div>
      </header>
      {analyze.isError ? <p className="inline-error" role="alert">{text("分析未启动", "Analysis did not start")}: {errorMessage(analyze.error)}</p> : null}
      {analyze.data?.reused ? <p className="inline-success">{text("相同 Head SHA、索引、Prompt 和模型已有运行，已复用该 Run。", "An existing run with the same Head SHA, index, prompt, and model was reused.")}</p> : null}
      <div className="tab-list" role="tablist" aria-label={text("PR 详情视图", "PR detail views")}>{tabs.map(([id, label]) => <button key={id} className={tab === id ? "tab-active" : ""} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)}>{label}</button>)}</div>

      {tab === "overview" ? <Overview current={current} runs={runs.data?.items ?? []} /> : null}
      {tab === "files" ? <DiffPanel query={diff} selectedPath={selectedDiffPath} onSelectPath={selectDiffPath} /> : null}
      {tab === "map" ? <ReviewMapPanel query={reviewMap} onSelectPath={jumpToPath} /> : null}
      {tab === "tour" ? <TourPanel query={tour} onSelectPath={jumpToPath} /> : null}
      {tab === "findings" ? <FindingsPanel query={findings} onSelectPath={jumpToPath} /> : null}
      {tab === "evidence" ? <EvidencePanel query={evidence} onSelectPath={jumpToPath} /> : null}
      {tab === "trace" ? <TracePanel query={run} onOpenRun={() => effectiveRunId && selectRun(effectiveRunId)} /> : null}
      {tab === "checks" ? <div className="honest-empty-state"><div className="empty-mark">CI</div><div><h2>{text("Check Run 快照尚未持久化", "Check Run snapshots are not persisted yet")}</h2><p>{text("GitHub Provider 已实现真实 Check Runs 读取，但当前 PR 同步表尚未保存该响应，因此这里不会伪造绿色检查。", "GitHubProvider can read real Check Runs, but PR synchronization does not yet persist that response, so this view never fabricates green checks.")}</p></div></div> : null}
      {tab === "history" ? <HistoryPanel pullRequest={current} runs={runs.data?.items ?? []} /> : null}
    </div>
  );
}

function Overview({ current, runs }: { current: ReturnType<typeof usePullRequest>["data"] & {}; runs: NonNullable<ReturnType<typeof useRuns>["data"]>["items"] }) {
  const { text } = useI18n();
  const latest = runs[0];
  return <section className="panel"><div className="metric-cards"><div><span>{text("分析状态", "Analysis status")}</span><strong>{current.analysis_status}</strong></div><div><span>{text("风险", "Risk")}</span><strong>{latest?.status === "completed" ? text("查看 Findings", "View Findings") : text("尚无结论", "No conclusion")}</strong></div><div><span>Head SHA</span><strong className="mono">{current.head_sha?.slice(0, 12) ?? text("未记录", "Not recorded")}</strong></div><div><span>Base SHA</span><strong className="mono">{current.base_sha?.slice(0, 12) ?? text("未记录", "Not recorded")}</strong></div><div><span>{text("最近模型", "Latest model")}</span><strong>{latest?.model_profile ?? text("尚未运行", "Not run")}</strong></div><div><span>{text("耗时 / Token", "Duration / tokens")}</span><strong>{latest ? `${latest.latency_ms} ms · ${latest.input_tokens + latest.output_tokens}` : text("尚未运行", "Not run")}</strong></div></div>{latest?.error_message ? <p className="inline-error">{latest.error_code}: {latest.error_message}</p> : null}<p className="field-note">{text("结论摘要和推荐顺序只在真实 Agent Run 成功持久化后显示；静态 Change Tour 位于独立标签。", "Conclusions and recommendations appear only after a real Agent Run is persisted successfully; the static Change Tour has its own tab.")}</p></section>;
}

function DiffPanel({ query, selectedPath, onSelectPath }: { query: ReturnType<typeof usePullRequestDiff>; selectedPath: string | null; onSelectPath: (path: string) => void }) {
  const { text } = useI18n();
  if (query.isPending) return <LoadingState label={text("正在读取真实 Git diff…", "Reading real Git diff…")} />;
  if (query.isError) return <ErrorState title={text("Diff 不可用", "Diff unavailable")} message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  const path = query.data.selected_path ?? selectedPath;
  return <section className="diff-layout"><aside className="file-tree"><span className="eyebrow">CHANGED FILES</span>{query.data.changed_files.map((file) => <button key={file.path} className={path === file.path ? "file-active" : ""} type="button" onClick={() => onSelectPath(file.path)}><span>{file.status}</span>{file.path}</button>)}</aside><div className="diff-workspace"><div className="diff-toolbar"><strong>{path ?? text("没有变更文件", "No changed files")}</strong>{path ? <button className="text-button" type="button" onClick={() => void navigator.clipboard.writeText(path)}>{text("复制路径", "Copy path")}</button> : null}</div><DiffEditor height="620px" language={languageFor(path)} original={query.data.original ?? ""} modified={query.data.modified ?? ""} theme="vs-dark" options={{ readOnly: true, renderSideBySide: true, minimap: { enabled: true }, automaticLayout: true, originalEditable: false }} /></div></section>;
}

function ReviewMapPanel({ query, onSelectPath }: { query: ReturnType<typeof usePullRequestGraph>; onSelectPath: (path: string | null) => void }) {
  const { text } = useI18n();
  if (query.isPending) return <LoadingState label={text("正在构建 PR 影响图…", "Building PR impact graph…")} />;
  if (query.isError) return <ErrorState title={text("Review Map 不可用", "Review Map unavailable")} message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  const nodes: Node[] = query.data.nodes.slice(0, 300).map((node, index) => ({ id: node.id, position: { x: node.impact_depth * 280, y: (index % 25) * 82 }, data: { label: `${node.change_status ?? `L${node.impact_depth}`} · ${node.label}` }, className: `review-node impact-${node.impact_depth} risk-${node.risk ?? "none"}` }));
  const ids = new Set(nodes.map((node) => node.id));
  const edges: Edge[] = query.data.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)).map((edge) => ({ ...edge, label: edge.kind, className: edge.confirmed ? "map-edge-confirmed" : "map-edge-unconfirmed" }));
  const pathById = new Map(query.data.nodes.map((node) => [node.id, node.path]));
  return <section className="panel"><p className="map-message">{query.data.message}</p><div className="review-flow"><ReactFlow nodes={nodes} edges={edges} fitView onNodeDoubleClick={(_event, node) => onSelectPath(pathById.get(node.id) ?? null)}><Background /><MiniMap /><Controls /></ReactFlow></div><p className="field-note">{text("双击代码节点跳转 Diff。直接修改为 L0，一跳/二跳影响来自已确认静态关系；虚线表示未确认关系。", "Double-click a code node to open Diff. Direct changes are L0; one/two-hop impact comes from confirmed static relationships, while dashed edges are unconfirmed.")}</p></section>;
}

function TourPanel({ query, onSelectPath }: { query: ReturnType<typeof usePullRequestTour>; onSelectPath: (path: string | null) => void }) {
  const { text } = useI18n();
  if (query.isPending) return <LoadingState label={text("正在生成静态审查顺序…", "Generating static review order…")} />;
  if (query.isError) return <ErrorState title={text("Change Tour 不可用", "Change Tour unavailable")} message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  return <section className="panel"><p className={query.data.complete ? "inline-success" : "blocker-note"}>{query.data.message}</p><ol className="tour-list">{query.data.steps.map((step) => <li key={step.sequence}><button type="button" onClick={() => onSelectPath(step.files[0] ?? null)}><span>{String(step.sequence).padStart(2, "0")}</span><div><strong>{step.title}</strong><small>{step.files.join(", ")} · confidence {step.confidence}</small><p>{step.purpose}</p>{step.risk ? <em>{text("风险", "Risk")}: {step.risk}</em> : null}</div></button></li>)}</ol></section>;
}

function FindingsPanel({ query, onSelectPath }: { query: ReturnType<typeof useFindings>; onSelectPath: (path: string | null) => void }) {
  const { text } = useI18n();
  if (query.isPending) return <LoadingState label={text("正在读取 Findings…", "Reading Findings…")} />;
  if (query.isError) return <ErrorState title={text("Findings 不可用", "Findings unavailable")} message={errorMessage(query.error)} />;
  if (!query.data.length) return <div className="honest-empty-state"><div className="empty-mark">F</div><div><h2>{text("当前 Run 没有 Finding", "This run has no Findings")}</h2><p>{text("这表示后端未持久化 Finding，不代表代码自动安全。", "This means the backend persisted no Finding; it does not mean the code is automatically safe.")}</p></div></div>;
  return <div className="finding-list">{query.data.map((finding) => <article key={finding.id} className={`finding-card severity-${finding.severity}`}><div><span className="pill">{finding.severity} · {Math.round(finding.confidence * 100)}%</span><span className="mono">{finding.verifier_status}</span></div><h3>{finding.title}</h3><p>{finding.message}</p><button className="text-button" type="button" disabled={!finding.file_path} onClick={() => onSelectPath(finding.file_path)}>{finding.file_path ? `${finding.file_path}:${finding.line_start ?? "?"}` : text("没有可跳转的源码位置", "No source location to open")}</button><small>commit {finding.commit_sha?.slice(0, 12) ?? text("未记录", "not recorded")} · evidence {finding.evidence_ids_json.length}</small></article>)}</div>;
}

function EvidencePanel({ query, onSelectPath }: { query: ReturnType<typeof useEvidence>; onSelectPath: (path: string | null) => void }) {
  const { text } = useI18n();
  if (query.isPending) return <LoadingState label={text("正在读取 Evidence…", "Reading Evidence…")} />;
  if (query.isError) return <ErrorState title={text("Evidence 不可用", "Evidence unavailable")} message={errorMessage(query.error)} />;
  if (!query.data.length) return <div className="honest-empty-state"><div className="empty-mark">E</div><div><h2>{text("当前 Run 没有 Evidence", "This run has no Evidence")}</h2><p>{text("TraceGate 不会补造文件、行号或搜索结果。", "TraceGate never invents files, line numbers, or search results.")}</p></div></div>;
  return <div className="evidence-list">{query.data.map((item) => <article className="evidence-card" key={item.id}><span className="eyebrow">{item.source_type}</span><h3>{item.file_path ?? item.source_uri}</h3><p className="mono">{item.content_hash}</p><button className="text-button" type="button" disabled={!item.file_path} onClick={() => onSelectPath(item.file_path)}>{text("打开 Diff", "Open Diff")}</button><details><summary>{text("结构化载荷", "Structured payload")}</summary><pre>{JSON.stringify(item.payload_json, null, 2)}</pre></details></article>)}</div>;
}

function TracePanel({ query, onOpenRun }: { query: ReturnType<typeof useRun>; onOpenRun: () => void }) {
  const { text } = useI18n();
  if (query.isPending) return <LoadingState label={text("正在读取 Agent Trace…", "Reading Agent Trace…")} />;
  if (query.isError) return <ErrorState title={text("Agent Trace 不可用", "Agent Trace unavailable")} message={errorMessage(query.error)} />;
  if (!query.data) return <div className="honest-empty-state"><div className="empty-mark">RUN</div><div><h2>{text("尚无 Agent Run", "No Agent Run")}</h2><p>{text("配置真实模型并启动分析后，节点与工具调用会持久化到这里。", "After a real model is configured and analysis starts, nodes and tool calls are persisted here.")}</p></div></div>;
  return <section className="panel"><div className="section-heading"><div><span className="eyebrow">{query.data.status}</span><h2>{query.data.workflow_version}</h2></div><button className="button button-secondary button-small" type="button" onClick={onOpenRun}>{text("打开完整 Run", "Open full run")}</button></div><ol className="trace-timeline">{query.data.steps.map((step) => <li key={step.id} className={`trace-${step.status}`}><span>{step.sequence}</span><div><strong>{step.node}</strong><small>{step.duration_ms ?? 0} ms · {step.status}</small><p>{step.output_summary ?? step.error_message ?? text("尚无输出摘要", "No output summary")}</p>{query.data.tool_calls.filter((tool) => tool.agent_step_id === step.id).map((tool) => <details key={tool.id}><summary>{tool.tool_name} · {tool.status} · {tool.duration_ms ?? 0} ms</summary><pre>{tool.arguments_summary}\n{tool.output_summary}</pre></details>)}</div></li>)}</ol></section>;
}

function HistoryPanel({ pullRequest, runs }: { pullRequest: NonNullable<ReturnType<typeof usePullRequest>["data"]>; runs: NonNullable<ReturnType<typeof useRuns>["data"]>["items"] }) {
  const { locale, text } = useI18n();
  return <section className="panel"><h3>{text("同步与分析历史", "Synchronization and analysis history")}</h3><ol className="trace-timeline"><li><span>PR</span><div><strong>{text("GitHub 快照", "GitHub snapshot")}</strong><small>{pullRequest.updated_at_github ? new Date(pullRequest.updated_at_github).toLocaleString(locale) : text("未记录", "Not recorded")}</small><p>Head {pullRequest.head_sha ?? text("未记录", "not recorded")}</p></div></li>{runs.map((run) => <li key={run.id}><span>AI</span><div><strong>{run.status} · {run.model_profile ?? text("模型未记录", "model not recorded")}</strong><small>{new Date(run.created_at).toLocaleString(locale)}</small><p>{run.error_message ?? `${run.input_tokens + run.output_tokens} tokens · ${run.latency_ms} ms`}</p></div></li>)}</ol></section>;
}
