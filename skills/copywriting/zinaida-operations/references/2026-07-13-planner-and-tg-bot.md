# Планировщик и Telegram бот — полная карта (13.07.2026)

## Планировщик
- **Todoist API:** `/opt/zinaida/todoist_integration/todoist_api.py` — REST v1, прямой токен
- **scheduler.py:** `/opt/zinaida/scripts/scheduler.py` — парсит текст, cron + Todoist + events.json
- **Хранилище:** `/opt/zinaida/shared_memory/events.json`
- **Cron проверка:** `*/15 * * * * python3 scheduler.py check`
- **7 проектов Todoist:** Стратегия, Контент, Техника, Дизайн, Встречи, Идеи, Inbox

## Telegram bot эволюция
1. Изначально: `bot.py → 8002` (голой Gemini, без system prompt) — тупил
2. Переключено на `8003` (DeepSeek Flash/Pro) — лучше, но дорого
3. Переключено на `Gateway 8642` через `/api/chat-run/runs` — 404 (gateway не умеет custom провайдеры)
4. **Финально:** `bot.py → http://127.0.0.1:8005/v1/chat/completions` напрямую
   - System prompt = SOUL.md + SCHEDULER_INSTRUCTION
   - История диалога: последние 20 сообщений в `/opt/zinaida/telegram_bot/logs/history_{chat_id}.json`
   - Консилиум НЕ подгружается в каждое сообщение (починено 13.07)

## Железное правило тестирования (13.07.2026)
Перед «готово» — 3 проверки:
1. Компонент работает (health-check, curl)
2. Интеграция (ничего не сломалось)
3. Telegram отвечает (реальный запрос)
