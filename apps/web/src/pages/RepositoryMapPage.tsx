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

import {
  useEvidence,
  useFindings,
  usePullRequest,
  useRepositories,
  useRepositoryGraph,
} from "../api/queries";
import { ErrorState, LoadingState } from "../components/RequestState";
import type { HostBridge } from "../host/hostBridge";
import { useI18n } from "../i18n";
import { errorMessage } from "../lib/errors";
import { downloadMapPng, repositoryMapSvg, type ExportMapNodeData } from "../lib/repositoryMapExport";
import { useUiStore } from "../store/uiStore";

type MapNodeData = ExportMapNodeData;
type DetailLevel = "directories" | "files" | "symbols";
type Neighborhood = "all" | "1" | "2";

interface SavedView {
  search: string;
  kind: string;
  language: string;
  directory: string;
  relation: string;
  detailLevel: DetailLevel;
  prOnly: boolean;
  highRiskOnly: boolean;
  neighborhood: Neighborhood;
}

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

function neighborhoodIds(
  selectedId: string | null,
  depth: Neighborhood,
  edges: { source: string; target: string }[],
): Set<string> | null {
  if (!selectedId || depth === "all") return null;
  const allowed = new Set([selectedId]);
  let frontier = new Set([selectedId]);
  for (let hop = 0; hop < Number(depth); hop += 1) {
    const next = new Set<string>();
    for (const edge of edges) {
      if (frontier.has(edge.source)) next.add(edge.target);
      if (frontier.has(edge.target)) next.add(edge.source);
    }
    for (const id of next) allowed.add(id);
    frontier = next;
  }
  return allowed;
}

export function RepositoryMapPage({ host }: { host: HostBridge }) {
  const { text } = useI18n();
  const selectedRepositoryId = useUiStore((state) => state.selectedRepositoryId);
  const selectedPullRequestId = useUiStore((state) => state.selectedPullRequestId);
  const selectedRunId = useUiStore((state) => state.selectedRunId);
  const selectRepository = useUiStore((state) => state.selectRepository);
  const selectDiffPath = useUiStore((state) => state.selectDiffPath);
  const setActiveView = useUiStore((state) => state.setActiveView);
  const repositories = useRepositories();
  const graph = useRepositoryGraph(selectedRepositoryId ?? undefined);
  const pullRequest = usePullRequest(selectedPullRequestId ?? undefined);
  const findings = useFindings(selectedRunId ?? undefined);
  const evidence = useEvidence(selectedRunId ?? undefined);
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("all");
  const [language, setLanguage] = useState("all");
  const [directory, setDirectory] = useState("all");
  const [relation, setRelation] = useState("all");
  const [detailLevel, setDetailLevel] = useState<DetailLevel>("directories");
  const [prOnly, setPrOnly] = useState(false);
  const [highRiskOnly, setHighRiskOnly] = useState(false);
  const [neighborhood, setNeighborhood] = useState<Neighborhood>("all");
  const [collapsedDirectories, setCollapsedDirectories] = useState<Set<string>>(new Set());
  const [selectedNode, setSelectedNode] = useState<Node<MapNodeData> | null>(null);
  const [layoutError, setLayoutError] = useState<string | null>(null);
  const [viewMessage, setViewMessage] = useState<string | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<MapNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const selectedRepository = repositories.data?.items.find((item) => item.id === selectedRepositoryId);
  const selectedWorkspace = selectedRepository?.local_path ?? null;
  const prPaths = useMemo(() => new Set([
    ...(pullRequest.data?.impact_paths_json ?? []),
    ...(pullRequest.data?.recommended_review_order_json ?? []),
  ]), [pullRequest.data?.impact_paths_json, pullRequest.data?.recommended_review_order_json]);
  const selectedPrIsHighRisk = pullRequest.data?.risk_level === "high" || pullRequest.data?.risk_level === "critical";
  const selectedGraphId = selectedNode?.id ?? null;

  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    const levelKinds = detailLevel === "directories"
      ? new Set(["repository", "directory"])
      : detailLevel === "files"
        ? new Set(["repository", "directory", "file", "test"])
        : null;
    const related = neighborhoodIds(selectedGraphId, neighborhood, graph.data?.edges ?? []);
    const sourceNodes = graph.data?.nodes.filter((node) => {
      if (levelKinds && !levelKinds.has(node.kind)) return false;
      if (kind !== "all" && node.kind !== kind) return false;
      if (language !== "all" && node.language !== null && node.language !== language) return false;
      if (directory !== "all" && node.path !== directory && !node.path.startsWith(`${directory}/`)) return false;
      if ([...collapsedDirectories].some((path) => node.path !== path && node.path.startsWith(`${path}/`))) return false;
      if ((prOnly || highRiskOnly) && !prPaths.has(node.path)) return false;
      if (highRiskOnly && !selectedPrIsHighRisk) return false;
      if (related && !related.has(node.id)) return false;
      return !query || `${node.label} ${node.path} ${node.symbol ?? ""}`.toLocaleLowerCase().includes(query);
    }) ?? [];
    const boundedNodes = sourceNodes.slice(0, 800);
    const ids = new Set(boundedNodes.map((node) => node.id));
    return {
      totalNodes: sourceNodes.length,
      nodes: boundedNodes,
      edges: graph.data?.edges.filter((edge) =>
        ids.has(edge.source)
        && ids.has(edge.target)
        && (relation === "all" || edge.kind === relation)) ?? [],
    };
  }, [collapsedDirectories, detailLevel, directory, graph.data, highRiskOnly, kind, language, neighborhood, prOnly, prPaths, relation, search, selectedGraphId, selectedPrIsHighRisk]);

  const layout = useCallback(() => {
    setLayoutError(null);
    try {
      const positions = layeredPositions(filtered.nodes.map((node) => node.id), filtered.edges);
      setNodes(filtered.nodes.map((node) => ({
        id: node.id,
        position: positions.get(node.id) ?? { x: 0, y: 0 },
        data: { label: node.label, kind: node.kind, path: node.path, language: node.language, symbol: node.symbol },
        className: `map-node map-node-${node.kind}`,
      })));
      setEdges(filtered.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.kind,
        animated: false,
        className: `map-edge map-edge-${edge.kind} ${edge.confirmed ? "map-edge-confirmed" : "map-edge-unconfirmed"}`,
      })));
    } catch (error) {
      setLayoutError(errorMessage(error));
    }
  }, [filtered.edges, filtered.nodes, setEdges, setNodes]);

  useEffect(() => { layout(); }, [layout]);
  useEffect(() => {
    setSelectedNode(null);
    setCollapsedDirectories(new Set());
  }, [selectedRepositoryId]);

  const kinds = useMemo(() => Array.from(new Set(graph.data?.nodes.map((node) => node.kind) ?? [])).sort(), [graph.data]);
  const languages = useMemo(() => Array.from(new Set(graph.data?.nodes.map((node) => node.language).filter((item): item is string => Boolean(item)) ?? [])).sort(), [graph.data]);
  const directories = useMemo(() => graph.data?.nodes.filter((node) => node.kind === "directory").map((node) => node.path).sort() ?? [], [graph.data]);
  const relations = useMemo(() => Array.from(new Set(graph.data?.edges.map((edge) => edge.kind) ?? [])).sort(), [graph.data]);

  function toggleDirectory(path: string) {
    setCollapsedDirectories((current) => {
      const next = new Set(current);
      if (next.has(path)) next.delete(path); else next.add(path);
      return next;
    });
  }

  function currentView(): SavedView {
    return { search, kind, language, directory, relation, detailLevel, prOnly, highRiskOnly, neighborhood };
  }

  function saveView() {
    if (!selectedRepositoryId) return;
    localStorage.setItem(`tracegate:repository-map:${selectedRepositoryId}`, JSON.stringify(currentView()));
    setViewMessage(text("当前非敏感筛选视图已保存在本机。", "The current non-secret filter view was saved locally."));
  }

  function restoreView() {
    if (!selectedRepositoryId) return;
    try {
      const raw = localStorage.getItem(`tracegate:repository-map:${selectedRepositoryId}`);
      if (!raw) throw new Error(text("尚未保存视图。", "No saved view exists."));
      const saved = JSON.parse(raw) as Partial<SavedView>;
      setSearch(typeof saved.search === "string" ? saved.search : "");
      setKind(typeof saved.kind === "string" ? saved.kind : "all");
      setLanguage(typeof saved.language === "string" ? saved.language : "all");
      setDirectory(typeof saved.directory === "string" ? saved.directory : "all");
      setRelation(typeof saved.relation === "string" ? saved.relation : "all");
      setDetailLevel(["directories", "files", "symbols"].includes(saved.detailLevel ?? "") ? saved.detailLevel as DetailLevel : "directories");
      setPrOnly(Boolean(saved.prOnly));
      setHighRiskOnly(Boolean(saved.highRiskOnly));
      setNeighborhood(["all", "1", "2"].includes(saved.neighborhood ?? "") ? saved.neighborhood as Neighborhood : "all");
      setViewMessage(text("已恢复本机保存的视图。", "Restored the locally saved view."));
    } catch (error) {
      setLayoutError(errorMessage(error));
    }
  }

  function openDiff(path: string) {
    if (!selectedPullRequestId) return;
    selectDiffPath(path);
    setActiveView("pull-request-detail");
  }

  const incoming = selectedNode ? edges.filter((edge) => edge.target === selectedNode.id) : [];
  const outgoing = selectedNode ? edges.filter((edge) => edge.source === selectedNode.id) : [];
  const neighborIds = new Set([...incoming.map((edge) => edge.source), ...outgoing.map((edge) => edge.target)]);
  const relatedTests = nodes.filter((node) => neighborIds.has(node.id) && node.data.kind === "test");
  const selectedFindings = findings.data?.filter((item) => item.file_path === selectedNode?.data.path) ?? [];
  const selectedEvidence = evidence.data?.filter((item) => item.file_path === selectedNode?.data.path) ?? [];

  return (
    <div className="page-stack map-page">
      <header className="page-header"><span className="eyebrow">STATIC REPOSITORY GRAPH</span><h2>Repository Map</h2><p>{text("节点和关系来自当前索引版本；默认只展开目录级聚合，关键词检索不会被标记成向量检索。", "Nodes and relationships come from the current index version. The default view is directory aggregation, and keyword retrieval is never labelled vector search.")}</p></header>
      <section className="filter-bar">
        <label className="field"><span>{text("仓库", "Repository")}</span><select value={selectedRepositoryId ?? ""} onChange={(event) => selectRepository(event.target.value, "repository-map")}><option value="" disabled>{text("选择已索引仓库", "Select an indexed repository")}</option>{repositories.data?.items.map((repository) => <option key={repository.id} value={repository.id}>{repository.full_name}</option>)}</select></label>
        <label className="field"><span>{text("层级", "Detail level")}</span><select value={detailLevel} onChange={(event) => setDetailLevel(event.target.value as DetailLevel)}><option value="directories">{text("目录聚合", "Directories")}</option><option value="files">{text("目录与文件", "Directories and files")}</option><option value="symbols">{text("文件与符号", "Files and symbols")}</option></select></label>
        <label className="field"><span>{text("搜索路径或符号", "Search path or symbol")}</span><input value={search} onChange={(event) => setSearch(event.target.value)} /></label>
        <label className="field"><span>{text("节点类型", "Node type")}</span><select value={kind} onChange={(event) => setKind(event.target.value)}><option value="all">{text("全部", "All")}</option>{kinds.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label className="field"><span>{text("语言", "Language")}</span><select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="all">{text("全部", "All")}</option>{languages.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label className="field"><span>{text("目录", "Directory")}</span><select value={directory} onChange={(event) => setDirectory(event.target.value)}><option value="all">{text("全部", "All")}</option>{directories.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label className="field"><span>{text("关系", "Relationship")}</span><select value={relation} onChange={(event) => setRelation(event.target.value)}><option value="all">{text("全部", "All")}</option>{relations.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label className="field"><span>{text("邻接范围", "Neighborhood")}</span><select value={neighborhood} disabled={!selectedNode} onChange={(event) => setNeighborhood(event.target.value as Neighborhood)}><option value="all">{text("全部", "All")}</option><option value="1">{text("一跳", "1 hop")}</option><option value="2">{text("二跳", "2 hops")}</option></select></label>
        <label className="filter-check"><input type="checkbox" checked={prOnly} disabled={!selectedPullRequestId || prPaths.size === 0} onChange={(event) => setPrOnly(event.target.checked)} />{text("只看当前 PR 相关", "Current PR only")}</label>
        <label className="filter-check"><input type="checkbox" checked={highRiskOnly} disabled={!selectedPrIsHighRisk || prPaths.size === 0} onChange={(event) => setHighRiskOnly(event.target.checked)} />{text("只看高风险", "High risk only")}</label>
        <button className="button button-secondary" type="button" disabled={!graph.data} onClick={layout}>{text("重新布局", "Relayout")}</button>
        <button className="button button-secondary" type="button" disabled={!graph.data} onClick={saveView}>{text("保存视图", "Save view")}</button>
        <button className="button button-secondary" type="button" disabled={!graph.data} onClick={restoreView}>{text("恢复视图", "Restore view")}</button>
        <button className="button button-secondary" type="button" disabled={!graph.data} onClick={() => graph.data && download("tracegate-repository-map.json", JSON.stringify(graph.data, null, 2), "application/json")}>{text("导出 JSON", "Export JSON")}</button>
        <button className="button button-secondary" type="button" disabled={nodes.length === 0} onClick={() => download("tracegate-repository-map.svg", repositoryMapSvg(nodes, edges), "image/svg+xml")}>{text("导出 SVG", "Export SVG")}</button>
        <button className="button button-secondary" type="button" disabled={nodes.length === 0} onClick={() => void downloadMapPng("tracegate-repository-map.png", repositoryMapSvg(nodes, edges)).catch((error: unknown) => setLayoutError(errorMessage(error)))}>{text("导出 PNG", "Export PNG")}</button>
      </section>
      {selectedNode ? <nav className="path-breadcrumb" aria-label={text("节点路径", "Node path")}>{selectedNode.data.path.split("/").map((part, index, parts) => <button type="button" key={`${part}-${index}`} onClick={() => setDirectory(index === parts.length - 1 ? "all" : parts.slice(0, index + 1).join("/"))}>{part}</button>)}</nav> : null}
      {!selectedRepositoryId ? <div className="honest-empty-state"><div className="empty-mark">MAP</div><div><h2>{text("请选择已索引仓库", "Select an indexed repository")}</h2><p>{text("Repository Map 不会在没有真实索引时生成示例节点。", "Repository Map never generates example nodes without a real index.")}</p></div></div> : null}
      {graph.isPending ? <LoadingState label={text("正在加载静态图…", "Loading static graph…")} /> : null}
      {graph.isError ? <ErrorState title={text("Repository Map 不可用", "Repository Map unavailable")} message={errorMessage(graph.error)} onRetry={() => void graph.refetch()} /> : null}
      {filtered.totalNodes > 800 ? <p className="blocker-note">{text(`当前视图有 ${filtered.totalNodes} 个匹配节点，只渲染前 800 个；请按目录、语言、类型或关系缩小范围。`, `This view has ${filtered.totalNodes} matching nodes and renders only the first 800. Narrow it by directory, language, type, or relationship.`)}</p> : null}
      {selectedPullRequestId && prPaths.size === 0 ? <p className="field-note">{text("当前 PR 尚无持久化影响路径，因此 PR/高风险筛选保持禁用。", "The current PR has no persisted impact paths, so PR/high-risk filters remain disabled.")}</p> : null}
      {layoutError ? <p className="inline-error" role="alert">{text("布局或视图操作失败", "Layout or view operation failed")}: {layoutError}</p> : null}
      {viewMessage ? <p className="inline-success" role="status">{viewMessage}</p> : null}
      {graph.data ? <div className="map-layout"><div className="repository-flow"><ReactFlow<Node<MapNodeData>, Edge> nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onNodeClick={(_event, node) => setSelectedNode(node)} onNodeDoubleClick={(_event, node) => node.data.kind === "directory" ? toggleDirectory(node.data.path) : openDiff(node.data.path)} fitView selectionOnDrag panOnScroll><Background /><MiniMap pannable zoomable /><Controls /></ReactFlow></div><aside className="inspector-panel"><span className="eyebrow">NODE INSPECTOR</span>{selectedNode ? <><h3>{selectedNode.data.label}</h3><dl className="metadata-grid single"><div><dt>{text("路径", "Path")}</dt><dd>{selectedNode.data.path}</dd></div><div><dt>{text("类型", "Type")}</dt><dd>{selectedNode.data.kind}</dd></div><div><dt>{text("语言", "Language")}</dt><dd>{selectedNode.data.language ?? text("不适用", "Not applicable")}</dd></div><div><dt>{text("符号签名", "Symbol signature")}</dt><dd>{selectedNode.data.symbol ?? text("非符号节点", "Not a symbol node")}</dd></div><div><dt>{text("入边 / 出边", "Incoming / outgoing")}</dt><dd>{incoming.length} / {outgoing.length}</dd></div><div><dt>{text("相关测试", "Related tests")}</dt><dd>{relatedTests.length ? relatedTests.map((item) => item.data.path).join(" · ") : text("当前可见关系中无测试节点", "No test nodes in visible relationships")}</dd></div><div><dt>{text("最近提交", "Current indexed commit")}</dt><dd className="mono">{graph.data.commit_sha}</dd></div><div><dt>{text("当前 PR 变更", "Current PR change")}</dt><dd>{prPaths.has(selectedNode.data.path) ? text("有持久化影响证据", "Persisted impact evidence") : text("未标记", "Not marked")}</dd></div><div><dt>Findings / Evidence</dt><dd>{selectedFindings.length} / {selectedEvidence.length}</dd></div><div><dt>{text("文件摘要", "File summary")}</dt><dd>{text(`静态索引中的 ${selectedNode.data.kind} 节点。`, `${selectedNode.data.kind} node from the static index.`)}</dd></div></dl><div className="action-row compact">{selectedNode.data.kind === "directory" ? <button className="button button-secondary button-small" type="button" onClick={() => toggleDirectory(selectedNode.data.path)}>{collapsedDirectories.has(selectedNode.data.path) ? text("展开目录", "Expand directory") : text("折叠目录", "Collapse directory")}</button> : null}<button className="button button-secondary button-small" type="button" disabled={!selectedPullRequestId || selectedNode.data.kind === "repository" || selectedNode.data.kind === "directory"} onClick={() => openDiff(selectedNode.data.path)}>{text("打开 Diff", "Open Diff")}</button>{selectedWorkspace ? <button className="button button-secondary button-small" type="button" disabled={!host.openWorkspace} onClick={() => void host.openWorkspace?.(selectedWorkspace, true)}>VS Code</button> : null}{selectedRepository ? <a className="button button-secondary button-small" href={`https://github.com/${selectedRepository.full_name}/blob/${graph.data.commit_sha}/${selectedNode.data.path}`} target="_blank" rel="noreferrer">GitHub</a> : null}</div></> : <p>{text("点击节点查看真实索引元数据；双击目录折叠，双击代码节点跳转当前 PR Diff。", "Click a node to inspect real index metadata. Double-click a directory to collapse it or a code node to open the current PR diff.")}</p>}<div className="graph-legend"><strong>{text("关系图例", "Relationship legend")}</strong>{relations.map((item) => <span className={`legend-${item}`} key={item}>{item}</span>)}</div><p className="field-note">{graph.data.vector_search_message}</p></aside></div> : null}
    </div>
  );
}
