import { useMemo, useState } from "react";
import type { EvaluationCase } from "@tracegate/shared-types";

import { useEvaluations } from "../api/queries";
import { ErrorState, LoadingState } from "../components/RequestState";
import { errorMessage } from "../lib/errors";
import { useI18n } from "../i18n";

function download(name: string, content: string, type: string) {
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(new Blob([content], { type }));
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(anchor.href);
}

function groupComparison(cases: EvaluationCase[], key: "model" | "context_group") {
  const groups = new Map<string, EvaluationCase[]>();
  for (const item of cases) groups.set(item[key], [...(groups.get(item[key]) ?? []), item]);
  return [...groups].map(([name, rows]) => ({
    name,
    runs: rows.length,
    safe: rows.filter((item) => item.safe_success).length / rows.length,
    evidenceAware: rows.filter((item) => item.evidence_aware_decision).length / rows.length,
    averageTokens: Math.round(rows.reduce((total, item) => total + item.context_tokens, 0) / rows.length),
  })).sort((left, right) => right.safe - left.safe || left.name.localeCompare(right.name));
}

export function EvalCenterPage() {
  const { text } = useI18n();
  const evaluation = useEvaluations();
  const [context, setContext] = useState("all");
  const [status, setStatus] = useState("all");
  const [errorsOnly, setErrorsOnly] = useState(false);
  const visible = useMemo(() => evaluation.data?.cases.filter((item) =>
    (context === "all" || item.context_group === context)
    && (status === "all" || item.evidence_status === status)
    && (!errorsOnly || !item.safe_success || !item.evidence_aware_decision || item.expected_decision !== item.decision)) ?? [], [context, errorsOnly, evaluation.data?.cases, status]);

  if (evaluation.isPending) return <LoadingState label={text("正在验证 TraceGate Eval 与 ClaimBench 产物…", "Verifying TraceGate Eval and ClaimBench artifacts…")} />;
  if (evaluation.isError) return <ErrorState title={text("Eval 产物不可用", "Eval artifacts unavailable")} message={errorMessage(evaluation.error)} onRetry={() => void evaluation.refetch()} />;
  const data = evaluation.data;
  const decisions = [...new Set(data.cases.flatMap((item) => [item.expected_decision, item.decision]))].sort();
  const confusion = new Map<string, number>();
  for (const item of data.cases) confusion.set(`${item.expected_decision}\u0000${item.decision}`, (confusion.get(`${item.expected_decision}\u0000${item.decision}`) ?? 0) + 1);
  const modelComparison = groupComparison(data.cases, "model");
  const promptComparison = groupComparison(data.cases, "context_group");
  const errorCases = data.cases.filter((item) => !item.safe_success || !item.evidence_aware_decision || item.expected_decision !== item.decision);

  return (
    <div className="page-stack">
      <header className="page-header"><span className="eyebrow">REAL BENCHMARK EVIDENCE</span><h2>Eval Center</h2><p>{data.benchmark_note}</p></header>
      <section className="hero-panel compact-hero"><div><span className="eyebrow">{data.is_real_dataset ? "REAL DATASET" : "INVALID"}</span><h2>{data.benchmark_name}</h2><p className="mono">dataset version / sha256 {data.dataset_sha256}</p><p>{text("模型配置", "Model configurations")}: {Object.entries(data.models).map(([model, count]) => `${model} (${count})`).join(" · ")}</p></div><div className="system-verdict"><span>Real cases</span><strong>{data.case_count}</strong><small>{data.claimbench_run_count} ClaimBench runs</small></div></section>

      <section><div className="section-heading"><div><span className="eyebrow">EVIDENCE STATUS</span><h2>{text("真实分布", "Real distribution")}</h2></div></div><div className="metric-cards">{Object.entries(data.status_distribution).map(([key, value]) => <div key={key}><span>{key}</span><strong>{value}</strong><div className="metric-bar"><i style={{ width: `${value / data.case_count * 100}%` }} /></div></div>)}</div></section>
      <section><div className="section-heading"><div><span className="eyebrow">METRICS</span><h2>{text("原始指标", "Raw metrics")}</h2></div></div><div className="metric-cards">{Object.entries(data.metrics).map(([key, value]) => <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{(value * 100).toFixed(2)}%</strong></div>)}</div></section>

      <section className="panel">
        <div className="section-heading"><div><span className="eyebrow">CONFUSION MATRIX</span><h2>{text("期望决策 × 实际决策", "Expected × actual decisions")}</h2></div></div>
        <div className="data-table-wrap"><table className="data-table"><thead><tr><th>{text("期望 \\ 实际", "Expected \\ Actual")}</th>{decisions.map((decision) => <th key={decision}>{decision}</th>)}</tr></thead><tbody>{decisions.map((expected) => <tr key={expected}><th>{expected}</th>{decisions.map((actual) => <td className={expected === actual ? "matrix-correct" : "matrix-error"} key={actual}>{confusion.get(`${expected}\u0000${actual}`) ?? 0}</td>)}</tr>)}</tbody></table></div>
        <p className="field-note">{text("矩阵直接由已校验 case 的 expected_decision 与 decision 计数，不重定义原有指标。", "The matrix counts expected_decision versus decision from validated cases and does not redefine existing metrics.")}</p>
      </section>

      <section className="comparison-grid">
        <ComparisonTable title={text("模型对比", "Model comparison")} rows={modelComparison} />
        <ComparisonTable title={text("Prompt / Context 对比", "Prompt / context comparison")} rows={promptComparison} />
      </section>

      <section className="panel">
        <div className="section-heading"><div><span className="eyebrow">CASE DRILL-DOWN</span><h2>{text("ClaimBench 运行记录", "ClaimBench run records")}</h2></div><div className="action-row compact"><button className="button button-secondary button-small" type="button" onClick={() => download("tracegate-evaluation.json", JSON.stringify(data, null, 2), "application/json")}>{text("导出 JSON 报告", "Export JSON report")}</button><button className="button button-secondary button-small" type="button" onClick={() => download("tracegate-evaluation-errors.csv", ["task_id,model,context_group,evidence_status,expected_decision,decision,safe_success,evidence_aware_decision", ...errorCases.map((item) => [item.task_id, item.model, item.context_group, item.evidence_status, item.expected_decision, item.decision, item.safe_success, item.evidence_aware_decision].map((value) => JSON.stringify(value)).join(","))].join("\n"), "text/csv")}>{text("导出错误案例", "Export error cases")}</button></div></div>
        <div className="filter-bar"><label className="field"><span>Context</span><select value={context} onChange={(event) => setContext(event.target.value)}><option value="all">{text("全部", "All")}</option>{Object.keys(data.context_groups).map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label className="field"><span>Evidence status</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">{text("全部", "All")}</option>{Object.keys(data.status_distribution).map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label className="switch-row compact-switch"><span><strong>{text("只看错误案例", "Errors only")}</strong><small>{errorCases.length} {text("条", "cases")}</small></span><input type="checkbox" checked={errorsOnly} onChange={(event) => setErrorsOnly(event.target.checked)} /></label><span className="count-label">{visible.length} rows</span></div>
        <div className="data-table-wrap eval-table"><table className="data-table"><thead><tr><th>Task</th><th>Model</th><th>Context</th><th>Evidence</th><th>Expected / Actual</th><th>Safe</th><th>Tokens</th><th>{text("详情", "Detail")}</th></tr></thead><tbody>{visible.map((item, index) => <tr key={`${item.task_id}-${item.context_group}-${index}`}><td>{item.task_id}</td><td>{item.model}</td><td>{item.context_group}</td><td>{item.evidence_status}</td><td className={item.expected_decision === item.decision ? "matrix-correct" : "matrix-error"}>{item.expected_decision} / {item.decision}</td><td>{item.safe_success ? "yes" : "no"}</td><td>{item.context_tokens}</td><td><details><summary>{text("运行证据", "Run evidence")}</summary><dl className="metadata-grid single"><div><dt>Status</dt><dd>{item.claimbench_status}</dd></div><div><dt>Evidence aware</dt><dd>{String(item.evidence_aware_decision)}</dd></div><div><dt>Run directory</dt><dd className="mono">{item.run_dir}</dd></div></dl></details></td></tr>)}</tbody></table></div>
      </section>

      <section className="panel"><span className="eyebrow">LIMITATIONS</span><ul className="plain-list">{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul><details><summary>{text("已验证 Artifact", "Verified artifacts")}</summary><ul className="plain-list">{data.artifacts.map((item) => <li key={item.path}><span className="mono">{item.path}</span><br /><small className="mono">{item.sha256}</small></li>)}</ul></details></section>
    </div>
  );
}

function ComparisonTable({ title, rows }: { title: string; rows: ReturnType<typeof groupComparison> }) {
  return <section className="panel"><span className="eyebrow">CONTROLLED COMPARISON</span><h2>{title}</h2><div className="data-table-wrap"><table className="data-table"><thead><tr><th>Name</th><th>Runs</th><th>Safe success</th><th>Evidence aware</th><th>Avg tokens</th></tr></thead><tbody>{rows.map((row) => <tr key={row.name}><td>{row.name}</td><td>{row.runs}</td><td>{(row.safe * 100).toFixed(1)}%</td><td>{(row.evidenceAware * 100).toFixed(1)}%</td><td>{row.averageTokens}</td></tr>)}</tbody></table></div></section>;
}
