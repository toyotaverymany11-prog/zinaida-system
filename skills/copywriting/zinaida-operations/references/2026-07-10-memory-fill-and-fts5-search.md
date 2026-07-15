# Memory Fill + FTS5 Search Protocol (2026-07-10)

## FTS5 Search — Concrete Keywords Required

**Проблема:** `session_search(query="техника роутер сервер")` возвращает 0 результатов, даже если данные есть.

**Причина:** FTS5 требует точных термов. Широкие запросы из 3+ общих слов не матчатся.

**Фикс:** Делать 3-4 отдельных запроса с **конкретными** словами:
- «роутер 8002»
- «livekit caddy»
- «telegram бот»
- «systemd cron onedrive»

**То же для Zinaida Memory MCP:** искать с FTS5-синтаксисом — кавычки для фраз, AND/OR для комбинаций. Тег-фильтр обязателен.

## Двухуровневая заливка памяти

Технические факты нужно сохранять в ОБЕ системы, иначе при следующем «техник» половина контекста потеряется:

1. **Zinaida Memory MCP** — через `mcp_zinaida_memory_memory_save()`. Работает надёжно, SQLite + FTS5. 46+ записей.
2. **agentmemory** — через `mcp_agentmemory_memory_save()`. Сохраняет в `/root/.agentmemory/standalone.json`. 13+ записей (5 дизайн + 8 техника).

**Почему обе:** Zinaida Memory ищется по тегам и FTS5. agentmemory — по концептам и семантике. Они не дублируют друг друга — ищут по-разному.

## Схема технических фактов (10.07.2026)

Zinaida Memory MCP id 35-44 (техника), 47 (бэкап):
- 35: триггер «техник»
- 37: роутер 8002
- 38: роутер 8003
- 39: vision proxy 8901
- 40: telegram-бот
- 41: livekit
- 42: onedrive rclone
- 43: memory-системы (3 уровня)
- 44: консилиум
- 47: еженедельный бэкап (systemd timer)

agentmemory: 8 технических фактов (роутер 8002/8003, vision 8901, telegram, livekit, onedrive, memory-системы, триггер)
