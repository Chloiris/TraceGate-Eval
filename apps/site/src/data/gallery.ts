import type { Language } from "../i18n";

export type GalleryScope = "real-local" | "test-fixture" | "controlled-benchmark";

export interface GalleryItem {
  id: string;
  title: Record<Language, string>;
  description: Record<Language, string>;
  scope: GalleryScope;
  scopeLabel: Record<Language, string>;
  source: string;
  focal: "wide" | "tall";
}

const scopes = {
  "real-local": { zh: "真实本地运行", en: "Real local runtime" },
  "test-fixture": { zh: "Playwright 仓库 Fixture", en: "Playwright repository fixture" },
  "controlled-benchmark": { zh: "受控 Benchmark 产物", en: "Controlled benchmark artifact" },
} as const;

function item(
  id: string,
  scope: GalleryScope,
  source: string,
  title: [string, string],
  description: [string, string],
  focal: "wide" | "tall" = "wide",
): GalleryItem {
  return {
    id,
    scope,
    source,
    focal,
    scopeLabel: scopes[scope],
    title: { zh: title[0], en: title[1] },
    description: { zh: description[0], en: description[1] },
  };
}

export const galleryItems: GalleryItem[] = [
  item("dashboard", "real-local", "docs/screenshots/p0-dashboard-macos.png", ["系统概览", "System dashboard"], ["真实显示本地后端、存储和未配置 Provider 状态。", "Real local backend, storage, and explicit unconfigured-provider state."]),
  item("pr-inbox", "test-fixture", "e2e/site-product-captures.spec.ts", ["PR 审查队列", "PR Inbox"], ["Fixture 仓库中的 PR 列表、状态和 Head 绑定入口。", "Fixture Pull Requests with state and Head-bound review entry points."]),
  item("pr-diff", "test-fixture", "docs/screenshots/p1-pr-diff-macos.png", ["PR Diff", "PR Diff"], ["Monaco Diff 将 Finding 与 Evidence 锚定到确切变更行。", "Monaco Diff anchors Findings and Evidence to exact changed lines."]),
  item("findings-evidence", "test-fixture", "e2e/site-product-captures.spec.ts", ["Findings 与 Evidence", "Findings & Evidence"], ["从结构化 Finding 回到 Evidence、路径、行号与 Agent 来源。", "Trace a structured Finding back to Evidence, path, range, and Agent source."]),
  item("repository-map", "test-fixture", "e2e/site-product-captures.spec.ts", ["Repository Map", "Repository Map"], ["Commit 绑定的目录、文件、符号和测试关系视图。", "Commit-bound directories, files, symbols, and test relationships."]),
  item("review-map", "test-fixture", "docs/screenshots/p1-review-map-macos.png", ["Review Map", "Review Map"], ["把真实 Diff、confirmed 静态边、Finding 与 Agent Evidence 合并。", "Combines the real Diff, confirmed static edges, Findings, and Agent Evidence."]),
  item("agent-trace", "test-fixture", "e2e/site-product-captures.spec.ts", ["Agent Trace", "Agent Trace"], ["节点、Tool Call、Evidence 与失败状态保持可观察。", "Nodes, Tool Calls, Evidence, and failure states remain observable."]),
  item("eval-center", "controlled-benchmark", "docs/screenshots/p1-eval-center-macos.png", ["Eval Center", "Eval Center"], ["展示 19 个公共 PR 案例与 160 条 ClaimBench 受控记录。", "Renders 19 public-PR cases and 160 controlled ClaimBench records."], "tall"),
  item("fix-plan", "test-fixture", "docs/screenshots/autofix-playwright-fixture-confirmation-macos.png", ["Fix Plan", "Fix Plan"], ["从既有 Finding 生成结构化目标、步骤、约束与风险。", "A structured objective, steps, constraints, and risks from an existing Finding."], "tall"),
  item("patch-proposal", "test-fixture", "docs/screenshots/autofix-playwright-fixture-confirmation-macos.png", ["Patch Proposal", "Patch Proposal"], ["完整 Unified Diff、影响文件、风险和验证计划保持可检查。", "The full unified diff, affected files, risks, and validation plan stay inspectable."], "tall"),
  item("patch-confirmation", "test-fixture", "docs/screenshots/autofix-playwright-fixture-confirmation-macos.png", ["Patch Hash 确认", "Patch Hash confirmation"], ["确认绑定 Finding、Head SHA、Patch Hash、nonce 与有效期。", "Confirmation binds Finding, Head SHA, Patch Hash, nonce, and expiry."]),
  item("validation", "test-fixture", "e2e/site-product-captures.spec.ts", ["受控验证", "Controlled validation"], ["参数数组命令、返回码和输出摘要被持久化。", "Argument-vector commands, return codes, and bounded output summaries are persisted."]),
  item("final-report", "test-fixture", "docs/screenshots/autofix-playwright-fixture-result-macos.png", ["最终修复报告", "Final Fix Report"], ["验证、re-review、残余风险与 Resolution 同屏呈现。", "Validation, re-review, residual risk, and Resolution in one report."]),
  item("settings", "real-local", "docs/screenshots/p0-settings-macos.png", ["设置与诊断", "Settings & Diagnostics"], ["凭据只显示 configured / missing，原始密钥不会进入页面。", "Credentials expose configured / missing state only; raw secrets never enter the page."], "tall"),
  item("native-shell", "real-local", "docs/screenshots/p0-desktop-macos.png", ["原生桌面外壳", "Native desktop shell"], ["Tauri 窗口、认证 Sidecar 与本地优先体验。", "Tauri window, authenticated Sidecar, and the local-first desktop experience."]),
];

export function imageSources(id: string) {
  return {
    avif: `/media/product/${id}-640.avif 640w, /media/product/${id}-960.avif 960w, /media/product/${id}-1200.avif 1200w`,
    webp: `/media/product/${id}-640.webp 640w, /media/product/${id}-960.webp 960w, /media/product/${id}-1200.webp 1200w`,
    fallback: `/media/product/${id}-960.webp`,
  };
}
