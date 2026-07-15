# RAG-отравление контекста - проблема и фикс

**Дата:** 12.07.2026
**Симптом:** В ответах Зинаиды появляются старые паттерны: «она берёт телефон», «она проверяет локацию», «тайминг 2:40 ночи» — хотя эти паттерны запрещены в 14_WRITER_FORMATION.md.

## Причина

Router 8005 (router_8005_v2.py) в каждом запросе запускает Server RAG (функция `_search_rag`, строка 211). RAG ищет grep-ом файлы на сервере по словам из запроса пользователя.

**До фикса (12.07.2026):**
RAG искал в `/opt/zinaida/memory/` и находил там:
- `post_vk_izmena_draft.txt` — СТАРЫЙ черновик с паттернами
- `post_architecture_latest.txt` — старая структура
- `writer_context_latest.txt` — старый контекст писателя
- `MEMORY.md` — старые правила

DeepSeek получал эти файлы в контекст (строка 731-737) и встраивал их содержимое в ответ.

## Фикс (3 варианта, выполнены 12.07.2026)

### Вариант 1: Удалить файлы-отравители
Файлы перенесены из `/opt/zinaida/memory/` в `/opt/zinaida/memory/archive/`:
- `post_vk_izmena_draft.txt`
- `post_architecture_latest.txt`
- `writer_context_latest.txt`
- `server_research_latest.txt`
- `BASELINE.txt`
- `MEMORY.md`

### Вариант 2: Исключения в RAG
В `router_8005_v2.py` добавлены glob-исключения для rg (строки 249-250):
```python
"--glob", "!archive/*", "--glob", "!*draft*", "--glob", "!*.bak",
```

### Вариант 3: Создан writer_rag/ с проверенными файлами
Создана папка `/opt/zinaida/writer_rag/` с 4 файлами:
- `14_WRITER_FORMATION.md` — ЕДИНСТВЕННЫЙ источник правил писателя
- `02_blacklist.md` — чёрный список
- `oleg_writing_rules_master.md` — все комментарии Олега
- `approved_phrases.md` — одобренные фразы (создан)

RAG настроен искать сначала в `writer_rag/` (приоритетная директория, строка 238), потом в остальных.

### Проверка после фикса
```bash
# writer_rag доступен
rg -i -l "" /opt/zinaida/writer_rag/  # 4 файла

# archive исключён
rg -i -l "измен" /opt/zinaida/memory/archive/  # пусто

# роутер перезапущен
systemctl restart zina2-router-8005.service
```

## Код до/после

**До (старая строка 240-244):**
```python
search_dirs = [
    "/opt/zinaida/meta_agent",
    "/opt/zinaida/memory",
    ...
]
```

**После (новая строка 238-244):**
```python
search_dirs = [
    "/opt/zinaida/writer_rag",  # Приоритет: проверенные файлы писателя
    "/opt/zinaida/meta_agent",
    "/opt/zinaida/memory",
    ...
]
```

**До (старые строки 249-252):**
```python
"-g", "*.md", "-g", "*.py", "-g", "*.yaml",
"-g", "*.yml", "-g", "*.json", "-g", "*.toml",
] + search_dirs
```

**После (новые строки 249-252):**
```python
"-g", "*.md", "-g", "*.py", "-g", "*.yaml",
"-g", "*.yml", "-g", "*.json", "-g", "*.toml",
"--glob", "!archive/*", "--glob", "!*draft*", "--glob", "!*.bak",
] + search_dirs
```

## Когда проверять RAG

Если в новом ответе появились старые паттерны (описание действий читательницы, бытовые детали, тайминги) — первым делом проверить RAG:

1. Открыть `/opt/zinaida/meta_agent/router_8005_v2.py` строка 238 — проверить search_dirs
2. Проверить `/opt/zinaida/writer_rag/` — что там лежит
3. Проверить `/opt/zinaida/memory/archive/` — не вернулись ли файлы
4. Проверить логи роутера: `journalctl -u zina2-router-8005.service --no-pager -n 20 | grep RAG`
