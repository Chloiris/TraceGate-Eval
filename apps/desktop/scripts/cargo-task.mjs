import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const task = process.argv[2];
const manifestPath = fileURLToPath(
  new URL("../src-tauri/Cargo.toml", import.meta.url),
);
const sourceCheckConfig = JSON.stringify({ bundle: { externalBin: [] } });

const taskArguments = {
  check: ["check", "--manifest-path", manifestPath],
  test: ["test", "--manifest-path", manifestPath, "--all-targets"],
  "fmt-check": [
    "fmt",
    "--manifest-path",
    manifestPath,
    "--all",
    "--",
    "--check",
  ],
  clippy: [
    "clippy",
    "--manifest-path",
    manifestPath,
    "--all-targets",
    "--all-features",
    "--",
    "-D",
    "warnings",
  ],
};

const cargoArguments = taskArguments[task];
if (!cargoArguments) {
  process.stderr.write(
    "usage: node scripts/cargo-task.mjs <check|test|fmt-check|clippy>\n",
  );
  process.exit(64);
}

const result = spawnSync("cargo", cargoArguments, {
  env: {
    ...process.env,
    // Source checks do not bundle. Production `tauri build` keeps the real
    // externalBin requirement and fails when the target Sidecar is absent.
    TAURI_CONFIG: sourceCheckConfig,
  },
  shell: false,
  stdio: "inherit",
});

if (result.error) {
  process.stderr.write(`${result.error.message}\n`);
  process.exit(1);
}
process.exit(result.status ?? 1);
