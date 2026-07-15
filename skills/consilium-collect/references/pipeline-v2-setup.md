# Настройка консилиума v2 — эволюция

## ⚠️ 12.07.2026: СКРИПТЫ consilium_v2.py И consilium_analyze_v2.py УДАЛЕНЫ
Не существуют в файловой системе. Только consilium_analyze.py (старый, с хардкодом) остался.
Cron `0 3 * * *` всё ещё ссылается на удалённые скрипты. При запуске — ошибка.

## v2.0 (2026-07-08) — Первый запуск (ИСТОРИЧЕСКИ)
- Сбор: `/opt/zinaida/scripts/consilium_v2.py` — 6 каналов, 21 результат → RAW JSON
- Анализ: `/opt/zinaida/scripts/consilium_analyze_v2.py` — Аналитик → Скептик → Финал → файл

## v2.1 (2026-07-09) — Затыки выявлены
- **RAW JSON не пришёл** — consilium_v2.py сгенерировал только диджесты (replicate/DIGEST, hermes_studio/DIGEST). RAW-файл отсутствовал.
- **Telegram таймаут** — notify.py упал с httpx.ConnectTimeout. Сервер не доходит до api.telegram.org. Fallback: сохранить CONSILIUM_*.md, сообщить в ответе.
- **Анализ сделан Зинаидой напрямую** — 3-раундовый LLM-пайплайн не запускался. Прочитаны диджесты, выполнена фильтрация и формулировка вручную. Результат: CONSILIUM_2026-07-09.md.

## Telegram
- Бот @DCHP_Shtab_bot, сервис zinaida-telegram-bot.service
- TG_CHAT_ID=6670783611 (Олег)
- Отправка: `python3 /opt/zinaida/telegram_bot/notify.py "текст"`
- Известная проблема: ConnectTimeout (httpx). Не retry, сохранить в файл.

## Затык: автоотправка
В первой версии скрипт отправлял сырой вывод модели в Telegram.
Исправление: убрать auto-Telegram из скрипта, отправлять вручную после проверки.

## Затык: фильтрация
Первая версия промптов не отсекала технические баги Hermes → топ-3 состоял из "починить Leave Room" и "исправить ZAI provider".
Исправление: добавить жёсткое "ТОЛЬКО контент-завод, отсекать техбаги" в промпты и инструкцию Зинаиде.

## Источники данных (живые на 07.2026)
- Replicate changelog: https://replicate.com/changelog
- Hermes Studio releases: https://github.com/EKKOLearnAI/hermes-studio/releases
- Mage blog (skin/AI art): https://blog.mage.space/
- Atlas Cloud (model comparison): https://www.atlascloud.ai/blog/guides/best-ai-image-generation-models-2026
- Imagera (LoRA guide): https://imagera.ai/learn/best-lora-models-realistic-ai-images-2026
