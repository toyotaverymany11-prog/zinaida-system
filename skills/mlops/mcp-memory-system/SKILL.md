---
name: mcp-memory-system
description: "Три уровня памяти агента: Holographic (автоматический, Hermes built-in, SQLite), Mem0 (семантический поиск + граф, Qdrant) и Zinaida Memory MCP (резервный, SQLite+FTS5)."
version: 3.0.0
author: Zinaida-System
tags: [memory, mcp, mem0, qdrant, deepseek, agent-memory, persistence, semantic-search]
---

# MCP Memory System — агентная память (3 уровня)

## Общая архитектура

```
Hermes Agent (built-in memory — быстрая, лимит 10K символов)
    ├── Holographic (АВТОМАТИЧЕСКИЙ, добавлен 12.07.2026) — Hermes built-in provider
    │       ↓ SQLite (memory_store.db), без API ключей, без инфраструктуры
    │       ↓ prefetch: авто-поиск релевантных фактов перед каждым ответом
    │       ↓ auto_extract: авто-сохранение фактов после сессии (en patterns)
    │       ↓ on_memory_write: зеркалит built-in memory action='add'
    │       → Инструменты: fact_store (add/search/probe/reason), fact_feedback
    │
    ├── Mem0 MCP (ОСНОВНОЙ ДЛЯ RAG) — семантическая память с графом
    │       ↓ LLM: роутер 8003 (DeepSeek) — ручная экстракция фактов
    │       ↓ Embedding: intfloat/multilingual-e5-base (русский, 768-dim)
    │       ↓ Vector store: Qdrant (Docker, systemd, порт 6333)
    │       ↓ Поиск: векторный (cosine), BM25 недоступен для старой коллекции
    │       → 7 инструментов: add_memory, search_memories, get_all_memories,
    │         update_memory, delete_memory, delete_all_memories, memory_stats
    │
    └── Zinaida Memory MCP (РЕЗЕРВНЫЙ) — SQLite+FTS5, ручное наполнение
            ↓ 8 инструментов: memory_save, memory_search, memory_link и др.
            ↓ Без графа (только ручные memory_link), без семантики
```

## УРОВЕНЬ 1: Mem0 (основной, с 10.07.2026)

### Суть
Mem0 (59.9K ⭐ GitHub, Apache 2.0) — самая популярная система памяти для AI-агентов. Извлекает факты из сообщений через LLM, строит векторные представления для семантического поиска и граф связей между сущностями.

**Архитектура:** Dual-store: векторная БД (Qdrant) + опционально граф (Neo4j).
**Self-hosted:** Python SDK + Qdrant (Docker, systemd). Без облака.
**MCP:** Собственный MCP-сервер на FastMCP.

### Установка

#### Pre-requisites
```bash
# Пакеты
pip install mem0ai "mem0ai[extras]"  # extras = BM25, elasticsearch

# Qdrant (Docker + systemd)
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v /opt/zinaida/mem0/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

#### Systemd unit (`/etc/systemd/system/qdrant-mem0.service`)
```ini
[Unit]
Description=Qdrant vector search engine for Mem0
After=docker.service
Requires=docker.service

[Service]
Restart=always
RestartSec=5
ExecStartPre=-/usr/bin/docker rm -f qdrant
ExecStart=/usr/bin/docker run --rm --name qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v /opt/zinaida/mem0/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
ExecStop=/usr/bin/docker stop qdrant

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload && systemctl enable --now qdrant-mem0.service
```

#### MCP-сервер (`hermes mcp add`)
```bash
# Уже добавлен как "mem0-memory" (5 инструментов)
# Если надо переустановить:
hermes mcp remove mem0-memory 2>/dev/null
echo "y" | hermes mcp add mem0-memory --command python3 \
  --args /opt/zinaida/mem0/mem0_mcp_server.py
systemctl restart hermes-gateway.service
```

### Конфигурация

**Файлы:**
- MCP-сервер: `/opt/zinaida/mem0/mem0_mcp_server.py`
- База Qdrant: `/opt/zinaida/mem0/qdrant_storage/` (persistent volume)
- Логи: `/opt/zinaida/mem0/mem0_mcp.log`
- История операций: `/opt/zinaida/mem0/history/`

**Конфиг (встроен в MCP-сервер, обновлён 12.07.2026 — добавлен Redis cache + import fix):**
```python
config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "zinaida_memories",
            "host": "localhost",
            "port": 6333,
            "embedding_model_dims": 768,  # e5-base = 768-dim
            "on_disk": True,              # данные переживают перезагрузку
        },
    },
    "llm": {
        "provider": "openai",  # OpenAI-совместимый (наш роутер)
        "config": {
            "model": "deepseek-chat",
            "openai_base_url": "http://localhost:8003/v1",  # Zina2-Router
            "api_key": "***",  # не проверяется роутером
            "temperature": 0.3,
            "max_tokens": 4000,
        },
    },
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "intfloat/multilingual-e5-base",  # 768-dim, лучший для русского
        },
    },
    "history_store": {
        "provider": "sqlite",
        "config": {"path": "/opt/zinaida/mem0/history"},
    },
}
```

**Важно:** Модель эмбеддинга multilingual-e5-base (~1.8GB на диске) кэшируется в `~/.cache/huggingface/hub/`
после первого запуска. Для ускорения загрузки установить HF_TOKEN (иначе rate-limit warning при каждом старте).
**12.07.2026:** HF_TOKEN не установлен — не критично, модель уже закэширована, грузится локально.

### ⚠️ КРИТИЧЕСКОЕ: Hermes запускает MCP через свой venv (Python 3.11)

**Установлено 12.07.2026 (диагностика «Техник 8»).**

**Симптом:** MCP сервер падает с `No module named 'mem0'`, хотя `pip3 list` показывает mem0ai установленным.
**Причина:** Hermes запускает MCP-серверы через `/usr/local/lib/hermes-agent/venv/bin/python3` (Python 3.11),
но mem0ai установлен в системный Python (/usr/bin/python3, Python 3.10). venv не видит системные site-packages.

**Проверка:**
```bash
# Какой Python реально запускает MCP?
ps aux | grep mem0_mcp_server
# → /usr/local/lib/hermes-agent/venv/bin/python3 /opt/zinaida/mem0/mem0_mcp_server.py

# mem0 в venv Hermes?
/usr/local/lib/hermes-agent/venv/bin/python3 -c "import mem0; print(mem0.__version__)"
# → ModuleNotFoundError если не установлен
```

**Фикс — установить mem0 в venv Hermes:**
```bash
/usr/local/lib/hermes-agent/venv/bin/python3 -m pip install mem0ai sentence-transformers qdrant-client
```

**Также:** sentence-transformers и torch устанавливаются под Python 3.11 (был конфликт: torch собран под 3.10, а используется 3.11 — `Python version mismatch`). `--force-reinstall` решает.

**Что НЕ работает:** retry с `addsitedir()` через `#!/usr/bin/env python3` — shebang резолвится в venv Python, у которого нет pip-пакетов. Единственный надёжный путь — установка в venv.

### BM25 hybrid search — недоступен для старой коллекции (12.07.2026)

**Симптом:** Mem0 v2.0.11 при старте пишет:
```
Collection 'zinaida_memories' predates v3 hybrid search (no 'bm25' sparse slot).
BM25 keyword scoring will be disabled for this collection; semantic search works normally.
```

**Причина:** Коллекция создана Mem0 до версии v3 (которая ввела BM25 sparse slot). Добавить задним числом нельзя.
**Влияние:** Semantic search (cosine) работает. Keyword scoring (BM25) — нет.
**Решение:** Для включения hybrid search — создать новую коллекцию и перезагрузить записи. Пока не требуется — cosine search даёт score 0.78-0.84, релевантность высокая.

### Бэкап Qdrant — автоматизирован (12.07.2026)

```bash
# Cron (добавлен 12.07.2026): ежедневно в 5:00
0 5 * * * /opt/zinaida/mem0/backup_qdrant.sh >> /opt/zinaida/mem0/backup.log 2>&1

# Скрипт: /opt/zinaida/mem0/backup_qdrant.sh
#   → Создаёт snapshot через Qdrant API
#   → Копирует из Docker в /opt/zinaida/mem0/snapshots/
#   → Keep 14 снапшотов
```

### Redis cache — добавлен (12.07.2026)

В конфиг Mem0 добавлен:
```python
"cache": {
    "provider": "redis",
    "config": {
        "host": "localhost",
        "port": 6379,   # Docker Redis уже работает
        "ttl": 3600,     # 1 час
    },
}
```
Fallback: если Redis недоступен — инициализация без кэша (graceful degradation).

### MCP инструменты Mem0 (5 шт)

| Инструмент | Описание | Параметры |
|------------|----------|-----------|
| `add_memory` | Сохранить факт в долговременную память (с JUNK_FILTER — инструкция DeepSeek что сохранять) | `content` (обяз), `user_id` (по умолч. 'zinaida') |
| `search_memories` | Семантический поиск по памяти (threshold=0.3) | `query` (обяз), `user_id`, `limit` (по умолч. 5) |
| `get_all_memories` | Показать все воспоминания пользователя | `user_id`, `limit` (по умолч. 50) |
| `update_memory` | Обновить существующую запись | `memory_id` (обяз), `content` (обяз) |
| `delete_memory` | Удалить конкретную запись по ID | `memory_id` (обяз) |
| `delete_all_memories` | Стереть всё (ОСТОРОЖНО) | `user_id` |
| `memory_stats` | Статистика памяти (количество, статус) | `user_id` |

### Когда сохранять в Mem0 — АВТОМАТИЧЕСКИ, без команд

**Правило (12.07.2026, требование Олега):** Я сама решаю что важно, и сохраняю сразу. Без ожидания команды «запомни/зафиксируй».

**Автомат:** в конце каждого ответа оценить: «было ли в этом разговоре что-то, что стоит сохранить?» (решение, фикс, архитектура, договорённость, урок). Если да — вызвать add_memory ДО отправки ответа. Не откладывать. Потом = никогда.

**Параметры сохранения (entity scoping):**
```python
# user_id — кто (всегда "zinaida")
# agent_id — какая система ("zinaida-main", "zinaida-tech", "zinaida-writer")
# run_id — какая сессия (авто: "session-YYYYMMDD")
mcp_mem0_memory_add_memory(
    content="...",
    user_id="zinaida",
    agent_id="zinaida-main",
    # run_id генерируется автоматически
)
```

**Что это даёт:**
- Поиск по `agent_id` — найди всё что писатель сохранил, или всё что техник
- Поиск по `run_id` — найди всё что обсуждали 12 июля
- Фильтрация: `search_memories(user_id="zinaida", agent_id="zinaida-main")`

**Что сохранять:**
1. **Решения и договорённости** — что выбрали, утвердили, согласовали
2. **Архитектура и конфиги** — какие сервисы, порты, версии, изменения
3. **Фиксы и проблемы** — что сломалось, как починили, корень
4. **Правила и уроки** — что нельзя делать, что работает, стиль
5. **О пользователе** — Олег: предпочтения, роли, окружение
6. **Планы и следующие шаги** — что решили делать дальше

### Когда НЕ сохранять

- Временные данные (пути, ID сессий, PID)
- Текущие задачи (для этого todo/kanban)
- То что уже есть в built-in memory
- Приветствия, прощания, общие фразы
- Промежуточные логи ошибок (только финальное решение)

### Поток работы

1. Узнала важное → НЕ ждать → `add_memory(content="...", user_id="zinaida")` сразу
2. В новом чате → `search_memories(query="что знаю о ...", user_id="zinaida")`
3. Нужен список → `get_all_memories(user_id="zinaida")`
4. Факт устарел → `update_memory(memory_id="...", content="...")`

### Полная диагностика Mem0

Для развёрнутой диагностики (когда Олег просит «проверь память»):
**`references/mem0-diagnostics-protocol.md`** — 10 шагов: Qdrant, записи, поиск, логи, конфиг, бэкапы, ресурсы, HF_TOKEN.

### Краткая проверка работоспособности

```bash
# Qdrant жив?
curl -s http://localhost:6333/ | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['version'])"

# Детали коллекции
curl -s "http://localhost:6333/collections/zinaida_memories" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('result',{})
print(f\"Статус: {d.get('status')}, Точек: {d.get('points_count')}\")
"

# Логи MCP-сервера
tail -20 /opt/zinaida/mem0/mem0_mcp.log

# Статистика (через MCP)
mcp_mem0_memory_memory_stats(user_id="zinaida")

# Поиск (через MCP)
mcp_mem0_memory_search_memories(query="тестовый запрос по-русски", user_id="zinaida", limit=3)

### Типичные проблемы

| Проблема | Решение |
|----------|---------|
| MCP-сервер не отвечает | `systemctl is-active qdrant-mem0.service` — проверить Qdrant |
| Qdrant упал | `systemctl restart qdrant-mem0.service` |
| Поиск пустой | Проверить Qdrant: `curl -s http://localhost:6333/collections/zinaida_memories` |
| Embedding медленный (~3 сек) | Нормально для CPU. Модель кэширована, прогрев первый запуск |
| DeepSeek экстрактит на английском | Нормально. Поиск по-русски работает через multilingual embedding |
| MCP ERROR: mem0ai not installed | Retry-цикл исправляет. Если повторяется — проверить `pip3 show mem0ai` и `python3 -c "import mem0"` |
| DeepSeek экстрактит на английском | Нормально. Поиск по-русски работает через multilingual embedding |

## УРОВЕНЬ 2: Zinaida Memory MCP (резервный, ручной)

### Когда использовать
- Если Mem0 недоступен (Qdrant упал, нет Docker)
- Для ручных графовых связей (memory_link)
- Для записей, которые не нужно искать семантически

### Краткая справка
- Сервер: `/opt/zinaida/memory/memory_server.py`
- БД: `/opt/zinaida/memory/memory.db` (SQLite WAL + FTS5)
- MCP имя: `zinaida-memory` (8 инструментов)
- Подробнее: старая версия этого навыка (v1.0)

## УРОВЕНЬ 3: Holographic (добавлен 12.07.2026) — автоматическая память Hermes

### Суть
Holographic — встроенный Hermes memory provider (не MCP). SQLite-based, без API ключей, без дополнительной инфраструктуры. Хранит структурированные факты с entity resolution, trust scoring и FTS5-поиском.

**Главное преимущество:** `prefetch` — автоматически ищет релевантные факты перед каждым ответом и инжектит их в system prompt. Это работает на ЛЮБОМ языке (FTS5 keyword search).

### Когда использовать

| Ситуация | Что использовать |
|----------|-----------------|
| Автоматическая память между сессиями | **Holographic** — prefetch сам ищет факты |
| Семантический поиск по смыслу | **Mem0** — search_memories (vector) |
| Важные решения — сохранить навсегда | **Mem0 add_memory** + **fact_store** |
| Быстрая контекстная память | **MEMORY.md** (built-in) |

### Активация

```bash
hermes memory setup holographic
# → Provider: holographic, Status: available ✓
```

### БД и схема

`~/.hermes/memory_store.db` (SQLite)

```sql
facts (fact_id, content, category, tags, trust_score, retrieval_count, helpful_count, created_at, updated_at, hrr_vector)
entities (entity_id, name, entity_type, aliases, created_at)
fact_entities (fact_id, entity_id)
memory_banks (bank_id, bank_name, vector, dim, fact_count, updated_at)
-- FTS5: facts_fts (content, tags)
```

### Настройка

В `~/.hermes/config.yaml`:
```yaml
plugins:
  hermes-memory-store:
    auto_extract: true        # авто-экстракция (en patterns)
    default_trust: 0.5        # trust score для новых фактов
    min_trust_threshold: 0.3   # мин. trust для prefetch
```

### Механизм auto_extract

Работает при `on_session_end()`. Ищет английские паттерны:
- `I prefer/like/love/use/want/need ...` → user_pref
- `we decided/agreed/chose ...` → project

**На русском не срабатывает.** Для русского контента — `memory(action='add')` (зеркалируется через on_memory_write) или `fact_store(action='add')`.

### Инструменты сессии

- `fact_store(action='add', content='...', category='general')` — сохранить факт
- `fact_store(action='search', query='...')` — поиск по ключевым словам
- `fact_store(action='probe', entity='Олег')` — все факты о сущности
- `fact_store(action='reason', entities=['Олег', 'Зинаида'])` — пересечение
- `fact_feedback(action='helpful', fact_id=1)` — оценить факт (тренировка trust)

### Поток работы

1. Важный факт → `fact_store(action='add', content='...')` ИЛИ `memory(action='add', ...)`
2. В каждой сессии → holographic сам ищет релевантное через prefetch
3. Если holographic не находит → Mem0 search_memories (семантический)

### Проверка

```bash
hermes memory status
# Provider: holographic, available ✓

# Прямой запрос к БД
sqlite3 ~/.hermes/memory_store.db "SELECT COUNT(*) FROM facts;"
```

### Cache и место
- `memory_store.db` — ~4KB пустая, растёт с фактами
- huggingface cache (~1.8GB) — НЕ для holographic (только для Mem0 e5-base)
- state.db — 123MB (общая БД Hermes)

## История изменений

| Дата | Изменение |
|------|-----------|
| 10.07.2026 | Полная замена agentmemory на Mem0. Qdrant через systemd. MCP-сервер на FastMCP. |
| 09.07.2026 | Создан навык v1.0: Zinaida Memory MCP (SQLite+FTS5), agentmemory (node.js) |
