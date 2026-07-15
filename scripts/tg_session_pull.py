#!/usr/bin/env python3
"""
Загрузчик статуса Telegram-сессии для веб-чата.
Триггер: первое слово "Telegram" в новом чате.

Показывает:
- Статус Telegram-бота (активен, провайдер, роутер)
- Что было загружено (SOUL.md, консилиум)
- Последние сообщения из сессии
"""
import json, os, sys

LOGS_DIR = "/opt/zinaida/telegram_bot/logs"
SESSIONS_FILE = f"{LOGS_DIR}/tg_sessions.json"
BOT_LOG = f"{LOGS_DIR}/bot.log"
CONSILIUM_DIR = "/opt/zinaida/shared_memory/consilium"

def main():
    result = {
        "telegram_bot": {
            "version": "v2.0",
            "provider": "8005-Router (Super Cascade)",
            "system_prompt": "SOUL.md загружен ✅",
            "url": "http://127.0.0.1:8005/v1/chat/completions"
        },
        "cascade": {
            "1_mistral": "бесплатно, самооценка confidence",
            "2_github_gpt4o": "бесплатно, 2 ключа",
            "3_deepseek_flash": "$0.27/M, запасной",
            "4_deepseek_pro": "$1.42/M, экстрим"
        }
    }

    # Активные сессии
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r") as f:
            sessions = json.load(f)
        result["active_sessions"] = len(sessions)
        result["session_ids"] = list(sessions.keys())
    else:
        result["active_sessions"] = 0
        result["session_ids"] = []

    # Последний консилиум
    if os.path.exists(CONSILIUM_DIR):
        files = sorted([f for f in os.listdir(CONSILIUM_DIR) if f.startswith("CONSILIUM_")])
        if files:
            result["last_consilium"] = files[-1]
        else:
            result["last_consilium"] = None

    # Последние логи (статус)
    if os.path.exists(BOT_LOG):
        with open(BOT_LOG, "r") as f:
            lines = f.readlines()
        recent = [l.strip() for l in lines[-10:] if "ERROR" in l or "200" in l or "error" in l]
        result["recent_logs"] = recent[-5:] if recent else ["(нет ошибок)"]

    result["commands"] = {
        "/newchat": "сбросить сессию, начать новый диалог",
        "/status": "статус системы",
        "/start": "приветствие"
    }

    result["note"] = (
        "Telegram-бот @DCHP_Shtab_bot работает через 8005 Super Cascade. "
        "Личность Зинаиды загружена из SOUL.md. "
        "Если хочешь перенести контекст из Telegram сюда — напиши что обсуждали, я подхвачу."
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
