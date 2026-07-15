# Диагностика памяти контент-завода — 10.07.2026

## Контекст
В сессии от 10.07.2026 Олег спросил почему session_search не подтянула дизайн-тесты. 
Проведена полная диагностика всех 3 слоёв памяти.

## Измерения

### Слой 1: session_search (FTS5 по SQLite сессий)
- **Работает.** Сессия `mrdl3an8ypespj` (09.07.2026, дизайн-тесты, 114 сообщений) найдена по:
  - `"Nano Banana Seedream дизайн генерация Replicate"` — success
  - `"Seedream Replicate дизайн Мегамозг"` — success
- **Первый вызов был unavailable** — попал на момент компрессии контекста (threshold=0.8, target_ratio=0.4). Это не баг.
- Всего сессий в базе: 10+. Самая старая: 2026-07-07.

### Слой 2: Zinaida Memory MCP (ручной)
- **Статистика:** 25 total_memories, 62 unique tags, 2 links
- top_tags: аватар(2), голос(2), меню(2), темы(2), старт(2), хэндовер(2), память(2), тест(2), hyperframes(2), видео(2)
- DB: `/opt/zinaida/memory/memory.db`
- **Работает,** но требует ручного сохранения через `mcp_zinaida_memory_memory_save()`

### Слой 3: agentmemory MCP (автоматический)
- **Пустой.** `memory_sessions()` → sessions: [], `memory_audit()` → entries: []
- Порты: 3111 (MCP) и 3113 (viewer) — не отвечают на HTTP
- MCP сервер: `npx -y @agentmemory/mcp` в config.yaml
- **Коренная причина:** `memory.provider: ''` в config.yaml. agentmemory НЕ настроен как memory provider — Hermes не пишет в него автоматически. Он только MCP сервер с 43 инструментами, но без данных.

### Built-in Hermes memory
- `memory_enabled: true`, `provider: ''` — использует встроенную KV память
- Лимит: 20000 символов (memory) + 10000 (user)
- На момент диагностики: 19841/20000 = 99.2% — почти заполнено
- Скоро переполнение

## config.yaml (релевантные строки)
```yaml
memory:
  memory_enabled: true
  user_profile_enabled: true
  write_approval: false
  memory_char_limit: 20000
  user_char_limit: 10000
  provider: ''           # <-- пустой, agentmemory не подключён

mcp_servers:
  zinaida-memory:
    command: python3
    args: ["/opt/zinaida/memory/memory_server.py"]
  agentmemory:
    command: npx
    args: ["-y", "@agentmemory/mcp"]
```

## Варианты фикса

### Вариант 1 — подключить agentmemory как provider (рекомендуемый)
```yaml
memory:
  provider: agentmemory
  memory_char_limit: 50000   # увеличить лимит
```
Hermes начнёт писать key-value пары в agentmemory. Решит проблему пустоты.

### Вариант 2 — увеличить char_limit (быстрое решение)
```yaml
memory:
  memory_char_limit: 50000
  user_char_limit: 20000
```
Продлевает жизнь built-in памяти без смены provider.

### Вариант 3 — ничего не менять
session_search работает стабильно. Zinaida Memory MCP содержит 25 важных записей. design_registry.md на сервере. Для текущих задач хватает.

## Что сделано (10.07.2026)

1. **Увеличен лимит built-in памяти:** `memory_char_limit` с 20000 до **50000** (через прямой edit config.yaml)
2. **Наполнен agentmemory:** 5 записей сохранено вручную через `mcp_agentmemory_memory_save`:
   - Дизайн-реестр (шрифты, цвета, референс)
   - Тесты 7 моделей (Seedream, FLUX, Recraft, Nano Banana...)
   - Утверждённые файлы (портреты, аватары, цитаты)
   - Правила Олега (9 пунктов)
   - Три направления тестирования (A/B/C)
3. **Прописан протокол загрузки в AGENTS.md:** при выборе темы — подгружать контекст из ВСЕХ источников (agentmemory, Zinaida Memory, session_search, файлы на сервере)
4. **Сохранено в built-in memory:** инструкция о протоколе загрузки и статусе agentmemory

## Итоговое состояние (10.07.2026 07:40)

| Слой | Размер | Статус |
|------|--------|--------|
| built-in Hermes memory | 20457/50000 (40%) | ✅ Увеличен, есть запас |
| agentmemory (MCP) | 5 записей | ✅ Наполнен вручную |
| Zinaida Memory (MCP) | 26 записей | ✅ Работает |
| session_search | все 10+ сессий | ✅ Работает |
