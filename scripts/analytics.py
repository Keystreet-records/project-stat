#!/usr/bin/env python3
"""Visit stats via Vercel Web Analytics API (optional GA4 later)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

VERCEL_COUNT_URL = "https://api.vercel.com/v1/query/web-analytics/visits/count"


def fetch_visits(site: dict[str, Any]) -> dict[str, Any]:
    """
    Fetch last-24h visitors/pageviews for a site.

    Without credentials we return a clear 'not configured' status so the
    daily report never invents numbers.
    """
    token = os.environ.get("VERCEL_TOKEN", "").strip()
    project = (site.get("vercel_project") or "").strip()

    if not token:
        return {
            "configured": False,
            "source": None,
            "visitors_24h": None,
            "pageviews_24h": None,
            "note": "analytics not configured",
        }

    if not project:
        return {
            "configured": True,
            "source": "vercel",
            "visitors_24h": None,
            "pageviews_24h": None,
            "note": "нет vercel_project в sites.yaml",
        }

    return _fetch_vercel_24h(token, project)


def _fetch_vercel_24h(token: str, project_id: str) -> dict[str, Any]:
    team_id = os.environ.get("VERCEL_TEAM_ID", "").strip()
    now = datetime.now(timezone.utc)
    # Vercel day-buckets `until`, so a mid-day timestamp becomes midnight and
    # drops today's traffic. Use calendar dates that include "today".
    since = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    until = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    params: dict[str, str] = {
        "projectId": project_id,
        "since": since,
        "until": until,
    }
    if team_id:
        params["teamId"] = team_id

    try:
        resp = requests.get(
            VERCEL_COUNT_URL,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
    except requests.RequestException as exc:
        return {
            "configured": True,
            "source": "vercel",
            "visitors_24h": None,
            "pageviews_24h": None,
            "note": f"ошибка сети: {exc}",
        }

    if resp.status_code == 404 or (
        resp.status_code >= 400
        and "web_analytics_not_enabled" in (resp.text or "")
    ):
        return {
            "configured": True,
            "source": "vercel",
            "visitors_24h": None,
            "pageviews_24h": None,
            "note": "Web Analytics не включён в проекте Vercel",
        }

    if resp.status_code >= 400:
        try:
            err = resp.json().get("error") or {}
            msg = err.get("message") or resp.text[:120]
        except Exception:
            msg = resp.text[:120]
        return {
            "configured": True,
            "source": "vercel",
            "visitors_24h": None,
            "pageviews_24h": None,
            "note": f"Vercel API {resp.status_code}: {msg}",
        }

    data = (resp.json() or {}).get("data") or {}
    visitors = data.get("visitors")
    pageviews = data.get("pageviews")
    if visitors is None and pageviews is None:
        return {
            "configured": True,
            "source": "vercel",
            "visitors_24h": None,
            "pageviews_24h": None,
            "note": "пустой ответ Analytics",
        }

    return {
        "configured": True,
        "source": "vercel",
        "visitors_24h": int(visitors or 0),
        "pageviews_24h": int(pageviews or 0),
        "note": None,
    }
