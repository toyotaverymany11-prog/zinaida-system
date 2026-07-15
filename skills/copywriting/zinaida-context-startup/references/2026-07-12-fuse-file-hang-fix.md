# FUSE/OneDrive file system hangs — Python text-mode open

**Дата:** 2026-07-12
**Симптом:** Python скрипт (server_research.py) зависает на `Path.iterdir()` или `open()` с `encoding='utf-8'` после ~40 открытых файлов. `bash ls/head` работают нормально. `os.listdir()` работает, но `open(fname, 'r', encoding='utf-8')` виснет.

**Корень:** Файловая система через FUSE/rclone/OneDrive. Python делает decode буфер при text-режиме, системный вызов `read()` упирается в FUSE, который при превышении лимита дескрипторов блокируется.

## Симптомы диагностики
- `sorted(Path.iterdir())` — зависает. Замена на `sorted(os.listdir(dir))` работает
- `open(path, 'r', encoding='utf-8')` — зависает после ~40 файлов
- `open(path, 'rb')` — работает. `bash cat/head` — работает
- В изоляции (маленький набор файлов) — всё работает. В полном цикле (все 54 файла) — виснет

## Решение
1. Заменить `Path.iterdir()` на `os.listdir()`
2. Заменить text-mode `open()` на binary: `open(path, 'rb')` + `.decode('utf-8', errors='replace')`
3. Для поиска по содержимому — использовать `subprocess.run(["grep", "-ril", kw, dir])` вместо ручного перебора

## Пример проблемного кода
```python
# ❌ ВИСНЕТ на FUSE
for f in sorted(STATS.iterdir()):
    content = f.read_text(encoding='utf-8')[:500]

# ✅ РАБОТАЕТ
for fname in sorted(os.listdir(stats_dir)):
    with open(os.path.join(stats_dir, fname), 'rb') as fh:
        raw = fh.read(500)
    content = raw.decode('utf-8', errors='replace')
```

## Какие файлы пострадали
- `/opt/zinaida/scripts/server_research.py` — Агент 3 (statistics) и Агент 4 (templates) — переписаны
- `stats/mechanics/` — 54 файла статистики
- `cta_library/` — 9 файлов
- `hooks/templates/` — 38 файлов

## Схемы БД (обнаружены при фиксе 12.07)
- `phases.db` — поле `trigger_action` (не `trigger`), `hook_template_id` (не `hook_id`)
- `smm_rag.db` FTS5 — колонка `project_name` (не `source`)
