#!/usr/bin/env python3
"""Daily Project Stat report → Telegram (+ local JSON)."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from concurrent.futures import ThreadPoolExecutor

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analytics import fetch_visits  # noqa: E402
from health import check_site  # noqa: E402
from telegram_notify import send_message  # noqa: E402


def load_config() -> dict:
    path = ROOT / "config" / "sites.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _status_label(site: dict) -> tuple[str, str]:
    if not site["ok"]:
        return "❌", "недоступен"
    if site.get("slow"):
        return "⚠️", "медленно"
    return "✅", "ок"


def _check_label(check: dict) -> str:
    if check.get("label"):
        return str(check["label"])
    url = check.get("url") or ""
    if url.startswith("http"):
        parsed = urlparse(url)
        host = parsed.netloc
        path = parsed.path or "/"
        return host if path in ("", "/") else f"{host}{path}"
    return url or "/"


def _visits_line(visits: dict) -> str:
    if not visits.get("configured"):
        return "посещения не настроены"
    if visits.get("visitors_24h") is None:
        note = visits.get("note") or "ожидание данных"
        return f"посещения: {note}"
    return f"посещения: {visits['visitors_24h']} чел. / {visits['pageviews_24h']} просм."


def format_report(sites_out: list[dict], tz_name: str) -> str:
    now = datetime.now(ZoneInfo(tz_name))
    all_ok = all(s["ok"] for s in sites_out)
    summary = "всё в порядке" if all_ok else "нужно внимание"

    lines = [
        "📊 <b>Project Stat</b>",
        f"<i>{now.strftime('%d.%m.%Y')} · {now.strftime('%H:%M')} МСК</i>",
        f"Итог: <b>{summary}</b>",
    ]

    for s in sites_out:
        icon, status = _status_label(s)
        lines.append("")
        lines.append(f"{icon} <b>{s['name']}</b> — {status}, {s['max_elapsed_ms']} мс")
        for c in s["checks"]:
            mark = "✓" if c["ok"] else "✗"
            st = c["status"] if c["status"] is not None else "—"
            lines.append(f"    {mark} {_check_label(c)} · {st}")
        lines.append(f"    📈 {_visits_line(s.get('visits') or {})}")

    return "\n".join(lines)


def generate_report(*, save_json: bool = True) -> tuple[str, list[dict], bool]:
    """Build report text. Returns (html_text, sites_out, all_ok)."""
    load_dotenv(ROOT / ".env")
    cfg = load_config()
    defaults = cfg.get("defaults") or {}
    tz = defaults.get("timezone", "Europe/Moscow")

    sites = list(cfg.get("sites") or [])

    def _one(site: dict) -> dict:
        result = check_site(site, defaults)
        result["visits"] = fetch_visits(site)
        return result

    if len(sites) <= 1:
        sites_out = [_one(s) for s in sites]
    else:
        with ThreadPoolExecutor(max_workers=min(4, len(sites))) as pool:
            sites_out = list(pool.map(_one, sites))

    text = format_report(sites_out, tz)
    all_ok = all(s["ok"] for s in sites_out)

    if save_json:
        reports_dir = ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        stamp = datetime.now(ZoneInfo(tz)).strftime("%Y%m%d_%H%M")
        out_json = reports_dir / f"report_{stamp}.json"
        out_json.write_text(
            json.dumps({"generated_at": stamp, "sites": sites_out}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return text, sites_out, all_ok


def _console_text(html: str) -> str:
    text = re.sub(r'<a href="[^"]+">([^<]+)</a>', r"\1", html)
    for tag in ("b", "i", "code"):
        text = text.replace(f"<{tag}>", "").replace(f"</{tag}>", "")
    return text


def main() -> int:
    text, sites_out, all_ok = generate_report(save_json=True)
    print(_console_text(text))

    try:
        send_message(text)
        print("telegram: sent")
    except Exception as exc:
        print(f"telegram: skipped/failed — {exc}", file=sys.stderr)
        return 2 if not all_ok else 1

    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
