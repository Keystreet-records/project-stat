#!/usr/bin/env python3
"""HTTP health checks for configured sites."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests


def check_url(
    url: str,
    expect_status: list[int] | None = None,
    timeout_sec: float = 15,
    *,
    label: str | None = None,
) -> dict[str, Any]:
    expect = expect_status or [200]

    started = time.perf_counter()
    try:
        resp = requests.get(url, timeout=timeout_sec, allow_redirects=True)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        ok = resp.status_code in expect
        return {
            "url": url,
            "label": label,
            "ok": ok,
            "status": resp.status_code,
            "elapsed_ms": elapsed_ms,
            "final_url": str(resp.url),
            "error": None if ok else f"unexpected status {resp.status_code}",
        }
    except requests.RequestException as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "url": url,
            "label": label,
            "ok": False,
            "status": None,
            "elapsed_ms": elapsed_ms,
            "final_url": None,
            "error": str(exc),
        }


def _resolve_check_url(site_url: str, item: dict[str, Any]) -> tuple[str, str]:
    """Return (absolute_url, short_label) for a check config item."""
    absolute = (item.get("url") or "").strip()
    if absolute.startswith("http://") or absolute.startswith("https://"):
        parsed = urlparse(absolute)
        host = parsed.netloc or absolute
        path = parsed.path or "/"
        label = host if path in ("", "/") else f"{host}{path}"
        return absolute, label

    path = item.get("path", "/")
    if path == "/":
        url = site_url.rstrip("/") + "/"
        label = urlparse(site_url).netloc or path
    else:
        url = urljoin(site_url.rstrip("/") + "/", path.lstrip("/"))
        label = path
    return url, label


def check_site(site: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    timeout = float(defaults.get("timeout_sec", 15))
    slow_ms = int(defaults.get("slow_ms", 3000))
    checks_cfg = site.get("checks") or [{"path": "/", "expect_status": [200]}]
    results = []
    for item in checks_cfg:
        url, label = _resolve_check_url(site["url"], item)
        results.append(
            check_url(
                url,
                expect_status=item.get("expect_status"),
                timeout_sec=timeout,
                label=label,
            )
        )

    ok = all(r["ok"] for r in results)
    max_ms = max((r["elapsed_ms"] for r in results), default=0)
    return {
        "id": site["id"],
        "name": site["name"],
        "url": site["url"],
        "ok": ok,
        "slow": max_ms >= slow_ms,
        "max_elapsed_ms": max_ms,
        "checks": results,
    }
