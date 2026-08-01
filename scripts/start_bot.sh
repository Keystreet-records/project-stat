#!/bin/bash
# Start Project Stat Telegram bot in background (on-demand /report).
# launchd cannot read ~/Desktop without Full Disk Access — use nohup instead.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
pkill -f "$ROOT/scripts/bot.py" 2>/dev/null || true
sleep 1
nohup "$ROOT/.venv/bin/python3" "$ROOT/scripts/bot.py" \
  >>"$LOG_DIR/bot.stdout.log" 2>>"$LOG_DIR/bot.stderr.log" &
echo "bot started pid=$!"
