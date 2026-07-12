import { access, mkdir, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = resolve(here, "..");
const repositoryRoot = resolve(siteRoot, "../..");
const outputRoot = resolve(siteRoot, "public/media/product");
const captureRoot = resolve(repositoryRoot, "build/site-product-captures");
const docsRoot = resolve(repositoryRoot, "docs/screenshots");

const assets = [
  { name: "dashboard", candidates: ["dashboard.png", "p0-dashboard-macos.png"], crop: { left: 0, top: 0, width: 1280, height: 900 } },
  { name: "native-shell", candidates: ["native-shell.png", "p0-desktop-macos.png"] },
  { name: "settings", candidates: ["settings-diagnostics.png", "p0-settings-macos.png"], crop: { left: 0, top: 0, width: 1280, height: 980 } },
  { name: "pr-inbox", candidates: ["pr-inbox.png", "p1-pr-diff-macos.png"], crop: { left: 0, top: 0, width: 1280, height: 720 } },
  { name: "pr-diff", candidates: ["pr-diff.png", "p1-pr-diff-macos.png"], crop: { left: 0, top: 140, width: 1280, height: 900 } },
  { name: "findings-evidence", candidates: ["findings-evidence.png", "p1-pr-diff-macos.png"], crop: { left: 0, top: 120, width: 1280, height: 900 } },
  { name: "repository-map", candidates: ["repository-map.png", "p1-review-map-macos.png"], crop: { left: 0, top: 160, width: 1280, height: 1050 } },
  { name: "review-map", candidates: ["review-map.png", "p1-review-map-macos.png"], crop: { left: 0, top: 160, width: 1280, height: 1050 } },
  { name: "agent-trace", candidates: ["agent-trace.png", "p1-registry-macos.png"], crop: { left: 0, top: 0, width: 1280, height: 980 } },
  { name: "eval-center", candidates: ["eval-center.png", "p1-eval-center-macos.png"], crop: { left: 0, top: 0, width: 1280, height: 1000 } },
  { name: "fix-plan", candidates: ["fix-plan.png", "autofix-playwright-fixture-confirmation-macos.png"], crop: { left: 0, top: 720, width: 1280, height: 850 } },
  { name: "patch-proposal", candidates: ["patch-proposal.png", "autofix-playwright-fixture-confirmation-macos.png"], crop: { left: 0, top: 1370, width: 1280, height: 900 } },
  { name: "patch-confirmation", candidates: ["patch-confirmation.png", "autofix-playwright-fixture-confirmation-macos.png"], crop: { left: 0, top: 0, width: 1280, height: 900 } },
  { name: "validation", candidates: ["validation.png", "autofix-playwright-fixture-confirmation-macos.png"], crop: { left: 0, top: 2080, width: 1280, height: 760 } },
  { name: "final-report", candidates: ["final-report.png", "autofix-playwright-fixture-result-macos.png"], crop: { left: 0, top: 2700, width: 1280, height: 800 } },
];

async function exists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function sourceFor(candidates) {
  const capture = resolve(captureRoot, candidates[0]);
  if (await exists(capture)) return capture;
  const fallback = resolve(docsRoot, candidates[1]);
  if (await exists(fallback)) return fallback;
  throw new Error(`Missing product screenshot source: ${candidates.join(" or ")}`);
}

await rm(outputRoot, { recursive: true, force: true });
await mkdir(outputRoot, { recursive: true });

for (const asset of assets) {
  const source = await sourceFor(asset.candidates);
  const image = sharp(source, { failOn: "warning" }).rotate();
  const metadata = await image.metadata();
  let prepared = image;

  if (asset.crop) {
    const sourceWidth = metadata.autoOrient?.width ?? metadata.width;
    const sourceHeight = metadata.autoOrient?.height ?? metadata.height;

    if (!sourceWidth || !sourceHeight) {
      throw new Error(`Unable to read dimensions for ${source}`);
    }

    const width = Math.min(asset.crop.width, sourceWidth);
    const height = Math.min(asset.crop.height, sourceHeight);
    const left = Math.min(asset.crop.left, sourceWidth - width);
    const top = Math.min(asset.crop.top, sourceHeight - height);

    prepared = image.extract({ left, top, width, height });
  }
  for (const width of [640, 960, 1200]) {
    await prepared
      .clone()
      .resize({ width, withoutEnlargement: true })
      .webp({ quality: 78, effort: 5, smartSubsample: true })
      .toFile(resolve(outputRoot, `${asset.name}-${width}.webp`));
    await prepared
      .clone()
      .resize({ width, withoutEnlargement: true })
      .avif({ quality: 54, effort: 5 })
      .toFile(resolve(outputRoot, `${asset.name}-${width}.avif`));
  }
}

const ogSvg = `
<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="glow" cx="70%" cy="30%" r="65%"><stop stop-color="#2ee6b2" stop-opacity=".26"/><stop offset="1" stop-color="#07100f" stop-opacity="0"/></radialGradient>
    <linearGradient id="line" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#67f6c4"/><stop offset="1" stop-color="#88b8ff"/></linearGradient>
  </defs>
  <rect width="1200" height="630" fill="#07100f"/>
  <rect width="1200" height="630" fill="url(#glow)"/>
  <g stroke="#16342f" opacity=".6"><path d="M0 90h1200M0 180h1200M0 270h1200M0 360h1200M0 450h1200M0 540h1200"/><path d="M90 0v630M180 0v630M270 0v630M360 0v630M450 0v630M540 0v630M630 0v630M720 0v630M810 0v630M900 0v630M990 0v630M1080 0v630"/></g>
  <g transform="translate(84 76)"><path d="M54 0 104 28v58L54 114 4 86V28L54 0Z" fill="url(#line)"/><path d="M28 31h52v16H62v48H46V47H28V31Z" fill="#07100f"/></g>
  <text x="220" y="130" fill="#eafdf8" font-family="Arial, sans-serif" font-size="44" font-weight="700">TraceGate Studio</text>
  <text x="84" y="280" fill="#f2fbf8" font-family="Arial, sans-serif" font-size="72" font-weight="750">Review with evidence.</text>
  <text x="84" y="368" fill="#67f6c4" font-family="Arial, sans-serif" font-size="72" font-weight="750">Fix with control.</text>
  <text x="88" y="455" fill="#9ab2ad" font-family="Arial, sans-serif" font-size="26">Evidence-grounded PR review · Code intelligence · Controlled Autofix</text>
  <g transform="translate(850 130)" fill="#0d1b19" stroke="#67f6c4" stroke-width="2"><rect x="0" y="0" width="220" height="64" rx="18"/><rect x="-90" y="124" width="220" height="64" rx="18"/><rect x="60" y="248" width="220" height="64" rx="18"/></g>
  <g fill="#dffaf2" font-family="Arial, sans-serif" font-size="18" font-weight="600"><text x="914" y="169">EVIDENCE</text><text x="813" y="293">FINDING</text><text x="939" y="417">RESOLVED</text></g>
  <path d="M955 194C950 232 875 240 852 254M875 318C906 350 951 350 962 378" fill="none" stroke="url(#line)" stroke-width="4" stroke-linecap="round"/>
</svg>`;
await sharp(Buffer.from(ogSvg)).png({ compressionLevel: 9 }).toFile(resolve(siteRoot, "public/og-tracegate.png"));

console.log(`Optimized ${assets.length} product views into AVIF/WebP variants.`);
