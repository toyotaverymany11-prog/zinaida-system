# Сессия 2026-07-08: настройка консилиума, GitHub Models, дизайнер Лера

## Ключевые изменения за сессию

### Профили
- grigoriy → lera (дизайнер). Gateway запущен (systemd, 8645). SOUL.md обновлён — женский род.
- designer — старый профиль, gateway stopped (не используется).
- Олег (оператор, мужчина) — исправлен род обращения.

### Сети/инструменты
- **Tavily** — `web.backend: tavily` в корневом config.yaml. Ключ в .env.
- **GitHub Models** — custom provider + auxiliary.vision. Токен `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` в .env.
- **Ollama Cloud** — ключ `29d283bbe11546dd81893e8ac8438d4b._Y7S8JCwwoPN3KDjIco5ZH5M`. Бесплатные модели gemma3:4b, ministral-3:3b.

### Hermes Studio
- Репозиторий: EKKOLearnAI/hermes-studio (не EKKOLearnAI/hermes-web-ui)
- Новая фича: group-chat rooms (мульти-агентные)
- Вышел v0.6.27 (08.07.2026)
- Issue #10965 — Multiple Agents в одном group-chat
- Agent teams в Telegram — Julian Goldie протестировал

### Telegram
- Бот: @DCHP_Shtab_bot (zinaida-telegram-bot.service)
- TG_CHAT_ID=6670783611 (Олег)
- Скрипт отправки: `/opt/zinaida/telegram_bot/notify.py` — `python3 notify.py "текст"`

### Консилиум v2
- Скрипт сбора: `consilium_v2.py` (6 каналов)
- Скрипт анализа: `consilium_analyze_v2.py` (Аналитик + Скептик + Финал)
- Auto-Telegram отключён из скрипта — отправлять вручную после проверки
- Cron: 0 6 * * *

## Затыки и решения

### GitHub Models `***`
`***` — это маскировка вывода, не подстановка. Потрачено 2+ часа.
Решение: полный токен в Python коде, чтение из .env через open().
Готовый скрипт: `/opt/zinaida/scripts/consilium_analyze_v2.py` (не требует `***`).

### Hermes Studio login
admin/123456 — не подошёл. Доступ через порт 8648 не настроен.

### Ollama Cloud
gemma3:4b — `temporarily overloaded`. ministral-3:3b — 401 (возможно нет доступа). Только список моделей работает (GET /v1/models).
Fallback: GitHub Models при недоступности Ollama.

### Фильтрация консилиума
Первая версия выдавала технические баги Hermes в топ-3.
Решение: жёсткие промпты "ТОЛЬКО контент-завод, генерация картинок, AI-контент. Технические баги — отсекать."
