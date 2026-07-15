# Mem0 Health Check Protocol (12.07.2026)

Пятиступенчатая проверка Mem0 — запускать при диагностике памяти.

## Уровень 1: Qdrant

```bash
# Статус коллекции
curl -s "http://localhost:6333/collections/zinaida_memories" | python3 -c "
import sys,json
d=json.load(sys.stdin)
r=d.get('result',{})
print(f'Статус: {r.get(\"status\")}')
print(f'Точек: {r.get(\"points_count\")}')
print(f'Векторов: {r.get(\"config\",{}).get(\"params\",{}).get(\"vectors\",{}).get(\"size\",\"?\")}d')
print(f'On-disk: {r.get(\"config\",{}).get(\"params\",{}).get(\"vectors\",{}).get(\"on_disk\",\"?\")}')
"

# Снапшот (тест записи)
curl -s -X POST "http://localhost:6333/collections/zinaida_memories/snapshots" | python3 -c "
import sys,json
d=json.load(sys.stdin)
n=d.get('result',{}).get('name','?')
print(f'Снапшот: {n}')
"
```

Ожидание: статус `green`, точки >0, снапшот создаётся без ошибок.

## Уровень 2: MCP сервер

```bash
# Логи — нет ERROR после последнего фикса?
tail -5 /opt/zinaida/mem0/mem0_mcp.log
grep "Mem0 v2 initialized OK" /opt/zinaida/mem0/mem0_mcp.log | wc -l
```

Ожидание: последние записи — INFO/Processing, нет `ERROR`.

## Уровень 3: MCP инструменты

Вызвать через MCP:
1. `memory_stats` — должно вернуть total_memories, status=healthy
2. `search_memories(query="тест фикс", limit=3)` — должно вернуть >=1 результат со score >0.7

## Уровень 4: Снапшоты и бэкап

```bash
ls -la /opt/zinaida/mem0/snapshots/
crontab -l | grep backup_qdrant
```

Ожидание: снапшоты >0, cron `0 5 * * *` активен.

## Уровень 5: Ресурсы

```bash
docker stats qdrant --no-stream
du -sh /opt/zinaida/mem0/qdrant_storage/
du -sh /opt/zinaida/mem0/snapshots/
```

Ожидание: Qdrant RAM <100MB, диск <1GB.
