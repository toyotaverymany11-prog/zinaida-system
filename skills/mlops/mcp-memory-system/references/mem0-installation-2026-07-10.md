# Mem0 Installation Log — 10.07.2026

## Что устанавливали
Замена agentmemory (node.js, нестабильный) на Mem0 (Python, Qdrant, 59.9K ⭐).

## Выбор архитектуры

### Отвергнутые варианты
1. **Mem0 Docker Compose (3 контейнера)** — PostgreSQL + pgvector + Neo4j. Отвергнут: слишком тяжёлый для простой задачи.
2. **Chromadb** — пытались, search() возвращал 0 результатов при работающем get_all(). Chroma не поддерживает keyword search с mem0ai.
3. **Redis Agent Memory Server** — нужен Redis, нет графа.

### Выбранный вариант
**Mem0 Python SDK + Qdrant (один Docker-контейнер)**
- LLM: наш роутер 8003 (OpenAI-совместимый протокол, DeepSeek)
- Embedding: paraphrase-multilingual-MiniLM-L12-v2 (huggingface, 384-dim, русский)
- Vector store: Qdrant (Docker, systemd)
- MCP: собственный сервер на FastMCP

## Процесс установки

### 1. Установка пакетов
```bash
pip install mem0ai chromadb sentence-transformers
# chromadb — не заработал
pip install mcp
# FastMCP для MCP-сервера
pip install "mem0ai[extras]"
# BM25 keyword search
```

### 2. Qdrant
```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v /opt/zinaida/mem0/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
# Qdrant v1.18.2
```

### 3. MCP-сервер
Файл: `/opt/zinaida/mem0/mem0_mcp_server.py`
- FastMCP, stdio transport
- 5 инструментов: add_memory, search_memories, get_all_memories, delete_memory, delete_all_memories
- Конфиг с Qdrant + DeepSeek + multilingual embedding

### 4. Регистрация в Hermes
```bash
echo "y" | hermes mcp add mem0-memory --command python3 \
  --args /opt/zinaida/mem0/mem0_mcp_server.py
```

### 5. Systemd service для Qdrant
Файл: `/etc/systemd/system/qdrant-mem0.service`
```bash
systemctl daemon-reload && systemctl enable --now qdrant-mem0.service
```

### 6. Gateway restart
```bash
systemctl restart hermes-gateway.service
```

## Результаты тестирования

### Добавление (через MCP)
```
add_memory(content="Зинаида - аналитик мужской психологии...")
→ OK, memory extracted: "Zinaida is a male psychology analyst..."
```

### Поиск (через MCP)
```
search_memories(query="Какой стиль у Зинаиды?")
→ [0.54] Zinaida's writing style is 'Шквальный'...
→ [0.52] Zinaida's style blacklist includes...
→ [0.44] Zinaida is a male psychology analyst...
```

### Seed-памяти (15 шт, user_id="zinaida")
- Кто такая Зинаида
- Архитектура проекта (7 слоёв)
- Стиль Шквальный + чёрный список
- 8 соцсетей
- Роль Олега
- Роутер 8003 + DeepSeek
- Replicate API + LoRA
- 35 фаз отношений + smm_rag.db
- Генерация на русском, женский род

## Удаление agentmemory

```bash
rm -rf /root/.hermes/plugins/agentmemory/
rm -rf /root/.agentmemory/
# Проверка: find /root/.hermes/ -name "*agentmemory*" | grep -v sessions
# Остался только skill reference (документация) — не удаляем
```

## Известные особенности

1. **DeepSeek экстрактит факты на английском** — Mem0 посылает промпт на английском. Поиск по-русски работает через multilingual embedding. Это не проблема.
2. **Qdrant vs Chroma** — Chroma не работала с mem0ai search(). Qdrant заработал сразу.
3. **Загрузка embedding модели** — ~200MB скачивается при первом запуске. Кэшируется в `~/.cache/huggingface/hub/`.
4. **PostHog warning** — mem0ai шлёт телеметрию. Можно отключить через `MEM0_TELEMETRY=false`.
5. **spaCy not installed** — не влияет. Для русского языка не нужен.
