# Свип-протокол после удаления сервиса — пример agentmemory

**Дата:** 10.07.2026
**Сервис:** agentmemory (MCP-сервер, порт 3111, viewer 3113)
**Причина удаления:** Нестабилен, постоянно падал, не стартовал с сессией.
**Замена:** Mem0 (Qdrant + DeepSeek, порт 6333)

## Свип — найдено 5 файлов с упоминаниями

| № | Файл | Что сделано |
|---|------|-------------|
| 1 | `/opt/zinaida/scripts/tech_diagnostic.py` | Убраны 2 проверки (agentmemory MCP 3111, viewer 3113). Добавлена проверка Mem0 Qdrant 6333 |
| 2 | `/opt/zinaida/tech_protocol.md` | Убраны строки из карты сервисов и памяти. Версия 1.0→1.1 |
| 3 | `/opt/zinaida/memory/SYSTEM_SNAPSHOT.md` | Заменён блок памяти. Версия 2.1→2.2 |
| 4 | `/opt/zinaida/shared_memory/service_registry.md` | agentmemory: ✅ РАБОТАЕТ → ❌ УДАЛЁН. Добавлен Mem0: ✅ РАБОТАЕТ |
| 5 | `/opt/zinaida/AGENTS.md` | Протокол старта: agentmemory → Mem0. Триггер техник: убрана ссылка. Планировщик: переписан без agentmemory |

## Результат

```
✅ Роутер 8002 (Zinaida)     ЖИВ
✅ Роутер 8003 (Zina2)       ЖИВ
✅ Vision proxy 8901         ЖИВ
✅ Telegram-бот              ЖИВ
✅ Mem0 Qdrant (6333)        ЖИВ
✅ OneDrive rclone           ЖИВ
✅ Caddy                     ЖИВ
```

7/7 ✅ — ни одного мёртвого сервиса. В файлах системы agentmemory больше не упоминается (0 совпадений).

## Что проверять при каждом удалении сервиса

```bash
# Шаг 1: найти все ссылки
grep -rl "имя_сервиса" /opt/zinaida/ --include="*.md" --include="*.py" --include="*.yaml" --include="*.yml" --include="*.json" 2>/dev/null

# Шаг 2: проверить дополнительно корневые конфиги
grep -rl "имя_сервиса" /root/.hermes/ --include="*.yaml" --include="*.yml" 2>/dev/null
grep -rl "имя_сервиса" /root/ --include=".hermes.md" 2>/dev/null

# Шаг 3: финальная проверка
python3 /opt/zinaida/scripts/tech_diagnostic.py
echo "Осталось ссылок:"
grep -rn "имя_сервиса" /opt/zinaida/ --include="*.md" --include="*.py" --include="*.yaml" 2>/dev/null | wc -l
```
