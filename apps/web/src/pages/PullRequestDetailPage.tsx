import { useEffect, useState } from "react";
import { DiffEditor, Editor, loader } from "@monaco-editor/react";
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
  usePullRequestChecks,
  usePullRequestCommits,
  usePullRequestDiff,
  usePullRequestFiles,
  usePullRequestGraph,
  usePullRequestTour,
  useRepositories,
  useRun,
  useRuns,
  useSyncRepository,
} from "../api/queries";
import { ErrorState, LoadingState } from "../components/RequestState";
import type { HostBridge } from "../host/hostBridge";
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

export function PullRequestDetailPage({ host }: { host: HostBridge }) {
  const { text } = useI18n();
  const pullRequestId = useUiStore((state) => state.selectedPullRequestId);
  const selectedDiffPath = useUiStore((state) => state.selectedDiffPath);
  const selectedRunId = useUiStore((state) => state.selectedRunId);
  const selectDiffPath = useUiStore((state) => state.selectDiffPath);
  const selectRun = useUiStore((state) => state.selectRun);
  const setActiveView = useUiStore((state) => state.setActiveView);
  const [tab, setTab] = useState<DetailTab>("overview");
  const [targetLine, setTargetLine] = useState<number | null>(null);
  const repositories = useRepositories();
  const pullRequest = usePullRequest(pullRequestId ?? undefined);
  const diff = usePullRequestDiff(pullRequestId ?? undefined, selectedDiffPath ?? undefined);
  const checks = usePullRequestChecks(pullRequestId ?? undefined);
  const commits = usePullRequestCommits(pullRequestId ?? undefined);
  const fileDetails = usePullRequestFiles(pullRequestId ?? undefined);
  const reviewMap = usePullRequestGraph(pullRequestId ?? undefined);
  const tour = usePullRequestTour(pullRequestId ?? undefined);
  const runs = useRuns(pullRequestId ?? undefined);
  const effectiveRunId = selectedRunId ?? runs.data?.items[0]?.id;
  const run = useRun(effectiveRunId);
  const findings = useFindings(effectiveRunId);
  const evidence = useEvidence(effectiveRunId);
  const analyze = useAnalyzePullRequest();
  const syncRepository = useSyncRepository();

  function jumpToPath(path: string | null, line?: number | null) {
    if (!path) return;
    selectDiffPath(path);
    setTargetLine(line ?? null);
    setTab("files");
  }

  if (!pullRequestId) {
    return <div className="honest-empty-state"><div className="empty-mark">PR</div><div><h2>{text("未选择 Pull Request", "No Pull Request selected")}</h2><p>{text("从 PR Inbox 选择一条真实同步记录。", "Select a real synchronized record from PR Inbox.")}</p></div></div>;
  }
  if (pullRequest.isPending) return <LoadingState label={text("正在读取 PR 详情…", "Reading PR details…")} />;
  if (pullRequest.isError) return <ErrorState title={text("PR 详情不可用", "PR details unavailable")} message={errorMessage(pullRequest.error)} onRetry={() => void pullRequest.refetch()} />;

  const current = pullRequest.data;
  const repository = repositories.data?.items.find((item) => item.id === current.repository_id);
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
      {tab === "files" ? <DiffPanel query={diff} selectedPath={selectedDiffPath} onSelectPath={(path) => { selectDiffPath(path); setTargetLine(null); }} targetLine={targetLine} findings={findings.data ?? []} evidence={evidence.data ?? []} fileDetails={fileDetails.data ?? []} pullRequestUrl={current.url} workspace={repository?.local_path ?? null} host={host} /> : null}
      {tab === "map" ? <ReviewMapPanel query={reviewMap} onSelectPath={jumpToPath} /> : null}
      {tab === "tour" ? <TourPanel query={tour} onSelectPath={jumpToPath} /> : null}
      {tab === "findings" ? <FindingsPanel query={findings} onSelectPath={jumpToPath} /> : null}
      {tab === "evidence" ? <EvidencePanel query={evidence} onSelectPath={jumpToPath} /> : null}
      {tab === "trace" ? <TracePanel query={run} onOpenRun={() => effectiveRunId && selectRun(effectiveRunId)} /> : null}
      {tab === "checks" ? <ChecksPanel query={checks} syncPending={syncRepository.isPending} syncError={syncRepository.error} onRefresh={() => syncRepository.mutate(current.repository_id)} /> : null}
      {tab === "history" ? <HistoryPanel pullRequest={current} runs={runs.data?.items ?? []} commits={commits.data ?? []} /> : null}
    </div>
  );
}

function Overview({ current, runs }: { current: ReturnType<typeof usePullRequest>["data"] & {}; runs: NonNullable<ReturnType<typeof useRuns>["data"]>["items"] }) {
  const { text } = useI18n();
  const latest = runs[0];
  return (
    <section className="panel">
      <div className="metric-cards">
        <div><span>{text("分析状态", "Analysis status")}</span><strong>{current.analysis_status}</strong></div>
        <div><span>Checks</span><strong>{current.checks_status}</strong></div>
        <div><span>{text("风险", "Risk")}</span><strong>{current.risk_level ? `${current.risk_level} · ${current.risk_score ?? 0}` : text("尚无结论", "No conclusion")}</strong></div>
        <div><span>{text("分支", "Branches")}</span><strong className="mono">{current.head_ref ?? text("未记录", "not recorded")} → {current.base_ref ?? text("未记录", "not recorded")}</strong></div>
        <div><span>Head SHA</span><strong className="mono">{current.head_sha?.slice(0, 12) ?? text("未记录", "Not recorded")}</strong></div>
        <div><span>Base SHA</span><strong className="mono">{current.base_sha?.slice(0, 12) ?? text("未记录", "Not recorded")}</strong></div>
        <div><span>{text("最近模型", "Latest model")}</span><strong>{current.latest_model_profile ?? latest?.model_profile ?? text("尚未运行", "Not run")}</strong></div>
        <div><span>{text("索引版本", "Index version")}</span><strong className="mono">{latest?.index_version?.slice(0, 12) ?? text("未记录", "Not recorded")}</strong></div>
        <div><span>{text("模型上下文", "Model context")}</span><strong>{latest?.context_scope ?? text("尚未运行", "Not run")}</strong></div>
        <div><span>{text("耗时 / Token", "Duration / tokens")}</span><strong>{latest ? `${latest.latency_ms} ms · ${latest.input_tokens + latest.output_tokens}` : text("尚未运行", "Not run")}</strong></div>
      </div>
      {latest?.error_message ? <p className="inline-error">{latest.error_code}: {latest.error_message}</p> : null}
      {current.conclusion_summary ? (
        <div className="review-summary">
          <h3>{text("结论摘要", "Review summary")}</h3>
          <p>{current.conclusion_summary}</p>
          <dl className="metadata-grid">
            <div><dt>{text("影响范围", "Impact scope")}</dt><dd>{current.impact_paths_json.length ? current.impact_paths_json.join(" · ") : text("未识别到有证据支持的影响路径", "No evidence-backed impact paths identified")}</dd></div>
            <div><dt>{text("推荐审查顺序", "Recommended review order")}</dt><dd>{current.recommended_review_order_json.length ? current.recommended_review_order_json.join(" → ") : text("没有可验证的推荐顺序", "No verifiable review order")}</dd></div>
          </dl>
        </div>
      ) : null}
      <p className="field-note">{text("结论摘要和推荐顺序只在真实 Agent Run 成功持久化后显示；静态 Change Tour 位于独立标签。", "Conclusions and recommendations appear only after a real Agent Run is persisted successfully; the static Change Tour has its own tab.")}</p>
    </section>
  );
}

function ChecksPanel({ query, syncPending, syncError, onRefresh }: { query: ReturnType<typeof usePullRequestChecks>; syncPending: boolean; syncError: unknown; onRefresh: () => void }) {
  const { locale, text } = useI18n();
  if (query.isPending) return <LoadingState label={text("正在读取 Check Run 快照…", "Reading Check Run snapshots…")} />;
  if (query.isError) return <ErrorState title={text("Checks 不可用", "Checks unavailable")} message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  return <section className="panel"><div className="section-heading"><div><span className="eyebrow">GITHUB CHECK RUNS · {query.data.aggregate_status}</span><h2>Checks</h2></div><button className="button button-secondary button-small" type="button" disabled={syncPending} onClick={onRefresh}>{syncPending ? text("刷新中…", "Refreshing…") : text("从 GitHub 刷新", "Refresh from GitHub")}</button></div>{syncError ? <p className="inline-error">{text("刷新失败", "Refresh failed")}: {errorMessage(syncError)}</p> : null}{query.data.items.length === 0 ? <div className="honest-empty-state"><div className="empty-mark">CI</div><div><h2>{text("当前 Head 没有 Check Run", "No Check Runs for this head")}</h2><p>{text("这是 GitHub 返回并持久化的空结果，不代表检查自动通过。", "This is the empty result returned by GitHub and persisted by TraceGate; it does not mean checks passed.")}</p></div></div> : <div className="check-list">{query.data.items.map((check) => <article className="check-card" key={check.id}><div><span className={`pill pill-${check.conclusion ?? check.status}`}>{check.status}</span><strong>{check.name}</strong></div><p>{check.app_name ?? "GitHub"} · {check.conclusion ?? text("尚无结论", "No conclusion")}</p><small>{check.completed_at ? new Date(check.completed_at).toLocaleString(locale) : text("仍在运行或未记录完成时间", "Still running or completion time unavailable")}</small>{check.details_url ? <a className="text-button" href={check.details_url} target="_blank" rel="noreferrer">{text("打开检查详情", "Open check details")}</a> : null}</article>)}</div>}<p className="field-note">{text("快照时间", "Snapshot time")}: {query.data.synced_at ? new Date(query.data.synced_at).toLocaleString(locale) : text("尚未同步", "Not synchronized")}</p></section>;
}

function DiffPanel({ query, selectedPath, onSelectPath, targetLine, findings, evidence, fileDetails, pullRequestUrl, workspace, host }: {
  query: ReturnType<typeof usePullRequestDiff>;
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
  targetLine: number | null;
  findings: NonNullable<ReturnType<typeof useFindings>["data"]>;
  evidence: NonNullable<ReturnType<typeof useEvidence>["data"]>;
  fileDetails: NonNullable<ReturnType<typeof usePullRequestFiles>["data"]>;
  pullRequestUrl: string;
  workspace: string | null;
  host: HostBridge;
}) {
  const { text } = useI18n();
  const [version, setVersion] = useState<"diff" | "base" | "head">("diff");
  const [editor, setEditor] = useState<monaco.editor.IStandaloneDiffEditor | null>(null);
  const data = query.data;
  const path = data?.selected_path ?? selectedPath;
  const pathFindings = findings.filter((item) => item.file_path === path && item.line_start !== null);
  const pathEvidence = evidence.filter((item) => item.file_path === path);

  useEffect(() => {
    if (!editor || version !== "diff") return;
    const modified = editor.getModifiedEditor();
    const decorations = [
      ...pathFindings.map((finding) => ({
        range: new monaco.Range(finding.line_start ?? 1, 1, finding.line_end ?? finding.line_start ?? 1, 1),
        options: {
          isWholeLine: true,
          className: `monaco-finding-line severity-${finding.severity}`,
          glyphMarginClassName: "monaco-finding-glyph",
          glyphMarginHoverMessage: { value: `**Finding · ${finding.severity}**\n\n${finding.title}` },
          overviewRuler: { color: "#ef5b67", position: monaco.editor.OverviewRulerLane.Right },
        },
      })),
      ...pathEvidence.map((item) => {
        const rawLine = item.payload_json.line;
        const line = typeof rawLine === "number" && Number.isInteger(rawLine) && rawLine > 0 ? rawLine : 1;
        return {
          range: new monaco.Range(line, 1, line, 1),
          options: {
            isWholeLine: true,
            className: "monaco-evidence-line",
            glyphMarginClassName: "monaco-evidence-glyph",
            glyphMarginHoverMessage: { value: `**Evidence · ${item.source_type}**\n\n${item.content_hash}` },
            overviewRuler: { color: "#4ea1ff", position: monaco.editor.OverviewRulerLane.Left },
          },
        };
      }),
    ];
    const collection = modified.createDecorationsCollection(decorations);
    if (targetLine && targetLine > 0) {
      modified.revealLineInCenter(targetLine);
      modified.setPosition({ lineNumber: targetLine, column: 1 });
      modified.focus();
    }
    return () => collection.clear();
  }, [editor, pathEvidence, pathFindings, targetLine, version]);

  if (query.isError) return <ErrorState title={text("Diff 不可用", "Diff unavailable")} message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  if (query.isPending || !data) return <LoadingState label={text("正在读取真实 Git diff…", "Reading real Git diff…")} />;
  const editorOptions: monaco.editor.IStandaloneEditorConstructionOptions = { readOnly: true, minimap: { enabled: true }, automaticLayout: true, glyphMargin: true };
  return <section className="diff-layout"><aside className="file-tree"><span className="eyebrow">CHANGED FILES</span>{data.changed_files.map((file) => { const detail = fileDetails.find((item) => item.path === file.path); return <button key={file.path} className={path === file.path ? "file-active" : ""} type="button" onClick={() => onSelectPath(file.path)}><span>{file.status}</span><span>{file.path}{detail ? <small>+{detail.additions} / −{detail.deletions} · {detail.hunks.length} hunks</small> : null}</span></button>; })}</aside><div className="diff-workspace"><div className="diff-toolbar"><strong>{path ?? text("没有变更文件", "No changed files")}</strong><div className="action-row compact"><div className="segmented-control" aria-label={text("版本视图", "Version view")}>{(["diff", "base", "head"] as const).map((value) => <button className={version === value ? "segment-active" : ""} key={value} type="button" onClick={() => setVersion(value)}>{value === "diff" ? "Diff" : value === "base" ? "Base" : "Head"}</button>)}</div>{path ? <button className="text-button" type="button" onClick={() => void navigator.clipboard.writeText(path)}>{text("复制路径", "Copy path")}</button> : null}<a className="text-button" href={`${pullRequestUrl}/files`} target="_blank" rel="noreferrer">GitHub</a><button className="text-button" type="button" disabled={!path || !workspace || !host.openWorkspaceFile} onClick={() => path && workspace && void host.openWorkspaceFile?.(workspace, path, targetLine ?? undefined)}>VS Code</button></div></div>{version === "diff" ? <DiffEditor height="620px" language={languageFor(path)} original={data.original ?? ""} modified={data.modified ?? ""} theme="vs-dark" onMount={setEditor} options={{ ...editorOptions, renderSideBySide: true, originalEditable: false }} /> : <Editor height="620px" language={languageFor(path)} value={version === "base" ? data.original ?? "" : data.modified ?? ""} theme="vs-dark" options={editorOptions} /> }<div className="diff-marker-legend"><span className="finding-marker">Finding {pathFindings.length}</span><span className="evidence-marker">Evidence {pathEvidence.length}</span><span>{text("缺少精确行号的 Evidence 标在第 1 行，并在悬停中明确来源。", "Evidence without an exact line is marked on line 1 and identified by source on hover.")}</span></div></div></section>;
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
  return <section className="panel"><p className={query.data.complete ? "inline-success" : "blocker-note"}>{query.data.message}</p><ol className="tour-list">{query.data.steps.map((step) => <li key={step.sequence}><button type="button" onClick={() => onSelectPath(step.files[0] ?? null)}><span>{String(step.sequence).padStart(2, "0")}</span><div><strong>{step.title}</strong><small>{step.files.join(", ")} · confidence {step.confidence}{step.prerequisite_step ? ` · after ${step.prerequisite_step}` : ""}</small><p>{step.purpose}</p>{step.risk ? <em>{text("风险", "Risk")}: {step.risk}</em> : null}<dl className="tour-metadata"><div><dt>{text("相关符号", "Symbols")}</dt><dd>{step.symbols.length ? step.symbols.join(" · ") : text("静态索引未解析出相关符号", "No related symbol resolved by the static index")}</dd></div><div><dt>Evidence</dt><dd>{step.evidence_ids.length ? step.evidence_ids.join(" · ") : text("尚无 Agent Evidence", "No Agent Evidence yet")}</dd></div><div><dt>{text("建议检查点", "Checkpoints")}</dt><dd><ul>{step.checkpoints.map((checkpoint) => <li key={checkpoint}>{checkpoint}</li>)}</ul></dd></div></dl></div></button></li>)}</ol></section>;
}

function FindingsPanel({ query, onSelectPath }: { query: ReturnType<typeof useFindings>; onSelectPath: (path: string | null, line?: number | null) => void }) {
  const { text } = useI18n();
  if (query.isPending) return <LoadingState label={text("正在读取 Findings…", "Reading Findings…")} />;
  if (query.isError) return <ErrorState title={text("Findings 不可用", "Findings unavailable")} message={errorMessage(query.error)} />;
  if (!query.data.length) return <div className="honest-empty-state"><div className="empty-mark">F</div><div><h2>{text("当前 Run 没有 Finding", "This run has no Findings")}</h2><p>{text("这表示后端未持久化 Finding，不代表代码自动安全。", "This means the backend persisted no Finding; it does not mean the code is automatically safe.")}</p></div></div>;
  return <div className="finding-list">{query.data.map((finding) => <article key={finding.id} className={`finding-card severity-${finding.severity}`}><div><span className="pill">{finding.severity} · {Math.round(finding.confidence * 100)}%</span><span className="mono">{finding.verifier_status}</span></div><h3>{finding.title}</h3><p>{finding.message}</p><button className="text-button" type="button" disabled={!finding.file_path} onClick={() => onSelectPath(finding.file_path, finding.line_start)}>{finding.file_path ? `${finding.file_path}:${finding.line_start ?? "?"}` : text("没有可跳转的源码位置", "No source location to open")}</button><small>commit {finding.commit_sha?.slice(0, 12) ?? text("未记录", "not recorded")} · evidence {finding.evidence_ids_json.length}</small></article>)}</div>;
}

function EvidencePanel({ query, onSelectPath }: { query: ReturnType<typeof useEvidence>; onSelectPath: (path: string | null, line?: number | null) => void }) {
  const { text } = useI18n();
  if (query.isPending) return <LoadingState label={text("正在读取 Evidence…", "Reading Evidence…")} />;
  if (query.isError) return <ErrorState title={text("Evidence 不可用", "Evidence unavailable")} message={errorMessage(query.error)} />;
  if (!query.data.length) return <div className="honest-empty-state"><div className="empty-mark">E</div><div><h2>{text("当前 Run 没有 Evidence", "This run has no Evidence")}</h2><p>{text("TraceGate 不会补造文件、行号或搜索结果。", "TraceGate never invents files, line numbers, or search results.")}</p></div></div>;
  return <div className="evidence-list">{query.data.map((item) => <article className="evidence-card" key={item.id}><span className="eyebrow">{item.source_type}</span><h3>{item.file_path ?? item.source_uri}</h3><p className="mono">{item.content_hash}</p><button className="text-button" type="button" disabled={!item.file_path} onClick={() => onSelectPath(item.file_path, typeof item.payload_json.line === "number" ? item.payload_json.line : null)}>{text("打开 Diff", "Open Diff")}</button><details><summary>{text("结构化载荷", "Structured payload")}</summary><pre>{JSON.stringify(item.payload_json, null, 2)}</pre></details></article>)}</div>;
}

function TracePanel({ query, onOpenRun }: { query: ReturnType<typeof useRun>; onOpenRun: () => void }) {
  const { text } = useI18n();
  if (query.isPending) return <LoadingState label={text("正在读取 Agent Trace…", "Reading Agent Trace…")} />;
  if (query.isError) return <ErrorState title={text("Agent Trace 不可用", "Agent Trace unavailable")} message={errorMessage(query.error)} />;
  if (!query.data) return <div className="honest-empty-state"><div className="empty-mark">RUN</div><div><h2>{text("尚无 Agent Run", "No Agent Run")}</h2><p>{text("配置真实模型并启动分析后，节点与工具调用会持久化到这里。", "After a real model is configured and analysis starts, nodes and tool calls are persisted here.")}</p></div></div>;
  return <section className="panel"><div className="section-heading"><div><span className="eyebrow">{query.data.status}</span><h2>{query.data.workflow_version}</h2></div><button className="button button-secondary button-small" type="button" onClick={onOpenRun}>{text("打开完整 Run", "Open full run")}</button></div><ol className="trace-timeline">{query.data.steps.map((step) => <li key={step.id} className={`trace-${step.status}`}><span>{step.sequence}</span><div><strong>{step.node}</strong><small>{step.duration_ms ?? 0} ms · {step.status}</small><p>{step.output_summary ?? step.error_message ?? text("尚无输出摘要", "No output summary")}</p>{query.data.tool_calls.filter((tool) => tool.agent_step_id === step.id).map((tool) => <details key={tool.id}><summary>{tool.tool_name} · {tool.status} · {tool.duration_ms ?? 0} ms</summary><pre>{tool.arguments_summary}\n{tool.output_summary}</pre></details>)}</div></li>)}</ol></section>;
}

function HistoryPanel({ pullRequest, runs, commits }: { pullRequest: NonNullable<ReturnType<typeof usePullRequest>["data"]>; runs: NonNullable<ReturnType<typeof useRuns>["data"]>["items"]; commits: NonNullable<ReturnType<typeof usePullRequestCommits>["data"]> }) {
  const { locale, text } = useI18n();
  return <section className="panel"><h3>{text("提交、同步与分析历史", "Commit, synchronization, and analysis history")}</h3><ol className="trace-timeline"><li><span>PR</span><div><strong>{text("GitHub 快照", "GitHub snapshot")}</strong><small>{pullRequest.updated_at_github ? new Date(pullRequest.updated_at_github).toLocaleString(locale) : text("未记录", "Not recorded")}</small><p>Head {pullRequest.head_sha ?? text("未记录", "not recorded")}</p></div></li>{commits.map((commit) => <li key={commit.id}><span>Git</span><div><strong>{commit.message.split("\n", 1)[0]}</strong><small>{commit.authored_at ? new Date(commit.authored_at).toLocaleString(locale) : text("时间未记录", "Time not recorded")} · {commit.author_login ?? commit.author_name ?? text("作者未记录", "Author not recorded")}</small><p className="mono">{commit.sha}</p>{commit.html_url ? <a className="text-button" href={commit.html_url} target="_blank" rel="noreferrer">GitHub</a> : null}</div></li>)}{runs.map((run) => <li key={run.id}><span>AI</span><div><strong>{run.status} · {run.model_profile ?? text("模型未记录", "model not recorded")}</strong><small>{new Date(run.created_at).toLocaleString(locale)}</small><p>{run.error_message ?? `${run.input_tokens + run.output_tokens} tokens · ${run.latency_ms} ms`}</p></div></li>)}</ol></section>;
}
