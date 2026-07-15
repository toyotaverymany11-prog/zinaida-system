# Telegram Bot: Direct Connect to 8005

## Проблема (13.07.2026)
Hermes Gateway (8642) возвращает 404 на `/api/chat-run/runs` с `provider: custom:8005, model: 8005-Router`.
Gateway знает провайдера (он есть в available-models), но НЕ может через него запустить чат-ран.

Симптом: пользователь пишет в Telegram → bot.py → Gateway → 404 Not Found.

## Причина
Hermes Gateway поддерживает chat-run ТОЛЬКО для встроенных провайдеров (openai, anthropic, deepseek, mistral и т.д.).
Кастомные провайдеры (добавленные через config.yaml `custom_providers:`) не поддерживают `/api/chat-run/runs`.

## Решение
bot.py ходит напрямую на 8005 через OpenAI-совместимый API, минуя Gateway.

**До:**
```
Telegram → bot.py → Hermes Gateway (8642) /api/chat-run/runs → 404 ❌
```

**После:**
```
Telegram → bot.py → http://127.0.0.1:8005/v1/chat/completions → 200 ✅
```

## Код (bot.py)

```python
HERMES_DIRECT_URL = "http://127.0.0.1:8005/v1/chat/completions"

ds_payload = {
    "model": "8005-Router",
    "messages": [
        {"role": "system", "content": ZINAIDA_SYSTEM_PROMPT},
        {"role": "user", "content": full_message}
    ],
    "max_tokens": 4096,
    "temperature": 0.7
}

async with session.post(HERMES_DIRECT_URL, json=ds_payload, ...) as resp:
    data = await resp.json()
    reply = data["choices"][0]["message"]["content"]
```

## Session management
- bot.py хранит сессии в `/opt/zinaida/telegram_bot/logs/tg_sessions.json` (chat_id → session_id)
- Прямой API вызов не возвращает session_id от Hermes
- Для уникальности сессии используется `f"tg_{chat_id}"` как заглушка
- Сессия сбрасывается командой `/newchat`

## System prompt
bot.py загружает `/root/.hermes/SOUL.md` при старте как `ZINAIDA_SYSTEM_PROMPT`.
Это критически важно — без system prompt 8005 отвечает как безликий Mistral/gpt-4o без личности.

## Consilium pollution (исправлено)
Было: `get_last_consilium()` добавлял контент CONSILIUM_*.md в каждое сообщение как `[Консилиум: ...]`.
Стало: consilium НЕ подгружается в обычный диалог. Приходит только утром как отдельное уведомление через `notify.py`.

## Ключевые файлы
- `/opt/zinaida/telegram_bot/bot.py` — сам бот
- `/opt/zinaida/telegram_bot/logs/tg_sessions.json` — сессии
- `/opt/zinaida/telegram_bot/notify.py` — отправка уведомлений
- `/root/.hermes/SOUL.md` — личность (system prompt)
