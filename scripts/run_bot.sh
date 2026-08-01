#!/bin/bash
# Keepalive wrapper — Project Stat Telegram bot (on-demand reports).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  exec "$ROOT/.venv/bin/python3" "$ROOT/scripts/bot.py"
else
  exec python3 "$ROOT/scripts/bot.py"
fi
