# Consilium — утренний консилиум

## Cron
- **Время:** 3:00 UTC = 6:00 МСК ежедневно
- **Команда:** `cd /opt/zinaida/scripts && python3 consilium_v2.py && sleep 120 && python3 consilium_analyze_v2.py`

## Скрипты
- `consilium_v2.py` — сбор 21 новости из 6 каналов (GitHub Issues, GitHub Releases, Tavily, Replicate changelog, Hugging Face)
- `consilium_analyze_v2.py` — двухраундовый анализ:
  1. **Аналитик** (GitHub Models gpt-4o-mini) → топ-7
  2. **Скептик** (Ollama Cloud ministral-3:3b) → оспаривает
  3. **Финал** (GitHub Models) → топ-3

## Результаты
- Сохраняются: `/opt/zinaida/shared_memory/consilium/CONSILIUM_YYYY-MM-DD.md`
- Отправляются в Telegram через notify.py

## Формат для Telegram
Перед отправкой — очищать от markdown-символов (`**`, `###`, `*`, `` ` ``, `[ссылки](url)`), иначе Telegram отображает их нечитаемо.

## История исправлений
- **Jul 8:** Включена отправка в Telegram (была закомментирована)
- **Jul 9:** Добавлена очистка markdown перед отправкой
