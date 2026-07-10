import type { Edge, Node } from "@xyflow/react";

export interface ExportMapNodeData extends Record<string, unknown> {
  label: string;
  kind: string;
  path: string;
  language: string | null;
  symbol: string | null;
}

function escapeXml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&apos;",
  })[character] ?? character);
}

export function repositoryMapSvg(nodes: Node<ExportMapNodeData>[], edges: Edge[]): string {
  const nodeWidth = 220;
  const nodeHeight = 54;
  const padding = 32;
  const maximumX = Math.max(0, ...nodes.map((node) => node.position.x + nodeWidth));
  const maximumY = Math.max(0, ...nodes.map((node) => node.position.y + nodeHeight));
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const edgeMarkup = edges.map((edge) => {
    const source = byId.get(edge.source);
    const target = byId.get(edge.target);
    if (!source || !target) return "";
    return `<line x1="${source.position.x + nodeWidth + padding}" y1="${source.position.y + nodeHeight / 2 + padding}" x2="${target.position.x + padding}" y2="${target.position.y + nodeHeight / 2 + padding}" stroke="#6f7f92" stroke-width="2" />`;
  }).join("");
  const nodeMarkup = nodes.map((node) => `<g transform="translate(${node.position.x + padding} ${node.position.y + padding})"><rect width="${nodeWidth}" height="${nodeHeight}" rx="8" fill="#17212b" stroke="#50d890" /><text x="12" y="22" fill="#f4f7fa" font-family="system-ui, sans-serif" font-size="13">${escapeXml(String(node.data.label).slice(0, 30))}</text><text x="12" y="41" fill="#9aabba" font-family="ui-monospace, monospace" font-size="10">${escapeXml(node.data.kind)}</text></g>`).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${maximumX + padding * 2}" height="${maximumY + padding * 2}" viewBox="0 0 ${maximumX + padding * 2} ${maximumY + padding * 2}"><rect width="100%" height="100%" fill="#0b1118"/>${edgeMarkup}${nodeMarkup}</svg>`;
}

export async function downloadMapPng(name: string, svg: string): Promise<void> {
  const image = new Image();
  const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
  try {
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve();
      image.onerror = () => reject(new Error("SVG could not be rendered for PNG export"));
      image.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Canvas 2D is unavailable");
    context.drawImage(image, 0, 0);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
    if (!blob) throw new Error("PNG encoding failed");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = name;
    link.click();
    URL.revokeObjectURL(link.href);
  } finally {
    URL.revokeObjectURL(url);
  }
}
