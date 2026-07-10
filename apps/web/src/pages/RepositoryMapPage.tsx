import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useRepositories, useRepositoryGraph } from "../api/queries";
import { ErrorState, LoadingState } from "../components/RequestState";
import { errorMessage } from "../lib/errors";
import { useUiStore } from "../store/uiStore";
import { useI18n } from "../i18n";
import { downloadMapPng, repositoryMapSvg, type ExportMapNodeData } from "../lib/repositoryMapExport";

type MapNodeData = ExportMapNodeData;

function layeredPositions(
  nodeIds: string[],
  graphEdges: { source: string; target: string }[],
): Map<string, { x: number; y: number }> {
  const ids = new Set(nodeIds);
  const incoming = new Map(nodeIds.map((id) => [id, 0]));
  const outgoing = new Map(nodeIds.map((id) => [id, [] as string[]]));
  for (const edge of graphEdges) {
    if (!ids.has(edge.source) || !ids.has(edge.target)) continue;
    incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1);
    outgoing.get(edge.source)?.push(edge.target);
  }
  const layers = new Map(nodeIds.map((id) => [id, 0]));
  const queue = nodeIds.filter((id) => incoming.get(id) === 0).sort();
  for (const source of queue) {
    for (const target of outgoing.get(source) ?? []) {
      layers.set(target, Math.max(layers.get(target) ?? 0, (layers.get(source) ?? 0) + 1));
      incoming.set(target, (incoming.get(target) ?? 1) - 1);
      if (incoming.get(target) === 0) queue.push(target);
    }
  }
  const lanes = new Map<number, string[]>();
  for (const id of nodeIds) {
    const layer = layers.get(id) ?? 0;
    lanes.set(layer, [...(lanes.get(layer) ?? []), id]);
  }
  const positions = new Map<string, { x: number; y: number }>();
  for (const [layer, lane] of lanes) {
    lane.sort().forEach((id, index) => positions.set(id, { x: layer * 260, y: index * 86 }));
  }
  return positions;
}

function download(name: string, content: string, type: string) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([content], { type }));
  link.download = name;
  link.click();
  URL.revokeObjectURL(link.href);
}

export function RepositoryMapPage() {
  const { text } = useI18n();
  const selectedRepositoryId = useUiStore((state) => state.selectedRepositoryId);
  const selectRepository = useUiStore((state) => state.selectRepository);
  const repositories = useRepositories();
  const graph = useRepositoryGraph(selectedRepositoryId ?? undefined);
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("all");
  const [selectedNode, setSelectedNode] = useState<Node<MapNodeData> | null>(null);
  const [layoutError, setLayoutError] = useState<string | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<MapNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    const sourceNodes = graph.data?.nodes.filter((node) =>
      (kind === "all" || node.kind === kind)
      && (!query || `${node.label} ${node.path} ${node.symbol ?? ""}`.toLocaleLowerCase().includes(query))) ?? [];
    const boundedNodes = sourceNodes.slice(0, 800);
    const ids = new Set(boundedNodes.map((node) => node.id));
    return {
      nodes: boundedNodes,
      edges: graph.data?.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)) ?? [],
    };
  }, [graph.data, kind, search]);

  const layout = useCallback(() => {
    setLayoutError(null);
    try {
      const positions = layeredPositions(filtered.nodes.map((node) => node.id), filtered.edges);
      setNodes(filtered.nodes.map((node) => {
        const position = positions.get(node.id);
        return {
          id: node.id,
          position: position ?? { x: 0, y: 0 },
          data: { label: node.label, kind: node.kind, path: node.path, language: node.language, symbol: node.symbol },
          className: `map-node map-node-${node.kind}`,
        };
      }));
      setEdges(filtered.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.kind,
        animated: false,
        className: `map-edge map-edge-${edge.kind}`,
      })));
    } catch (error) {
      setLayoutError(errorMessage(error));
    }
  }, [filtered.edges, filtered.nodes, setEdges, setNodes]);

  useEffect(() => { layout(); }, [layout]);

  const kinds = useMemo(() => Array.from(new Set(graph.data?.nodes.map((node) => node.kind) ?? [])).sort(), [graph.data]);

  return (
    <div className="page-stack map-page">
      <header className="page-header"><span className="eyebrow">STATIC REPOSITORY GRAPH</span><h2>Repository Map</h2><p>{text("节点和关系来自当前索引版本；关键词检索不会被标记成向量检索。", "Nodes and relationships come from the current index version; keyword retrieval is never labelled as vector search.")}</p></header>
      <section className="filter-bar">
        <label className="field"><span>{text("仓库", "Repository")}</span><select value={selectedRepositoryId ?? ""} onChange={(event) => selectRepository(event.target.value, "repository-map")}><option value="" disabled>{text("选择已索引仓库", "Select an indexed repository")}</option>{repositories.data?.items.map((repository) => <option key={repository.id} value={repository.id}>{repository.full_name}</option>)}</select></label>
        <label className="field"><span>{text("搜索路径或符号", "Search path or symbol")}</span><input value={search} onChange={(event) => setSearch(event.target.value)} /></label>
        <label className="field"><span>{text("节点类型", "Node type")}</span><select value={kind} onChange={(event) => setKind(event.target.value)}><option value="all">{text("全部", "All")}</option>{kinds.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <button className="button button-secondary" type="button" disabled={!graph.data} onClick={layout}>{text("重新布局", "Relayout")}</button>
        <button className="button button-secondary" type="button" disabled={!graph.data} onClick={() => graph.data && download("tracegate-repository-map.json", JSON.stringify(graph.data, null, 2), "application/json")}>{text("导出 JSON", "Export JSON")}</button>
        <button className="button button-secondary" type="button" disabled={nodes.length === 0} onClick={() => download("tracegate-repository-map.svg", repositoryMapSvg(nodes, edges), "image/svg+xml")}>{text("导出 SVG", "Export SVG")}</button>
        <button className="button button-secondary" type="button" disabled={nodes.length === 0} onClick={() => void downloadMapPng("tracegate-repository-map.png", repositoryMapSvg(nodes, edges)).catch((error: unknown) => setLayoutError(errorMessage(error)))}>{text("导出 PNG", "Export PNG")}</button>
      </section>
      {!selectedRepositoryId ? <div className="honest-empty-state"><div className="empty-mark">MAP</div><div><h2>{text("请选择已索引仓库", "Select an indexed repository")}</h2><p>{text("Repository Map 不会在没有真实索引时生成示例节点。", "Repository Map never generates example nodes without a real index.")}</p></div></div> : null}
      {graph.isPending ? <LoadingState label={text("正在加载静态图…", "Loading static graph…")} /> : null}
      {graph.isError ? <ErrorState title={text("Repository Map 不可用", "Repository Map unavailable")} message={errorMessage(graph.error)} onRetry={() => void graph.refetch()} /> : null}
      {graph.data && graph.data.nodes.length > 800 ? <p className="blocker-note">{text("当前视图限制为前 800 个匹配节点；请使用路径、符号或类型筛选缩小范围。", "The view is capped at the first 800 matching nodes; narrow it by path, symbol, or type.")}</p> : null}
      {layoutError ? <p className="inline-error" role="alert">{text("布局失败", "Layout failed")}: {layoutError}</p> : null}
      {graph.data ? <div className="map-layout"><div className="repository-flow"><ReactFlow<Node<MapNodeData>, Edge> nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onNodeClick={(_event, node) => setSelectedNode(node)} fitView selectionOnDrag panOnScroll><Background /><MiniMap pannable zoomable /><Controls /></ReactFlow></div><aside className="inspector-panel"><span className="eyebrow">NODE INSPECTOR</span>{selectedNode ? <><h3>{selectedNode.data.label}</h3><dl className="metadata-grid single"><div><dt>{text("路径", "Path")}</dt><dd>{selectedNode.data.path}</dd></div><div><dt>{text("类型", "Type")}</dt><dd>{selectedNode.data.kind}</dd></div><div><dt>{text("语言", "Language")}</dt><dd>{selectedNode.data.language ?? text("未知", "Unknown")}</dd></div><div><dt>{text("符号", "Symbol")}</dt><dd>{selectedNode.data.symbol ?? text("文件节点", "File node")}</dd></div><div><dt>{text("入边", "Incoming")}</dt><dd>{edges.filter((edge) => edge.target === selectedNode.id).length}</dd></div><div><dt>{text("出边", "Outgoing")}</dt><dd>{edges.filter((edge) => edge.source === selectedNode.id).length}</dd></div></dl></> : <p>{text("点击节点查看真实索引元数据。", "Click a node to inspect real index metadata.")}</p>}<div className="graph-legend"><strong>{text("关系图例", "Relationship legend")}</strong><span className="legend-solid">contains</span><span className="legend-dashed">import</span><span className="legend-dotted">call</span></div><p className="field-note">{graph.data.vector_search_message}</p></aside></div> : null}
    </div>
  );
}
