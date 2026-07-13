#!/usr/bin/env bash
set -euo pipefail

readonly SSH_HOST="tracegate-server"
readonly REMOTE_ROOT="/var/www/tracegate"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${repo_root}" || ! -f "${repo_root}/pnpm-workspace.yaml" || ! -d "${repo_root}/apps/site" ]]; then
  echo "Refusing to deploy: run this script from the TraceGate-Eval repository." >&2
  exit 1
fi

cd "${repo_root}"
readonly DIST_DIR="${repo_root}/apps/site/dist"
if [[ ! -f "${DIST_DIR}/index.html" ]]; then
  echo "Refusing to deploy: apps/site/dist/index.html is missing. Run pnpm site:build first." >&2
  exit 1
fi

file_count="$(find "${DIST_DIR}" -type f | wc -l | tr -d ' ')"
total_size="$(du -sh "${DIST_DIR}" | awk '{print $1}')"
echo "Deploying ${file_count} files (${total_size}) from apps/site/dist/"
echo "Target: ${SSH_HOST}:${REMOTE_ROOT}/"

ssh -o BatchMode=yes "${SSH_HOST}" 'whoami && hostname'
ssh -o BatchMode=yes "${SSH_HOST}" "test -d '${REMOTE_ROOT}' && test -w '${REMOTE_ROOT}' && ls -la '${REMOTE_ROOT}' | head"

rsync -az --delete --delay-updates \
  --exclude '.DS_Store' \
  "${DIST_DIR}/" \
  "${SSH_HOST}:${REMOTE_ROOT}/"

ssh -o BatchMode=yes "${SSH_HOST}" "test -s '${REMOTE_ROOT}/index.html' && find '${REMOTE_ROOT}' -type f | wc -l && stat -c '%n %s bytes' '${REMOTE_ROOT}/index.html'"

if ! http_status="$(curl --silent --show-error --location --output /dev/null --write-out '%{http_code}' --max-time 20 http://tracegate.chlogonia.xyz)"; then
  echo "HTTP status: unavailable"
  echo "Deployment uploaded, but the public HTTP endpoint is not serving a response." >&2
  exit 1
fi
echo "HTTP status: ${http_status}"
if [[ "${http_status}" != "200" ]]; then
  echo "Deployment uploaded, but HTTP verification did not return 200." >&2
  exit 1
fi

if https_status="$(curl --silent --show-error --location --output /dev/null --write-out '%{http_code}' --max-time 20 https://tracegate.chlogonia.xyz 2>/dev/null)"; then
  echo "HTTPS status: ${https_status}"
  if [[ "${https_status}" != "200" ]]; then
    echo "Deployment uploaded, but HTTPS verification did not return 200." >&2
    exit 1
  fi
else
  echo "HTTPS status: unavailable (configure TLS with the documented root-only steps)."
fi

echo "TraceGate site deployment verified."
