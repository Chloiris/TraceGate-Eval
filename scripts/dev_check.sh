#!/usr/bin/env bash
set -euo pipefail

echo "[TraceGate] compile check"
python -m compileall .

echo "[TraceGate] tests"
pytest -q

echo "[TraceGate] CLI help if available"
if python -m tracegate --help >/tmp/tracegate_cli_help.txt 2>&1 && [ -s /tmp/tracegate_cli_help.txt ]; then
  cat /tmp/tracegate_cli_help.txt
elif python -m tracegate.cli --help >/tmp/tracegate_cli_help.txt 2>&1 && [ -s /tmp/tracegate_cli_help.txt ]; then
  cat /tmp/tracegate_cli_help.txt
else
  echo "TraceGate CLI help not available yet; this may be implemented on Mac development phase."
fi

echo "[TraceGate] done"
