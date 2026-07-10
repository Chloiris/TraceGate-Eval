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
    return <div className="honest-empty-state"><div className="empty-mark">PR</div><div><h2>未选择 Pull Request</h2><p>从 PR Inbox 选择一条真实同步记录。</p></div></div>;
  }
  if (pullRequest.isPending) return <LoadingState label="正在读取 PR 详情…" />;
  if (pullRequest.isError) return <ErrorState title="PR 详情不可用" message={errorMessage(pullRequest.error)} onRetry={() => void pullRequest.refetch()} />;

  const current = pullRequest.data;
  return (
    <div className="page-stack pr-detail-page">
      <header className="detail-hero">
        <div><button className="text-button" type="button" onClick={() => setActiveView("pull-requests")}>← 返回 Inbox</button><span className="eyebrow">PR #{current.number} · {current.state}</span><h2>{current.title}</h2><p>{current.author ?? "未知作者"} · {current.changed_files} files · <span className="positive">+{current.additions}</span> / <span className="negative">−{current.deletions}</span></p></div>
        <div className="detail-actions"><a className="button button-secondary" href={current.url} target="_blank" rel="noreferrer">在 GitHub 打开</a><button className="button button-primary" type="button" disabled={analyze.isPending} onClick={() => analyze.mutate({ pullRequestId: current.id })}>{analyze.isPending ? "启动中…" : "启动 Agent 分析"}</button></div>
      </header>
      {analyze.isError ? <p className="inline-error" role="alert">分析未启动：{errorMessage(analyze.error)}</p> : null}
      {analyze.data?.reused ? <p className="inline-success">相同 Head SHA、索引、Prompt 和模型已有运行，已复用该 Run。</p> : null}
      <div className="tab-list" role="tablist" aria-label="PR 详情视图">{tabs.map(([id, label]) => <button key={id} className={tab === id ? "tab-active" : ""} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)}>{label}</button>)}</div>

      {tab === "overview" ? <Overview current={current} runs={runs.data?.items ?? []} /> : null}
      {tab === "files" ? <DiffPanel query={diff} selectedPath={selectedDiffPath} onSelectPath={selectDiffPath} /> : null}
      {tab === "map" ? <ReviewMapPanel query={reviewMap} onSelectPath={jumpToPath} /> : null}
      {tab === "tour" ? <TourPanel query={tour} onSelectPath={jumpToPath} /> : null}
      {tab === "findings" ? <FindingsPanel query={findings} onSelectPath={jumpToPath} /> : null}
      {tab === "evidence" ? <EvidencePanel query={evidence} onSelectPath={jumpToPath} /> : null}
      {tab === "trace" ? <TracePanel query={run} onOpenRun={() => effectiveRunId && selectRun(effectiveRunId)} /> : null}
      {tab === "checks" ? <div className="honest-empty-state"><div className="empty-mark">CI</div><div><h2>Check Run 快照尚未持久化</h2><p>GitHub Provider 已实现真实 Check Runs 读取，但当前 PR 同步表尚未保存该响应，因此这里不会伪造绿色检查。</p></div></div> : null}
      {tab === "history" ? <HistoryPanel pullRequest={current} runs={runs.data?.items ?? []} /> : null}
    </div>
  );
}

function Overview({ current, runs }: { current: ReturnType<typeof usePullRequest>["data"] & {}; runs: NonNullable<ReturnType<typeof useRuns>["data"]>["items"] }) {
  const latest = runs[0];
  return <section className="panel"><div className="metric-cards"><div><span>分析状态</span><strong>{current.analysis_status}</strong></div><div><span>风险</span><strong>{latest?.status === "completed" ? "查看 Findings" : "尚无结论"}</strong></div><div><span>Head SHA</span><strong className="mono">{current.head_sha?.slice(0, 12) ?? "未记录"}</strong></div><div><span>Base SHA</span><strong className="mono">{current.base_sha?.slice(0, 12) ?? "未记录"}</strong></div><div><span>最近模型</span><strong>{latest?.model_profile ?? "尚未运行"}</strong></div><div><span>耗时 / Token</span><strong>{latest ? `${latest.latency_ms} ms · ${latest.input_tokens + latest.output_tokens}` : "尚未运行"}</strong></div></div>{latest?.error_message ? <p className="inline-error">{latest.error_code}: {latest.error_message}</p> : null}<p className="field-note">结论摘要和推荐顺序只在真实 Agent Run 成功持久化后显示；静态 Change Tour 位于独立标签。</p></section>;
}

function DiffPanel({ query, selectedPath, onSelectPath }: { query: ReturnType<typeof usePullRequestDiff>; selectedPath: string | null; onSelectPath: (path: string) => void }) {
  if (query.isPending) return <LoadingState label="正在读取真实 Git diff…" />;
  if (query.isError) return <ErrorState title="Diff 不可用" message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  const path = query.data.selected_path ?? selectedPath;
  return <section className="diff-layout"><aside className="file-tree"><span className="eyebrow">CHANGED FILES</span>{query.data.changed_files.map((file) => <button key={file.path} className={path === file.path ? "file-active" : ""} type="button" onClick={() => onSelectPath(file.path)}><span>{file.status}</span>{file.path}</button>)}</aside><div className="diff-workspace"><div className="diff-toolbar"><strong>{path ?? "没有变更文件"}</strong>{path ? <button className="text-button" type="button" onClick={() => void navigator.clipboard.writeText(path)}>复制路径</button> : null}</div><DiffEditor height="620px" language={languageFor(path)} original={query.data.original ?? ""} modified={query.data.modified ?? ""} theme="vs-dark" options={{ readOnly: true, renderSideBySide: true, minimap: { enabled: true }, automaticLayout: true, originalEditable: false }} /></div></section>;
}

function ReviewMapPanel({ query, onSelectPath }: { query: ReturnType<typeof usePullRequestGraph>; onSelectPath: (path: string | null) => void }) {
  if (query.isPending) return <LoadingState label="正在构建 PR 影响图…" />;
  if (query.isError) return <ErrorState title="Review Map 不可用" message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  const nodes: Node[] = query.data.nodes.slice(0, 300).map((node, index) => ({ id: node.id, position: { x: node.impact_depth * 280, y: (index % 25) * 82 }, data: { label: `${node.change_status ?? `L${node.impact_depth}`} · ${node.label}` }, className: `review-node impact-${node.impact_depth} risk-${node.risk ?? "none"}` }));
  const ids = new Set(nodes.map((node) => node.id));
  const edges: Edge[] = query.data.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)).map((edge) => ({ ...edge, label: edge.kind, className: edge.confirmed ? "map-edge-confirmed" : "map-edge-unconfirmed" }));
  const pathById = new Map(query.data.nodes.map((node) => [node.id, node.path]));
  return <section className="panel"><p className="map-message">{query.data.message}</p><div className="review-flow"><ReactFlow nodes={nodes} edges={edges} fitView onNodeDoubleClick={(_event, node) => onSelectPath(pathById.get(node.id) ?? null)}><Background /><MiniMap /><Controls /></ReactFlow></div><p className="field-note">双击代码节点跳转 Diff。直接修改为 L0，一跳/二跳影响来自已确认静态关系；虚线表示未确认关系。</p></section>;
}

function TourPanel({ query, onSelectPath }: { query: ReturnType<typeof usePullRequestTour>; onSelectPath: (path: string | null) => void }) {
  if (query.isPending) return <LoadingState label="正在生成静态审查顺序…" />;
  if (query.isError) return <ErrorState title="Change Tour 不可用" message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  return <section className="panel"><p className={query.data.complete ? "inline-success" : "blocker-note"}>{query.data.message}</p><ol className="tour-list">{query.data.steps.map((step) => <li key={step.sequence}><button type="button" onClick={() => onSelectPath(step.files[0] ?? null)}><span>{String(step.sequence).padStart(2, "0")}</span><div><strong>{step.title}</strong><small>{step.files.join(", ")} · confidence {step.confidence}</small><p>{step.purpose}</p>{step.risk ? <em>风险：{step.risk}</em> : null}</div></button></li>)}</ol></section>;
}

function FindingsPanel({ query, onSelectPath }: { query: ReturnType<typeof useFindings>; onSelectPath: (path: string | null) => void }) {
  if (query.isPending) return <LoadingState label="正在读取 Findings…" />;
  if (query.isError) return <ErrorState title="Findings 不可用" message={errorMessage(query.error)} />;
  if (!query.data.length) return <div className="honest-empty-state"><div className="empty-mark">F</div><div><h2>当前 Run 没有 Finding</h2><p>这表示后端未持久化 Finding，不代表代码自动安全。</p></div></div>;
  return <div className="finding-list">{query.data.map((finding) => <article key={finding.id} className={`finding-card severity-${finding.severity}`}><div><span className="pill">{finding.severity} · {Math.round(finding.confidence * 100)}%</span><span className="mono">{finding.verifier_status}</span></div><h3>{finding.title}</h3><p>{finding.message}</p><button className="text-button" type="button" disabled={!finding.file_path} onClick={() => onSelectPath(finding.file_path)}>{finding.file_path ? `${finding.file_path}:${finding.line_start ?? "?"}` : "没有可跳转的源码位置"}</button><small>commit {finding.commit_sha?.slice(0, 12) ?? "未记录"} · evidence {finding.evidence_ids_json.length}</small></article>)}</div>;
}

function EvidencePanel({ query, onSelectPath }: { query: ReturnType<typeof useEvidence>; onSelectPath: (path: string | null) => void }) {
  if (query.isPending) return <LoadingState label="正在读取 Evidence…" />;
  if (query.isError) return <ErrorState title="Evidence 不可用" message={errorMessage(query.error)} />;
  if (!query.data.length) return <div className="honest-empty-state"><div className="empty-mark">E</div><div><h2>当前 Run 没有 Evidence</h2><p>TraceGate 不会补造文件、行号或搜索结果。</p></div></div>;
  return <div className="evidence-list">{query.data.map((item) => <article className="evidence-card" key={item.id}><span className="eyebrow">{item.source_type}</span><h3>{item.file_path ?? item.source_uri}</h3><p className="mono">{item.content_hash}</p><button className="text-button" type="button" disabled={!item.file_path} onClick={() => onSelectPath(item.file_path)}>打开 Diff</button><details><summary>结构化载荷</summary><pre>{JSON.stringify(item.payload_json, null, 2)}</pre></details></article>)}</div>;
}

function TracePanel({ query, onOpenRun }: { query: ReturnType<typeof useRun>; onOpenRun: () => void }) {
  if (query.isPending) return <LoadingState label="正在读取 Agent Trace…" />;
  if (query.isError) return <ErrorState title="Agent Trace 不可用" message={errorMessage(query.error)} />;
  if (!query.data) return <div className="honest-empty-state"><div className="empty-mark">RUN</div><div><h2>尚无 Agent Run</h2><p>配置真实模型并启动分析后，节点与工具调用会持久化到这里。</p></div></div>;
  return <section className="panel"><div className="section-heading"><div><span className="eyebrow">{query.data.status}</span><h2>{query.data.workflow_version}</h2></div><button className="button button-secondary button-small" type="button" onClick={onOpenRun}>打开完整 Run</button></div><ol className="trace-timeline">{query.data.steps.map((step) => <li key={step.id} className={`trace-${step.status}`}><span>{step.sequence}</span><div><strong>{step.node}</strong><small>{step.duration_ms ?? 0} ms · {step.status}</small><p>{step.output_summary ?? step.error_message ?? "尚无输出摘要"}</p>{query.data.tool_calls.filter((tool) => tool.agent_step_id === step.id).map((tool) => <details key={tool.id}><summary>{tool.tool_name} · {tool.status} · {tool.duration_ms ?? 0} ms</summary><pre>{tool.arguments_summary}\n{tool.output_summary}</pre></details>)}</div></li>)}</ol></section>;
}

function HistoryPanel({ pullRequest, runs }: { pullRequest: NonNullable<ReturnType<typeof usePullRequest>["data"]>; runs: NonNullable<ReturnType<typeof useRuns>["data"]>["items"] }) {
  return <section className="panel"><h3>同步与分析历史</h3><ol className="trace-timeline"><li><span>PR</span><div><strong>GitHub 快照</strong><small>{pullRequest.updated_at_github ? new Date(pullRequest.updated_at_github).toLocaleString("zh-CN") : "未记录"}</small><p>Head {pullRequest.head_sha ?? "未记录"}</p></div></li>{runs.map((run) => <li key={run.id}><span>AI</span><div><strong>{run.status} · {run.model_profile ?? "模型未记录"}</strong><small>{new Date(run.created_at).toLocaleString("zh-CN")}</small><p>{run.error_message ?? `${run.input_tokens + run.output_tokens} tokens · ${run.latency_ms} ms`}</p></div></li>)}</ol></section>;
}
