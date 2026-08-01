/**
 * Telegram webhook → ack in chat → trigger GitHub Actions report.
 * Heavy work (health + analytics + Telegram send) runs in Actions (no Mac/VPN).
 */
module.exports = async function handler(req, res) {
  if (req.method === "GET") {
    res.status(200).json({ ok: true, service: "project-stat-telegram-webhook" });
    return;
  }
  if (req.method !== "POST") {
    res.status(405).json({ ok: false, error: "method not allowed" });
    return;
  }

  const token = process.env.TELEGRAM_BOT_TOKEN;
  const allowedChatId = String(process.env.TELEGRAM_CHAT_ID || "");
  const ghPat = process.env.GH_PAT;
  const ghRepo = process.env.GH_REPO || "Keystreet-records/project-stat";

  if (!token || !allowedChatId) {
    res.status(500).json({ ok: false, error: "telegram env missing" });
    return;
  }

  const secret = process.env.TELEGRAM_WEBHOOK_SECRET;
  if (secret) {
    const header = req.headers["x-telegram-bot-api-secret-token"];
    if (header !== secret) {
      res.status(401).json({ ok: false, error: "bad secret" });
      return;
    }
  }

  const update = req.body || {};
  const message = update.message;
  if (!message) {
    res.status(200).json({ ok: true, ignored: true });
    return;
  }

  const chatId = String(message.chat && message.chat.id);
  const text = String(message.text || "").trim();
  const lower = text.toLowerCase();
  const cmd = lower.startsWith("/")
    ? lower.split("@")[0].split(/\s+/)[0]
    : lower;

  const isStart = cmd === "/start" || cmd === "start";
  const isReport =
    cmd === "/report" ||
    cmd === "/otchet" ||
    cmd === "/отчёт" ||
    cmd === "/отчет" ||
    lower === "отчёт" ||
    lower === "отчет";

  if (chatId !== allowedChatId) {
    await tg(token, "sendMessage", {
      chat_id: chatId,
      text: "Доступ только для владельца бота.",
    });
    res.status(200).json({ ok: true });
    return;
  }

  if (isStart) {
    await tg(token, "sendMessage", {
      chat_id: chatId,
      text:
        "Бот в облаке ✅\nНажми <b>Отчёт</b> или /report — пришлю сводку по сайтам.",
      parse_mode: "HTML",
      reply_markup: reportKeyboard(),
      disable_web_page_preview: true,
    });
    res.status(200).json({ ok: true });
    return;
  }

  if (isReport) {
    await tg(token, "sendMessage", {
      chat_id: chatId,
      text: "⏳ Собираю отчёт в облаке… пришлю сюда через минуту.",
      reply_markup: reportKeyboard(),
      disable_web_page_preview: true,
    });

    if (!ghPat) {
      await tg(token, "sendMessage", {
        chat_id: chatId,
        text: "Ошибка конфигурации: нет GH_PAT для запуска отчёта.",
        reply_markup: reportKeyboard(),
      });
      res.status(200).json({ ok: false, error: "GH_PAT missing" });
      return;
    }

    try {
      await dispatchReport(ghPat, ghRepo);
    } catch (err) {
      await tg(token, "sendMessage", {
        chat_id: chatId,
        text: `Не удалось запустить облачный отчёт: ${String(err.message || err)}`,
        reply_markup: reportKeyboard(),
      });
      res.status(200).json({ ok: false });
      return;
    }

    res.status(200).json({ ok: true, dispatched: true });
    return;
  }

  res.status(200).json({ ok: true, ignored: true });
};

function reportKeyboard() {
  return {
    keyboard: [[{ text: "Отчёт" }]],
    resize_keyboard: true,
    is_persistent: true,
  };
}

async function tg(token, method, body) {
  const r = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`Telegram ${method}: ${r.status} ${t.slice(0, 200)}`);
  }
  return r.json();
}

async function dispatchReport(pat, repo) {
  const url = `https://api.github.com/repos/${repo}/dispatches`;
  const r = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${pat}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      event_type: "telegram-report",
      client_payload: { source: "telegram" },
    }),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`GitHub dispatch: ${r.status} ${t.slice(0, 200)}`);
  }
}
