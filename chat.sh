#!/usr/bin/env bash
# Start an interactive Codex session with the arm tools attached.
# Arguments pass through to codex, e.g.:  ./chat.sh "Put the tip at x=0.3, z=0.7"
#
# PYTHON overrides the interpreter:  PYTHON=./.venv/bin/python ./chat.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

cd "$HERE"
exec codex \
  -c "mcp_servers.arm.command=\"$PYTHON\"" \
  -c "mcp_servers.arm.args=[\"$HERE/arm_mcp.py\"]" \
  -c 'mcp_servers.arm.startup_timeout_sec=60' \
  -c 'approval_policy="never"' \
  -c 'sandbox_mode="danger-full-access"' \
  "$@"
