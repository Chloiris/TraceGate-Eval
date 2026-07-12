import { projectFacts } from "../generated/projectFacts";
import { copy, useLanguage } from "../i18n";
import { ArrowIcon, GithubIcon, GlowCard, Reveal, SectionHeader, StatusDot } from "./Primitives";

const architectureLayers = [
  ["EXPERIENCE", "React · TypeScript · Vite", "PR workspace · Maps · Trace · Eval · Autofix"],
  ["DESKTOP HOST", "Tauri 2 · Rust", "Window lifecycle · Keychain · Credential Manager · Sidecar"],
  ["AUTHENTICATED SIDECAR", "FastAPI · Python · Pydantic", "REST · SSE · repository boundary · policy"],
  ["AGENT RUNTIME", "LangGraph Review / Autofix", "7-node read-only review · 11-node controlled fix"],
  ["CONTROL PLANE", "Tool Registry · GitHub · Code Index", "19 schema-validated tools · confirmed static edges"],
  ["PERSISTENCE", "SQLite · SQLAlchemy · optional MySQL", "Evidence · Findings · Agent Trace · Fix transaction"],
] as const;

const verificationRows = {
  zh: [
    ["macOS full-stack runtime", "VERIFIED", "真实 API、Sidecar、Tauri 构建与原生启动"],
    ["Real DeepSeek Review E2E", "VERIFIED", "公共 PR Review；不等于 Autofix"],
    ["Real DeepSeek Autofix E2E", "VERIFIED", "真实模型 + 合成临时 Git 仓库"],
    ["Windows x86-64 packaging", "VERIFIED IN CI", "未签名 Setup.exe / MSI / portable"],
    ["Windows GUI manual acceptance", "BLOCKED", "仍需真实 Windows 图形界面验收"],
    ["Public-PR Autofix E2E", "BLOCKED", "未拿随机 PR 冒充修复成功"],
  ],
  en: [
    ["macOS full-stack runtime", "VERIFIED", "Real API, Sidecar, Tauri build, and native launch"],
    ["Real DeepSeek Review E2E", "VERIFIED", "Public-PR Review; not Autofix evidence"],
    ["Real DeepSeek Autofix E2E", "VERIFIED", "Real model + synthetic temporary Git repository"],
    ["Windows x86-64 packaging", "VERIFIED IN CI", "Unsigned Setup.exe / MSI / portable"],
    ["Windows GUI manual acceptance", "BLOCKED", "Still requires a real Windows graphical session"],
    ["Public-PR Autofix E2E", "BLOCKED", "No random PR is presented as a successful fix"],
  ],
} as const;

const securityRings = [
  ["IDENTITY", "Per-launch token", "Exact Head SHA", "Patch Hash"],
  ["BOUNDARY", "RepositoryBoundary", "Sensitive files", "Isolated worktree"],
  ["EXECUTION", "Command allowlist", "Filtered env", "Timeout + output cap"],
  ["RECOVERY", "No auto push", "Rollback", "Cleanup diagnostics"],
] as const;

export function Architecture() {
  const { language } = useLanguage();
  const text = copy[language].architecture;

  return (
    <section id="architecture" className="architecture section" aria-labelledby="architecture-title">
      <div className="shell">
        <SectionHeader eyebrow={text.eyebrow} title={text.title} body={text.body} />
        <div className="architecture__frame">
          <div className="architecture__header"><span><StatusDot /> {text.flow}</span><span className="mono">LOCAL TRUST BOUNDARY</span></div>
          <div className="architecture__layers">
            {architectureLayers.map(([label, tech, detail], index) => (
              <Reveal className="architecture-layer" delay={index * 0.045} key={label}>
                <span className="architecture-layer__index">0{index + 1}</span>
                <small>{label}</small>
                <strong>{tech}</strong>
                <p>{detail}</p>
                {index < architectureLayers.length - 1 && <i aria-hidden="true" />}
              </Reveal>
            ))}
          </div>
          <div className="architecture__stack" aria-label="Technology stack">
            {["React", "TypeScript", "Vite", "FastAPI", "Python", "LangGraph", "Pydantic", "SQLAlchemy", "SQLite", "MySQL", "Tauri 2", "Rust", "GitHub Actions", "PyInstaller", "Playwright"].map((tech) => <span key={tech}>{tech}</span>)}
          </div>
        </div>
      </div>
    </section>
  );
}

export function Verification() {
  const { language } = useLanguage();
  const text = copy[language].verification;
  return (
    <section id="verification" className="verification section" aria-labelledby="verification-title">
      <div className="shell">
        <SectionHeader eyebrow={text.eyebrow} title={text.title} body={text.body} />
        <div className="verification__layout">
          <div className="verification-table" role="table" aria-label="TraceGate verification matrix">
            {verificationRows[language].map(([capability, status, scope]) => {
              const blocked = status === "BLOCKED";
              const ci = status === "VERIFIED IN CI";
              return (
                <div className="verification-row" role="row" key={capability}>
                  <div role="cell"><strong>{capability}</strong><span>{scope}</span></div>
                  <div role="cell" className={`verification-status ${blocked ? "verification-status--blocked" : ci ? "verification-status--ci" : ""}`}>
                    <StatusDot tone={blocked ? "warning" : "success"} />{status}
                  </div>
                </div>
              );
            })}
          </div>
          <GlowCard className="verification-notes">
            <span className="verification-notes__version">TRACEGATE {projectFacts.version}</span>
            <h3>Explicit boundaries.<br />Inspectable proof.</h3>
            <ul>{text.notes.map((note) => <li key={note}>{note}</li>)}</ul>
            <a href="https://github.com/Chloiris/TraceGate-Eval/tree/main/docs/verification" target="_blank" rel="noreferrer">Verification records <ArrowIcon /></a>
          </GlowCard>
        </div>
      </div>
    </section>
  );
}

export function Security() {
  const { language } = useLanguage();
  const text = copy[language].security;
  return (
    <section className="security section" aria-labelledby="security-title">
      <div className="shell security__grid">
        <SectionHeader eyebrow={text.eyebrow} title={text.title} body={text.body} />
        <div className="security-orbit" aria-label="Security guardrails around the Agent">
          <div className="security-orbit__core"><span>CONTROLLED</span><strong>AGENT</strong><small>model output = untrusted</small></div>
          {securityRings.map(([label, ...items], index) => (
            <Reveal className={`security-ring security-ring--${index + 1}`} delay={index * 0.06} key={label}>
              <small>{label}</small>
              {items.map((item) => <span key={item}>{item}</span>)}
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

const footerLinks = [
  "https://github.com/Chloiris/TraceGate-Eval/blob/main/docs/README_CN.md",
  "https://github.com/Chloiris/TraceGate-Eval/tree/main/docs/architecture",
  "https://github.com/Chloiris/TraceGate-Eval/blob/main/docs/autofix-safety.md",
  "https://github.com/Chloiris/TraceGate-Eval/tree/main/docs/verification",
  "https://github.com/Chloiris/TraceGate-Eval/blob/main/LICENSE",
] as const;

export function FooterCta() {
  const { language } = useLanguage();
  const text = copy[language].cta;
  return (
    <footer className="footer-cta">
      <div className="footer-cta__glow" aria-hidden="true" />
      <div className="shell">
        <Reveal className="footer-cta__main">
          <p className="eyebrow">{text.eyebrow}</p>
          <h2>{text.title}</h2>
          <p>{text.body}</p>
          <a className="button button--primary button--large" href="https://github.com/Chloiris/TraceGate-Eval" target="_blank" rel="noreferrer"><GithubIcon /><span>{text.primary}</span><ArrowIcon /></a>
        </Reveal>
        <div className="footer-cta__links">
          <a className="footer-cta__author" href="https://github.com/Chloiris" target="_blank" rel="noreferrer">{text.built}<span>@Chloiris</span></a>
          <nav aria-label="Project resources">
            {text.links.map((label, index) => <a key={label} href={footerLinks[index]} target="_blank" rel="noreferrer">{label}</a>)}
          </nav>
        </div>
        <div className="footer-cta__bottom"><span>TraceGate Studio · {projectFacts.version}</span><span>Evidence-grounded PR review and controlled Coding Agent Autofix.</span><span>MIT License</span></div>
      </div>
    </footer>
  );
}
