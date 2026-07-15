# Telegram Bot Architecture — Zinaida Bridge

## Two Telegram Bots (12.07.2026)

| Бот | Сервис | Скрипт | Token | LLM endpoint | Назначение |
|-----|--------|--------|-------|-------------|------------|
| @DCHP_Shtab_bot | `zinaida-telegram-bot.service` | `/opt/zinaida/telegram_bot/bot.py` | TG_BOT_TOKEN из `/root/.hermes/.env` | `127.0.0.1:8002` (Zinaida-Router) | Основной — общение с Олегом, получение консилиума |
| IraBrief | `ira-bot.service` | `/opt/zinaida/yadro/IraBrief.py` | TELEGRAM_BOT_TOKEN из `/opt/zinaida/config/secrets.env` | `127.0.0.1:8002` (Zinaida-Router) | Маркетолог Ира — брифинг клиентов |

## КРИТИЧЕСКАЯ ПРОБЛЕМА (12.07.2026)

### Telegram bot отвечает как «даун» — root cause

Файл: `/opt/zinaida/telegram_bot/bot.py`, функция `send_to_hermes()` (строка 92-139).

**Как сейчас работает:**
```python
payload = {
    "model": "Zinaida-Router",
    "messages": [
        {"role": "user", "content": full_message}  # ← ТОЛЬКО user, без system prompt
    ]
}
```

**Проблемы:**
1. **Нет system prompt** — запрос не содержит ДНК Зинаиды, стиля, правил. Модель (Gemini 2.0 Flash) отвечает как голый LLM без личности.
2. **Нет истории** — каждый запрос single-turn. Ни Gemini, ни DeepSeek не помнят прошлые сообщения.
3. **Порт 8002 — голый прокси** — в отличие от Hermes Studio (8642), у 8002 нет system prompt, profile, навыков, Mem0 памяти.
4. **Нет контекста консилиума** — если Олег спрашивает про пункт из утренней рассылки, бот не знает, о чём речь.

**Результат:** Когда Олег пишет в Telegram после утреннего консилиума "давай это протестируем" — Gemini Flash без контекста выдаёт generic ответ. Олег: «как будто Даун какой-то отвечает».

### Отличия от Hermes Studio (Web UI)

| Параметр | Hermes Studio (Web UI) | Telegram bot |
|----------|----------------------|--------------|
| System prompt | ✅ Полный (ДНК Зинаиды + стиль) | ❌ Отсутствует |
| История сессии | ✅ Поддерживается | ❌ Single-turn |
| Навыки (skills) | ✅ Подгружаются | ❌ Нет |
| Mem0 память | ✅ Доступна | ❌ Нет |
| Модель | Zina2-Router (DeepSeek) | Gemini 2.0 Flash |
| Роутер | 8642 (Hermes Studio) | 8002 (голый прокси) |

## Направление фикса (предложен 12.07.2026)

**Вариант А (рекомендован):** Подключить bot.py к Hermes Studio API через порт 8642 вместо 8002.

Как:
- bot.py создаёт Hermes Studio сессию при старте (через `/api/hermes/sessions`)
- Каждое сообщение пользователя → POST в эту сессию
- Ответ — тот же, что видит Олег в Hermes Studio (с полным контекстом Зинаиды)
- Получает system prompt, навыки, Mem0, историю

**Вариант Б (проще, но слабее):** Внедрить system prompt в bot.py.
- Читать ZINAIDA_IDENTITY.md из проекта и передавать как system prompt
- Всё равно без истории, навыков и памяти
- Лучше, чем ничего, но не полноценно

## One-way Notification Pattern

Консилиум и другие автоматические уведомления НЕ проходят через полноценный LLM-диалог.
Они используют однонаправленный уведомитель:

```
cron/скрипт → notify.py → Telegram (send_message только)
```

Файл: `/opt/zinaida/telegram_bot/notify.py`

```python
async def send(text, chat_id=None):
    from telegram import Bot
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=chat_id or DEFAULT_CHAT_ID, text=text)
```

Это отправляет текст в Telegram, НО когда Олег отвечает на это сообщение — ответ идёт в bot.py (см. критическую проблему выше), а notify.py об этом не знает.

## Потенциальный улучшатель: контекстный триггер

Олег предложил: первое слово «Telegram» в новом чате Hermes Studio = автоматом подгружать Telegram-контекст (историю, последние сообщения, консилиум дня) и привязывать к Telegram-сессии.

## Связанные файлы

- `/opt/zinaida/telegram_bot/bot.py` — основной бот
- `/opt/zinaida/telegram_bot/notify.py` — однонаправленные уведомления
- `/opt/zinaida/yadro/IraBrief.py` — второй бот (Ира)
- `/opt/zinaida/telegram_bot/logs/` — логи бота
- `/etc/systemd/system/zinaida-telegram-bot.service`
- `/etc/systemd/system/ira-bot.service`
