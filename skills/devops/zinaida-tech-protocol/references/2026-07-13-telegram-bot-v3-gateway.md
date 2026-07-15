# Telegram Bot v3.0 — Gateway API Migration (13.07.2026)

## Проблема
Telegram бот @DCHP_Shtab_bot ходил НАПРЯМУЮ к роутеру 8005 через OpenAI API (`POST /v1/chat/completions`), минуя Hermes Gateway. Из-за этого Telegram терял:

| Что терял Telegram | Статус |
|---|---|
| Навыки (Skills — 92 шт) | ❌ не загружались |
| Инструменты (web_search, terminal, MCP, vision) | ❌ недоступны |
| Память Mem0 + Holographic | ❌ не подключена |
| Session management (полноценный) | ❌ только 20 сообщений в JSON |
| SOUL.md (ДНК Зинаиды) | ⚠️ ручная загрузка в system prompt |

## Решение
Переписать bot.py → v3.0 — ходить через Gateway `/api/chat-run/runs`.

**Ключевой питфолл:** Gateway отдавал 404, потому что передавали `provider: "8005-Router"` (это модель, не провайдер). Правильное имя провайдера — `"8005"` (из `custom_providers` в config.yaml).

```
# ❌ 404 — "8005-Router" это model
payload = {"provider": "8005-Router", ...}

# ✅ 200 — "8005" это name из custom_providers
payload = {"provider": "8005", "model": "8005-Router", ...}
```

**Как проверить правильное имя провайдера:**
```bash
grep -A2 "name:" /root/.hermes/config.yaml | grep "8005"
# → name: '8005'
```

## Новая архитектура
```
Telegram → bot.py → Gateway 8642 (/api/chat-run/runs)
    provider: "8005"
    model: "8005-Router"
    profile: "default"
    → профиль default (навыки + память + MCP + SOUL.md)
    → 8005 Super Cascade
```

## Что изменилось в bot.py

**Старое (v2.0):**
- `HERMES_DIRECT_URL = "http://127.0.0.1:8005/v1/chat/completions"` — прямой вызов
- System prompt загружался из SOUL.md вручную
- История хранилась в JSON (20 последних сообщений)

**Новое (v3.0):**
- `HERMES_CHAT_RUN = "http://127.0.0.1:8642/api/chat-run/runs"` — через Gateway
- Gateway сам загружает навыки, память, SOUL.md, MCP
- Session management через Gateway (session_id сохраняется в JSON)

## Результаты тестирования (7 тестов)

| Тест | Результат |
|------|-----------|
| 1. Простой вопрос (приветствие) | ✅ Ответ живой, с личностью Зинаиды |
| 2. Сложный анализ (3 причины с цифрами) | ✅ Ушёл на 8005-github (бесплатно) |
| 3. Память контекста (ссылается на предыдущий ответ) | ✅ Модель помнит историю |
| 4. Навыки и инструменты | ✅ Полный список: инструменты, интеграции, память |
| 5. Telegram bot service | ✅ active, polling каждые 10 сек |
| 6. Логи без ошибок | ✅ v3 — 0 ошибок |
| 7. Консилиум | ✅ cron в 6:00 МСК, notify.py отдельно |

## Файлы
- `/opt/zinaida/telegram_bot/bot.py` — v3.0
- `/opt/zinaida/telegram_bot/bot.py.bak.20260713_0703` — бэкап v2.0
