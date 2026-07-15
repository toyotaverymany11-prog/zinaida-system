# agentmemory — установка и интеграция (09.07.2026)

## Установка
```bash
npm install -g @agentmemory/agentmemory
agentmemory  # запуск на порту 3111
```

## Подключение к Hermes
В `~/.hermes/config.yaml` добавить:
```yaml
mcp_servers:
  agentmemory:
    command: npx
    args: ["-y", "@agentmemory/mcp"]
memory:
  provider: agentmemory
```

## Плагин глубокой интеграции
Скопирован из https://github.com/rohitg00/agentmemory/tree/main/integrations/hermes
в `~/.hermes/plugins/agentmemory/`
Включает 6 lifecycle hooks: prefetch, sync_turn, on_session_end, on_pre_compress, on_memory_write, system_prompt_block

## Проблема при установке
Установленный через npm пакет не содержит папку `integrations/` — она есть только в GitHub репозитории.
Решение: `git clone --depth 1 https://github.com/rohitg00/agentmemory.git` и копировать оттуда.

## Портовая схема
- Memory server: http://localhost:3111 (JSON-RPC)
- Real-time viewer: http://localhost:3113 (браузер)
- MCP server: npx @agentmemory/mcp (через Hermes)

## Проверка
```bash
curl http://localhost:3111/agentmemory/health
# -> {"status":"healthy", ...}
```

## 263 функции, 43 MCP инструмента
Список функций в выводе health. Ключевые:
- `mem::smart-search` — гибридный поиск (BM25 + вектор + граф)
- `mem::remember` — запомнить
- `mem::relate` — связать
- `event::observation` — автоматическое наблюдение
- `mem::consolidate` — консолидация памяти
- `mem::graph-extract` — извлечение графа
- `api::graph-query` — запрос графа
