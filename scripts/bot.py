#!/usr/bin/env python3
"""Interactive Telegram bot: /report and «Отчёт» button on demand."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from daily_report import generate_report  # noqa: E402
from telegram_notify import (  # noqa: E402
    api,
    bot_token,
    default_chat_id,
    report_keyboard,
    send_message,
)

REPORT_TRIGGERS = {
    "отчёт",
    "отчет",
    "/report",
    "/otchet",
    "/отчёт",
    "/отчет",
}


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _is_authorized(chat_id: int | str) -> bool:
    return str(chat_id) == str(default_chat_id())


def _safe_exc(exc: BaseException) -> str:
    """Avoid leaking bot token if requests puts it in the URL."""
    text = str(exc)
    token = ""
    try:
        token = bot_token()
    except Exception:
        pass
    if token and token in text:
        text = text.replace(token, "***")
    return text


def _setup_commands() -> None:
    api(
        "setMyCommands",
        {
            "commands": [
                {"command": "report", "description": "Получить отчёт сейчас"},
                {"command": "start", "description": "Перезапустить"},
            ]
        },
        timeout=30,
    )


def _handle_start(chat_id: str) -> None:
    send_message(
        "Бот перезапущен ✅\n"
        "Нажми <b>Отчёт</b> или /report — пришлю сводку по сайтам.",
        chat_id=chat_id,
        reply_markup=report_keyboard(),
    )


def _handle_report(chat_id: str) -> None:
    send_message("⏳ Собираю отчёт…", chat_id=chat_id, parse_mode=None)
    try:
        text, _sites, _ok = generate_report(save_json=True)
        send_message(text, chat_id=chat_id, reply_markup=report_keyboard())
    except Exception as exc:
        send_message(
            f"Не удалось собрать отчёт: <code>{_safe_exc(exc)}</code>",
            chat_id=chat_id,
            reply_markup=report_keyboard(),
        )


def _dispatch(message: dict) -> None:
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return
    if not _is_authorized(chat_id):
        send_message("Доступ только для владельца бота.", chat_id=str(chat_id), parse_mode=None)
        return

    text = _normalize(message.get("text") or "")
    if not text:
        return

    # /report@BotName → /report
    cmd = text.split("@", 1)[0].split()[0] if text.startswith("/") else text

    if cmd in {"/start", "start"}:
        _handle_start(str(chat_id))
        return
    if cmd in REPORT_TRIGGERS or text in REPORT_TRIGGERS:
        _handle_report(str(chat_id))
        return


def _bootstrap() -> None:
    """Best-effort startup; network may be down (VPN)."""
    try:
        api("deleteWebhook", {"drop_pending_updates": False}, timeout=20)
    except Exception as exc:
        print(f"bot: deleteWebhook skipped — {_safe_exc(exc)}", file=sys.stderr, flush=True)
    try:
        _setup_commands()
    except Exception as exc:
        print(f"bot: setMyCommands skipped — {_safe_exc(exc)}", file=sys.stderr, flush=True)


def run() -> None:
    load_dotenv(ROOT / ".env")
    _bootstrap()
    print("project-stat bot: listening for /report and «Отчёт»", flush=True)

    offset = 0
    backoff = 3
    while True:
        try:
            data = api(
                "getUpdates",
                {"offset": offset, "timeout": 25, "allowed_updates": ["message"]},
                timeout=35,
            )
            backoff = 3
            for update in data.get("result") or []:
                offset = max(offset, int(update["update_id"]) + 1)
                message = update.get("message")
                if message:
                    _dispatch(message)
        except KeyboardInterrupt:
            print("bot: stopped", flush=True)
            return
        except Exception as exc:
            print(f"bot: error — {_safe_exc(exc)}", file=sys.stderr, flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    run()
