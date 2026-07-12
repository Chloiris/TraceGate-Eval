import { animate, useInView, useMotionValue, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";

import { projectFacts } from "../generated/projectFacts";
import { copy, useLanguage } from "../i18n";
import { GlowCard, ProductPicture, Reveal, SectionHeader, StatusDot } from "./Primitives";

function Count({ value }: { value: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduced = useReducedMotion();
  const motionValue = useMotionValue(reduced ? value : 0);

  useEffect(() => {
    if (!inView || reduced) return;
    const controls = animate(motionValue, value, { duration: 1.15, ease: [0.22, 1, 0.36, 1] });
    const unsubscribe = motionValue.on("change", (next) => {
      if (ref.current) ref.current.textContent = String(Math.round(next));
    });
    return () => {
      controls.stop();
      unsubscribe();
    };
  }, [inView, motionValue, reduced, value]);

  return <span ref={ref}>{reduced ? value : 0}</span>;
}

export function ProofStrip() {
  const { language } = useLanguage();
  const text = copy[language].proof;
  const facts = [
    [projectFacts.review.nodeCount, text.review],
    [projectFacts.autofix.nodeCount, text.autofix],
    [projectFacts.tools, text.tools],
    [projectFacts.tests.python, text.python],
    [projectFacts.tests.typescript, text.typescript],
    [projectFacts.tests.rust, text.rust],
    [projectFacts.tests.playwright, text.playwright],
  ] as const;

  return (
    <section className="proof-strip" aria-labelledby="proof-heading">
      <div className="shell">
        <div className="proof-strip__header">
          <p className="eyebrow" id="proof-heading">{text.label}</p>
          <span className="proof-strip__version">v{projectFacts.version}</span>
        </div>
        <div className="proof-strip__grid">
          {facts.map(([value, label]) => (
            <div className="proof-stat" key={label}>
              <strong><Count value={value} /></strong>
              <span>{label}</span>
            </div>
          ))}
          <div className="proof-stat proof-stat--package">
            <span><StatusDot /> Windows x86-64</span>
            <strong>CI PACKAGE</strong>
          </div>
          <div className="proof-stat proof-stat--package">
            <span><StatusDot /> macOS arm64</span>
            <strong>NATIVE BUILD</strong>
          </div>
        </div>
        <p className="proof-strip__note">{text.note}</p>
      </div>
    </section>
  );
}

export function ProblemStory() {
  const { language } = useLanguage();
  const text = copy[language].problem;
  const [active, setActive] = useState(0);

  return (
    <section className="story section" aria-labelledby="story-title">
      <div className="shell story__grid">
        <div className="story__copy">
          <Reveal>
            <p className="eyebrow">{text.eyebrow}</p>
            <h2 id="story-title">{text.title}</h2>
            <p className="story__lead">{text.lead}</p>
          </Reveal>
          <Reveal className="risk-signal" delay={0.08}>
            <span className="risk-signal__line" aria-hidden="true" />
            <div>
              <small>AGENT RISK SURFACE</small>
              <div className="risk-cloud">
                {text.risks.map((risk, index) => <button type="button" key={risk} onClick={() => setActive(index)} aria-pressed={active === index}>{risk}</button>)}
              </div>
            </div>
          </Reveal>
          <Reveal className="story__statement" delay={0.14}><p>{text.statement}</p></Reveal>
        </div>
        <div className="trust-chain" aria-label="TraceGate trust chain">
          {text.chain.map(([label, description], index) => (
            <Reveal className={`trust-step ${active === index ? "trust-step--active" : ""}`} delay={index * 0.05} key={label}>
              <button type="button" onClick={() => setActive(index)}>
                <span className="trust-step__index">0{index + 1}</span>
                <span><small>{label}</small><strong>{description}</strong></span>
                <span className="trust-step__pulse" aria-hidden="true" />
              </button>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

const capabilityCopy = {
  zh: [
    ["证据驱动 PR Review", "结论必须绑定 Head、文件、行号与 Evidence；模型无法独自宣布 Finding 成立。"],
    ["Controlled Autofix", "从 Finding 到 Patch Hash、隔离应用、验证与 re-review，每一步都可审计。"],
    ["Repository Map", "以 Commit 绑定索引展示 confirmed 文件、符号与测试关系。"],
    ["Review Map", "将 Diff、静态影响、Finding 和 Agent Evidence 放进同一上下文。"],
    ["Agent Trace", "节点、Tool Call、token、延迟和错误状态都进入持久化轨迹。"],
    ["Eval Center", "把 19 个公共 PR 案例与 160 条 ClaimBench 受控结果变成可检查界面。"],
  ],
  en: [
    ["Evidence-grounded PR Review", "Every conclusion binds Head, file, range, and Evidence. The model cannot establish a Finding by itself."],
    ["Controlled Autofix", "Finding, Patch Hash, isolated apply, validation, and re-review remain one auditable transaction."],
    ["Repository Map", "Commit-bound indexing shows confirmed file, symbol, and test relationships."],
    ["Review Map", "Diff, static impact, Findings, and Agent Evidence share one context view."],
    ["Agent Trace", "Nodes, Tool Calls, tokens, latency, and failures persist as an inspectable trace."],
    ["Eval Center", "Nineteen public-PR cases and 160 controlled ClaimBench rows become an explorable product surface."],
  ],
} as const;

const capabilityVisuals = ["pr-diff", "patch-confirmation", "repository-map", "review-map", "agent-trace", "eval-center"] as const;
const capabilityScopes = ["PLAYWRIGHT FIXTURE", "PLAYWRIGHT FIXTURE", "PARSER-CONFIRMED EDGES", "PLAYWRIGHT FIXTURE", "PERSISTED TRACE", "CONTROLLED BENCHMARK"] as const;

export function Capabilities() {
  const { language } = useLanguage();
  const text = copy[language].capabilities;

  return (
    <section id="product" className="capabilities section" aria-labelledby="capabilities-title">
      <div className="shell">
        <SectionHeader eyebrow={text.eyebrow} title={text.title} body={text.body} align="center" />
        <div className="capability-layout">
          {capabilityCopy[language].map(([title, body], index) => (
            <Reveal className={`capability capability--${index + 1}`} delay={(index % 3) * 0.06} key={title}>
              <GlowCard className="capability__inner">
                <div className="capability__text">
                  <span className="capability__number">0{index + 1}</span>
                  <div><small>{capabilityScopes[index]}</small><h3>{title}</h3><p>{body}</p></div>
                </div>
                <div className="capability__visual product-frame">
                  <ProductPicture id={capabilityVisuals[index] ?? "dashboard"} alt={`${title} — ${capabilityScopes[index] ?? "VERIFIED SCOPE"}`} sizes="(max-width: 760px) 92vw, 580px" />
                  <span className="product-frame__scope">{capabilityScopes[index] ?? "VERIFIED SCOPE"}</span>
                </div>
              </GlowCard>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
