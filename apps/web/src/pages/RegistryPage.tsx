import {
  useAgents,
  useSetAgentEnabled,
  useSetToolEnabled,
  useTools,
} from "../api/queries";
import { ErrorState, LoadingState } from "../components/RequestState";
import { errorMessage } from "../lib/errors";
import { useI18n } from "../i18n";

export function RegistryPage() {
  const { text } = useI18n();
  const agents = useAgents();
  const tools = useTools();
  const setAgentEnabled = useSetAgentEnabled();
  const setToolEnabled = useSetToolEnabled();
  const mutationError = setAgentEnabled.error ?? setToolEnabled.error;

  return (
    <div className="page-stack">
      <header className="page-header">
        <span className="eyebrow">OBSERVABLE CAPABILITIES</span>
        <h2>Agent & Tool Registry</h2>
        <p>{text("只列出生产工作流实际注册的节点和工具；调用统计来自持久化 ToolCall 记录。", "Only nodes and tools registered in the production workflow are listed; call totals come from persisted ToolCall records.")}</p>
      </header>
      {mutationError ? <p className="inline-error">{text("Registry 更新失败", "Registry update failed")}: {errorMessage(mutationError)}</p> : null}
      <section>
        <div className="section-heading">
          <div><span className="eyebrow">LANGGRAPH NODES</span><h2>Agent Registry</h2></div>
        </div>
        <p className="field-note">{text("停用任一 Agent 会阻止新的分析任务启动；已经运行的任务继续使用启动时的 Registry 快照。", "Disabling any agent blocks new analyses; already-running analyses continue with the Registry snapshot captured at launch.")}</p>
        {agents.isPending ? <LoadingState label={text("正在读取 Agent Registry…", "Reading Agent Registry…")} /> : null}
        {agents.isError ? <ErrorState title={text("Agent Registry 不可用", "Agent Registry unavailable")} message={errorMessage(agents.error)} /> : null}
        <div className="registry-grid">
          {agents.data?.map((agent, index) => {
            const enabled = agent.status === "enabled";
            const pending = setAgentEnabled.isPending && setAgentEnabled.variables?.name === agent.name;
            return <article className="registry-card" key={agent.name}>
              <div className="repository-card-heading">
                <span className="registry-index">{String(index + 1).padStart(2, "0")}</span>
                <span className={`pill pill-${enabled ? "active" : "muted"}`}>{agent.status}</span>
              </div>
              <h3>{agent.name}</h3>
              <p>{agent.responsibility}</p>
              <small className="mono">{agent.version}</small>
              <dl>
                <dt>Capabilities</dt><dd>{agent.capabilities.join(" · ")}</dd>
                <dt>Allowed tools</dt><dd>{agent.allowed_tools.length ? agent.allowed_tools.join(" · ") : text("不直接调用工具", "No direct tool calls")}</dd>
              </dl>
              <button className="button button-secondary button-small" type="button" disabled={pending} onClick={() => setAgentEnabled.mutate({ name: agent.name, enabled: !enabled })}>
                {pending ? text("保存中…", "Saving…") : enabled ? text("停用 Agent", "Disable agent") : text("启用 Agent", "Enable agent")}
              </button>
            </article>;
          })}
        </div>
      </section>
      <section>
        <div className="section-heading">
          <div><span className="eyebrow">CONTROLLED EXECUTION</span><h2>Tool Registry</h2></div>
        </div>
        <p className="field-note">{text("工具开关由后端在每次执行前强制校验。apply_patch 不能全局启用，仍需要写入模式与逐次精确确认。", "The backend enforces tool switches before every execution. apply_patch cannot be globally enabled and still requires write mode plus exact per-use confirmation.")}</p>
        {tools.isPending ? <LoadingState label={text("正在读取 Tool Registry…", "Reading Tool Registry…")} /> : null}
        {tools.isError ? <ErrorState title={text("Tool Registry 不可用", "Tool Registry unavailable")} message={errorMessage(tools.error)} /> : null}
        <div className="registry-grid">
          {tools.data?.map((tool) => {
            const confirmationOnly = tool.permission === "WRITE_CONFIRMATION";
            const pending = setToolEnabled.isPending && setToolEnabled.variables?.name === tool.name;
            return <article className="registry-card" key={tool.name}>
              <div className="repository-card-heading">
                <span className="pill">{tool.permission}</span>
                <span className={`pill pill-${tool.enabled ? "active" : "muted"}`}>{confirmationOnly ? "confirmation only" : tool.enabled ? "enabled" : "disabled"}</span>
              </div>
              <h3 className="mono">{tool.name}</h3>
              <p>{tool.description}</p>
              <dl>
                <dt>Timeout</dt><dd>{tool.timeout_seconds}s</dd>
                <dt>Output cap</dt><dd>{Math.round(tool.max_output_bytes / 1024)} KiB</dd>
                <dt>Calls / Errors</dt><dd>{tool.recent_call_count} / {tool.recent_error_count}</dd>
                <dt>Recent error</dt><dd>{tool.most_recent_error ?? "none"}</dd>
              </dl>
              <details><summary>JSON Schema</summary><pre>{JSON.stringify(tool.input_schema, null, 2)}</pre></details>
              <button className="button button-secondary button-small" type="button" disabled={confirmationOnly || pending} onClick={() => setToolEnabled.mutate({ name: tool.name, enabled: !tool.enabled })}>
                {confirmationOnly ? text("必须逐次确认", "Per-use confirmation required") : pending ? text("保存中…", "Saving…") : tool.enabled ? text("停用 Tool", "Disable tool") : text("启用 Tool", "Enable tool")}
              </button>
            </article>;
          })}
        </div>
      </section>
    </div>
  );
}
