/* eslint-disable react-refresh/only-export-components -- pure state guards are exported for focused safety tests beside the UI. */
import { useEffect, useRef, useState } from "react";
import type { TraceGateApiClient } from "@tracegate/api-client";
import type {
  Evidence,
  Finding,
  FixAction,
  FixPatchResponse,
  FixResult,
  FixSessionDetail,
  FixSessionEvent,
  FixSessionStatus,
  FixWorkflowNode,
} from "@tracegate/shared-types";

import {
  useApplyFixSession,
  useCancelFixSession,
  useConfirmFixSession,
  useDeleteFixWorkspace,
  useFixPatch,
  useFixReport,
  useFixSession,
  useFixSessions,
  useGenerateFixPatch,
  usePlanFixSession,
  useRereviewFixSession,
  useRollbackFixSession,
  useValidateFixSession,
} from "../api/queries";
import { useApiClient } from "../api/clientContext";
import { ErrorState, LoadingState } from "./RequestState";
import { errorMessage } from "../lib/errors";
import { useI18n } from "../i18n";

const workflowNodes: readonly FixWorkflowNode[] = [
  "LOAD_FINDING",
  "CHECK_FIX_ELIGIBILITY",
  "PLAN_FIX",
  "GENERATE_PATCH",
  "VALIDATE_PATCH",
  "AWAIT_USER_CONFIRMATION",
  "APPLY_PATCH",
  "RUN_VALIDATION",
  "REINDEX_CHANGES",
  "RE_REVIEW",
  "FINALIZE",
];

const terminalStatuses = new Set<FixSessionStatus>([
  "COMPLETED",
  "FAILED",
  "CANCELLED",
  "ROLLED_BACK",
  "STALE",
]);

const statusTranslations: Record<FixSessionStatus, readonly [string, string]> = {
  CREATED: ["已创建", "Created"],
  CHECKING_ELIGIBILITY: ["正在检查修复资格", "Checking eligibility"],
  ELIGIBLE: ["可以规划", "Eligible"],
  PLANNING: ["正在规划", "Planning"],
  PLAN_READY: ["计划已就绪", "Plan ready"],
  GENERATING_PATCH: ["正在生成补丁", "Generating patch"],
  VALIDATING_PATCH: ["正在静态校验补丁", "Validating patch"],
  AWAITING_USER_CONFIRMATION: ["等待用户确认", "Awaiting user confirmation"],
  APPLYING_PATCH: ["正在隔离工作区应用", "Applying in isolated workspace"],
  PATCH_APPLIED: ["补丁已隔离应用", "Patch applied in isolation"],
  RUNNING_VALIDATION: ["正在运行验证", "Running validation"],
  VALIDATION_COMPLETE: ["验证已完成", "Validation complete"],
  REINDEXING_CHANGES: ["正在重建变更索引", "Reindexing changes"],
  RE_REVIEWING: ["正在重新审查", "Re-reviewing"],
  FINALIZING: ["正在生成最终报告", "Finalizing report"],
  COMPLETED: ["已完成", "Completed"],
  FAILED: ["失败", "Failed"],
  CANCELLED: ["已取消", "Cancelled"],
  ROLLED_BACK: ["已回滚", "Rolled back"],
  STALE: ["Head 已过期", "Head is stale"],
};

export function localizedFixStatus(status: FixSessionStatus, locale: "zh-CN" | "en-US"): string {
  return statusTranslations[status][locale === "en-US" ? 1 : 0];
}

export function commandText(argv: readonly string[]): string {
  return argv.map((part) => (/^[A-Za-z0-9_./:=@+-]+$/.test(part) ? part : JSON.stringify(part))).join(" ");
}

export function isFixStale(session: FixSessionDetail, currentHead: string | null): boolean {
  return session.status === "STALE" || currentHead === null || currentHead !== session.head_sha;
}

export function canApplyFix(session: FixSessionDetail, currentHead: string | null): boolean {
  const confirmation = session.confirmation;
  const proposalHash = session.patch_inspection?.patch_hash;
  return session.allowed_actions.includes("APPLY")
    && !isFixStale(session, currentHead)
    && proposalHash !== undefined
    && confirmation !== null
    && confirmation.patch_hash === proposalHash
    && confirmation.confirmed_at !== null
    && confirmation.consumed_at === null
    && confirmation.invalidated_at === null
    && Date.parse(confirmation.expires_at) > Date.now();
}

export function fixStreamRetryDelay(attempt: number): number {
  return Math.min(4_000, 250 * (2 ** Math.max(0, attempt)));
}

async function abortableDelay(milliseconds: number, signal: AbortSignal): Promise<void> {
  if (signal.aborted) throw new DOMException("Aborted", "AbortError");
  await new Promise<void>((resolve, reject) => {
    const onAbort = () => {
      window.clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    const timer = window.setTimeout(() => {
      signal.removeEventListener("abort", onAbort);
      resolve();
    }, milliseconds);
    signal.addEventListener("abort", onAbort, { once: true });
  });
}

export async function streamFixEventsWithRetry(
  stream: TraceGateApiClient["streamFixSessionEvents"],
  fixSessionId: string,
  onEvent: (event: FixSessionEvent) => void,
  onTerminalError: (error: unknown) => void,
  signal: AbortSignal,
  options: { maxAttempts?: number; wait?: (milliseconds: number, signal: AbortSignal) => Promise<void> } = {},
): Promise<void> {
  const maxAttempts = options.maxAttempts ?? 5;
  const wait = options.wait ?? abortableDelay;
  let lastEventId: string | null = null;
  let consecutiveFailures = 0;
  let lastError: unknown = new Error("Fix Session event stream closed unexpectedly.");
  while (!signal.aborted && consecutiveFailures < maxAttempts) {
    let receivedEvent = false;
    try {
      const cursor = await stream(fixSessionId, (event) => {
        receivedEvent = true;
        lastEventId = event.event_id;
        onEvent(event);
      }, { signal, ...(lastEventId ? { lastEventId } : {}) });
      if (cursor.lastEventId) lastEventId = cursor.lastEventId;
      if (signal.aborted) return;
      lastError = new Error("Fix Session event stream closed unexpectedly.");
    } catch (error) {
      if (signal.aborted || (error instanceof DOMException && error.name === "AbortError")) return;
      lastError = error;
    }
    if (receivedEvent) consecutiveFailures = 0;
    consecutiveFailures += 1;
    if (consecutiveFailures >= maxAttempts) break;
    try {
      await wait(fixStreamRetryDelay(consecutiveFailures - 1), signal);
    } catch (error) {
      if (signal.aborted || (error instanceof DOMException && error.name === "AbortError")) return;
      lastError = error;
      break;
    }
  }
  if (!signal.aborted) onTerminalError(lastError);
}

function saveArtifact(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

interface FixExperienceProps {
  pullRequestId: string;
  currentHead: string | null;
  findings: Finding[];
  evidence: Evidence[];
  preferredSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onOpenDiff: (path: string | null, line?: number | null) => void;
}

export function FixExperience({
  pullRequestId,
  currentHead,
  findings,
  evidence,
  preferredSessionId,
  onSelectSession,
  onOpenDiff,
}: FixExperienceProps) {
  const { locale, text } = useI18n();
  const client = useApiClient();
  const sessions = useFixSessions(pullRequestId);
  const activeId = preferredSessionId ?? sessions.data?.items[0]?.id;
  const detail = useFixSession(activeId);
  const refetchDetail = detail.refetch;
  const detailStatus = detail.data?.status;
  const [patchPath, setPatchPath] = useState<string | undefined>(undefined);
  const patch = useFixPatch(detail.data?.proposal ? activeId : undefined, patchPath);
  const report = useFixReport(detail.data?.result ? activeId : undefined);
  const [events, setEvents] = useState<FixSessionEvent[]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);
  const streamedSessionId = useRef<string | null>(null);

  useEffect(() => {
    const firstId = sessions.data?.items[0]?.id;
    if (!preferredSessionId && firstId) onSelectSession(firstId);
  }, [onSelectSession, preferredSessionId, sessions.data?.items]);

  useEffect(() => {
    if (!activeId || !detailStatus || terminalStatuses.has(detailStatus)) return;
    const controller = new AbortController();
    if (streamedSessionId.current !== activeId) {
      streamedSessionId.current = activeId;
      setEvents([]);
    }
    setStreamError(null);
    void streamFixEventsWithRetry(client.streamFixSessionEvents.bind(client), activeId, (event) => {
      setEvents((current) => [...current.filter((item) => item.event_id !== event.event_id), event].slice(-80));
      void refetchDetail();
    }, (error) => setStreamError(errorMessage(error)), controller.signal);
    return () => controller.abort();
  }, [activeId, client, detailStatus, refetchDetail]);

  if (sessions.isPending) return <LoadingState label={text("正在读取自动修复会话…", "Reading autofix sessions…")} />;
  if (sessions.isError) return <ErrorState title={text("自动修复会话不可用", "Autofix sessions unavailable")} message={errorMessage(sessions.error)} onRetry={() => void sessions.refetch()} />;
  if (!sessions.data?.items.length || !activeId) {
    return <div className="honest-empty-state"><div className="empty-mark">FIX</div><div><h2>{text("尚无修复会话", "No fix session yet")}</h2><p>{text("从 Finding 卡片启动。TraceGate 会先检查 Evidence、Head SHA 和路径安全性，再调用真实模型生成计划与补丁。", "Start from a Finding card. TraceGate checks Evidence, Head SHA, and path safety before asking the real model for a plan and patch.")}</p></div></div>;
  }
  if (detail.isError) return <ErrorState title={text("修复详情不可用", "Fix detail unavailable")} message={errorMessage(detail.error)} onRetry={() => void detail.refetch()} />;
  if (detail.isPending || !detail.data) return <LoadingState label={text("正在读取修复详情…", "Reading fix details…")} />;

  return <div className="fix-experience">
    <aside className="fix-session-list" aria-label={text("修复会话", "Fix sessions")}>
      <span className="eyebrow">CONTROLLED FIX SESSIONS</span>
      {sessions.data.items.map((session) => <button className={session.id === activeId ? "fix-session-active" : ""} key={session.id} type="button" onClick={() => { setPatchPath(undefined); onSelectSession(session.id); }}><strong>{localizedFixStatus(session.status, locale)}</strong><small className="mono">{session.head_sha.slice(0, 12)} · v{session.lock_version}</small></button>)}
    </aside>
    <FixSessionView
      session={detail.data}
      finding={findings.find((item) => item.id === detail.data?.finding_id) ?? null}
      evidence={evidence.filter((item) => findings.find((finding) => finding.id === detail.data?.finding_id)?.evidence_ids_json.includes(item.id))}
      currentHead={currentHead}
      patch={patch.data ?? null}
      patchError={patch.isError ? errorMessage(patch.error) : null}
      report={report.data ?? detail.data.result}
      events={events}
      streamError={streamError}
      onOpenDiff={onOpenDiff}
      onSelectPatchPath={setPatchPath}
      onRefresh={() => void detail.refetch()}
      client={client}
    />
  </div>;
}

interface FixSessionViewProps {
  session: FixSessionDetail;
  finding: Finding | null;
  evidence: Evidence[];
  currentHead: string | null;
  patch: FixPatchResponse | null;
  patchError: string | null;
  report: FixResult | null;
  events: FixSessionEvent[];
  streamError: string | null;
  onOpenDiff: (path: string | null, line?: number | null) => void;
  onSelectPatchPath?: (path: string) => void;
  onRefresh: () => void;
  client: ReturnType<typeof useApiClient>;
}

export function FixSessionView(props: FixSessionViewProps) {
  const { locale, text } = useI18n();
  const { session, finding, evidence, currentHead, patch, patchError, report, events, streamError } = props;
  const plan = usePlanFixSession();
  const generate = useGenerateFixPatch();
  const confirm = useConfirmFixSession();
  const apply = useApplyFixSession();
  const validate = useValidateFixSession();
  const rereview = useRereviewFixSession();
  const cancel = useCancelFixSession();
  const rollback = useRollbackFixSession();
  const cleanup = useDeleteFixWorkspace();
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [forceEligibilityAcknowledged, setForceEligibilityAcknowledged] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(patch?.selected_path ?? patch?.changed_files[0]?.path ?? null);
  const selectedPatchPath = patch?.selected_path;
  const firstPatchPath = patch?.changed_files[0]?.path;
  const stale = isFixStale(session, currentHead);
  const actions = new Set<FixAction>(session.allowed_actions);
  const mutationError = plan.error ?? generate.error ?? confirm.error ?? apply.error ?? validate.error ?? rereview.error ?? cancel.error ?? rollback.error ?? cleanup.error;
  const busy = plan.isPending || generate.isPending || confirm.isPending || apply.isPending || validate.isPending || rereview.isPending || cancel.isPending || rollback.isPending || cleanup.isPending;

  useEffect(() => {
    if (selectedPatchPath) setSelectedPath(selectedPatchPath);
    else if (firstPatchPath) setSelectedPath(firstPatchPath);
  }, [firstPatchPath, patch?.patch_hash, selectedPatchPath]);

  const selectedPatch = selectedPath === patch?.selected_path ? patch : null;
  const completedNodeIndex = session.current_node ? workflowNodes.indexOf(session.current_node) : (session.status === "COMPLETED" ? workflowNodes.length : -1);
  const confirmationReady = canApplyFix(session, currentHead);

  const actionInput = { expected_lock_version: session.lock_version };
  const runExport = async (kind: "patch" | "report") => {
    try {
      setExportError(null);
      const artifact = kind === "patch" ? await props.client.downloadFixPatch(session.id) : await props.client.downloadFixReport(session.id);
      saveArtifact(artifact.blob, artifact.filename);
    } catch (error) {
      setExportError(errorMessage(error));
    }
  };

  return <section className="fix-session-detail">
    <header className="fix-session-hero">
      <div><span className="eyebrow">CODING AGENT · {session.permission_mode}</span><h2>{localizedFixStatus(session.status, locale)}</h2><p>{text("每一步均由后端状态机控制；补丁只会应用到临时 Git worktree，不会提交或推送。", "Every step is server-state-machine controlled. The patch is applied only to a temporary Git worktree and is never committed or pushed.")}</p></div>
      <span className={`pill pill-${terminalStatuses.has(session.status) ? session.status.toLowerCase() : "active"}`}>{session.status}</span>
    </header>

    {stale ? <div className="fix-blocker" role="alert"><strong>{text("Head SHA 已变化，禁止确认或应用", "Head SHA changed; confirmation and apply are blocked")}</strong><span className="mono">session {session.head_sha} · current {currentHead ?? text("不可用", "unavailable")}</span></div> : null}
    {session.error_message ? <pre className="error-block">{session.error_code ?? "FIX_FAILED"}\n{session.error_message}</pre> : null}
    {mutationError || exportError ? <p className="inline-error" role="alert">{text("操作失败", "Action failed")}: {errorMessage(mutationError ?? exportError)}</p> : null}

    <div className="fix-actions" aria-label={text("修复操作", "Fix actions")}>
      <button className="button button-primary" type="button" disabled={busy || !actions.has("PLAN") || stale} onClick={() => plan.mutate({ fixSessionId: session.id, input: { ...actionInput, force_eligibility: false } })}>{text("检查资格并规划", "Check eligibility & plan")}</button>
      <button className="button button-primary" type="button" disabled={busy || !actions.has("GENERATE") || stale} onClick={() => generate.mutate({ fixSessionId: session.id, input: actionInput })}>{text("生成并静态校验补丁", "Generate & inspect patch")}</button>
      <button className="button button-primary" type="button" disabled={busy || !actions.has("CONFIRM") || stale || !session.patch_inspection} onClick={() => setShowConfirmation(true)}>{text("核对并确认补丁", "Review & confirm patch")}</button>
      <button className="button button-primary" type="button" disabled={busy || !confirmationReady} title={!confirmationReady ? text("需要有效、未过期且匹配当前 Head 与 Patch Hash 的服务端确认", "Requires a valid unexpired server confirmation bound to the current Head and Patch Hash") : undefined} onClick={() => session.patch_inspection && apply.mutate({ fixSessionId: session.id, input: { ...actionInput, patch_hash: session.patch_inspection.patch_hash } })}>{text("应用到隔离工作区", "Apply in isolated workspace")}</button>
      <button className="button button-primary" type="button" disabled={busy || stale || !actions.has("VALIDATE")} onClick={() => validate.mutate({ fixSessionId: session.id, input: actionInput })}>{text("运行受控验证", "Run controlled validation")}</button>
      <button className="button button-primary" type="button" disabled={busy || stale || !actions.has("RE_REVIEW")} onClick={() => rereview.mutate({ fixSessionId: session.id, input: actionInput })}>{text("重建索引并重新审查", "Reindex & re-review")}</button>
      <button className="button button-secondary" type="button" disabled={!actions.has("EXPORT_PATCH") || !session.proposal} onClick={() => void runExport("patch")}>{text("导出 .patch", "Export .patch")}</button>
      <button className="button button-secondary" type="button" disabled={!actions.has("EXPORT_REPORT") || !session.result} onClick={() => void runExport("report")}>{text("导出报告", "Export report")}</button>
      <button className="button button-secondary" type="button" disabled={busy || !actions.has("ROLLBACK")} onClick={() => rollback.mutate({ fixSessionId: session.id, input: actionInput })}>{text("回滚隔离工作区", "Rollback workspace")}</button>
      <button className="button button-secondary button-danger" type="button" disabled={busy || !actions.has("DELETE_WORKSPACE")} onClick={() => cleanup.mutate({ fixSessionId: session.id, expectedLockVersion: session.lock_version })}>{text("清理工作区", "Delete workspace")}</button>
      <button className="text-button" type="button" disabled={cancel.isPending || !actions.has("CANCEL")} onClick={() => cancel.mutate({ fixSessionId: session.id, input: actionInput })}>{text("取消运行", "Cancel run")}</button>
      <button className="text-button" type="button" onClick={props.onRefresh}>{text("刷新", "Refresh")}</button>
    </div>

    <div className="fix-grid">
      <article className="panel fix-finding"><span className="eyebrow">SOURCE FINDING</span><h3>{finding?.title ?? text("Finding 记录不可用", "Finding record unavailable")}</h3><p>{finding?.message}</p><dl className="metadata-grid"><div><dt>Head SHA</dt><dd className="mono">{session.head_sha}</dd></div><div><dt>{text("位置", "Location")}</dt><dd><button className="text-button" disabled={!finding?.file_path} type="button" onClick={() => props.onOpenDiff(finding?.file_path ?? null, finding?.line_start)}>{finding?.file_path ?? text("未记录", "Not recorded")}:{finding?.line_start ?? "?"}</button></dd></div><div><dt>Verifier</dt><dd>{finding?.verifier_status ?? text("未记录", "Not recorded")}</dd></div><div><dt>Evidence</dt><dd>{evidence.length}</dd></div></dl>{evidence.map((item) => <details key={item.id}><summary>{item.source_type} · {item.file_path ?? item.source_uri}</summary><pre>{item.content_hash}\n{JSON.stringify(item.payload_json, null, 2)}</pre></details>)}</article>
      <article className="panel"><span className="eyebrow">ELIGIBILITY</span><h3>{session.eligibility?.status ?? text("尚未检查", "Not checked")}</h3><ul className="plain-list">{session.eligibility?.reasons.map((reason) => <li key={reason}>{reason}</li>) ?? <li>{text("点击“检查资格并规划”后显示后端结论。", "The server decision appears after eligibility & planning.")}</li>}</ul>{session.eligibility?.warnings.map((warning) => <p className="blocker-note" key={warning}>{warning}</p>)}{session.eligibility?.status === "NEEDS_CONFIRMATION" && session.eligibility.force_allowed ? <div className="force-eligibility"><strong>{text("需要额外风险授权", "Additional risk authorization required")}</strong><p>{text("默认规划不会绕过资格结论。只有逐项核对上述原因并明确承担风险后，才会向后端发送 force_eligibility=true；此授权不等于补丁应用确认。", "Default planning never bypasses eligibility. Only after reviewing the reasons and explicitly accepting the risk will the UI send force_eligibility=true. This is separate from patch-apply confirmation.")}</p><label className="fix-confirm-check"><input type="checkbox" checked={forceEligibilityAcknowledged} onChange={(event) => setForceEligibilityAcknowledged(event.target.checked)} /><span>{text("我已理解资格警告，并同意仅继续生成修复计划；补丁仍需单独核对 Hash 后确认。", "I understand the eligibility warnings and authorize planning only; the patch still requires a separate hash-bound confirmation.")}</span></label><button className="button button-danger" type="button" disabled={busy || stale || !actions.has("PLAN") || !forceEligibilityAcknowledged} onClick={() => plan.mutate({ fixSessionId: session.id, input: { ...actionInput, force_eligibility: true } })}>{text("承担风险，继续规划", "Accept risk & continue planning")}</button></div> : null}</article>
    </div>

    <ol className="fix-progress" aria-label={text("修复工作流进度", "Fix workflow progress")}>{workflowNodes.map((node, index) => <li className={index < completedNodeIndex || session.status === "COMPLETED" ? "fix-step-done" : index === completedNodeIndex ? "fix-step-active" : ""} key={node}><span>{String(index + 1).padStart(2, "0")}</span><strong>{node.replaceAll("_", " ")}</strong></li>)}</ol>

    {session.plan ? <article className="panel fix-plan"><div className="section-heading"><div><span className="eyebrow">MODEL FIX PLAN · {Math.round(session.plan.confidence * 100)}%</span><h2>{session.plan.objective}</h2></div></div><p>{session.plan.root_cause}</p><div className="fix-grid"><div><h3>{text("受影响文件", "Affected files")}</h3><ul className="plain-list">{session.plan.affected_files.map((file) => <li key={file} className="mono">{file}</li>)}</ul></div><div><h3>{text("受影响符号", "Affected symbols")}</h3><ul className="plain-list">{session.plan.affected_symbols.map((symbol) => <li key={symbol} className="mono">{symbol}</li>)}</ul></div><div><h3>{text("计划步骤", "Proposed steps")}</h3><ol className="plain-list">{session.plan.proposed_steps.map((step) => <li key={step}>{step}</li>)}</ol></div><div><h3>{text("风险与约束", "Risks & constraints")}</h3><ul className="plain-list">{[...session.plan.risk_notes, ...session.plan.constraints].map((note) => <li key={note}>{note}</li>)}</ul></div></div></article> : null}

    {session.patch_inspection ? <article className="panel patch-inspection"><div className="section-heading"><div><span className="eyebrow">STATIC PATCH INSPECTION</span><h2>{session.patch_inspection.changed_files.length} {text("个文件", "files")} · {session.patch_inspection.changed_lines} {text("行变更", "changed lines")}</h2></div><code>{session.patch_inspection.patch_hash}</code></div><div className="metric-cards"><div><span>{text("新增", "Additions")}</span><strong className="positive">+{session.patch_inspection.additions}</strong></div><div><span>{text("删除", "Deletions")}</span><strong className="negative">−{session.patch_inspection.deletions}</strong></div><div><span>{text("确认要求", "Confirmation")}</span><strong>{session.patch_inspection.requires_confirmation ? text("必须", "Required") : text("不要求", "Not required")}</strong></div></div>{session.patch_inspection.warnings.map((warning) => <p className="blocker-note" key={warning}>{warning}</p>)}</article> : null}

    {patch ? <PatchViewer patch={patch} selectedPath={selectedPath} selectedPatch={selectedPatch} onSelectPath={(path) => { setSelectedPath(path); props.onSelectPatchPath?.(path); }} /> : patchError ? <p className="inline-error">{text("补丁读取失败", "Could not read patch")}: {patchError}</p> : null}

    {session.validation_plan ? <article className="panel"><span className="eyebrow">CONTROLLED VALIDATION PLAN</span><h2>{text("将执行的命令", "Commands to execute")}</h2>{session.validation_plan.commands.length ? <ol className="validation-commands">{session.validation_plan.commands.map((command, index) => <li key={`${index}-${commandText(command.argv)}`}><code>{commandText(command.argv)}</code><span>{command.required ? text("必需", "required") : text("可选", "optional")} · {command.timeout}s · {command.command_purpose}</span></li>)}</ol> : <p className="blocker-note">NO_TEST_COMMAND_AVAILABLE</p>}{session.validation_plan.notes.map((note) => <p className="field-note" key={note}>{note}</p>)}</article> : null}

    {session.validation_runs.length ? <article className="panel"><span className="eyebrow">VALIDATION RESULTS</span><h2>{text("真实命令结果", "Real command results")}</h2><div className="validation-results">{session.validation_runs.map((run) => <details open={run.status === "FAILED"} key={run.id}><summary><span className={`pill pill-${run.status.toLowerCase()}`}>{run.status}</span><code>{commandText(run.command)}</code><small>{run.duration_ms ?? 0} ms · exit {run.return_code ?? "—"}</small></summary>{run.error_code ? <p className="inline-error">{run.error_code}</p> : null}<pre>{run.stdout_summary ?? ""}\n{run.stderr_summary ?? ""}{run.output_truncated ? `\n${text("输出已安全截断", "Output safely truncated")}` : ""}</pre></details>)}</div></article> : null}

    {session.steps.length ? <article className="panel"><span className="eyebrow">PERSISTED AGENT TRACE</span><h2>{text("节点、模型耗时与工具调用", "Nodes, model timing & tool calls")}</h2><ol className="trace-timeline">{session.steps.map((step) => <li key={step.id}><span>{step.sequence}</span><div><strong>{step.node} · {step.status}</strong><small>{step.duration_ms ?? 0} ms · {step.id}</small>{step.error_message ? <p className="inline-error">{step.error_code}: {step.error_message}</p> : null}{step.tool_calls.map((call) => <details key={call.id}><summary>{call.tool_name} · {call.status} · {call.duration_ms ?? 0} ms</summary><pre>{call.arguments_summary}\n{call.output_summary ?? ""}</pre></details>)}</div></li>)}</ol></article> : null}

    <article className="panel"><div className="section-heading"><div><span className="eyebrow">LIVE FIX TRACE</span><h2>{text("持久化事件与进度日志", "Persisted events & progress log")}</h2></div><span className={`pill ${streamError ? "pill-failed" : "pill-active"}`}>SSE {streamError ? text("断开", "disconnected") : text("已连接/待命", "connected/idle")}</span></div>{streamError ? <p className="inline-error">{streamError}</p> : null}{events.length ? <ol className="trace-timeline">{events.map((event) => <li key={event.event_id}><span>{event.sequence}</span><div><strong>{event.type}</strong><small>{new Date(event.created_at).toLocaleString(locale)} · {event.event_id}</small><p>{eventMessage(event)}</p></div></li>)}</ol> : <p className="field-note">{text("没有尚未展示的新事件；当前状态仍来自持久化详情。", "No undisplayed event yet; current state still comes from persisted detail.")}</p>}</article>

    {report ? <article className={`panel fix-result resolution-${report.resolution.toLowerCase()}`}><span className="eyebrow">POST-FIX REPORT</span><h2>{report.resolution}</h2><p>{report.report.final_summary}</p><dl className="metadata-grid"><div><dt>{text("验证", "Validation")}</dt><dd>{report.validation_status ?? text("无", "none")}</dd></div><div><dt>{text("重新审查", "Re-review")}</dt><dd>{report.re_review_status}</dd></div><div><dt>Patch Hash</dt><dd className="mono">{report.report.patch_hash}</dd></div><div><dt>{text("隔离工作区", "Isolated workspace")}</dt><dd>{session.cleanup_status}</dd></div></dl><div className="fix-grid"><div><h3>{text("残余 Finding", "Residual findings")}</h3><ul className="plain-list">{report.residual_findings.length ? report.residual_findings.map((item) => <li key={item}>{item}</li>) : <li>{text("没有持久化的残余 Finding", "No persisted residual finding")}</li>}</ul></div><div><h3>{text("残余风险", "Residual risks")}</h3><ul className="plain-list">{report.residual_risks.length ? report.residual_risks.map((item) => <li key={item}>{item}</li>) : <li>{text("没有持久化的残余风险", "No persisted residual risk")}</li>}</ul></div></div></article> : null}

    {showConfirmation && session.patch_inspection ? <FixConfirmationDialog session={session} onCancel={() => setShowConfirmation(false)} onConfirm={() => { confirm.mutate({ fixSessionId: session.id, input: { expected_lock_version: session.lock_version, patch_hash: session.patch_inspection?.patch_hash ?? "" } }, { onSuccess: () => setShowConfirmation(false) }); }} busy={confirm.isPending} /> : null}
  </section>;
}

function PatchViewer({ patch, selectedPath, selectedPatch, onSelectPath }: { patch: FixPatchResponse; selectedPath: string | null; selectedPatch: FixPatchResponse | null; onSelectPath: (path: string) => void }) {
  const { text } = useI18n();
  return <article className="panel patch-viewer"><div className="section-heading"><div><span className="eyebrow">AUTHORITATIVE PATCH</span><h2>{text("完整补丁与文件预览", "Full patch & file preview")}</h2></div><code>{patch.patch_hash}</code></div><div className="patch-file-tabs">{patch.changed_files.map((file) => <button className={selectedPath === file.path ? "patch-file-active" : ""} type="button" key={file.path} onClick={() => onSelectPath(file.path)}><span>{file.status}</span>{file.path}</button>)}</div>{selectedPatch ? <div className="patch-code-grid"><div><strong>Base</strong><pre>{selectedPatch.original ?? text("文件不存在", "File absent")}</pre></div><div><strong>Patched</strong><pre>{selectedPatch.modified ?? text("文件已删除", "File deleted")}</pre></div></div> : <p className="field-note">{text("选择文件后，后端会按路径返回 Base 与隔离补丁内容。完整 unified diff 始终保留在下方。", "Select a file to request its Base and isolated patched content. The full unified diff remains below.")}</p>}<details><summary>{text("查看完整 Unified Diff", "View full unified diff")}</summary><pre className="unified-diff">{patch.unified_diff}</pre></details></article>;
}

export function FixConfirmationDialog({ session, onCancel, onConfirm, busy }: { session: FixSessionDetail; onCancel: () => void; onConfirm: () => void; busy: boolean }) {
  const { text } = useI18n();
  const [acknowledged, setAcknowledged] = useState(false);
  const inspection = session.patch_inspection;
  const commands = session.validation_plan?.commands ?? session.proposal?.validation_commands ?? [];
  if (!inspection) return null;
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onCancel(); }}><section className="confirmation-modal fix-confirmation" role="dialog" aria-modal="true" aria-labelledby="fix-confirm-title"><span className="eyebrow">HASH-BOUND CONFIRMATION</span><h2 id="fix-confirm-title">{text("确认这一个精确补丁", "Confirm this exact patch")}</h2><p>{text("确认仅绑定当前 Finding、Head SHA 和下方完整 Patch Hash。Head 或补丁变化都会使确认失效。", "Confirmation is bound only to the current Finding, Head SHA, and full Patch Hash below. A Head or patch change invalidates it.")}</p><dl className="metadata-grid"><div><dt>{text("文件 / 变更行", "Files / changed lines")}</dt><dd>{inspection.changed_files.length} / {inspection.changed_lines}</dd></div><div><dt>Head SHA</dt><dd className="mono">{session.head_sha}</dd></div><div className="full-row"><dt>Patch Hash</dt><dd className="mono hash-value">{inspection.patch_hash}</dd></div></dl>{inspection.warnings.length ? <div className="fix-confirm-risks"><strong>{text("静态风险提示", "Static risk warnings")}</strong><ul>{inspection.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div> : null}<div className="fix-confirm-commands"><strong>{text("确认后允许执行的验证命令", "Validation commands allowed after confirmation")}</strong>{commands.length ? <ul>{commands.map((command) => <li key={commandText(command.argv)}><code>{commandText(command.argv)}</code>{command.required ? " · required" : " · optional"}</li>)}</ul> : <p>NO_TEST_COMMAND_AVAILABLE</p>}<p className="blocker-note">{text("安全边界：测试代码仍以当前用户权限运行；参数白名单、工作目录和环境变量过滤不等同于操作系统或容器沙箱。", "Security boundary: test code still runs with the current user privileges; argv allowlisting, cwd restriction, and environment filtering are not an OS or container sandbox.")}</p></div><label className="fix-confirm-check"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /><span>{text("我已核对文件、行数、风险、命令和完整 Hash；理解验证会执行仓库代码，补丁只进入隔离 worktree，且不会 commit、push 或修改原工作区。", "I reviewed files, line count, risks, commands, and the full hash; I understand validation executes repository code, while the patch stays in an isolated worktree and is never committed, pushed, or applied to the source workspace.")}</span></label><div className="form-actions"><button className="button button-secondary" type="button" disabled={busy} onClick={onCancel}>{text("返回继续核对", "Go back")}</button><button className="button button-primary" type="button" disabled={!acknowledged || busy} onClick={onConfirm}>{busy ? text("正在绑定确认…", "Binding confirmation…") : text("确认该 Hash 并授权隔离应用", "Confirm hash & authorize isolated apply")}</button></div></section></div>;
}

function eventMessage(event: FixSessionEvent): string {
  if (event.type === "workflow_step") return event.data.message;
  if (event.type === "terminal") return event.data.error_message ?? event.data.status;
  if (event.type === "error") return `${event.data.code}: ${event.data.message}`;
  if (event.type === "validation_output") return `${event.data.stream}: ${event.data.chunk}`;
  if (event.type === "session") return event.data.status;
  if (event.type === "patch_ready") return `${event.data.changed_files.length} files · ${event.data.changed_lines} lines`;
  if (event.type === "validation_started" || event.type === "validation_finished") return `${event.data.status}: ${commandText(event.data.command)}`;
  if (event.type === "re_review") return event.data.summary;
  return event.data.report.final_summary;
}
