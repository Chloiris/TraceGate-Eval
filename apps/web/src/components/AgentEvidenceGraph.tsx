import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useRunEvidenceGraph } from "../api/queries";
import { ErrorState, LoadingState } from "./RequestState";
import { errorMessage } from "../lib/errors";
import { useI18n } from "../i18n";

const kindColumn: Record<string, number> = {
  user_task: 0,
  agent_step: 1,
  tool_call: 2,
  evidence: 3,
  finding: 4,
};

export function AgentEvidenceGraph({ runId }: { runId: string }) {
  const { text } = useI18n();
  const graph = useRunEvidenceGraph(runId);
  if (graph.isPending) return <LoadingState label={text("正在读取 Agent Evidence Graph…", "Reading Agent Evidence Graph…")} />;
  if (graph.isError) return <ErrorState title={text("Agent Evidence Graph 不可用", "Agent Evidence Graph unavailable")} message={errorMessage(graph.error)} />;
  const counters = new Map<number, number>();
  const nodes: Node[] = graph.data.nodes.map((node) => {
    const column = kindColumn[node.kind] ?? 2;
    const row = counters.get(column) ?? 0;
    counters.set(column, row + 1);
    return {
      id: node.id,
      position: { x: column * 280, y: row * 95 },
      data: { label: `${node.kind} · ${node.label}` },
      title: [node.detail, node.path, node.commit_sha].filter(Boolean).join("\n"),
      className: `evidence-graph-node evidence-kind-${node.kind}`,
    };
  });
  const edges: Edge[] = graph.data.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.kind,
    className: edge.confirmed ? "map-edge-confirmed" : "map-edge-unconfirmed",
  }));
  return <section className="evidence-graph-section"><div className="section-heading"><div><span className="eyebrow">TRACE PROVENANCE</span><h2>Agent Evidence Graph</h2></div></div><p className="field-note">{graph.data.message}</p><div className="evidence-flow"><ReactFlow nodes={nodes} edges={edges} fitView><Background /><MiniMap /><Controls /></ReactFlow></div></section>;
}
