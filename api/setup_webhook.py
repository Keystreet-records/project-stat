#!/usr/bin/env python3
"""One-shot: set Telegram webhook to this Vercel deployment (runs in cloud)."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler

import requests


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._run()

    def do_POST(self):
        self._run()

    def log_message(self, fmt: str, *args) -> None:
        return

    def _run(self) -> None:
        expected = os.environ.get("CRON_SECRET", "").strip()
        auth = self.headers.get("Authorization", "")
        if expected and auth != f"Bearer {expected}":
            self._json(401, {"ok": False, "error": "unauthorized"})
            return

        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
        base = (
            os.environ.get("REPORT_BASE_URL", "").strip()
            or (f"https://{os.environ['VERCEL_URL']}" if os.environ.get("VERCEL_URL") else "")
        )
        if not token or not base:
            self._json(500, {"ok": False, "error": "missing token or base url"})
            return

        url = f"{base.rstrip('/')}/api/telegram"
        requests.post(
            f"https://api.telegram.org/bot{token}/deleteWebhook",
            json={"drop_pending_updates": True},
            timeout=30,
        ).raise_for_status()
        payload = {
            "url": url,
            "allowed_updates": ["message"],
            "drop_pending_updates": True,
        }
        if secret:
            payload["secret_token"] = secret
        r = requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json=payload,
            timeout=30,
        )
        data = r.json()
        info = requests.get(
            f"https://api.telegram.org/bot{token}/getWebhookInfo",
            timeout=30,
        ).json()
        self._json(200 if data.get("ok") else 500, {"setWebhook": data, "info": info})

    def _json(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
