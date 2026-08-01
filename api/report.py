#!/usr/bin/env python3
"""Vercel serverless: run Project Stat report and send to Telegram."""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from daily_report import generate_report  # noqa: E402
from telegram_notify import report_keyboard, send_message  # noqa: E402


def _authorized(handler: BaseHTTPRequestHandler) -> bool:
    expected = os.environ.get("CRON_SECRET", "").strip()
    if not expected:
        return True
    auth = handler.headers.get("Authorization", "")
    if auth == f"Bearer {expected}":
        return True
    # Vercel Cron sends this header on Pro; also allow query for manual tests
    if handler.headers.get("x-vercel-cron") == "1":
        return True
    q = urlparse(handler.path).query
    return f"secret={expected}" in q


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._run()

    def do_POST(self):
        self._run()

    def log_message(self, fmt: str, *args) -> None:  # quieter logs
        return

    def _run(self) -> None:
        if not _authorized(self):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"ok":false,"error":"unauthorized"}')
            return
        try:
            text, sites, all_ok = generate_report(save_json=False)
            send_message(text, reply_markup=report_keyboard())
            body = {
                "ok": True,
                "all_ok": all_ok,
                "sites": [
                    {
                        "id": s.get("id"),
                        "ok": s.get("ok"),
                        "visits": s.get("visits"),
                    }
                    for s in sites
                ],
            }
            raw = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except Exception as exc:
            raw = json.dumps({"ok": False, "error": str(exc)}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
