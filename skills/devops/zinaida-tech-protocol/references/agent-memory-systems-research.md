# Исследование систем памяти для AI-агентов (июль 2026)

## Контекст
Замена agentmemory (node.js MCP-сервер, постоянно падает). Нужно: стабильность 24/7, MCP-интеграция с Hermes Agent, русский язык, графовые связи между записями, self-hosted на Linux (7.8GB RAM).

## Таблица сравнения

| Критерий | agentmemory ❌ | Zinaida MCP (текущий) | Mem0 | Graphiti/Zep | Redis AMS | Engram |
|---|---|---|---|---|---|---|
| Стабильность | ❌ Падает | ✅ Работает | ✅ Proof | ✅ Proof | 🏆 Redis | ✅ Просто |
| MCP | ❌ Глючный | ✅ Свой | ✅ Официальный | ✅ v1.0 | ✅ Встроен | ✅ Встроен |
| Семантический поиск | ✅ | ✅ FTS5 | ✅ Vector DB | ✅ Vector+Graph | ✅ Vector+Keyword+Hybrid | ✅ SQLite FTS5 |
| Граф связей | ✅ | ❌ Нет | ✅ (Pro) | ✅ Лучший (temporal) | ❌ Нет | ⚠️ Базовый |
| Авто-экстракция фактов | ✅ | ❌ Ручная | ✅ Через LLM | ✅ Через LLM | ✅ Через LLM | ❌ |
| Временные метки | ❌ | ❌ | ✅ | ✅ Лучший | ✅ Working→Long | ✅ Git-aware |
| Русский через DeepSeek | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Docker | ❌ | ❌ | 3 контейнера (PG+Neo4j+API) | 2 контейнера (FalkorDB+API) | Redis | ❌ |
| RAM на сервере | - | - | ~1GB | ~1.5GB | ~500MB | ~50MB |
| Сложность | Средняя | Низкая | Средняя | Средняя | Низкая | Низкая |
| ⭐ GitHub | 24.6K | - | **59.9K** | 24K | ~2K | ~1K |
| Лицензия | MIT | - | Apache 2.0 | Apache 2.0 | MIT | MIT |
| Managed Cloud | - | - | Есть ($19-249/мес) | Zep Cloud | - | Lumetra |

## Детальный обзор

### 1. Mem0 — главный кандидат (59.9K ⭐)
**Архитектура:** Dual-store: векторная БД (PostgreSQL+pgvector) + граф знаний (Neo4j).
**MCP:** Официальный сервер `mem0-mcp` (npm или Docker). 6+ инструментов: add_memory, search, get_memories, delete, update.
**Self-host:** Docker Compose (3 контейнера). Требует LLM для экстракции — можно наш роутер 8003.
**Память:** Иерархия scopes: user_id, agent_id, session_id, app_id — разделяет факты по уровням.
**Цена OSS:** Бесплатно. Граф-фичи в Pro ($249/мес).
**Плюсы:** Крупнейшее сообщество, production-ready (SOC2/HIPAA), MCP-native, документация.
**Минусы:** Docker обязателен, Neo4j ~800MB RAM, граф в Pro.

**Команды:**
```bash
# MCP сервер (официальный)
npx -y @pinkpixel/mem0-mcp
# или self-hosted Docker
git clone https://github.com/mem0ai/mem0-mcp-server
docker compose up
```

### 2. Zep / Graphiti — лучший граф (24K ⭐)
**Архитектура:** Temporal Knowledge Graph — каждая связь имеет "окно валидности" (когда факт был правдой, когда устарел).
**MCP:** Graphiti MCP Server v1.0 (вышел июнь 2026). HTTP+stdio.
**Бэкенд:** FalkorDB (Redis-based graph) или Neo4j.
**Плюсы:** Рекорды на LoCoMo (74%) и LongMemEval. Детерминированное разрешение сущностей. Понимает противоречия во времени.
**Минусы:** Сложнее настройка. Zep Cloud — managed (платный). Graphiti — Open Source, но только ядро.

### 3. Redis Agent Memory Server — промышленный стандарт
**Архитектура:** Working Memory → Long-term Memory (авто-промоушн через LLM). Semantic + keyword + hybrid search.
**MCP:** Встроен (`uv run agent-memory mcp`). FastMCP powered.
**Бэкенд:** Redis (нужен отдельно).
**Плюсы:** Redis = надёжность. Активная разработка (v0.15.2). Простая установка (uv).
**Минусы:** Нет графа. Нужен Redis. Относительно молодой (~2K ⭐).

### 4. Letta (MemGPT) — фреймворк (21K ⭐)
**Архитектура:** Tiered memory как ОС: Core → Archival → Recall. Agent сам пишет/читает свою память.
**MCP:** ❌ Нет поддержки (своя архитектура агента).
**Вердикт:** Заменяет собой агента, не встраивается в Hermes. Не подходит.

### 5. Engram — лёгкая альтернатива
**Архитектура:** Go binary + SQLite + FTS5. MCP-сервер. Git-aware (цепляет память к веткам).
**Плюсы:** Простейшая установка (один бинарник). Не требует Docker. Работает с любым MCP-клиентом.
**Минусы:** Нет графа, нет авто-экстракции, слабее фич.
**Вердикт:** Резервный вариант если Docker не вариант.

### 6. Obsidian как память — НЕ ПОДХОДИТ
MCP-серверы для Obsidian есть (через REST API плагин). Но:
- Нет семантического поиска (только grep по .md)
- Нет графа (только wiki-ссылки)
- Требует Obsidian REST API плагин на iPad
- Олег отказался ставить Obsidian на iPad
**Вердикт:** ❌ Не предлагать.

## ⚡ ИТОГ (10.07.2026): Mem0 УСТАНОВЛЕН. agentmemory УДАЛЁН.

**Выбран вариант: Mem0 Python SDK + Qdrant (без Docker Compose, без PostgreSQL, без Neo4j).**

**Почему не полный Docker-стек:**
- ChromaDB не работала с mem0ai (search возвращал 0 результатов, хотя get_all работал)
- Chroma не поддерживает keyword search с mem0ai (только semantic)
- Перешли на Qdrant (один Docker-контейнер вместо трёх) — поиск заработал идеально

**Итоговая архитектура:**
- MCP-сервер: `/opt/zinaida/mem0/mem0_mcp_server.py` (Python, FastMCP, stdio)
- Vector store: Qdrant v1.18.2 (отдельный Docker-контейнер, systemd qdrant-mem0.service)
- LLM: роутер 8003 (DeepSeek), OpenAI-совместимый протокол
- Embedding: paraphrase-multilingual-MiniLM-L12-v2 (huggingface, кэширован)
- MCP имя в Hermes: `mem0-memory` (5 инструментов)
- Данные: 15 seed-памятей загружено

**Ссылки по установке:**
- MCP-сервер: `/opt/zinaida/mem0/mem0_mcp_server.py`
- Логи: `/opt/zinaida/mem0/mem0_mcp.log`
- Навык с полной документацией: `mlops/mcp-memory-system`
- Ставится через Docker (3 контейнера)
- MCP-сервер за 10 минут
- Подключаем DeepSeek через роутер 8003 для экстракции
- Русский, граф, семантика — всё есть
- 59.9K ⭐ — не бросят

**Вариант 2 (план Б): Усилить Zinaida Memory MCP**
- Текущий сервер (SQLite+FTS5) уже стабилен
- Добавить авто-экстракцию фактов через LLM (роутер 8003)
- Добавить простой граф через таблицу edges в SQLite
- Не требует Docker, не тратит RAM
- Но слабее Mem0

## Ресурсы
- Mem0: https://mem0.ai | https://github.com/mem0ai/mem0 | https://docs.mem0.ai/platform/mem0-mcp
- Mem0 self-host Docker: https://mem0.ai/blog/self-host-mem0-docker
- Mem0 MCP (community): https://github.com/elvismdev/mem0-mcp-selfhosted
- Mem0 MCP (official): https://github.com/pinkpixel-dev/mem0-mcp
- Graphiti: https://github.com/getzep/graphiti
- Graphiti MCP: https://github.com/getzep/graphiti/blob/main/mcp_server/README.md
- Redis AMS: https://github.com/redis/agent-memory-server
- Redis MCP docs: https://redis.github.io/agent-memory-server/mcp
- Engram: https://github.com/edg-l/engram-mcp
- Letta: https://github.com/letta-ai/letta
- Zep: https://www.getzep.com/platform/graphiti
- Сравнение Mem0 vs Zep: https://vectorize.io/articles/mem0-vs-zep
- 8 фреймворков памяти: https://vectorize.io/articles/best-ai-agent-memory-systems
- Состояние агентной памяти 2026: https://mem0.ai/blog/state-of-ai-agent-memory-2026
- Awesome Agent Memory: https://github.com/TeleAI-UAGI/Awesome-Agent-Memory
