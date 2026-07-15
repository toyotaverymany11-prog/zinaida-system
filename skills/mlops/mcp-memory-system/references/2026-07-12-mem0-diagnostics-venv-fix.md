# Mem0 диагностика + фикс venv — 12.07.2026 (Техник 8)

## Контекст
Олег попросил проверить систему Mem0: работает ли, эффективно ли, хватает ли настроек.
Проведено глубокое исследование Mem0 best practices (12.07.2026) через deep_research.

## Найденные проблемы

### 🔴 #1 — Import error на старте MCP
**Симптом:** Каждые 30 секунд MCP лог: `[ERROR] No module named 'mem0'`
**Корень:** Hermes запускает MCP-серверы через свой venv Python:
```
/usr/local/lib/hermes-agent/venv/bin/python3 (Python 3.11)
```
а mem0ai был установлен только в системный Python:
```
/usr/bin/python3 (Python 3.10)
```
`#!/usr/bin/env python3` резолвится в venv Python (Hermes управляет PATH).
**Фикс:** `pip install mem0ai sentence-transformers qdrant-client` в venv Hermes.

**Доп. проблема:** После установки в venv — `Python version mismatch: module compiled for 3.10, interpreter 3.11`.
**Фикс:** `--force-reinstall sentence-transformers qdrant-client` для пересборки под Python 3.11.

### 🔴 #2 — Бэкап Qdrant не запускался
**Симптом:** backup_qdrant.sh существует, но не подключен к cron/systemd. 2 снапшота за 2 дня — ручные.
**Фикс:** `0 5 * * * /opt/zinaida/mem0/backup_qdrant.sh >> /opt/zinaida/mem0/backup.log 2>&1`

### 🟡 #3 — HF_TOKEN не установлен
**Симптом:** `Warning: You are sending unauthenticated requests to the HF Hub`
**Причина:** sentence-transformers при загрузке embedding-модели пытается проверить HuggingFace.
**Статус:** Модель уже закэширована (~1.8GB в ~/.cache/huggingface/hub/). Не критично — косметика.
**Решение:** Получить токен на huggingface.co → Settings → Access Tokens → New token (read-only).

### 🟡 #4 — Redis не использовался
**Симптом:** Mem0 работал без кэша. Redis (Docker) запущен, но не подключён.
**Фикс:** В config Mem0 добавлен `cache: {provider: redis, host: localhost, port: 6379, ttl: 3600}`.
Если Redis недоступен — graceful fallback без кэша.

### 🟡 #5 — BM25 hybrid search disabled
**Симптом:** Collection predates v3 — нет sparse slot для BM25.
**Влияние:** Только semantic (cosine) search. BM25 keyword scoring не работает.
**Решение:** Создать новую коллекцию при необходимости.

### 🟡 #6 — 20 записей, нет авто-сохранения
**Симптом:** В Mem0 всего ~20 записей (10 seed + ~10 из диалогов).
**Причина:** Нет автоматического сохранения фактов из диалогов — только ручное через mcp_mem0_memory_add_memory.
**Решение:** Пока не реализовано. Требует хука на конец диалога или расписания.

## Глубокое исследование Mem0 (12.07.2026)

Проведено через deep_research_orchestrator. Отчёт:
`/opt/zinaida/sandbox/deep_research/20260712_074744_Mem0_практика_использования__советы__оши/report.html`
`/opt/zinaida/sandbox/deep_research/20260712_074744_Mem0_практика_использования__советы__оши/final_report.md`

### Ключевые выводы исследования
1. Mem0 — де-факто стандарт памяти AI-агентов (41K ⭐, 14M загрузок, Y Combinator)
2. Entity-Scoped Memory: user_id, agent_id, app_id, run_id — критично
3. Гибридный поиск + zerank-1 reranking даёт +20-30% точности
4. Рекомендуемая embedding-модель: Qwen 600M (у нас e5-base — ок, но можно апгрейднуть)
5. Разделение временной (run_id) и постоянной (user_id) памяти

### Применимость к нашей системе
- ✅ Entity scoping: user_id используется
- ✅ Настроен junk filter (97.8% noise reduction)
- ✅ on_disk=True — данные переживают перезагрузку
- ⚠️ Нет agent_id, app_id, run_id разделения
- ⚠️ Нет zerank-1 reranking
- ⚠️ Нет авто-чистки устаревших данных
