# Qdrant Container Restoration (12.07.2026)

## Симптом

Qdrant Docker container пропал (docker rm, crash, cleanup). Mem0 не работает, MCP падает с `Connection refused`.

## Диагностика

```bash
# Контейнер существует?
docker ps -a --format "{{.Names}} {{.Status}}" | grep qdrant
# → пусто = контейнера нет

# Данные на диске?
ls -la /opt/zinaida/mem0/qdrant_storage/
# → должны быть папки collections, aliases, .deleted

# Qdrant API жив?
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:6333/
# → 000 = не отвечает
```

## Восстановление

Данные хранятся на диске в `/opt/zinaida/mem0/qdrant_storage/` — on_disk=True, они переживают удаление контейнера.

```bash
# Поднять контейнер с теми же данными
docker run -d \
  --name qdrant \
  --restart unless-stopped \
  -p 6333:6333 \
  -p 6334:6334 \
  -v /opt/zinaida/mem0/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Проверка через 5 секунд
sleep 5
curl -s "http://localhost:6333/collections/zinaida_memories" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Status: {d.get(\"result\",{}).get(\"status\")}, Points: {d.get(\"result\",{}).get(\"points_count\")}')"
# → Status: green, Points: 90+
```

## Почему контейнер пропал

Возможные причины:
- `docker system prune` (если кто-то запустил)
- Ручное удаление
- Сбой Docker daemon

## Профилактика

Контейнер запущен с `--restart unless-stopped` — переживает рестарт Docker и сервера.

**Бэкап:** ежедневный cron `0 5 * * * /opt/zinaida/mem0/backup_qdrant.sh` сохраняет снапшоты в `/opt/zinaida/mem0/snapshots/`.

## Связанное

- Mem0 MCP server: `/opt/zinaida/mem0/mem0_mcp_server.py`
- Логи: `/opt/zinaida/mem0/mem0_mcp.log`
- Бэкап: `/opt/zinaida/mem0/backup_qdrant.sh`
