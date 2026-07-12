import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

export type Language = "zh" | "en";

const descriptions = {
  zh: "面向 GitHub Pull Request 的证据驱动代码审查、代码可视化与受控 Autofix 平台。",
  en: "Evidence-grounded Pull Request review, code intelligence, and controlled Coding Agent Autofix.",
} as const;

const LanguageContext = createContext<{
  language: Language;
  setLanguage: (language: Language) => void;
} | null>(null);

function initialLanguage(): Language {
  const saved = window.localStorage.getItem("tracegate-site-language");
  return saved === "en" ? "en" : "zh";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(initialLanguage);

  useEffect(() => {
    window.localStorage.setItem("tracegate-site-language", language);
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
    document.title = "TraceGate Studio — Evidence-grounded AI Coding Agent";
    const meta = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    meta?.setAttribute("content", descriptions[language]);
  }, [language]);

  const value = useMemo(() => ({ language, setLanguage }), [language]);
  return <LanguageContext value={value}>{children}</LanguageContext>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("useLanguage must be used inside LanguageProvider");
  return context;
}

export const copy = {
  zh: {
    nav: {
      product: "产品",
      autofix: "受控修复",
      intelligence: "代码智能",
      evidence: "证据链",
      architecture: "架构",
      verification: "验证",
      github: "GitHub",
      menu: "打开导航",
      close: "关闭导航",
    },
    hero: {
      eyebrow: "EVIDENCE-GROUNDED CODING AGENT",
      titleA: "审查有证据。",
      titleB: "修复有控制。",
      body: "TraceGate Studio 是面向 GitHub Pull Request 的本地优先 AI Coding Agent 工作区，把代码索引、证据驱动审查、影响分析与受控 Autofix 统一为一条可观察、可验证的完整流程。",
      primary: "查看产品演示",
      secondary: "查看 GitHub",
      architecture: "技术架构",
      preview: "Windows preview verified in CI",
      status: "OPEN SOURCE · LOCAL FIRST · HUMAN CONTROL",
      graphLabel: "实时证据关系图",
    },
    proof: {
      label: "经过边界说明的工程证据",
      note: "TraceGate Studio 0.4.0 的 source-bound verification。数字来自构建时同步的 project-facts，不代表用户量、准确率或修复成功率。",
      review: "Review 节点",
      autofix: "Autofix 节点",
      tools: "受控工具",
      python: "Python 测试",
      typescript: "TypeScript 测试",
      rust: "Rust 测试",
      playwright: "Playwright 流程",
    },
    problem: {
      eyebrow: "CONTEXT SAFETY",
      title: "测试通过，不代表修改安全。",
      lead: "真正危险的不是 Agent 会写代码，而是它可能在证据不足时仍然给出确定答案。",
      risks: ["信任过期上下文", "引用错误提交", "忽略冲突证据", "误解代码关系", "生成未验证 Patch", "失败后仍声称完成"],
      statement: "TraceGate 把“为什么相信这个结论”变成产品的一等数据。",
      chain: [
        ["HEAD BINDING", "每个结论绑定当前 Head SHA"],
        ["EVIDENCE", "Finding 必须有可定位证据"],
        ["TRACE", "Tool Call 与 Agent Step 可追溯"],
        ["STATIC TRUTH", "confirmed / inferred / unknown 不混写"],
        ["HUMAN GATE", "Autofix 由用户发起并确认"],
        ["DETERMINISTIC END", "验证失败永不成为 RESOLVED"],
      ],
    },
    capabilities: {
      eyebrow: "ONE WORKSPACE · SIX LENSES",
      title: "从代码变更，到可验证的决策闭环。",
      body: "每个界面都回答一个不同的问题；它们共享同一条 Commit、Evidence 与 Agent Trace 身份链。",
    },
    review: {
      eyebrow: "READ-ONLY BY DEFAULT",
      title: "七个可观察节点，而不是七个独立大模型。",
      body: "Review 是持久化的 LangGraph Workflow。每个节点都有输入、输出、工具调用和证据边界；默认只读。",
      input: "输入",
      output: "输出",
      evidence: "证据边界",
      readonly: "Review workflow · READ ONLY",
    },
    autofix: {
      eyebrow: "CONTROLLED AUTOFIX",
      title: "把自由生成，变成一条可审计的修复事务。",
      body: "Fix 与 Review 完全分离。只有从既有 Finding 发起，经过精确 Patch Hash 确认，才可在隔离 Worktree 中应用和验证。",
      finding: "Finding",
      confirmation: "用户确认",
      worktree: "隔离工作区",
      validation: "真实验证",
      resolution: "确定性结果",
      boundaries: ["不修改原始工作区", "不自动 commit", "不自动 push", "不自动评论 PR", "失败测试不能 RESOLVED"],
      demoTitle: "一次修复，十一段可观察状态",
      demoHint: "选择任一节点查看它在受控事务中的职责。",
    },
    intelligence: {
      eyebrow: "CODE INTELLIGENCE",
      title: "静态关系、变更影响与 Agent 证据，在同一张图上保持诚实。",
      body: "Repository Map 只展示解析器确认的边；Review Map 再叠加 Diff、Finding 与 Evidence。无法确认的关系保持 inferred 或 unknown。",
      confirmed: "confirmed 静态边",
      inferred: "inferred 关系",
      unknown: "unknown / 上下文缺口",
      locate: "点击 Finding，回到确切 Diff 行范围。",
    },
    gallery: {
      eyebrow: "PRODUCT GALLERY",
      title: "真实运行画面，逐张标明证据范围。",
      body: "截图来自 macOS 本地运行、Playwright 仓库 Fixture 或受控 Benchmark。Fixture 从不被称为公共 PR 真实分析。",
      open: "放大查看",
      close: "关闭图片",
      previous: "上一张",
      next: "下一张",
    },
    architecture: {
      eyebrow: "SYSTEM ARCHITECTURE",
      title: "本地优先，不等于不可观察。",
      body: "Tauri 管理本地生命周期与凭据，FastAPI Sidecar 承载索引、工作流与受控工具；所有 Evidence、Finding 和 Trace 都进入可检查的持久化层。",
      flow: "数据与信任边界",
    },
    verification: {
      eyebrow: "TRUST THROUGH EXPLICIT BOUNDARIES",
      title: "可信，不来自把所有格子涂成绿色。",
      body: "TraceGate 把已验证、仅 CI 验证和仍需人工验收的范围公开展示。边界清楚，本身就是产品能力。",
      verified: "已验证",
      verifiedCi: "CI 已验证",
      blocked: "待外部条件",
      notes: [
        "VERIFIED_WINDOWS_CI 不等于 Windows GUI 人工验收。",
        "真实 Autofix E2E 使用真实 DeepSeek，但仓库内容为合成临时 Git 仓库。",
        "当前不声称公共 PR 自动修复成功率。",
        "不声称完整 JS / TS / Java 语义调用图。",
        "验证命令具有 argv/cwd/env 约束，但不是 OS / 容器级沙箱。",
      ],
    },
    security: {
      eyebrow: "GUARDRAILS AROUND THE AGENT",
      title: "Agent 在护栏内工作，而不是护栏写在提示词里。",
      body: "密钥、路径、Patch、命令和工作区都由应用层策略控制；模型输出始终是不可信输入。",
    },
    cta: {
      eyebrow: "OPEN SOURCE",
      title: "Every patch should explain itself.",
      body: "阅读源码、验证记录与安全模型，了解 TraceGate 如何把 Evidence 与 Human Control 放进 Coding Agent 的默认路径。",
      primary: "在 GitHub 探索 TraceGate",
      built: "Built by Chloiris",
      links: ["中文 README", "技术架构", "Autofix 安全", "验证记录", "MIT License"],
    },
  },
  en: {
    nav: {
      product: "Product",
      autofix: "Autofix",
      intelligence: "Code Intelligence",
      evidence: "Evidence",
      architecture: "Architecture",
      verification: "Verification",
      github: "GitHub",
      menu: "Open navigation",
      close: "Close navigation",
    },
    hero: {
      eyebrow: "EVIDENCE-GROUNDED CODING AGENT",
      titleA: "Review with evidence.",
      titleB: "Fix with control.",
      body: "TraceGate Studio is a local-first AI Coding Agent workspace for GitHub Pull Requests, unifying code indexing, evidence-grounded review, visual impact analysis, and controlled Autofix in one observable, verifiable loop.",
      primary: "Explore the Product",
      secondary: "View on GitHub",
      architecture: "Architecture",
      preview: "Windows preview verified in CI",
      status: "OPEN SOURCE · LOCAL FIRST · HUMAN CONTROL",
      graphLabel: "Live evidence relationship graph",
    },
    proof: {
      label: "Engineering evidence with explicit scope",
      note: "Source-bound verification for TraceGate Studio 0.4.0. Counts are generated from project-facts and are not users, accuracy, or fix-success metrics.",
      review: "Review nodes",
      autofix: "Autofix nodes",
      tools: "Controlled tools",
      python: "Python tests",
      typescript: "TypeScript tests",
      rust: "Rust tests",
      playwright: "Playwright flows",
    },
    problem: {
      eyebrow: "CONTEXT SAFETY",
      title: "Passing tests do not make a change safe.",
      lead: "The real risk is not that an Agent can write code. It is that it can sound certain while the evidence is incomplete.",
      risks: ["Trust stale context", "Reference the wrong commit", "Ignore conflicting evidence", "Misread code relationships", "Generate an unverified patch", "Claim completion after failure"],
      statement: "TraceGate makes “why should I trust this conclusion?” a first-class product object.",
      chain: [
        ["HEAD BINDING", "Every conclusion is bound to the current Head SHA"],
        ["EVIDENCE", "Every Finding must point to inspectable evidence"],
        ["TRACE", "Tool Calls and Agent Steps stay attributable"],
        ["STATIC TRUTH", "confirmed / inferred / unknown remain distinct"],
        ["HUMAN GATE", "Autofix starts and proceeds through human control"],
        ["DETERMINISTIC END", "Failed validation can never become RESOLVED"],
      ],
    },
    capabilities: {
      eyebrow: "ONE WORKSPACE · SIX LENSES",
      title: "From code change to a verifiable decision loop.",
      body: "Each surface answers a different question while sharing the same Commit, Evidence, and Agent Trace identity chain.",
    },
    review: {
      eyebrow: "READ-ONLY BY DEFAULT",
      title: "Seven observable nodes—not seven separate models.",
      body: "Review is a persisted LangGraph Workflow. Every node has an input, output, tool trace, and evidence boundary; the default contract is read-only.",
      input: "Input",
      output: "Output",
      evidence: "Evidence boundary",
      readonly: "Review workflow · READ ONLY",
    },
    autofix: {
      eyebrow: "CONTROLLED AUTOFIX",
      title: "Turn free-form generation into an auditable repair transaction.",
      body: "Fix is separate from Review. Only an existing Finding can start it, and only an exact Patch Hash confirmation can authorize apply and validation in an isolated worktree.",
      finding: "Finding",
      confirmation: "User confirmation",
      worktree: "Isolated worktree",
      validation: "Real validation",
      resolution: "Deterministic result",
      boundaries: ["Original workspace stays unchanged", "No automatic commit", "No automatic push", "No automatic PR comment", "Failed tests cannot become RESOLVED"],
      demoTitle: "One fix, eleven observable states",
      demoHint: "Select a node to inspect its responsibility in the controlled transaction.",
    },
    intelligence: {
      eyebrow: "CODE INTELLIGENCE",
      title: "Static relationships, change impact, and Agent evidence—without blurring confidence.",
      body: "Repository Map shows only parser-confirmed edges. Review Map layers Diff, Findings, and Evidence on top. Unconfirmed relationships stay inferred or unknown.",
      confirmed: "confirmed static edge",
      inferred: "inferred relationship",
      unknown: "unknown / context gap",
      locate: "Select a Finding and return to the exact Diff range.",
    },
    gallery: {
      eyebrow: "PRODUCT GALLERY",
      title: "Running product views, each with its evidence scope.",
      body: "Screens come from local macOS runs, Playwright repository fixtures, or controlled benchmarks. A fixture is never presented as public-PR analysis.",
      open: "Open image",
      close: "Close image",
      previous: "Previous",
      next: "Next",
    },
    architecture: {
      eyebrow: "SYSTEM ARCHITECTURE",
      title: "Local-first does not mean opaque.",
      body: "Tauri owns local lifecycle and credentials. The authenticated FastAPI Sidecar runs indexing, workflows, and controlled tools. Evidence, Findings, and Trace remain inspectable in persistence.",
      flow: "Data and trust boundaries",
    },
    verification: {
      eyebrow: "TRUST THROUGH EXPLICIT BOUNDARIES",
      title: "Trust is not built by painting every cell green.",
      body: "TraceGate publishes what is verified, what is CI-only, and what still requires hands-on acceptance. Honest boundaries are part of the product.",
      verified: "Verified",
      verifiedCi: "Verified in CI",
      blocked: "External gate",
      notes: [
        "VERIFIED_WINDOWS_CI is not Windows GUI manual acceptance.",
        "The real Autofix E2E used real DeepSeek with a synthetic temporary Git repository.",
        "No public-PR automatic-fix success rate is claimed.",
        "Complete JavaScript, TypeScript, or Java semantic call graphs are not claimed.",
        "Validation constrains argv/cwd/env, but it is not an OS/container sandbox.",
      ],
    },
    security: {
      eyebrow: "GUARDRAILS AROUND THE AGENT",
      title: "The Agent works inside policy—not policy written as prompt prose.",
      body: "Credentials, paths, patches, commands, and workspaces are governed by application code. Model output is always untrusted input.",
    },
    cta: {
      eyebrow: "OPEN SOURCE",
      title: "Every patch should explain itself.",
      body: "Read the source, verification records, and safety model to see how TraceGate puts Evidence and Human Control on the default Coding Agent path.",
      primary: "Explore TraceGate on GitHub",
      built: "Built by Chloiris",
      links: ["Chinese README", "Architecture", "Autofix Safety", "Verification Records", "MIT License"],
    },
  },
} as const;
