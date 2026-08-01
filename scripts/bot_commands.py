# Shared helpers for Telegram bot (polling / webhook).

from __future__ import annotations

from telegram_notify import report_keyboard, send_message

REPORT_TRIGGERS = {
    "отчёт",
    "отчет",
    "/report",
    "/otchet",
    "/отчёт",
    "/отчет",
}


def normalize(text: str) -> str:
    return (text or "").strip().lower()


def is_report_command(text: str) -> bool:
    raw = normalize(text)
    if not raw:
        return False
    cmd = raw.split("@", 1)[0].split()[0] if raw.startswith("/") else raw
    return cmd in REPORT_TRIGGERS or raw in REPORT_TRIGGERS


def is_start_command(text: str) -> bool:
    raw = normalize(text)
    if not raw:
        return False
    cmd = raw.split("@", 1)[0].split()[0] if raw.startswith("/") else raw
    return cmd in {"/start", "start"}


def handle_start(chat_id: str) -> None:
    send_message(
        "Бот перезапущен ✅\n"
        "Нажми <b>Отчёт</b> или /report — пришлю сводку по сайтам.",
        chat_id=chat_id,
        reply_markup=report_keyboard(),
    )


def handle_report_ack(chat_id: str) -> None:
    send_message(
        "⏳ Собираю отчёт в облаке… пришлю сюда через минуту.",
        chat_id=chat_id,
        parse_mode=None,
        reply_markup=report_keyboard(),
    )
