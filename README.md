# Project Stat

Ежедневный мониторинг сайтов **Key Street** и **Amelindrum** → отчёт в Telegram.
Работает **в облаке** (без Mac и без VPN).

## Как устроено

| Что | Где |
|-----|-----|
| Ежедневно в **11:00 МСК** | GitHub Actions (`project-stat-report.yml`) |
| Кнопка **Отчёт** / `/report` | Vercel webhook `api/telegram` → Actions → Telegram |
| Секреты | GitHub Secrets + Vercel env |

```
Telegram → Vercel /api/telegram
        → «⏳ Собираю…»
        → repository_dispatch
        → GitHub Actions → daily_report.py → Telegram
```

## Секреты

GitHub Actions:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `VERCEL_TOKEN`
- `VERCEL_TEAM_ID`

Vercel (webhook):

- те же Telegram + `GH_PAT` (токен с правом `repo` на этот репозиторий)
- `GH_REPO=Keystreet-records/project-stat`
- `TELEGRAM_WEBHOOK_SECRET` (произвольная строка)

## Локальный прогон

```bash
cp .env.example .env   # заполнить токены
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/daily_report.py
```

Локальный polling-бот (`scripts/bot.py`) — только для отладки; в проде используется webhook.

## Добавить сайт

Правка `config/sites.yaml` — новый блок `id` / `url` / `checks` / `vercel_project`.
