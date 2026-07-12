import { useDiagnostics, useUpdateStatus } from "../api/queries";
import { ErrorState, LoadingState } from "../components/RequestState";
import { StatusCard } from "../components/StatusCard";
import { errorMessage } from "../lib/errors";
import { useI18n } from "../i18n";

export function DiagnosticsPage() {
  return <DiagnosticsContent />;
}

export function DiagnosticsContent({ embedded = false }: { embedded?: boolean }) {
  const { locale, text } = useI18n();
  const diagnostics = useDiagnostics();
  const updateStatus = useUpdateStatus();
  if (diagnostics.isPending) return <LoadingState label={text("正在读取脱敏诊断信息…", "Reading redacted diagnostics…")} />;
  if (diagnostics.isError) return <ErrorState title={text("诊断信息不可用", "Diagnostics unavailable")} message={errorMessage(diagnostics.error)} onRetry={() => void diagnostics.refetch()} />;
  const data = diagnostics.data;
  return (
    <div className={embedded ? "page-stack settings-diagnostics" : "page-stack"}>
      <header className="page-header">
        <span className="eyebrow">LOCAL DIAGNOSTICS</span>
        <h2>{text("诊断", "Diagnostics")}</h2>
        <p>{text("诊断响应不包含 API Token、模型密钥、GitHub Token 或 Relay Token；Telemetry 默认关闭。", "Diagnostic responses contain no API, model, GitHub, or Relay tokens; telemetry is off by default.")}</p>
      </header>
      <div className="status-grid">
        <StatusCard eyebrow="GITHUB" title="GitHub" status={data.github} />
        <StatusCard eyebrow="MODEL" title={text("模型", "Model")} status={data.model} />
        <StatusCard eyebrow="REALTIME" title="Webhook Relay" status={data.webhook_relay} />
      </div>
      <section className="panel">
        <div className="section-heading"><div><span className="eyebrow">RUNTIME</span><h2>{text("版本与进程", "Versions and process")}</h2></div><button className="button button-secondary button-small" type="button" onClick={() => void diagnostics.refetch()}>{text("刷新", "Refresh")}</button></div>
        <dl className="metadata-grid">
          <div><dt>{text("软件版本", "Software version")}</dt><dd>{data.software_version}</dd></div>
          <div><dt>Git Commit</dt><dd className="mono">{data.git_commit ?? text("不可用", "Unavailable")}</dd></div>
          <div><dt>OS / {text("架构", "architecture")}</dt><dd>{data.operating_system} / {data.architecture}</dd></div>
          <div><dt>Python</dt><dd>{data.python_version}</dd></div>
          <div><dt>Rust</dt><dd>{data.rust_version_info ?? text("宿主未报告", "Not reported by host")}</dd></div>
          <div><dt>Frontend / Desktop</dt><dd>{data.frontend_version ?? text("不可用", "Unavailable")} / {data.desktop_version ?? text("不可用", "Unavailable")}</dd></div>
          <div><dt>Sidecar PID / Port</dt><dd>{data.sidecar_pid} / {data.api_port}</dd></div>
        </dl>
        {updateStatus.data ? <p className={updateStatus.data.configured ? "inline-success" : "blocker-note"}>{text("更新通道", "Update channel")}: {updateStatus.data.channel} · {updateStatus.data.message}</p> : null}
      </section>
      <section className="panel">
        <span className="eyebrow">STORAGE</span><h2>{text("本地数据", "Local data")}</h2>
        <dl className="metadata-grid">
          <div><dt>{text("数据库类型", "Database type")}</dt><dd>{data.database_type}</dd></div>
          <div><dt>{text("数据库路径", "Database path")}</dt><dd className="mono">{data.database_path ?? text("服务端模式不公开连接字符串", "Server mode does not expose the connection string")}</dd></div>
          <div><dt>{text("日志路径", "Log path")}</dt><dd className="mono">{data.log_path}</dd></div>
          <div><dt>{text("日志级别", "Log level")}</dt><dd>{data.log_level}</dd></div>
          <div><dt>Telemetry</dt><dd>{data.telemetry_enabled ? text("已开启", "Enabled") : text("关闭（默认）", "Off (default)")}</dd></div>
        </dl>
        <details><summary>{text("已授权工作区", "Authorized workspaces")}</summary><ul className="plain-list">{data.workspace_paths.map((path) => <li className="mono" key={path}>{path}</li>)}</ul></details>
      </section>
      <section className="panel">
        <span className="eyebrow">OBSERVABILITY</span><h2>{text("最近持久化指标", "Latest persisted metrics")}</h2>
        <div className="metric-cards">
          <div><span>GitHub API</span><strong>{data.last_github_api_duration_ms ?? "—"} ms</strong><small>{data.last_github_api_request_count ?? 0} requests</small></div>
          <div><span>Index</span><strong>{data.last_index_duration_ms ?? "—"} ms</strong></div>
          <div><span>Graph</span><strong>{data.last_graph_duration_ms ?? "—"} ms</strong></div>
          <div><span>Retrieval</span><strong>{data.last_retrieval_result_count ?? "—"}</strong><small>{text("个结果", "results")}</small></div>
          <div><span>Model</span><strong>{data.last_model_latency_ms ?? "—"} ms</strong><small>{data.last_model_input_tokens ?? 0} in / {data.last_model_output_tokens ?? 0} out · {data.last_model_retry_count ?? 0} retries</small></div>
          <div><span>{text("系统通知", "Notifications")}</span><strong>{data.delivered_notification_count} / {data.failed_notification_count}</strong><small>{text("交给系统 / 失败", "handed to OS / failed")}</small></div>
        </div>
        <p className="field-note">{text("空值表示当前数据库尚无对应真实运行记录；页面不会用估算值补齐。", "An empty value means the current database has no corresponding real run; the page does not fill it with estimates.")}</p>
      </section>
      <section className="panel">
        <span className="eyebrow">QUEUES & STREAMS</span><h2>{text("后台队列", "Background queues")}</h2>
        <div className="metric-cards">
          <div><span>Monitor</span><strong>{data.monitor.running ? (data.monitor.polling ? "polling" : "idle") : "stopped"}</strong></div>
          <div><span>Relay SSE</span><strong>{data.webhook_relay.state === "not_configured" ? "not configured" : data.relay_monitor.connected ? "connected" : data.relay_monitor.running ? "reconnecting" : "stopped"}</strong></div>
          <div><span>Relay reconnects</span><strong>{data.relay_monitor.reconnect_count}</strong></div>
          <div><span>Repository queue</span><strong>{data.monitor.queued_repositories}</strong></div>
          <div><span>GitHub backoff</span><strong>{data.monitor.rate_limited_until ? new Date(data.monitor.rate_limited_until).toLocaleString(locale) : text("无", "None")}</strong></div>
          <div><span>Agent queue</span><strong>{data.agent_queue}</strong></div>
          <div><span>Index queue</span><strong>{data.index_queue}</strong></div>
        </div>
        {data.monitor.last_error ? <p className="inline-error">{data.monitor.last_error}</p> : null}
        {data.relay_monitor.last_error ? <p className="inline-error">{data.relay_monitor.last_error}</p> : null}
        <p className="field-note">{text("最近轮询", "Last poll")}: {data.monitor.last_finished_at ? new Date(data.monitor.last_finished_at).toLocaleString(locale) : text("尚未运行", "Not run yet")} · Relay {data.relay_monitor.last_event_at ? new Date(data.relay_monitor.last_event_at).toLocaleString(locale) : text("尚无事件", "no events")}</p>
      </section>
    </div>
  );
}
