import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useApiClient } from "../api/clientContext";
import { useCancelRun, useEvidence, useFindings, useRetryRun, useRun, useRuns } from "../api/queries";
import { ErrorState, LoadingState } from "../components/RequestState";
import { errorMessage } from "../lib/errors";
import { useUiStore } from "../store/uiStore";

const AgentEvidenceGraph = lazy(async () => {
  const module = await import("../components/AgentEvidenceGraph");
  return { default: module.AgentEvidenceGraph };
});

function download(name: string, content: string, type: string) {
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(new Blob([content], { type }));
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(anchor.href);
}

export function AgentRunsPage() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  const runs = useRuns();
  const storedRunId = useUiStore((state) => state.selectedRunId);
  const selectRun = useUiStore((state) => state.selectRun);
  const effectiveRunId = storedRunId ?? runs.data?.items[0]?.id;
  const detail = useRun(effectiveRunId);
  const findings = useFindings(effectiveRunId);
  const evidence = useEvidence(effectiveRunId);
  const cancel = useCancelRun();
  const retry = useRetryRun();
  const [streamState, setStreamState] = useState<"idle" | "connected" | "complete" | "error">("idle");

  useEffect(() => {
    if (!effectiveRunId || !detail.data || !["queued", "running"].includes(detail.data.status)) {
      setStreamState(detail.data ? "complete" : "idle");
      return;
    }
    const controller = new AbortController();
    setStreamState("connected");
    void client.streamRunEvents(effectiveRunId, (event) => {
      void queryClient.invalidateQueries({ queryKey: ["run", effectiveRunId] });
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      if (event.type === "run") setStreamState("complete");
    }, controller.signal).catch((error: unknown) => {
      if (!(error instanceof DOMException && error.name === "AbortError")) setStreamState("error");
    });
    return () => controller.abort();
  }, [client, detail.data, effectiveRunId, queryClient]);

  const markdown = useMemo(() => {
    if (!detail.data) return "";
    const lines = [`# TraceGate Agent Run ${detail.data.id}`, "", `- Status: ${detail.data.status}`, `- Head SHA: ${detail.data.head_sha ?? "not recorded"}`, `- Model: ${detail.data.model_profile ?? "not recorded"}`, "", "## Steps", ""];
    for (const step of detail.data.steps) lines.push(`- ${step.sequence}. ${step.node}: ${step.status} (${step.duration_ms ?? 0} ms)`);
    lines.push("", "## Findings", "");
    for (const finding of findings.data ?? []) lines.push(`- [${finding.severity}] ${finding.title} — ${finding.file_path ?? "no source location"}`);
    return lines.join("\n");
  }, [detail.data, findings.data]);

  return <div className="page-stack"><header className="page-header"><span className="eyebrow">LANGGRAPH EXECUTION</span><h2>Agent Runs</h2><p>运行、节点、工具调用和错误均来自 SQLite 持久化；运行中使用鉴权 SSE 推送更新。</p></header>{runs.isPending ? <LoadingState label="正在读取 Agent Runs…" /> : null}{runs.isError ? <ErrorState title="Run 列表不可用" message={errorMessage(runs.error)} onRetry={() => void runs.refetch()} /> : null}{runs.data?.items.length === 0 ? <div className="honest-empty-state"><div className="empty-mark">RUN</div><div><h2>尚无 Agent Run</h2><p>在 PR 详情中配置真实模型后启动分析。缺少模型时后端会明确拒绝，不会产生伪造报告。</p></div></div> : null}<div className="run-layout"><aside className="run-list">{runs.data?.items.map((run) => <button key={run.id} type="button" className={effectiveRunId === run.id ? "run-active" : ""} onClick={() => selectRun(run.id)}><span className={`pill pill-${run.status}`}>{run.status}</span><strong>{run.current_node ?? run.workflow_version ?? "等待开始"}</strong><small>{run.model_profile ?? "模型未记录"} · {new Date(run.created_at).toLocaleString("zh-CN")}</small></button>)}</aside><section className="panel run-detail">{detail.isPending && effectiveRunId ? <LoadingState label="正在读取 Run Trace…" /> : null}{detail.isError ? <ErrorState title="Run 详情不可用" message={errorMessage(detail.error)} /> : null}{detail.data ? <><div className="section-heading"><div><span className="eyebrow">{detail.data.status} · SSE {streamState}</span><h2>{detail.data.current_node ?? detail.data.workflow_version}</h2></div><div className="action-row"><button className="button button-secondary button-small" type="button" disabled={!['queued','running'].includes(detail.data.status) || cancel.isPending} onClick={() => cancel.mutate(detail.data.id)}>取消</button><button className="button button-secondary button-small" type="button" disabled={!['failed','cancelled'].includes(detail.data.status) || retry.isPending} onClick={() => retry.mutate(detail.data.id)}>重试</button><button className="button button-secondary button-small" type="button" onClick={() => download(`run-${detail.data.id}.json`, JSON.stringify({ run: detail.data, findings: findings.data ?? [], evidence: evidence.data ?? [] }, null, 2), "application/json")}>导出 JSON</button><button className="button button-secondary button-small" type="button" onClick={() => download(`run-${detail.data.id}.md`, markdown, "text/markdown")}>导出 Markdown</button></div></div>{cancel.isError || retry.isError ? <p className="inline-error">操作失败：{errorMessage(cancel.error ?? retry.error)}</p> : null}<dl className="metadata-grid"><div><dt>Head SHA</dt><dd className="mono">{detail.data.head_sha ?? "未记录"}</dd></div><div><dt>Index Version</dt><dd className="mono">{detail.data.index_version ?? "未记录"}</dd></div><div><dt>Prompt</dt><dd>{detail.data.prompt_version ?? "未记录"}</dd></div><div><dt>Token</dt><dd>{detail.data.input_tokens} in / {detail.data.output_tokens} out</dd></div><div><dt>延迟</dt><dd>{detail.data.latency_ms} ms</dd></div><div><dt>重试</dt><dd>{detail.data.retry_count}</dd></div></dl>{detail.data.error_message ? <pre className="error-block">{detail.data.error_code}\n{detail.data.error_message}</pre> : null}<ol className="trace-timeline">{detail.data.steps.map((step) => <li key={step.id}><span>{step.sequence}</span><div><strong>{step.node}</strong><small>{step.status} · {step.duration_ms ?? 0} ms</small><p>{step.output_summary ?? step.error_message ?? "执行中"}</p>{detail.data.tool_calls.filter((tool) => tool.agent_step_id === step.id).map((tool) => <details key={tool.id}><summary>{tool.tool_name} · {tool.permission} · {tool.status}</summary><pre>arguments: {tool.arguments_summary}\noutput: {tool.output_summary ?? ""}\nerror: {tool.error_code ?? "none"}</pre></details>)}</div></li>)}</ol><Suspense fallback={<LoadingState label="正在加载 Evidence Graph…" />}><AgentEvidenceGraph runId={detail.data.id} /></Suspense></> : null}</section></div></div>;
}
