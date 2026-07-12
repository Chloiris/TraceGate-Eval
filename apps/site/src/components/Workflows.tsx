import { AnimatePresence, motion, useInView, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";

import { projectFacts } from "../generated/projectFacts";
import { copy, useLanguage } from "../i18n";
import { ProductPicture, Reveal, SectionHeader, StatusDot } from "./Primitives";

const reviewDetails = {
  zh: [
    ["PR 身份、用户目标、策略", "有界审查计划", "当前 Base / Head 与只读策略"],
    ["计划与 Commit 身份", "受控仓库上下文", "RepositoryBoundary 与 Tool Registry"],
    ["检索片段与状态声明", "active / stale / unknown / conflicting", "来源、时间和 Commit 绑定"],
    ["Diff、符号和上下文", "候选 Finding", "文件、行范围与静态关系置信度"],
    ["候选 Finding 与 Evidence", "风险分级与策略判断", "不确定性不能被提示词覆盖"],
    ["Finding、路径、范围、证据", "验证或拒绝", "应用层重新检查身份与来源"],
    ["已验证 Finding 与 Trace", "结构化审查报告", "不支持的结论不会进入最终报告"],
  ],
  en: [
    ["PR identity, user goal, policy", "Bounded review plan", "Current Base / Head and read-only policy"],
    ["Plan and commit identity", "Controlled repository context", "RepositoryBoundary and Tool Registry"],
    ["Retrieved context and claims", "active / stale / unknown / conflicting", "Source, time, and commit binding"],
    ["Diff, symbols, context", "Candidate Findings", "File, range, and static-confidence provenance"],
    ["Candidate Findings and Evidence", "Risk and policy judgement", "Prompt text cannot erase uncertainty"],
    ["Finding, path, range, Evidence", "Verify or reject", "Application code rechecks identity and source"],
    ["Verified Findings and Trace", "Structured review report", "Unsupported claims never reach the final report"],
  ],
} as const;

export function ReviewWorkflow() {
  const { language } = useLanguage();
  const text = copy[language].review;
  const [selected, setSelected] = useState(0);
  const detail = reviewDetails[language][selected];

  return (
    <section className="review-workflow section" aria-labelledby="review-title">
      <div className="shell">
        <SectionHeader eyebrow={text.eyebrow} title={text.title} body={text.body} />
        <div className="review-workflow__panel">
          <div className="review-workflow__topline">
            <span><StatusDot /> {text.readonly}</span>
            <span className="mono">tracegate-langgraph-v1</span>
          </div>
          <div className="review-nodes" role="tablist" aria-label="Review workflow nodes">
            {projectFacts.review.nodes.map((node, index) => (
              <button key={node} type="button" role="tab" aria-selected={selected === index} onClick={() => setSelected(index)}>
                <span>0{index + 1}</span>
                <strong>{node}</strong>
              </button>
            ))}
          </div>
          <AnimatePresence mode="wait">
            <motion.div
              className="review-detail"
              key={selected}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.25 }}
              role="tabpanel"
            >
              {[text.input, text.output, text.evidence].map((label, index) => (
                <div key={label}><small>{label}</small><p>{detail?.[index]}</p></div>
              ))}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}

const autofixDisplay = [
  "Finding",
  "Eligibility",
  "Fix Plan",
  "Patch Proposal",
  "Patch Hash",
  "User Confirmation",
  "Isolated Worktree",
  "Validation",
  "Reindex",
  "Re-review",
  "Resolution",
] as const;

const autofixDescriptions = {
  zh: [
    "加载已持久化 Finding 与其 Evidence 身份。",
    "重新检查 Head、索引、路径、范围和敏感目标。",
    "模型生成结构化目标、步骤、约束与验证策略。",
    "生成完整 Unified Diff；它仍是不可信输入。",
    "应用层解析 Diff、检查限额并计算规范化 SHA-256。",
    "用户确认精确的 Finding、Head 与 Patch Hash。",
    "只在 Fix 管理的 detached Git Worktree 中应用。",
    "运行 Manifest / Preset 解析出的受控 argv 命令。",
    "对真实修改后 Worktree 生成瞬时索引身份。",
    "Verifier 重新评估原 Finding 与新风险。",
    "确定性策略输出 RESOLVED 或明确的非成功状态。",
  ],
  en: [
    "Load the persisted Finding and its Evidence identity.",
    "Recheck Head, index, path, range, and sensitive targets.",
    "Generate a structured objective, steps, constraints, and validation strategy.",
    "Generate the complete unified diff; it remains untrusted input.",
    "Parse the diff, enforce limits, and compute normalized SHA-256 in application code.",
    "The user confirms the exact Finding, Head, and Patch Hash.",
    "Apply only inside a Fix-managed detached Git worktree.",
    "Run controlled argv commands resolved from manifests and presets.",
    "Create a transient index identity for the actual modified worktree.",
    "The Verifier reassesses the original Finding and any new risk.",
    "Deterministic policy emits RESOLVED or an explicit non-success state.",
  ],
} as const;

export function AutofixWorkflow() {
  const { language } = useLanguage();
  const text = copy[language].autofix;
  const [selected, setSelected] = useState(0);
  const sectionRef = useRef<HTMLElement>(null);
  const inView = useInView(sectionRef, { amount: 0.3 });
  const reduced = useReducedMotion();

  useEffect(() => {
    if (reduced || !inView || document.hidden) return;
    const timer = window.setInterval(() => setSelected((index) => (index + 1) % projectFacts.autofix.nodes.length), 2200);
    return () => window.clearInterval(timer);
  }, [inView, reduced]);

  return (
    <section id="autofix" ref={sectionRef} className="autofix section" aria-labelledby="autofix-title">
      <div className="autofix__beam" aria-hidden="true" />
      <div className="shell">
        <SectionHeader eyebrow={text.eyebrow} title={text.title} body={text.body} />
        <div className="autofix__transaction">
          <div className="autofix__summary">
            {[text.finding, text.confirmation, text.worktree, text.validation, text.resolution].map((label, index) => (
              <span key={label}><small>0{index + 1}</small>{label}</span>
            ))}
          </div>
          <div className="autofix__stage">
            <div className="autofix__stage-header">
              <div><small>{text.demoTitle}</small><p>{text.demoHint}</p></div>
              <span className="autofix__state"><StatusDot tone={selected === 5 ? "warning" : "success"} /> {autofixDisplay[selected]}</span>
            </div>
            <div className="autofix-nodes" role="tablist" aria-label="Autofix workflow nodes">
              {projectFacts.autofix.nodes.map((node, index) => (
                <button key={node} type="button" role="tab" aria-selected={selected === index} onClick={() => setSelected(index)}>
                  <span>0{index + 1}</span>
                  <strong>{node}</strong>
                  <i aria-hidden="true" />
                </button>
              ))}
            </div>
            <AnimatePresence mode="wait">
              <motion.div className="autofix-detail" key={selected} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}>
                <div className="autofix-detail__identity"><span>NODE {String(selected + 1).padStart(2, "0")}</span><strong>{autofixDisplay[selected]}</strong></div>
                <p>{autofixDescriptions[language][selected]}</p>
                <div className="autofix-detail__trace">
                  <span className="mono">HEAD 74e4577</span>
                  <span className="mono">PATCH sha256:e009…</span>
                  <span className="mono">STATE persisted</span>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
          <div className="autofix__boundaries">
            {text.boundaries.map((boundary) => <span key={boundary}><StatusDot /> {boundary}</span>)}
          </div>
        </div>
        <Reveal className="autofix__visual" delay={0.08}>
          <div className="product-window product-window--autofix">
            <div className="product-window__bar"><span /><span /><span /><small>Fix / 自动修复 · exact Hash confirmation</small></div>
            <ProductPicture id="patch-confirmation" alt="TraceGate Studio hash-bound patch confirmation in a clearly labelled Playwright fixture" sizes="(max-width: 760px) 95vw, 1050px" />
            <div className="fixture-ribbon">PLAYWRIGHT UI FIXTURE · NOT PUBLIC-PR EVIDENCE</div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

export function CodeIntelligence() {
  const { language } = useLanguage();
  const text = copy[language].intelligence;

  return (
    <section id="intelligence" className="intelligence section" aria-labelledby="intelligence-title">
      <div className="shell">
        <SectionHeader eyebrow={text.eyebrow} title={text.title} body={text.body} />
        <div className="intelligence__grid">
          <Reveal className="map-demo">
            <div className="map-demo__toolbar"><span><StatusDot /> COMMIT-BOUND INDEX</span><span className="mono">74e4577</span></div>
            <div className="map-demo__canvas" aria-label="Static relationship confidence example">
              <svg viewBox="0 0 720 470" aria-hidden="true">
                <path className="map-edge map-edge--confirmed" d="M165 110 C250 100 260 185 340 200" />
                <path className="map-edge map-edge--confirmed" d="M375 225 C455 260 465 355 555 345" />
                <path className="map-edge map-edge--inferred" d="M165 110 C290 45 480 70 555 345" />
                <path className="map-edge map-edge--unknown" d="M165 355 C260 320 270 250 340 200" />
              </svg>
              <div className="map-node map-node--file" style={{ left: "7%", top: "13%" }}><small>FILE</small><strong>service.py</strong><span>modified</span></div>
              <div className="map-node map-node--symbol" style={{ left: "40%", top: "35%" }}><small>SYMBOL</small><strong>calculate_total</strong><span>confirmed</span></div>
              <div className="map-node map-node--test" style={{ left: "69%", top: "65%" }}><small>TEST</small><strong>test_total</strong><span>supported-by-code</span></div>
              <div className="map-node map-node--evidence" style={{ left: "6%", top: "68%" }}><small>EVIDENCE</small><strong>Return semantics</strong><span>service.py:2</span></div>
            </div>
            <div className="map-demo__legend">
              <span><i className="legend-line legend-line--confirmed" />{text.confirmed}</span>
              <span><i className="legend-line legend-line--inferred" />{text.inferred}</span>
              <span><i className="legend-line legend-line--unknown" />{text.unknown}</span>
            </div>
          </Reveal>
          <Reveal className="intelligence__screenshot" delay={0.08}>
            <div className="product-window">
              <div className="product-window__bar"><span /><span /><span /><small>Review Map · fixture scope</small></div>
              <ProductPicture id="review-map" alt="TraceGate Studio Review Map running on a Playwright repository fixture" sizes="(max-width: 760px) 95vw, 650px" />
            </div>
            <p><StatusDot /> {text.locate}</p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
