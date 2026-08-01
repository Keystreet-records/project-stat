#!/usr/bin/env python3
"""Telegram Bot API helpers."""

from __future__ import annotations

import os
from typing import Any

import requests


def bot_token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    return token


def default_chat_id() -> str:
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is required")
    return chat_id


def api(method: str, payload: dict[str, Any] | None = None, *, timeout: float = 60) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{bot_token()}/{method}"
    resp = requests.post(url, json=payload or {}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error ({method}): {data}")
    return data


def send_message(
    text: str,
    *,
    chat_id: str | None = None,
    parse_mode: str | None = "HTML",
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "chat_id": chat_id or default_chat_id(),
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return api("sendMessage", payload)


def report_keyboard() -> dict[str, Any]:
    """Persistent reply keyboard with Отчёт button."""
    return {
        "keyboard": [[{"text": "Отчёт"}]],
        "resize_keyboard": True,
        "is_persistent": True,
    }
