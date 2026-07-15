# Telegram Bot Architecture (v3.0, 13.07.2026)

## Архитектура

```
Ты → Telegram → bot.py → Hermes Gateway 8642 (/api/chat-run/runs)
                           ↓
                    профиль default (навыки + память + MCP → 8005 Super Cascade)
```

Telegram бот теперь ходит **через Hermes Gateway**, а не напрямую на роутер. Это даёт Telegram полный доступ к:
- **Навыкам (Skills)** — 92 шт, автоматически загружаются при старте сессии
- **Инструментам** — web_search, terminal, MCP серверы, file tools
- **Памяти** — Mem0 (Qdrant, семантическая) + Holographic (автоматическая экстракция фактов)
- **Session management** — полная история в Hermes Studio, не только 20 сообщений
- **SOUL.md** — загружается Gateway через профиль default

## Gateway: правильный провайдер — ключевой нюанс

**ПИТФОЛЛ:** Gateway `/api/chat-run/runs` возвращал 404, потому что я передавала `provider: "8005-Router"`.
Правильный provider — **имя из `custom_providers` в config.yaml**, а не модель:

```python
# ❌ 404 — 8005-Router это модель, не провайдер
payload = {"provider": "8005-Router", "model": "8005-Router", ...}

# ✅ 200 — "8005" это имя custom провайдера
payload = {"provider": "8005", "model": "8005-Router", ...}
```

Проверка: `config.yaml → custom_providers:` → у имени провайдера поле `name: '8005'`.

## Компоненты bot.py (v3.0)

- **bot.py** — `/opt/zinaida/telegram_bot/bot.py`
- **Session tracking** — JSON файл `/opt/zinaida/telegram_bot/logs/tg_sessions.json` (chat_id → session_id)
- **Медиа** — сохраняются в `/opt/zinaida/telegram_bot/media/`
- **Лог** — `/opt/zinaida/telegram_bot/logs/bot.log`
- **systemd** — `zinaida-telegram-bot.service`
- **Файл истории больше не нужен** — Gateway сам управляет историей через session_id

## Команды
- `/start` — приветствие
- `/status` — статус Gateway + 8005
- `/newchat` — новая сессия (сброс контекста)

## Чем отличается от v2.0 (прямой 8005)
- v2.0: bot.py сам формировал system prompt из SOUL.md + инструкции планировщика
- v3.0: Gateway сам грузит SOUL.md, навыки, память — отдельно system prompt не нужен
- v2.0: хранил историю в JSON (20 сообщений)
- v3.0: Gateway хранит полную историю сессии
- v2.0: не имел доступа ни к навыкам, ни к инструментам
- v3.0: имеет всё то же что веб-чат в Hermes Studio

## Консилиум
НЕ подгружается в каждое сообщение — засорял контекст (бот отвечал про LoRA вместо вопроса).
Приходит утром как отдельное сообщение в Telegram через notify.py.

## Файлы
- `/opt/zinaida/telegram_bot/bot.py` — основной скрипт (v3.0)
- `/opt/zinaida/telegram_bot/notify.py` — отправка уведомлений
- `/opt/zinaida/telegram_bot/logs/bot.log` — лог бота
- `/opt/zinaida/telegram_bot/logs/tg_sessions.json` — маппинг chat_id → session_id
- `/opt/zinaida/telegram_bot/media/` — загруженные медиа-файлы
