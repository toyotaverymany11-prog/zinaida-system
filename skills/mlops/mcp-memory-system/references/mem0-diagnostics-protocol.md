# Mem0 Full Diagnostic Protocol

Когда Олег просит «проверь как работает память», «диагностика Mem0», «пробегись по мему».

## Полный протокол (10 шагов)

### Шаг 0: Проверить что всё стартует
- Qdrant: `docker ps | grep qdrant`
- MCP server: MCP tools отвечают (просто вызвать memory_stats)

### Шаг 1: Qdrant статус
```bash
# Версия + здоровье
curl -s http://localhost:6333/ | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2, ensure_ascii=False))"

# Список коллекций
curl -s http://localhost:6333/collections | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2, ensure_ascii=False)[:2000])"
```

Ключевое: версия (минимум 1.18), коллекции (должны быть `zinaida_memories` и `mem0migrations`).

### Шаг 2: Детали коллекции zinaida_memories
```bash
curl -s "http://localhost:6333/collections/zinaida_memories" | python3 -c "
import sys,json
d=json.load(sys.stdin)
res=d.get('result',{})
print('Статус:', res.get('status'))
print('Точек:', res.get('points_count'))
print('Конфиг:', json.dumps(res.get('config'), indent=2, ensure_ascii=False)[:2000])
"
```

Ключевое:
- status = **green** (жёлтый = деградация)
- points_count = сколько векторов (должно совпадать с числом записей ± удалённые)
- vectors.size = 768 (e5-base)
- on_disk = true (вектора и payload)

### Шаг 3: Количество записей в Mem0
```bash
# Через MCP инструмент
mcp_mem0_memory_memory_stats(user_id="zinaida")
mcp_mem0_memory_get_all_memories(limit=50, user_id="zinaida")
```

Ключевое:
- total_memories: сколько уникальных записей
- status: healthy
- Посмотреть последние 10 — нет ли мусора/дубликатов

### Шаг 4: Проверить MCP server логи на ошибки
```bash
tail -30 /opt/zinaida/mem0/mem0_mcp.log
```

Ключевое:
- `[ERROR] mem0ai not installed: No module named 'mem0'` — проблема с import path (но работает через fallback)
- `[INFO] Processing request...` — нормально
- `Traceback` — плохо

### Шаг 5: Конфиг
```bash
grep -A 40 '"config"' /opt/zinaida/mem0/mem0_mcp_server.py | head -50
```

Ключевое:
- Модель: intfloat/multilingual-e5-base (768-dim, не MiniLM)
- LLM: deepseek-chat, роутер 8003, temp=0.3, max_tokens=4000
- on_disk: True

### Шаг 6: Тест семантического поиска
```bash
mcp_mem0_memory_search_memories(query="контент-завод фазы отношений", user_id="zinaida", limit=5)
```

Ключевое:
- Должен находить релевантные записи (scores 0.70+)
- Первый результат — самый релевантный
- Если scores < 0.50 — проблема с embedding или пустая БД

### Шаг 7: Qdrant ресурсы
```bash
# RAM + CPU контейнера
docker stats qdrant --no-stream

# Диск
du -sh /opt/zinaida/mem0/qdrant_storage/
du -sh /opt/zinaida/mem0/

# HF кэш
du -sh ~/.cache/huggingface/
```

Ключевое:
- Qdrant RAM: ~20-30 MB для 20-40 записей
- Диск Qdrant: ~1-2 MB для маленькой БД
- HF кэш: ~1.8 GB (e5-base модель)

### Шаг 8: Бэкапы
```bash
# Снапшоты Qdrant
curl -s "http://localhost:6333/collections/zinaida_memories/snapshots" | python3 -c "
import sys,json
d=json.load(sys.stdin)
snaps=d.get('result',[])
for s in snaps:
    print(f'  {s.get(\"name\")} — {s.get(\"creation_time\",\"?\")[:19]} — {s.get(\"size\",0)/1024:.0f}KB')
"

# Скрипт бэкапа
cat /opt/zinaida/mem0/backup_qdrant.sh | head -5

# Автоматизация?
systemctl list-timers --all | grep qdrant
crontab -l | grep qdrant
```

Ключевое:
- Снапшоты должны быть < 2 дней (ежедневно)
- Скрипт backup_qdrant.sh должен запускаться автоматически (cron/systemd timer)

### Шаг 9: Проверить HF_TOKEN
```bash
# Установлен ли токен для HuggingFace
grep HF_TOKEN /opt/zinaida/.env /opt/zinaida/meta_agent/.env /root/.hermes/.env 2>/dev/null
```

Ключевое:
- Без HF_TOKEN: `[WARNING] You are sending unauthenticated requests to the HF Hub` — rate-limit при загрузке
- Модель в кэше — не критично, но на холодном старте тормозит

### Шаг 10: Итоговый чеклист (для отчёта Олегу)
| Параметр | OK? | Критерий |
|----------|-----|----------|
| Qdrant версия 1.18+ | ✅/❌ | |
| Коллекция green | ✅/❌ | |
| Точки > 0 | ✅/❌ | |
| MCP инструменты отвечают | ✅/❌ | |
| Поиск находит релевантно | ✅/❌ | scores > 0.70 |
| Нет ERROR в логах | ✅/❌ | |
| on_disk = True | ✅/❌ | |
| Embedding e5-base | ✅/❌ | |
| Бэкап автоматизирован | ✅/❌ | |
| HF_TOKEN установлен | ✅/❌ | |

## Реальный кейс (12.07.2026)

Проверяли Mem0 по просьбе Олега. Нашли:
- 20 записей, поиск работает (scores 0.78-0.84) ✅
- ERROR в логах «mem0ai not installed» — падает import, но работает через fallback к прямому Qdrant API ⚠️
- Нет автоматизации бэкапа (скрипт есть, но не в cron) ❌
- HF_TOKEN не установлен (warning при старте) ⚠️
- Embedding модель на диске: 1.8 GB ✅

Фикс: backup_qdrant.sh добавить в cron, HF_TOKEN прописать, import path поправить.
