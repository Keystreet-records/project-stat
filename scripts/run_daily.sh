#!/bin/bash
# Wrapper for launchd / cron — Project Stat daily report.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Prefer project venv; fall back to system python3
if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  exec "$ROOT/.venv/bin/python3" "$ROOT/scripts/daily_report.py"
else
  exec python3 "$ROOT/scripts/daily_report.py"
fi
